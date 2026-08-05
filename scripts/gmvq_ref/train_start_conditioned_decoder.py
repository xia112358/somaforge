#!/usr/bin/env python3
"""Train an absolute GMVQ decoder correction conditioned on the actual atom start."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from gmvq.g1_fk import CanonicalG1TorchFK
from gmvq.hyar_wrapper import FrozenGMVQCodec
from somaforge_core import G1_29DOF_JOINT_ORDER
from somaforge_core.robot_assets import decode_robot_asset_json

from scripts.gmvq_ref.start_conditioned_decoder import StartConditionedDecoder


WBT_TRACKED_LINK_NAMES = (
    "pelvis",
    "left_hip_roll_link",
    "left_knee_link",
    "left_ankle_roll_link",
    "right_hip_roll_link",
    "right_knee_link",
    "right_ankle_roll_link",
    "torso_link",
    "left_shoulder_roll_link",
    "left_elbow_link",
    "left_wrist_yaw_link",
    "right_shoulder_roll_link",
    "right_elbow_link",
    "right_wrist_yaw_link",
)


def _group_masks(groups: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    unique = np.asarray(sorted(set(str(item) for item in groups)))
    rng = np.random.default_rng(seed)
    rng.shuffle(unique)
    train_groups = set(unique[: int(round(0.8 * len(unique)))])
    values = np.asarray(groups).astype(str)
    train = np.asarray([item in train_groups for item in values])
    return train, ~train


def _target_indices(
    *,
    selector_motion_ids: np.ndarray,
    selector_codes: np.ndarray,
    pack_motion_ids: np.ndarray,
) -> np.ndarray:
    lookup: dict[tuple[str, int], int] = {}
    for motion_id in dict.fromkeys(pack_motion_ids.tolist()):
        pack_rows = np.flatnonzero(pack_motion_ids == motion_id)
        selector_rows = np.flatnonzero(selector_motion_ids == motion_id)
        if len(selector_rows) < len(pack_rows):
            raise ValueError(f"selector dataset has too few rows for {motion_id}")
        first_codes = selector_codes[selector_rows[: len(pack_rows)]]
        if len(set(first_codes.tolist())) != len(pack_rows):
            raise ValueError(f"first selector pass has duplicate codes for {motion_id}")
        for pack_row, code in zip(pack_rows, first_codes, strict=True):
            lookup[(motion_id, int(code))] = int(pack_row)
    try:
        return np.asarray(
            [
                lookup[(motion_id, int(code))]
                for motion_id, code in zip(selector_motion_ids, selector_codes, strict=True)
            ],
            dtype=np.int64,
        )
    except KeyError as exc:
        raise ValueError(f"selector state has no real augmented target: {exc.args[0]}") from exc


def _masked_mse(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    feature_weight: torch.Tensor,
) -> torch.Tensor:
    weighted = (prediction - target).square() * mask.unsqueeze(-1) * feature_weight
    return weighted.sum() / (mask.sum() * feature_weight.sum()).clamp_min(1.0)


def _endpoint_mse(
    prediction: torch.Tensor,
    target: torch.Tensor,
    lengths: torch.Tensor,
) -> torch.Tensor:
    rows = torch.arange(prediction.shape[0], device=prediction.device)
    frame = (lengths - 1).clamp_min(0)
    return (prediction[rows, frame] - target[rows, frame]).square().mean()


def _condition_mse(prediction: torch.Tensor, start_state: torch.Tensor, condition_mask: torch.Tensor) -> torch.Tensor:
    weighted = (prediction - start_state).square() * condition_mask
    return weighted.sum() / (prediction.shape[0] * condition_mask.sum()).clamp_min(1.0)


def _quat_mul_wxyz(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    aw, ax, ay, az = a.unbind(dim=-1)
    bw, bx, by, bz = b.unbind(dim=-1)
    return torch.stack(
        (
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ),
        dim=-1,
    )


def _rotation_vector_quat_wxyz(value: torch.Tensor) -> torch.Tensor:
    angle = value.norm(dim=-1, keepdim=True)
    half = 0.5 * angle
    scale = torch.where(angle > 1.0e-7, torch.sin(half) / angle, 0.5 - angle.square() / 48.0)
    return torch.cat((torch.cos(half), value * scale), dim=-1)


def _constant_velocity_continuation(
    start_state: torch.Tensor,
    *,
    mean: torch.Tensor,
    std: torch.Tensor,
    frames: int,
    fps: float,
) -> torch.Tensor:
    """Build a physical-space constant-velocity prefix from a normalized entry state."""
    count = max(int(frames), 0)
    mean = mean.to(start_state).reshape(-1)
    std = std.to(start_state).reshape(-1)
    start = start_state * std + mean
    time = torch.arange(1, count + 1, dtype=start_state.dtype, device=start_state.device) / float(fps)
    time = time.view(1, count, 1)
    root_pos = start[:, None, :3] + start[:, None, 36:39] * time
    joint_pos = start[:, None, 7:36] + start[:, None, 42:] * time
    rotation = _rotation_vector_quat_wxyz(start[:, None, 39:42] * time)
    root_quat = _quat_mul_wxyz(rotation, start[:, None, 3:7])
    root_quat = root_quat / root_quat.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
    velocity = start[:, None, 36:].expand(-1, count, -1)
    return torch.cat((root_pos, root_quat, joint_pos, velocity), dim=-1)


def _connection_mse(
    prediction: torch.Tensor,
    *,
    start_state: torch.Tensor,
    valid: torch.Tensor,
    feature_weight: torch.Tensor,
    mean: torch.Tensor,
    std: torch.Tensor,
    frames: int,
    fps: float,
    decay_power: float,
) -> torch.Tensor:
    """Match a short prefix to constant-velocity continuation from the entry state."""
    count = min(int(frames), prediction.shape[1] - 1)
    if count <= 0:
        return prediction.new_zeros(())
    mean = mean.to(prediction).reshape(-1)
    std = std.to(prediction).reshape(-1)
    continuation = _constant_velocity_continuation(
        start_state,
        mean=mean,
        std=std,
        frames=count,
        fps=fps,
    )
    continuation = (continuation - mean) / std

    time = torch.arange(1, count + 1, dtype=prediction.dtype, device=prediction.device)
    time = time.view(1, count, 1)
    temporal_weight = (1.0 - time / float(count + 1)).pow(float(decay_power))
    frame_valid = valid[:, 1 : count + 1].unsqueeze(-1)
    weight = frame_valid * temporal_weight * feature_weight.view(1, 1, -1)
    return ((prediction[:, 1 : count + 1] - continuation).square() * weight).sum() / weight.sum().clamp_min(1.0)


def _taskspace_connection_mse(
    prediction: torch.Tensor,
    *,
    start_state: torch.Tensor,
    valid: torch.Tensor,
    mean: torch.Tensor,
    std: torch.Tensor,
    frames: int,
    fps: float,
    decay_power: float,
    fk: CanonicalG1TorchFK | None,
) -> torch.Tensor:
    """Match the WBT body prefix to entry-state continuation in metric task space."""
    count = min(int(frames), prediction.shape[1] - 1)
    if count <= 0 or fk is None:
        return prediction.new_zeros(())
    mean = mean.to(prediction).reshape(-1)
    std = std.to(prediction).reshape(-1)
    predicted_physical = prediction[:, 1 : count + 1] * std + mean
    continuation = _constant_velocity_continuation(
        start_state,
        mean=mean,
        std=std,
        frames=count,
        fps=fps,
    )
    predicted_body = fk(predicted_physical[..., :36])
    continuation_body = fk(continuation[..., :36])
    time = torch.arange(1, count + 1, dtype=prediction.dtype, device=prediction.device)
    temporal_weight = (1.0 - time / float(count + 1)).pow(float(decay_power)).view(1, count, 1, 1)
    weight = valid[:, 1 : count + 1, None, None] * temporal_weight
    squared_error = (predicted_body - continuation_body).square()
    denominator = (weight.sum() * predicted_body.shape[-2] * predicted_body.shape[-1]).clamp_min(1.0)
    return (squared_error * weight).sum() / denominator


@torch.no_grad()
def _evaluate(
    *,
    model: StartConditionedDecoder,
    codec: FrozenGMVQCodec,
    codes: torch.Tensor,
    theta: torch.Tensor,
    start_state: torch.Tensor,
    target: torch.Tensor,
    lengths: torch.Tensor,
    valid: torch.Tensor,
    indices: torch.Tensor,
    feature_weight: torch.Tensor,
    args: argparse.Namespace,
    condition_mask: torch.Tensor,
    fk: CanonicalG1TorchFK | None,
) -> dict[str, float]:
    model.eval()
    totals = {
        "trajectory": 0.0,
        "start": 0.0,
        "connection": 0.0,
        "taskspace_connection": 0.0,
        "velocity": 0.0,
        "endpoint": 0.0,
    }
    count = 0
    for batch in indices.split(128):
        base = codec.decode_hybrid(codes[batch], theta[batch], lengths=lengths[batch])["x_hat"]
        prediction = model(
            base,
            start_state=start_state[batch],
            codes=codes[batch],
            theta=theta[batch],
            lengths=lengths[batch],
        )
        trajectory = _masked_mse(prediction, target[batch], valid[batch], feature_weight)
        start = _condition_mse(prediction[:, 0], start_state[batch], condition_mask)
        connection = _connection_mse(
            prediction,
            start_state=start_state[batch],
            valid=valid[batch],
            feature_weight=feature_weight,
            mean=codec.norm_stats.mean,
            std=codec.norm_stats.std,
            frames=args.connection_frames,
            fps=args.fps,
            decay_power=args.connection_decay_power,
        )
        taskspace_connection = _taskspace_connection_mse(
            prediction,
            start_state=start_state[batch],
            valid=valid[batch],
            mean=codec.norm_stats.mean,
            std=codec.norm_stats.std,
            frames=args.connection_frames,
            fps=args.fps,
            decay_power=args.connection_decay_power,
            fk=fk,
        )
        pair_mask = valid[batch, 1:] & valid[batch, :-1]
        velocity = _masked_mse(
            prediction[:, 1:] - prediction[:, :-1],
            target[batch, 1:] - target[batch, :-1],
            pair_mask,
            feature_weight,
        )
        endpoint = _endpoint_mse(prediction, target[batch], lengths[batch])
        size = int(batch.numel())
        for key, value in (
            ("trajectory", trajectory),
            ("start", start),
            ("connection", connection),
            ("taskspace_connection", taskspace_connection),
            ("velocity", velocity),
            ("endpoint", endpoint),
        ):
            totals[key] += float(value.item()) * size
        count += size
    metrics = {key: value / max(count, 1) for key, value in totals.items()}
    metrics["objective"] = (
        metrics["trajectory"]
        + args.start_weight * metrics["start"]
        + args.connection_weight * metrics["connection"]
        + args.taskspace_connection_weight * metrics["taskspace_connection"]
        + args.velocity_weight * metrics["velocity"]
        + args.endpoint_weight * metrics["endpoint"]
    )
    return metrics


def train(args: argparse.Namespace) -> dict[str, object]:
    device = torch.device(args.device)
    with np.load(args.selector_dataset.expanduser(), allow_pickle=False) as data:
        robot_asset = decode_robot_asset_json(
            data.get("robot_asset_json"), context=f"selector dataset {args.selector_dataset}"
        )
        all_codes = np.asarray(data["codes"], dtype=np.int64)
        keep = all_codes < args.stop_code
        codes_np = all_codes[keep]
        theta_np = np.asarray(data["theta"], dtype=np.float32)[keep]
        motion_ids = np.asarray(data["motion_ids"]).astype(str)[keep]
        start_q = np.asarray(data["joint_pos"], dtype=np.float32)[keep].copy()
        start_q[:, :3] = 0.0
        start_qd = np.asarray(data["joint_vel"], dtype=np.float32)[keep]
    with np.load(args.segment_pack.expanduser(), allow_pickle=False) as pack:
        target_indices = _target_indices(
            selector_motion_ids=motion_ids,
            selector_codes=codes_np,
            pack_motion_ids=np.asarray(pack["motion_ids"]).astype(str),
        )
        segments_np = np.asarray(pack["segments"], dtype=np.float32)[target_indices]
        lengths_np = np.asarray(pack["lengths"], dtype=np.int64)[target_indices]
        valid_np = np.asarray(pack["valid_mask"], dtype=bool)[target_indices]

    codec = FrozenGMVQCodec(args.gmvq_checkpoint, device=device, trainable=False)
    target = codec.normalize(torch.from_numpy(segments_np).to(device))
    start_raw = torch.from_numpy(np.concatenate((start_q, start_qd), axis=1)).to(device)
    stats = codec.norm_stats
    if stats is None:
        raise ValueError("connection loss requires GMVQ normalization statistics")
    start_state = start_raw
    start_state = (start_state - stats.mean.to(device).reshape(-1)) / stats.std.to(device).reshape(-1)
    # Only the first frame is replaced by the actual current state.  Every
    # later frame remains the original absolute augmented-motion target.
    condition_mask = torch.ones(segments_np.shape[-1], dtype=torch.float32, device=device)
    if not args.condition_root:
        condition_mask[:7] = 0.0
        condition_mask[36:42] = 0.0
    target = target.clone()
    target[:, 0] = target[:, 0] * (1.0 - condition_mask) + start_state * condition_mask
    codes = torch.from_numpy(codes_np).to(device)
    theta = torch.from_numpy(theta_np).to(device)
    lengths = torch.from_numpy(lengths_np).to(device)
    valid = torch.from_numpy(valid_np).to(device)

    model = StartConditionedDecoder(
        feature_dim=segments_np.shape[-1],
        num_codes=codec.num_codes,
        theta_dim=codec.theta_dim,
        hidden_dim=args.hidden_dim,
        depth=args.depth,
        condition_decay_power=args.condition_decay_power,
        condition_root=args.condition_root,
        anchor_start=args.anchor_start,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    train_mask_np, eval_mask_np = _group_masks(motion_ids, args.seed)
    train_indices = torch.from_numpy(np.flatnonzero(train_mask_np)).to(device)
    eval_indices = torch.from_numpy(np.flatnonzero(eval_mask_np)).to(device)
    feature_weight = torch.ones(segments_np.shape[-1], dtype=torch.float32, device=device)
    feature_weight[:36] = args.qpos_weight
    fk = None
    if args.taskspace_connection_weight > 0.0:
        fk = CanonicalG1TorchFK(
            joint_names=list(G1_29DOF_JOINT_ORDER),
            link_names=list(WBT_TRACKED_LINK_NAMES),
        ).to(device)
        fk.eval()

    before = _evaluate(
        model=model,
        codec=codec,
        codes=codes,
        theta=theta,
        start_state=start_state,
        target=target,
        lengths=lengths,
        valid=valid,
        indices=eval_indices,
        feature_weight=feature_weight,
        args=args,
        condition_mask=condition_mask,
        fk=fk,
    )
    best_objective = before["objective"]
    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    generator = torch.Generator(device=device).manual_seed(args.seed)
    for step in range(1, args.steps + 1):
        permutation = train_indices[torch.randperm(train_indices.numel(), generator=generator, device=device)]
        model.train()
        for batch in permutation.split(args.batch_size):
            with torch.no_grad():
                base = codec.decode_hybrid(codes[batch], theta[batch], lengths=lengths[batch])["x_hat"]
            prediction = model(
                base,
                start_state=start_state[batch],
                codes=codes[batch],
                theta=theta[batch],
                lengths=lengths[batch],
            )
            trajectory = _masked_mse(prediction, target[batch], valid[batch], feature_weight)
            start = _condition_mse(prediction[:, 0], start_state[batch], condition_mask)
            connection = _connection_mse(
                prediction,
                start_state=start_state[batch],
                valid=valid[batch],
                feature_weight=feature_weight,
                mean=codec.norm_stats.mean,
                std=codec.norm_stats.std,
                frames=args.connection_frames,
                fps=args.fps,
                decay_power=args.connection_decay_power,
            )
            taskspace_connection = _taskspace_connection_mse(
                prediction,
                start_state=start_state[batch],
                valid=valid[batch],
                mean=codec.norm_stats.mean,
                std=codec.norm_stats.std,
                frames=args.connection_frames,
                fps=args.fps,
                decay_power=args.connection_decay_power,
                fk=fk,
            )
            pair_mask = valid[batch, 1:] & valid[batch, :-1]
            velocity = _masked_mse(
                prediction[:, 1:] - prediction[:, :-1],
                target[batch, 1:] - target[batch, :-1],
                pair_mask,
                feature_weight,
            )
            endpoint = _endpoint_mse(prediction, target[batch], lengths[batch])
            loss = (
                trajectory
                + args.start_weight * start
                + args.connection_weight * connection
                + args.taskspace_connection_weight * taskspace_connection
                + args.velocity_weight * velocity
                + args.endpoint_weight * endpoint
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            metrics = _evaluate(
                model=model,
                codec=codec,
                codes=codes,
                theta=theta,
                start_state=start_state,
                target=target,
                lengths=lengths,
                valid=valid,
                indices=eval_indices,
                feature_weight=feature_weight,
                args=args,
                condition_mask=condition_mask,
                fk=fk,
            )
            print(
                f"step={step} objective={metrics['objective']:.7f} "
                f"trajectory={metrics['trajectory']:.7f} start={metrics['start']:.7f} "
                f"connection={metrics['connection']:.7f} "
                f"taskspace_connection={metrics['taskspace_connection']:.7f} "
                f"velocity={metrics['velocity']:.7f}",
                flush=True,
            )
            if metrics["objective"] < best_objective:
                best_objective = metrics["objective"]
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    model.load_state_dict(best_state)
    after = _evaluate(
        model=model,
        codec=codec,
        codes=codes,
        theta=theta,
        start_state=start_state,
        target=target,
        lengths=lengths,
        valid=valid,
        indices=eval_indices,
        feature_weight=feature_weight,
        args=args,
        condition_mask=condition_mask,
        fk=fk,
    )
    output = args.output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "model_config": model.config(),
            "robot_asset": robot_asset,
            "gmvq_checkpoint": str(args.gmvq_checkpoint),
            "selector_dataset": str(args.selector_dataset),
            "segment_pack": str(args.segment_pack),
            "loss_config": {
                "qpos_weight": args.qpos_weight,
                "start_weight": args.start_weight,
                "connection_weight": args.connection_weight,
                "taskspace_connection_weight": args.taskspace_connection_weight,
                "taskspace_connection_links": list(WBT_TRACKED_LINK_NAMES),
                "connection_frames": args.connection_frames,
                "connection_decay_power": args.connection_decay_power,
                "fps": args.fps,
                "velocity_weight": args.velocity_weight,
                "endpoint_weight": args.endpoint_weight,
                "condition_root": args.condition_root,
                "anchor_start": args.anchor_start,
            },
        },
        output,
    )
    summary: dict[str, object] = {
        "schema": "gmvq_start_conditioned_decoder_v1",
        "output": str(output),
        "train_count": int(train_mask_np.sum()),
        "eval_count": int(eval_mask_np.sum()),
        "steps": args.steps,
        "before": before,
        "after": after,
    }
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-dataset", type=Path, required=True)
    parser.add_argument("--segment-pack", type=Path, required=True)
    parser.add_argument("--gmvq-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stop-code", type=int, default=13)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--condition-decay-power", type=float, default=4.0)
    parser.add_argument("--condition-root", action="store_true")
    parser.add_argument("--anchor-start", action="store_true")
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--qpos-weight", type=float, default=4.0)
    parser.add_argument("--start-weight", type=float, default=20.0)
    parser.add_argument("--connection-weight", type=float, default=5.0)
    parser.add_argument("--taskspace-connection-weight", type=float, default=0.0)
    parser.add_argument("--connection-frames", type=int, default=8)
    parser.add_argument("--connection-decay-power", type=float, default=1.0)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--velocity-weight", type=float, default=1.0)
    parser.add_argument("--endpoint-weight", type=float, default=2.0)
    parser.add_argument("--eval-every", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260801)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
