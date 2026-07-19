from __future__ import annotations

from pathlib import Path

import numpy as np
from somaforge_core.contact_schema import CONTACT_FORCE_PART_NAMES


def load_motion_sequence(path: str | Path) -> tuple[np.ndarray, int, tuple[str, ...]]:
    with np.load(Path(path).expanduser(), allow_pickle=False) as data:
        fps = int(np.asarray(data["fps"]).reshape(-1)[0]) if "fps" in data else 50
        if "qpos" in data:
            qpos = np.asarray(data["qpos"], dtype=np.float32)
        elif "joint_pos" in data:
            qpos = np.asarray(data["joint_pos"], dtype=np.float32)
        else:
            raise KeyError(f"{path} has neither qpos nor joint_pos")
        if qpos.ndim != 2:
            raise ValueError(f"{path} motion array must be [T,D], got {qpos.shape}")
        if "joint_names" not in data:
            raise ValueError(f"{path} has no joint_names; canonical playback requires named joints")
        joint_names = tuple(str(item) for item in np.asarray(data["joint_names"]).reshape(-1).tolist())
    if qpos.shape[1] != 7 + len(joint_names):
        raise ValueError(f"{path} motion width {qpos.shape[1]} does not match 7 + {len(joint_names)} joint_names")
    return qpos, fps, joint_names


def load_contact_force_payload(path: str | Path, *, frame_count: int) -> dict:
    with np.load(Path(path).expanduser(), allow_pickle=False) as data:
        names = (
            [str(item) for item in np.asarray(data["contact_force_part_order"]).reshape(-1).tolist()]
            if "contact_force_part_order" in data
            else list(CONTACT_FORCE_PART_NAMES)
        )
        forces = (
            np.asarray(data["contact_force_part_w"], dtype=np.float32)
            if "contact_force_part_w" in data
            else np.zeros((frame_count, len(names), 3), dtype=np.float32)
        )
        masks = (
            np.asarray(data["contact_force_part_mask"], dtype=bool)
            if "contact_force_part_mask" in data
            else np.linalg.norm(forces, axis=-1) > 0.0
        )
        positions = (
            np.asarray(data["contact_force_part_position_w"], dtype=np.float32)
            if "contact_force_part_position_w" in data
            else np.zeros_like(forces)
        )
        position_valid = (
            np.asarray(data["contact_force_part_position_valid"], dtype=bool)
            if "contact_force_part_position_valid" in data
            else masks.copy()
        )
        raw_counts = np.asarray(data["raw_contact_count"], dtype=np.int64) if "raw_contact_count" in data else None
        raw_points = np.asarray(data["raw_contact_point0_w"], dtype=np.float32) if "raw_contact_point0_w" in data else None
        raw_forces = np.asarray(data["raw_contact_force_w"], dtype=np.float32) if "raw_contact_force_w" in data else None
    count = min(frame_count, forces.shape[0], masks.shape[0], positions.shape[0], position_valid.shape[0])
    sample_points: list[list[list[float]]] = []
    sample_forces: list[list[list[float]]] = []
    if raw_counts is not None and raw_points is not None and raw_forces is not None:
        raw_frame_count = min(count, raw_counts.shape[0], raw_points.shape[0], raw_forces.shape[0])
        for frame in range(raw_frame_count):
            sample_count = max(0, min(int(raw_counts[frame]), raw_points.shape[1], raw_forces.shape[1]))
            sample_points.append(raw_points[frame, :sample_count].tolist())
            sample_forces.append(raw_forces[frame, :sample_count].tolist())
        for _ in range(raw_frame_count, count):
            sample_points.append([])
            sample_forces.append([])
    else:
        for frame in range(count):
            active = np.asarray(masks[frame], dtype=bool)
            sample_points.append(np.asarray(positions[frame])[active].tolist())
            sample_forces.append(np.asarray(forces[frame])[active].tolist())
    return {
        "part_order": names,
        "forces": forces[:count].tolist(),
        "masks": masks[:count].tolist(),
        "positions": positions[:count].tolist(),
        "position_valid": position_valid[:count].tolist(),
        "sample_points": sample_points,
        "sample_forces": sample_forces,
    }
