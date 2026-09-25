"""Train the single-forward mechanically constrained climb00 infiller."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import fields
from pathlib import Path

import numpy as np
import torch
from torch.nn.utils import clip_grad_norm_
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler

from generator.fullbody_dataset import FullBodyEventDataset, build_fullbody_event_dataset, build_generated_fullbody_event_dataset
from contact_solver.collision_geometry import CanonicalG1CollisionPoints, full_geometry_box_collision_penalty
from generator.neural_infiller import G1ConstrainedKeypointInfiller, constrained_infiller_loss, constrained_infiller_seam_loss
from somaforge_core.g1_kinematics import _matrix_from_rotation6d, _rotation_angle_degrees


def _combine_datasets(primary: FullBodyEventDataset, mechanical: FullBodyEventDataset) -> FullBodyEventDataset:
    values = {}
    motion_offset = int(primary.motion_id.max()) + 1
    for field in fields(primary):
        first = getattr(primary, field.name)
        second = getattr(mechanical, field.name)
        if field.name == "motion_id":
            second = second + motion_offset
        values[field.name] = torch.cat((first, second), dim=0)
    return FullBodyEventDataset(**values)


def _adjacent_pairs(data: FullBodyEventDataset, mask: torch.Tensor) -> torch.Tensor:
    lookup = {
        (int(data.motion_id[index]), int(data.event_index[index])): index
        for index in torch.nonzero(mask, as_tuple=False).flatten().tolist()
    }
    pairs = []
    for (motion_id, event_index), left in lookup.items():
        right = lookup.get((motion_id, event_index + 1))
        if right is not None:
            pairs.append((left, right))
    if not pairs:
        raise RuntimeError("dataset split produced no adjacent event pairs")
    return torch.tensor(pairs, dtype=torch.long)


def main() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", type=Path)
    source.add_argument("--teacher", type=Path)
    parser.add_argument("--mechanical-manifest", type=Path)
    parser.add_argument("--mechanical-sampling-weight", type=float, default=6.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--phase-frames", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--init-checkpoint", type=Path)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--log-every", type=int, default=25)
    parser.add_argument("--validation-samples", type=int, default=256)
    parser.add_argument("--maximum-mesh-points", type=int, default=32)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device(args.device)

    data = (
        build_fullbody_event_dataset(args.manifest, args.phase_frames)
        if args.manifest is not None
        else build_generated_fullbody_event_dataset(args.teacher, args.phase_frames)
    )
    if args.mechanical_manifest is not None:
        if args.teacher is None:
            raise ValueError("--mechanical-manifest is only needed with a public --teacher dataset")
        mechanical = build_fullbody_event_dataset(args.mechanical_manifest, args.phase_frames)
        data = _combine_datasets(data, mechanical)
    validation_mask = data.motion_id.remainder(10) == 0
    train_mask = ~validation_mask
    initial = (
        None
        if args.init_checkpoint is None
        else torch.load(args.init_checkpoint, map_location="cpu", weights_only=False)
    )
    if initial is None:
        condition_mean = data.condition[train_mask].mean(dim=0)
        condition_std = data.condition[train_mask].std(dim=0).clamp_min(1.0e-5)
    else:
        if int(initial["condition_dim"]) != data.condition.shape[1]:
            raise ValueError("initial checkpoint condition dimension does not match the dataset")
        condition_mean = initial["condition_mean"].cpu()
        condition_std = initial["condition_std"].cpu()
    normalized_condition = (data.condition - condition_mean) / condition_std
    train_pairs = _adjacent_pairs(data, train_mask)
    dataset = TensorDataset(train_pairs)
    pair_has_q = data.q_valid[train_pairs].all(dim=1)
    sample_weight = torch.ones(len(train_pairs), dtype=torch.float32)
    sample_weight[pair_has_q] = args.mechanical_sampling_weight
    sampler = WeightedRandomSampler(sample_weight, num_samples=len(train_pairs), replacement=True)
    loader = DataLoader(dataset, batch_size=min(args.batch_size, len(dataset)), sampler=sampler, drop_last=True)
    iterator = iter(loader)
    model = G1ConstrainedKeypointInfiller(data.condition.shape[1]).to(device)
    if initial is not None:
        model.load_state_dict(initial["model"])
    collision_geometry = CanonicalG1CollisionPoints(args.maximum_mesh_points).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-4)
    phase = torch.linspace(0.0, 1.0, args.phase_frames, device=device)[None]
    history = []
    best_score = float("inf")
    best_state = None
    best_validation = None
    for step in range(1, args.steps + 1):
        try:
            batch = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            batch = next(iterator)
        pair_indices = batch[0]
        left_indices, right_indices = pair_indices[:, 0], pair_indices[:, 1]
        combined_indices = torch.cat((left_indices, right_indices))
        condition = normalized_condition[combined_indices].to(device)
        position = data.position[combined_indices].to(device)
        rotation = data.rotation6d[combined_indices].to(device)
        contact = data.contact[combined_indices].to(device)
        qpos = data.qpos[combined_indices].to(device)
        q_valid = data.q_valid[combined_indices].to(device)
        center = data.box_center[combined_indices].to(device)
        box_rotation = data.box_rotation[combined_indices].to(device)
        half_extents = data.box_half_extents[combined_indices].to(device)
        ground = data.ground_height[combined_indices].to(device)
        phase_batch = phase.expand(len(combined_indices), -1)
        output = model(
            condition,
            phase_batch,
            position[:, 0],
            rotation[:, 0],
            position[:, -1],
            rotation[:, -1],
            contact[:, 0],
            contact[:, -1],
        )
        collision_points, point_part = collision_geometry(model.fk, output.auxiliary_qpos)
        collision = full_geometry_box_collision_penalty(
            collision_points,
            point_part,
            contact,
            box_center=center,
            box_rotation=box_rotation,
            box_half_extents=half_extents,
            ground_height=ground,
        )
        losses = constrained_infiller_loss(
            model,
            output,
            target_position=position,
            target_rotation6d=rotation,
            target_contact=contact,
            target_qpos=qpos,
            q_valid=q_valid,
            collision_penalty=collision,
        )
        pair_count = len(left_indices)
        left_output = type(output)(*(getattr(output, field.name)[:pair_count] for field in fields(output)))
        right_output = type(output)(*(getattr(output, field.name)[pair_count:] for field in fields(output)))
        seam = constrained_infiller_seam_loss(
            left_output,
            right_output,
            left_duration=data.condition[left_indices, -1].to(device),
            right_duration=data.condition[right_indices, -1].to(device),
            q_valid=(data.q_valid[left_indices] & data.q_valid[right_indices]).to(device),
        )
        optimizer.zero_grad(set_to_none=True)
        (losses.total + 0.5 * seam.total).backward()
        gradient_norm = clip_grad_norm_(model.parameters(), 2.0)
        optimizer.step()
        if step == 1 or step % args.log_every == 0 or step == args.steps:
            record = {field.name: float(getattr(losses, field.name).detach()) for field in fields(losses)}
            record["seam"] = {field.name: float(getattr(seam, field.name).detach()) for field in fields(seam)}
            record.update(step=step, gradient_norm=float(gradient_norm), samples=len(data), pairs=len(dataset))
            validation_all = torch.nonzero(validation_mask, as_tuple=False).flatten()
            validation_public = validation_all[data.q_valid[validation_all] == 0][: args.validation_samples // 2]
            validation_mechanical = validation_all[data.q_valid[validation_all] != 0][: args.validation_samples // 2]
            validation_indices = torch.cat((validation_public, validation_mechanical))
            if not len(validation_indices):
                validation_indices = validation_all[: args.validation_samples]
            with torch.no_grad():
                validation_condition = normalized_condition[validation_indices].to(device)
                validation_position = data.position[validation_indices].to(device)
                validation_rotation = data.rotation6d[validation_indices].to(device)
                validation_contact = data.contact[validation_indices].to(device)
                validation_qpos = data.qpos[validation_indices].to(device)
                validation_q_valid = data.q_valid[validation_indices].to(device)
                validation_output = model(
                    validation_condition,
                    phase.expand(len(validation_indices), -1),
                    validation_position[:, 0],
                    validation_rotation[:, 0],
                    validation_position[:, -1],
                    validation_rotation[:, -1],
                    validation_contact[:, 0],
                    validation_contact[:, -1],
                )
                fk_position, fk_rotation6d = model.fk(validation_output.auxiliary_qpos)
                output_rotation = _matrix_from_rotation6d(validation_output.keypoint_rotation6d)
                target_rotation = _matrix_from_rotation6d(validation_rotation)
                fk_rotation = _matrix_from_rotation6d(fk_rotation6d)
                active_contact = validation_contact > 0.5
                active_count = active_contact.sum().clamp_min(1)
                contact_position_cm = (
                    torch.linalg.vector_norm(
                        validation_output.keypoint_position[..., 1:, :] - validation_position[..., 1:, :],
                        dim=-1,
                    )
                    .mul(active_contact)
                    .sum()
                    .div(active_count)
                    .mul(100.0)
                )
                contact_rotation_deg = (
                    _rotation_angle_degrees(output_rotation[..., 1:, :, :], target_rotation[..., 1:, :, :])
                    .mul(active_contact)
                    .sum()
                    .div(active_count)
                )
                validation_points, validation_part = collision_geometry(model.fk, validation_output.auxiliary_qpos)
                validation_collision = full_geometry_box_collision_penalty(
                    validation_points,
                    validation_part,
                    validation_contact,
                    box_center=data.box_center[validation_indices].to(device),
                    box_rotation=data.box_rotation[validation_indices].to(device),
                    box_half_extents=data.box_half_extents[validation_indices].to(device),
                    ground_height=data.ground_height[validation_indices].to(device),
                )
                record["validation"] = {
                    "keypoint_error_cm": float(
                        torch.linalg.vector_norm(validation_output.keypoint_position - validation_position, dim=-1)
                        .mean()
                        .mul(100.0)
                    ),
                    "fk_keypoint_consistency_cm": float(
                        torch.linalg.vector_norm(validation_output.keypoint_position - fk_position, dim=-1)
                        .mean()
                        .mul(100.0)
                    ),
                    "keypoint_rotation_error_deg": float(
                        _rotation_angle_degrees(output_rotation, target_rotation).mean()
                    ),
                    "fk_rotation_consistency_deg": float(
                        _rotation_angle_degrees(output_rotation, fk_rotation).mean()
                    ),
                    "boundary_fk_position_error_cm": float(
                        torch.linalg.vector_norm(
                            fk_position[:, (0, -1)] - validation_position[:, (0, -1)], dim=-1
                        )
                        .mean()
                        .mul(100.0)
                    ),
                    "boundary_fk_rotation_error_deg": float(
                        _rotation_angle_degrees(
                            fk_rotation[:, (0, -1)], target_rotation[:, (0, -1)]
                        ).mean()
                    ),
                    "contact_position_error_cm": float(contact_position_cm),
                    "contact_rotation_error_deg": float(contact_rotation_deg),
                    "joint_mae_rad": float(
                        (
                            (validation_output.auxiliary_qpos[..., 7:] - validation_qpos[..., 7:])
                            .abs()
                            .mean(dim=(-1, -2))
                            * validation_q_valid
                        ).sum()
                        / validation_q_valid.sum().clamp_min(1)
                    ),
                    "boundary_joint_mae_rad": float(
                        (
                            (
                                validation_output.auxiliary_qpos[:, (0, -1), 7:]
                                - validation_qpos[:, (0, -1), 7:]
                            )
                            .abs()
                            .mean(dim=(-1, -2))
                            * validation_q_valid
                        )
                        .sum()
                        / validation_q_valid.sum().clamp_min(1)
                    ),
                    "collision_penalty": float(validation_collision),
                    "endpoint_max_error_m": float(
                        (validation_output.keypoint_position[:, (0, -1)] - validation_position[:, (0, -1)]).abs().max()
                    ),
                }
                validation_pairs = _adjacent_pairs(data, validation_mask)[: args.validation_samples]
                left_validation = validation_pairs[:, 0]
                right_validation = validation_pairs[:, 1]
                pair_validation_indices = torch.cat((left_validation, right_validation))
                pair_condition = normalized_condition[pair_validation_indices].to(device)
                pair_position = data.position[pair_validation_indices].to(device)
                pair_rotation = data.rotation6d[pair_validation_indices].to(device)
                pair_contact = data.contact[pair_validation_indices].to(device)
                pair_output = model(
                    pair_condition,
                    phase.expand(len(pair_validation_indices), -1),
                    pair_position[:, 0],
                    pair_rotation[:, 0],
                    pair_position[:, -1],
                    pair_rotation[:, -1],
                    pair_contact[:, 0],
                    pair_contact[:, -1],
                )
                validation_pair_count = len(left_validation)
                validation_left_output = type(pair_output)(
                    *(getattr(pair_output, field.name)[:validation_pair_count] for field in fields(pair_output))
                )
                validation_right_output = type(pair_output)(
                    *(getattr(pair_output, field.name)[validation_pair_count:] for field in fields(pair_output))
                )
                validation_seam = constrained_infiller_seam_loss(
                    validation_left_output,
                    validation_right_output,
                    left_duration=data.condition[left_validation, -1].to(device),
                    right_duration=data.condition[right_validation, -1].to(device),
                    q_valid=(data.q_valid[left_validation] & data.q_valid[right_validation]).to(device),
                )
                record["validation_seam"] = {
                    field.name: float(getattr(validation_seam, field.name)) for field in fields(validation_seam)
                }
                validation = record["validation"]
                validation_score = (
                    validation["keypoint_error_cm"]
                    + validation["fk_keypoint_consistency_cm"]
                    + 0.1 * validation["keypoint_rotation_error_deg"]
                    + 0.1 * validation["fk_rotation_consistency_deg"]
                    + validation["boundary_fk_position_error_cm"]
                    + 0.2 * validation["boundary_fk_rotation_error_deg"]
                    + validation["contact_position_error_cm"]
                    + 0.2 * validation["contact_rotation_error_deg"]
                    + 5.0 * validation["joint_mae_rad"]
                    + 10.0 * validation["boundary_joint_mae_rad"]
                    + 100.0 * validation["collision_penalty"]
                    + float(validation_seam.total)
                )
                record["validation_score"] = validation_score
                if validation_score < best_score:
                    best_score = validation_score
                    best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
                    best_validation = dict(validation)
            history.append(record)
            print(json.dumps(record), flush=True)

    if best_state is None:
        raise RuntimeError("training produced no validation checkpoint")
    checkpoint = {
        "schema": "climb00_g1_constrained_keypoint_infiller_v3_se3_continuity",
        "model": best_state,
        "condition_mean": condition_mean,
        "condition_std": condition_std,
        "condition_dim": data.condition.shape[1],
        "phase_frames": args.phase_frames,
        "manifest": None if args.manifest is None else str(args.manifest.resolve()),
        "teacher": None if args.teacher is None else str(args.teacher.resolve()),
        "mechanical_manifest": (
            None if args.mechanical_manifest is None else str(args.mechanical_manifest.resolve())
        ),
        "samples": len(dataset),
        "validation_samples": int(validation_mask.sum()),
        "best_validation_score": best_score,
        "best_validation": best_validation,
    }
    torch.save(checkpoint, args.output / "model.pt")
    (args.output / "history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
