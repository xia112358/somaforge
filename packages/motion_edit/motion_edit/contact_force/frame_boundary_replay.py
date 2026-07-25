"""Contracts for Newton frame-boundary force replay and policy references."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from somaforge_core.contact_schema import (
    CONTACT_FORCE_PART_BODY_NAMES,
    CONTACT_FORCE_PART_ORDER,
    encode_contact_force_provenance,
    newton_contact_provenance,
)
from somaforge_core.motion_schema import decode_kinematics_provenance
from somaforge_core.robot_assets import decode_robot_asset_json


POLICY_MOTION_FIELDS = (
    "fps",
    "joint_pos",
    "joint_vel",
    "body_pos_w",
    "body_quat_w",
    "body_lin_vel_w",
    "body_ang_vel_w",
    "joint_names",
    "body_names",
    "robot_asset_json",
    "kinematics_provenance_json",
)

FRAME_BOUNDARY_REPLAY_CONTRACT = {
    "boundary_state_source": "command_motion",
    "control_mode": "recorded_torques",
    "force_sampling": "latest_physics_step",
    "state_policy": "frame_boundary_playback",
}


def stable_contact_masks(
    force: np.ndarray,
    *,
    on_threshold: float,
    off_threshold: float,
    close_gap_frames: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return raw and hysteresis-stabilized masks for ``[T, P, 3]`` force."""

    if not 0.0 <= off_threshold <= on_threshold:
        raise ValueError("contact thresholds must satisfy 0 <= off <= on")
    if close_gap_frames < 0:
        raise ValueError("close_gap_frames must be nonnegative")
    values = np.asarray(force)
    if values.ndim != 3 or values.shape[-1] != 3:
        raise ValueError("force must have shape [T, P, 3]")
    magnitude = np.linalg.norm(values, axis=-1)
    raw = magnitude > on_threshold
    stable = np.zeros_like(raw)
    active = np.zeros(raw.shape[1], dtype=bool)
    for frame in range(raw.shape[0]):
        active = np.where(active, magnitude[frame] > off_threshold, raw[frame])
        stable[frame] = active
    if close_gap_frames:
        for part in range(stable.shape[1]):
            part_mask = stable[:, part]
            start = 0
            while start < part_mask.size:
                end = start + 1
                while end < part_mask.size and part_mask[end] == part_mask[start]:
                    end += 1
                if (
                    not part_mask[start]
                    and start > 0
                    and end < part_mask.size
                    and end - start <= close_gap_frames
                ):
                    part_mask[start:end] = True
                start = end
    return raw, stable


def reduce_sensor_force_parts(
    sensor_force: np.ndarray,
    sensor_body_names: Sequence[str],
) -> np.ndarray:
    """Reduce one or more sensor-force samples to the canonical eight parts."""

    values = np.asarray(sensor_force)
    if values.ndim < 2 or values.shape[-1] != 3:
        raise ValueError("sensor force must end in [body, xyz]")
    names = tuple(str(name) for name in sensor_body_names)
    if values.shape[-2] != len(names):
        raise ValueError("sensor force body axis does not match sensor_body_names")
    name_to_index = {name: index for index, name in enumerate(names)}
    output = np.zeros(
        (*values.shape[:-2], len(CONTACT_FORCE_PART_ORDER), 3),
        dtype=values.dtype,
    )
    for part_index, part in enumerate(CONTACT_FORCE_PART_ORDER):
        indices = [
            name_to_index[name]
            for name in CONTACT_FORCE_PART_BODY_NAMES[part]
            if name in name_to_index
        ]
        if indices:
            output[..., part_index, :] = values[..., indices, :].sum(axis=-2)
    return output


def validate_frame_boundary_replay(
    replay: Mapping[str, Any],
    *,
    expected_frames: int | None = None,
) -> dict[str, Any]:
    """Validate a replay result and return its decoded metadata."""

    required = (
        "contact_force_part_w",
        "contact_force_part_mask",
        "contact_force_part_mask_raw",
        "contact_force_part_order",
        "contact_force_frame_valid",
        "metadata_json",
    )
    missing = [name for name in required if name not in replay]
    if missing:
        raise ValueError(f"frame-boundary replay is missing: {missing}")
    force = np.asarray(replay["contact_force_part_w"])
    if force.ndim != 3 or force.shape[1:] != (len(CONTACT_FORCE_PART_ORDER), 3):
        raise ValueError(f"invalid replay force shape: {force.shape}")
    if expected_frames is not None and force.shape[0] != expected_frames:
        raise ValueError(
            f"replay frames={force.shape[0]} does not match motion frames={expected_frames}"
        )
    if not np.isfinite(force).all():
        raise ValueError("frame-boundary replay force contains NaN or Inf")
    order = tuple(
        str(value)
        for value in np.asarray(replay["contact_force_part_order"]).reshape(-1)
    )
    if order != CONTACT_FORCE_PART_ORDER:
        raise ValueError(f"replay part order is {order}, expected {CONTACT_FORCE_PART_ORDER}")
    mask_shape = force.shape[:2]
    for name in ("contact_force_part_mask", "contact_force_part_mask_raw"):
        if np.asarray(replay[name]).shape != mask_shape:
            raise ValueError(f"{name} must be {mask_shape}")
    valid = np.asarray(replay["contact_force_frame_valid"], dtype=bool)
    if valid.shape != (force.shape[0],):
        raise ValueError("contact_force_frame_valid must have one value per frame")
    if valid.size and valid[0]:
        raise ValueError("frame zero must be invalid for frame-boundary replay force")
    metadata = json.loads(str(np.asarray(replay["metadata_json"]).item()))
    mismatches = {
        key: (metadata.get(key), expected)
        for key, expected in FRAME_BOUNDARY_REPLAY_CONTRACT.items()
        if metadata.get(key) != expected
    }
    if mismatches:
        raise ValueError(f"frame-boundary replay contract mismatch: {mismatches}")
    return metadata


