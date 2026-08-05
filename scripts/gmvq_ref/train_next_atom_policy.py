#!/usr/bin/env python3
"""Train one shared next-atom selector and package a candidate runtime bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from gmvq.policy_reference import GMVQPolicyReferenceRuntime, SharedNextAtomSelector
from somaforge_core.robot_assets import decode_robot_asset_json


FEATURE_KEYS = (
    "height_scan",
    "root_pos_w",
    "root_quat_w",
    "root_lin_vel_w",
    "root_ang_vel_w",
    "joint_pos",
    "joint_vel",
)


def _features(data: np.lib.npyio.NpzFile) -> np.ndarray:
    return np.concatenate(
        [np.asarray(data[key], dtype=np.float32).reshape(len(data[key]), -1) for key in FEATURE_KEYS], axis=1
    )


def _runtime_features(height_scan: np.ndarray, joint_pos: np.ndarray, joint_vel: np.ndarray) -> np.ndarray:
    return np.concatenate(
        (
            np.asarray(height_scan, dtype=np.float32),
            np.asarray(joint_pos[:, :3], dtype=np.float32),
            np.asarray(joint_pos[:, 3:7], dtype=np.float32),
            np.asarray(joint_vel[:, :3], dtype=np.float32),
            np.asarray(joint_vel[:, 3:6], dtype=np.float32),
            np.asarray(joint_pos, dtype=np.float32),
            np.asarray(joint_vel, dtype=np.float32),
        ),
        axis=1,
    )


def _previous_codes(motion_ids: np.ndarray, starts: np.ndarray, codes: np.ndarray) -> np.ndarray:
    result = np.full(len(codes), -1, dtype=np.int64)
    for motion_id in sorted(set(motion_ids.astype(str))):
        rows = np.flatnonzero(motion_ids.astype(str) == motion_id)
        rows = rows[np.argsort(starts[rows])]
        if rows.size > 1:
            result[rows[1:]] = codes[rows[:-1]]
    return result


def _split(motion_ids: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    groups = np.asarray(sorted(set(motion_ids.astype(str))))
    rng = np.random.default_rng(seed)
    rng.shuffle(groups)
    train_groups = set(groups[:38])
    val_groups = set(groups[38:43])
    train = np.asarray([str(value) in train_groups for value in motion_ids])
    val = np.asarray([str(value) in val_groups for value in motion_ids])
    test = ~(train | val)
    return train, val, test


@torch.no_grad()
def _metrics(
    model: SharedNextAtomSelector,
    x: torch.Tensor,
    x_raw: torch.Tensor,
    previous: torch.Tensor,
    codes: torch.Tensor,
    theta: torch.Tensor,
    mask: torch.Tensor,
    transition_mask: torch.Tensor,
    theta_mean: torch.Tensor,
    theta_std: torch.Tensor,
    stop_code: int,
    teacher: GMVQPolicyReferenceRuntime,
) -> dict[str, float]:
    model.eval()
    _, predicted_code, predicted_theta_norm = model(x[mask], previous[mask], transition_mask)
    active = codes[mask] < stop_code
    predicted_theta = predicted_theta_norm[active] * theta_std + theta_mean
    active_codes = codes[mask][active]
    one_hot = F.one_hot(active_codes, num_classes=stop_code + 1).to(x.dtype)
    teacher_input = torch.cat((x_raw[mask][active], one_hot), dim=-1)
    teacher_theta_norm = teacher.theta_model(
        (teacher_input - teacher.theta_x_mean) / teacher.theta_x_std
    )
    teacher_theta = teacher_theta_norm * teacher.theta_std + teacher.theta_mean
    return {
        "count": int(mask.sum().item()),
        "code_accuracy": float((predicted_code == codes[mask]).float().mean().item()),
        "theta_mse": float(F.mse_loss(predicted_theta, theta[mask][active]).item()),
        "teacher_theta_mse": float(F.mse_loss(predicted_theta, teacher_theta).item()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--base-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--online-boundaries", type=Path, nargs="*", default=[])
    parser.add_argument("--online-repeat", type=int, default=4)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=3.0e-4)
    parser.add_argument("--theta-weight", type=float, default=4.0)
    parser.add_argument("--distill-weight", type=float, default=4.0)
    parser.add_argument("--distill-jitter-std", type=float, default=0.05)
    parser.add_argument("--branch-dim", type=int, default=128)
    parser.add_argument("--context-dim", type=int, default=256)
    parser.add_argument("--code-embed-dim", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20260802)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    with np.load(args.dataset, allow_pickle=False) as data:
        robot_asset = decode_robot_asset_json(data["robot_asset_json"], context=str(args.dataset))
        offline_x_raw = _features(data)
        codes_np = np.asarray(data["codes"], dtype=np.int64)
        theta_np = np.asarray(data["theta"], dtype=np.float32)
        starts = np.asarray(data["start_frames"], dtype=np.int64)
        motion_ids = np.asarray(data["motion_ids"]).astype(str)
        local_grid = np.asarray(data["local_grid"], dtype=np.float32)
    previous_np = _previous_codes(motion_ids, starts, codes_np)
    offline_train, offline_val, offline_test = _split(motion_ids, args.seed)
    online_x: list[np.ndarray] = []
    online_previous: list[np.ndarray] = []
    online_codes: list[np.ndarray] = []
    online_theta: list[np.ndarray] = []
    for boundary_path in args.online_boundaries:
        with np.load(boundary_path, allow_pickle=False) as boundary:
            if str(boundary["schema"].item()) != "gmvq_online_boundary_dataset_v1":
                raise ValueError(f"unsupported online boundary dataset: {boundary_path}")
            online_x.append(
                _runtime_features(boundary["height_scan"], boundary["joint_pos"], boundary["joint_vel"])
            )
            online_previous.append(np.asarray(boundary["previous_code"], dtype=np.int64).reshape(-1))
            online_codes.append(np.asarray(boundary["code"], dtype=np.int64).reshape(-1))
            online_theta.append(np.asarray(boundary["theta"], dtype=np.float32))
    if args.online_repeat < 1:
        raise ValueError("online-repeat must be positive")
    if online_x:
        repeated_online_x = np.tile(np.concatenate(online_x), (args.online_repeat, 1))
        repeated_online_previous = np.tile(np.concatenate(online_previous), args.online_repeat)
        repeated_online_codes = np.tile(np.concatenate(online_codes), args.online_repeat)
        repeated_online_theta = np.tile(np.concatenate(online_theta), (args.online_repeat, 1))
        x_raw = np.concatenate((offline_x_raw, repeated_online_x), axis=0)
        previous_np = np.concatenate((previous_np, repeated_online_previous), axis=0)
        codes_np = np.concatenate((codes_np, repeated_online_codes), axis=0)
        theta_np = np.concatenate((theta_np, repeated_online_theta), axis=0)
        online_count = len(repeated_online_codes)
    else:
        x_raw = offline_x_raw
        online_count = 0
    train_np = np.concatenate((offline_train, np.ones(online_count, dtype=np.bool_)))
    val_np = np.concatenate((offline_val, np.zeros(online_count, dtype=np.bool_)))
    test_np = np.concatenate((offline_test, np.zeros(online_count, dtype=np.bool_)))
    active_train = train_np & (codes_np < int(codes_np.max()))
    x_mean = x_raw[train_np].mean(0).astype(np.float32)
    x_std = np.maximum(x_raw[train_np].std(0), 1.0e-6).astype(np.float32)
    theta_mean = theta_np[active_train].mean(0).astype(np.float32)
    theta_std = np.maximum(theta_np[active_train].std(0), 1.0e-6).astype(np.float32)
    x_np = ((x_raw - x_mean) / x_std).astype(np.float32)
    theta_norm_np = ((theta_np - theta_mean) / theta_std).astype(np.float32)

    base = torch.load(args.base_bundle, map_location="cpu", weights_only=False)
    stop_code = int(base["stop_code"])
    if stop_code != int(codes_np.max()):
        raise ValueError(f"dataset STOP={int(codes_np.max())} disagrees with bundle STOP={stop_code}")
    if not np.allclose(local_grid, np.asarray(base["local_grid"]), atol=1.0e-6):
        raise ValueError("selector dataset local grid disagrees with runtime bundle")
    device = torch.device(args.device)
    transition_mask = torch.as_tensor(base["transition_mask"], dtype=torch.bool, device=device)
    teacher = GMVQPolicyReferenceRuntime(base, device=device)
    model = SharedNextAtomSelector(
        height_dim=local_grid.shape[0],
        state_dim=x_np.shape[1] - local_grid.shape[0],
        num_codes=stop_code + 1,
        theta_dim=theta_np.shape[1],
        branch_dim=args.branch_dim,
        context_dim=args.context_dim,
        code_embed_dim=args.code_embed_dim,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1.0e-4)
    x = torch.from_numpy(x_np).to(device)
    x_raw = torch.from_numpy(x_raw).to(device)
    previous = torch.from_numpy(previous_np).to(device)
    codes = torch.from_numpy(codes_np).to(device)
    theta = torch.from_numpy(theta_np).to(device)
    theta_norm = torch.from_numpy(theta_norm_np).to(device)
    train = torch.from_numpy(train_np).to(device)
    val = torch.from_numpy(val_np).to(device)
    test = torch.from_numpy(test_np).to(device)
    theta_mean_t = torch.from_numpy(theta_mean).to(device)
    theta_std_t = torch.from_numpy(theta_std).to(device)
    x_mean_t = torch.from_numpy(x_mean).to(device)
    x_std_t = torch.from_numpy(x_std).to(device)
    train_rows = torch.where(train)[0]
    best_state: dict[str, torch.Tensor] | None = None
    best_score = float("inf")
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = train_rows[torch.randperm(len(train_rows), device=train_rows.device)]
        for start in range(0, len(order), args.batch_size):
            rows = order[start : start + args.batch_size]
            logits, predicted_code, predicted_theta = model(x[rows], previous[rows], transition_mask)
            code_loss = F.cross_entropy(logits, codes[rows])
            active = codes[rows] < stop_code
            theta_loss = F.smooth_l1_loss(predicted_theta[active], theta_norm[rows][active])
            loss = code_loss + args.theta_weight * theta_loss
            if args.distill_weight > 0.0:
                active_rows = rows[active]
                jittered_x = x[active_rows] + args.distill_jitter_std * torch.randn_like(x[active_rows])
                jittered_observation = jittered_x * x_std_t + x_mean_t
                active_codes = codes[active_rows]
                one_hot = F.one_hot(active_codes, num_classes=stop_code + 1).to(jittered_observation.dtype)
                teacher_input = torch.cat((jittered_observation, one_hot), dim=-1)
                with torch.no_grad():
                    teacher_theta_norm = teacher.theta_model(
                        (teacher_input - teacher.theta_x_mean) / teacher.theta_x_std
                    )
                    teacher_theta = teacher_theta_norm * teacher.theta_std + teacher.theta_mean
                    teacher_target = (teacher_theta - theta_mean_t) / theta_std_t
                _, _, jittered_theta = model(jittered_x, previous[active_rows], transition_mask)
                distill_loss = F.smooth_l1_loss(jittered_theta, teacher_target)
                loss = loss + args.distill_weight * distill_loss
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        if epoch == 1 or epoch % 25 == 0 or epoch == args.epochs:
            val_metrics = _metrics(
                model,
                x,
                x_raw,
                previous,
                codes,
                theta,
                val,
                transition_mask,
                theta_mean_t,
                theta_std_t,
                stop_code,
                teacher,
            )
            score = (
                val_metrics["theta_mse"]
                + args.distill_weight * val_metrics["teacher_theta_mse"]
                + (1.0 - val_metrics["code_accuracy"])
            )
            print(
                f"epoch={epoch} val_code_acc={val_metrics['code_accuracy']:.4f} "
                f"val_theta_mse={val_metrics['theta_mse']:.6f} "
                f"val_teacher_theta_mse={val_metrics['teacher_theta_mse']:.6f}"
            )
            if score < best_score:
                best_score = score
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    next_atom_payload = {
        "model_config": model.config(),
        "model_state": model.state_dict(),
        "observation_norm": {"mean": x_mean, "std": x_std},
        "theta_norm": {"mean": theta_mean, "std": theta_std},
        "feature_keys": list(FEATURE_KEYS),
        "training_dataset": "runtime/current/gmvq/data/climb00_pairwise48/selector.npz",
        "robot_asset": robot_asset,
    }
    candidate = dict(base)
    candidate.pop("code_selector", None)
    candidate.pop("theta_selector", None)
    candidate["next_atom_model"] = next_atom_payload
    candidate["runtime_architecture"] = "shared_next_atom_selector_v1"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(candidate, args.output)

    metrics = {
        split: _metrics(
            model,
            x,
            x_raw,
            previous,
            codes,
            theta,
            mask,
            transition_mask,
            theta_mean_t,
            theta_std_t,
            stop_code,
            teacher,
        )
        for split, mask in (("train", train), ("validation", val), ("test", test))
    }
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    old_parameter_count = sum(parameter.numel() for parameter in teacher.code_model.parameters()) + sum(
        parameter.numel() for parameter in teacher.theta_model.parameters()
    )
    summary = {
        "schema": "gmvq_shared_next_atom_training_v1",
        "dataset": str(args.dataset),
        "base_bundle": str(args.base_bundle),
        "output": str(args.output),
        "epochs": args.epochs,
        "distill_weight": args.distill_weight,
        "distill_jitter_std": args.distill_jitter_std,
        "online_boundary_datasets": [str(path) for path in args.online_boundaries],
        "online_training_sample_count": online_count,
        "model_config": model.config(),
        "selector_parameter_count": parameter_count,
        "old_selector_parameter_count": old_parameter_count,
        "metrics": metrics,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
