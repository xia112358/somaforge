from __future__ import annotations

import tempfile
import json
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from motion_edit.cli import build_parser
from motion_edit.schema import SegmentRecord
from motion_edit.workbench import (
    WorkbenchSession,
    curate_segment,
    load_workbench_segments,
    make_workbench_server,
    replace_segment,
    select_segment,
    split_segment,
    trim_segment,
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


class WorkbenchActionTests(unittest.TestCase):
    def test_trim_preserves_identity_and_records_provenance(self) -> None:
        trimmed = trim_segment(_segment(), start_frame=12, end_frame=28)

        self.assertEqual(trimmed.segment_id, "motion_a_force_0000")
        self.assertEqual((trimmed.start_frame, trimmed.end_frame), (12, 28))
        edits = trimmed.metadata["motion_edit_edits"]
        self.assertEqual(edits[-1]["kind"], "trim")
        self.assertEqual(edits[-1]["params"]["old_start_frame"], 10)

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
            accepted = load_workbench_segments("accepted/session_probe", layers_root=layers_root)
            self.assertEqual(accepted[0].status, "accepted")

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

        self.assertEqual(view_args.cmd, "view")
        self.assertEqual(workbench_server_args.cmd, "workbench")
        self.assertEqual(workbench_args.cmd, "workbench-action")
        self.assertTrue(workbench_args.dry_run)


if __name__ == "__main__":
    unittest.main()
