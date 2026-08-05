#!/usr/bin/env python3
"""Fine-tune the current-frame future model through complete generated atom chains."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from gmvq.current_frame_future import CausalSegmentFutureModel, canonical_boundary_state
from gmvq.g1_fk import CanonicalG1TorchFK, quat_mul_wxyz
from gmvq.hyar_wrapper import FrozenGMVQCodec
from somaforge_core import G1_29DOF_JOINT_ORDER

from scripts.gmvq_ref.train_current_frame_future import _codec_guide, _trajectory_losses
from scripts.gmvq_ref.train_start_conditioned_decoder import WBT_TRACKED_LINK_NAMES, _target_indices


def _runtime_observation(height_scan: torch.Tensor, q: torch.Tensor, qd: torch.Tensor) -> torch.Tensor:
    return torch.cat((height_scan, canonical_boundary_state(q, qd)), dim=-1)


def _endpoint_velocity(joint_pos: torch.Tensor, fps: float) -> torch.Tensor:
    """Match the runtime finite-difference qd computed from the last two poses."""
    previous = joint_pos[:, -2]
    current = joint_pos[:, -1]
    linear = (current[:, :3] - previous[:, :3]) * float(fps)
    previous_quat = previous[:, 3:7]
    conjugate = torch.cat((previous_quat[:, :1], -previous_quat[:, 1:]), dim=-1)
    delta = quat_mul_wxyz(current[:, 3:7], conjugate)
    delta = delta / delta.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
    delta = torch.where(delta[:, :1] < 0.0, -delta, delta)
    xyz = delta[:, 1:]
    sin_half = xyz.norm(dim=-1, keepdim=True)
    angle = 2.0 * torch.atan2(sin_half, delta[:, :1].clamp(-1.0, 1.0))
    scale = torch.where(sin_half > 1.0e-8, angle / sin_half, torch.full_like(sin_half, 2.0))
    angular = xyz * scale * float(fps)
    joints = (current[:, 7:] - previous[:, 7:]) * float(fps)
    return torch.cat((linear, angular, joints), dim=-1)


def _pose_velocity_consistency(
    joint_pos: torch.Tensor,
    joint_vel: torch.Tensor,
    valid: torch.Tensor,
    fps: float,
) -> torch.Tensor:
    """Keep qd consistent with every generated pose interval, not only endpoints."""
    interval_valid = valid[:, 1:] & valid[:, :-1]
    pose_delta = torch.cat(
        (
            joint_pos[:, 1:, :3] - joint_pos[:, :-1, :3],
            joint_pos[:, 1:, 7:] - joint_pos[:, :-1, 7:],
        ),
        dim=-1,
    ) * float(fps)
    velocity = torch.cat((joint_vel[:, :-1, :3], joint_vel[:, :-1, 6:]), dim=-1)
    error = F.smooth_l1_loss(pose_delta, velocity, reduction="none").mean(dim=-1)
    weight = interval_valid.to(error)
    return (error * weight).sum() / weight.sum().clamp_min(1.0)


def _integrate_pose_velocity(
    joint_pos: torch.Tensor,
    joint_vel: torch.Tensor,
    fps: float,
) -> torch.Tensor:
    """Advance canonical G1 q by one sample using world-frame root velocity."""
    result = joint_pos.clone()
    dt = 1.0 / float(fps)
    result[..., :3] = joint_pos[..., :3] + joint_vel[..., :3] * dt
    angular = joint_vel[..., 3:6]
    norm = angular.norm(dim=-1, keepdim=True)
    angle = norm * dt
    axis = angular / norm.clamp_min(1.0e-8)
    delta = torch.cat((torch.cos(0.5 * angle), axis * torch.sin(0.5 * angle)), dim=-1)
    result[..., 3:7] = quat_mul_wxyz(delta, joint_pos[..., 3:7])
    result[..., 7:] = joint_pos[..., 7:] + joint_vel[..., 6:] * dt
    return result


def _taskspace_velocity_consistency(
    joint_pos: torch.Tensor,
    joint_vel: torch.Tensor,
    valid: torch.Tensor,
    fps: float,
    fk: CanonicalG1TorchFK,
) -> torch.Tensor:
    """Match every generated FK step to the motion implied by its qd."""
    current = joint_pos[:, :-1]
    expected_next = _integrate_pose_velocity(current, joint_vel[:, :-1], fps)
    batch, steps = current.shape[:2]
    current_body = fk(current.reshape(-1, 36)).reshape(batch, steps, -1, 3)
    expected_body = fk(expected_next.reshape(-1, 36)).reshape(batch, steps, -1, 3)
    actual_body = fk(joint_pos[:, 1:].reshape(-1, 36)).reshape(batch, steps, -1, 3)
    expected_delta = expected_body - current_body
    actual_delta = actual_body - current_body
    error = F.smooth_l1_loss(actual_delta, expected_delta, reduction="none").mean(dim=(-1, -2))
    weight = (valid[:, 1:] & valid[:, :-1]).to(error)
    return (error * weight).sum() / weight.sum().clamp_min(1.0)


def _taskspace_velocity_peak_consistency(
    joint_pos: torch.Tensor,
    joint_vel: torch.Tensor,
    valid: torch.Tensor,
    fps: float,
    fk: CanonicalG1TorchFK,
    tail_fraction: float = 0.1,
    link_tail_fraction: float = 0.25,
) -> torch.Tensor:
    """Penalize high-error links and intervals without singling out a frame."""
    if not 0.0 < float(tail_fraction) <= 1.0:
        raise ValueError("tail_fraction must be in (0, 1]")
    if not 0.0 < float(link_tail_fraction) <= 1.0:
        raise ValueError("link_tail_fraction must be in (0, 1]")
    current = joint_pos[:, :-1]
    expected_next = _integrate_pose_velocity(current, joint_vel[:, :-1], fps)
    batch, steps = current.shape[:2]
    expected_body = fk(expected_next.reshape(-1, 36)).reshape(batch, steps, -1, 3)
    actual_body = fk(joint_pos[:, 1:].reshape(-1, 36)).reshape(batch, steps, -1, 3)
    link_error = (actual_body - expected_body).square().sum(dim=-1)
    interval_valid = valid[:, 1:] & valid[:, :-1]
    tail_losses = []
    for row in range(batch):
        values = link_error[row, interval_valid[row]]
        if values.shape[0] == 0:
            tail_losses.append(link_error[row].sum() * 0.0)
            continue
        link_count = max(1, int(np.ceil(float(values.shape[1]) * float(link_tail_fraction))))
        interval_error = values.topk(link_count, dim=1).values.mean(dim=1)
        interval_count = max(
            1, int(np.ceil(float(interval_error.numel()) * float(tail_fraction)))
        )
        tail_losses.append(interval_error.topk(interval_count).values.mean())
    return torch.stack(tail_losses).mean()


def _cross_atom_velocity_loss(
    previous_tail: torch.Tensor | None,
    current_head: torch.Tensor,
) -> torch.Tensor:
    """Match pose increments across atom boundaries in one unrolled trajectory."""
    if previous_tail is None:
        return current_head.new_zeros(())
    previous_delta = torch.cat(
        (
            previous_tail[:, 1, :3] - previous_tail[:, 0, :3],
            previous_tail[:, 1, 7:] - previous_tail[:, 0, 7:],
        ),
        dim=-1,
    )
    current_delta = torch.cat(
        (
            current_head[:, 1, :3] - current_head[:, 0, :3],
            current_head[:, 1, 7:] - current_head[:, 0, 7:],
        ),
        dim=-1,
    )
    return F.smooth_l1_loss(current_delta, previous_delta)


def _relative_motion_loss(
    prediction: torch.Tensor,
    guide: torch.Tensor,
    valid: torch.Tensor,
    target_mean: torch.Tensor,
    target_std: torch.Tensor,
) -> torch.Tensor:
    """Preserve the whole guide motion shape after conditioning on a live state."""
    predicted = prediction * target_std + target_mean
    target = guide * target_std + target_mean
    pose_indices = torch.cat(
        (
            torch.arange(3, device=prediction.device),
            torch.arange(7, 36, device=prediction.device),
        )
    )
    predicted_pose = predicted[..., pose_indices]
    target_pose = target[..., pose_indices]
    predicted_relative = predicted_pose - predicted_pose[:, :1]
    target_relative = target_pose - target_pose[:, :1]
    pose_error = F.smooth_l1_loss(predicted_relative, target_relative, reduction="none").mean(dim=-1)
    weight = valid.to(pose_error)
    return (pose_error * weight).sum() / weight.sum().clamp_min(1.0)


def _load_boundary_records(paths: list[Path]) -> dict[str, np.ndarray] | None:
    if not paths:
        return None
    chunks: dict[str, list[np.ndarray]] = {
        key: []
        for key in ("height_scan", "joint_pos", "joint_vel", "previous_code", "code", "theta", "length")
    }
    for path in paths:
        with np.load(path, allow_pickle=False) as data:
            for key in chunks:
                chunks[key].append(np.asarray(data[key]))
    return {key: np.concatenate(values, axis=0) for key, values in chunks.items()}


@torch.no_grad()
def _filter_boundary_tensors(
    tensors: dict[str, torch.Tensor],
    *,
    codec: FrozenGMVQCodec,
    target_mean: torch.Tensor,
    target_std: torch.Tensor,
    fk: CanonicalG1TorchFK,
    max_body_error_m: float,
) -> tuple[dict[str, torch.Tensor], dict[str, float | int]]:
    """Keep live states that remain inside the decoder's recoverable FK neighborhood."""
    code = tensors["code"][:, 0].long()
    theta = tensors["theta"].float()
    lengths = tensors["length"][:, 0].long()
    decoded = codec.decode_hybrid(code, theta, lengths=lengths)["x_hat"]
    source_q = decoded[:, 0, :36] * target_std[:36] + target_mean[:36]
    current_q = tensors["joint_pos"].float().clone()
    current_q[:, :3] = 0.0
    current_body = fk(current_q)
    source_body = fk(source_q)
    current_body = current_body - current_body[:, :1]
    source_body = source_body - source_body[:, :1]
    error = torch.linalg.norm(current_body - source_body, dim=-1).mean(dim=-1)
    keep = error <= float(max_body_error_m)
    filtered = {key: value[keep] for key, value in tensors.items()}
    accepted = error[keep]
    report: dict[str, float | int] = {
        "candidate_count": int(error.numel()),
        "accepted_count": int(keep.sum()),
        "rejected_count": int((~keep).sum()),
        "max_body_error_m": float(max_body_error_m),
        "accepted_body_error_m_mean": 0.0 if accepted.numel() == 0 else float(accepted.mean()),
        "accepted_body_error_m_max": 0.0 if accepted.numel() == 0 else float(accepted.max()),
    }
    return filtered, report


