from __future__ import annotations

import argparse
import tempfile
import json
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.request import Request, urlopen

import numpy as np

from motion_edit import cli
from motion_edit.cli import build_parser
from motion_edit.contact import contact_graph_from_masks, write_contact_layer
from motion_edit.io import read_jsonl, write_jsonl
from motion_edit.schema import SegmentRecord
from motion_edit.workbench import (
    WorkbenchSession,
    curate_segment,
    export_cutter_session_file,
    load_workbench_segments,
    make_workbench_server,
    replace_segment,
    select_segment,
    sync_cutter_session_file,
    split_segment,
    trim_segment,
    upsert_workbench_segments,
    validate_workbench_segments,
    write_workbench_segments,
)


def _segment() -> SegmentRecord:
    return SegmentRecord(
        motion_id="motion_a",
        segment_id="motion_a_force_0000",
        start_frame=10,
        end_frame=30,
        source="force_contact",
        status="candidate",
        motion_path="/tmp/motion_a.npz",
        clip_npz="/tmp/motion_a.npz",
    )


def _segment_b() -> SegmentRecord:
    return SegmentRecord(
        motion_id="motion_a",
        segment_id="motion_a_force_0001",
        start_frame=30,
        end_frame=45,
        source="force_contact",
        status="candidate",
        motion_path="/tmp/motion_a.npz",
        clip_npz="/tmp/motion_a.npz",
    )


class WorkbenchActionTests(unittest.TestCase):
    def test_trim_preserves_identity_and_records_provenance(self) -> None:
        trimmed = trim_segment(_segment(), start_frame=12, end_frame=28)

        self.assertEqual(trimmed.segment_id, "motion_a_force_0000")
        self.assertEqual((trimmed.start_frame, trimmed.end_frame), (12, 28))
        edits = trimmed.metadata["motion_edit_edits"]
        self.assertEqual(edits[-1]["kind"], "trim")
        self.assertEqual(edits[-1]["params"]["old_start_frame"], 10)

    def test_trim_outside_original_bounds_raises(self) -> None:
        with self.assertRaises(ValueError):
            trim_segment(_segment(), start_frame=9, end_frame=28)
        with self.assertRaises(ValueError):
            trim_segment(_segment(), start_frame=12, end_frame=31)

    def test_trim_can_extend_when_explicitly_allowed(self) -> None:
        trimmed = trim_segment(_segment(), start_frame=9, end_frame=31, allow_extend=True)

        self.assertEqual((trimmed.start_frame, trimmed.end_frame), (9, 31))

    def test_split_creates_two_valid_child_segments(self) -> None:
        left, right = split_segment(_segment(), frame=18)

        self.assertEqual((left.start_frame, left.end_frame), (10, 18))
        self.assertEqual((right.start_frame, right.end_frame), (18, 30))
        self.assertIn("_split0_10_18", left.segment_id)
        self.assertIn("_split1_18_30", right.segment_id)

    def test_curate_sets_status_and_records_provenance(self) -> None:
        accepted = curate_segment(_segment(), status="accepted")

        self.assertEqual(accepted.status, "accepted")
        edits = accepted.metadata["motion_edit_edits"]
        self.assertEqual(edits[-1]["kind"], "curate")
        self.assertEqual(edits[-1]["params"]["new_status"], "accepted")


class WorkbenchStateTests(unittest.TestCase):
    def test_load_select_replace_and_write_temp_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            layers_root = Path(tmp) / "layers"
            original = _segment()
            write_workbench_segments("candidates/source", [original], layers_root=layers_root)

            loaded = load_workbench_segments("candidates/source", layers_root=layers_root)
            selected = select_segment(loaded, motion_id="motion_a", index=0)
            trimmed = trim_segment(selected, start_frame=11, end_frame=29)
            updated = replace_segment(loaded, selected.segment_id, [trimmed])
            out = write_workbench_segments("manual/workbench_tmp", updated, layers_root=layers_root)

            reloaded = load_workbench_segments(out, layers_root=layers_root)
            self.assertEqual(len(reloaded), 1)
            self.assertEqual((reloaded[0].start_frame, reloaded[0].end_frame), (11, 29))

    def test_upsert_preserves_existing_segments_and_replaces_by_segment_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            layers_root = Path(tmp) / "layers"
            first = curate_segment(_segment(), status="accepted")
            second = curate_segment(_segment_b(), status="accepted")
            updated_first = trim_segment(first, start_frame=12, end_frame=28)

            upsert_workbench_segments("accepted/probe", [first], layers_root=layers_root)
            upsert_workbench_segments("accepted/probe", [second], layers_root=layers_root)
            upsert_workbench_segments("accepted/probe", [updated_first], layers_root=layers_root)

            accepted = load_workbench_segments("accepted/probe", layers_root=layers_root)
            self.assertEqual([segment.segment_id for segment in accepted], ["motion_a_force_0000", "motion_a_force_0001"])
            self.assertEqual((accepted[0].start_frame, accepted[0].end_frame), (12, 28))
            self.assertEqual((accepted[1].start_frame, accepted[1].end_frame), (30, 45))


