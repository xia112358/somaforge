from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import argparse
from unittest import mock

import numpy as np

from motion_edit import cli
from motion_edit.contact import (
    ContactEditPlan,
    append_anchor_edit_to_plan,
    contact_graph_from_masks,
    read_contact_edit_plan,
    validate_contact_edit_plan,
    write_contact_edit_plan,
    write_contact_layer,
)
from motion_edit.contact.generation import apply_contact_edit_plan_to_motion
from motion_edit.contact.schema import ContactAnchorEditRecord
from motion_edit.layers import read_layer


def _surface_edit() -> ContactAnchorEditRecord:
    return ContactAnchorEditRecord(
        edit_id="edit_0",
        motion_id="motion_a",
        anchor_id="anchor_lf",
        body="left_foot",
        old_world_position=[0.0, 0.0, 0.0],
        new_world_position=[0.1, 0.0, 0.0],
        requested_delta_world=[0.1, 0.0, 0.2],
        delta_world=[0.1, 0.0, 0.0],
        tangent_delta=[0.1, 0.0],
        affected_frames=[0, 10],
        surface_id="platform_top",
        surface_normal=[0.0, 0.0, 1.0],
        surface_coordinates_before={"u": 0.0, "v": 0.0},
        surface_coordinates_after={"u": 0.1, "v": 0.0},
        constraint_mode="reject",
    )


def _write_synthetic_motion_and_contact(root: Path, *, plan_status: str = "validated") -> tuple[Path, Path, ContactEditPlan]:
    motion = root / "motion_a.npz"
    body_pos = np.zeros((8, 2, 3), dtype=np.float32)
    body_pos[:, 1, 1] = 1.0
    body_lin_vel = np.zeros_like(body_pos)
    body_quat = np.zeros((8, 2, 4), dtype=np.float32)
    body_quat[..., 0] = 1.0
    joint_pos = np.arange(8 * 3, dtype=np.float32).reshape(8, 3)
    joint_vel = np.ones((8, 3), dtype=np.float32)
    np.savez(
        motion,
        body_pos_w=body_pos,
        body_lin_vel_w=body_lin_vel,
        body_quat_w=body_quat,
        joint_pos=joint_pos,
        joint_vel=joint_vel,
        body_names=np.asarray(["left_foot", "torso"], dtype=object),
        fps=np.asarray(50.0),
    )
    graph = contact_graph_from_masks(
        motion_id="motion_a",
        contact_mask=np.asarray([[False], [False], [True], [True], [True], [False], [False], [False]]),
        body_pos_w=np.zeros((8, 1, 3), dtype=np.float32),
        body_names=["left_foot"],
    )
    anchor = graph.anchors[0]
    graph = type(graph)(
        motion_id=graph.motion_id,
        events=graph.events,
        anchors=[
            type(anchor)(
                **{
                    **anchor.__dict__,
                    "anchor_id": "anchor_lf",
                    "body": "left_foot",
                    "start_frame": 2,
                    "end_frame": 5,
                    "world_position": [0.0, 0.0, 0.0],
                    "surface_id": "platform_top",
                    "object_id": "platform",
                    "surface_normal": [0.0, 0.0, 1.0],
                    "surface_origin": [0.0, 0.0, 0.0],
                    "surface_tangent_u": [1.0, 0.0, 0.0],
                    "surface_tangent_v": [0.0, 1.0, 0.0],
                    "surface_coordinates": {"u": 0.0, "v": 0.0},
                }
            )
        ],
        patches=graph.patches,
        transitions=graph.transitions,
    )
    write_contact_layer(root / "layers" / "contact" / "force_contact", graph)
    edit = ContactAnchorEditRecord(
        **{
            **_surface_edit().to_dict(),
            "affected_frames": [2, 5],
            "old_world_position": [0.0, 0.0, 0.0],
            "new_world_position": [0.2, 0.0, 0.0],
            "delta_world": [0.2, 0.0, 0.0],
            "surface_coordinates_after": {"u": 0.2, "v": 0.0},
        }
    )
    plan = ContactEditPlan(
        plan_id="plan_a",
        source_motion_path=str(motion),
        source_motion_id="motion_a",
        source_contact_layer="contact/force_contact",
        edits=[edit.to_dict()],
        status=plan_status,
    )
    plan_path = root / "plan.json"
    write_contact_edit_plan(plan_path, plan)
    return motion, plan_path, plan


