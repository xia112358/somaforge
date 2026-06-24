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
    ContactAnchorRecord,
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
from motion_edit.viewer.contact_timeline import _timeline_html, contact_timeline_state
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
    _add_loaded_editor_sidebar,
    _anchor_color,
    _anchor_patch_mesh,
    _layer_name_from_path,
    _anchor_positions_differ,
    _contact_editor_config_from_motion_asset,
    _generate_fullbody_lte_from_session,
    _recent_entry_from_generated_session,
    _render_overlay,
    _save_and_validate_plan,
    _validate_session_plan,
    _selected_tangent_arrows,
    _directory_contains_loadable_file,
    _filtered_picker_entries,
    _setup_load_dialog_config,
    _setup_save_dialog_config,
    _setup_load_suffixes,
    append_move_request,
    apply_direct_anchor_move,
    ContactEditorShellController,
    load_editor_state,
    load_surface_overlay,
    save_editor_state,
    SurfaceEditorController,
    surface_quad_corners,
)
from motion_edit.storage.schema import MotionAssetRecord
from motion_edit.storage.io import write_motion_asset
from motion_edit.workbench.recent import RecentMotionEntry, read_recent_motions, recent_entry_labels, upsert_recent_motion
from motion_edit.workbench.contact_editor_setup import ContactEditorConfig, prepare_contact_editor_session as prepare_contact_editor_workbench_session
from motion_edit.workbench.surface_editor_session import read_pending_surface_edits


class _FakeSceneHandle:
    def __init__(self, name: str, position=None) -> None:
        self.name = name
        self.position = position
        self.click_cb = None
        self.drag_cb = None
        self.removed = False

    def on_click(self, func):
        self.click_cb = func
        return func

    def on_drag(self, func):
        self.drag_cb = func
        return func

    def remove(self) -> None:
        self.removed = True


class _FakePlayback:
    def __init__(self, n_frames: int = 8, frame: int = 0) -> None:
        self.n_frames = n_frames
        self._frame = frame
        self.playing = {"value": False}

    def frame(self) -> int:
        return self._frame

    def set_frame(self, frame: int) -> None:
        self._frame = int(frame)


class _FakeScene:
    def __init__(self) -> None:
        self.handles = {}

    def add_frame(self, name, **kwargs):
        handle = _FakeSceneHandle(name, position=kwargs.get("position"))
        self.handles[name] = handle
        return handle

    def add_line_segments(self, name, **_kwargs):
        handle = _FakeSceneHandle(name)
        self.handles[name] = handle
        return handle

    def add_point_cloud(self, name, **_kwargs):
        handle = _FakeSceneHandle(name)
        self.handles[name] = handle
        return handle

    def add_mesh_simple(self, name, **_kwargs):
        handle = _FakeSceneHandle(name)
        self.handles[name] = handle
        return handle

    def add_arrows(self, name, **_kwargs):
        handle = _FakeSceneHandle(name)
        self.handles[name] = handle
        return handle


class _FakeServer:
    def __init__(self) -> None:
        self.scene = _FakeScene()
        self.gui = _FakeGui()


class _FakeGuiHandle:
    def __init__(self, label: str, initial_value=None) -> None:
        self.label = label
        self.value = initial_value
        self.disabled = False
        self.click_cb = None

    def on_click(self, func):
        self.click_cb = func
        return func

    def on_update(self, func):
        return func


class _FakeFolder:
    def __init__(self, gui: "_FakeGui", name: str) -> None:
        self.gui = gui
        self.name = name

    def __enter__(self):
        self.gui.folders.append(self.name)
        return self

    def __exit__(self, *_args):
        return False


class _FakeGui:
    def __init__(self) -> None:
        self.folders: list[str] = []
        self.buttons: list[str] = []
        self.texts: list[str] = []

    def add_folder(self, name: str):
        return _FakeFolder(self, name)

    def add_button(self, label: str):
        self.buttons.append(label)
        return _FakeGuiHandle(label)

    def add_text(self, label: str, initial_value="", multiline: bool = False):
        _ = multiline
        self.texts.append(label)
        return _FakeGuiHandle(label, initial_value)

    def add_checkbox(self, label: str, initial_value=False):
        return _FakeGuiHandle(label, initial_value)


