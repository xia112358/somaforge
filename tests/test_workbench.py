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
from motion_edit.contact import (
    ContactSurfaceRecord,
    contact_graph_from_masks,
    read_contact_edit_plan,
    read_contact_graph,
    write_contact_layer,
    write_contact_surfaces,
)
from motion_edit.io import read_jsonl, write_jsonl
from motion_edit.schema import SegmentRecord
from motion_edit.viewer.app import launch_viewer
from motion_edit.workbench import (
    WorkbenchSession,
    curate_segment,
    export_cutter_session_file,
    load_workbench_segments,
    make_workbench_server,
    move_surface_editor_anchor,
    prepare_surface_editor_session,
    read_surface_editor_requests,
    replace_segment,
    select_segment,
    save_surface_editor_session,
    sync_surface_editor_requests,
    sync_cutter_session_file,
    split_segment,
    trim_segment,
    upsert_workbench_segments,
    validate_workbench_segments,
    write_workbench_segments,
)
from motion_edit.viewer.surface_overlay_player import (
    append_move_request,
    apply_direct_anchor_move,
    load_editor_state,
    load_surface_overlay,
    save_editor_state,
    surface_quad_corners,
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


class SurfaceEditorSessionTests(unittest.TestCase):
    def test_surface_editor_session_moves_anchor_and_saves_layer_and_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"original")
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.asarray([[[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]]]),
                body_names=["LF"],
            )
            surface = ContactSurfaceRecord(
                motion_id="motion_a",
                surface_id="top",
                object_id="box",
                surface_type="box_face",
                origin=[0.0, 0.0, 0.0],
                normal=[0.0, 0.0, 1.0],
                tangent_u=[1.0, 0.0, 0.0],
                tangent_v=[0.0, 1.0, 0.0],
                bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
            )
            # Bind the generated anchor enough for surface-constrained editor moves.
            anchor = graph.anchors[0]
            graph = type(graph)(
                motion_id=graph.motion_id,
                events=graph.events,
                anchors=[
                    type(anchor)(
                        **{
                            **anchor.__dict__,
                            "surface_id": "top",
                            "surface_normal": [0.0, 0.0, 1.0],
                            "surface_origin": [0.0, 0.0, 0.0],
                            "surface_tangent_u": [1.0, 0.0, 0.0],
                            "surface_tangent_v": [0.0, 1.0, 0.0],
                            "surface_bounds": {"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
                            "surface_coordinates": {"u": 0.0, "v": 0.0},
                        }
                    )
                ],
                patches=graph.patches,
                transitions=graph.transitions,
            )
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            write_contact_surfaces(root / "surfaces.jsonl", [surface])
            plan_path = root / "surface_plan.json"
            session = prepare_surface_editor_session(
                motion_path=str(motion),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=str(root / "surfaces.jsonl"),
                session_name="session_a",
                edit_plan_path=str(plan_path),
                output_contact_layer="contact/edited",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            moved_graph, edit = move_surface_editor_anchor(
                session,
                anchor_id=graph.anchors[0].anchor_id,
                tangent_delta=[0.1, 0.0],
            )
            out_layer = save_surface_editor_session(session, layers_root=root / "layers")
            edited = read_contact_graph(root / "layers" / "contact" / "edited", "motion_a")
            plan = read_contact_edit_plan(plan_path)
            overlay = json.loads(session.overlay_path.read_text(encoding="utf-8"))
            motion_bytes = motion.read_bytes()
            report_exists = session.report_path.exists()
            contact_overlay_exists = session.contact_overlay_path.exists()
            state_exists = session.state_path.exists()

        self.assertEqual(motion_bytes, b"original")
        self.assertTrue(report_exists)
        self.assertTrue(contact_overlay_exists)
        self.assertTrue(state_exists)
        self.assertEqual(moved_graph.anchors[0].world_position, [0.1, 0.0, 0.0])
        self.assertEqual(edit.delta_world, [0.1, 0.0, 0.0])
        self.assertEqual(edited.anchors[0].world_position, [0.1, 0.0, 0.0])
        self.assertEqual(out_layer, root / "layers" / "contact" / "edited")
        self.assertEqual(plan.status, "draft")
        self.assertEqual(plan.edits[0]["source"], "viser_surface_editor")
        self.assertEqual(plan.edits[0]["metadata"]["binding_granularity"], "anchor_point")
        anchor_point = next(item for item in overlay["objects"] if item["type"] == "anchor_point")
        self.assertEqual(anchor_point["status"], "edited")

    def test_surface_editor_move_rejects_outside_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchor_graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.asarray([[[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]]]),
                body_names=["LF"],
            )
            anchor = anchor_graph.anchors[0]
            bound_anchor = type(anchor)(
                **{
                    **anchor.__dict__,
                    "surface_id": "top",
                    "surface_normal": [0.0, 0.0, 1.0],
                    "surface_origin": [0.0, 0.0, 0.0],
                    "surface_tangent_u": [1.0, 0.0, 0.0],
                    "surface_tangent_v": [0.0, 1.0, 0.0],
                    "surface_bounds": {"u": [-0.05, 0.05], "v": [-0.05, 0.05]},
                    "surface_coordinates": {"u": 0.0, "v": 0.0},
                }
            )
            graph = type(anchor_graph)(
                motion_id="motion_a",
                events=anchor_graph.events,
                anchors=[bound_anchor],
                patches=anchor_graph.patches,
                transitions=anchor_graph.transitions,
            )
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="session_bounds",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )

            with self.assertRaisesRegex(ValueError, "bounds"):
                move_surface_editor_anchor(session, anchor_id=bound_anchor.anchor_id, tangent_delta=[0.1, 0.0])

    def test_surface_editor_cli_prepares_session_and_launches_viewer_without_saving_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"original")
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.asarray([[[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]]]),
                body_names=["LF"],
            )
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            process = mock.Mock(pid=1234)
            process.wait.return_value = None
            with (
                mock.patch.object(cli, "LAYERS_ROOT", root / "layers"),
                mock.patch.object(cli, "WORKBENCH_ROOT", root / "workbench"),
                mock.patch.object(cli, "launch_viewer", return_value=process) as launch_mock,
            ):
                cli._cmd_surface_editor(
                    type(
                        "Args",
                        (),
                        {
                            "motion": str(motion),
                            "motion_id": "motion_a",
                            "contact_layer": "contact/bound",
                            "surface_catalog": None,
                            "session_name": "surface_a",
                            "edit_plan": None,
                            "output_contact_layer": "contact/edited",
                            "repo_root": None,
                            "conda_env": "hsretargeting",
                            "timeline_port": 8094,
                            "fps": 50,
                            "with_terrain": False,
                            "save_on_exit": False,
                            "edit_mode": "direct",
                            "external_viewer": False,
                        },
                    )()
                )
                session_dir = root / "workbench" / "surface_sessions" / "surface_a"
                report_exists = (session_dir / "motion_a.surface_binding_report.json").exists()
                overlay_exists = (session_dir / "motion_a.surface_binding_overlay.json").exists()
                contact_overlay_exists = (session_dir / "motion_a.contact_overlay.json").exists()
                motion_bytes = motion.read_bytes()
                output_layer_exists = (root / "layers" / "contact" / "edited").exists()

        launch_mock.assert_called_once()
        launch_kwargs = launch_mock.call_args.kwargs
        self.assertTrue(str(launch_kwargs["surface_binding_overlay"]).endswith("motion_a.surface_binding_overlay.json"))
        self.assertTrue(str(launch_kwargs["surface_editor_requests"]).endswith("motion_a.surface_editor_requests.jsonl"))
        self.assertEqual(launch_kwargs["surface_editor_edit_mode"], "direct")
        self.assertFalse(launch_kwargs["prefer_local_surface_editor"] is False)
        self.assertEqual(motion_bytes, b"original")
        self.assertTrue(report_exists)
        self.assertTrue(overlay_exists)
        self.assertTrue(contact_overlay_exists)
        self.assertFalse(output_layer_exists)

    def test_surface_editor_cli_save_on_exit_writes_output_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"original")
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.asarray([[[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]]]),
                body_names=["LF"],
            )
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            process = mock.Mock(pid=1234)
            process.wait.return_value = None
            with (
                mock.patch.object(cli, "LAYERS_ROOT", root / "layers"),
                mock.patch.object(cli, "WORKBENCH_ROOT", root / "workbench"),
                mock.patch.object(cli, "launch_viewer", return_value=process),
            ):
                cli._cmd_surface_editor(
                    type(
                        "Args",
                        (),
                        {
                            "motion": str(motion),
                            "motion_id": "motion_a",
                            "contact_layer": "contact/bound",
                            "surface_catalog": None,
                            "session_name": "surface_save",
                            "edit_plan": None,
                            "output_contact_layer": "contact/edited",
                            "repo_root": None,
                            "conda_env": "hsretargeting",
                            "timeline_port": 8094,
                            "fps": 50,
                            "with_terrain": False,
                            "save_on_exit": True,
                            "edit_mode": "direct",
                            "external_viewer": False,
                        },
                    )()
                )
                saved = read_contact_graph(root / "layers" / "contact" / "edited", "motion_a")

        self.assertEqual(len(saved.anchors), 1)

    def test_surface_editor_move_anchor_cli_updates_session_and_can_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.asarray([[[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]]]),
                body_names=["LF"],
            )
            anchor = graph.anchors[0]
            bound_anchor = type(anchor)(
                **{
                    **anchor.__dict__,
                    "surface_id": "top",
                    "surface_normal": [0.0, 0.0, 1.0],
                    "surface_origin": [0.0, 0.0, 0.0],
                    "surface_tangent_u": [1.0, 0.0, 0.0],
                    "surface_tangent_v": [0.0, 1.0, 0.0],
                    "surface_bounds": {"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
                    "surface_coordinates": {"u": 0.0, "v": 0.0},
                }
            )
            graph = type(graph)(motion_id="motion_a", events=graph.events, anchors=[bound_anchor], patches=graph.patches, transitions=graph.transitions)
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="surface_move",
                output_contact_layer="contact/edited",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            with mock.patch.object(cli, "LAYERS_ROOT", root / "layers"):
                cli._cmd_surface_editor_move_anchor(
                    type(
                        "Args",
                        (),
                        {
                            "session": str(session.session_dir / "session.json"),
                            "anchor_id": bound_anchor.anchor_id,
                            "tangent_delta": [0.1, 0.0],
                            "requested_world_position": None,
                            "mode": "reject",
                            "save": True,
                        },
                    )()
                )
                saved = read_contact_graph(root / "layers" / "contact" / "edited", "motion_a")

        self.assertEqual(saved.anchors[0].world_position, [0.1, 0.0, 0.0])

    def test_surface_editor_sync_applies_request_and_can_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.asarray([[[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]]]),
                body_names=["LF"],
            )
            anchor = graph.anchors[0]
            bound_anchor = type(anchor)(
                **{
                    **anchor.__dict__,
                    "surface_id": "top",
                    "surface_normal": [0.0, 0.0, 1.0],
                    "surface_origin": [0.0, 0.0, 0.0],
                    "surface_tangent_u": [1.0, 0.0, 0.0],
                    "surface_tangent_v": [0.0, 1.0, 0.0],
                    "surface_bounds": {"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
                    "surface_coordinates": {"u": 0.0, "v": 0.0},
                }
            )
            graph = type(graph)(motion_id="motion_a", events=graph.events, anchors=[bound_anchor], patches=graph.patches, transitions=graph.transitions)
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="surface_sync",
                output_contact_layer="contact/edited",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            append_move_request(
                session.request_path,
                anchor_id=bound_anchor.anchor_id,
                tangent_delta=[0.2, 0.0],
                mode="reject",
            )
            count, out = sync_surface_editor_requests(session, save=True, layers_root=root / "layers")
            saved = read_contact_graph(root / "layers" / "contact" / "edited", "motion_a")
            requests = read_surface_editor_requests(session)
            overlay = load_surface_overlay(session.overlay_path)

        self.assertEqual(count, 1)
        self.assertEqual(out, root / "layers" / "contact" / "edited")
        self.assertEqual(saved.anchors[0].world_position, [0.2, 0.0, 0.0])
        self.assertEqual(requests[0]["anchor_id"], bound_anchor.anchor_id)
        anchor_point = next(item for item in overlay["objects"] if item["type"] == "anchor_point")
        self.assertEqual(anchor_point["status"], "edited")

    def test_surface_overlay_direct_move_and_save_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.asarray([[[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]]]),
                body_names=["LF"],
            )
            anchor = graph.anchors[0]
            bound_anchor = type(anchor)(
                **{
                    **anchor.__dict__,
                    "surface_id": "top",
                    "surface_normal": [0.0, 0.0, 1.0],
                    "surface_origin": [0.0, 0.0, 0.0],
                    "surface_tangent_u": [1.0, 0.0, 0.0],
                    "surface_tangent_v": [0.0, 1.0, 0.0],
                    "surface_bounds": {"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
                    "surface_coordinates": {"u": 0.0, "v": 0.0},
                }
            )
            graph = type(graph)(motion_id="motion_a", events=graph.events, anchors=[bound_anchor], patches=graph.patches, transitions=graph.transitions)
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="surface_direct",
                output_contact_layer="contact/edited",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            result = apply_direct_anchor_move(
                state,
                anchor_id=bound_anchor.anchor_id,
                tangent_delta=[0.3, 0.0],
                mode="reject",
            )
            out = save_editor_state(state, layers_root=root / "layers")
            saved = read_contact_graph(root / "layers" / "contact" / "edited", "motion_a")
            overlay = load_surface_overlay(session.overlay_path)

        self.assertEqual(result["delta_world"], [0.3, 0.0, 0.0])
        self.assertEqual(state.applied_edit_count, 1)
        self.assertEqual(out, root / "layers" / "contact" / "edited")
        self.assertEqual(saved.anchors[0].world_position, [0.3, 0.0, 0.0])
        anchor_point = next(item for item in overlay["objects"] if item["type"] == "anchor_point")
        self.assertEqual(anchor_point["status"], "edited")

    def test_surface_overlay_direct_move_records_error_for_reject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.asarray([[[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]]]),
                body_names=["LF"],
            )
            anchor = graph.anchors[0]
            bound_anchor = type(anchor)(
                **{
                    **anchor.__dict__,
                    "surface_id": "top",
                    "surface_normal": [0.0, 0.0, 1.0],
                    "surface_origin": [0.0, 0.0, 0.0],
                    "surface_tangent_u": [1.0, 0.0, 0.0],
                    "surface_tangent_v": [0.0, 1.0, 0.0],
                    "surface_bounds": {"u": [-0.1, 0.1], "v": [-0.1, 0.1]},
                    "surface_coordinates": {"u": 0.0, "v": 0.0},
                }
            )
            graph = type(graph)(motion_id="motion_a", events=graph.events, anchors=[bound_anchor], patches=graph.patches, transitions=graph.transitions)
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="surface_reject",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")

            with self.assertRaises(ValueError):
                apply_direct_anchor_move(
                    state,
                    anchor_id=bound_anchor.anchor_id,
                    tangent_delta=[0.3, 0.0],
                    mode="reject",
                )

    def test_surface_overlay_helper_reuses_or_computes_corners(self) -> None:
        corners = surface_quad_corners(
            {
                "type": "surface_quad",
                "origin": [1.0, 2.0, 0.0],
                "tangent_u": [1.0, 0.0, 0.0],
                "tangent_v": [0.0, 1.0, 0.0],
                "bounds": {"u": [-1.0, 1.0], "v": [-2.0, 2.0]},
            }
        )

        self.assertEqual(corners[0], [0.0, 0.0, 0.0])
        self.assertEqual(corners[2], [2.0, 4.0, 0.0])

    def test_launch_viewer_uses_local_surface_adapter_direct_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"npz")
            overlay = root / "overlay.json"
            overlay.write_text("{}", encoding="utf-8")
            session = root / "session.json"
            session.write_text("{}", encoding="utf-8")
            requests = root / "requests.jsonl"
            process = mock.Mock(pid=1234)
            with mock.patch("motion_edit.viewer.app.subprocess.Popen", return_value=process) as popen:
                returned = launch_viewer(
                    motion,
                    surface_binding_overlay=overlay,
                    surface_editor_session=session,
                    surface_editor_requests=requests,
                    surface_editor_edit_mode="direct",
                )
            cmd = popen.call_args.args[0]

        self.assertIs(returned, process)
        self.assertIn("motion_edit.viewer.surface_overlay_player", cmd)
        self.assertIn("--edit-mode", cmd)
        self.assertEqual(cmd[cmd.index("--edit-mode") + 1], "direct")


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
        validate_plan_args = parser.parse_args(["validate-contact-edit-plan", "--plan", "plan.json"])
        generate_args = parser.parse_args(["generate-lte-augmentation", "--plan", "plan.json", "--output-motion", "out.npz"])
        move_anchor_args = parser.parse_args(
            [
                "move-contact-anchor",
                "--source",
                "contact/force_contact",
                "--motion-id",
                "motion_a",
                "--anchor-id",
                "anchor_lf",
                "--delta-world",
                "0.1",
                "0",
                "0",
                "--edit-plan",
                "plan.json",
                "--source-motion",
                "motion_a.npz",
                "--source-segments",
                "candidates/force_contact",
            ]
        )

        self.assertEqual(view_args.cmd, "view")
        self.assertEqual(workbench_server_args.cmd, "workbench")
        self.assertEqual(workbench_args.cmd, "workbench-action")
        self.assertEqual(contact_args.cmd, "list-contact-layer")
        self.assertEqual(overlay_args.cmd, "export-contact-overlay")
        self.assertEqual(validate_plan_args.cmd, "validate-contact-edit-plan")
        self.assertEqual(generate_args.cmd, "generate-lte-augmentation")
        self.assertFalse(generate_args.allow_draft)
        self.assertEqual(move_anchor_args.cmd, "move-contact-anchor")
        self.assertEqual(move_anchor_args.delta_world, [0.1, 0.0, 0.0])
        self.assertIsNone(move_anchor_args.tangent_delta)
        self.assertEqual(move_anchor_args.mode, "reject")
        self.assertFalse(move_anchor_args.allow_free_3d)
        self.assertEqual(move_anchor_args.edit_plan, "plan.json")
        self.assertEqual(move_anchor_args.source_motion, "motion_a.npz")
        self.assertEqual(move_anchor_args.source_segments, "candidates/force_contact")
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

    def test_legacy_accept_reject_command_prints_warning(self) -> None:
        args = argparse.Namespace(
            source="candidates/force_contact",
            layer_name="curated",
            motion_id="motion_a",
            segment_id=None,
            index=[0],
            status="accepted",
        )
        with (
            mock.patch.object(cli, "_load_source_segments", return_value=[_segment()]),
            mock.patch.object(cli, "write_status_layer", return_value=Path("/tmp/accepted/curated")),
            mock.patch("sys.stdout") as stdout_mock,
        ):
            cli._cmd_curate(args)

        output = "".join(call.args[0] for call in stdout_mock.write.call_args_list if call.args)
        self.assertIn("legacy layer workflow", output)
        self.assertIn("mark-segment-status", output)

    def test_legacy_workbench_accept_prints_warning(self) -> None:
        args = argparse.Namespace(
            source="candidates/force_contact",
            action="accept",
            motion_id="motion_a",
            segment_id=None,
            index=0,
            current_frame=-1,
            start_frame=None,
            end_frame=None,
            frame=None,
            output_source="accepted/workbench_tmp",
            layer_name="workbench_tmp",
            dry_run=True,
        )
        with (
            mock.patch.object(cli, "load_workbench_segments", return_value=[_segment()]),
            mock.patch("sys.stdout") as stdout_mock,
        ):
            cli._cmd_workbench_action(args)

        output = "".join(call.args[0] for call in stdout_mock.write.call_args_list if call.args)
        self.assertIn("legacy layer workflow", output)
        self.assertIn("mark-segment-status", output)

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
