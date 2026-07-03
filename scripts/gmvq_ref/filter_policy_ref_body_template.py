#!/usr/bin/env python3
"""Filter a policy_ref_v1 motion to a template body schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


BODY_ALIAS = {
    "left_foot_contact_point": "left_ankle_roll_link",
    "right_foot_contact_point": "right_ankle_roll_link",
}


BODY_KEYS = ("body_pos_w", "body_quat_w", "body_lin_vel_w", "body_ang_vel_w")


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path.expanduser(), allow_pickle=False) as data:
        return {key: np.asarray(data[key]) for key in data.files}


def _match_body_indices(source_names: np.ndarray, template_names: np.ndarray) -> tuple[list[int], list[str]]:
    source = [str(x) for x in np.asarray(source_names).reshape(-1)]
    indices: list[int] = []
    aliases: list[str] = []
    for name in [str(x) for x in np.asarray(template_names).reshape(-1)]:
        lookup = BODY_ALIAS.get(name, name)
        if lookup not in source:
            raise ValueError(f"template body {name!r} maps to {lookup!r}, which is missing from source")
        indices.append(source.index(lookup))
        aliases.append(f"{name}->{lookup}" if lookup != name else name)
    return indices, aliases


def _finite_difference(values: np.ndarray, fps: float) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    if arr.shape[0] <= 1:
        return np.zeros_like(arr, dtype=np.float32)
    return np.gradient(arr, 1.0 / fps, axis=0).astype(np.float32)


def _normalize_quat(q: np.ndarray) -> np.ndarray:
    out = np.asarray(q, dtype=np.float32).copy()
    norm = np.linalg.norm(out, axis=-1, keepdims=True)
    out /= np.maximum(norm, 1.0e-8)
    return out.astype(np.float32)


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


def _root_ang_vel_from_wxyz(root_quat_wxyz: np.ndarray, fps: float) -> np.ndarray:
    q = _normalize_quat(np.asarray(root_quat_wxyz, dtype=np.float32)[:, [1, 2, 3, 0]])
    if q.shape[0] <= 1:
        return np.zeros((q.shape[0], 3), dtype=np.float32)
    for i in range(1, q.shape[0]):
        if float(np.sum(q[i - 1] * q[i])) < 0.0:
            q[i] *= -1.0
    delta = _quat_mul_xyzw(q[1:], _quat_conjugate_xyzw(q[:-1]))
    interval_omega = _quat_to_rotvec_xyzw(delta) * float(fps)
    omega = np.zeros((q.shape[0], 3), dtype=np.float32)
    omega[0] = interval_omega[0]
    omega[-1] = interval_omega[-1]
    if q.shape[0] > 2:
        omega[1:-1] = 0.5 * (interval_omega[:-1] + interval_omega[1:])
    return omega.astype(np.float32)


def _joint_vel_from_joint_pos(joint_pos: np.ndarray, fps: float) -> np.ndarray:
    root_lin_vel = _finite_difference(joint_pos[:, :3], fps)
    root_ang_vel = _root_ang_vel_from_wxyz(joint_pos[:, 3:7], fps)
    dof_vel = _finite_difference(joint_pos[:, 7:], fps)
    return np.concatenate([root_lin_vel, root_ang_vel, dof_vel], axis=1).astype(np.float32)


def filter_ref(args: argparse.Namespace) -> dict[str, object]:
    source = _load_npz(args.input)
    template = _load_npz(args.template)
    template_body_names = np.asarray(template["body_names"])
    body_indices, alias_report = _match_body_indices(source["body_names"], template_body_names)

    out: dict[str, np.ndarray] = {}
    for key, value in source.items():
        if key in BODY_KEYS:
            out[key] = np.asarray(value)[:, body_indices].astype(np.float32, copy=False)
        elif key == "body_names":
            out[key] = template_body_names
        elif key == "joint_vel":
            joint_pos = np.asarray(source["joint_pos"], dtype=np.float32)
            joint_vel = np.asarray(value, dtype=np.float32)
            expected_dim = int(np.asarray(source["joint_names"]).reshape(-1).shape[0]) + 6
            if joint_vel.ndim == 2 and joint_vel.shape == (joint_pos.shape[0], expected_dim):
                out[key] = joint_vel
            else:
                fps = float(np.asarray(source["fps"]).reshape(-1)[0])
                out[key] = _joint_vel_from_joint_pos(joint_pos, fps)
        elif key == "policy_ref_canonicalization_report_json":
            continue
        else:
            out[key] = np.asarray(value)

    out["policy_ref_schema"] = np.asarray("policy_ref_v1")
    report = {
        "schema": "policy_ref_body_template_filter_v1",
        "input": str(args.input.expanduser()),
        "template": str(args.template.expanduser()),
        "output": str(args.output.expanduser()),
        "frame_count": int(out["joint_pos"].shape[0]),
        "joint_pos_dim": int(out["joint_pos"].shape[1]),
        "joint_vel_dim": int(out["joint_vel"].shape[1]),
        "body_count": int(out["body_pos_w"].shape[1]),
        "body_aliases": alias_report,
    }
    out["policy_ref_body_template_filter_report_json"] = np.asarray(json.dumps(report, sort_keys=True))

    args.output.expanduser().parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output.expanduser(), **out)
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    filter_ref(parse_args())


if __name__ == "__main__":
    main()