class _FakeDragEvent:
    def __init__(self, *, target, phase: str, end_position) -> None:
        self.target = target
        self.phase = phase
        self.end_position = end_position


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
                            "step_size": 0.02,
                            "default_mode": "reject",
                            "show_only": "all",
                            "select_anchor": None,
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
        self.assertEqual(launch_kwargs["surface_editor_step_size"], 0.02)
        self.assertEqual(launch_kwargs["surface_editor_default_mode"], "reject")
        self.assertEqual(launch_kwargs["surface_editor_show_only"], "all")
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
                            "step_size": 0.02,
                            "default_mode": "reject",
                            "show_only": "all",
                            "select_anchor": None,
                            "external_viewer": False,
                        },
                    )()
                )
                saved = read_contact_graph(root / "layers" / "contact" / "edited", "motion_a")

        self.assertEqual(len(saved.anchors), 1)

    def test_contact_editor_prepares_bound_editor_ready_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"original")
            anchors = [
                ContactAnchorRecord(
                    motion_id="motion_a",
                    anchor_id="top",
                    body="left_foot",
                    start_frame=0,
                    end_frame=10,
                    world_position=[0.0, 0.0, 0.0],
                    metadata={"raw_contact_position_refinement": {"binding_candidate_class": "top"}},
                ),
                ContactAnchorRecord(
                    motion_id="motion_a",
                    anchor_id="raw",
                    body="left_foot",
                    start_frame=11,
                    end_frame=12,
                    world_position=[0.0, 0.0, 0.0],
                    metadata={"raw_contact_position_refinement": {"binding_candidate_class": "raw_missing"}},
                ),
                ContactAnchorRecord(
                    motion_id="motion_a",
                    anchor_id="edge",
                    body="left_foot",
                    start_frame=13,
                    end_frame=14,
                    world_position=[0.0, 0.0, 0.0],
                    metadata={"raw_contact_position_refinement": {"binding_candidate_class": "edge_candidate"}},
                ),
                ContactAnchorRecord(
                    motion_id="motion_a",
                    anchor_id="outside",
                    body="left_foot",
                    start_frame=15,
                    end_frame=16,
                    world_position=[0.0, 0.0, 0.0],
                    metadata={"raw_contact_position_refinement": {"binding_candidate_class": "outside_known_surfaces"}},
                ),
            ]
            write_contact_layer(root / "layers" / "contact" / "source", type(contact_graph_from_masks(motion_id="motion_a", contact_mask=None))(motion_id="motion_a", anchors=anchors))
            surface = ContactSurfaceRecord(
                motion_id="motion_a",
                surface_id="terrain_ground_z0",
                object_id=None,
                surface_type="plane",
                origin=[0.0, 0.0, 0.0],
                normal=[0.0, 0.0, 1.0],
                tangent_u=[1.0, 0.0, 0.0],
                tangent_v=[0.0, 1.0, 0.0],
                bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
            )
            surface_catalog = root / "surfaces.jsonl"
            write_contact_surfaces(surface_catalog, [surface])
            process = mock.Mock(pid=1234)
            process.wait.return_value = None
            with (
                mock.patch.object(cli, "LAYERS_ROOT", root / "layers"),
                mock.patch.object(cli, "WORKBENCH_ROOT", root / "workbench"),
                mock.patch.object(cli, "launch_viewer", return_value=process) as launch_mock,
            ):
                cli._cmd_contact_editor(
                    type(
                        "Args",
                        (),
                        {
                            "motion": str(motion),
                            "motion_id": "motion_a",
                            "source_contact_layer": "contact/source",
                            "surface_catalog": str(surface_catalog),
                            "terrain_urdf": None,
                            "include_side_surfaces": False,
                            "no_ground": False,
                            "ground_z": 0.0,
                            "ground_half_extent": 10.0,
                            "output_prefix": "contact/editor",
                            "session_name": "contact_editor",
                            "edit_plan": None,
                            "output_contact_layer": None,
                            "repo_root": None,
                            "conda_env": "hsretargeting",
                            "timeline_port": 8094,
                            "fps": 50,
                            "with_terrain": False,
                            "save_on_exit": False,
                            "edit_mode": "direct",
                            "step_size": 0.02,
                            "default_mode": "reject",
                            "show_only": "all",
                            "select_anchor": None,
                            "external_viewer": False,
                            "merge_max_gap": 3,
                            "merge_max_distance": 0.06,
                            "max_surface_distance": 0.08,
                            "bind_mode": "reject",
                        },
                    )()
                )

        launch_mock.assert_called_once()
        self.assertEqual(launch_mock.call_args.kwargs["surface_binding_overlay"], "__setup__")
        defaults = launch_mock.call_args.kwargs["contact_editor_defaults"]
        self.assertEqual(defaults["motion"], str(motion))
        self.assertEqual(defaults["motion_id"], "motion_a")
        self.assertEqual(defaults["source_contact_layer"], "contact/source")
        self.assertEqual(defaults["surface_catalog"], str(surface_catalog))
        self.assertEqual(launch_mock.call_args.kwargs["surface_editor_edit_mode"], "direct")

    def test_contact_editor_refuses_unbound_editor_ready_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            motion.write_bytes(b"original")
            anchor = ContactAnchorRecord(
                motion_id="motion_a",
                anchor_id="top",
                body="left_foot",
                start_frame=0,
                end_frame=10,
                world_position=[10.0, 0.0, 0.0],
                metadata={"raw_contact_position_refinement": {"binding_candidate_class": "top"}},
            )
            write_contact_layer(root / "layers" / "contact" / "source", type(contact_graph_from_masks(motion_id="motion_a", contact_mask=None))(motion_id="motion_a", anchors=[anchor]))
            surface = ContactSurfaceRecord(
                motion_id="motion_a",
                surface_id="terrain_ground_z0",
                object_id=None,
                surface_type="plane",
                origin=[0.0, 0.0, 0.0],
                normal=[0.0, 0.0, 1.0],
                tangent_u=[1.0, 0.0, 0.0],
                tangent_v=[0.0, 1.0, 0.0],
                bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
            )
            surface_catalog = root / "surfaces.jsonl"
            write_contact_surfaces(surface_catalog, [surface])
            with self.assertRaisesRegex(ValueError, "not fully bound"):
                prepare_contact_editor_workbench_session(
                    ContactEditorConfig(
                        motion=str(motion),
                        motion_id="motion_a",
                        source_contact_layer="contact/source",
                        surface_catalog=str(surface_catalog),
                        session_name="contact_editor",
                        output_prefix="contact/editor",
                        max_surface_distance=0.08,
                    ),
                    layers_root=root / "layers",
                    workbench_root=root / "workbench",
                )

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

    def test_surface_overlay_filters_anchors_by_current_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray(
                    [
                        [True, False],
                        [True, False],
                        [False, False],
                        [False, True],
                        [False, True],
                    ]
                ),
                body_pos_w=np.zeros((5, 2, 3), dtype=np.float32),
                body_names=["LF", "RH"],
            )
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
                    for anchor in graph.anchors
                ],
                patches=graph.patches,
                transitions=graph.transitions,
            )
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="surface_current_frame",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            controller = SurfaceEditorController.create(_FakeServer(), state)
            controller.current_frame_getter = lambda: 3
            matches = controller.filter_anchors(current_only=True)

        self.assertEqual(len(matches), 1)
        self.assertIn("RH", matches[0]["anchor_id"])

    def test_contact_timeline_state_exports_anchor_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray(
                    [
                        [True, False],
                        [True, False],
                        [False, True],
                        [False, True],
                    ]
                ),
                body_pos_w=np.zeros((4, 2, 3), dtype=np.float32),
                body_names=["LF", "RH"],
            )
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
                    for anchor in graph.anchors
                ],
                patches=graph.patches,
                transitions=graph.transitions,
            )
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="timeline_state",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            controller = SurfaceEditorController.create(_FakeServer(), state)
            controller.select_anchor(graph.anchors[0].anchor_id)
            controller.recent_motion_items = lambda: [  # type: ignore[method-assign]
                {"label": "motion_a", "motion_path": str(root / "motion_a.npz"), "motion_id": "motion_a"}
            ]
            payload = contact_timeline_state(
                controller=controller,
                playback=_FakePlayback(n_frames=4, frame=2),
                motion_name="motion_a.npz",
                fps=50,
            )

        self.assertEqual(payload["motion_name"], "motion_a.npz")
        self.assertEqual(payload["current_frame"], 2)
        self.assertEqual(payload["bodies"], ["LF", "RH"])
        self.assertEqual(len(payload["anchors"]), 2)
        self.assertEqual(payload["anchors"][0]["status"], "selected")
        self.assertEqual(payload["recent_motions"][0]["label"], "motion_a")

    def test_contact_timeline_html_embeds_viser_iframe_and_anchor_api(self) -> None:
        html = _timeline_html(viser_url="http://localhost:8084")

        self.assertIn("<iframe id=\"viewer\"", html)
        self.assertIn("http://localhost:8084", html)
        self.assertIn("/api/select_anchor", html)
        self.assertIn("/api/open_recent", html)
        self.assertIn("recentSelect.onchange", html)
        self.assertNotIn("openRecent", html)
        self.assertIn("openLatest", html)
        self.assertIn("anchorBlock", html)
        self.assertIn("#bottom", html)

    def test_recent_motions_upsert_prunes_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "recent.json"
            motion_a = root / "a.npz"
            motion_b = root / "b.npz"
            motion_a.write_bytes(b"a")
            motion_b.write_bytes(b"b")

            upsert_recent_motion(RecentMotionEntry(label="a", motion_path=str(motion_a), motion_id="a"), cache)
            upsert_recent_motion(RecentMotionEntry(label="b", motion_path=str(motion_b), motion_id="b"), cache)
            upsert_recent_motion(RecentMotionEntry(label="a2", motion_path=str(motion_a), motion_id="a"), cache)
            motion_b.unlink()
            entries = read_recent_motions(cache)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].label, "a2")
        self.assertEqual(recent_entry_labels(entries), ["a2"])

    def test_loaded_surface_editor_sidebar_restores_file_and_session_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.zeros((3, 1, 3), dtype=np.float32),
                body_names=["LF"],
            )
            graph = type(graph)(
                motion_id=graph.motion_id,
                events=graph.events,
                anchors=[
                    type(graph.anchors[0])(
                        **{
                            **graph.anchors[0].__dict__,
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
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="loaded_sidebar",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            server = _FakeServer()
            state = load_editor_state(session.session_dir / "session.json")
            controller = SurfaceEditorController.create(server, state)
            args = argparse.Namespace(
                qpos_npz=str(root / "motion_a.npz"),
                surface_editor_session=str(session.session_dir / "session.json"),
                timeline_port=8094,
                edit_mode="direct",
                default_mode="reject",
                show_only="all",
                fps=50,
                robot_urdf=None,
            )

            _add_loaded_editor_sidebar(server, controller=controller, args=args, playback=_FakePlayback())

        self.assertIn("Motion", server.gui.folders)
        self.assertIn("Contact Anchor", server.gui.folders)
        self.assertIn("Augmentation", server.gui.folders)
        self.assertNotIn("Load Motion Bundle...", server.gui.buttons)
        self.assertIn("Validate plan", server.gui.buttons)
        self.assertIn("Dry run fullbody LTE", server.gui.buttons)
        self.assertIn("Generate fullbody LTE", server.gui.buttons)
        self.assertIn("Export debug ContactLayer", server.gui.buttons)
        self.assertIn("Reset session", server.gui.buttons)
        self.assertNotIn("Undo", server.gui.buttons)
        self.assertNotIn("Redo", server.gui.buttons)
        self.assertNotIn("Select previous", server.gui.buttons)
        self.assertNotIn("Select next", server.gui.buttons)
        self.assertIn("info", server.gui.texts)

    def test_validate_session_plan_marks_draft_plan_validated_without_contact_layer_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.zeros((3, 1, 3), dtype=np.float32),
                body_names=["LF"],
            )
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
            plan_path = root / "plan.json"
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="validate_save",
                edit_plan_path=str(plan_path),
                output_contact_layer="contact/edited",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            move_surface_editor_anchor(session, anchor_id=anchor.anchor_id, tangent_delta=[0.1, 0.0], mode="reject")

            plan_path, warnings = _validate_session_plan(session, layers_root=root / "layers")
            plan_path_2, warnings_2 = _validate_session_plan(session, layers_root=root / "layers")
            plan = read_contact_edit_plan(plan_path)

        self.assertEqual(plan_path_2, plan_path)
        self.assertEqual(warnings, [])
        self.assertEqual(warnings_2, [])
        self.assertEqual(plan.status, "validated")
        self.assertEqual(len(plan.edits), 1)
        self.assertFalse((root / "layers" / "contact" / "edited").exists())

    def test_validate_session_plan_coalesces_repeated_anchor_moves_to_final_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.zeros((3, 1, 3), dtype=np.float32),
                body_names=["LF"],
            )
            anchor = graph.anchors[0]
            bound_anchor = type(anchor)(
                **{
                    **anchor.__dict__,
                    "world_position": [0.0, 0.0, 0.0],
                    "surface_id": "top",
                    "surface_normal": [0.0, 0.0, 1.0],
                    "surface_origin": [0.0, 0.0, 0.0],
                    "surface_tangent_u": [1.0, 0.0, 0.0],
                    "surface_tangent_v": [0.0, 1.0, 0.0],
                    "surface_bounds": {"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
                    "surface_coordinates": {"u": 0.0, "v": 0.0},
                }
            )
            graph = type(graph)(motion_id=graph.motion_id, events=graph.events, anchors=[bound_anchor], patches=graph.patches, transitions=graph.transitions)
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            plan_path = root / "plan.json"
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="validate_coalesce",
                edit_plan_path=str(plan_path),
                output_contact_layer=None,
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            move_surface_editor_anchor(session, anchor_id=anchor.anchor_id, tangent_delta=[0.1, 0.0], mode="reject")
            move_surface_editor_anchor(session, anchor_id=anchor.anchor_id, tangent_delta=[0.2, 0.3], mode="reject")

            plan_path, warnings = _validate_session_plan(session, layers_root=root / "layers")
            plan = read_contact_edit_plan(plan_path)

        self.assertEqual(warnings, [])
        self.assertEqual(len(plan.edits), 1)
        edit = plan.edits[0]
        np.testing.assert_allclose(edit["old_world_position"], [0.0, 0.0, 0.0])
        np.testing.assert_allclose(edit["new_world_position"], [0.3, 0.3, 0.0])
        np.testing.assert_allclose(edit["delta_world"], [0.3, 0.3, 0.0])
        np.testing.assert_allclose(edit["tangent_delta"], [0.3, 0.3])
        self.assertEqual(edit["metadata"]["coalesced_pending_edits"], 2)

    def test_contact_editor_shell_syncs_state_after_recent_reload(self) -> None:
        class _Current:
            def __init__(self) -> None:
                self.state = type("State", (), {"last_error": None, "last_message": "old"})()
                self.selected_anchor_id = "old"

            def open_recent_motion(self, index: int) -> None:
                self.state = type("State", (), {"last_error": None, "last_message": f"new_{index}"})()
                self.selected_anchor_id = "new"

            def graph(self) -> object:
                return object()

            def pending_edits(self) -> list:
                return []

            def recent_motion_items(self) -> list:
                return []

        current = _Current()
        shell = ContactEditorShellController(current=current)
        shell.set_current(current)
        shell.open_recent_motion(3)

        self.assertEqual(shell.state.last_message, "new_3")
        self.assertEqual(shell.selected_anchor_id, "new")

    def test_contact_editor_shell_can_load_recent_before_controller_exists(self) -> None:
        entry = RecentMotionEntry(label="motion", motion_path="/tmp/motion.npz", motion_id="motion", contact_layer="contact/layer")
        loaded: list[RecentMotionEntry] = []
        shell = ContactEditorShellController()
        shell.load_recent_callback = loaded.append

        with mock.patch("motion_edit.viewer.surface_overlay_player.read_recent_motions", return_value=[entry]):
            shell.open_recent_motion(0)

        self.assertEqual(loaded, [entry])
        self.assertIsNone(shell.state.last_error)

    def test_generated_recent_entry_preserves_source_motion_id_for_contact_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = prepare_surface_editor_session(
                motion_path=str(root / "source.npz"),
                motion_id="source_motion",
                contact_layer="contact/source",
                surface_catalog=None,
                session_name="generated_recent",
                edit_plan_path=str(root / "plan.json"),
                output_contact_layer="contact/debug",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            entry = _recent_entry_from_generated_session(
                session,
                output_motion=str(root / "generated.npz"),
                output_contact_layer="contact/generated",
                output_segment_layer="candidates/generated",
                output_motion_version_id="generated_motion_version",
            )

        self.assertEqual(entry.label, "generated_motion_version")
        self.assertEqual(entry.motion_path, str(root / "generated.npz"))
        self.assertEqual(entry.motion_id, "source_motion")
        self.assertEqual(entry.contact_layer, "contact/generated")

    def test_debug_save_and_validate_still_exports_contact_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.zeros((3, 1, 3), dtype=np.float32),
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
            graph = type(graph)(motion_id=graph.motion_id, events=graph.events, anchors=[bound_anchor], patches=graph.patches, transitions=graph.transitions)
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            plan_path = root / "plan.json"
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="debug_validate_save",
                edit_plan_path=str(plan_path),
                output_contact_layer="contact/edited",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            move_surface_editor_anchor(session, anchor_id=anchor.anchor_id, tangent_delta=[0.1, 0.0], mode="reject")

            out, warnings = _save_and_validate_plan(session, layers_root=root / "layers")
            plan = read_contact_edit_plan(plan_path)

        self.assertEqual(out, root / "layers" / "contact" / "edited")
        self.assertEqual(warnings, [])
        self.assertEqual(plan.status, "validated")
        self.assertEqual(len(plan.edits), 1)

    def test_generate_fullbody_lte_from_session_writes_plan_then_calls_generator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True], [True], [False]]),
                body_pos_w=np.zeros((3, 1, 3), dtype=np.float32),
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
            graph = type(graph)(motion_id=graph.motion_id, events=graph.events, anchors=[bound_anchor], patches=graph.patches, transitions=graph.transitions)
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            plan_path = root / "plan.json"
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="generate_lte",
                edit_plan_path=str(plan_path),
                output_contact_layer="contact/debug",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            move_surface_editor_anchor(session, anchor_id=anchor.anchor_id, tangent_delta=[0.1, 0.0], mode="reject")
            fake_result = type("FakeResult", (), {"output_motion_path": root / "out.npz", "warnings": []})()

            with mock.patch("motion_edit.viewer.surface_overlay_player.apply_contact_edit_plan_to_motion", return_value=fake_result) as generate:
                result = _generate_fullbody_lte_from_session(
                    session,
                    output_motion=str(root / "out.npz"),
                    output_motion_version_id="motion_a_aug",
                    output_contact_layer="contact/generated",
                    output_segment_layer="candidates/generated",
                    intermediate_dir=str(root / "intermediate"),
                    dry_run=True,
                    layers_root=root / "layers",
                )
            plan = read_contact_edit_plan(plan_path)

        self.assertIs(result, fake_result)
        self.assertEqual(plan.status, "validated")
        self.assertEqual(len(plan.edits), 1)
        self.assertFalse((root / "layers" / "contact" / "debug").exists())
        kwargs = generate.call_args.kwargs
        self.assertEqual(kwargs["mode"], "lte_fullbody")
        self.assertTrue(kwargs["dry_run"])
        self.assertEqual(kwargs["output_motion_version_id"], "motion_a_aug")
        self.assertEqual(kwargs["output_contact_layer"], "contact/generated")

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
            pending = read_pending_surface_edits(session)

        self.assertEqual(pending, [])

    def test_surface_overlay_direct_move_clamps_out_of_bounds(self) -> None:
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
                session_name="surface_clamp",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            result = apply_direct_anchor_move(
                state,
                anchor_id=bound_anchor.anchor_id,
                tangent_delta=[0.3, 0.0],
                mode="clamp",
            )
            moved = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[0]
            pending = read_pending_surface_edits(session)

        np.testing.assert_allclose(moved.world_position, [0.1, 0.0, 0.0])
        self.assertEqual(len(pending), 1)
        self.assertTrue(pending[0].clamped)
        np.testing.assert_allclose(result["delta_world"], [0.1, 0.0, 0.0])

    def test_surface_editor_controller_select_filter_move_undo_redo_reset_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True, True], [True, True], [False, False]]),
                body_pos_w=np.asarray(
                    [
                        [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]],
                        [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]],
                        [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]],
                    ]
                ),
                body_names=["LF", "RF"],
            )
            first, second = graph.anchors
            unbound_first = first
            bound_second = type(second)(
                **{
                    **second.__dict__,
                    "surface_id": "top",
                    "surface_normal": [0.0, 0.0, 1.0],
                    "surface_origin": [0.0, 0.0, 0.0],
                    "surface_tangent_u": [1.0, 0.0, 0.0],
                    "surface_tangent_v": [0.0, 1.0, 0.0],
                    "surface_bounds": {"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
                    "surface_coordinates": {"u": 0.5, "v": 0.0},
                    "metadata": {
                        **second.metadata,
                        "surface_bindings": [
                            {
                                "original_world_position": [0.5, 0.0, 0.0],
                                "projected_world_position": [0.5, 0.0, 0.0],
                                "bound_world_position": [0.5, 0.0, 0.0],
                                "signed_surface_distance": 0.0,
                                "raw_surface_coordinates": {"u": 0.5, "v": 0.0},
                                "surface_coordinates": {"u": 0.5, "v": 0.0},
                                "clamped": False,
                            }
                        ],
                    },
                }
            )
            graph = type(graph)(motion_id="motion_a", events=graph.events, anchors=[unbound_first, bound_second], patches=graph.patches, transitions=graph.transitions)
            write_contact_layer(root / "layers" / "contact" / "bound", graph)
            plan_path = root / "plan.json"
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion_a.npz"),
                motion_id="motion_a",
                contact_layer="contact/bound",
                surface_catalog=None,
                session_name="surface_controller",
                edit_plan_path=str(plan_path),
                output_contact_layer="contact/edited",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            controller = SurfaceEditorController.create(None, state)
            initial_selected = controller.selected_anchor_id
            bound_matches = controller.filter_anchors(status="bound")
            unbound_matches = controller.filter_anchors(status="unbound")
            info = controller.selected_info_text()
            move_result = controller.move_selected(tangent_delta=[0.1, 0.0], mode="reject")
            moved = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[1]
            pending_after_move = read_pending_surface_edits(session)
            undo_ok = controller.undo()
            undone = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[1]
            pending_after_undo = read_pending_surface_edits(session)
            redo_ok = controller.redo()
            redone = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[1]
            controller.reset()
            reset = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[1]
            pending_after_reset = read_pending_surface_edits(session)
            controller.move_selected(tangent_delta=[0.2, 0.0], mode="reject")
            out = controller.save(layers_root=root / "layers")
            saved = read_contact_graph(root / "layers" / "contact" / "edited", "motion_a").anchors[1]
            plan = read_contact_edit_plan(plan_path)

        self.assertEqual(initial_selected, bound_second.anchor_id)
        self.assertEqual(len(bound_matches), 1)
        self.assertEqual(len(unbound_matches), 1)
        self.assertIn("surface_id: top", info)
        np.testing.assert_allclose(move_result["delta_world"], [0.1, 0.0, 0.0])
        np.testing.assert_allclose(moved.world_position, [0.6, 0.0, 0.0])
        self.assertEqual(len(pending_after_move), 1)
        self.assertTrue(undo_ok)
        np.testing.assert_allclose(undone.world_position, [0.5, 0.0, 0.0])
        self.assertEqual(len(pending_after_undo), 0)
        self.assertTrue(redo_ok)
        np.testing.assert_allclose(redone.world_position, [0.6, 0.0, 0.0])
        np.testing.assert_allclose(reset.world_position, [0.5, 0.0, 0.0])
        self.assertEqual(len(pending_after_reset), 0)
        self.assertEqual(out, root / "layers" / "contact" / "edited")
        np.testing.assert_allclose(saved.world_position, [0.7, 0.0, 0.0])
        self.assertEqual(plan.status, "draft")
        self.assertEqual(len(plan.edits), 1)

    def test_surface_editor_drag_projects_to_same_surface(self) -> None:
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
                    "object_id": "box",
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
                session_name="surface_drag",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            controller = SurfaceEditorController.create(None, state)
            normal_only = controller.drag_selected_to_world([0.0, 0.0, 0.25], mode="reject")
            pending_after_noop = read_pending_surface_edits(session)
            result = controller.drag_selected_to_world([0.2, 0.1, 0.4], mode="reject")
            moved = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[0]
            pending = read_pending_surface_edits(session)

        self.assertTrue(normal_only["no_op"])
        self.assertEqual(pending_after_noop, [])
        np.testing.assert_allclose(result["tangent_delta"], [0.2, 0.1])
        np.testing.assert_allclose(moved.world_position, [0.2, 0.1, 0.0])
        self.assertEqual(moved.surface_id, "top")
        self.assertEqual(moved.object_id, "box")
        self.assertEqual(len(pending), 1)

    def test_surface_editor_drag_reject_and_clamp_bounds(self) -> None:
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
                session_name="surface_drag_bounds",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            controller = SurfaceEditorController.create(None, state)
            with self.assertRaises(ValueError):
                controller.drag_selected_to_world([0.3, 0.0, 0.2], mode="reject")
            rejected = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[0]
            pending_after_reject = read_pending_surface_edits(session)
            result = controller.drag_selected_to_world([0.3, 0.0, 0.2], mode="clamp")
            clamped = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[0]
            pending_after_clamp = read_pending_surface_edits(session)

        np.testing.assert_allclose(rejected.world_position, [0.0, 0.0, 0.0])
        self.assertEqual(pending_after_reject, [])
        np.testing.assert_allclose(clamped.world_position, [0.1, 0.0, 0.0])
        self.assertEqual(len(pending_after_clamp), 1)
        self.assertTrue(pending_after_clamp[0].clamped)
        np.testing.assert_allclose(result["delta_world"], [0.1, 0.0, 0.0])

    def test_surface_editor_render_click_and_drag_callbacks(self) -> None:
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
                session_name="surface_render_drag",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            server = _FakeServer()
            controller = SurfaceEditorController.create(server, state)
            controller.drag_mode_getter = lambda: "reject"
            overlay = load_surface_overlay(session.overlay_path)
            _render_overlay(server, overlay, selected_anchor_id=bound_anchor.anchor_id, controller=controller, edit_mode="direct")
            marker = next(handle for name, handle in server.scene.handles.items() if "/anchors/" in name)
            marker.click_cb(None)
            marker.drag_cb(_FakeDragEvent(target=marker, phase="end", end_position=[0.2, 0.0, 0.4]))
            moved = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[0]
            pending = read_pending_surface_edits(session)

        self.assertEqual(controller.selected_anchor_id, bound_anchor.anchor_id)
        self.assertIn("selected_anchor_tangent_arrows", "\n".join(server.scene.handles.keys()))
        np.testing.assert_allclose(moved.world_position, [0.2, 0.0, 0.0])
        self.assertEqual(len(pending), 1)

    def test_surface_editor_drag_update_does_not_commit_or_rerender(self) -> None:
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
                session_name="surface_render_update",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            server = _FakeServer()
            controller = SurfaceEditorController.create(server, state)
            controller.drag_mode_getter = lambda: "reject"
            overlay = load_surface_overlay(session.overlay_path)
            _render_overlay(server, overlay, selected_anchor_id=bound_anchor.anchor_id, controller=controller, edit_mode="direct")
            marker = next(handle for name, handle in server.scene.handles.items() if "/anchors/" in name)
            render_generation = controller.state.render_generation
            marker.drag_cb(_FakeDragEvent(target=marker, phase="update", end_position=[0.2, 0.0, 0.4]))
            moved = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[0]
            pending = read_pending_surface_edits(session)

        self.assertEqual(controller.state.render_generation, render_generation)
        np.testing.assert_allclose(moved.world_position, [0.0, 0.0, 0.0])
        self.assertEqual(pending, [])

    def test_surface_editor_initial_ghost_click_restores_anchor(self) -> None:
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
                session_name="surface_restore",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )
            state = load_editor_state(session.session_dir / "session.json")
            server = _FakeServer()
            controller = SurfaceEditorController.create(server, state)
            controller.drag_mode_getter = lambda: "reject"
            controller.move_selected(tangent_delta=[0.2, 0.0], mode="reject")
            moved = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[0]
            self.assertTrue(_anchor_positions_differ(bound_anchor, moved))

            overlay = load_surface_overlay(session.overlay_path)
            _render_overlay(server, overlay, selected_anchor_id=bound_anchor.anchor_id, controller=controller, edit_mode="direct")
            ghost = next(handle for name, handle in server.scene.handles.items() if name.endswith("_initial_ghost"))
            ghost.click_cb(None)
            restored = read_contact_graph(session.contact_layer_snapshot, "motion_a").anchors[0]
            pending = read_pending_surface_edits(session)

        np.testing.assert_allclose(restored.world_position, [0.0, 0.0, 0.0])
        self.assertEqual(len(pending), 2)
        self.assertEqual(pending[-1].metadata["surface_editor_action"], "restore_initial_position")

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

    def test_anchor_patch_mesh_lies_on_surface_tangent_plane(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[1.0, 2.0, 0.5],
            surface_normal=[0.0, 0.0, 1.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
        )

        mesh = _anchor_patch_mesh(anchor, radius=0.1, normal_offset=0.002, segments=16)

        self.assertIsNotNone(mesh)
        vertices, faces = mesh
        self.assertEqual(vertices.shape, (17, 3))
        self.assertEqual(faces.shape, (16, 3))
        np.testing.assert_allclose(vertices[:, 2], np.full(17, 0.502))
        np.testing.assert_allclose(vertices.mean(axis=0), [1.0, 2.0, 0.502], atol=1e-6)

    def test_selected_tangent_arrows_use_viser_color_shape(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[1.0, 2.0, 0.5],
            surface_normal=[0.0, 0.0, 1.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
        )

        arrows = _selected_tangent_arrows(anchor)

        self.assertIsNotNone(arrows)
        points, colors = arrows
        self.assertEqual(points.shape, (2, 2, 3))
        self.assertEqual(colors.shape, (2, 3))

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
        self.assertIn("motion_edit.viewer.contact_editor.app", cmd)
        self.assertIn("--edit-mode", cmd)
        self.assertEqual(cmd[cmd.index("--edit-mode") + 1], "direct")

    def test_surface_overlay_anchor_color_uses_body_palette_with_status_override(self) -> None:
        left = _anchor_color({"type": "anchor_point", "body": "left_foot", "status": "bound"})
        right = _anchor_color({"type": "anchor_point", "body": "right_foot", "status": "bound"})
        suspicious = _anchor_color({"type": "anchor_point", "body": "left_foot", "status": "suspicious"})

        self.assertNotEqual(left, right)
        self.assertEqual(left, (60, 140, 255))
        self.assertEqual(right, (255, 120, 65))
        self.assertEqual(suspicious, (255, 120, 95))

    def test_setup_layer_name_from_path_uses_layers_relative_name(self) -> None:
        layer_file = Path("data/layers/contact/example/motion_a.jsonl")
        with mock.patch("motion_edit.viewer.surface_overlay_player.LAYERS_ROOT", Path("data/layers")):
            name = _layer_name_from_path(layer_file)

        self.assertEqual(name, "contact/example")

    def test_setup_picker_configs_filter_by_selected_file_type(self) -> None:
        registered_motion_config = _setup_load_dialog_config("Motion")
        motion_config = _setup_load_dialog_config("Motion NPZ")
        contact_config = _setup_load_dialog_config("Contact Layer")
        terrain_config = _setup_load_dialog_config("Terrain URDF")
        surface_config = _setup_load_dialog_config("Surface Catalog")
        output_config = _setup_save_dialog_config("Output Contact Layer")
        plan_config = _setup_save_dialog_config("Edit Plan")

        self.assertEqual(registered_motion_config["filetypes"], [("Motion asset", "*.json")])
        self.assertEqual(motion_config["filetypes"], [("Motion npz", "*.npz")])
        self.assertEqual(contact_config["filetypes"], [("Contact layer jsonl", "*.jsonl")])
        self.assertEqual(terrain_config["filetypes"], [("URDF", "*.urdf")])
        self.assertEqual(surface_config["filetypes"], [("Surface catalog jsonl", "*.jsonl")])
        self.assertEqual(output_config["filetypes"], [("Contact layer jsonl", "*.jsonl")])
        self.assertEqual(plan_config["filetypes"], [("Contact edit plan", "*.json")])

    def test_motion_asset_config_uses_derived_contact_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = MotionAssetRecord(
                motion_asset_id="climb_01_raw_contact_29",
                motion_path=str(root / "climb_01.npz"),
                source="test",
                fps=50.0,
                motion_id="climb_01_z_scale_1.0",
                terrain_urdf=str(root / "terrain.urdf"),
                raw_contact={"available": True},
                derived={"contact_layer": "contact/raw_contact_29"},
            )
            path = root / "climb_01_raw_contact_29.json"
            write_motion_asset(record, path)
            config = _contact_editor_config_from_motion_asset(path)

        self.assertEqual(config.motion, record.motion_path)
        self.assertEqual(config.motion_id, "climb_01_z_scale_1.0")
        self.assertEqual(config.source_contact_layer, "contact/raw_contact_29")
        self.assertEqual(config.session_name, "climb_01_raw_contact_29_contact_editor")

    def test_filtered_picker_hides_directories_without_loadable_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty_dir = root / "empty"
            useful_dir = root / "useful"
            nested_dir = useful_dir / "nested"
            empty_dir.mkdir()
            nested_dir.mkdir(parents=True)
            (empty_dir / "notes.txt").write_text("nope", encoding="utf-8")
            (root / "motion_a.npz").write_bytes(b"npz")
            (nested_dir / "motion_b.npz").write_bytes(b"npz")
            (root / "surface.jsonl").write_text("{}", encoding="utf-8")

            entries = _filtered_picker_entries(root, _setup_load_suffixes("Motion NPZ"))
            labels = [label for label, _path in entries]
            useful_contains_npz = _directory_contains_loadable_file(useful_dir, (".npz",))
            empty_contains_npz = _directory_contains_loadable_file(empty_dir, (".npz",))

        self.assertIn("[file] motion_a.npz", labels)
        self.assertIn("[dir] useful", labels)
        self.assertNotIn("[dir] empty", labels)
        self.assertNotIn("[file] surface.jsonl", labels)
        self.assertTrue(useful_contains_npz)
        self.assertFalse(empty_contains_npz)


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
        self.assertEqual(generate_args.mode, "lte_fullbody")
        self.assertEqual(generate_args.fullbody_solver, "ik_subprocess")
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
