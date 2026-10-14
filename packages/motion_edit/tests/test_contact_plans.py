from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
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
from motion_edit.generation import resolve_body_index
from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.io import write_contact_surfaces
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord, ContactSurfaceRecord
from motion_edit.generation.lte_fullbody import (
    _copy_contact_force_payload_with_edits,
    _semantic_keypoints_from_motion,
)
from motion_edit.layers import read_layer
from somaforge_core.robot_assets import encode_robot_asset_json

_NP_SAVEZ = np.savez


def _savez(path: str | Path, *args: object, **kwargs: object) -> None:
    kwargs.setdefault("robot_asset_json", np.asarray(encode_robot_asset_json()))
    _NP_SAVEZ(path, *args, **kwargs)


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
    _savez(
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
                    "metadata": {
                        "surface_bindings": [
                            {
                                "original_world_position": [0.0, 0.0, 0.0],
                                "projected_world_position": [0.0, 0.0, 0.0],
                                "bound_world_position": [0.0, 0.0, 0.0],
                                "raw_surface_coordinates": {"u": 0.0, "v": 0.0},
                                "surface_coordinates": {"u": 0.0, "v": 0.0},
                                "signed_surface_distance": 0.0,
                            }
                        ]
                    },
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


def _write_fullbody_lte_source(root: Path) -> tuple[Path, ContactEditPlan]:
    motion = root / "fullbody_source.npz"
    body_names = np.asarray(
        [
            "pelvis",
            "left_hip_roll_link",
            "left_knee_link",
            "left_ankle_roll_link",
            "right_hip_roll_link",
            "right_knee_link",
            "right_ankle_roll_link",
            "torso_link",
            "left_shoulder_roll_link",
            "left_elbow_link",
            "left_wrist_yaw_link",
            "right_shoulder_roll_link",
            "right_elbow_link",
            "right_wrist_yaw_link",
            "left_ankle_roll_sphere_5_link",
            "left_ankle_roll_sphere_2_link",
            "left_ankle_roll_sphere_3_link",
            "left_ankle_roll_sphere_4_link",
            "left_ankle_roll_sphere_5_link",
            "right_ankle_roll_sphere_5_link",
            "right_ankle_roll_sphere_2_link",
            "right_ankle_roll_sphere_3_link",
            "right_ankle_roll_sphere_4_link",
            "right_ankle_roll_sphere_5_link",
        ],
        dtype=object,
    )
    body_pos = np.zeros((8, len(body_names), 3), dtype=np.float32)
    for index in range(len(body_names)):
        body_pos[:, index, 0] = float(index)
    joint_pos = np.zeros((8, 10), dtype=np.float32)
    joint_pos[:, 3] = 1.0
    _savez(
        motion,
        body_pos_w=body_pos,
        body_quat_w=np.tile(np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32), (8, len(body_names), 1)),
        body_lin_vel_w=np.zeros_like(body_pos),
        body_names=body_names,
        joint_pos=joint_pos,
        joint_vel=np.zeros_like(joint_pos),
        joint_names=np.asarray(["j0", "j1", "j2"], dtype=object),
        fps=np.asarray(50.0),
    )
    anchor = ContactGraph(
        motion_id="motion_a",
        anchors=[
            ContactAnchorRecord(
                motion_id="motion_a",
                anchor_id="anchor_lf",
                body="left_foot",
                start_frame=2,
                end_frame=5,
                world_position=[3.0, 0.0, 0.0],
                surface_id="platform_top",
                surface_normal=[0.0, 0.0, 1.0],
                surface_coordinates={"u": 0.0, "v": 0.0},
            )
        ],
    )
    write_contact_layer(root / "layers" / "contact" / "force_contact", anchor)
    terrain = root / "terrain.obj"
    terrain.write_text(
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\n"
        "f 1 2 3\nf 1 2 4\nf 1 3 4\nf 2 3 4\n",
        encoding="utf-8",
    )
    write_contact_surfaces(
        root / "layers" / "contact" / "force_contact" / "surfaces" / "motion_a.jsonl",
        [
            ContactSurfaceRecord(
                motion_id="motion_a",
                surface_id="platform_top",
                object_id="terrain",
                surface_type="mesh_face",
                origin=[0.0, 0.0, 0.0],
                normal=[0.0, 0.0, 1.0],
                tangent_u=[1.0, 0.0, 0.0],
                tangent_v=[0.0, 1.0, 0.0],
                metadata={"mesh_path": str(terrain)},
            )
        ],
    )
    edit = ContactAnchorEditRecord(
        edit_id="fullbody_edit",
        motion_id="motion_a",
        anchor_id="anchor_lf",
        body="left_foot",
        old_world_position=[3.0, 0.0, 0.0],
        new_world_position=[3.2, 0.0, 0.0],
        delta_world=[0.2, 0.0, 0.0],
        affected_frames=[2, 5],
        surface_id="platform_top",
        surface_normal=[0.0, 0.0, 1.0],
        constraint_mode="reject",
    )
    plan = ContactEditPlan(
        plan_id="fullbody_plan",
        source_motion_path=str(motion),
        source_motion_id="motion_a",
        source_contact_layer="contact/force_contact",
        edits=[edit.to_dict()],
        status="validated",
    )
    return motion, plan