def finetune(args: argparse.Namespace) -> dict[str, object]:
    device = torch.device(args.device)
    torch.manual_seed(args.seed)
    payload = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    if payload.get("schema") != "gmvq_causal_segment_future_v1":
        raise ValueError("full-trajectory fine-tuning requires a causal segment future checkpoint")
    model_config = dict(payload["model_config"])
    if args.joint_trajectory_output:
        model_config["guide_residual_output"] = False
        model_config["joint_trajectory_output"] = True
    if args.start_residual_conditioning:
        model_config["start_residual_conditioning"] = True
    model = CausalSegmentFutureModel(**model_config).to(device)
    adds_start_conditioning = args.start_residual_conditioning and not payload[
        "model_config"
    ].get("start_residual_conditioning", False)
    incompatible = model.load_state_dict(payload["model_state"], strict=not adds_start_conditioning)
    if adds_start_conditioning and set(incompatible.missing_keys) != {"start_residual_input.weight"}:
        raise RuntimeError(f"unexpected missing start-conditioning weights: {incompatible.missing_keys}")
    model.train()
    observation_mean = torch.as_tensor(payload["observation_norm"]["mean"], device=device)
    observation_std = torch.as_tensor(payload["observation_norm"]["std"], device=device)
    target_mean = torch.as_tensor(payload["target_norm"]["mean"], device=device)
    target_std = torch.as_tensor(payload["target_norm"]["std"], device=device)
    theta_mean = torch.as_tensor(payload["theta_norm"]["mean"], device=device)
    theta_std = torch.as_tensor(payload["theta_norm"]["std"], device=device)
    stop_code = int(payload["stop_code"])
    codec_path = payload.get("training", {}).get("gmvq_checkpoint_initialization")
    if not codec_path:
        raise ValueError("causal checkpoint does not record its GMVQ guide checkpoint")
    codec = FrozenGMVQCodec(codec_path, device=device, trainable=False)

    with np.load(args.selector_dataset, allow_pickle=False) as data:
        codes_np = np.asarray(data["codes"], dtype=np.int64)
        theta_np = np.asarray(data["theta"], dtype=np.float32)
        motion_ids = np.asarray(data["motion_ids"]).astype(str)
        starts_np = np.asarray(data["start_frames"], dtype=np.int64)
        height_np = np.asarray(data["height_scan"], dtype=np.float32)
        q_np = np.asarray(data["joint_pos"], dtype=np.float32)
        qd_np = np.asarray(data["joint_vel"], dtype=np.float32)
    active_np = codes_np < stop_code
    with np.load(args.segment_pack, allow_pickle=False) as pack:
        target_rows = _target_indices(
            selector_motion_ids=motion_ids[active_np],
            selector_codes=codes_np[active_np],
            pack_motion_ids=np.asarray(pack["motion_ids"]).astype(str),
        )
        shape = np.asarray(pack["segments"]).shape
        segments_np = np.zeros((len(codes_np), shape[1], shape[2]), dtype=np.float32)
        lengths_np = np.ones(len(codes_np), dtype=np.int64)
        valid_np = np.zeros((len(codes_np), shape[1]), dtype=bool)
        segments_np[active_np] = np.asarray(pack["segments"], dtype=np.float32)[target_rows]
        lengths_np[active_np] = np.asarray(pack["lengths"], dtype=np.int64)[target_rows]
        valid_np[active_np] = np.asarray(pack["valid_mask"], dtype=bool)[target_rows]

    sequence_rows = []
    for motion_id in sorted(set(motion_ids)):
        rows = np.flatnonzero(motion_ids == motion_id)
        rows = rows[np.argsort(starts_np[rows])]
        if len(rows) != stop_code + 1 or int(codes_np[rows[-1]]) != stop_code:
            raise ValueError(f"{motion_id} must contain {stop_code} atoms followed by STOP")
        sequence_rows.append(rows)
    sequences = torch.as_tensor(np.stack(sequence_rows), dtype=torch.long, device=device)
    codes = torch.from_numpy(codes_np).to(device)
    theta_target = (torch.from_numpy(theta_np).to(device) - theta_mean) / theta_std
    height = torch.from_numpy(height_np).to(device)
    source_q = torch.from_numpy(q_np).to(device)
    source_qd = torch.from_numpy(qd_np).to(device)
    target = (torch.from_numpy(segments_np).to(device) - target_mean) / target_std
    lengths = torch.from_numpy(lengths_np).to(device)
    valid = torch.from_numpy(valid_np).to(device)
    fk = CanonicalG1TorchFK(
        joint_names=list(G1_29DOF_JOINT_ORDER),
        link_names=list(WBT_TRACKED_LINK_NAMES),
    ).to(device)
    feature_weight = torch.ones(shape[2], device=device)
    feature_weight[:36] = args.qpos_weight
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    boundary_records = _load_boundary_records(list(args.boundary_records))
    boundary_tensors = (
        None
        if boundary_records is None
        else {key: torch.from_numpy(value).to(device) for key, value in boundary_records.items()}
    )
    if boundary_tensors is not None:
        active_boundary = boundary_tensors["code"][:, 0] < stop_code
        boundary_tensors = {
            key: value[active_boundary] for key, value in boundary_tensors.items()
        }
        boundary_tensors, boundary_filter = _filter_boundary_tensors(
            boundary_tensors,
            codec=codec,
            target_mean=target_mean,
            target_std=target_std,
            fk=fk,
            max_body_error_m=args.boundary_max_body_error_m,
        )
        if not boundary_filter["accepted_count"]:
            raise ValueError("no boundary records passed the FK recovery filter")
        print(json.dumps({"boundary_filter": boundary_filter}, sort_keys=True), flush=True)
    else:
        boundary_filter = None
    history: list[dict[str, float]] = []
    best_loss = float("inf")
    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    for epoch in range(1, args.epochs + 1):
        order = sequences[torch.randperm(sequences.shape[0], device=device)]
        epoch_loss = 0.0
        epoch_code_correct = 0
        epoch_code_count = 0
        epoch_boundary_max = 0.0
        batches = 0
        for sequence_batch in order.split(args.batch_size):
            current_q = source_q[sequence_batch[:, 0]]
            current_qd = source_qd[sequence_batch[:, 0]]
            loss = current_q.new_zeros(())
            active_steps = 0
            previous_tail: torch.Tensor | None = None
            previous_code = torch.full(
                (sequence_batch.shape[0],), -1, dtype=torch.long, device=device
            )
            for step in range(sequence_batch.shape[1]):
                rows = sequence_batch[:, step]
                observation_raw = _runtime_observation(height[rows], current_q, current_qd)
                observation = (observation_raw - observation_mean) / observation_std
                local_q = current_q.clone()
                local_q[:, :3] = 0.0
                start_state = (torch.cat((local_q, current_qd), dim=-1) - target_mean) / target_std
                expected_code = codes[rows]
                guide = _codec_guide(
                    model,
                    observation=observation,
                    start_state=start_state,
                    codes=expected_code,
                    lengths=lengths[rows],
                    codec=codec,
                    theta_mean=theta_mean,
                    theta_std=theta_std,
                    stop_code=stop_code,
                    previous_code=previous_code,
                )
                output = model(
                    observation,
                    start_state=start_state,
                    lengths=lengths[rows],
                    guide_trajectory=guide,
                    previous_code=previous_code,
                )
                loss = loss + args.code_weight * F.cross_entropy(output["code_logits"], expected_code)
                epoch_code_correct += int((output["codes"] == expected_code).sum().item())
                epoch_code_count += int(rows.numel())
                if step == sequence_batch.shape[1] - 1:
                    continue
                dynamic_target = target[rows].clone()
                dynamic_target[:, 0] = start_state
                losses = _trajectory_losses(
                    output["trajectory"],
                    dynamic_target,
                    valid[rows],
                    lengths[rows],
                    feature_weight,
                    target_mean=target_mean,
                    target_std=target_std,
                    fk=fk,
                    fk_frames=args.fk_frames,
                    body_weights=torch.ones(
                        (output["trajectory"].shape[0], len(WBT_TRACKED_LINK_NAMES)),
                        device=device,
                    ),
                    taskspace_frame_sampling=args.taskspace_frame_sampling,
                )
                theta_loss = F.smooth_l1_loss(output["theta"], theta_target[rows])
                physical = output["trajectory"] * target_std + target_mean
                world_q = physical[..., :36].clone()
                world_q[..., :3] = current_q[:, None, :3] + (
                    world_q[..., :3] - world_q[:, :1, :3]
                )
                pose_velocity = _pose_velocity_consistency(
                    world_q, physical[..., 36:], valid[rows], args.fps
                )
                taskspace_velocity = _taskspace_velocity_consistency(
                    world_q, physical[..., 36:], valid[rows], args.fps, fk
                )
                taskspace_velocity_peak = _taskspace_velocity_peak_consistency(
                    world_q, physical[..., 36:], valid[rows], args.fps, fk
                )
                cross_atom_velocity = _cross_atom_velocity_loss(previous_tail, world_q[:, :2])
                epoch_boundary_max = max(
                    epoch_boundary_max,
                    float(cross_atom_velocity.detach().sqrt().item()),
                )
                loss = loss + (
                    args.theta_weight * theta_loss
                    + losses["trajectory"]
                    + args.velocity_weight * losses["velocity"]
                    + args.acceleration_weight * losses["acceleration"]
                    + args.jerk_weight * losses["jerk"]
                    + args.endpoint_weight * losses["endpoint"]
                    + args.taskspace_weight * losses["taskspace"]
                    + args.pose_velocity_weight * pose_velocity
                    + args.taskspace_velocity_weight * taskspace_velocity
                    + args.taskspace_velocity_peak_weight * taskspace_velocity_peak
                    + args.cross_atom_velocity_weight * cross_atom_velocity
                )
                active_steps += 1
                end = lengths[rows] - 1
                batch_index = torch.arange(rows.numel(), device=device)
                next_q = world_q[batch_index, end]
                previous_q = world_q[batch_index, (end - 1).clamp_min(0)]
                generated_tail = torch.stack((previous_q, next_q), dim=1)
                previous_tail = generated_tail
                current_q = next_q
                current_qd = _endpoint_velocity(generated_tail, args.fps)
                previous_code = expected_code
            loss = loss / float(max(active_steps, 1))
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += float(loss.item())
            batches += 1
        if boundary_tensors is not None:
            boundary_count = int(boundary_tensors["code"].shape[0])
            boundary_order = torch.randperm(boundary_count, device=device)
            for boundary_batch in boundary_order.split(args.boundary_batch_size):
                boundary_q = boundary_tensors["joint_pos"][boundary_batch].float()
                boundary_qd = boundary_tensors["joint_vel"][boundary_batch].float()
                boundary_height = boundary_tensors["height_scan"][boundary_batch].float()
                boundary_previous = boundary_tensors["previous_code"][boundary_batch, 0].long()
                boundary_code = boundary_tensors["code"][boundary_batch, 0].long()
                boundary_theta = boundary_tensors["theta"][boundary_batch].float()
                boundary_lengths = boundary_tensors["length"][boundary_batch, 0].long()
                boundary_observation = (
                    _runtime_observation(boundary_height, boundary_q, boundary_qd) - observation_mean
                ) / observation_std
                local_q = boundary_q.clone()
                local_q[:, :3] = 0.0
                boundary_start = (
                    torch.cat((local_q, boundary_qd), dim=-1) - target_mean
                ) / target_std
                guide = _codec_guide(
                    model,
                    observation=boundary_observation,
                    start_state=boundary_start,
                    codes=boundary_code,
                    lengths=boundary_lengths,
                    codec=codec,
                    theta_mean=theta_mean,
                    theta_std=theta_std,
                    stop_code=stop_code,
                    previous_code=boundary_previous,
                )
                output = model(
                    boundary_observation,
                    start_state=boundary_start,
                    lengths=boundary_lengths,
                    guide_trajectory=guide,
                    previous_code=boundary_previous,
                )
                frame = torch.arange(model.max_frames, device=device)[None]
                boundary_valid = frame < boundary_lengths[:, None]
                smooth = _trajectory_losses(
                    output["trajectory"],
                    guide,
                    boundary_valid,
                    boundary_lengths,
                    feature_weight,
                    target_mean=target_mean,
                    target_std=target_std,
                    fk=fk,
                    fk_frames=args.fk_frames,
                    body_weights=torch.ones(
                        (len(boundary_batch), len(WBT_TRACKED_LINK_NAMES)), device=device
                    ),
                    taskspace_frame_sampling=args.taskspace_frame_sampling,
                )
                physical = output["trajectory"] * target_std + target_mean
                relative_motion = _relative_motion_loss(
                    output["trajectory"], guide, boundary_valid, target_mean, target_std
                )
                pose_velocity = _pose_velocity_consistency(
                    physical[..., :36], physical[..., 36:], boundary_valid, args.fps
                )
                taskspace_velocity = _taskspace_velocity_consistency(
                    physical[..., :36], physical[..., 36:], boundary_valid, args.fps, fk
                )
                taskspace_velocity_peak = _taskspace_velocity_peak_consistency(
                    physical[..., :36], physical[..., 36:], boundary_valid, args.fps, fk
                )
                code_loss = F.cross_entropy(output["code_logits"], boundary_code)
                theta_loss = F.smooth_l1_loss(
                    output["theta"], (boundary_theta - theta_mean) / theta_std
                )
                recovery_loss = (
                    args.code_weight * code_loss
                    + args.theta_weight * theta_loss
                    + args.recovery_relative_weight * relative_motion
                    + args.velocity_weight * smooth["velocity"]
                    + args.acceleration_weight * smooth["acceleration"]
                    + args.jerk_weight * smooth["jerk"]
                    + args.pose_velocity_weight * pose_velocity
                    + args.taskspace_velocity_weight * taskspace_velocity
                    + args.taskspace_velocity_peak_weight * taskspace_velocity_peak
                    + args.endpoint_weight * smooth["endpoint"]
                    + args.taskspace_weight * smooth["taskspace"]
                )
                optimizer.zero_grad(set_to_none=True)
                recovery_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                epoch_loss += float(recovery_loss.item())
                batches += 1
        report = {
            "epoch": float(epoch),
            "loss": epoch_loss / max(batches, 1),
            "code_accuracy": epoch_code_correct / max(epoch_code_count, 1),
            "worst_cross_atom_velocity_loss_sqrt": epoch_boundary_max,
        }
        history.append(report)
        if report["loss"] < best_loss:
            best_loss = report["loss"]
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        if epoch == 1 or epoch % args.eval_every == 0 or epoch == args.epochs:
            print(
                f"epoch={epoch} loss={report['loss']:.6f} "
                f"code_acc={report['code_accuracy']:.4f} "
                f"cross_atom_velocity_sqrt={report['worst_cross_atom_velocity_loss_sqrt']:.5f}",
                flush=True,
            )

    model.load_state_dict(best_state)
    output_payload = dict(payload)
    output_payload["model_state"] = model.state_dict()
    output_payload["model_config"] = model.config()
    output_payload["unrolled_training"] = {
        "schema": "gmvq_current_frame_future_unrolled_v1",
        "source_checkpoint": str(args.checkpoint),
        "epochs": args.epochs,
        "best_loss": best_loss,
        "sequence_count": int(sequences.shape[0]),
        "atoms_per_sequence": int(sequences.shape[1] - 1),
        "boundary_record_count": 0 if boundary_tensors is None else int(boundary_tensors["code"].shape[0]),
        "boundary_filter": boundary_filter,
        "joint_trajectory_output": model.joint_trajectory_output,
        "start_residual_conditioning": model.start_residual_conditioning,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(output_payload, args.output)
    summary = {
        "schema": "gmvq_current_frame_future_unrolled_training_v1",
        "output": str(args.output),
        "source": str(args.checkpoint),
        "sequence_count": int(sequences.shape[0]),
        "history": history,
        "final": history[-1],
    }
    args.output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary["final"], indent=2, sort_keys=True))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--selector-dataset", type=Path, required=True)
    parser.add_argument("--segment-pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--boundary-records", type=Path, nargs="*", default=[])
    parser.add_argument("--boundary-batch-size", type=int, default=64)
    parser.add_argument("--boundary-max-body-error-m", type=float, default=0.05)
    parser.add_argument("--joint-trajectory-output", action="store_true")
    parser.add_argument("--start-residual-conditioning", action="store_true")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5.0e-5)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--qpos-weight", type=float, default=4.0)
    parser.add_argument("--code-weight", type=float, default=1.0)
    parser.add_argument("--theta-weight", type=float, default=1.0)
    parser.add_argument("--velocity-weight", type=float, default=2.0)
    parser.add_argument("--acceleration-weight", type=float, default=2.0)
    parser.add_argument("--jerk-weight", type=float, default=1.0)
    parser.add_argument("--endpoint-weight", type=float, default=2.0)
    parser.add_argument("--taskspace-weight", type=float, default=20.0)
    parser.add_argument("--pose-velocity-weight", type=float, default=2.0)
    parser.add_argument("--taskspace-velocity-weight", type=float, default=2000.0)
    parser.add_argument("--taskspace-velocity-peak-weight", type=float, default=0.0)
    parser.add_argument("--cross-atom-velocity-weight", type=float, default=10.0)
    parser.add_argument("--recovery-relative-weight", type=float, default=10.0)
    parser.add_argument("--fk-frames", type=int, default=8)
    parser.add_argument("--taskspace-frame-sampling", choices=("first", "uniform"), default="first")
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--eval-every", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260803)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


if __name__ == "__main__":
    finetune(parse_args())