def build_force_policy_reference(
    *,
    kinematics: Mapping[str, Any],
    replay: Mapping[str, Any],
    recording_metadata: Mapping[str, Any],
    recording_path: str | Path,
    kinematics_path: str | Path,
) -> dict[str, np.ndarray]:
    """Combine canonical Newton kinematics with calculated replay force."""

    missing = [name for name in POLICY_MOTION_FIELDS if name not in kinematics]
    if missing:
        raise ValueError(f"policy-reference kinematics is missing: {missing}")
    frame_count = int(np.asarray(kinematics["joint_pos"]).shape[0])
    replay_metadata = validate_frame_boundary_replay(
        replay,
        expected_frames=frame_count,
    )
    decode_robot_asset_json(
        kinematics["robot_asset_json"],
        context=f"policy-reference kinematics {kinematics_path}",
    )
    decode_kinematics_provenance(
        kinematics["kinematics_provenance_json"],
        context=f"policy-reference kinematics {kinematics_path}",
        require_newton=True,
    )
    solver_config = recording_metadata.get("newton_solver_config")
    if not isinstance(solver_config, Mapping):
        raise ValueError("recording metadata has no Newton solver config")
    provenance = newton_contact_provenance(
        solver_config=solver_config,
        source_recording=str(Path(recording_path).expanduser().resolve()),
        threshold_n=10.0,
    )
    provenance.update(
        {
            "playback_contract": (
                "authoritative_20ms_trajectory_boundary_state_then_"
                "four_continuous_5ms_newton_substeps"
            ),
            "boundary_state_source": str(
                Path(kinematics_path).expanduser().resolve()
            ),
            "torque_source": (
                f"{Path(recording_path).expanduser().resolve()}"
                "::torques_substep[env0]"
            ),
            "state_overwrite_frequency": "once_per_control_frame",
            "force_sampling": "fourth_physics_substep",
            "frame_zero_force_valid": False,
            "self_collisions_enabled": False,
            "reference_force_migration": False,
            "raw_contact_persisted": False,
        }
    )
    output = {
        name: np.asarray(kinematics[name])
        for name in POLICY_MOTION_FIELDS
    }
    output.update(
        {
            "contact_force_part_w": np.asarray(
                replay["contact_force_part_w"], dtype=np.float32
            ),
            "contact_force_part_mask": np.asarray(
                replay["contact_force_part_mask"], dtype=bool
            ),
            "contact_force_part_mask_raw": np.asarray(
                replay["contact_force_part_mask_raw"], dtype=bool
            ),
            "contact_force_part_order": np.asarray(CONTACT_FORCE_PART_ORDER),
            "contact_force_part_body_names_json": np.asarray(
                json.dumps(
                    {
                        key: list(value)
                        for key, value in CONTACT_FORCE_PART_BODY_NAMES.items()
                    },
                    sort_keys=True,
                )
            ),
            "contact_force_demo_threshold": np.asarray(10.0, dtype=np.float32),
            "contact_force_demo_off_threshold": np.asarray(5.0, dtype=np.float32),
            "contact_force_demo_close_gap_frames": np.asarray(2, dtype=np.int32),
            "contact_force_sample_semantics": np.asarray(
                "latest Newton physics substep after trajectory boundary state"
            ),
            "contact_force_provenance_json": np.asarray(
                encode_contact_force_provenance(provenance)
            ),
            "frame_state_replay_metadata_json": np.asarray(
                json.dumps(replay_metadata, sort_keys=True)
            ),
        }
    )
    object_fields = [
        name for name, value in output.items() if np.asarray(value).dtype == object
    ]
    if object_fields:
        raise ValueError(f"policy reference contains object arrays: {object_fields}")
    return output


__all__ = [
    "FRAME_BOUNDARY_REPLAY_CONTRACT",
    "POLICY_MOTION_FIELDS",
    "build_force_policy_reference",
    "reduce_sensor_force_parts",
    "stable_contact_masks",
    "validate_frame_boundary_replay",
]
