from __future__ import annotations

import unittest

import numpy as np

from motion_edit.contact.graph import contact_graph_from_masks
from motion_edit.storage.canonical import segments_from_contact_transitions


class ContactSegmentExtractionTests(unittest.TestCase):
    def test_anchor_pair_segments_own_only_contact_point_to_contact_point_window(self) -> None:
        contact = np.zeros((12, 2), dtype=bool)
        contact[0:3, 0] = True
        contact[7:10, 0] = True
        contact[:, 1] = True
        body_names = ["left_foot", "right_hand"]

        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=contact,
            body_names=body_names,
        )
        transitions = [transition for transition in graph.transitions if transition.active_body == "left_foot"]

        self.assertEqual(len(transitions), 1)
        transition = transitions[0]
        self.assertEqual(transition.start_frame, 2)
        self.assertEqual(transition.end_frame, 8)
        self.assertEqual(transition.metadata["segmentation_kind"], "anchor_pair")
        self.assertEqual(transition.metadata["endpoint_policy"], "contact_point_inclusive")
        self.assertEqual(transition.metadata["source_anchor_interval"], [0, 3])
        self.assertEqual(transition.metadata["target_anchor_interval"], [7, 10])
        self.assertEqual(transition.metadata["source_anchor_frame"], 2)
        self.assertEqual(transition.metadata["target_anchor_frame"], 7)
        self.assertEqual(transition.metadata["outside_policy"], "copy_original")
        self.assertEqual(transition.metadata["owned_bodies"], ["left_foot"])

    def test_canonical_segment_metadata_keeps_endpoint_anchors_for_local_deform(self) -> None:
        contact = np.zeros((12, 2), dtype=bool)
        contact[0:3, 0] = True
        contact[7:10, 0] = True
        contact[:, 1] = True

        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=contact,
            body_names=["left_foot", "right_hand"],
        )
        segments = segments_from_contact_transitions(
            graph,
            motion_version_id="motion_v1",
            motion_path="motion_a.npz",
        )
        foot_segments = [segment for segment in segments if segment.active == "left_foot"]

        self.assertEqual(len(foot_segments), 1)
        segment = foot_segments[0]
        self.assertEqual(segment.start_frame, 2)
        self.assertEqual(segment.end_frame, 8)
        self.assertEqual(segment.metadata["segmentation_kind"], "anchor_pair")
        self.assertEqual(segment.metadata["endpoint_policy"], "contact_point_inclusive")
        self.assertEqual(segment.metadata["outside_policy"], "copy_original")
        anchors = {anchor["anchor_id"]: anchor for anchor in segment.metadata["contact_anchors"]}
        self.assertIn(segment.metadata["source_anchor_id"], anchors)
        self.assertIn(segment.metadata["target_anchor_id"], anchors)

    def test_proto_indices_take_precedence_over_auto_anchor_pairs(self) -> None:
        contact = np.zeros((12, 1), dtype=bool)
        contact[0:3, 0] = True
        contact[7:10, 0] = True

        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=contact,
            proto_starts=[1],
            proto_ends=[5],
            body_names=["left_foot"],
        )

        self.assertEqual(len(graph.transitions), 1)
        transition = graph.transitions[0]
        self.assertEqual(transition.start_frame, 1)
        self.assertEqual(transition.end_frame, 5)
        self.assertEqual(transition.metadata["segmentation_kind"], "proto_index")

    def test_single_anchor_motion_keeps_no_auto_segment(self) -> None:
        contact = np.zeros((8, 1), dtype=bool)
        contact[2:5, 0] = True

        graph = contact_graph_from_masks(
            motion_id="motion_a",
            contact_mask=contact,
            body_names=["left_foot"],
        )

        self.assertEqual(len(graph.anchors), 1)
        self.assertEqual(graph.transitions, [])


if __name__ == "__main__":
    unittest.main()
