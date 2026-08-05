#!/usr/bin/env python3
"""Generate a GMVQ reference by repeatedly sensing and decoding one atom.

Only frame zero of ``--initial-motion`` is used.  Every later observation is
constructed from the previously decoded endpoint and a freshly evaluated
terrain scan.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from motion_edit.generation.newton_direct_fk import canonicalize_motion_with_direct_newton_fk
from scripts.gmvq_ref.decode_selector_ref import _chain_pose_segment, _recompute_velocities
from scripts.gmvq_ref.extract_selector_height_dataset import (
    _load_surfaces,
    _quat_yaw_wxyz,
    _rot_yaw,
    _terrain_heights,
)
from scripts.gmvq_ref.selector_runtime import GMVQSelectorRuntime, build_observation
from somaforge_core.robot_assets import decode_robot_asset_json


def _load_npz(path: Path, *, allow_pickle: bool = False) -> dict[str, np.ndarray]:
    with np.load(path.expanduser(), allow_pickle=allow_pickle) as data:
        return {key: np.asarray(data[key]) for key in data.files}


def _scan(
    *,
    root_pos_w: np.ndarray,
    root_quat_wxyz: np.ndarray,
    local_grid: np.ndarray,
    surfaces: list,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    yaw = _quat_yaw_wxyz(root_quat_wxyz)
    points_w = _rot_yaw(local_grid, yaw) + root_pos_w
    heights, surface_indices = _terrain_heights(points_w[:, :2], surfaces)
    points_w[:, 2] = heights
    return (
        (heights - root_pos_w[2]).astype(np.float32),
        points_w.astype(np.float32),
        surface_indices,
    )


def _back_shift_from_surfaces(root_pos: np.ndarray, surfaces: list, distance: float) -> np.ndarray:
    if distance == 0.0:
        return np.zeros(3, dtype=np.float32)
    elevated = [surface for surface in surfaces if float(surface.origin[2]) > 0.05]
    if not elevated:
        raise ValueError("cannot derive backward direction: surface catalog has no elevated surface")
    target = min(
        elevated,
        key=lambda surface: float(np.linalg.norm(surface.origin[:2] - root_pos[:2])),
    ).origin[:2]
    forward = np.asarray(target - root_pos[:2], dtype=np.float64)
    norm = float(np.linalg.norm(forward))
    if norm < 1.0e-8:
        raise ValueError("cannot derive backward direction from coincident root/surface centers")
    shift = np.zeros(3, dtype=np.float32)
    shift[:2] = np.asarray(-float(distance) * forward / norm, dtype=np.float32)
    return shift


def _current_velocity(
    joint_poses: list[np.ndarray],
    fps: float,
    initial_velocity: np.ndarray,
) -> np.ndarray:
    if len(joint_poses) <= 1:
        return np.asarray(initial_velocity, dtype=np.float32).copy()
    pose = np.stack(joint_poses[-3:]).astype(np.float32)
    state = {
        "joint_pos": pose,
        "joint_vel": np.zeros((pose.shape[0], 35), dtype=np.float32),
        "fps": np.asarray(fps, dtype=np.float32),
    }
    _recompute_velocities(state)
    return np.asarray(state["joint_vel"][-1], dtype=np.float32)


def generate(args: argparse.Namespace) -> dict:
    initial = _load_npz(args.initial_motion, allow_pickle=True)
    decode_robot_asset_json(
        initial.get("robot_asset_json"),
        context=f"closed-loop initial motion {args.initial_motion}",
    )
    q_source = np.asarray(initial["joint_pos"], dtype=np.float32)
    if q_source.ndim != 2 or q_source.shape[1] != 36:
        raise ValueError(f"initial motion must contain joint_pos [T,36], got {q_source.shape}")
    fps = float(np.asarray(initial["fps"]).reshape(-1)[0])
    qd_source = np.asarray(initial["joint_vel"], dtype=np.float32)
    if qd_source.ndim != 2 or qd_source.shape[1] != 35:
        raise ValueError(f"initial motion must contain joint_vel [T,35], got {qd_source.shape}")
    initial_velocity = qd_source[0].copy()
    joint_names = np.asarray(initial["joint_names"])

    with np.load(args.selector_dataset.expanduser(), allow_pickle=False) as dataset:
        local_grid = np.asarray(dataset["local_grid"], dtype=np.float32)
        dataset_codes = np.asarray(dataset["codes"], dtype=np.int64)
        dataset_lengths = np.asarray(dataset["lengths"], dtype=np.int64)
        dataset_motion_ids = np.asarray(dataset["motion_ids"]).astype(str)
        dataset_start_frames = np.asarray(dataset["start_frames"], dtype=np.int64)
        theta_knn_raw = None
        theta_knn_targets = None
        if args.theta_knn_neighbors > 0:
            theta_knn_raw = np.concatenate(
                [
                    np.asarray(dataset[key], dtype=np.float32).reshape(len(dataset_codes), -1)
                    for key in (
                        "height_scan",
                        "root_pos_w",
                        "root_quat_w",
                        "root_lin_vel_w",
                        "root_ang_vel_w",
                        "joint_pos",
                        "joint_vel",
                    )
                ],
                axis=1,
            )
            theta_knn_targets = np.asarray(dataset["theta"], dtype=np.float32)
        code_length_prior = {
            int(code): int(np.rint(np.median(dataset_lengths[dataset_codes == code])))
            for code in np.unique(dataset_codes)
            if int(code) < runtime_code_limit(args.gmvq_checkpoint)
        }
        observed_transitions: dict[int, set[int]] = {}
        for motion_id in sorted(set(dataset_motion_ids)):
            rows = np.flatnonzero(
                (dataset_motion_ids == motion_id)
                & (dataset_codes < runtime_code_limit(args.gmvq_checkpoint))
            )
            rows = rows[np.argsort(dataset_start_frames[rows])]
            sequence = dataset_codes[rows].astype(int).tolist()
            if sequence:
                sequence.append(runtime_code_limit(args.gmvq_checkpoint))
            for source_code, target_code in zip(sequence[:-1], sequence[1:]):
                observed_transitions.setdefault(source_code, set()).add(target_code)

    surfaces = _load_surfaces(args.surface_jsonl.expanduser())
    q0 = q_source[0].copy()
    start_shift = _back_shift_from_surfaces(q0[:3], surfaces, args.start_back_distance)
    q0[:3] += start_shift

    runtime = GMVQSelectorRuntime(
        code_checkpoint=args.code_selector,
        theta_checkpoint=args.theta_selector,
        gmvq_checkpoint=args.gmvq_checkpoint,
        start_decoder_checkpoint=args.start_decoder,
        device=args.device,
    )
    stop_code = runtime.gmvq_codec.num_codes
    if runtime.num_codes != stop_code + 1:
        raise ValueError(
            f"closed-loop selector must contain {stop_code} motion codes plus STOP, "
            f"got {runtime.num_codes}"
        )
    theta_knn_norm = None
    if theta_knn_raw is not None:
        obs_dim = theta_knn_raw.shape[1]
        theta_knn_norm = (
            theta_knn_raw - runtime.theta_x_mean[:obs_dim].cpu().numpy()
        ) / runtime.theta_x_std[:obs_dim].cpu().numpy()

    trajectory: list[np.ndarray] = [q0]
    atom_reports: list[dict] = []
    stopped = False
    previous_code: int | None = None
    for atom_index in range(args.max_atoms):
        current_q = trajectory[-1]
        current_qd = _current_velocity(trajectory, fps, initial_velocity)
        height_scan, scan_points_w, surface_indices = _scan(
            root_pos_w=current_q[:3],
            root_quat_wxyz=current_q[3:7],
            local_grid=local_grid,
            surfaces=surfaces,
        )
        observation = build_observation(
            height_scan=height_scan[None, :],
            root_pos_w=current_q[None, :3],
            root_quat_w=current_q[None, 3:7],
            root_lin_vel_w=current_qd[None, :3],
            root_ang_vel_w=current_qd[None, 3:6],
            joint_pos=current_q[None, :],
            joint_vel=current_qd[None, :],
            device=runtime.device_ref,
        )
        with torch.no_grad():
            code_input = (observation - runtime.code_mean) / runtime.code_std
            code_logits = runtime.code_model(code_input)[0]
            raw_code = int(code_logits.argmax().item())
        code = raw_code
        allowed_codes: list[int] = []
        if args.enforce_observed_code_transitions and previous_code is not None:
            allowed_codes = sorted(observed_transitions.get(previous_code, ()))
            if not allowed_codes:
                raise ValueError(f"training data has no observed successor for code {previous_code}")
            allowed_tensor = torch.as_tensor(
                allowed_codes, dtype=torch.long, device=runtime.device_ref
            )
            code = int(allowed_tensor[code_logits[allowed_tensor].argmax()].item())
        report = {
            "atom_index": atom_index,
            "code": code,
            "raw_code": raw_code,
            "allowed_codes": allowed_codes,
            "root_pos_w": current_q[:3].astype(float).tolist(),
            "height_scan_min": float(height_scan.min()),
            "height_scan_max": float(height_scan.max()),
            "elevated_scan_point_count": int(
                np.sum(scan_points_w[:, 2] > 0.05)
            ),
            "visible_surface_indices": sorted(
                int(value) for value in np.unique(surface_indices) if int(value) >= 0
            ),
        }
        if code == stop_code:
            report["stop"] = True
            atom_reports.append(report)
            stopped = True
            break
        if code < 0 or code >= stop_code:
            raise ValueError(f"selector produced invalid code {code}")

        code_tensor = torch.as_tensor([code], dtype=torch.long, device=runtime.device_ref)
        theta_neighbor_indices: list[int] = []
        if theta_knn_norm is not None and theta_knn_targets is not None:
            obs_np = observation[0].cpu().numpy()
            obs_norm = (
                obs_np - runtime.theta_x_mean[: obs_np.shape[0]].cpu().numpy()
            ) / runtime.theta_x_std[: obs_np.shape[0]].cpu().numpy()
            candidates = np.flatnonzero(dataset_codes == code)
            distances = np.mean((theta_knn_norm[candidates] - obs_norm[None, :]) ** 2, axis=1)
            count = min(args.theta_knn_neighbors, len(candidates))
            selected_local = np.argpartition(distances, count - 1)[:count]
            selected = candidates[selected_local]
            selected_distance = distances[selected_local]
            if count == 1:
                weights = np.ones(1, dtype=np.float32)
            else:
                weights = 1.0 / np.maximum(selected_distance, 1.0e-8)
                weights /= weights.sum()
            theta_np = np.sum(theta_knn_targets[selected] * weights[:, None], axis=0)
            theta = torch.as_tensor(theta_np[None, :], device=runtime.device_ref)
            theta_neighbor_indices = selected.astype(int).tolist()
        else:
            with torch.no_grad():
                theta = runtime.predict_theta(observation, code_tensor)
        if code not in code_length_prior:
            raise ValueError(f"selector dataset has no duration prior for code {code}")
        length = int(np.clip(code_length_prior[code], args.min_atom_frames, runtime.gmvq_codec.t))
        length_tensor = torch.as_tensor([length], dtype=torch.long, device=runtime.device_ref)
        with torch.no_grad():
            decoded = runtime.decode(
                code_tensor,
                theta,
                lengths=length_tensor,
                start_joint_pos=current_q[None],
                start_joint_vel=current_qd[None],
            )["x_hat"]
            stats = runtime.gmvq_codec.norm_stats
            if stats is not None:
                decoded = decoded * stats.std.to(decoded.device) + stats.mean.to(decoded.device)
        values = decoded[0, :length].cpu().numpy()
        if values.shape[1] != 71:
            raise ValueError(f"closed-loop decoder expects 71D q/qd output, got {values.shape}")
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
        # Frame zero is the current state and is already present.
        trajectory.extend(atom_q[1:])
        report.update(
            {
                "stop": False,
                "predicted_length": length,
                "theta": theta[0].cpu().numpy().astype(float).tolist(),
                "theta_neighbor_indices": theta_neighbor_indices,
                "end_root_pos_w": atom_q[-1, :3].astype(float).tolist(),
            }
        )
        atom_reports.append(report)
        previous_code = code

    qpos = np.stack(trajectory).astype(np.float32)
    pre_fk = args.output.with_name(f"{args.output.stem}.pre_fk.npz")
    pre_motion = {
        "fps": np.asarray(fps, dtype=np.float32),
        "joint_pos": qpos,
        "joint_vel": np.zeros((qpos.shape[0], 35), dtype=np.float32),
        "joint_names": joint_names,
        "robot_asset_json": np.asarray(initial["robot_asset_json"]),
        "policy_ref_schema": np.asarray("policy_ref_v1"),
        "gmvq_closed_loop_report_json": np.asarray(
            json.dumps(
                {
                    "schema": "gmvq_observation_closed_loop_v1",
                    "initial_motion_frame_used": 0,
                    "source_future_frames_used": False,
                    "start_shift_xyz_m": start_shift.astype(float).tolist(),
                    "stop_code": stop_code,
                    "stopped": stopped,
                    "atom_reports": atom_reports,
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
        "schema": "gmvq_observation_closed_loop_summary_v1",
        "output": str(canonical.output_path),
        "pre_fk": str(pre_fk),
        "frame_count": int(qpos.shape[0]),
        "atom_count": len([item for item in atom_reports if not item["stop"]]),
        "stopped": stopped,
        "start_shift_xyz_m": start_shift.astype(float).tolist(),
        "codes": [int(item["code"]) for item in atom_reports],
        "lengths": [
            int(item["predicted_length"])
            for item in atom_reports
            if not item["stop"]
        ],
        "atom_reports": atom_reports,
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def runtime_code_limit(checkpoint: Path) -> int:
    payload = torch.load(checkpoint.expanduser(), map_location="cpu", weights_only=False)
    return int(payload["model_config"]["num_codes"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-motion", type=Path, required=True)
    parser.add_argument("--surface-jsonl", type=Path, required=True)
    parser.add_argument("--selector-dataset", type=Path, required=True)
    parser.add_argument("--gmvq-checkpoint", type=Path, required=True)
    parser.add_argument("--code-selector", type=Path, required=True)
    parser.add_argument("--theta-selector", type=Path, required=True)
    parser.add_argument("--start-decoder", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-back-distance", type=float, default=0.0)
    parser.add_argument(
        "--theta-knn-neighbors",
        type=int,
        default=0,
        help="Use observation-only same-code theta interpolation; 0 uses the learned theta MLP.",
    )
    parser.add_argument(
        "--enforce-observed-code-transitions",
        action="store_true",
        help="Mask current-observation code logits to transitions present in the training set.",
    )
    parser.add_argument("--max-atoms", type=int, default=20)
    parser.add_argument("--min-atom-frames", type=int, default=8)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--newton-device", default="cpu")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    generate(parse_args())


if __name__ == "__main__":
    main()
