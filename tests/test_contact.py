from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.contact import (
    anchors_from_contact_mask,
    bind_segment_to_contact_graph,
    contact_graph_from_masks,
    detect_contact_events,
    make_anchor_move_edit,
    move_contact_anchor,
    move_contact_anchor_on_surface,
    move_anchor_in_graph,
    move_anchor_in_contact_layer,
    read_contact_anchors,
    read_contact_events,
    read_contact_graph,
    read_contact_patches,
    read_contact_transitions,
    segment_from_contact_transition,
    transitions_from_proto_indices,
    write_contact_jsonl,
    write_contact_layer,
)
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.schema import SegmentRecord


class ContactEventTests(unittest.TestCase):
    def test_anchor_world_position_roundtrips_jsonl(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[0.1, 0.2, 0.3],
            object_position=[0.0, 0.2, 0.3],
            object_id="terrain",
            normal=[0.0, 0.0, 1.0],
            surface_id="platform_top",
            surface_type="box_face",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[0.0, 0.0, 0.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
            surface_bounds={"u": [-1.0, 1.0], "v": [-0.5, 0.5]},
            surface_coordinates={"u": 0.1, "v": 0.2},
            surface_binding_source="manual",
            editable=True,
            position_source="manual",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "anchors.jsonl"
            write_contact_jsonl(path, [anchor])
            loaded = read_contact_anchors(path)[0]

        self.assertEqual(loaded.world_position, [0.1, 0.2, 0.3])
        self.assertEqual(loaded.object_position, [0.0, 0.2, 0.3])
        self.assertEqual(loaded.normal, [0.0, 0.0, 1.0])
        self.assertEqual(loaded.surface_id, "platform_top")
        self.assertEqual(loaded.surface_type, "box_face")
        self.assertEqual(loaded.surface_normal, [0.0, 0.0, 1.0])
        self.assertEqual(loaded.surface_bounds, {"u": [-1.0, 1.0], "v": [-0.5, 0.5]})
        self.assertEqual(loaded.surface_coordinates, {"u": 0.1, "v": 0.2})
        self.assertEqual(loaded.surface_binding_source, "manual")
        self.assertTrue(loaded.editable)
        self.assertEqual(loaded.position_source, "manual")

    def test_anchor_edit_surface_constraint_fields_validate(self) -> None:
        edit = ContactAnchorEditRecord(
            edit_id="edit_a",
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            old_world_position=[0.0, 0.0, 0.0],
            new_world_position=[0.1, 0.0, 0.0],
            requested_delta_world=[0.1, 0.0, 0.2],
            delta_world=[0.1, 0.0, 0.0],
            tangent_delta=[0.1, 0.0],
            surface_id="platform_top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_coordinates_before={"u": 0.0, "v": 0.0},
            surface_coordinates_after={"u": 0.1, "v": 0.0},
            constraint_mode="reject",
            clamped=False,
        )

        data = edit.to_dict()

        self.assertEqual(data["requested_delta_world"], [0.1, 0.0, 0.2])
        self.assertEqual(data["delta_world"], [0.1, 0.0, 0.0])
        self.assertEqual(data["tangent_delta"], [0.1, 0.0])
        self.assertEqual(data["surface_id"], "platform_top")

    def test_move_contact_anchor_records_old_new_and_delta(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="LF",
            start_frame=0,
            end_frame=10,
            world_position=[1.0, 2.0, 0.0],
            position_source="body_pos_w_mean",
        )

        moved = move_contact_anchor(anchor, delta_world=[0.1, 0.0, 0.0])
        edit = make_anchor_move_edit(anchor, new_world_position=[1.1, 2.0, 0.0], affected_frames=[0, 10], source="lte")

        self.assertEqual(moved.world_position, [1.1, 2.0, 0.0])
        self.assertEqual(moved.position_source, "manual")
        self.assertEqual(moved.metadata["contact_anchor_edits"][-1]["old_world_position"], [1.0, 2.0, 0.0])
        self.assertEqual(edit.edit_type, "move_contact_anchor")
        self.assertEqual(edit.old_world_position, [1.0, 2.0, 0.0])
        self.assertEqual(edit.new_world_position, [1.1, 2.0, 0.0])
        self.assertEqual(edit.delta_world, [0.10000000000000009, 0.0, 0.0])

    def test_move_contact_anchor_on_surface_projects_normal_delta(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.0],
            object_id="box",
            surface_id="top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[0.0, 0.0, 0.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
            surface_bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
            surface_coordinates={"u": 0.0, "v": 0.0},
        )

        moved, edit = move_contact_anchor_on_surface(anchor, requested_world_delta=[0.1, 0.0, 0.2])

        self.assertEqual(moved.world_position, [0.1, 0.0, 0.0])
        self.assertEqual(edit.requested_delta_world, [0.1, 0.0, 0.2])
        self.assertEqual(edit.delta_world, [0.1, 0.0, 0.0])
        self.assertEqual(edit.tangent_delta, [0.1, 0.0])
        self.assertEqual(edit.surface_id, "top")
        self.assertEqual(edit.constraint_mode, "reject")
        self.assertFalse(edit.clamped)

    def test_move_contact_anchor_on_surface_uses_tangent_basis(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[1.0, 2.0, 0.0],
            object_id="box",
            surface_id="top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[1.0, 2.0, 0.0],
            surface_tangent_u=[0.0, 1.0, 0.0],
            surface_tangent_v=[1.0, 0.0, 0.0],
            surface_bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
            surface_coordinates={"u": 0.0, "v": 0.0},
        )

        moved, edit = move_contact_anchor_on_surface(anchor, tangent_delta=[0.2, 0.3])

        self.assertEqual(moved.world_position, [1.3, 2.2, 0.0])
        self.assertEqual(moved.surface_coordinates, {"u": 0.2, "v": 0.3})
        self.assertEqual(edit.delta_world, [0.3, 0.2, 0.0])

    def test_move_contact_anchor_on_surface_rejects_outside_bounds(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.0],
            surface_id="top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[0.0, 0.0, 0.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
            surface_bounds={"u": [-0.1, 0.1], "v": [-0.1, 0.1]},
            surface_coordinates={"u": 0.0, "v": 0.0},
        )

        with self.assertRaises(ValueError):
            move_contact_anchor_on_surface(anchor, tangent_delta=[0.2, 0.0])

    def test_move_contact_anchor_on_surface_clamps_outside_bounds(self) -> None:
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=10,
            world_position=[0.0, 0.0, 0.0],
            object_id="box",
            surface_id="top",
            surface_normal=[0.0, 0.0, 1.0],
            surface_origin=[0.0, 0.0, 0.0],
            surface_tangent_u=[1.0, 0.0, 0.0],
            surface_tangent_v=[0.0, 1.0, 0.0],
            surface_bounds={"u": [-0.1, 0.1], "v": [-0.1, 0.1]},
            surface_coordinates={"u": 0.0, "v": 0.0},
        )

        moved, edit = move_contact_anchor_on_surface(anchor, tangent_delta=[0.2, 0.0], mode="clamp")

        self.assertEqual(moved.world_position, [0.1, 0.0, 0.0])
        self.assertEqual(moved.object_id, "box")
        self.assertEqual(moved.surface_id, "top")
        self.assertEqual(edit.delta_world, [0.1, 0.0, 0.0])
        self.assertEqual(edit.tangent_delta, [0.1, 0.0])
        self.assertEqual(edit.surface_id, "top")
        self.assertEqual(edit.constraint_mode, "clamp")
        self.assertTrue(edit.clamped)

    def test_move_anchor_in_graph_updates_anchor_patch_and_returns_edit(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [True, False], [False, False]]),
            body_pos_w=np.asarray(
                [
                    [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                    [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                    [[9.0, 9.0, 9.0], [0.0, 0.0, 0.0]],
                ]
            ),
            body_names=["left_foot", "right_foot"],
        )

        with self.assertRaises(ValueError):
            move_anchor_in_graph(graph, anchor_id=graph.anchors[0].anchor_id, delta_world=[0.1, 0.0, 0.0])

        moved_graph, edit = move_anchor_in_graph(
            graph,
            anchor_id=graph.anchors[0].anchor_id,
            delta_world=[0.1, 0.0, 0.0],
            allow_free_3d=True,
        )

        self.assertEqual(moved_graph.anchors[0].world_position, [1.1, 2.0, 0.0])
        self.assertEqual(moved_graph.patches[0].patch_center_world, [1.1, 2.0, 0.0])
        self.assertEqual(edit.edit_type, "move_contact_anchor")

    def test_move_anchor_in_contact_layer_writes_graph_and_edit_record(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [True, False], [False, False]]),
            body_pos_w=np.asarray(
                [
                    [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                    [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                    [[9.0, 9.0, 9.0], [0.0, 0.0, 0.0]],
                ]
            ),
            body_names=["left_foot", "right_foot"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contact_layer(root / "source", graph)
            moved_graph, edit = move_anchor_in_contact_layer(
                root / "source",
                root / "moved",
                motion_id="motion_a",
                anchor_id=graph.anchors[0].anchor_id,
                delta_world=[0.1, 0.0, 0.0],
                allow_free_3d=True,
            )
            loaded = read_contact_graph(root / "moved", "motion_a")
            edit_lines = (root / "moved" / "edits" / "motion_a.jsonl").read_text(encoding="utf-8").splitlines()

        self.assertEqual(loaded.anchors[0].world_position, [1.1, 2.0, 0.0])
        self.assertEqual(moved_graph.anchors[0].world_position, [1.1, 2.0, 0.0])
        self.assertEqual(edit.edit_type, "move_contact_anchor")
        self.assertEqual(len(edit_lines), 1)

    def test_detects_touchdown_liftoff_active_and_support_changes(self) -> None:
        contact = np.asarray(
            [
                [False, True],
                [True, True],
                [True, False],
                [False, False],
                [False, True],
            ]
        )
        active = np.asarray(
            [
                [False, True],
                [True, False],
                [True, False],
                [False, True],
                [False, True],
            ]
        )
        support = np.asarray(
            [
                [False, True],
                [False, True],
                [True, False],
                [True, False],
                [False, True],
            ]
        )

        events = detect_contact_events(
            motion_id="motion_a",
            contact_mask=contact,
            active_mask=active,
            support_mask=support,
            body_names=["LF", "RF"],
            source="test",
        )

        event_types = [(event.frame, event.body, event.event_type) for event in events]
        self.assertIn((1, "LF", "touchdown"), event_types)
        self.assertIn((2, "RF", "liftoff"), event_types)
        self.assertIn((1, "active", "active_change"), event_types)
        self.assertIn((2, "support", "support_switch"), event_types)

    def test_anchor_interval_grouping(self) -> None:
        contact = np.asarray(
            [
                [False, True],
                [True, True],
                [True, False],
                [False, False],
                [False, True],
            ]
        )
        support = np.asarray(
            [
                [False, True],
                [False, True],
                [True, False],
                [True, False],
                [False, True],
            ]
        )

        anchors = anchors_from_contact_mask(
            motion_id="motion_a",
            contact_mask=contact,
            support_mask=support,
            body_names=["LF", "RF"],
        )

        spans = [(anchor.body, anchor.start_frame, anchor.end_frame, anchor.role) for anchor in anchors]
        self.assertIn(("LF", 1, 3, "support"), spans)
        self.assertIn(("RF", 0, 2, "support"), spans)
        self.assertIn(("RF", 4, 5, "support"), spans)

    def test_anchor_position_estimated_from_body_pos_w_interval(self) -> None:
        contact = np.asarray([[True, False], [True, False], [False, False]])
        body_pos_w = np.asarray(
            [
                [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                [[1.2, 2.0, 0.0], [0.0, 0.0, 0.0]],
                [[9.0, 9.0, 9.0], [0.0, 0.0, 0.0]],
            ]
        )

        anchors = anchors_from_contact_mask(
            motion_id="motion_a",
            contact_mask=contact,
            body_pos_w=body_pos_w,
            body_names=["LF", "RF"],
        )

        self.assertEqual(anchors[0].world_position, [1.1, 2.0, 0.0])
        self.assertEqual(anchors[0].position_source, "body_pos_w_mean")
        self.assertEqual(anchors[0].metadata["first_world_position"], [1.0, 2.0, 0.0])
        self.assertEqual(anchors[0].metadata["last_world_position"], [1.2, 2.0, 0.0])
        self.assertAlmostEqual(anchors[0].metadata["max_drift_xy"], 0.2)

    def test_transition_converts_to_segment_with_contact_metadata(self) -> None:
        contact = np.asarray(
            [
                [False, True],
                [True, True],
                [True, False],
                [False, False],
                [False, True],
            ]
        )
        active = np.asarray(
            [
                [False, True],
                [True, False],
                [True, False],
                [False, True],
                [False, True],
            ]
        )
        support = np.asarray(
            [
                [False, True],
                [False, True],
                [True, False],
                [True, False],
                [False, True],
            ]
        )

        events, anchors, transitions = transitions_from_proto_indices(
            motion_id="motion_a",
            starts=[1],
            ends=[4],
            contact_mask=contact,
            active_mask=active,
            support_mask=support,
            body_names=["LF", "RF"],
        )
        segment = segment_from_contact_transition(
            transition=transitions[0],
            segment_id="motion_a_force_0000",
            source="force_contact",
            status="candidate",
            track="proto",
            motion_path="/tmp/motion_a.npz",
            clip_npz="/tmp/motion_a.npz",
            clip_output_dir=None,
            clip_file_name="motion_a.npz",
            atom_label="force_contact_00",
            contact_start="11",
            contact_end="00",
            active="10",
            support="01",
            events=events,
            anchors=anchors,
        )

        self.assertEqual(segment.metadata["active_body"], "LF")
        self.assertEqual(segment.metadata["support_bodies"], ["RF"])
        self.assertEqual(segment.metadata["contact_transition"]["start_frame"], 1)
        self.assertGreaterEqual(len(segment.metadata["contact_events"]), 1)
        self.assertGreaterEqual(len(segment.metadata["contact_anchors"]), 1)

    def test_contact_records_roundtrip_as_typed_jsonl(self) -> None:
        contact = np.asarray([[False, True], [True, True], [True, False]])
        events, anchors, transitions = transitions_from_proto_indices(
            motion_id="motion_a",
            starts=[0],
            ends=[3],
            contact_mask=contact,
            body_names=["LF", "RF"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_contact_jsonl(root / "events.jsonl", events)
            write_contact_jsonl(root / "anchors.jsonl", anchors)
            write_contact_jsonl(root / "patches.jsonl", contact_graph_from_masks(motion_id="motion_a", contact_mask=contact, body_names=["LF", "RF"]).patches)
            write_contact_jsonl(root / "transitions.jsonl", transitions)

            loaded_events = read_contact_events(root / "events.jsonl")
            loaded_anchors = read_contact_anchors(root / "anchors.jsonl")
            loaded_patches = read_contact_patches(root / "patches.jsonl")
            loaded_transitions = read_contact_transitions(root / "transitions.jsonl")

        self.assertEqual(loaded_events[0].event_id, events[0].event_id)
        self.assertEqual(loaded_anchors[0].anchor_id, anchors[0].anchor_id)
        self.assertEqual(loaded_patches[0].anchor_id, loaded_anchors[0].anchor_id)
        self.assertEqual(loaded_transitions[0].transition_id, transitions[0].transition_id)

    def test_contact_graph_groups_events_anchors_and_transitions(self) -> None:
        contact = np.asarray([[True, False], [False, False], [True, False]])

        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=contact,
            body_names=["LF", "RF"],
            source="test",
        )

        self.assertEqual(graph.motion_id, "motion_a")
        self.assertTrue(any(event.event_type == "liftoff" for event in graph.events))
        self.assertTrue(any(event.event_type == "touchdown" for event in graph.events))
        self.assertEqual(len(graph.anchors), 2)
        self.assertEqual(len(graph.patches), 2)
        self.assertEqual(graph.patches[0].patch_type, "foot")
        self.assertEqual(graph.transitions[0].active_body, "LF")
        self.assertEqual(graph.to_dict()["motion_id"], "motion_a")
        self.assertEqual(len(graph.to_dict()["patches"]), 2)

    def test_contact_patch_uses_anchor_position_and_patch_preset(self) -> None:
        contact = np.asarray([[True, False], [True, False], [False, False]])
        body_pos_w = np.asarray(
            [
                [[1.0, 2.0, 0.0], [0.0, 0.0, 0.0]],
                [[1.2, 2.0, 0.0], [0.0, 0.0, 0.0]],
                [[9.0, 9.0, 9.0], [0.0, 0.0, 0.0]],
            ]
        )

        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=contact,
            body_pos_w=body_pos_w,
            body_names=["left_foot", "right_foot"],
        )

        patch = graph.patches[0]
        self.assertEqual(patch.patch_type, "foot")
        self.assertEqual(patch.patch_center_world, [1.1, 2.0, 0.0])
        self.assertEqual(patch.link_names, ["left_foot", "left_foot_sole"])
        self.assertAlmostEqual(patch.slip_score or 0.0, 0.1)

    def test_contact_layer_roundtrips_graph_components(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
            body_names=["LF", "RF"],
            source="test",
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "contact_layer"
            write_contact_layer(root, graph)
            loaded = read_contact_graph(root, "motion_a")

        self.assertEqual([event.event_id for event in loaded.events], [event.event_id for event in graph.events])
        self.assertEqual([anchor.anchor_id for anchor in loaded.anchors], [anchor.anchor_id for anchor in graph.anchors])
        self.assertEqual([patch.patch_id for patch in loaded.patches], [patch.patch_id for patch in graph.patches])
        self.assertEqual(
            [transition.transition_id for transition in loaded.transitions],
            [transition.transition_id for transition in graph.transitions],
        )

    def test_contact_layer_read_derives_missing_patches_for_legacy_layers(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
            body_names=["LF", "RF"],
            source="test",
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "contact_layer"
            write_contact_jsonl(root / "events" / "motion_a.jsonl", graph.events)
            write_contact_jsonl(root / "anchors" / "motion_a.jsonl", graph.anchors)
            write_contact_jsonl(root / "transitions" / "motion_a.jsonl", graph.transitions)
            loaded = read_contact_graph(root, "motion_a")

        self.assertEqual(len(loaded.patches), len(graph.anchors))

    def test_bind_segment_to_contact_graph_refreshes_metadata_for_bounds(self) -> None:
        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
            body_names=["LF", "RF"],
            source="test",
        )
        segment = SegmentRecord(
            motion_id="motion_a",
            segment_id="segment_a",
            start_frame=1,
            end_frame=2,
            source="manual",
            metadata={"contact_transition": {"stale": True}},
        )

        bound = bind_segment_to_contact_graph(segment, graph)

        self.assertEqual(bound.metadata["contact_transition"]["transition_id"], graph.transitions[0].transition_id)
        self.assertEqual(bound.metadata["contact_binding"]["transition_id"], graph.transitions[0].transition_id)
        self.assertEqual(bound.metadata["contact_binding"]["patch_count"], 2)
        self.assertEqual(len(bound.metadata["contact_patches"]), 2)
        self.assertEqual(bound.metadata["active_body"], "LF")


if __name__ == "__main__":
    unittest.main()
