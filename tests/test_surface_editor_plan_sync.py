from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.contact import contact_graph_from_masks, read_contact_edit_plan, write_contact_layer
from motion_edit.contact.plans import append_anchor_edit_to_plan
from motion_edit.contact.schema import ContactAnchorEditRecord
from motion_edit.workbench.surface_editor_session import move_surface_editor_anchor, prepare_surface_editor_session


def _bound_single_anchor_graph():
    graph = contact_graph_from_masks(
        motion_id="motion_a",
        contact_mask=np.asarray([[True], [True], [False]], dtype=bool),
        body_pos_w=np.asarray([[[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0]]], dtype=np.float32),
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
    return type(graph)(motion_id=graph.motion_id, events=graph.events, anchors=[bound_anchor], patches=graph.patches, transitions=graph.transitions)


class SurfaceEditorPlanSyncTests(unittest.TestCase):
    def test_direct_drag_writes_pending_edit_into_configured_plan_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = _bound_single_anchor_graph()
            write_contact_layer(root / "layers" / "contact" / "ready", graph)
            plan_path = root / "plan.json"
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion.npz"),
                motion_id="motion_a",
                contact_layer="contact/ready",
                surface_catalog=None,
                session_name="plan_sync",
                edit_plan_path=str(plan_path),
                output_contact_layer="contact/out",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )

            move_surface_editor_anchor(session, anchor_id=graph.anchors[0].anchor_id, tangent_delta=[0.2, 0.0], mode="reject")
            plan = read_contact_edit_plan(plan_path)

        self.assertEqual(plan.status, "draft")
        self.assertEqual(len(plan.edits), 1)
        self.assertEqual(plan.edits[0]["anchor_id"], graph.anchors[0].anchor_id)
        np.testing.assert_allclose(plan.edits[0]["delta_world"], [0.2, 0.0, 0.0])
        self.assertEqual(plan.edits[0]["metadata"]["session_name"], "plan_sync")

    def test_repeated_drag_replaces_stale_plan_edit_for_same_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = _bound_single_anchor_graph()
            write_contact_layer(root / "layers" / "contact" / "ready", graph)
            plan_path = root / "plan.json"
            stale = ContactAnchorEditRecord(
                edit_id="stale_edit",
                motion_id="motion_a",
                anchor_id=graph.anchors[0].anchor_id,
                body=graph.anchors[0].body,
                old_world_position=[0.0, 0.0, 0.0],
                new_world_position=[0.5, 0.0, 0.0],
                delta_world=[0.5, 0.0, 0.0],
                tangent_delta=[0.5, 0.0],
                affected_frames=[graph.anchors[0].start_frame, graph.anchors[0].end_frame],
                surface_id="top",
                surface_normal=[0.0, 0.0, 1.0],
                surface_coordinates_before={"u": 0.0, "v": 0.0},
                surface_coordinates_after={"u": 0.5, "v": 0.0},
                constraint_mode="reject",
            )
            append_anchor_edit_to_plan(
                plan_path,
                stale,
                plan_id="plan",
                source_motion_path=str(root / "motion.npz"),
                source_motion_id="motion_a",
                source_contact_layer="contact/ready",
            )
            session = prepare_surface_editor_session(
                motion_path=str(root / "motion.npz"),
                motion_id="motion_a",
                contact_layer="contact/ready",
                surface_catalog=None,
                session_name="plan_sync_replace",
                edit_plan_path=str(plan_path),
                output_contact_layer="contact/out",
                layers_root=root / "layers",
                workbench_root=root / "workbench",
            )

            move_surface_editor_anchor(session, anchor_id=graph.anchors[0].anchor_id, tangent_delta=[0.1, 0.0], mode="reject")
            move_surface_editor_anchor(session, anchor_id=graph.anchors[0].anchor_id, tangent_delta=[0.0, 0.3], mode="reject")
            plan = read_contact_edit_plan(plan_path)

        self.assertEqual(len(plan.edits), 1)
        self.assertNotEqual(plan.edits[0]["edit_id"], "stale_edit")
        np.testing.assert_allclose(plan.edits[0]["old_world_position"], [0.0, 0.0, 0.0])
        np.testing.assert_allclose(plan.edits[0]["new_world_position"], [0.1, 0.3, 0.0])
        np.testing.assert_allclose(plan.edits[0]["delta_world"], [0.1, 0.3, 0.0])
        np.testing.assert_allclose(plan.edits[0]["tangent_delta"], [0.1, 0.3])


if __name__ == "__main__":
    unittest.main()
