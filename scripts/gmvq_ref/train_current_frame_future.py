#!/usr/bin/env python3
"""Train one model that maps the current observation directly to a future atom."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from gmvq.current_frame_future import (
    CausalSegmentFutureModel,
    CurrentFrameFutureModel,
    canonical_boundary_state,
)
from gmvq.g1_fk import CanonicalG1TorchFK
from gmvq.hyar_wrapper import FrozenGMVQCodec
from somaforge_core import G1_29DOF_JOINT_ORDER
from somaforge_core.kinematics import angular_velocity_wxyz
from somaforge_core.robot_assets import decode_robot_asset_json

from scripts.gmvq_ref.train_start_conditioned_decoder import WBT_TRACKED_LINK_NAMES, _target_indices


FEATURE_KEYS = (
    "height_scan",
    "canonical_boundary_state",
)

CONTACT_BODY_TO_LINK = {
    "left_foot": "left_ankle_roll_link",
    "right_foot": "right_ankle_roll_link",
    "left_hand": "left_wrist_yaw_link",
    "right_hand": "right_wrist_yaw_link",
    "left_knee": "left_knee_link",
    "right_knee": "right_knee_link",
}


def _forward_model(
    model: CurrentFrameFutureModel | CausalSegmentFutureModel,
    observation: torch.Tensor,
    start_state: torch.Tensor,
    lengths: torch.Tensor,
    *,
    teacher_trajectory: torch.Tensor | None = None,
    guide_trajectory: torch.Tensor | None = None,
    previous_code: torch.Tensor | None = None,
) -> dict[str, torch.Tensor]:
    if isinstance(model, CausalSegmentFutureModel):
        return model(
            observation,
            start_state=start_state,
            lengths=lengths,
            teacher_trajectory=teacher_trajectory,
            guide_trajectory=guide_trajectory,
            previous_code=previous_code,
        )
    return model(observation, start_state=start_state, previous_code=previous_code)


def _codec_guide(
    model: CurrentFrameFutureModel | CausalSegmentFutureModel,
    *,
    observation: torch.Tensor,
    start_state: torch.Tensor,
    codes: torch.Tensor,
    lengths: torch.Tensor,
    codec: FrozenGMVQCodec,
    theta_mean: torch.Tensor,
    theta_std: torch.Tensor,
    stop_code: int,
    previous_code: torch.Tensor | None = None,
) -> torch.Tensor | None:
    if not isinstance(model, CausalSegmentFutureModel) or not model.use_guide:
        return None
    _, _, theta_normalized, _ = model._latent(observation, previous_code)
    theta = theta_normalized * theta_std + theta_mean
    guide = start_state[:, None].expand(-1, model.max_frames, -1).clone()
    active = torch.where(codes < stop_code)[0]
    if active.numel() > 0:
        decoded = codec.decode_hybrid(codes[active], theta[active], lengths=lengths[active])["x_hat"]
        guide[active] = decoded
    return guide


def _features(data: np.lib.npyio.NpzFile) -> np.ndarray:
    joint_pos = torch.from_numpy(np.asarray(data["joint_pos"], dtype=np.float32))
    joint_vel = torch.from_numpy(np.asarray(data["joint_vel"], dtype=np.float32))
    state = canonical_boundary_state(joint_pos, joint_vel).numpy()
    return np.concatenate((np.asarray(data["height_scan"], dtype=np.float32), state), axis=1)


def _observation_statistics(
    observation: np.ndarray,
    train: np.ndarray,
    *,
    height_dim: int,
    scan_grid_shapes: tuple[tuple[int, int], ...] | None,
    scan_normalization: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute observation statistics without breaking spatial scan equivariance."""
    selected = observation[train]
    mean = selected.mean(axis=0).astype(np.float32)
    std = np.maximum(selected.std(axis=0), 1.0e-6).astype(np.float32)
    if scan_normalization == "per_point":
        return mean, std
    if scan_normalization != "branch":
        raise ValueError(f"unsupported scan normalization: {scan_normalization!r}")
    if scan_grid_shapes is None or sum(rows * cols for rows, cols in scan_grid_shapes) != height_dim:
        raise ValueError("branch scan normalization requires scan_grid_shapes matching height_dim")
    offset = 0
    for rows, cols in scan_grid_shapes:
        count = rows * cols
        values = selected[:, offset : offset + count]
        branch_mean = np.float32(values.mean())
        branch_std = np.float32(max(float(values.std()), 1.0e-6))
        mean[offset : offset + count] = branch_mean
        std[offset : offset + count] = branch_std
        offset += count
    return mean, std