class ContactEditPlanTests(unittest.TestCase):
    def test_contact_edit_plan_roundtrip_and_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            plan = append_anchor_edit_to_plan(
                path,
                _surface_edit(),
                plan_id="plan_a",
                source_motion_path="motion_a.npz",
                source_motion_id="motion_a",
                source_contact_layer="contact/force_contact",
                source_segment_layer="candidates/force_contact",
            )
            loaded = read_contact_edit_plan(path)

        self.assertEqual(plan.plan_id, "plan_a")
        self.assertEqual(loaded.source_motion_path, "motion_a.npz")
        self.assertEqual(loaded.source_segment_layer, "candidates/force_contact")
        self.assertEqual(len(loaded.edits), 1)
        self.assertEqual(loaded.edits[0]["surface_id"], "platform_top")

    def test_plan_validation_accepts_surface_constrained_edit(self) -> None:
        plan = ContactEditPlan(
            plan_id="plan_a",
            source_motion_path="motion_a.npz",
            source_motion_id="motion_a",
            source_contact_layer="contact/force_contact",
            edits=[_surface_edit().to_dict()],
        )

        warnings = validate_contact_edit_plan(plan)

        self.assertEqual(warnings, [])

    def test_plan_validation_rejects_free_edit_by_default(self) -> None:
        edit = ContactAnchorEditRecord(
            edit_id="edit_free",
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            old_world_position=[0.0, 0.0, 0.0],
            new_world_position=[0.0, 0.0, 0.1],
            delta_world=[0.0, 0.0, 0.1],
            affected_frames=[0, 10],
            constraint_mode="free_3d",
        )
        plan = ContactEditPlan(
            plan_id="plan_a",
            source_motion_path="motion_a.npz",
            source_motion_id="motion_a",
            source_contact_layer="contact/force_contact",
            edits=[edit.to_dict()],
        )

        with self.assertRaises(ValueError):
            validate_contact_edit_plan(plan)

        self.assertEqual(validate_contact_edit_plan(plan, allow_free=True), [])

    def test_plan_validation_rejects_normal_displacement(self) -> None:
        edit = _surface_edit()
        unsafe = ContactAnchorEditRecord(**{**edit.to_dict(), "delta_world": [0.1, 0.0, 0.1]})
        plan = ContactEditPlan(
            plan_id="plan_a",
            source_motion_path="motion_a.npz",
            source_motion_id="motion_a",
            source_contact_layer="contact/force_contact",
            edits=[unsafe.to_dict()],
        )

        with self.assertRaises(ValueError):
            validate_contact_edit_plan(plan)

    def test_write_contact_edit_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            plan = ContactEditPlan(
                plan_id="plan_a",
                source_motion_path="motion_a.npz",
                source_motion_id="motion_a",
                source_contact_layer="contact/force_contact",
                edits=[_surface_edit().to_dict()],
            )
            written = write_contact_edit_plan(path, plan)

            self.assertTrue(written.exists())

    def test_validate_contact_edit_plan_command_marks_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            write_contact_edit_plan(
                path,
                ContactEditPlan(
                    plan_id="plan_a",
                    source_motion_path="motion_a.npz",
                    source_motion_id="motion_a",
                    source_contact_layer="contact/force_contact",
                    edits=[_surface_edit().to_dict()],
                ),
            )

            cli._cmd_validate_contact_edit_plan(argparse.Namespace(plan=str(path), allow_free=False, no_write=False))
            loaded = read_contact_edit_plan(path)

        self.assertEqual(loaded.status, "validated")

    def test_validate_contact_edit_plan_command_rejects_free_edit(self) -> None:
        edit = ContactAnchorEditRecord(
            edit_id="edit_free",
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            old_world_position=[0.0, 0.0, 0.0],
            new_world_position=[0.0, 0.0, 0.1],
            delta_world=[0.0, 0.0, 0.1],
            affected_frames=[0, 10],
            constraint_mode="free_3d",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            write_contact_edit_plan(
                path,
                ContactEditPlan(
                    plan_id="plan_a",
                    source_motion_path="motion_a.npz",
                    source_motion_id="motion_a",
                    source_contact_layer="contact/force_contact",
                    edits=[edit.to_dict()],
                ),
            )

            with self.assertRaises(ValueError):
                cli._cmd_validate_contact_edit_plan(argparse.Namespace(plan=str(path), allow_free=False, no_write=False))

    def test_generate_lte_augmentation_refuses_draft_plan_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            write_contact_edit_plan(
                path,
                ContactEditPlan(
                    plan_id="plan_a",
                    source_motion_path="motion_a.npz",
                    source_motion_id="motion_a",
                    source_contact_layer="contact/force_contact",
                    edits=[_surface_edit().to_dict()],
                ),
            )

            with mock.patch.object(cli, "apply_contact_edit_plan_to_motion") as apply_mock:
                with self.assertRaises(ValueError):
                    cli._cmd_generate_lte_augmentation(
                        argparse.Namespace(
                            plan=str(path),
                            output_motion="out.npz",
                            output_motion_version_id=None,
                            output_contact_layer=None,
                            output_segment_layer=None,
                            source_contact_layer=None,
                            allow_draft=False,
                            allow_free=False,
                            mode="lte_windowed",
                            falloff_before=20,
                            falloff_after=20,
                            global_weight=0.35,
                            edited_body_weight=1.0,
                            fps=50.0,
                            overwrite=False,
                            register_motion_version=False,
                            build_canonical=False,
                            dry_run=False,
                        )
                    )

        apply_mock.assert_not_called()

    def test_generate_lte_augmentation_windowed_backend_writes_motion_and_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_motion, _plan_path, plan = _write_synthetic_motion_and_contact(root)
            output = root / "out.npz"
            result = apply_contact_edit_plan_to_motion(
                plan,
                output_motion_path=output,
                output_contact_layer="contact/generated",
                output_segment_layer="candidates/generated",
                falloff_before=1,
                falloff_after=1,
                global_weight=0.25,
                layers_root=root / "layers",
            )
            generated = np.load(output, allow_pickle=True)
            source = np.load(source_motion, allow_pickle=True)
            body_pos = generated["body_pos_w"]

            self.assertEqual(result.output_motion_path, output)
            np.testing.assert_allclose(body_pos[2:5, 0, 0], 0.2)
            np.testing.assert_allclose(body_pos[2:5, 1, 0], 0.05)
            np.testing.assert_allclose(body_pos[0, :, :], source["body_pos_w"][0])
            self.assertGreater(body_pos[1, 0, 0], 0.0)
            self.assertLess(body_pos[1, 0, 0], 0.2)
            self.assertFalse(np.allclose(generated["body_lin_vel_w"], source["body_lin_vel_w"]))
            np.testing.assert_array_equal(generated["body_quat_w"], source["body_quat_w"])
            np.testing.assert_array_equal(generated["joint_pos"], source["joint_pos"])
            metadata = generated["motion_edit_generation_metadata"].item()
            self.assertIn("lte_windowed", metadata)
            edited_graph = cli.read_contact_graph(root / "layers" / "contact" / "generated", "motion_a")
            self.assertEqual(edited_graph.anchors[0].world_position, [0.2, 0.0, 0.0])
            self.assertEqual(edited_graph.anchors[0].surface_id, "platform_top")
            segments = read_layer(root / "layers" / "candidates" / "generated" / "motion_a.jsonl", default_source="lte_windowed", default_status="candidate")
            self.assertTrue(segments)

    def test_generate_lte_augmentation_dry_run_and_overwrite_safety(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source_motion, _plan_path, plan = _write_synthetic_motion_and_contact(root)
            output = root / "out.npz"
            output.write_bytes(b"existing")

            result = apply_contact_edit_plan_to_motion(
                plan,
                output_motion_path=output,
                dry_run=True,
                layers_root=root / "layers",
            )
            self.assertEqual(result.output_motion_path, output)
            self.assertEqual(output.read_bytes(), b"existing")
            with self.assertRaises(FileExistsError):
                apply_contact_edit_plan_to_motion(plan, output_motion_path=output, layers_root=root / "layers")

    def test_generate_lte_augmentation_requires_body_pos_and_body_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source_motion, _plan_path, plan = _write_synthetic_motion_and_contact(root)
            missing_body_pos = root / "missing_body_pos.npz"
            np.savez(missing_body_pos, joint_pos=np.zeros((4, 3), dtype=np.float32))
            plan_missing = ContactEditPlan(
                plan_id=plan.plan_id,
                source_motion_path=str(missing_body_pos),
                source_motion_id=plan.source_motion_id,
                source_contact_layer=plan.source_contact_layer,
                edits=plan.edits,
                status=plan.status,
            )
            with self.assertRaisesRegex(ValueError, "requires body_pos_w"):
                apply_contact_edit_plan_to_motion(plan_missing, output_motion_path=root / "out.npz", layers_root=root / "layers")

            no_names = root / "no_names.npz"
            np.savez(no_names, body_pos_w=np.zeros((8, 2, 3), dtype=np.float32))
            plan_no_names = ContactEditPlan(
                plan_id=plan.plan_id,
                source_motion_path=str(no_names),
                source_motion_id=plan.source_motion_id,
                source_contact_layer=plan.source_contact_layer,
                edits=plan.edits,
                status=plan.status,
            )
            with self.assertRaisesRegex(ValueError, "cannot resolve body index"):
                apply_contact_edit_plan_to_motion(plan_no_names, output_motion_path=root / "out.npz", layers_root=root / "layers")


if __name__ == "__main__":
    unittest.main()
