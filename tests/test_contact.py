from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.contact import (
    anchors_from_contact_mask,
    detect_contact_events,
    read_contact_anchors,
    read_contact_events,
    read_contact_transitions,
    segment_from_contact_transition,
    transitions_from_proto_indices,
    write_contact_jsonl,
)


class ContactEventTests(unittest.TestCase):
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
            write_contact_jsonl(root / "transitions.jsonl", transitions)

            loaded_events = read_contact_events(root / "events.jsonl")
            loaded_anchors = read_contact_anchors(root / "anchors.jsonl")
            loaded_transitions = read_contact_transitions(root / "transitions.jsonl")

        self.assertEqual(loaded_events[0].event_id, events[0].event_id)
        self.assertEqual(loaded_anchors[0].anchor_id, anchors[0].anchor_id)
        self.assertEqual(loaded_transitions[0].transition_id, transitions[0].transition_id)


if __name__ == "__main__":
    unittest.main()
