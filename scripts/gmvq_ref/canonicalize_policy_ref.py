#!/usr/bin/env python3
"""Canonicalize a motion NPZ into the policy_ref_v1 contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA_NAME = "policy_ref_v1"
REQUIRED_KEYS = (
    "fps",
    "joint_names",
    "body_names",
    "joint_pos",
    "joint_vel",
    "body_pos_w",
    "body_quat_w",
    "body_lin_vel_w",
    "body_ang_vel_w",
)
FLOAT_KEYS = (
    "joint_pos",
    "joint_vel",
    "body_pos_w",
    "body_quat_w",
    "body_lin_vel_w",
    "body_ang_vel_w",
)


def _scalar_fps(value: np.ndarray) -> float:
    fps = float(np.asarray(value).reshape(()).item())
    if not np.isfinite(fps) or fps <= 0.0:
        raise ValueError(f"fps must be positive, got {fps}")
    return fps


def _normalize_quat(q: np.ndarray) -> np.ndarray:
    out = np.asarray(q, dtype=np.float32).copy()
    norm = np.linalg.norm(out, axis=-1, keepdims=True)
    out /= np.maximum(norm, 1.0e-8)
    return out.astype(np.float32)


def _finite_difference(values: np.ndarray, fps: float) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    if arr.shape[0] <= 1:
        return np.zeros_like(arr, dtype=np.float32)
    return np.gradient(arr, 1.0 / fps, axis=0).astype(np.float32)


def _quat_conjugate_xyzw(q: np.ndarray) -> np.ndarray:
    out = q.copy()
    out[..., :3] *= -1.0
    return out


def _quat_mul_xyzw(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ax, ay, az, aw = np.moveaxis(a, -1, 0)
    bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack(
        (
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz,
        ),
        axis=-1,
    )


def _quat_to_rotvec_xyzw(q: np.ndarray) -> np.ndarray:
    q = _normalize_quat(q)
    xyz = q[..., :3]
    w = np.clip(q[..., 3], -1.0, 1.0)
    sin_half = np.linalg.norm(xyz, axis=-1)
    angle = 2.0 * np.arctan2(sin_half, w)
    angle = (angle + np.pi) % (2.0 * np.pi) - np.pi
    scale = np.zeros_like(angle, dtype=np.float32)
    valid = sin_half > 1.0e-8
    scale[valid] = angle[valid] / sin_half[valid]
    return (xyz * scale[..., None]).astype(np.float32)


def _body_ang_vel_from_quat(body_quat_w: np.ndarray, fps: float) -> np.ndarray:
    q = _normalize_quat(body_quat_w)
    if q.shape[0] <= 1:
        return np.zeros(q.shape[:-1] + (3,), dtype=np.float32)

    # Keep neighboring quaternions on the same hemisphere before differencing.
    q = q.copy()
    for i in range(1, q.shape[0]):
        dot = np.sum(q[i - 1] * q[i], axis=-1, keepdims=True)
        q[i] = np.where(dot < 0.0, -q[i], q[i])

    delta = _quat_mul_xyzw(q[1:], _quat_conjugate_xyzw(q[:-1]))
    interval_omega = _quat_to_rotvec_xyzw(delta) * float(fps)
    omega = np.zeros(q.shape[:-1] + (3,), dtype=np.float32)
    omega[0] = interval_omega[0]
    omega[-1] = interval_omega[-1]
    if q.shape[0] > 2:
        omega[1:-1] = 0.5 * (interval_omega[:-1] + interval_omega[1:])
    return omega.astype(np.float32)


def _root_ang_vel_from_wxyz(root_quat_wxyz: np.ndarray, fps: float) -> np.ndarray:
    quat_xyzw = np.asarray(root_quat_wxyz, dtype=np.float32)[:, [1, 2, 3, 0]]
    return _body_ang_vel_from_quat(quat_xyzw[:, None, :], fps)[:, 0]


def _joint_vel_from_joint_pos(joint_pos: np.ndarray, fps: float) -> np.ndarray:
    if joint_pos.ndim != 2 or joint_pos.shape[1] < 7:
        raise ValueError(f"joint_pos must be [T, 7 + num_joints], got {joint_pos.shape}")
    root_lin_vel = _finite_difference(joint_pos[:, :3], fps)
    root_ang_vel = _root_ang_vel_from_wxyz(joint_pos[:, 3:7], fps)
    dof_vel = _finite_difference(joint_pos[:, 7:], fps)
    return np.concatenate([root_lin_vel, root_ang_vel, dof_vel], axis=1).astype(np.float32)


def _canonical_joint_vel(
    joint_vel: np.ndarray,
    *,
    joint_pos: np.ndarray,
    num_joints: int,
    fps: float,
    report: dict[str, Any],
) -> np.ndarray:
    expected_dim = int(num_joints) + 6
    if joint_vel.ndim == 2 and joint_vel.shape == (joint_pos.shape[0], expected_dim):
        return joint_vel.astype(np.float32)
    if joint_vel.size:
        report["normalized"].append(f"joint_vel:{tuple(joint_vel.shape)}->{(joint_pos.shape[0], expected_dim)}")
    else:
        report["filled"].append("joint_vel")
    return _joint_vel_from_joint_pos(joint_pos, fps)


def _load_optional(data: np.lib.npyio.NpzFile, key: str, skipped: list[str]) -> np.ndarray | None:
    try:
        return data[key]
    except Exception as exc:  # optional legacy pickle metadata may be unreadable across numpy versions
        skipped.append(f"{key}: {exc}")
        return None


def _string_array(value: np.ndarray) -> np.ndarray:
    return np.asarray([str(item) for item in np.asarray(value).reshape(-1)], dtype=np.str_)


def canonicalize(input_path: Path, output_path: Path, *, strict_optional: bool = False) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "input": str(input_path),
        "output": str(output_path),
        "filled": [],
        "normalized": [],
        "skipped_optional": [],
    }

    with np.load(input_path, allow_pickle=True) as data:
        files = list(data.files)
        required_source = [key for key in REQUIRED_KEYS if key not in {"joint_vel", "body_lin_vel_w", "body_ang_vel_w"}]
        missing = [key for key in required_source if key not in files]
        if missing:
            raise KeyError(f"{input_path} missing required policy_ref_v1 source fields: {missing}")

        fps = _scalar_fps(data["fps"])
        joint_pos = np.asarray(data["joint_pos"], dtype=np.float32)
        body_pos_w = np.asarray(data["body_pos_w"], dtype=np.float32)
        body_quat_w = _normalize_quat(np.asarray(data["body_quat_w"], dtype=np.float32))
        joint_names = _string_array(data["joint_names"])
        body_names = _string_array(data["body_names"])

        if joint_pos.ndim != 2:
            raise ValueError(f"joint_pos must be [T,D], got {joint_pos.shape}")
        if body_pos_w.ndim != 3 or body_pos_w.shape[2] != 3:
            raise ValueError(f"body_pos_w must be [T,B,3], got {body_pos_w.shape}")
        if body_quat_w.shape != body_pos_w.shape[:2] + (4,):
            raise ValueError(f"body_quat_w shape {body_quat_w.shape} incompatible with body_pos_w {body_pos_w.shape}")
        if joint_pos.shape[0] != body_pos_w.shape[0]:
            raise ValueError(f"joint_pos/body_pos_w frame mismatch: {joint_pos.shape[0]} vs {body_pos_w.shape[0]}")
        if body_names.shape[0] != body_pos_w.shape[1]:
            raise ValueError(f"body_names/body_pos_w body mismatch: {body_names.shape[0]} vs {body_pos_w.shape[1]}")
        expected_joint_pos_dim = int(joint_names.shape[0]) + 7
        if joint_pos.shape[1] != expected_joint_pos_dim:
            raise ValueError(
                f"joint_pos columns must be len(joint_names)+7: got {joint_pos.shape[1]}, "
                f"expected {expected_joint_pos_dim}"
            )

        if "joint_vel" in files:
            joint_vel = np.asarray(data["joint_vel"], dtype=np.float32)
        else:
            joint_vel = np.empty((0,), dtype=np.float32)
        joint_vel = _canonical_joint_vel(
            joint_vel,
            joint_pos=joint_pos,
            num_joints=int(joint_names.shape[0]),
            fps=fps,
            report=report,
        )

        if "body_lin_vel_w" in files:
            body_lin_vel_w = np.asarray(data["body_lin_vel_w"], dtype=np.float32)
        else:
            body_lin_vel_w = np.empty((0,), dtype=np.float32)
        if body_lin_vel_w.shape != body_pos_w.shape:
            body_lin_vel_w = _finite_difference(body_pos_w, fps)
            report["filled"].append("body_lin_vel_w")

        if "body_ang_vel_w" in files:
            body_ang_vel_w = np.asarray(data["body_ang_vel_w"], dtype=np.float32)
        else:
            body_ang_vel_w = np.empty((0,), dtype=np.float32)
        if body_ang_vel_w.shape != body_pos_w.shape:
            body_ang_vel_w = _body_ang_vel_from_quat(body_quat_w, fps)
            report["filled"].append("body_ang_vel_w")

        arrays: dict[str, np.ndarray] = {
            "fps": np.asarray(fps, dtype=np.float32),
            "joint_names": joint_names,
            "body_names": body_names,
            "joint_pos": joint_pos.astype(np.float32),
            "joint_vel": joint_vel.astype(np.float32),
            "body_pos_w": body_pos_w.astype(np.float32),
            "body_quat_w": body_quat_w.astype(np.float32),
            "body_lin_vel_w": body_lin_vel_w.astype(np.float32),
            "body_ang_vel_w": body_ang_vel_w.astype(np.float32),
            "policy_ref_schema": np.asarray(SCHEMA_NAME),
        }
        report["normalized"].append("body_quat_w")

        for key in files:
            if key in arrays or key in FLOAT_KEYS:
                continue
            value = _load_optional(data, key, report["skipped_optional"])
            if value is None:
                if strict_optional:
                    raise RuntimeError(f"failed to read optional key {key}")
                continue
            if value.dtype == object:
                report["skipped_optional"].append(f"{key}: skipped object dtype optional metadata")
                continue
            arrays[key] = value

    report["frames"] = int(arrays["joint_pos"].shape[0])
    report["joint_pos_dim"] = int(arrays["joint_pos"].shape[1])
    report["joint_vel_dim"] = int(arrays["joint_vel"].shape[1])
    report["body_count"] = int(arrays["body_pos_w"].shape[1])
    arrays["policy_ref_canonicalization_report_json"] = np.asarray(json.dumps(report, sort_keys=True))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **arrays)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strict-optional", action="store_true")
    args = parser.parse_args()

    report = canonicalize(args.input.expanduser(), args.output.expanduser(), strict_optional=args.strict_optional)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
