from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.contact import contact_graph_from_masks
from motion_edit.export import export_contact_overlay, export_cutter_segments, export_motion_manifest, export_split_npz
from motion_edit.io import read_jsonl
from motion_edit.schema import SegmentRecord


def _contact_segment(motion_path: str) -> SegmentRecord:
    return SegmentRecord(
        motion_id="motion_a",
        segment_id="motion_a_force_0000",
        start_frame=1,
        end_frame=4,
        source="force_contact",
        status="candidate",
        motion_path=motion_path,
        clip_npz=motion_path,
        contact_start="11",
        contact_end="00",
        active="10",
        support="01",
        metadata={
            "contact_transition": {
                "transition_id": "motion_a_force_transition_0000",
                "start_frame": 1,
                "end_frame": 4,
                "transition_type": "support_transfer",
            },
            "active_body": "LF",
            "support_bodies": ["RF"],
            "source_anchor_id": "anchor_src",
            "target_anchor_id": "anchor_dst",
            "transition_type": "support_transfer",
            "contact_events": [{"event_id": "event_0"}],
            "contact_anchors": [{"anchor_id": "anchor_src"}, {"anchor_id": "anchor_dst"}],
            "contact_patches": [{"patch_id": "patch_src", "patch_type": "foot"}],
            "old_anchor_world": [0.0, 0.0, 0.0],
            "new_anchor_world": [0.1, 0.0, 0.0],
            "delta_world": [0.1, 0.0, 0.0],
            "affected_frames": [1, 4],
            "contact_anchor_edit": {"edit_type": "move_contact_anchor", "anchor_id": "anchor_src"},
        },
    )


class ExportContactMetadataTests(unittest.TestCase):
    def test_contact_overlay_export_writes_contact_graph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = contact_graph_from_masks(
                motion_id="motion_a",
                contact_mask=np.asarray([[True, False], [False, False], [True, False]]),
                body_names=["LF", "RF"],
            )
            out = export_contact_overlay(root / "overlay.json", graph)
            overlay = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(overlay["schema_version"], 1)
        self.assertEqual(overlay["contact_graph"]["motion_id"], "motion_a")
        self.assertGreaterEqual(len(overlay["contact_graph"]["anchors"]), 1)

    def test_cutter_export_preserves_contact_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            np.savez(motion, qpos=np.zeros((6, 2)))
            export_cutter_segments(root / "cutter", [_contact_segment(str(motion))])

            records = read_jsonl(root / "cutter" / "motion_a.segments.jsonl")

        self.assertEqual(records[0]["metadata"]["active_body"], "LF")
        self.assertEqual(records[0]["metadata"]["contact_transition"]["transition_id"], "motion_a_force_transition_0000")

    def test_split_npz_includes_contact_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            np.savez(motion, qpos=np.zeros((6, 2)))
            written = export_split_npz(root / "split", [_contact_segment(str(motion))])

            data = np.load(written[0], allow_pickle=True)

        self.assertEqual(str(data["motion_edit_active_body"]), "LF")
        self.assertEqual(json.loads(str(data["motion_edit_support_bodies"])), ["RF"])
        self.assertEqual(str(data["motion_edit_source_anchor_id"]), "anchor_src")
        self.assertEqual(str(data["motion_edit_target_anchor_id"]), "anchor_dst")
        self.assertEqual(json.loads(str(data["motion_edit_contact_transition"]))["transition_id"], "motion_a_force_transition_0000")
        self.assertEqual(json.loads(str(data["motion_edit_old_anchor_world"])), [0.0, 0.0, 0.0])
        self.assertEqual(json.loads(str(data["motion_edit_new_anchor_world"])), [0.1, 0.0, 0.0])
        self.assertEqual(json.loads(str(data["motion_edit_delta_world"])), [0.1, 0.0, 0.0])
        self.assertEqual(json.loads(str(data["motion_edit_affected_frames"])), [1, 4])
        self.assertEqual(json.loads(str(data["motion_edit_contact_patches"]))[0]["patch_type"], "foot")

    def test_manifest_includes_contact_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion = root / "motion_a.npz"
            np.savez(motion, qpos=np.zeros((6, 2)))
            out = export_motion_manifest(root / "manifest.json", [_contact_segment(str(motion))])
            manifest = json.loads(out.read_text(encoding="utf-8"))

        item = manifest["motions"][0]["segments"][0]
        self.assertEqual(item["active_body"], "LF")
        self.assertEqual(item["support_bodies"], ["RF"])
        self.assertEqual(item["source_anchor_id"], "anchor_src")
        self.assertEqual(item["target_anchor_id"], "anchor_dst")
        self.assertEqual(item["old_anchor_world"], [0.0, 0.0, 0.0])
        self.assertEqual(item["new_anchor_world"], [0.1, 0.0, 0.0])
        self.assertEqual(item["delta_world"], [0.1, 0.0, 0.0])
        self.assertEqual(item["affected_frames"], [1, 4])
        self.assertEqual(item["transition_type"], "support_transfer")
        self.assertEqual(item["contact_metadata"]["event_count"], 1)
        self.assertEqual(item["contact_metadata"]["anchor_count"], 2)
        self.assertEqual(item["contact_metadata"]["patch_count"], 1)
        self.assertEqual(item["contact_metadata"]["patches"][0]["patch_type"], "foot")
        self.assertEqual(item["contact_metadata"]["anchor_edit"]["edit_type"], "move_contact_anchor")


if __name__ == "__main__":
    unittest.main()
