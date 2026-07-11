from __future__ import annotations

import numpy as np
import pytest
from somaforge_core.kinematics import (
    POSE_FINITE_DIFFERENCE,
    body_velocities_from_pose,
    validate_pose_velocity_consistency,
    validate_root_body_consistency,
)
from somaforge_core.motion_schema import (
    G1_29DOF_JOINT_ORDER,
    decode_kinematics_provenance,
    encode_kinematics_provenance,
    newton_kinematics_provenance,
)


def test_newton_kinematics_provenance_round_trip() -> None:
    metadata = newton_kinematics_provenance(
        source_path="motion.npz",
        source_sha256="a" * 64,
        output_fps=50.0,
        body_names=["pelvis"],
    )
    decoded = decode_kinematics_provenance(encode_kinematics_provenance(metadata), context="test motion")
    assert tuple(decoded["joint_order"]) == G1_29DOF_JOINT_ORDER
    assert decoded["body_names"] == ["pelvis"]
    assert decoded["velocity_derivation"] == POSE_FINITE_DIFFERENCE


def test_body_velocities_are_derived_from_pose() -> None:
    fps = 10.0
    times = np.arange(5, dtype=np.float32) / fps
    body_pos = np.zeros((5, 2, 3), dtype=np.float32)
    body_pos[..., 0] = times[:, None]
    angles = 0.5 * times
    body_quat = np.zeros((5, 2, 4), dtype=np.float32)
    body_quat[..., 0] = np.cos(angles[:, None] / 2.0)
    body_quat[..., 3] = np.sin(angles[:, None] / 2.0)

    body_lin_vel, body_ang_vel = body_velocities_from_pose(body_pos, body_quat, fps)

    np.testing.assert_allclose(body_lin_vel[..., 0], 1.0, atol=1.0e-6)
    np.testing.assert_allclose(body_ang_vel[..., 2], 0.5, atol=1.0e-5)
    validate_pose_velocity_consistency(body_pos, body_quat, body_lin_vel, body_ang_vel, fps)


def test_pose_velocity_validation_rejects_inconsistent_velocity() -> None:
    body_pos = np.zeros((3, 1, 3), dtype=np.float32)
    body_quat = np.zeros((3, 1, 4), dtype=np.float32)
    body_quat[..., 0] = 1.0
    body_lin_vel, body_ang_vel = body_velocities_from_pose(body_pos, body_quat, 50.0)
    body_lin_vel[1, 0, 0] = 1.0

    with pytest.raises(ValueError, match="linear velocity is inconsistent"):
        validate_pose_velocity_consistency(body_pos, body_quat, body_lin_vel, body_ang_vel, 50.0)


def test_root_body_consistency_accepts_quaternion_sign_flip() -> None:
    joint_pos = np.zeros((2, 8), dtype=np.float32)
    joint_pos[:, :3] = [[1.0, 2.0, 3.0], [2.0, 3.0, 4.0]]
    joint_pos[:, 3] = 1.0
    body_pos = joint_pos[:, None, :3].copy()
    body_quat = np.zeros((2, 1, 4), dtype=np.float32)
    body_quat[:, 0, 0] = [-1.0, 1.0]

    validate_root_body_consistency(joint_pos, body_pos, body_quat)


def test_root_body_consistency_rejects_stale_fk_pose() -> None:
    joint_pos = np.zeros((2, 8), dtype=np.float32)
    joint_pos[:, 3] = 1.0
    joint_pos[1, 0] = 0.1
    body_pos = np.zeros((2, 1, 3), dtype=np.float32)
    body_quat = np.zeros((2, 1, 4), dtype=np.float32)
    body_quat[:, 0, 0] = 1.0

    with pytest.raises(ValueError, match="root body position is inconsistent"):
        validate_root_body_consistency(joint_pos, body_pos, body_quat)
