from __future__ import annotations

import tempfile
import unittest
import argparse
from pathlib import Path
from unittest import mock

import numpy as np

from motion_edit import cli
from motion_edit.contact import read_contact_graph
from motion_edit.force_proto import contact_graph_from_masked_motion, segments_from_masked_motion
from motion_edit.layers import read_layer


def _write_proto_motion(path: Path) -> None:
    np.savez(
        path,
        proto_start_idx=np.asarray([1]),
        proto_end_idx=np.asarray([4]),
        contact_part_mask=np.asarray(
            [
                [False, True],
                [True, True],
                [True, False],
                [False, False],
                [False, True],
            ]
        ),
        active_part_mask=np.asarray(
            [
                [False, True],
                [True, False],
                [True, False],
                [False, True],
                [False, True],
            ]
        ),
        support_part_mask=np.asarray(
            [
                [False, True],
                [False, True],
                [True, False],
                [True, False],
                [False, True],
            ]
        ),
        contact_body_names=np.asarray(["LF", "RF"]),
    )


class ForceProtoContactTests(unittest.TestCase):
    def test_force_proto_segments_include_structured_contact_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion_a.npz"
            _write_proto_motion(path)

            segments = segments_from_masked_motion(path)

        self.assertEqual(len(segments), 1)
        segment = segments[0]
        self.assertEqual((segment.start_frame, segment.end_frame), (1, 4))
        self.assertEqual(segment.contact_start, "11")
        self.assertEqual(segment.contact_end, "00")
        self.assertEqual(segment.metadata["active_body"], "LF")
        self.assertEqual(segment.metadata["support_bodies"], ["RF"])
        self.assertIn("contact_transition", segment.metadata)
        self.assertIn("contact_events", segment.metadata)
        self.assertIn("contact_anchors", segment.metadata)

    def test_contact_graph_from_masked_motion_uses_same_contact_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion_a.npz"
            _write_proto_motion(path)

            graph = contact_graph_from_masked_motion(path)

        self.assertEqual(graph.motion_id, "motion_a")
        self.assertEqual(len(graph.transitions), 1)
        self.assertGreaterEqual(len(graph.events), 1)
        self.assertGreaterEqual(len(graph.anchors), 1)

    def test_import_force_proto_writes_contact_layer_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            motion_dir = root / "motions"
            motion_dir.mkdir()
            _write_proto_motion(motion_dir / "motion_a.npz")
            layers_root = root / "layers"
            args = argparse.Namespace(
                motion_dir=str(motion_dir),
                pattern="*.npz",
                layer_name="force_contact",
                source="force_contact",
            )
            with (
                mock.patch.object(cli, "LAYERS_ROOT", layers_root),
                mock.patch.object(cli, "layer_dir", lambda status, name: layers_root / "candidates" / name),
            ):
                cli._cmd_import_force_proto(args)

            segments = read_layer(
                layers_root / "candidates" / "force_contact" / "motion_a.jsonl",
                default_source="force_contact",
                default_status="candidate",
            )
            graph = read_contact_graph(layers_root / "contact" / "force_contact", "motion_a")

        self.assertEqual(len(segments), 1)
        self.assertEqual(len(graph.transitions), 1)
        self.assertGreaterEqual(len(graph.anchors), 1)


if __name__ == "__main__":
    unittest.main()
