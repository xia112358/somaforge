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
    count = min(frame_count, forces.shape[0], masks.shape[0], positions.shape[0])
    return {
        "part_order": names,
        "forces": forces[:count].tolist(),
        "masks": masks[:count].tolist(),
        "positions": positions[:count].tolist(),
    }