class ContactEditPlanTests(unittest.TestCase):
    def test_generated_contact_force_points_follow_episode_edit(self) -> None:
        frames = 5
        forces = np.arange(frames * 8 * 3, dtype=np.float32).reshape(frames, 8, 3)
        positions = np.zeros((frames, 8, 3), dtype=np.float32)
        valid = np.zeros((frames, 8), dtype=bool)
        valid[1:4, 5] = True
        position_history = np.zeros((frames, 2, 8, 3), dtype=np.float32)
        valid_history = np.zeros((frames, 2, 8), dtype=bool)
        valid_history[1:4, :, 5] = True
        motion = {
            "contact_force_part_order": np.asarray(
                ["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"]
            ),
            "contact_force_part_w": forces,
            "contact_force_part_mask": valid,
            "contact_force_part_position_w": positions,
            "contact_force_part_position_valid": valid,
            "contact_force_part_position_history_w": position_history,
            "contact_force_part_position_valid_history": valid_history,
            "contact_force_provenance_json": np.asarray("{}"),
            "raw_contact_point0_w": np.ones((frames, 2, 3), dtype=np.float32),
        }
        edit = ContactAnchorEditRecord(
            edit_id="move_right_hand",
            motion_id="motion_a",
            anchor_id="right_hand_contact",
            body="right_hand",
            old_world_position=[0.0, 0.0, 0.0],
            new_world_position=[0.1, 0.2, 0.0],
            delta_world=[0.1, 0.2, 0.0],
            affected_frames=[1, 4],
        )
        generated: dict[str, object] = {}

        _copy_contact_force_payload_with_edits(
            generated,
            motion=motion,
            edits=[edit],
            n_frames=frames,
        )

        np.testing.assert_array_equal(generated["source_reference_contact_force_part_w"], forces)
        np.testing.assert_array_equal(generated["source_reference_contact_force_part_position_w"], positions)
        np.testing.assert_array_equal(generated["source_reference_contact_force_part_position_history_w"], position_history)
        self.assertNotIn("contact_force_part_w", generated)
        self.assertNotIn("raw_contact_point0_w", generated)
        assessment = json.loads(str(generated["support_assessment_json"]))
        self.assertEqual(assessment["status"], "unknown")

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

    def test_legacy_cli_cannot_bypass_contact_aware_generation(self) -> None:
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["generate-lte-augmentation"])


    def test_dense_taskspace_maps_contact_point_names_to_feet(self) -> None:
        from motion_edit.generation.lte_fullbody import _semantic_body_weights

        weights = _semantic_body_weights(["left_foot_contact_point", "right_foot_contact_point"], ["pelvis", "torso", "left_hand", "right_hand", "left_foot", "right_foot"])

        self.assertEqual(float(weights[0, 4]), 1.0)
        self.assertEqual(float(weights[1, 5]), 1.0)


    def test_resolve_body_index_maps_contact_parts_to_holosoma_links(self) -> None:
        motion = {
            "body_names": np.asarray(
                [
                    "world",
                    "pelvis",
                    "left_ankle_roll_sphere_5_link",
                    "left_ankle_roll_link",
                    "right_ankle_roll_sphere_5_link",
                    "left_sphere_hand_link",
                    "right_sphere_hand_link",
                ],
                dtype=object,
            )
        }

        self.assertEqual(resolve_body_index(motion, "left_foot"), 2)
        self.assertEqual(resolve_body_index(motion, "right_foot"), 4)
        self.assertEqual(resolve_body_index(motion, "left_hand"), 5)
        self.assertEqual(resolve_body_index(motion, "right_hand"), 6)

    def test_fullbody_contact_keypoints_accept_canonical_kinematic_body_subset(self) -> None:
        body_names = [
            "pelvis",
            "left_hip_roll_link",
            "left_knee_link",
            "left_ankle_roll_link",
            "left_ankle_roll_sphere_5_link",
            "right_hip_roll_link",
            "right_knee_link",
            "right_ankle_roll_link",
            "right_ankle_roll_sphere_5_link",
            "torso_link",
            "left_shoulder_roll_link",
            "left_elbow_link",
            "left_wrist_yaw_link",
            "right_shoulder_roll_link",
            "right_elbow_link",
            "right_wrist_yaw_link",
        ]
        frames = 2
        body_pos = np.zeros((frames, len(body_names), 3), dtype=np.float64)
        body_quat = np.zeros((frames, len(body_names), 4), dtype=np.float64)
        body_quat[..., 0] = 1.0
        part_positions = np.zeros((frames, 8, 3), dtype=np.float64)
        part_positions[0, 1] = [0.4, 0.2, 0.1]
        part_valid = np.zeros((frames, 8), dtype=bool)
        part_valid[0, 1] = True
        keypoints = _semantic_keypoints_from_motion(
            {
                "body_names": np.asarray(body_names),
                "body_pos_w": body_pos,
                "body_quat_w": body_quat,
                "contact_force_part_order": np.asarray(
                    ["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"]
                ),
                "contact_force_part_position_w": part_positions,
                "contact_force_part_position_valid": part_valid,
            }
        )

        self.assertNotIn("left_toe", keypoints)
        self.assertNotIn("right_toe", keypoints)
        self.assertIn("left_ankle", keypoints)
        self.assertIn("left_foot", keypoints)
        self.assertEqual(keypoints["right_foot"].shape, (frames, 3))

    def test_missing_canonical_foot_does_not_fall_back_to_ankle(self) -> None:
        from motion_edit.generation.omni_contact_graph import OMNI_KEYPOINT_LINKS
        self.assertEqual(OMNI_KEYPOINT_LINKS["left_foot"], ("left_ankle_roll_sphere_5_link",))
        self.assertEqual(OMNI_KEYPOINT_LINKS["right_foot"], ("right_ankle_roll_sphere_5_link",))
        with self.assertRaises(ValueError):
            _semantic_keypoints_from_motion({
                "body_names": np.asarray(["left_ankle_roll_link", "right_ankle_roll_link"]),
                "body_pos_w": np.zeros((2, 2, 3)),
            })


if __name__ == "__main__":
    unittest.main()
