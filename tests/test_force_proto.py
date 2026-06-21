from __future__ import annotations

import argparse
import contextlib
import io
import json
import tempfile
import unittest
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


def _write_proto_motion_with_positions(path: Path) -> None:
    _write_proto_motion(path)
    with np.load(path, allow_pickle=True) as data:
        payload = {key: data[key] for key in data.files}
    payload["body_pos_w"] = np.asarray(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.2, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.4, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.6, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.8, 0.0, 0.0], [1.0, 0.0, 0.0]],
        ]
    )
    np.savez(path, **payload)


class ForceProtoContactTests(unittest.TestCase):
    def test_contact_graph_accepts_multi_proto_numpy_indices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion_multi.npz"
            np.savez(
                path,
                proto_start_idx=np.asarray([0, 2]),
                proto_end_idx=np.asarray([2, 5]),
                contact_part_mask=np.asarray(
                    [
                        [True, False],
                        [False, False],
                        [True, False],
                        [True, True],
                        [False, True],
                    ]
                ),
                contact_body_names=np.asarray(["LF", "RF"]),
            )

            graph = contact_graph_from_masked_motion(path)

        self.assertEqual(len(graph.transitions), 2)

    def test_force_proto_without_proto_indices_derives_segments_from_event_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion_events.npz"
            np.savez(
                path,
                contact_part_mask=np.asarray(
                    [
                        [True, False],
                        [False, False],
                        [True, False],
                        [True, False],
                    ]
                ),
                contact_body_names=np.asarray(["LF", "RF"]),
            )

            segments = segments_from_masked_motion(path)
            graph = contact_graph_from_masked_motion(path)

        self.assertEqual(len(segments), 1)
        self.assertEqual((segments[0].start_frame, segments[0].end_frame), (1, 2))
        self.assertEqual(len(graph.transitions), 1)

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
        self.assertIn("contact_patches", segment.metadata)
        self.assertGreaterEqual(len(segment.metadata["contact_patches"]), 1)

    def test_force_proto_anchor_positions_are_estimated_when_body_pos_w_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion_a.npz"
            _write_proto_motion_with_positions(path)

            graph = contact_graph_from_masked_motion(path)

        lf_anchor = next(anchor for anchor in graph.anchors if anchor.body == "LF")
        self.assertEqual(lf_anchor.world_position, [0.30000000000000004, 0.0, 0.0])
        self.assertEqual(lf_anchor.position_source, "body_pos_w_mean")
        self.assertIn("mean_drift_xy", lf_anchor.metadata)

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
            motion_path = motion_dir / "motion_a.npz"
            _write_proto_motion_with_positions(motion_path)
            original_motion_bytes = motion_path.read_bytes()
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
                list_args = argparse.Namespace(source="contact/force_contact", motion_id="motion_a", limit=1)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    cli._cmd_list_contact_layer(list_args)
                overlay_path = root / "overlay.json"
                export_args = argparse.Namespace(
                    source="contact/force_contact",
                    motion_id="motion_a",
                    output=str(overlay_path),
                )
                cli._cmd_export_contact_overlay(export_args)
                overlay_text = overlay_path.read_text(encoding="utf-8")
                graph_before_move = read_contact_graph(layers_root / "contact" / "force_contact", "motion_a")
                unsafe_default_args = argparse.Namespace(
                    source="contact/force_contact",
                    motion_id="motion_a",
                    anchor_id=graph_before_move.anchors[0].anchor_id,
                    delta_world=[0.1, 0.0, 0.0],
                    tangent_delta=None,
                    new_world_position=None,
                    mode="reject",
                    allow_free_3d=False,
                    output_source="contact/force_contact_moved",
                    edit_source="manual",
                    edit_plan=None,
                    append_to_plan=False,
                    plan_id=None,
                    source_motion=None,
                    source_segments=None,
                )
                with self.assertRaises(ValueError):
                    cli._cmd_move_contact_anchor(unsafe_default_args)
                plan_path = root / "contact_edit_plan.json"
                move_args = argparse.Namespace(
                    source="contact/force_contact",
                    motion_id="motion_a",
                    anchor_id=graph_before_move.anchors[0].anchor_id,
                    delta_world=[0.1, 0.0, 0.0],
                    tangent_delta=None,
                    new_world_position=None,
                    mode="reject",
                    allow_free_3d=True,
                    output_source="contact/force_contact_moved",
                    edit_source="manual",
                    edit_plan=str(plan_path),
                    append_to_plan=False,
                    plan_id="plan_a",
                    source_motion=str(motion_path),
                    source_segments="candidates/force_contact",
                )
                with mock.patch.object(cli, "apply_contact_edit_plan_to_motion") as apply_mock:
                    cli._cmd_move_contact_anchor(move_args)
                apply_mock.assert_not_called()
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                motion_bytes_after_move = motion_path.read_bytes()

            segments = read_layer(
                layers_root / "candidates" / "force_contact" / "motion_a.jsonl",
                default_source="force_contact",
                default_status="candidate",
            )
            graph = read_contact_graph(layers_root / "contact" / "force_contact", "motion_a")
            moved_graph = read_contact_graph(layers_root / "contact" / "force_contact_moved", "motion_a")

        self.assertEqual(motion_bytes_after_move, original_motion_bytes)
        self.assertEqual(plan["plan_id"], "plan_a")
        self.assertEqual(plan["source_motion_path"], str(motion_path))
        self.assertEqual(plan["source_segment_layer"], "candidates/force_contact")
        self.assertEqual(len(plan["edits"]), 1)
        self.assertEqual(len(segments), 1)
        self.assertEqual(len(graph.transitions), 1)
        self.assertGreaterEqual(len(graph.anchors), 1)
        self.assertNotEqual(moved_graph.anchors[0].world_position, graph.anchors[0].world_position)
        self.assertIn("motion_a: events=", out.getvalue())
        self.assertIn("patches=", out.getvalue())
        self.assertIn("transitions=1", out.getvalue())
        self.assertIn('"contact_graph"', overlay_text)


if __name__ == "__main__":
    unittest.main()
