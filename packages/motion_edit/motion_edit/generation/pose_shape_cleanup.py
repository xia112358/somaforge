from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from scipy.signal import butter, sosfiltfilt


def clean_pose_shape_qpos(
    joint_pos: np.ndarray,
    *,
    fps: float,
    cutoff_hz: float = 6.0,
    endpoint_blend_frames: int = 20,
) -> np.ndarray:
    """Remove rollout jitter while retaining its full-body pose shape."""

    qpos = np.asarray(joint_pos, dtype=np.float64)
    if qpos.ndim != 2 or qpos.shape[1] < 7:
        raise ValueError(f"joint_pos must have shape [T,7+J], got {qpos.shape}")
    if not 0.0 < float(cutoff_hz) < 0.5 * float(fps):
        raise ValueError(
            f"cutoff_hz must be between zero and Nyquist ({0.5 * float(fps)}), "
            f"got {cutoff_hz}"
        )

    cleaned = qpos.copy()
    cleaned[:, :3] = _lowpass(qpos[:, :3], fps=fps, cutoff_hz=cutoff_hz)
    quaternion = _continuous_quaternion_wxyz(qpos[:, 3:7])
    quaternion = _lowpass(quaternion, fps=fps, cutoff_hz=cutoff_hz)
    cleaned[:, 3:7] = _normalize_quaternion(quaternion)
    cleaned[:, 7:] = _lowpass(qpos[:, 7:], fps=fps, cutoff_hz=cutoff_hz)

    blend_frames = min(
        int(endpoint_blend_frames),
        max(1, cleaned.shape[0] // 10),
    )
    phase = np.linspace(0.0, 1.0, blend_frames, dtype=np.float64)
    weight = 0.5 - 0.5 * np.cos(np.pi * phase)
    cleaned[:blend_frames] = (
        (1.0 - weight[:, None]) * qpos[:blend_frames]
        + weight[:, None] * cleaned[:blend_frames]
    )
    cleaned[-blend_frames:] = (
        weight[::-1, None] * cleaned[-blend_frames:]
        + (1.0 - weight[::-1, None]) * qpos[-blend_frames:]
    )
    cleaned[:, 3:7] = _normalize_quaternion(cleaned[:, 3:7])
    return cleaned


def filtered_pose_seed_arrays(
    source: Mapping[str, Any],
    *,
    source_path: str | Path,
    cutoff_hz: float = 6.0,
) -> dict[str, np.ndarray]:
    """Build the q-only seed consumed by direct Newton FK canonicalization."""

    for key in ("joint_pos", "joint_names", "robot_asset_json"):
        if key not in source:
            raise ValueError(f"pose-shape source is missing {key}")
    fps = float(np.asarray(source.get("fps", 50.0)).reshape(-1)[0])
    cleaned = clean_pose_shape_qpos(
        np.asarray(source["joint_pos"], dtype=np.float64),
        fps=fps,
        cutoff_hz=cutoff_hz,
    )
    return {
        "fps": np.asarray(fps, dtype=np.float32),
        "joint_pos": cleaned.astype(np.float32),
        "joint_names": np.asarray(source["joint_names"]),
        "robot_asset_json": np.asarray(source["robot_asset_json"]),
        "cleanup_source_motion": np.asarray(
            str(Path(source_path).expanduser().resolve())
        ),
        "cleanup_filter": np.asarray("zero_phase_butterworth_order4"),
        "cleanup_cutoff_hz": np.asarray(cutoff_hz, dtype=np.float32),
    }


def pose_shape_plan_payload(
    template: Mapping[str, Any],
    *,
    rollout_path: str | Path,
    canonical_motion_path: str | Path,
    cutoff_hz: float = 6.0,
) -> dict[str, Any]:
    """Point a task-variant plan at the cleaned canonical pose authority."""

    rollout = Path(rollout_path).expanduser().resolve()
    canonical = Path(canonical_motion_path).expanduser().resolve()
    plan = dict(template)
    plan["source_motion_path"] = str(canonical)
    metadata = dict(plan.get("metadata", {}))
    contact_authority = metadata.get("contact_force_source_path")
    if not contact_authority:
        raise ValueError(
            "pose-shape plan requires metadata.contact_force_source_path"
        )
    metadata["kinematic_cleanup"] = {
        "source_motion": str(rollout),
        "canonical_motion": str(canonical),
        "filter": "zero_phase_butterworth_order4",
        "cutoff_hz": float(cutoff_hz),
        "contact_authority": str(
            Path(str(contact_authority)).expanduser().resolve()
        ),
    }
    plan["metadata"] = metadata
    return plan


def write_pose_shape_plan(
    template_path: str | Path,
    output_path: str | Path,
    *,
    rollout_path: str | Path,
    canonical_motion_path: str | Path,
    cutoff_hz: float = 6.0,
) -> Path:
    template_file = Path(template_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    template = json.loads(template_file.read_text(encoding="utf-8"))
    payload = pose_shape_plan_payload(
        template,
        rollout_path=rollout_path,
        canonical_motion_path=canonical_motion_path,
        cutoff_hz=cutoff_hz,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output


def _continuous_quaternion_wxyz(quaternion: np.ndarray) -> np.ndarray:
    result = np.asarray(quaternion, dtype=np.float64).copy()
    for frame in range(1, result.shape[0]):
        if float(np.dot(result[frame - 1], result[frame])) < 0.0:
            result[frame] *= -1.0
    return result


def _lowpass(
    values: np.ndarray,
    *,
    fps: float,
    cutoff_hz: float,
) -> np.ndarray:
    sos = butter(4, cutoff_hz, btype="lowpass", fs=fps, output="sos")
    return sosfiltfilt(sos, np.asarray(values, dtype=np.float64), axis=0)


def _normalize_quaternion(quaternion: np.ndarray) -> np.ndarray:
    values = np.asarray(quaternion, dtype=np.float64)
    return values / np.maximum(
        np.linalg.norm(values, axis=-1, keepdims=True),
        1.0e-12,
    )
