from __future__ import annotations

import json

import numpy as np
import pytest
from motion_edit.contact_force.frame_boundary_replay import (
    build_force_policy_reference,
    reduce_sensor_force_parts,
    stable_contact_masks,
    validate_frame_boundary_replay,
)
from somaforge_core.contact_schema import (
    CONTACT_FORCE_PART_ORDER,
    decode_contact_force_provenance,
)
from somaforge_core.motion_schema import (
    G1_29DOF_JOINT_ORDER,
    direct_newton_kinematics_provenance,
    encode_kinematics_provenance,
)
from somaforge_core.robot_assets import encode_robot_asset_json


def _replay(force: np.ndarray) -> dict[str, np.ndarray]:
    raw, stable = stable_contact_masks(
        force,
        on_threshold=10.0,
        off_threshold=5.0,
        close_gap_frames=2,
    )
    valid = np.ones(force.shape[0], dtype=bool)
    valid[0] = False
    return {
        "contact_force_part_w": force,
        "contact_force_part_mask": stable,
        "contact_force_part_mask_raw": raw,
        "contact_force_part_order": np.asarray(CONTACT_FORCE_PART_ORDER),
        "contact_force_frame_valid": valid,
        "metadata_json": np.asarray(
            json.dumps(
                {
                    "boundary_state_source": "command_motion",
                    "control_mode": "recorded_torques",
                    "force_sampling": "latest_physics_step",
                    "state_policy": "frame_boundary_playback",
                }
            )
        ),
    }


def _kinematics(frames: int) -> dict[str, np.ndarray]:
    body_names = ["pelvis"]
    provenance = direct_newton_kinematics_provenance(
        source_path="/tmp/source.npz",
        source_sha256="abc",
        output_fps=50.0,
        body_names=body_names,
    )
    return {
        "fps": np.asarray([50.0], dtype=np.float32),
        "joint_pos": np.zeros((frames, 36), dtype=np.float32),
        "joint_vel": np.zeros((frames, 35), dtype=np.float32),
        "body_pos_w": np.zeros((frames, 1, 3), dtype=np.float32),
        "body_quat_w": np.tile(
            np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float32),
            (frames, 1, 1),
        ),
        "body_lin_vel_w": np.zeros((frames, 1, 3), dtype=np.float32),
        "body_ang_vel_w": np.zeros((frames, 1, 3), dtype=np.float32),
        "joint_names": np.asarray(G1_29DOF_JOINT_ORDER),
        "body_names": np.asarray(body_names),
        "robot_asset_json": np.asarray(encode_robot_asset_json()),
        "kinematics_provenance_json": np.asarray(
            encode_kinematics_provenance(provenance)
        ),
    }


def test_stable_contact_masks_close_only_short_internal_gaps() -> None:
    force = np.zeros((8, 1, 3), dtype=np.float32)
    force[[1, 2, 5, 6], 0, 2] = 12.0
    raw, stable = stable_contact_masks(
        force,
        on_threshold=10.0,
        off_threshold=5.0,
        close_gap_frames=2,
    )
    assert raw[:, 0].tolist() == [False, True, True, False, False, True, True, False]
    assert stable[:, 0].tolist() == [False, True, True, True, True, True, True, False]


def test_reduce_sensor_force_parts_separates_heel_and_toe() -> None:
    names = [
        "left_ankle_roll_sphere_1_link",
        "left_ankle_roll_sphere_2_link",
        "left_ankle_roll_sphere_5_link",
        "left_knee_link",
    ]
    force = np.zeros((len(names), 3), dtype=np.float32)
    force[:, 2] = [3.0, 4.0, 11.0, 7.0]
    reduced = reduce_sensor_force_parts(force, names)
    assert reduced.shape == (8, 3)
    assert reduced[0, 2] == pytest.approx(7.0)
    assert reduced[1, 2] == pytest.approx(11.0)
    assert reduced[6, 2] == pytest.approx(7.0)


def test_replay_contract_rejects_force_migration() -> None:
    replay = _replay(np.zeros((3, 8, 3), dtype=np.float32))
    metadata = json.loads(str(replay["metadata_json"].item()))
    metadata["control_mode"] = "migrated_reference_force"
    replay["metadata_json"] = np.asarray(json.dumps(metadata))
    with pytest.raises(ValueError, match="contract mismatch"):
        validate_frame_boundary_replay(replay, expected_frames=3)


def test_policy_reference_contains_only_calculated_newton_force() -> None:
    force = np.zeros((4, 8, 3), dtype=np.float32)
    force[1:, 1, 2] = [12.0, 8.0, 3.0]
    output = build_force_policy_reference(
        kinematics=_kinematics(4),
        replay=_replay(force),
        recording_metadata={
            "newton_solver_config": {
                "solver": "mjwarp",
                "collision_pipeline": "newton",
                "sim_dt": 0.005,
                "control_decimation": 4,
            }
        },
        recording_path="/tmp/rollout_recording.npz",
        kinematics_path="/tmp/edited_kinematics.npz",
    )
    assert np.array_equal(output["contact_force_part_w"], force)
    assert not any(name.startswith("raw_contact_") for name in output)
    assert all(np.asarray(value).dtype != object for value in output.values())
    provenance = decode_contact_force_provenance(
        output["contact_force_provenance_json"],
        context="test policy reference",
        require_newton=True,
    )
    assert provenance["reference_force_migration"] is False
    assert provenance["raw_contact_persisted"] is False
    assert provenance["playback_contract"].startswith("authoritative_20ms")
