from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from motion_edit.contact_force import (
    DEFAULT_CONTACT_FORCE_PART_ORDER,
    MuJoCoPrescribedContactBackend,
    PrescribedContactBackend,
    PrescribedContactSolveConfig,
    differentiate_mujoco_qpos_sequence,
    solve_prescribed_contact_forces,
)


@dataclass(frozen=True)
class ContactForceBakeResult:
    output_motion_path: Path
    metadata: dict[str, Any]
    warnings: list[str]


def bake_prescribed_contact_forces_for_motion(
    motion_path: str | Path,
    *,
    output_motion_path: str | Path | None = None,
    backend: PrescribedContactBackend | None = None,
    mujoco_model_path: str | Path | None = None,
    solve_mode: str = "forward",
    fps: float | None = None,
    assignment_max_distance: float = 0.35,
    force_unit_scale: float = 1.0,
    overwrite: bool = False,
) -> ContactForceBakeResult:
    """Bake prescribed-playback contact forces into a motion npz.

    This helper is intentionally post-generation: it reads an already generated
    fullbody motion, queries contact forces under prescribed qpos/qvel/qacc, and
    writes canonical part-level force arrays. It does not alter the pose fields
    and does not run a forward rollout.
    """

    source = Path(motion_path).expanduser()
    out = Path(output_motion_path).expanduser() if output_motion_path is not None else source
    if out.exists() and out != source and not overwrite:
        raise FileExistsError(f"{out} already exists; pass overwrite=True to replace it")
    motion = _load_motion_npz(source)
    if "joint_pos" not in motion:
        raise ValueError(f"{source}: missing joint_pos; prescribed contact force bake requires fullbody qpos")
    qpos = np.asarray(motion["joint_pos"], dtype=np.float64)
    if qpos.ndim != 2:
        raise ValueError(f"joint_pos must have shape [T, nq], got {qpos.shape}")
    actual_fps = _fps_from_motion(motion, fallback=50.0 if fps is None else float(fps))
    config = PrescribedContactSolveConfig(
        part_order=_part_order_from_motion(motion),
        solve_mode=str(solve_mode),
        assignment_max_distance=float(assignment_max_distance),
        force_unit_scale=float(force_unit_scale),
        metadata={
            "bake_entry": "generation.contact_force_bake",
            "source_motion": str(source),
            "output_motion": str(out),
        },
    )
    force_backend = backend
    qvel: np.ndarray | None = None
    qacc: np.ndarray | None = None
    if force_backend is None:
        if mujoco_model_path is None:
            raise ValueError("mujoco_model_path is required when backend is not provided")
        force_backend = MuJoCoPrescribedContactBackend(mujoco_model_path)
        qvel, qacc = differentiate_mujoco_qpos_sequence(mujoco_model_path, qpos, dt=1.0 / actual_fps)
    else:
        qvel = _optional_motion_array(motion, "joint_vel", n_frames=qpos.shape[0])
    if str(solve_mode) == "inverse" and qacc is None:
        if mujoco_model_path is not None:
            qvel, qacc = differentiate_mujoco_qpos_sequence(mujoco_model_path, qpos, dt=1.0 / actual_fps)
        else:
            qacc = _finite_difference_qvel(qvel, fps=actual_fps) if qvel is not None else None
    mask = _contact_mask_from_motion(motion, n_frames=qpos.shape[0], part_count=len(config.part_order))
    positions = _contact_positions_from_motion(motion, n_frames=qpos.shape[0], part_count=len(config.part_order))
    field = solve_prescribed_contact_forces(
        qpos,
        force_backend,
        config,
        qvel_ref=qvel,
        qacc_ref=qacc,
        contact_mask=mask,
        contact_part_position_w=positions,
    )
    output = dict(motion)
    output.update(field.to_npz_arrays())
    force_metadata = dict(field.metadata)
    force_metadata.update(
        {
            "fps": float(actual_fps),
            "qpos_key": "joint_pos",
            "qvel_source": "mujoco_differentiate" if backend is None and mujoco_model_path is not None else ("joint_vel" if qvel is not None else "none"),
            "qacc_source": "mujoco_differentiate" if mujoco_model_path is not None else ("finite_difference_joint_vel" if qacc is not None else "none"),
        }
    )
    output["motion_edit_force_metadata"] = _json_npz_value(force_metadata)
    if "motion_edit_generation_metadata" in output:
        generation_metadata = _decode_json_npz(output["motion_edit_generation_metadata"])
        generation_metadata["contact_force_bake"] = force_metadata
        output["motion_edit_generation_metadata"] = _json_npz_value(generation_metadata)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out, **output)
    warnings: list[str] = []
    if int(force_metadata.get("missing_intended_contact_frames", 0)) > 0:
        warnings.append(
            f"prescribed contact solve missed {force_metadata['missing_intended_contact_frames']} intended contact frames"
        )
    if int(force_metadata.get("unknown_sample_count", 0)) > 0:
        warnings.append(f"prescribed contact solve left {force_metadata['unknown_sample_count']} samples unassigned")
    return ContactForceBakeResult(output_motion_path=out, metadata=force_metadata, warnings=warnings)