def _split(motion_ids: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    groups = np.asarray(sorted(set(motion_ids.astype(str))))
    rng = np.random.default_rng(seed)
    rng.shuffle(groups)
    train_groups = set(groups[:38])
    validation_groups = set(groups[38:43])
    train = np.asarray([str(value) in train_groups for value in motion_ids])
    validation = np.asarray([str(value) in validation_groups for value in motion_ids])
    return train, validation, ~(train | validation)


def _previous_codes(motion_ids: np.ndarray, start_frames: np.ndarray, codes: np.ndarray) -> np.ndarray:
    """Return the immediately preceding atom without imposing a transition mask."""
    previous = np.full(codes.shape, -1, dtype=np.int64)
    for motion_id in sorted(set(motion_ids.astype(str))):
        rows = np.flatnonzero(motion_ids.astype(str) == motion_id)
        rows = rows[np.argsort(start_frames[rows], kind="stable")]
        if rows.size > 1:
            previous[rows[1:]] = codes[rows[:-1]]
    return previous


def _contact_body_weights(
    active_bodies: np.ndarray | None,
    sequence_ids: np.ndarray,
    start_frames: np.ndarray,
    *,
    body_names: tuple[str, ...],
    contact_weight: float,
) -> np.ndarray:
    """Weight contact-capable links active now or in the immediately following atom."""
    weights = np.ones((len(sequence_ids), len(body_names)), dtype=np.float32)
    if active_bodies is None or contact_weight <= 1.0:
        return weights
    parsed = [set(json.loads(str(value))) for value in active_bodies]
    selected = [set(values) for values in parsed]
    for sequence_id in sorted(set(sequence_ids.astype(str))):
        rows = np.flatnonzero(sequence_ids.astype(str) == sequence_id)
        rows = rows[np.argsort(start_frames[rows], kind="stable")]
        for current, following in zip(rows[:-1], rows[1:], strict=True):
            selected[current].update(parsed[following])
    link_index = {name: index for index, name in enumerate(body_names)}
    for row, bodies in enumerate(selected):
        for body in bodies:
            link_name = CONTACT_BODY_TO_LINK.get(body)
            if link_name in link_index:
                weights[row, link_index[link_name]] = float(contact_weight)
    return weights


def _taskspace_sample_frames(lengths: torch.Tensor, *, samples: int) -> torch.Tensor:
    """Sample each complete atom uniformly, always including its first and last frames."""
    count = max(1, int(samples))
    if count == 1:
        return torch.zeros((lengths.shape[0], 1), dtype=torch.long, device=lengths.device)
    fraction = torch.linspace(0.0, 1.0, count, device=lengths.device)
    return torch.round(fraction[None] * (lengths.clamp_min(1) - 1)[:, None]).to(torch.long)


def _quat_mul_wxyz_np(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aw, ax, ay, az = np.moveaxis(a, -1, 0)
    bw, bx, by, bz = np.moveaxis(b, -1, 0)
    return np.stack(
        (
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ),
        axis=-1,
    )


def _finite_difference_np(value: np.ndarray, fps: float) -> np.ndarray:
    velocity = np.empty_like(value)
    if len(value) == 1:
        velocity[0] = 0.0
        return velocity
    velocity[0] = (value[1] - value[0]) * float(fps)
    velocity[-1] = (value[-1] - value[-2]) * float(fps)
    if len(value) > 2:
        velocity[1:-1] = (value[2:] - value[:-2]) * (0.5 * float(fps))
    return velocity


def _smooth_recovery_segment(
    segment: np.ndarray,
    *,
    length: int,
    start_joint_pos: np.ndarray,
    start_joint_vel: np.ndarray,
    recovery_fraction: float,
    fps: float,
) -> np.ndarray:
    """Create a continuous teacher that returns a measured boundary to one source atom."""
    result = np.asarray(segment, dtype=np.float32).copy()
    count = max(1, min(int(length), len(result)))
    q = result[:count, :36].copy()
    measured = np.asarray(start_joint_pos, dtype=np.float32).copy()
    measured[:3] = 0.0
    horizon = max(1, min(count - 1, int(round((count - 1) * float(recovery_fraction)))))
    u = np.clip(np.arange(count, dtype=np.float32) / float(horizon), 0.0, 1.0)
    decay = 1.0 - (3.0 * u**2 - 2.0 * u**3)
    q[:, :3] += decay[:, None] * (measured[:3] - q[0, :3])[None]
    q[:, 7:] += decay[:, None] * (measured[7:] - q[0, 7:])[None]

    reference_start = q[0, 3:7].copy()
    reference_start /= max(float(np.linalg.norm(reference_start)), 1.0e-8)
    measured_quat = measured[3:7] / max(float(np.linalg.norm(measured[3:7])), 1.0e-8)
    correction = _quat_mul_wxyz_np(
        measured_quat,
        np.asarray((reference_start[0], -reference_start[1], -reference_start[2], -reference_start[3])),
    )
    if correction[0] < 0.0:
        correction = -correction
    identity = np.asarray((1.0, 0.0, 0.0, 0.0), dtype=np.float32)
    correction_curve = decay[:, None] * correction[None] + (1.0 - decay[:, None]) * identity[None]
    correction_curve /= np.maximum(np.linalg.norm(correction_curve, axis=1, keepdims=True), 1.0e-8)
    q[:, 3:7] = _quat_mul_wxyz_np(correction_curve, q[:, 3:7])
    q[:, 3:7] /= np.maximum(np.linalg.norm(q[:, 3:7], axis=1, keepdims=True), 1.0e-8)
    q[0] = measured

    qd = np.concatenate(
        (
            _finite_difference_np(q[:, :3], fps),
            angular_velocity_wxyz(q[:, 3:7], 1.0 / float(fps)),
            _finite_difference_np(q[:, 7:], fps),
        ),
        axis=1,
    ).astype(np.float32)
    qd[0] = np.asarray(start_joint_vel, dtype=np.float32)
    result[:count, :36] = q
    result[:count, 36:] = qd
    return result


def _online_recovery_samples(
    boundary_paths: list[Path],
    *,
    motion_id: str | None,
    selector_motion_ids: np.ndarray,
    selector_codes: np.ndarray,
    selector_theta: np.ndarray,
    segments: np.ndarray,
    lengths: np.ndarray,
    body_weights: np.ndarray,
    max_body_error_m: float,
    recovery_fraction: float,
    fps: float,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    if not boundary_paths:
        return {}, {"candidate_count": 0, "accepted_count": 0, "rejected_count": 0}
    if not motion_id:
        raise ValueError("--online-motion-id is required with --online-boundaries")
    lookup = {
        int(selector_codes[row]): int(row)
        for row in np.flatnonzero(selector_motion_ids.astype(str) == str(motion_id))
    }
    fk = CanonicalG1TorchFK(
        joint_names=list(G1_29DOF_JOINT_ORDER),
        link_names=list(WBT_TRACKED_LINK_NAMES),
    )
    accepted: dict[str, list[np.ndarray | int | str]] = {
        key: []
        for key in (
            "observation_raw",
            "codes",
            "previous_codes",
            "theta",
            "joint_pos",
            "joint_vel",
            "segments",
            "lengths",
            "valid",
            "body_weights",
        )
    }
    errors: list[float] = []
    candidate_count = 0
    for path in boundary_paths:
        with np.load(path, allow_pickle=False) as boundary:
            if str(boundary["schema"].item()) != "gmvq_online_boundary_dataset_v1":
                raise ValueError(f"unsupported online boundary dataset: {path}")
            height = np.asarray(boundary["height_scan"], dtype=np.float32)
            measured_q = np.asarray(boundary["joint_pos"], dtype=np.float32)
            measured_qd = np.asarray(boundary["joint_vel"], dtype=np.float32)
            previous = np.asarray(boundary["previous_code"], dtype=np.int64).reshape(-1)
            boundary_codes = np.asarray(boundary["code"], dtype=np.int64).reshape(-1)
        canonical = canonical_boundary_state(
            torch.from_numpy(measured_q), torch.from_numpy(measured_qd)
        ).numpy()
        for index, code in enumerate(boundary_codes.tolist()):
            if int(code) not in lookup or int(code) >= int(selector_codes.max()):
                continue
            candidate_count += 1
            source_row = lookup[int(code)]
            length = int(lengths[source_row])
            source_q = torch.from_numpy(segments[source_row, 0, :36][None])
            current_q = measured_q[index].copy()
            current_q[:3] = 0.0
            current_body = fk(torch.from_numpy(current_q[None]))[0]
            source_body = fk(source_q)[0]
            current_body = current_body - current_body[:1]
            source_body = source_body - source_body[:1]
            error_m = float(torch.linalg.norm(current_body - source_body, dim=-1).mean().item())
            if error_m > float(max_body_error_m):
                continue
            errors.append(error_m)
            accepted["observation_raw"].append(np.concatenate((height[index], canonical[index])))
            accepted["codes"].append(int(code))
            accepted["previous_codes"].append(int(previous[index]))
            accepted["theta"].append(selector_theta[source_row])
            accepted["joint_pos"].append(current_q)
            accepted["joint_vel"].append(measured_qd[index])
            accepted["segments"].append(
                _smooth_recovery_segment(
                    segments[source_row],
                    length=length,
                    start_joint_pos=current_q,
                    start_joint_vel=measured_qd[index],
                    recovery_fraction=recovery_fraction,
                    fps=fps,
                )
            )
            accepted["lengths"].append(length)
            valid = np.zeros(segments.shape[1], dtype=bool)
            valid[:length] = True
            accepted["valid"].append(valid)
            accepted["body_weights"].append(body_weights[source_row])
    arrays = {key: np.asarray(value) for key, value in accepted.items()}
    report: dict[str, object] = {
        "candidate_count": candidate_count,
        "accepted_count": len(errors),
        "rejected_count": candidate_count - len(errors),
        "max_body_error_m": float(max_body_error_m),
        "accepted_body_error_m_mean": None if not errors else float(np.mean(errors)),
        "accepted_body_error_m_max": None if not errors else float(np.max(errors)),
        "motion_id": str(motion_id),
        "boundary_paths": [str(path) for path in boundary_paths],
    }
    return arrays, report


def _masked_mse(
    prediction: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    feature_weight: torch.Tensor,
) -> torch.Tensor:
    weight = mask[..., None] * feature_weight
    return ((prediction - target).square() * weight).sum() / weight.sum().clamp_min(1.0)


def _trajectory_losses(
    prediction: torch.Tensor,
    target: torch.Tensor,
    valid: torch.Tensor,
    lengths: torch.Tensor,
    feature_weight: torch.Tensor,
    *,
    target_mean: torch.Tensor,
    target_std: torch.Tensor,
    fk: CanonicalG1TorchFK,
    fk_frames: int,
    body_weights: torch.Tensor,
    taskspace_frame_sampling: str,
) -> dict[str, torch.Tensor]:
    trajectory = _masked_mse(prediction, target, valid, feature_weight)
    pair_valid = valid[:, 1:] & valid[:, :-1]
    velocity = _masked_mse(
        prediction[:, 1:] - prediction[:, :-1],
        target[:, 1:] - target[:, :-1],
        pair_valid,
        feature_weight,
    )
    prediction_velocity = prediction[:, 1:] - prediction[:, :-1]
    target_velocity = target[:, 1:] - target[:, :-1]
    acceleration_valid = pair_valid[:, 1:] & pair_valid[:, :-1]
    acceleration = _masked_mse(
        prediction_velocity[:, 1:] - prediction_velocity[:, :-1],
        target_velocity[:, 1:] - target_velocity[:, :-1],
        acceleration_valid,
        feature_weight,
    )
    prediction_acceleration = prediction_velocity[:, 1:] - prediction_velocity[:, :-1]
    target_acceleration = target_velocity[:, 1:] - target_velocity[:, :-1]
    jerk_valid = acceleration_valid[:, 1:] & acceleration_valid[:, :-1]
    jerk = _masked_mse(
        prediction_acceleration[:, 1:] - prediction_acceleration[:, :-1],
        target_acceleration[:, 1:] - target_acceleration[:, :-1],
        jerk_valid,
        feature_weight,
    )
    rows = torch.arange(prediction.shape[0], device=prediction.device)
    endpoint_frames = (lengths - 1).clamp_min(0)
    endpoint = (prediction[rows, endpoint_frames] - target[rows, endpoint_frames]).square().mean()
    sample_count = min(int(fk_frames), prediction.shape[1])
    if taskspace_frame_sampling == "uniform":
        frame_indices = _taskspace_sample_frames(lengths, samples=sample_count)
    elif taskspace_frame_sampling == "first":
        frame_indices = torch.arange(sample_count, device=lengths.device)[None].expand(len(lengths), -1)
    else:
        raise ValueError(f"unsupported taskspace frame sampling: {taskspace_frame_sampling!r}")
    batch_indices = torch.arange(prediction.shape[0], device=prediction.device)[:, None]
    predicted_physical = prediction[batch_indices, frame_indices] * target_std + target_mean
    target_physical = target[batch_indices, frame_indices] * target_std + target_mean
    predicted_body = fk(predicted_physical[..., :36])
    target_body = fk(target_physical[..., :36])
    fk_valid = valid[batch_indices, frame_indices]
    weight = fk_valid[..., None] * body_weights[:, None, :]
    squared_body_error = (predicted_body - target_body).square().sum(dim=-1)
    taskspace = (squared_body_error * weight).sum() / (weight.sum() * 3.0).clamp_min(1.0)
    return {
        "trajectory": trajectory,
        "velocity": velocity,
        "acceleration": acceleration,
        "jerk": jerk,
        "endpoint": endpoint,
        "taskspace": taskspace,
    }


@torch.no_grad()
def _evaluate(
    model: CurrentFrameFutureModel | CausalSegmentFutureModel,
    *,
    observation: torch.Tensor,
    start_state: torch.Tensor,
    codes: torch.Tensor,
    previous_codes: torch.Tensor,
    theta_target: torch.Tensor,
    target: torch.Tensor,
    lengths: torch.Tensor,
    valid: torch.Tensor,
    rows: torch.Tensor,
    active: torch.Tensor,
    feature_weight: torch.Tensor,
    body_weights: torch.Tensor,
    target_mean: torch.Tensor,
    target_std: torch.Tensor,
    fk: CanonicalG1TorchFK,
    codec: FrozenGMVQCodec,
    theta_mean: torch.Tensor,
    theta_std: torch.Tensor,
    stop_code: int,
    args: argparse.Namespace,
) -> dict[str, float]:
    model.eval()
    totals = {
        key: 0.0
        for key in (
            "code",
            "history_code",
            "theta",
            "trajectory",
            "velocity",
            "acceleration",
            "jerk",
            "endpoint",
            "taskspace",
        )
    }
    sample_count = 0
    active_count = 0
    correct = 0
    for batch in rows.split(args.batch_size):
        guide = _codec_guide(
            model,
            observation=observation[batch],
            start_state=start_state[batch],
            codes=codes[batch],
            lengths=lengths[batch],
            codec=codec,
            theta_mean=theta_mean,
            theta_std=theta_std,
            stop_code=stop_code,
            previous_code=previous_codes[batch],
        )
        output = _forward_model(
            model,
            observation[batch],
            start_state[batch],
            lengths[batch],
            guide_trajectory=guide,
            previous_code=previous_codes[batch],
        )
        code_loss = F.cross_entropy(output["code_logits"], codes[batch])
        history_code_loss = F.cross_entropy(
            model.previous_code_logits(
                previous_codes[batch],
                batch_size=int(batch.numel()),
                device=observation.device,
                apply_dropout=False,
            ),
            codes[batch],
        )
        batch_active = active[batch]
        active_rows = torch.where(batch_active)[0]
        correct += int((output["codes"] == codes[batch]).sum().item())
        size = int(batch.numel())
        totals["code"] += float(code_loss.item()) * size
        totals["history_code"] += float(history_code_loss.item()) * size
        sample_count += size
        if active_rows.numel() == 0:
            continue
        theta_loss = F.smooth_l1_loss(output["theta"][active_rows], theta_target[batch][active_rows])
        losses = _trajectory_losses(
            output["trajectory"][active_rows],
            target[batch][active_rows],
            valid[batch][active_rows],
            lengths[batch][active_rows],
            feature_weight,
            target_mean=target_mean,
            target_std=target_std,
            fk=fk,
            fk_frames=args.fk_frames,
            body_weights=body_weights[batch][active_rows],
            taskspace_frame_sampling=args.taskspace_frame_sampling,
        )
        count = int(active_rows.numel())
        totals["theta"] += float(theta_loss.item()) * count
        for key, value in losses.items():
            totals[key] += float(value.item()) * count
        active_count += count
    metrics = {
        "code_accuracy": correct / max(sample_count, 1),
        "code": totals["code"] / max(sample_count, 1),
        "history_code": totals["history_code"] / max(sample_count, 1),
        **{
            key: totals[key] / max(active_count, 1)
            for key in totals
            if key not in {"code", "history_code"}
        },
    }
    metrics["objective"] = (
        args.code_weight * metrics["code"]
        + args.history_code_weight * metrics["history_code"]
        + args.theta_weight * metrics["theta"]
        + metrics["trajectory"]
        + args.velocity_weight * metrics["velocity"]
        + args.acceleration_weight * metrics["acceleration"]
        + args.jerk_weight * metrics["jerk"]
        + args.endpoint_weight * metrics["endpoint"]
        + args.taskspace_weight * metrics["taskspace"]
    )
    return metrics


def train(args: argparse.Namespace) -> dict[str, object]:
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device)
    with np.load(args.selector_dataset, allow_pickle=False) as data:
        robot_asset = decode_robot_asset_json(data["robot_asset_json"], context=str(args.selector_dataset))
        observation_raw = _features(data)
        codes_np = np.asarray(data["codes"], dtype=np.int64)
        theta_np = np.asarray(data["theta"], dtype=np.float32)
        motion_ids = np.asarray(data["motion_ids"]).astype(str)
        sequence_ids = (
            np.asarray(data["sequence_ids"]).astype(str)
            if "sequence_ids" in data.files
            else motion_ids
        )
        active_bodies_np = (
            np.asarray(data["active_bodies"]).astype(str)
            if "active_bodies" in data.files
            else None
        )
        start_frames_np = np.asarray(data["start_frames"], dtype=np.int64)
        joint_pos = np.asarray(data["joint_pos"], dtype=np.float32).copy()
        joint_pos[:, :3] = 0.0
        joint_vel = np.asarray(data["joint_vel"], dtype=np.float32)
        local_grid = np.asarray(data["local_grid"], dtype=np.float32)
        scan_grid_shapes = (
            tuple(tuple(int(x) for x in shape) for shape in np.asarray(data["scan_grid_shapes"]))
            if "scan_grid_shapes" in data.files
            else None
        )
    stop_code = int(codes_np.max())
    active_np = codes_np < stop_code
    previous_codes_np = _previous_codes(sequence_ids, start_frames_np, codes_np)
    body_weights_np = _contact_body_weights(
        active_bodies_np,
        sequence_ids,
        start_frames_np,
        body_names=WBT_TRACKED_LINK_NAMES,
        contact_weight=args.contact_body_weight,
    )
    with np.load(args.segment_pack, allow_pickle=False) as pack:
        target_rows = _target_indices(
            selector_motion_ids=motion_ids[active_np],
            selector_codes=codes_np[active_np],
            pack_motion_ids=np.asarray(pack["motion_ids"]).astype(str),
        )
        segment_shape = np.asarray(pack["segments"]).shape
        segments_np = np.zeros((len(codes_np), segment_shape[1], segment_shape[2]), dtype=np.float32)
        lengths_np = np.ones(len(codes_np), dtype=np.int64)
        valid_np = np.zeros((len(codes_np), segment_shape[1]), dtype=bool)
        segments_np[active_np] = np.asarray(pack["segments"], dtype=np.float32)[target_rows]
        lengths_np[active_np] = np.asarray(pack["lengths"], dtype=np.int64)[target_rows]
        valid_np[active_np] = np.asarray(pack["valid_mask"], dtype=bool)[target_rows]

    train_np, validation_np, test_np = _split(motion_ids, args.seed)
    observation_mean, observation_std = _observation_statistics(
        observation_raw,
        train_np,
        height_dim=local_grid.shape[0],
        scan_grid_shapes=scan_grid_shapes,
        scan_normalization=args.scan_normalization,
    )
    theta_mean = theta_np[train_np & active_np].mean(axis=0).astype(np.float32)
    theta_std = np.maximum(theta_np[train_np & active_np].std(axis=0), 1.0e-6).astype(np.float32)
    recovery, recovery_report = _online_recovery_samples(
        list(args.online_boundaries),
        motion_id=args.online_motion_id,
        selector_motion_ids=motion_ids,
        selector_codes=codes_np,
        selector_theta=theta_np,
        segments=segments_np,
        lengths=lengths_np,
        body_weights=body_weights_np,
        max_body_error_m=args.max_online_body_error_m,
        recovery_fraction=args.recovery_fraction,
        fps=args.fps,
    )
    recovery_count = int(recovery_report["accepted_count"])
    if args.online_boundaries and recovery_count == 0:
        raise ValueError("no online boundary samples passed the recovery filter")
    if recovery_count:
        if args.online_repeat < 1:
            raise ValueError("online-repeat must be positive")
        repeated = np.tile(np.arange(recovery_count), int(args.online_repeat))
        observation_raw = np.concatenate((observation_raw, recovery["observation_raw"][repeated]), axis=0)
        codes_np = np.concatenate((codes_np, recovery["codes"][repeated]), axis=0)
        previous_codes_np = np.concatenate(
            (previous_codes_np, recovery["previous_codes"][repeated]), axis=0
        )
        theta_np = np.concatenate((theta_np, recovery["theta"][repeated]), axis=0)
        joint_pos = np.concatenate((joint_pos, recovery["joint_pos"][repeated]), axis=0)
        joint_vel = np.concatenate((joint_vel, recovery["joint_vel"][repeated]), axis=0)
        segments_np = np.concatenate((segments_np, recovery["segments"][repeated]), axis=0)
        lengths_np = np.concatenate((lengths_np, recovery["lengths"][repeated]), axis=0)
        valid_np = np.concatenate((valid_np, recovery["valid"][repeated]), axis=0)
        body_weights_np = np.concatenate((body_weights_np, recovery["body_weights"][repeated]), axis=0)
        online_rows = len(repeated)
        active_np = np.concatenate((active_np, np.ones(online_rows, dtype=bool)))
        train_np = np.concatenate((train_np, np.ones(online_rows, dtype=bool)))
        validation_np = np.concatenate((validation_np, np.zeros(online_rows, dtype=bool)))
        test_np = np.concatenate((test_np, np.zeros(online_rows, dtype=bool)))
    observation_np = ((observation_raw - observation_mean) / observation_std).astype(np.float32)
    theta_target_np = ((theta_np - theta_mean) / theta_std).astype(np.float32)
    codec = FrozenGMVQCodec(args.gmvq_checkpoint, device=device, trainable=False)
    stats = codec.norm_stats
    if stats is None:
        raise ValueError("GMVQ checkpoint must provide target normalization statistics")
    target_mean = stats.mean.to(device).reshape(-1)
    target_std = stats.std.to(device).reshape(-1)
    target = (torch.from_numpy(segments_np).to(device) - target_mean) / target_std
    start_raw = torch.from_numpy(np.concatenate((joint_pos, joint_vel), axis=1)).to(device)
    start_state = (start_raw - target_mean) / target_std
    target = target.clone()
    target[:, 0] = start_state

    observation = torch.from_numpy(observation_np).to(device)
    codes = torch.from_numpy(codes_np).to(device)
    previous_codes = torch.from_numpy(previous_codes_np).to(device)
    theta_target = torch.from_numpy(theta_target_np).to(device)
    lengths = torch.from_numpy(lengths_np).to(device)
    valid = torch.from_numpy(valid_np).to(device)
    active = torch.from_numpy(active_np).to(device)
    body_weights = torch.from_numpy(body_weights_np).to(device)
    model_kwargs = {
        "height_dim": local_grid.shape[0],
        "state_dim": observation.shape[1] - local_grid.shape[0],
        "feature_dim": segments_np.shape[-1],
        "num_codes": stop_code + 1,
        "theta_dim": theta_np.shape[1],
        "max_frames": segments_np.shape[1],
        "branch_dim": args.branch_dim,
        "context_dim": args.context_dim,
        "code_embed_dim": args.code_embed_dim,
        "time_harmonics": args.time_harmonics,
        "scan_grid_shapes": scan_grid_shapes,
        "scan_antialias": args.scan_antialias,
        "previous_code_embed_dim": args.previous_code_embed_dim,
        "previous_code_logit_scale": args.previous_code_logit_scale,
        "previous_code_dropout": args.previous_code_dropout,
    }
    if args.architecture == "causal":
        model = CausalSegmentFutureModel(
            **model_kwargs,
            dynamics_dim=args.decoder_dim,
            dynamics_layers=args.decoder_layers,
            use_guide=args.use_codec_guide,
            guide_residual_output=args.guide_residual_output,
        ).to(device)
    else:
        model = CurrentFrameFutureModel(
            **model_kwargs,
            decoder_dim=args.decoder_dim,
            decoder_layers=args.decoder_layers,
        ).to(device)
    length_prior = np.ones(stop_code + 1, dtype=np.int64)
    for code in range(stop_code):
        length_prior[code] = int(np.rint(np.median(lengths_np[codes_np == code])))
    if isinstance(model, CausalSegmentFutureModel):
        model.set_target_normalization(target_mean, target_std)
        model.set_length_prior(torch.from_numpy(length_prior).to(device))
    if args.resume_state is not None:
        recovery = torch.load(args.resume_state, map_location="cpu", weights_only=False)
        model.load_state_dict(recovery["model_state"])
    fk = CanonicalG1TorchFK(
        joint_names=list(G1_29DOF_JOINT_ORDER),
        link_names=list(WBT_TRACKED_LINK_NAMES),
    ).to(device)
    feature_weight = torch.ones(segments_np.shape[-1], device=device)
    feature_weight[:36] = args.qpos_weight
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    train_rows = torch.from_numpy(np.flatnonzero(train_np)).to(device)
    validation_rows = torch.from_numpy(np.flatnonzero(validation_np)).to(device)
    test_rows = torch.from_numpy(np.flatnonzero(test_np)).to(device)
    best_state: dict[str, torch.Tensor] | None = None
    best_objective = float("inf")
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = train_rows[torch.randperm(train_rows.numel(), device=device)]
        for batch in order.split(args.batch_size):
            teacher = None
            if isinstance(model, CausalSegmentFutureModel) and epoch <= args.teacher_epochs:
                teacher = target[batch]
            guide = _codec_guide(
                model,
                observation=observation[batch],
                start_state=start_state[batch],
                codes=codes[batch],
                lengths=lengths[batch],
                codec=codec,
                theta_mean=torch.from_numpy(theta_mean).to(device),
                theta_std=torch.from_numpy(theta_std).to(device),
                stop_code=stop_code,
                previous_code=previous_codes[batch],
            )
            output = _forward_model(
                model,
                observation[batch],
                start_state[batch],
                lengths[batch],
                teacher_trajectory=teacher,
                guide_trajectory=guide,
                previous_code=previous_codes[batch],
            )
            code_loss = F.cross_entropy(output["code_logits"], codes[batch])
            history_code_loss = F.cross_entropy(
                model.previous_code_logits(
                    previous_codes[batch],
                    batch_size=int(batch.numel()),
                    device=observation.device,
                    apply_dropout=False,
                ),
                codes[batch],
            )
            batch_active = active[batch]
            active_rows = torch.where(batch_active)[0]
            theta_loss = F.smooth_l1_loss(output["theta"][active_rows], theta_target[batch][active_rows])
            losses = _trajectory_losses(
                output["trajectory"][active_rows],
                target[batch][active_rows],
                valid[batch][active_rows],
                lengths[batch][active_rows],
                feature_weight,
                target_mean=target_mean,
                target_std=target_std,
                fk=fk,
                fk_frames=args.fk_frames,
                body_weights=body_weights[batch][active_rows],
                taskspace_frame_sampling=args.taskspace_frame_sampling,
            )
            loss = (
                args.code_weight * code_loss
                + args.history_code_weight * history_code_loss
                + args.theta_weight * theta_loss
                + losses["trajectory"]
                + args.velocity_weight * losses["velocity"]
                + args.acceleration_weight * losses["acceleration"]
                + args.jerk_weight * losses["jerk"]
                + args.endpoint_weight * losses["endpoint"]
                + args.taskspace_weight * losses["taskspace"]
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        if epoch == 1 or epoch % args.eval_every == 0 or epoch == args.epochs:
            metrics = _evaluate(
                model,
                observation=observation,
                start_state=start_state,
                codes=codes,
                previous_codes=previous_codes,
                theta_target=theta_target,
                target=target,
                lengths=lengths,
                valid=valid,
                rows=validation_rows,
                active=active,
                feature_weight=feature_weight,
                body_weights=body_weights,
                target_mean=target_mean,
                target_std=target_std,
                fk=fk,
                codec=codec,
                theta_mean=torch.from_numpy(theta_mean).to(device),
                theta_std=torch.from_numpy(theta_std).to(device),
                stop_code=stop_code,
                args=args,
            )
            print(
                f"epoch={epoch} objective={metrics['objective']:.6f} "
                f"code_acc={metrics['code_accuracy']:.4f} trajectory={metrics['trajectory']:.6f} "
                f"velocity={metrics['velocity']:.6f} taskspace={metrics['taskspace']:.7f}",
                flush=True,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            torch.save(
                {"epoch": epoch, "model_state": model.state_dict()},
                args.output.with_suffix(".recovery.pt"),
            )
            if metrics["objective"] < best_objective:
                best_objective = metrics["objective"]
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)

    payload = {
        "schema": (
            "gmvq_causal_segment_future_v1"
            if isinstance(model, CausalSegmentFutureModel)
            else "gmvq_current_frame_future_v1"
        ),
        "model_config": model.config(),
        "model_state": model.state_dict(),
        "robot_asset": robot_asset,
        "feature_keys": list(FEATURE_KEYS),
        "observation_norm": {"mean": observation_mean, "std": observation_std},
        "target_norm": {
            "mean": target_mean.detach().cpu().numpy(),
            "std": target_std.detach().cpu().numpy(),
        },
        "theta_norm": {"mean": theta_mean, "std": theta_std},
        "local_grid": local_grid,
        "length_prior": length_prior,
        "stop_code": stop_code,
        "training": {
            "selector_dataset": str(args.selector_dataset),
            "segment_pack": str(args.segment_pack),
            "gmvq_checkpoint_initialization": str(args.gmvq_checkpoint),
            "scan_normalization": args.scan_normalization,
            "scan_antialias": args.scan_antialias,
            "contact_body_weight": float(args.contact_body_weight),
            "taskspace_frame_sampling": str(args.taskspace_frame_sampling),
            "online_recovery": recovery_report,
            "online_repeat": int(args.online_repeat),
            "recovery_fraction": float(args.recovery_fraction),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, args.output)
    summary = {
        "schema": (
            "gmvq_causal_segment_future_training_v1"
            if isinstance(model, CausalSegmentFutureModel)
            else "gmvq_current_frame_future_training_v1"
        ),
        "output": str(args.output),
        "train": _evaluate(
            model,
            observation=observation,
            start_state=start_state,
            codes=codes,
            previous_codes=previous_codes,
            theta_target=theta_target,
            target=target,
            lengths=lengths,
            valid=valid,
            rows=train_rows,
            active=active,
            feature_weight=feature_weight,
            body_weights=body_weights,
            target_mean=target_mean,
            target_std=target_std,
            fk=fk,
            codec=codec,
            theta_mean=torch.from_numpy(theta_mean).to(device),
            theta_std=torch.from_numpy(theta_std).to(device),
            stop_code=stop_code,
            args=args,
        ),
        "validation": _evaluate(
            model,
            observation=observation,
            start_state=start_state,
            codes=codes,
            previous_codes=previous_codes,
            theta_target=theta_target,
            target=target,
            lengths=lengths,
            valid=valid,
            rows=validation_rows,
            active=active,
            feature_weight=feature_weight,
            body_weights=body_weights,
            target_mean=target_mean,
            target_std=target_std,
            fk=fk,
            codec=codec,
            theta_mean=torch.from_numpy(theta_mean).to(device),
            theta_std=torch.from_numpy(theta_std).to(device),
            stop_code=stop_code,
            args=args,
        ),
        "test": _evaluate(
            model,
            observation=observation,
            start_state=start_state,
            codes=codes,
            previous_codes=previous_codes,
            theta_target=theta_target,
            target=target,
            lengths=lengths,
            valid=valid,
            rows=test_rows,
            active=active,
            feature_weight=feature_weight,
            body_weights=body_weights,
            target_mean=target_mean,
            target_std=target_std,
            fk=fk,
            codec=codec,
            theta_mean=torch.from_numpy(theta_mean).to(device),
            theta_std=torch.from_numpy(theta_std).to(device),
            stop_code=stop_code,
            args=args,
        ),
    }
    args.output.with_suffix(".summary.json").write_text(
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
    parser.add_argument("--resume-state", type=Path)
    parser.add_argument("--online-boundaries", type=Path, nargs="*", default=[])
    parser.add_argument("--online-motion-id")
    parser.add_argument("--online-repeat", type=int, default=4)
    parser.add_argument("--max-online-body-error-m", type=float, default=0.03)
    parser.add_argument("--recovery-fraction", type=float, default=0.25)
    parser.add_argument("--fps", type=float, default=50.0)
    parser.add_argument("--architecture", choices=("causal", "direct"), default="causal")
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--branch-dim", type=int, default=128)
    parser.add_argument("--context-dim", type=int, default=256)
    parser.add_argument("--code-embed-dim", type=int, default=32)
    parser.add_argument("--decoder-dim", type=int, default=256)
    parser.add_argument("--decoder-layers", type=int, default=2)
    parser.add_argument("--time-harmonics", type=int, default=8)
    parser.add_argument("--previous-code-embed-dim", type=int, default=16)
    parser.add_argument("--previous-code-logit-scale", type=float, default=1.0)
    parser.add_argument("--previous-code-dropout", type=float, default=0.25)
    parser.add_argument("--scan-normalization", choices=("per_point", "branch"), default="branch")
    parser.add_argument("--scan-antialias", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--teacher-epochs", type=int, default=250)
    parser.add_argument("--use-codec-guide", action="store_true")
    parser.add_argument("--guide-residual-output", action="store_true")
    parser.add_argument("--qpos-weight", type=float, default=4.0)
    parser.add_argument("--code-weight", type=float, default=1.0)
    parser.add_argument("--history-code-weight", type=float, default=0.25)
    parser.add_argument("--theta-weight", type=float, default=1.0)
    parser.add_argument("--velocity-weight", type=float, default=2.0)
    parser.add_argument("--acceleration-weight", type=float, default=2.0)
    parser.add_argument("--jerk-weight", type=float, default=1.0)
    parser.add_argument("--endpoint-weight", type=float, default=2.0)
    parser.add_argument("--taskspace-weight", type=float, default=20.0)
    parser.add_argument("--contact-body-weight", type=float, default=1.0)
    parser.add_argument("--taskspace-frame-sampling", choices=("first", "uniform"), default="first")
    parser.add_argument("--fk-frames", type=int, default=8)
    parser.add_argument("--eval-every", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260803)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
