from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from somaforge_core.contact_schema import encode_contact_force_provenance, newton_contact_provenance
from somaforge_core.robot_assets import encode_robot_asset_json

from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.layers import write_contact_layer
from motion_edit.contact.schema import ContactAnchorRecord
from motion_edit.generation import bake_retargeted_contact_forces_for_motion
from motion_edit.generation.contact_force_bake import validate_wbt_contact_force_policy_ref


_NP_SAVEZ = np.savez


def _savez(path: str | Path, *args: object, **kwargs: object) -> None:
    kwargs.setdefault("robot_asset_json", np.asarray(encode_robot_asset_json()))
    kwargs.setdefault(
        "contact_force_provenance_json",
        np.asarray(
            encode_contact_force_provenance(
                newton_contact_provenance(solver_config={"nconmax_per_env": 64, "njmax_per_env": 512})
            )
        ),
    )
    _NP_SAVEZ(path, *args, **kwargs)


def _load_pickle_free_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


class GenerationContactForceBakeTests(unittest.TestCase):
    def test_retargets_force_phase_to_augmented_contact_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "augmented.npz"
            source_force = root / "source_force.npz"
            output = root / "augmented_force.npz"
            target_mask = np.zeros((9, 8), dtype=bool)
            target_mask[:, 0] = True
            _savez(
                target,
                joint_pos=np.zeros((9, 7), dtype=np.float64),
                joint_vel=np.zeros((9, 6), dtype=np.float64),
                joint_names=np.asarray([], dtype=object),
                body_names=np.asarray(["left_ankle_roll_link"], dtype=object),
                body_pos_w=np.zeros((9, 1, 3), dtype=np.float64),
                body_quat_w=np.tile(np.asarray([1.0, 0.0, 0.0, 0.0]), (9, 1, 1)),
                body_lin_vel_w=np.zeros((9, 1, 3), dtype=np.float64),
                fps=np.asarray(50.0),
                contact_force_part_order=np.asarray(["left_heel", "left_toe", "right_heel", "right_toe", "left_hand", "right_hand", "left_knee", "right_knee"], dtype=object),
                contact_force_part_mask=target_mask,
            )
            source_mask = np.zeros((5, 8), dtype=bool)
            source_mask[:, 0] = True
            source_forces = np.zeros((5, 8, 3), dtype=np.float64)
            source_forces[:, 0, 2] = [0.0, 10.0, 20.0, 10.0, 0.0]
            _savez(
                source_force,
                contact_force_part_order=np.asarray(["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"], dtype=object),
                contact_force_part_mask=source_mask,
                contact_force_part_w=source_forces,
                contact_force_part_position_w=np.zeros((5, 8, 3), dtype=np.float64),
            )

            result = bake_retargeted_contact_forces_for_motion(
                target,
                source_force_ref_path=source_force,
                output_motion_path=output,
                smoothing_window=1,
                overwrite=True,
            )
            with np.load(output, allow_pickle=True) as data:
                force = np.asarray(data["contact_force_part_w"], dtype=np.float64)
                order = data["contact_force_part_order"].tolist()
                self.assertEqual(data["body_ang_vel_w"].shape, (9, 1, 3))
                self.assertNotEqual(data["joint_names"].dtype, object)
                self.assertNotEqual(data["body_names"].dtype, object)
                self.assertNotEqual(data["contact_force_part_order"].dtype, object)
                force_meta = json.loads(str(data["motion_edit_force_metadata"].item()))
            _load_pickle_free_npz(output)
            report = validate_wbt_contact_force_policy_ref(output, require_newton_source=False)

        self.assertEqual(result.output_motion_path, output)
        self.assertEqual(order, ["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"])
        self.assertEqual(force.shape, (9, 8, 3))
        self.assertEqual(int(np.argmax(force[:, 0, 2])), 4)
        self.assertAlmostEqual(float(force[4, 0, 2]), 20.0)
        self.assertAlmostEqual(float(force[0, 0, 2]), 0.0)
        self.assertAlmostEqual(float(force[-1, 0, 2]), 0.0)
        self.assertEqual(force_meta["force_source"], "retargeted_contact_force")
        self.assertFalse(force_meta["force_applied_to_body"])
        self.assertFalse(force_meta["integrated"])
        self.assertEqual(force_meta["matched_phase_count"], 1)
        self.assertEqual(force_meta["derived_motion_fields"], ["body_ang_vel_w"])
        self.assertEqual(report["frames"], 9)

    def test_retarget_rewrites_wrong_width_joint_vel_for_wbt_policy_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "augmented.npz"
            source_force = root / "source_force.npz"
            mask = np.zeros((3, 8), dtype=bool)
            mask[:, 0] = True
            qpos = np.zeros((3, 9), dtype=np.float64)
            qpos[:, 0] = [0.0, 0.1, 0.2]
            qpos[:, 3] = 1.0
            _savez(
                target,
                joint_pos=qpos,
                joint_vel=np.zeros((3, 9), dtype=np.float64),
                joint_names=np.asarray(["hip", "knee"], dtype=object),
                body_names=np.asarray(["left_ankle_roll_link"], dtype=object),
                body_pos_w=np.zeros((3, 1, 3), dtype=np.float64),
                body_quat_w=np.tile(np.asarray([1.0, 0.0, 0.0, 0.0]), (3, 1, 1)),
                body_lin_vel_w=np.zeros((3, 1, 3), dtype=np.float64),
                body_ang_vel_w=np.zeros((3, 1, 3), dtype=np.float64),
                fps=np.asarray(10.0),
                contact_force_part_order=np.asarray(["left_heel", "left_toe", "right_heel", "right_toe", "left_hand", "right_hand", "left_knee", "right_knee"], dtype=object),
                contact_force_part_mask=mask,
            )
            source_forces = np.zeros((3, 8, 3), dtype=np.float64)
            source_forces[:, 0, 2] = [5.0, 6.0, 5.0]
            _savez(
                source_force,
                contact_force_part_order=np.asarray(["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"], dtype=object),
                contact_force_part_mask=mask,
                contact_force_part_w=source_forces,
            )

            bake_retargeted_contact_forces_for_motion(
                target,
                source_force_ref_path=source_force,
                smoothing_window=1,
                overwrite=True,
            )
            with np.load(target, allow_pickle=True) as data:
                self.assertEqual(data["joint_vel"].shape, (3, 8))
                np.testing.assert_allclose(data["joint_vel"][:, 0], [1.0, 1.0, 1.0])
                force_meta = json.loads(str(data["motion_edit_force_metadata"].item()))
            report = validate_wbt_contact_force_policy_ref(target, require_newton_source=False)

        self.assertIn("joint_vel", force_meta["derived_motion_fields"])
        self.assertEqual(report["joint_vel_shape"], (3, 8))

    def test_validator_rejects_object_dtype_policy_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ref = Path(tmp) / "legacy_object_ref.npz"
            _savez(
                ref,
                fps=np.asarray(50.0),
                joint_pos=np.zeros((2, 7), dtype=np.float64),
                joint_vel=np.zeros((2, 6), dtype=np.float64),
                joint_names=np.asarray([], dtype=object),
                body_names=np.asarray(["pelvis"], dtype=object),
                body_pos_w=np.zeros((2, 1, 3), dtype=np.float64),
                body_quat_w=np.tile(np.asarray([1.0, 0.0, 0.0, 0.0]), (2, 1, 1)),
                body_lin_vel_w=np.zeros((2, 1, 3), dtype=np.float64),
                body_ang_vel_w=np.zeros((2, 1, 3), dtype=np.float64),
                contact_force_part_w=np.zeros((2, 8, 3), dtype=np.float64),
                contact_force_part_mask=np.zeros((2, 8), dtype=bool),
                contact_force_part_order=np.asarray(["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"], dtype=object),
            )

            with self.assertRaisesRegex(ValueError, "allow_pickle=False|pickle-free|object-dtype"):
                validate_wbt_contact_force_policy_ref(ref)

    def test_retarget_uses_target_contact_layer_surface_normals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "augmented.npz"
            source_force = root / "source_force.npz"
            layer = root / "layers" / "contact" / "target"
            mask = np.zeros((3, 8), dtype=bool)
            mask[:, 0] = True
            _savez(
                target,
                joint_pos=np.zeros((3, 7), dtype=np.float64),
                joint_vel=np.zeros((3, 6), dtype=np.float64),
                contact_force_part_order=np.asarray(["left_heel", "left_toe", "right_heel", "right_toe", "left_hand", "right_hand", "left_knee", "right_knee"], dtype=object),
                contact_force_part_mask=mask,
            )
            source_forces = np.zeros((3, 8, 3), dtype=np.float64)
            source_forces[:, 0, 2] = [10.0, 20.0, 10.0]
            _savez(
                source_force,
                contact_force_part_order=np.asarray(["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"], dtype=object),
                contact_force_part_mask=mask,
                contact_force_part_w=source_forces,
            )
            write_contact_layer(
                layer,
                ContactGraph(
                    motion_id="motion_a",
                    anchors=[
                        ContactAnchorRecord(
                            motion_id="motion_a",
                            anchor_id="a0",
                            body="left_heel",
                            start_frame=0,
                            end_frame=3,
                            surface_normal=[1.0, 0.0, 0.0],
                        )
                    ],
                ),
            )

            bake_retargeted_contact_forces_for_motion(
                target,
                source_force_ref_path=source_force,
                target_contact_layer_path=layer,
                target_motion_id="motion_a",
                policy_ref_compat="none",
                smoothing_window=1,
                overwrite=True,
            )
            with np.load(target, allow_pickle=True) as data:
                force = np.asarray(data["contact_force_part_w"], dtype=np.float64)
                meta = json.loads(str(data["motion_edit_force_metadata"].item()))

        np.testing.assert_allclose(force[:, 0], [[10.0, 0.0, 0.0], [20.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
        self.assertEqual(meta["target_normal_source"], "contact_layer")
        self.assertEqual(meta["target_normal_frame_count"], 3)

if __name__ == "__main__":
    unittest.main()
