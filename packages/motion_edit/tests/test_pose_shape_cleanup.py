from __future__ import annotations

import numpy as np
import pytest

from motion_edit.generation.pose_shape_cleanup import (
    clean_pose_shape_qpos,
    filtered_pose_seed_arrays,
    pose_shape_plan_payload,
)


def _qpos(frame_count: int = 100) -> np.ndarray:
    phase = np.linspace(0.0, 4.0 * np.pi, frame_count)
    qpos = np.zeros((frame_count, 9), dtype=np.float64)
    qpos[:, 0] = 0.01 * np.sin(phase)
    qpos[:, 2] = 0.8 + 0.02 * np.sin(phase)
    qpos[:, 3] = 1.0
    qpos[frame_count // 2 :, 3] = -1.0
    qpos[:, 7] = np.sin(phase) + 0.1 * np.sin(12.0 * phase)
    qpos[:, 8] = np.cos(phase)
    return qpos


def test_clean_pose_shape_qpos_preserves_endpoints_and_quaternion_norm() -> None:
    source = _qpos()
    cleaned = clean_pose_shape_qpos(source, fps=50.0, cutoff_hz=6.0)

    np.testing.assert_allclose(cleaned[0], source[0], atol=1.0e-12)
    np.testing.assert_allclose(cleaned[-1], source[-1], atol=1.0e-12)
    np.testing.assert_allclose(
        np.linalg.norm(cleaned[:, 3:7], axis=1),
        1.0,
        atol=1.0e-12,
    )
    adjacent_quaternion_dot = np.sum(
        cleaned[:-1, 3:7] * cleaned[1:, 3:7],
        axis=1,
    )
    np.testing.assert_allclose(
        np.abs(adjacent_quaternion_dot),
        1.0,
        atol=1.0e-12,
    )


def test_filtered_pose_seed_contains_only_q_seed_contract(tmp_path) -> None:
    source_path = tmp_path / "rollout.npz"
    source = {
        "fps": np.asarray(50.0, dtype=np.float32),
        "joint_pos": _qpos(),
        "joint_names": np.asarray(["joint_a", "joint_b"]),
        "robot_asset_json": np.asarray('{"schema":"robot_asset_v1"}'),
        "raw_contact_force_w": np.ones((100, 1, 3)),
    }

    seed = filtered_pose_seed_arrays(source, source_path=source_path)

    assert set(seed) == {
        "fps",
        "joint_pos",
        "joint_names",
        "robot_asset_json",
        "cleanup_source_motion",
        "cleanup_filter",
        "cleanup_cutoff_hz",
    }
    assert "raw_contact_force_w" not in seed
    assert seed["cleanup_filter"].item() == "zero_phase_butterworth_order4"


def test_pose_shape_plan_keeps_force_rollout_as_contact_authority(
    tmp_path,
) -> None:
    force_rollout = tmp_path / "force_rollout.npz"
    canonical = tmp_path / "clean_6hz_newton.npz"
    template = {
        "source_motion_path": "/old/pose.npz",
        "metadata": {
            "contact_force_source_path": str(force_rollout),
            "task_variant": "obstacle_height",
        },
    }

    plan = pose_shape_plan_payload(
        template,
        rollout_path=force_rollout,
        canonical_motion_path=canonical,
        cutoff_hz=6.0,
    )

    assert plan["source_motion_path"] == str(canonical.resolve())
    cleanup = plan["metadata"]["kinematic_cleanup"]
    assert cleanup["source_motion"] == str(force_rollout.resolve())
    assert cleanup["canonical_motion"] == str(canonical.resolve())
    assert cleanup["contact_authority"] == str(force_rollout.resolve())
    assert plan["metadata"]["contact_force_source_path"] == str(force_rollout)


def test_pose_shape_plan_requires_contact_force_authority(tmp_path) -> None:
    with pytest.raises(ValueError, match="contact_force_source_path"):
        pose_shape_plan_payload(
            {"metadata": {}},
            rollout_path=tmp_path / "rollout.npz",
            canonical_motion_path=tmp_path / "canonical.npz",
        )
