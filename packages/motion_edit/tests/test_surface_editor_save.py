from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import numpy as np

from motion_edit.contact import (
    ContactEditPlan,
    ContactSurfaceRecord,
    contact_graph_from_masks,
    read_contact_edit_plan,
    write_contact_edit_plan,
    write_contact_layer,
    write_contact_surfaces,
)
from motion_edit.web import server
from motion_edit.web.server import EditorState
from motion_edit.workbench.surface_editor_session import (
    move_surface_editor_handle,
    move_surface_editor_anchor,
    prepare_surface_editor_session,
    read_pending_surface_edits,
    read_surface_editor_graph,
    restore_surface_editor_handle,
    save_surface_editor_session,
    write_surface_editor_graph,
)
from motion_edit.workbench.edit_handles import build_contact_episode_handles


class SurfaceEditorSaveTests(unittest.TestCase):
    def _prepare_session(self, root: Path):
        motion = root / "motion_a.npz"
        motion.write_bytes(b"original")
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True], [True], [False]]),
            body_pos_w=np.zeros((3, 1, 3), dtype=np.float32),
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
        anchor = graph.anchors[0]
        bound_anchor = type(anchor)(
            **{
                **anchor.__dict__,
                "surface_id": surface.surface_id,
                "surface_normal": surface.normal,
                "surface_origin": surface.origin,
                "surface_tangent_u": surface.tangent_u,
                "surface_tangent_v": surface.tangent_v,
                "surface_bounds": surface.bounds,
                "surface_coordinates": {"u": 0.0, "v": 0.0},
            }
        )
        graph = replace(graph, anchors=[bound_anchor])
        layers_root = root / "layers"
        write_contact_layer(layers_root / "contact" / "bound", graph)
        surface_catalog = root / "surfaces.jsonl"
        write_contact_surfaces(surface_catalog, [surface])
        plan_path = root / "surface_plan.json"
        session = prepare_surface_editor_session(
            motion_path=str(motion),
            motion_id="motion_a",
            contact_layer="contact/bound",
            surface_catalog=str(surface_catalog),
            session_name="session_a",
            edit_plan_path=str(plan_path),
            output_contact_layer="contact/edited",
            layers_root=layers_root,
            workbench_root=root / "workbench",
        )
        return session, bound_anchor.anchor_id, plan_path, layers_root

    def test_save_replaces_stale_plan_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session, anchor_id, plan_path, layers_root = self._prepare_session(root)
            _, edit = move_surface_editor_anchor(session, anchor_id=anchor_id, tangent_delta=[0.1, 0.0])
            stale = ContactEditPlan(
                plan_id="stale",
                source_motion_path=session.motion_path,
                source_motion_id=session.motion_id,
                source_contact_layer=session.contact_layer,
                edits=[edit.to_dict(), edit.to_dict()],
                status="validated",
            )
            write_contact_edit_plan(plan_path, stale)

            save_surface_editor_session(session, layers_root=layers_root)
            first = read_contact_edit_plan(plan_path)
            save_surface_editor_session(session, layers_root=layers_root)
            second = read_contact_edit_plan(plan_path)

        self.assertEqual(first.status, "draft")
        self.assertEqual(first.plan_id, "surface_plan")
        self.assertEqual(len(first.edits), 1)
        self.assertEqual(first, second)
        self.assertEqual(first.edits[0]["source"], "motion_edit_web")
        self.assertEqual(first.edits[0]["metadata"]["binding_granularity"], "anchor_point")

    def test_preparing_session_resets_graph_and_pending_edits_together(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session, anchor_id, _, layers_root = self._prepare_session(root)
            move_surface_editor_anchor(session, anchor_id=anchor_id, tangent_delta=[0.1, 0.0])
            self.assertEqual(len(read_pending_surface_edits(session)), 1)

            reopened = prepare_surface_editor_session(
                motion_path=session.motion_path,
                motion_id=session.motion_id,
                contact_layer=session.contact_layer,
                surface_catalog=session.surface_catalog,
                session_name=session.session_name,
                edit_plan_path=session.edit_plan_path,
                output_contact_layer=session.output_contact_layer,
                layers_root=layers_root,
                workbench_root=root / "workbench",
            )

            self.assertEqual(read_pending_surface_edits(reopened), [])
            restored = read_surface_editor_graph(reopened).anchors[0]
            self.assertAlmostEqual(restored.world_position[0], 0.0)

    def test_moving_one_foot_handle_moves_every_member_anchor_as_one_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session, _, _, _ = self._prepare_session(root)
            graph = read_surface_editor_graph(session)
            template = graph.anchors[0]
            members = [
                replace(template, anchor_id="heel", body="left_heel", start_frame=0, end_frame=1),
                replace(template, anchor_id="toe", body="left_toe", start_frame=1, end_frame=2),
            ]
            write_surface_editor_graph(session, replace(graph, anchors=members, patches=[]))
            handle = build_contact_episode_handles(members)[0]

            moved_graph, edits = move_surface_editor_handle(
                session,
                handle_id=handle.handle_id,
                tangent_delta=[0.1, 0.0],
            )

            self.assertEqual(len(edits), 2)
            self.assertEqual({edit.metadata["editor_handle_id"] for edit in edits}, {handle.handle_id})
            self.assertEqual(len(read_pending_surface_edits(session)), 2)
            for anchor in moved_graph.anchors:
                self.assertAlmostEqual(anchor.world_position[0], 0.1)
                self.assertEqual(anchor.metadata["editor_handle_id"], handle.handle_id)

    def test_restoring_handle_recovers_exact_episode_snapshot_and_pending_edits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session, _, _, _ = self._prepare_session(root)
            graph = read_surface_editor_graph(session)
            template = graph.anchors[0]
            members = [
                replace(template, anchor_id="heel", body="left_heel", start_frame=0, end_frame=1),
                replace(template, anchor_id="toe", body="left_toe", start_frame=1, end_frame=2),
            ]
            initial_graph = replace(graph, anchors=members, patches=[])
            write_surface_editor_graph(session, initial_graph)
            handle = build_contact_episode_handles(members)[0]
            move_surface_editor_handle(session, handle_id=handle.handle_id, tangent_delta=[0.1, 0.0])

            restored = restore_surface_editor_handle(
                session,
                handle_id=handle.handle_id,
                initial_graph=initial_graph,
            )

            self.assertEqual(read_pending_surface_edits(session), [])
            self.assertEqual([anchor.world_position for anchor in restored.anchors], [[0.0, 0.0, 0.0]] * 2)
            self.assertTrue(all("editor_handle_id" not in anchor.metadata for anchor in restored.anchors))

    def test_save_with_no_pending_edits_replaces_stale_plan_with_empty_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session, _, plan_path, layers_root = self._prepare_session(root)
            write_contact_edit_plan(
                plan_path,
                ContactEditPlan(
                    plan_id="stale",
                    source_motion_path=session.motion_path,
                    source_motion_id=session.motion_id,
                    source_contact_layer=session.contact_layer,
                    edits=[],
                    status="validated",
                ),
            )

            save_surface_editor_session(session, layers_root=layers_root)
            plan = read_contact_edit_plan(plan_path)

        self.assertEqual(plan.status, "draft")
        self.assertEqual(plan.edits, [])
        self.assertEqual(plan.output_contact_layer, "contact/edited")

    def test_validate_rejects_empty_plan_without_deleting_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session, _, plan_path, layers_root = self._prepare_session(root)
            state = EditorState(session=session)

            with (
                mock.patch.object(server, "LAYERS_ROOT", layers_root),
                mock.patch.object(Path, "unlink", side_effect=AssertionError("unlink must not be called")),
                self.assertRaisesRegex(ValueError, "has no edits"),
            ):
                server._save_session(state, validate=True)

            plan = read_contact_edit_plan(plan_path)

        self.assertEqual(plan.status, "draft")
        self.assertEqual(plan.edits, [])

    def test_save_then_validate_remains_single_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session, anchor_id, plan_path, layers_root = self._prepare_session(root)
            move_surface_editor_anchor(session, anchor_id=anchor_id, tangent_delta=[0.1, 0.0])
            state = EditorState(session=session)

            with mock.patch.object(server, "LAYERS_ROOT", layers_root):
                first = server._save_session(state, validate=True)
                second = server._save_session(state, validate=True)
            plan = read_contact_edit_plan(plan_path)

        self.assertEqual(first["plan"]["status"], "validated")
        self.assertEqual(second["plan"]["edit_count"], 1)
        self.assertEqual(plan.status, "validated")
        self.assertEqual(len(plan.edits), 1)


if __name__ == "__main__":
    unittest.main()
