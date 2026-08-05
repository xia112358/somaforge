#!/usr/bin/env python3
"""Augment selector training data with model-induced closed-loop atom starts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from scripts.gmvq_ref.decode_selector_ref import _chain_pose_segment
from scripts.gmvq_ref.extract_selector_height_dataset import _load_surfaces
from scripts.gmvq_ref.generate_closed_loop_ref import _current_velocity, _scan
from scripts.gmvq_ref.selector_runtime import GMVQSelectorRuntime, build_observation


FEATURE_KEYS = (
    "height_scan",
    "root_pos_w",
    "root_quat_w",
    "root_lin_vel_w",
    "root_ang_vel_w",
    "joint_pos",
    "joint_vel",
)


def build(args: argparse.Namespace) -> dict[str, object]:
    with np.load(args.dataset, allow_pickle=False) as source:
        original = {key: np.asarray(source[key]) for key in source.files}
    surface_map = json.loads(args.surface_map.read_text(encoding="utf-8"))["surfaces_by_motion"]
    codes = np.asarray(original["codes"], dtype=np.int64)
    motion_ids = np.asarray(original["motion_ids"]).astype(str)
    source_paths = np.asarray(original["source_paths"]).astype(str)
    start_frames = np.asarray(original["start_frames"], dtype=np.int64)
    stop_code = int(codes.max())

    runtime = GMVQSelectorRuntime(
        code_checkpoint=args.code_selector,
        theta_checkpoint=args.theta_selector,
        gmvq_checkpoint=args.gmvq_checkpoint,
        start_decoder_checkpoint=args.start_decoder,
        device=args.device,
    )
    local_grid = np.asarray(original["local_grid"], dtype=np.float32)
    fps = args.fps
    generated: dict[str, list[np.ndarray]] = {key: [] for key in FEATURE_KEYS}
    generated.update({"codes": [], "theta": [], "motion_ids": []})

    for motion_id in sorted(set(motion_ids)):
        rows = np.flatnonzero((motion_ids == motion_id) & (codes < stop_code))
        rows = rows[np.argsort(start_frames[rows])]
        if not len(rows):
            continue
        source_path = source_paths[rows[0]]
        catalog = surface_map.get(source_path)
        if catalog is None:
            raise KeyError(f"surface map has no entry for {source_path}")
        surfaces = _load_surfaces(Path(catalog))
        trajectory = [np.asarray(original["joint_pos"][rows[0]], dtype=np.float32).copy()]
        initial_velocity = np.asarray(original["joint_vel"][rows[0]], dtype=np.float32)

        for row in rows:
            current_q = trajectory[-1]
            current_qd = _current_velocity(trajectory, fps, initial_velocity)
            height_scan, _, _ = _scan(
                root_pos_w=current_q[:3],
                root_quat_wxyz=current_q[3:7],
                local_grid=local_grid,
                surfaces=surfaces,
            )
            values = {
                "height_scan": height_scan,
                "root_pos_w": current_q[:3],
                "root_quat_w": current_q[3:7],
                "root_lin_vel_w": current_qd[:3],
                "root_ang_vel_w": current_qd[3:6],
                "joint_pos": current_q,
                "joint_vel": current_qd,
            }
            for key, value in values.items():
                generated[key].append(np.asarray(value, dtype=np.float32))
            generated["codes"].append(np.asarray(codes[row], dtype=np.int64))
            generated["theta"].append(np.asarray(original["theta"][row], dtype=np.float32))
            generated["motion_ids"].append(np.asarray(motion_id))

            observation = build_observation(
                height_scan=height_scan[None],
                root_pos_w=current_q[None, :3],
                root_quat_w=current_q[None, 3:7],
                root_lin_vel_w=current_qd[None, :3],
                root_ang_vel_w=current_qd[None, 3:6],
                joint_pos=current_q[None],
                joint_vel=current_qd[None],
                device=runtime.device_ref,
            )
            code = torch.as_tensor([codes[row]], dtype=torch.long, device=runtime.device_ref)
            length = int(original["lengths"][row])
            length_tensor = torch.as_tensor([length], dtype=torch.long, device=runtime.device_ref)
            with torch.no_grad():
                theta = runtime.predict_theta(observation, code)
                decoded = runtime.decode(
                    code,
                    theta,
                    lengths=length_tensor,
                    start_joint_pos=current_q[None],
                    start_joint_vel=current_qd[None],
                )["x_hat"]
                stats = runtime.gmvq_codec.norm_stats
                if stats is not None:
                    decoded = decoded * stats.std.to(decoded.device) + stats.mean.to(decoded.device)
            decoded_np = decoded[0, :length].cpu().numpy()
            split = {"joint_pos": decoded_np[:, :36].copy()}
            _chain_pose_segment(
                split,
                base_joint_pose=current_q,
                base_body_pos=None,
                base_body_quat=None,
                rotate_root_translation=False,
                rebase_articulated_joints=False,
            )
            trajectory.extend(np.asarray(split["joint_pos"], dtype=np.float32)[1:])

    result: dict[str, np.ndarray] = {}
    append_count = len(generated["codes"])
    for key in FEATURE_KEYS + ("codes", "theta", "motion_ids"):
        added = np.stack(generated[key])
        result[key] = np.concatenate((np.asarray(original[key]), added), axis=0)
    result["robot_asset_json"] = np.asarray(original["robot_asset_json"])
    output = args.output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **result)
    summary = {
        "schema": "gmvq_closed_loop_selector_dataset_v1",
        "source": str(args.dataset),
        "output": str(output),
        "original_count": int(len(codes)),
        "closed_loop_count": int(append_count),
        "total_count": int(len(result["codes"])),
        "motion_count": int(len(set(motion_ids))),
    }
    output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--surface-map", type=Path, required=True)
    parser.add_argument("--gmvq-checkpoint", type=Path, required=True)
    parser.add_argument("--code-selector", type=Path, required=True)
    parser.add_argument("--theta-selector", type=Path, required=True)
    parser.add_argument("--start-decoder", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
