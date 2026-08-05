#!/usr/bin/env python3
"""Generate a closed-loop reference with the unified current-frame future model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from gmvq.current_frame_future import (
    load_causal_segment_future_model,
    load_current_frame_future_model,
)
from gmvq.hyar_wrapper import FrozenGMVQCodec
from motion_edit.generation.newton_direct_fk import canonicalize_motion_with_direct_newton_fk
from somaforge_core.robot_assets import decode_robot_asset_json

from scripts.gmvq_ref.decode_selector_ref import _chain_pose_segment, _recompute_velocities
from scripts.gmvq_ref.extract_selector_height_dataset import _load_surfaces
from scripts.gmvq_ref.generate_closed_loop_ref import _current_velocity, _scan


def generate(args: argparse.Namespace) -> dict[str, object]:
    with np.load(args.initial_motion, allow_pickle=True) as data:
        initial = {key: np.asarray(data[key]) for key in data.files}
    decode_robot_asset_json(initial.get("robot_asset_json"), context=str(args.initial_motion))
    q_source = np.asarray(initial["joint_pos"], dtype=np.float32)
    qd_source = np.asarray(initial["joint_vel"], dtype=np.float32)
    if q_source.shape[1:] != (36,) or qd_source.shape[1:] != (35,):
        raise ValueError("initial motion must contain canonical [T,36] q and [T,35] qd")
    fps = float(np.asarray(initial["fps"]).reshape(-1)[0])
    checkpoint_payload = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    if checkpoint_payload.get("schema") == "gmvq_causal_segment_future_v1":
        model, payload = load_causal_segment_future_model(checkpoint_payload, device=args.device)
    else:
        model, payload = load_current_frame_future_model(checkpoint_payload, device=args.device)
    observation_mean = torch.as_tensor(payload["observation_norm"]["mean"], device=args.device)
    observation_std = torch.as_tensor(payload["observation_norm"]["std"], device=args.device)
    target_mean = torch.as_tensor(payload["target_norm"]["mean"], device=args.device)
    target_std = torch.as_tensor(payload["target_norm"]["std"], device=args.device)
    theta_mean = torch.as_tensor(payload["theta_norm"]["mean"], device=args.device)
    theta_std = torch.as_tensor(payload["theta_norm"]["std"], device=args.device)
    guide_codec = None
    if getattr(model, "use_guide", False):
        guide_codec = FrozenGMVQCodec(
            payload["training"]["gmvq_checkpoint_initialization"],
            device=args.device,
            trainable=False,
        )
    local_grid = np.asarray(payload["local_grid"], dtype=np.float32)
    length_prior = np.asarray(payload["length_prior"], dtype=np.int64)
    stop_code = int(payload["stop_code"])
    surfaces = _load_surfaces(args.surface_jsonl)

    trajectory = [q_source[0].copy()]
    initial_velocity = qd_source[0].copy()
    reports: list[dict[str, object]] = []
    stopped = False
    for atom_index in range(args.max_atoms):
        current_q = trajectory[-1]
        current_qd = _current_velocity(trajectory, fps, initial_velocity)
        height_scan, _, _ = _scan(
            root_pos_w=current_q[:3],
            root_quat_wxyz=current_q[3:7],
            local_grid=local_grid,
            surfaces=surfaces,
        )
        observation_raw = np.concatenate(
            (
                height_scan,
                current_q[:3],
                current_q[3:7],
                current_qd[:3],
                current_qd[3:6],
                current_q,
                current_qd,
            )
        ).astype(np.float32)
        local_q = current_q.copy()
        local_q[:3] = 0.0
        start_raw = torch.as_tensor(
            np.concatenate((local_q, current_qd))[None], dtype=torch.float32, device=args.device
        )
        observation = torch.as_tensor(observation_raw[None], device=args.device)
        observation = (observation - observation_mean) / observation_std
        start_state = (start_raw - target_mean) / target_std
        with torch.no_grad():
            guide = None
            if guide_codec is not None:
                _, preview_codes, preview_theta_normalized, _ = model._latent(observation)
                preview_lengths = model.length_prior[preview_codes]
                guide = start_state[:, None].expand(-1, model.max_frames, -1).clone()
                active = torch.where(preview_codes < stop_code)[0]
                if active.numel() > 0:
                    preview_theta = preview_theta_normalized * theta_std + theta_mean
                    guide[active] = guide_codec.decode_hybrid(
                        preview_codes[active],
                        preview_theta[active],
                        lengths=preview_lengths[active],
                    )["x_hat"]
            if hasattr(model, "use_guide"):
                output = model(observation, start_state=start_state, guide_trajectory=guide)
            else:
                output = model(observation, start_state=start_state)
        code = int(output["codes"][0].item())
        report: dict[str, object] = {
            "atom_index": atom_index,
            "code": code,
            "root_pos_w": current_q[:3].astype(float).tolist(),
        }
        if code == stop_code:
            report["stop"] = True
            reports.append(report)
            stopped = True
            break
        if code < 0 or code >= stop_code:
            raise ValueError(f"future model produced invalid code {code}")
        length = int(length_prior[code])
        physical = output["trajectory"] * target_std + target_mean
        values = physical[0, :length].cpu().numpy()
        split = {"joint_pos": values[:, :36].copy()}
        _chain_pose_segment(
            split,
            base_joint_pose=current_q,
            base_body_pos=None,
            base_body_quat=None,
            rotate_root_translation=False,
            rebase_articulated_joints=False,
        )
        atom_q = np.asarray(split["joint_pos"], dtype=np.float32)
        trajectory.extend(atom_q[1:])
        theta = output["theta"][0] * theta_std + theta_mean
        report.update(
            {
                "stop": False,
                "predicted_length": length,
                "theta": theta.cpu().numpy().astype(float).tolist(),
                "end_root_pos_w": atom_q[-1, :3].astype(float).tolist(),
            }
        )
        reports.append(report)

    qpos = np.stack(trajectory).astype(np.float32)
    pre_fk = args.output.with_name(f"{args.output.stem}.pre_fk.npz")
    pre_motion = {
        "fps": np.asarray(fps, dtype=np.float32),
        "joint_pos": qpos,
        "joint_vel": np.zeros((len(qpos), 35), dtype=np.float32),
        "joint_names": np.asarray(initial["joint_names"]),
        "robot_asset_json": np.asarray(initial["robot_asset_json"]),
        "policy_ref_schema": np.asarray("gmvq_current_frame_future_ref_v1"),
        "gmvq_closed_loop_report_json": np.asarray(
            json.dumps(
                {
                    "schema": "gmvq_current_frame_future_closed_loop_v1",
                    "source_future_frames_used": False,
                    "stop_code": stop_code,
                    "stopped": stopped,
                    "atom_reports": reports,
                },
                sort_keys=True,
            )
        ),
    }
    _recompute_velocities(pre_motion)
    pre_fk.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(pre_fk, **pre_motion)
    canonical = canonicalize_motion_with_direct_newton_fk(
        pre_fk,
        args.output,
        device=args.newton_device,
        overwrite=args.overwrite,
    )
    summary = {
        "schema": "gmvq_current_frame_future_closed_loop_summary_v1",
        "output": str(canonical.output_path),
        "pre_fk": str(pre_fk),
        "frame_count": int(len(qpos)),
        "atom_count": len([item for item in reports if not item["stop"]]),
        "stopped": stopped,
        "codes": [int(item["code"]) for item in reports],
        "lengths": [int(item["predicted_length"]) for item in reports if not item["stop"]],
        "atom_reports": reports,
    }
    args.output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--initial-motion", type=Path, required=True)
    parser.add_argument("--surface-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-atoms", type=int, default=20)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--newton-device", default="cpu")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    generate(parse_args())