class CutterSessionTests(unittest.TestCase):
    def test_export_source_layer_to_cutter_session_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layers_root = root / "layers"
            workbench_root = root / "workbench"
            write_workbench_segments("candidates/source", [_segment(), _segment_b()], layers_root=layers_root)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
                body_names=["LF", "RF"],
                source="source",
            )
            write_contact_layer(layers_root / "contact" / "source", graph)

            session = export_cutter_session_file(
                motion_id="motion_a",
                source_layer="candidates/source",
                session_name="session_a",
                motion_path="/tmp/session_motion.npz",
                viewer_port=8123,
                layers_root=layers_root,
                workbench_root=workbench_root,
            )

            records = read_jsonl(session.segment_path)
            self.assertEqual(session.segment_path, workbench_root / "sessions" / "session_a" / "motion_a.segments.jsonl")
            self.assertEqual(session.manifest_path, workbench_root / "sessions" / "session_a" / "session.json")
            self.assertEqual(
                session.contact_overlay_path,
                workbench_root / "sessions" / "session_a" / "motion_a.contact_overlay.json",
            )
            self.assertEqual(len(records), 2)
            meta = records[0]["metadata"]["motion_edit_cutter_session"]
            self.assertEqual(meta["source_layer"], "candidates/source")
            self.assertEqual(meta["session_name"], "session_a")
            self.assertEqual(meta["original_segment_id"], "motion_a_force_0000")
            with session.manifest_path.open("r", encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["session_name"], "session_a")
            self.assertEqual(manifest["source_layer"], "candidates/source")
            self.assertEqual(manifest["motion_path"], "/tmp/session_motion.npz")
            self.assertEqual(manifest["output_layer"], "manual/session_a")
            self.assertEqual(
                manifest["contact_overlay_file"],
                str(workbench_root / "sessions" / "session_a" / "motion_a.contact_overlay.json"),
            )
            self.assertEqual(manifest["viewer_port"], 8123)
            self.assertEqual(manifest["sync_status"], "prepared")

    def test_sync_edited_cutter_jsonl_back_to_manual_session_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layers_root = root / "layers"
            workbench_root = root / "workbench"
            write_workbench_segments("candidates/source", [_segment(), _segment_b()], layers_root=layers_root)
            contact = np.zeros((60, 2), dtype=bool)
            contact[:, 1] = True
            contact[12:28, 0] = True
            active = np.zeros((60, 2), dtype=bool)
            active[12:28, 0] = True
            support = np.zeros((60, 2), dtype=bool)
            support[:, 1] = True
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=contact,
                active_mask=active,
                support_mask=support,
                proto_starts=[12],
                proto_ends=[28],
                body_names=["LF", "RF"],
                source="source",
            )
            write_contact_layer(layers_root / "contact" / "source", graph)
            session = export_cutter_session_file(
                motion_id="motion_a",
                source_layer="candidates/source",
                session_name="session_a",
                layers_root=layers_root,
                workbench_root=workbench_root,
            )
            records = read_jsonl(session.segment_path)
            records[0]["start_frame"] = 12
            records[0]["end_frame"] = 28
            records.append(
                {
                    "motion_id": "motion_a",
                    "segment_id": "motion_a_new_cut",
                    "start_frame": 45,
                    "end_frame": 60,
                    "clip_npz": "/tmp/motion_a.npz",
                }
            )
            write_jsonl(session.segment_path, records)

            out = sync_cutter_session_file(
                session.segment_path,
                source_layer="candidates/source",
                session_name="session_a",
                layers_root=layers_root,
            )

            synced = load_workbench_segments("manual/session_a", layers_root=layers_root)
            self.assertEqual(out, layers_root / "manual" / "session_a")
            self.assertEqual([segment.segment_id for segment in synced], ["motion_a_force_0000", "motion_a_force_0001", "motion_a_new_cut"])
            self.assertEqual((synced[0].start_frame, synced[0].end_frame), (12, 28))
            self.assertTrue(all(segment.status == "manual" for segment in synced))
            self.assertTrue(all(segment.source == "viser_cutter" for segment in synced))
            first_meta = synced[0].metadata["motion_edit_cutter_session"]
            new_meta = synced[2].metadata["motion_edit_cutter_session"]
            self.assertEqual(first_meta["edit_source"], "viser_cutter")
            self.assertEqual(first_meta["original_segment_id"], "motion_a_force_0000")
            self.assertIsNone(new_meta["original_segment_id"])
            self.assertEqual(synced[0].metadata["active_body"], "LF")
            self.assertEqual(synced[0].metadata["support_bodies"], ["RF"])
            self.assertEqual(synced[0].metadata["contact_binding"]["transition_id"], graph.transitions[0].transition_id)
            edit = synced[0].metadata["motion_edit_edits"][-1]
            self.assertEqual(edit["kind"], "import_from_cutter")
            self.assertEqual(edit["source"], "viser_cutter")
            self.assertEqual(edit["params"]["source_layer"], "candidates/source")
            with (workbench_root / "sessions" / "session_a" / "session.json").open("r", encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["sync_status"], "synced")
            self.assertEqual(manifest["output_layer"], "manual/session_a")

    def test_sync_to_accepted_layer_uses_upsert_and_sets_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layers_root = root / "layers"
            workbench_root = root / "workbench"
            existing = curate_segment(_segment(), status="accepted")
            write_workbench_segments("candidates/source", [_segment(), _segment_b()], layers_root=layers_root)
            upsert_workbench_segments("accepted/curated", [existing], layers_root=layers_root)
            session = export_cutter_session_file(
                motion_id="motion_a",
                source_layer="candidates/source",
                session_name="session_a",
                layers_root=layers_root,
                workbench_root=workbench_root,
            )
            records = read_jsonl(session.segment_path)
            write_jsonl(session.segment_path, [records[1]])

            sync_cutter_session_file(
                session.segment_path,
                source_layer="candidates/source",
                session_name="session_a",
                destination_layer="accepted/curated",
                layers_root=layers_root,
            )

            accepted = load_workbench_segments("accepted/curated", layers_root=layers_root)
            self.assertEqual([segment.segment_id for segment in accepted], ["motion_a_force_0000", "motion_a_force_0001"])
            self.assertTrue(all(segment.status == "accepted" for segment in accepted))
            self.assertEqual(accepted[1].metadata["motion_edit_edits"][-1]["params"]["new_status"], "accepted")

    def test_validate_workbench_segments_reports_duplicate_missing_path_and_overlap(self) -> None:
        duplicate = SegmentRecord(
            motion_id="motion_a",
            segment_id="motion_a_force_0000",
            start_frame=20,
            end_frame=40,
            source="force_contact",
            status="accepted",
        )

        warnings = validate_workbench_segments(
            [curate_segment(_segment(), status="accepted"), duplicate],
            destination="accepted/probe",
        )

        self.assertTrue(any("duplicate segment_id" in warning for warning in warnings))
        self.assertTrue(any("missing motion_path/clip_npz" in warning for warning in warnings))
        self.assertTrue(any("accepted overlap" in warning for warning in warnings))