def _load_motion_npz(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as data:
        return {key: data[key] for key in data.files}


def _decode_npz_string(value: Any) -> str:
    raw = np.asarray(value, dtype=object)
    item = raw.item() if raw.ndim == 0 else raw.reshape(-1)[0]
    if isinstance(item, bytes):
        return item.decode("utf-8")
    return str(item)


def _decode_json_npz(value: Any) -> dict[str, Any]:
    try:
        raw = _decode_npz_string(value)
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _json_npz_value(payload: dict[str, Any]) -> np.ndarray:
    return np.asarray(json.dumps(payload, sort_keys=True), dtype=object)


def _fps_from_motion(motion: dict[str, Any], *, fallback: float) -> float:
    if "fps" in motion:
        return float(np.asarray(motion["fps"]).reshape(-1)[0])
    if "dt" in motion:
        dt = float(np.asarray(motion["dt"]).reshape(-1)[0])
        if dt > 0.0:
            return 1.0 / dt
    return float(fallback)


def _motion_strings(motion: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        if key not in motion:
            continue
        arr = np.asarray(motion[key], dtype=object)
        if arr.ndim == 0:
            item = arr.item()
            if isinstance(item, str):
                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, list):
                        return [str(value) for value in parsed]
                except json.JSONDecodeError:
                    return [value.strip() for value in item.split(",") if value.strip()]
            if isinstance(item, (list, tuple)):
                return [str(value) for value in item]
            return [str(item)]
        return [str(value) for value in arr.reshape(-1).tolist()]
    return []


def _part_order_from_motion(motion: dict[str, Any]) -> tuple[str, ...]:
    names = _motion_strings(
        motion,
        (
            "contact_force_part_order",
            "contact_part_order",
            "part_order",
            "contact_part_names",
            "contact_force_part_names",
        ),
    )
    return tuple(names) if names else DEFAULT_CONTACT_FORCE_PART_ORDER


def _optional_motion_array(motion: dict[str, Any], key: str, *, n_frames: int) -> np.ndarray | None:
    if key not in motion:
        return None
    arr = np.asarray(motion[key], dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] != int(n_frames):
        return None
    return arr


def _contact_mask_from_motion(motion: dict[str, Any], *, n_frames: int, part_count: int) -> np.ndarray | None:
    for key in ("contact_force_part_mask", "contact_part_mask"):
        if key not in motion:
            continue
        arr = np.asarray(motion[key], dtype=bool)
        if arr.shape == (int(n_frames), int(part_count)):
            return arr
    return None


def _contact_positions_from_motion(motion: dict[str, Any], *, n_frames: int, part_count: int) -> np.ndarray | None:
    if "contact_force_part_position_w" not in motion:
        return None
    arr = np.asarray(motion["contact_force_part_position_w"], dtype=np.float64)
    if arr.shape != (int(n_frames), int(part_count), 3):
        return None
    return arr


def _finite_difference_qvel(qvel: np.ndarray | None, *, fps: float) -> np.ndarray | None:
    if qvel is None:
        return None
    if qvel.shape[0] <= 1:
        return np.zeros_like(qvel)
    dt = 1.0 / float(fps)
    qacc = np.zeros_like(qvel, dtype=np.float64)
    qacc[1:-1] = (qvel[2:] - qvel[:-2]) / (2.0 * dt)
    qacc[0] = (qvel[1] - qvel[0]) / dt
    qacc[-1] = (qvel[-1] - qvel[-2]) / dt
    return qacc
