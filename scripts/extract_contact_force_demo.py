#!/usr/bin/env python3
"""Build a contact-force demo motion from a complete eval recording."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


PART_BODY_NAMES: dict[str, list[str]] = {
    "LF": ["left_ankle_roll_link"],
    "RF": ["right_ankle_roll_link"],
    "LH": ["left_wrist_yaw_link"],
    "RH": ["right_wrist_yaw_link"],
    "LK": ["left_knee_link"],
    "RK": ["right_knee_link"],
}
PART_ORDER = ("LF", "RF", "LH", "RH", "LK", "RK")


def _load_npz(path: Path) -> dict[str, Any]:
    data = np.load(path, allow_pickle=True)
    return {key: data[key] for key in data.files}


def _metadata(recording: dict[str, Any]) -> dict[str, Any]:
    if "_metadata_json" not in recording:
        raise ValueError("Recording is missing _metadata_json.")
    return json.loads(str(recording["_metadata_json"].item()))


def _validate_complete_rollout(recording: dict[str, Any], num_frames: int, allow_timeout: bool) -> np.ndarray:
    required = ("motion_id", "motion_time_step", "terminated", "timeout")
    missing = [key for key in required if key not in recording]
    if missing:
        raise ValueError(f"Recording is missing required rollout keys: {missing}")

    motion_ids = np.asarray(recording["motion_id"]).reshape(-1)
    if np.unique(motion_ids).size != 1:
        raise ValueError(f"Recording must contain exactly one motion_id, got {np.unique(motion_ids).tolist()}")

    time_steps = np.asarray(recording["motion_time_step"]).reshape(-1).astype(np.int64)
    expected = np.arange(num_frames, dtype=np.int64)
    terminated = np.asarray(recording["terminated"]).reshape(-1).astype(bool)
    timeout = np.asarray(recording["timeout"]).reshape(-1).astype(bool)
    if not (time_steps.size == terminated.size == timeout.size == motion_ids.size):
        raise ValueError(
            "Rollout keys must have matching lengths: "
            f"motion_id={motion_ids.size}, motion_time_step={time_steps.size}, "
            f"terminated={terminated.size}, timeout={timeout.size}"
        )

    for start in range(0, time_steps.size - num_frames + 1):
        stop = start + num_frames
        window_steps = time_steps[start:stop]
        unique_steps = np.unique(window_steps)
        if unique_steps.size != num_frames or not np.array_equal(unique_steps, expected):
            continue
        if terminated[start:stop].any():
            continue
        if timeout[start:stop].any() and not allow_timeout:
            continue

        window = np.arange(start, stop)
        return window[np.argsort(window_steps)]

    unique_steps = np.unique(time_steps)
    missing = sorted(set(expected.tolist()) - set(unique_steps.tolist()))[:10]
    duplicate_count = int(max(0, time_steps.size - unique_steps.size))
    first_terminated = int(np.flatnonzero(terminated)[0]) if terminated.any() else None
    first_timeout = int(np.flatnonzero(timeout)[0]) if timeout.any() else None
    raise ValueError(
        "Recording does not contain a complete normal motion cycle. "
        f"recording_length={time_steps.size}, motion_length={num_frames}, "
        f"missing_head={missing}, duplicate_count={duplicate_count}, "
        f"first_terminated={first_terminated}, first_timeout={first_timeout}"
    )


def _body_force_from_history(contact_history: np.ndarray) -> np.ndarray:
    if contact_history.ndim != 4 or contact_history.shape[-1] != 3:
        raise ValueError(f"Expected contact_forces_history [T,H,B,3], got {contact_history.shape}")
    magnitude = np.linalg.norm(contact_history, axis=-1)
    history_idx = magnitude.argmax(axis=1)
    frame_idx = np.arange(contact_history.shape[0])[:, None]
    body_idx = np.arange(contact_history.shape[2])[None, :]
    return contact_history[frame_idx, history_idx, body_idx]


def _reduce_part_force(selected: np.ndarray, reduce: str) -> np.ndarray:
    if reduce == "sum":
        return selected.sum(axis=1)
    if reduce == "mean":
        return selected.mean(axis=1)
    if reduce == "max":
        idx = np.linalg.norm(selected, axis=-1).argmax(axis=1)
        return selected[np.arange(selected.shape[0]), idx]
    raise ValueError(f"Unsupported --force-reduce '{reduce}'.")


def _part_forces(
    recording: dict[str, Any],
    body_names: list[str],
    part_body_names: dict[str, list[str]],
    force_reduce: str,
) -> np.ndarray:
    if "contact_forces_history" in recording:
        body_force = _body_force_from_history(np.asarray(recording["contact_forces_history"], dtype=np.float32))
    elif "contact_forces" in recording:
        body_force = np.asarray(recording["contact_forces"], dtype=np.float32)
    else:
        raise ValueError("Recording has neither contact_forces_history nor contact_forces.")

    part_forces = []
    for part_name in PART_ORDER:
        names = part_body_names[part_name]
        ids = [body_names.index(name) for name in names if name in body_names]
        if not ids:
            raise ValueError(f"No simulator bodies found for part {part_name}: {names}")
        selected = body_force[:, ids, :]
        part_forces.append(_reduce_part_force(selected, force_reduce))
    return np.stack(part_forces, axis=1).astype(np.float32)


def _parse_part_body_names(value: str | None) -> dict[str, list[str]]:
    if value is None:
        return dict(PART_BODY_NAMES)
    parsed = json.loads(value)
    return {part: [str(name) for name in parsed[part]] for part in PART_ORDER}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion", required=True, type=Path, help="Original motion npz.")
    parser.add_argument("--recording", required=True, type=Path, help="Complete eval recording npz.")
    parser.add_argument("--output", required=True, type=Path, help="Output force-demo motion npz.")
    parser.add_argument("--threshold", type=float, default=10.0, help="Contact force mask threshold in Newtons.")
    parser.add_argument("--force-reduce", choices=("max", "sum", "mean"), default="max")
    parser.add_argument("--part-body-names-json", default=None, help="Optional JSON map for contact-force part body names.")
    parser.add_argument("--allow-timeout", action="store_true", help="Allow timeout flags in the recording.")
    args = parser.parse_args()

    motion = _load_npz(args.motion)
    recording = _load_npz(args.recording)
    meta = _metadata(recording)

    if "joint_pos" not in motion:
        raise ValueError(f"{args.motion} is missing joint_pos.")
    num_frames = int(np.asarray(motion["joint_pos"]).shape[0])
    order = _validate_complete_rollout(recording, num_frames, args.allow_timeout)

    body_names = [str(name) for name in meta.get("body_names", [])]
    if not body_names:
        raise ValueError("Recording metadata is missing body_names.")

    part_body_names = _parse_part_body_names(args.part_body_names_json)
    part_force = _part_forces(recording, body_names, part_body_names, args.force_reduce)[order]
    if not np.isfinite(part_force).all():
        raise ValueError("Computed contact_force_part_w contains NaN or Inf.")

    part_mask = (np.linalg.norm(part_force, axis=-1) > float(args.threshold)).astype(bool)

    out = dict(motion)
    out["contact_force_part_w"] = part_force
    out["contact_force_part_mask"] = part_mask
    out["contact_force_part_order"] = np.asarray(PART_ORDER)
    out["contact_force_part_body_names_json"] = np.asarray(json.dumps(part_body_names))
    out["contact_force_demo_source"] = np.asarray(str(args.recording))
    out["contact_force_demo_threshold"] = np.asarray(np.float32(args.threshold))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **out)
    print(
        f"Wrote {args.output} frames={num_frames} "
        f"force_shape={part_force.shape} contact_ratio={part_mask.mean():.4f}"
    )


if __name__ == "__main__":
    main()