class WorkbenchSessionTests(unittest.TestCase):
    def test_session_trim_and_accept_use_action_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            layers_root = Path(tmp) / "layers"
            write_workbench_segments("candidates/source", [_segment()], layers_root=layers_root)
            session = WorkbenchSession(
                source="candidates/source",
                motion_id="motion_a",
                selected_index=0,
                output_source="manual/workbench_tmp",
                layers_root=layers_root,
            )

            trimmed_state = session.trim(start_frame=12, end_frame=24)
            accepted_state = session.accept(output_source="accepted/session_probe")

            self.assertEqual(trimmed_state["selected_segment"]["start_frame"], 12)
            self.assertIn("manual/workbench_tmp", trimmed_state["last_write"])
            self.assertIn("accepted/session_probe", accepted_state["last_write"])
            self.assertEqual(accepted_state["selected_segment"]["status"], "accepted")
            accepted = load_workbench_segments("accepted/session_probe", layers_root=layers_root)
            self.assertEqual(accepted[0].status, "accepted")

    def test_session_accepting_two_segments_preserves_both_in_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            layers_root = Path(tmp) / "layers"
            write_workbench_segments("candidates/source", [_segment(), _segment_b()], layers_root=layers_root)
            session = WorkbenchSession(
                source="candidates/source",
                motion_id="motion_a",
                selected_index=0,
                layer_name="session_probe",
                layers_root=layers_root,
            )

            first_state = session.accept()
            session.set_selection(motion_id="motion_a", index=1)
            second_state = session.accept()

            accepted = load_workbench_segments("accepted/session_probe", layers_root=layers_root)
            self.assertEqual(len(accepted), 2)
            self.assertEqual([segment.segment_id for segment in accepted], ["motion_a_force_0000", "motion_a_force_0001"])
            self.assertEqual(first_state["selected_segment"]["status"], "accepted")
            self.assertEqual(second_state["selected_segment"]["status"], "accepted")

    def test_server_state_and_trim_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            layers_root = Path(tmp) / "layers"
            write_workbench_segments("candidates/source", [_segment()], layers_root=layers_root)
            session = WorkbenchSession(
                source="candidates/source",
                motion_id="motion_a",
                selected_index=0,
                dry_run=True,
                layers_root=layers_root,
            )
            try:
                server = make_workbench_server(session, port=0)
            except PermissionError as exc:
                self.skipTest(f"local sockets are unavailable in this sandbox: {exc}")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_address[1]}"
                with urlopen(f"{base}/api/state", timeout=2) as response:
                    state = json.loads(response.read().decode("utf-8"))
                request = Request(
                    f"{base}/api/trim",
                    data=json.dumps({"start_frame": 13, "end_frame": 25}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    trimmed = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            self.assertEqual(state["selected_segment_id"], "motion_a_force_0000")
            self.assertEqual(trimmed["selected_segment"]["start_frame"], 13)
            self.assertEqual(trimmed["last_write"], "dry-run:manual/workbench_tmp")


class WorkbenchCliTests(unittest.TestCase):
    def test_parser_keeps_existing_view_and_adds_workbench_action(self) -> None:
        parser = build_parser()
        view_args = parser.parse_args(["view", "motion.npz"])
        workbench_server_args = parser.parse_args(
            [
                "workbench",
                "motion.npz",
                "--source",
                "candidates/source",
                "--motion-id",
                "motion_a",
                "--once",
            ]
        )
        workbench_args = parser.parse_args(
            [
                "workbench-action",
                "--source",
                "candidates/source",
                "--motion-id",
                "motion_a",
                "--index",
                "0",
                "--action",
                "trim",
                "--start-frame",
                "11",
                "--end-frame",
                "29",
                "--dry-run",
            ]
        )
        contact_args = parser.parse_args(["list-contact-layer", "--source", "contact/force_contact", "--motion-id", "motion_a"])
        overlay_args = parser.parse_args(
            ["export-contact-overlay", "--source", "contact/force_contact", "--motion-id", "motion_a", "--output", "overlay.json"]
        )

        self.assertEqual(view_args.cmd, "view")
        self.assertEqual(workbench_server_args.cmd, "workbench")
        self.assertEqual(workbench_args.cmd, "workbench-action")
        self.assertEqual(contact_args.cmd, "list-contact-layer")
        self.assertEqual(overlay_args.cmd, "export-contact-overlay")
        self.assertTrue(workbench_args.dry_run)

    def test_existing_view_command_still_calls_launch_viewer(self) -> None:
        process = mock.Mock()
        args = argparse.Namespace(
            motion="motion.npz",
            repo_root=None,
            layer=None,
            conda_env="hsretargeting",
            timeline_port=8094,
            fps=50,
            with_terrain=False,
        )
        with mock.patch.object(cli, "launch_viewer", return_value=process) as launch_mock:
            cli._cmd_view(args)

        launch_mock.assert_called_once_with(
            "motion.npz",
            repo_root=None,
            layer=None,
            conda_env="hsretargeting",
            timeline_port=8094,
            fps=50,
            with_terrain=False,
        )
        process.wait.assert_called_once()

    def test_workbench_action_dry_run_executes_without_writing(self) -> None:
        args = argparse.Namespace(
            source="candidates/source",
            motion_id="motion_a",
            segment_id=None,
            index=0,
            action="trim",
            start_frame=11,
            end_frame=29,
            frame=None,
            output_source=None,
            layer_name="workbench_tmp",
            dry_run=True,
        )
        with (
            mock.patch.object(cli, "load_workbench_segments", return_value=[_segment()]),
            mock.patch.object(cli, "write_workbench_segments") as write_mock,
        ):
            cli._cmd_workbench_action(args)

        write_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
