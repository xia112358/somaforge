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
from motion_edit.contact.generation import apply_contact_edit_plan_to_motion, resolve_body_index
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
            "left_ankle_roll_sphere_1_link",
            "left_ankle_roll_sphere_2_link",
            "left_ankle_roll_sphere_3_link",
            "left_ankle_roll_sphere_4_link",
            "left_ankle_roll_sphere_5_link",
            "right_ankle_roll_sphere_1_link",
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

        np.testing.assert_array_equal(generated["contact_force_part_w"], forces)
        np.testing.assert_allclose(
            np.asarray(generated["contact_force_part_position_w"])[1:4, 5],
            [[0.1, 0.2, 0.0]] * 3,
        )
        np.testing.assert_allclose(
            np.asarray(generated["contact_force_part_position_history_w"])[1:4, :, 5],
            np.broadcast_to([0.1, 0.2, 0.0], (3, 2, 3)),
        )
        self.assertNotIn("raw_contact_point0_w", generated)
        self.assertEqual(
            str(generated["contact_force_part_position_source"]),
            "motion_edit_translated_source_contact_position",
        )
        provenance = json.loads(str(generated["contact_force_provenance_json"]))
        self.assertEqual(
            provenance["motion_edit_contact_position_translation"][0]["part"],
            "right_hand",
        )

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
                mode="lte_windowed",
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
            metadata = json.loads(generated["motion_edit_generation_metadata"].item())
            self.assertEqual(metadata["generation_mode"], "lte_windowed")
            edited_graph = cli.read_contact_graph(root / "layers" / "contact" / "generated", "motion_a")
            self.assertEqual(edited_graph.anchors[0].world_position, [0.2, 0.0, 0.0])
            self.assertEqual(edited_graph.anchors[0].surface_id, "platform_top")
            self.assertEqual(edited_graph.anchors[0].position_source, "motion_edit_generated")
            self.assertEqual(edited_graph.anchors[0].metadata["surface_editor_status"], "edited")
            binding = edited_graph.anchors[0].metadata["surface_bindings"][-1]
            self.assertEqual(binding["bound_world_position"], [0.2, 0.0, 0.0])
            self.assertEqual(binding["surface_coordinates"], {"u": 0.2, "v": 0.0})
            segments = read_layer(root / "layers" / "candidates" / "generated" / "motion_a.jsonl", default_source="lte_windowed", default_status="candidate")
            self.assertTrue(segments)

    def test_dense_taskspace_maps_contact_point_names_to_feet(self) -> None:
        from motion_edit.generation.lte_fullbody import _semantic_body_weights

        weights = _semantic_body_weights(["left_foot_contact_point", "right_foot_contact_point"], ["pelvis", "torso", "left_hand", "right_hand", "left_foot", "right_foot"])

        self.assertEqual(float(weights[0, 4]), 1.0)
        self.assertEqual(float(weights[1, 5]), 1.0)

    def test_generate_lte_augmentation_dry_run_and_overwrite_safety(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source_motion, _plan_path, plan = _write_synthetic_motion_and_contact(root)
            output = root / "out.npz"
            output.write_bytes(b"existing")

            result = apply_contact_edit_plan_to_motion(
                plan,
                output_motion_path=output,
                mode="lte_windowed",
                dry_run=True,
                layers_root=root / "layers",
            )
            self.assertEqual(result.output_motion_path, output)
            self.assertEqual(output.read_bytes(), b"existing")
            with self.assertRaises(FileExistsError):
                apply_contact_edit_plan_to_motion(plan, output_motion_path=output, mode="lte_windowed", layers_root=root / "layers")

    def test_generate_lte_augmentation_composes_multiple_edits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source_motion, _plan_path, plan = _write_synthetic_motion_and_contact(root)
            second = ContactAnchorEditRecord(
                **{
                    **plan.edits[0],
                    "edit_id": "edit_1",
                    "old_world_position": [0.2, 0.0, 0.0],
                    "new_world_position": [0.3, 0.0, 0.0],
                    "delta_world": [0.1, 0.0, 0.0],
                    "surface_coordinates_before": {"u": 0.2, "v": 0.0},
                    "surface_coordinates_after": {"u": 0.3, "v": 0.0},
                }
            )
            composed = ContactEditPlan(
                plan_id=plan.plan_id,
                source_motion_path=plan.source_motion_path,
                source_motion_id=plan.source_motion_id,
                source_contact_layer=plan.source_contact_layer,
                edits=[*plan.edits, second.to_dict()],
                status="validated",
            )
            output = root / "composed.npz"

            apply_contact_edit_plan_to_motion(
                composed,
                output_motion_path=output,
                mode="lte_windowed",
                falloff_before=0,
                falloff_after=0,
                global_weight=0.0,
                layers_root=root / "layers",
            )
            body_pos = np.load(output, allow_pickle=True)["body_pos_w"]

        np.testing.assert_allclose(body_pos[2:5, 0, 0], 0.3)

    def test_resolve_body_index_maps_contact_parts_to_holosoma_links(self) -> None:
        motion = {
            "body_names": np.asarray(
                [
                    "world",
                    "pelvis",
                    "left_ankle_roll_sphere_1_link",
                    "left_ankle_roll_link",
                    "right_ankle_roll_sphere_1_link",
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
            "left_ankle_roll_sphere_1_link",
            "right_hip_roll_link",
            "right_knee_link",
            "right_ankle_roll_link",
            "right_ankle_roll_sphere_1_link",
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

        np.testing.assert_allclose(keypoints["left_toe"][0], part_positions[0, 1])
        self.assertTrue(np.isfinite(keypoints["left_toe"]).all())
        self.assertFalse(np.allclose(keypoints["left_toe"][1], np.zeros(3)))
        self.assertEqual(keypoints["right_toe"].shape, (frames, 3))

    def test_real_newton_rollout_resolves_all_eight_contact_trajectories(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        motion_path = repo_root / "runtime/current/motions/newton_contact_force/climb_01_rollout_ref_contact_force.npz"
        if not motion_path.is_file():
            self.skipTest("canonical climb_01 Newton rollout is not installed")
        with np.load(motion_path, allow_pickle=True) as source:
            motion = {key: source[key] for key in source.files}
        keypoints = _semantic_keypoints_from_motion(motion)
        for part_name in (
            "left_heel",
            "left_toe",
            "right_heel",
            "right_toe",
            "left_hand",
            "right_hand",
            "left_knee",
            "right_knee",
        ):
            self.assertEqual(keypoints[part_name].shape, (870, 3))
            self.assertTrue(np.isfinite(keypoints[part_name]).all())

    def test_generate_lte_augmentation_accepts_semantic_contact_body_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_motion, _plan_path, plan = _write_synthetic_motion_and_contact(root)
            with np.load(source_motion, allow_pickle=True) as source:
                payload = {key: source[key] for key in source.files}
            body_pos = np.zeros((8, 3, 3), dtype=np.float32)
            payload["body_pos_w"] = body_pos
            payload["body_lin_vel_w"] = np.zeros_like(body_pos)
            payload["body_quat_w"] = np.zeros((8, 3, 4), dtype=np.float32)
            payload["body_quat_w"][..., 0] = 1.0
            payload["body_names"] = np.asarray(
                ["pelvis", "left_ankle_roll_sphere_1_link", "torso_link"],
                dtype=object,
            )
            semantic_motion = root / "semantic_motion.npz"
            _savez(semantic_motion, **payload)
            semantic_plan = ContactEditPlan(
                plan_id=plan.plan_id,
                source_motion_path=str(semantic_motion),
                source_motion_id=plan.source_motion_id,
                source_contact_layer=plan.source_contact_layer,
                edits=plan.edits,
                status=plan.status,
            )
            output = root / "semantic_out.npz"

            apply_contact_edit_plan_to_motion(
                semantic_plan,
                output_motion_path=output,
                mode="lte_windowed",
                falloff_before=0,
                falloff_after=0,
                global_weight=0.0,
                layers_root=root / "layers",
            )
            generated = np.load(output, allow_pickle=True)["body_pos_w"]

        np.testing.assert_allclose(generated[2:5, 1, 0], 0.2)
        np.testing.assert_allclose(generated[:, 0, :], 0.0)

    def test_lte_fullbody_generates_taskspace_and_merges_ik_output(self) -> None:
        class FakeLegacyLte:
            @staticmethod
            def deform_demo_with_contact_handles_lte(keypoints, handles, weights=None, config=None):
                edited = {name: value.copy() for name, value in keypoints.items()}
                for handle in handles:
                    frames = np.asarray(handle["frames"], dtype=np.int64)
                    edited[handle["name"]][frames] = np.asarray(handle["target"], dtype=np.float64)
                return {"edited_keypoints": edited, "debug": {"fake": True}}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _motion, plan = _write_fullbody_lte_source(root)
            output = root / "fullbody_out.npz"
            intermediate = root / "intermediate"

            def fake_run(cmd, cwd=None, env=None, check=False):
                ik_out = Path(cmd[cmd.index("--out") + 1])
                _savez(
                    ik_out,
                    joint_pos=np.full((8, 10), 9.0, dtype=np.float32),
                    joint_vel=np.full((8, 10), 2.0, dtype=np.float32),
                    joint_names=np.asarray(["j0", "j1", "j2"], dtype=object),
                    is_qpos=np.asarray(True),
                )
                return mock.Mock(returncode=0)

            with mock.patch("motion_edit.generation.lte_fullbody._import_legacy_lte_module", return_value=FakeLegacyLte):
                with mock.patch("motion_edit.generation.lte_fullbody.subprocess.run", side_effect=fake_run) as run_mock:
                    result = apply_contact_edit_plan_to_motion(
                        plan,
                        output_motion_path=output,
                        mode="lte_fullbody",
                        output_contact_layer="contact/fullbody_generated",
                        output_segment_layer="candidates/fullbody_generated",
                        intermediate_dir=intermediate,
                        layers_root=root / "layers",
                    )
            generated = np.load(output, allow_pickle=True)
            edited_graph = cli.read_contact_graph(root / "layers" / "contact" / "fullbody_generated", "motion_a")
            segments = read_layer(
                root / "layers" / "candidates" / "fullbody_generated" / "motion_a.jsonl",
                default_source="lte_fullbody",
                default_status="candidate",
            )
            self.assertEqual(result.output_motion_path, output)
            self.assertTrue((intermediate / "fullbody_out.lte_keypoints.npz").exists())
            self.assertTrue((intermediate / "fullbody_out.taskspace_motion.npz").exists())
            self.assertEqual(run_mock.call_args.kwargs["check"], True)
            cmd = run_mock.call_args.args[0]
            self.assertIn("--contact-foot-orientation-weight", cmd)
            self.assertIn("--contact-foot-toe-weight", cmd)
            lte = np.load(intermediate / "fullbody_out.lte_keypoints.npz", allow_pickle=True)
            self.assertIn("orientation_target_left_foot", lte.files)
            self.assertIn("orientation_target_right_foot", lte.files)
            np.testing.assert_allclose(generated["joint_pos"], 9.0)
            self.assertIn("body_pos_w", generated.files)
            self.assertIn("lte_fullbody", generated["motion_edit_generation_metadata"].item())
            self.assertEqual(edited_graph.anchors[0].world_position, [3.2, 0.0, 0.0])
            self.assertTrue(segments)
            self.assertTrue(all(segment.source == "lte_fullbody" for segment in segments))
            self.assertTrue(all(segment.metadata.get("cut_source") == "lte_fullbody" for segment in segments))

    def test_lte_fullbody_dry_run_writes_no_intermediates(self) -> None:
        class FakeLegacyLte:
            @staticmethod
            def deform_demo_with_contact_handles_lte(keypoints, handles, weights=None, config=None):
                return {"edited_keypoints": {name: value.copy() for name, value in keypoints.items()}, "debug": {}}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _motion, plan = _write_fullbody_lte_source(root)
            intermediate = root / "intermediate"
            with mock.patch("motion_edit.generation.lte_fullbody._import_legacy_lte_module", return_value=FakeLegacyLte):
                with mock.patch("motion_edit.generation.lte_fullbody.subprocess.run") as run_mock:
                    result = apply_contact_edit_plan_to_motion(
                        plan,
                        output_motion_path=root / "out.npz",
                        mode="lte_fullbody",
                        dry_run=True,
                        intermediate_dir=intermediate,
                        layers_root=root / "layers",
                    )

            self.assertFalse(intermediate.exists())
            self.assertFalse((root / "out.npz").exists())
            run_mock.assert_not_called()
            self.assertIn("would run fullbody IK", "\n".join(result.warnings or []))

    def test_lte_fullbody_adds_fixed_handles_for_unedited_contacts(self) -> None:
        captured = {}

        class FakeLegacyLte:
            @staticmethod
            def deform_demo_with_contact_handles_lte(keypoints, handles, weights=None, config=None):
                captured["handles"] = list(handles)
                edited = {name: value.copy() for name, value in keypoints.items()}
                for handle in handles:
                    frames = np.asarray(handle["frames"], dtype=np.int64)
                    edited[handle["name"]][frames] = np.asarray(handle["target"], dtype=np.float64)
                return {"edited_keypoints": edited, "debug": {"fake": True}}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _motion, plan = _write_fullbody_lte_source(root)
            graph = cli.read_contact_graph(root / "layers" / "contact" / "force_contact", "motion_a")
            graph = ContactGraph(
                motion_id=graph.motion_id,
                anchors=[
                    *graph.anchors,
                    ContactAnchorRecord(
                        motion_id="motion_a",
                        anchor_id="anchor_lh",
                        body="left_hand",
                        start_frame=2,
                        end_frame=5,
                        world_position=[10.0, 0.0, 0.0],
                        surface_id="platform_top",
                    ),
                ],
            )
            write_contact_layer(root / "layers" / "contact" / "force_contact", graph)

            def fake_run(cmd, cwd=None, env=None, check=False):
                ik_out = Path(cmd[cmd.index("--out") + 1])
                _savez(ik_out, joint_pos=np.zeros((8, 10), dtype=np.float32), joint_vel=np.zeros((8, 10), dtype=np.float32))
                return mock.Mock(returncode=0)

            with mock.patch("motion_edit.generation.lte_fullbody._import_legacy_lte_module", return_value=FakeLegacyLte):
                with mock.patch("motion_edit.generation.lte_fullbody.subprocess.run", side_effect=fake_run):
                    apply_contact_edit_plan_to_motion(
                        plan,
                        output_motion_path=root / "out.npz",
                        mode="lte_fullbody",
                        intermediate_dir=root / "intermediate",
                        layers_root=root / "layers",
                    )

        kinds = [handle.get("kind") for handle in captured["handles"]]
        self.assertIn("edited_contact", kinds)
        self.assertIn("fixed_contact", kinds)
        fixed = [handle for handle in captured["handles"] if handle.get("anchor_id") == "anchor_lh"][0]
        self.assertEqual(fixed["name"], "left_hand")

    def test_batch_contact_laplacian_backend_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _motion, plan = _write_fullbody_lte_source(root)
            result = apply_contact_edit_plan_to_motion(
                plan,
                output_motion_path=root / "out.npz",
                mode="lte_fullbody",
                fullbody_solver="batch_contact_laplacian",
                dry_run=True,
                layers_root=root / "layers",
            )

        self.assertFalse((root / "out.npz").exists())
        self.assertIn("batch contact-Laplacian", "\n".join(result.warnings or []))

    def test_batch_contact_laplacian_proxy_only_writes_proxy_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _motion, plan = _write_fullbody_lte_source(root)
            output = root / "out.npz"
            with mock.patch("motion_edit.generation.lte_fullbody.subprocess.run") as run_mock:
                result = apply_contact_edit_plan_to_motion(
                    plan,
                    output_motion_path=output,
                    mode="lte_fullbody",
                    fullbody_solver="batch_contact_laplacian",
                    mesh_laplacian_weight=1.0,
                    contact_laplacian_trust=1.0,
                    contact_laplacian_proxy_only=True,
                    layers_root=root / "layers",
                )
            generated = np.load(output, allow_pickle=True)
            metadata = json.loads(generated["motion_edit_generation_metadata"].item())

        self.assertEqual(result.output_motion_path, output)
        self.assertIn("body_pos_w", generated.files)
        self.assertIn("experimental body_pos_w proxy", "\n".join(result.warnings or []))
        run_mock.assert_not_called()
        self.assertEqual(metadata["fullbody_solver"], "batch_contact_laplacian")
        self.assertEqual(metadata["proxy_kinematics"], "body_pos_w_semantic_points")
        self.assertEqual(metadata["output_kind"], "bodyspace_proxy_only")

    def test_batch_contact_laplacian_writes_internal_generated_motion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _motion, plan = _write_fullbody_lte_source(root)
            output = root / "out.npz"
            intermediate = root / "intermediate"

            def fake_run(cmd, cwd=None, env=None, check=False):
                ik_out = Path(cmd[cmd.index("--out") + 1])
                _savez(
                    ik_out,
                    joint_pos=np.full((8, 10), 7.0, dtype=np.float32),
                    joint_vel=np.full((8, 10), 3.0, dtype=np.float32),
                    joint_names=np.asarray(["j0", "j1", "j2"], dtype=object),
                    is_qpos=np.asarray(True),
                    ik_backend=np.asarray("pyroki_internal"),
                )
                return mock.Mock(returncode=0)

            with mock.patch("motion_edit.generation.lte_fullbody.subprocess.run", side_effect=fake_run) as run_mock:
                result = apply_contact_edit_plan_to_motion(
                    plan,
                    output_motion_path=output,
                    mode="lte_fullbody",
                    fullbody_solver="batch_contact_laplacian",
                    mesh_laplacian_weight=1.0,
                    contact_laplacian_trust=1.0,
                    output_segment_layer="candidates/batch_generated",
                    intermediate_dir=intermediate,
                    layers_root=root / "layers",
                )
            generated = np.load(output, allow_pickle=True)
            metadata = json.loads(generated["motion_edit_generation_metadata"].item())
            segments = read_layer(
                root / "layers" / "candidates" / "batch_generated" / "motion_a.jsonl",
                default_source="lte_fullbody",
                default_status="candidate",
            )

            self.assertEqual(result.output_motion_path, output)
            self.assertTrue((intermediate / "out.contact_laplacian_keypoints.npz").exists())
            self.assertTrue((intermediate / "out.contact_laplacian_taskspace_motion.npz").exists())
            self.assertTrue((intermediate / "out.contact_laplacian_fullbody_ik_motion.npz").exists())
            self.assertEqual(run_mock.call_args.kwargs["check"], True)
            self.assertIn("-m", run_mock.call_args.args[0])
            self.assertIn("motion_edit.generation.pyroki_fullbody_ik", run_mock.call_args.args[0])
            self.assertIn("body_pos_w", generated.files)
            self.assertIn("joint_pos", generated.files)
            np.testing.assert_allclose(generated["joint_pos"], 7.0)
            self.assertEqual(metadata["output_kind"], "fullbody_ik_after_contact_laplacian_proxy")
            self.assertEqual(metadata["joint_consistency"], "fullbody_ik_subprocess")
            self.assertEqual(metadata["ik_backend"], "pyroki_internal")
            self.assertEqual(metadata["fullbody_solver"], "batch_contact_laplacian")
            self.assertIn("solver_metadata", metadata)
            self.assertIn("interaction_mesh", metadata["solver_metadata"])
            self.assertIn("evaluation_summary", metadata)
            self.assertTrue(segments)
            self.assertTrue(all(segment.source == "lte_fullbody" for segment in segments))
            self.assertTrue(all(segment.metadata.get("fullbody_solver") == "batch_contact_laplacian" for segment in segments))
            self.assertFalse(any(segment.metadata.get("cut_source") == "lte_windowed" for segment in segments))

    def test_batch_contact_laplacian_does_not_require_external_ik(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _motion, plan = _write_fullbody_lte_source(root)

            def fake_run(cmd, cwd=None, env=None, check=False):
                ik_out = Path(cmd[cmd.index("--out") + 1])
                _savez(
                    ik_out,
                    joint_pos=np.zeros((8, 10), dtype=np.float32),
                    joint_vel=np.zeros((8, 10), dtype=np.float32),
                    ik_backend=np.asarray("pyroki_internal"),
                )
                return mock.Mock(returncode=0)

            with mock.patch("motion_edit.generation.lte_fullbody.subprocess.run", side_effect=fake_run) as run_mock:
                result = apply_contact_edit_plan_to_motion(
                    plan,
                    output_motion_path=root / "out.npz",
                    mode="lte_fullbody",
                    fullbody_solver="batch_contact_laplacian",
                    layers_root=root / "layers",
                )

            self.assertEqual(result.output_motion_path, root / "out.npz")
            self.assertTrue((root / "out.npz").exists())
            cmd = run_mock.call_args.args[0]
            self.assertIn("-m", cmd)
            self.assertIn("motion_edit.generation.pyroki_fullbody_ik", cmd)
            self.assertNotIn("/home/xiaz/lte/scripts/solve_lte_fullbody_ik.py", cmd)

    def test_generate_lte_augmentation_can_register_motion_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source_motion, _plan_path, plan = _write_synthetic_motion_and_contact(root)
            with mock.patch("motion_edit.generation.lte_fullbody.write_motion_version") as write_version:
                apply_contact_edit_plan_to_motion(
                    plan,
                    output_motion_path=root / "versioned.npz",
                    mode="lte_windowed",
                    output_motion_version_id="motion_a_aug",
                    output_contact_layer="contact/generated",
                    register_motion_version=True,
                    layers_root=root / "layers",
                )
            record = write_version.call_args.args[0]

        self.assertEqual(record.motion_version_id, "motion_a_aug")
        self.assertEqual(record.kind, "augmented")
        self.assertEqual(record.base_motion_id, "motion_a")
        self.assertEqual(record.contact_layer, "contact/generated")

    def test_generate_lte_augmentation_requires_body_pos_and_body_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source_motion, _plan_path, plan = _write_synthetic_motion_and_contact(root)
            missing_body_pos = root / "missing_body_pos.npz"
            _savez(missing_body_pos, joint_pos=np.zeros((4, 3), dtype=np.float32))
            plan_missing = ContactEditPlan(
                plan_id=plan.plan_id,
                source_motion_path=str(missing_body_pos),
                source_motion_id=plan.source_motion_id,
                source_contact_layer=plan.source_contact_layer,
                edits=plan.edits,
                status=plan.status,
            )
            with self.assertRaisesRegex(ValueError, "requires body_pos_w"):
                apply_contact_edit_plan_to_motion(plan_missing, output_motion_path=root / "out.npz", mode="lte_windowed", layers_root=root / "layers")

            no_names = root / "no_names.npz"
            _savez(no_names, body_pos_w=np.zeros((8, 2, 3), dtype=np.float32))
            plan_no_names = ContactEditPlan(
                plan_id=plan.plan_id,
                source_motion_path=str(no_names),
                source_motion_id=plan.source_motion_id,
                source_contact_layer=plan.source_contact_layer,
                edits=plan.edits,
                status=plan.status,
            )
            with self.assertRaisesRegex(ValueError, "cannot resolve body index"):
                apply_contact_edit_plan_to_motion(plan_no_names, output_motion_path=root / "out.npz", mode="lte_windowed", layers_root=root / "layers")

    def test_generate_lte_augmentation_refuses_draft_plan_in_backend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _source_motion, _plan_path, plan = _write_synthetic_motion_and_contact(root, plan_status="draft")

            with self.assertRaisesRegex(ValueError, "must be validated or locked"):
                apply_contact_edit_plan_to_motion(plan, output_motion_path=root / "out.npz", mode="lte_windowed", layers_root=root / "layers")


if __name__ == "__main__":
    unittest.main()
