"""Train the q-only, contact-aware G1 event infiller."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import fields
from pathlib import Path

import numpy as np
import torch
from torch.nn.utils import clip_grad_norm_
from torch.utils.data import DataLoader, TensorDataset

from .fullbody_dataset import FullBodyEventDataset, build_fullbody_event_dataset
from .neural_infiller import (
    CanonicalG1CollisionPoints,
    G1ContactAwareQInfiller,
    _matrix_from_rotation6d,
    _rotation_angle_degrees,
    constrained_infiller_seam_loss,
    contact_aware_q_infiller_loss,
    full_geometry_box_collision_penalty,
    full_geometry_contact_surface_penalty,
)


def _adjacent_pairs(data: FullBodyEventDataset, mask: torch.Tensor) -> torch.Tensor:
    lookup = {
        (int(data.motion_id[index]), int(data.event_index[index])): index
        for index in torch.nonzero(mask, as_tuple=False).flatten().tolist()
    }
    pairs = [
        (left, lookup[(motion_id, event_index + 1)])
        for (motion_id, event_index), left in lookup.items()
        if (motion_id, event_index + 1) in lookup
    ]
    if not pairs:
        raise RuntimeError("dataset split produced no adjacent event pairs")
    return torch.tensor(pairs, dtype=torch.long)


def _persistent_contact_step_cm(output, contact: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    persistent = (contact[:, 1:] > 0.5) & (contact[:, :-1] > 0.5)
    count = persistent.sum().clamp_min(1)
    step = torch.linalg.vector_norm(
        output.keypoint_position[:, 1:, 1:] - output.keypoint_position[:, :-1, 1:], dim=-1
    )
    mean = (step * persistent).sum() / count * 100.0
    selected = step[persistent]
    p95 = torch.quantile(selected, 0.95) * 100.0 if len(selected) else step.new_zeros(())
    return mean, p95


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--phase-frames", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
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

    data = build_fullbody_event_dataset(args.manifest, args.phase_frames)
    if not bool(data.q_valid.all()):
        raise ValueError("q-only infiller requires canonical q for every training segment")
    validation_mask = data.motion_id.remainder(10) == 0
    train_mask = ~validation_mask
    condition_mean = data.condition[train_mask].mean(dim=0)
    condition_std = data.condition[train_mask].std(dim=0).clamp_min(1.0e-5)
    normalized_condition = (data.condition - condition_mean) / condition_std
    train_pairs = _adjacent_pairs(data, train_mask)
    loader = DataLoader(
        TensorDataset(train_pairs),
        batch_size=min(args.batch_size, len(train_pairs)),
        shuffle=True,
        drop_last=True,
    )
    iterator = iter(loader)
    model = G1ContactAwareQInfiller(data.condition.shape[1]).to(device)
    collision_geometry = CanonicalG1CollisionPoints(args.maximum_mesh_points).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-4)
    phase = torch.linspace(0.0, 1.0, args.phase_frames, device=device)[None]
    history = []
    best_score = float("inf")
    best_step = None
    best_state = None
    best_validation = None
    validation_indices = torch.nonzero(validation_mask, as_tuple=False).flatten()[: args.validation_samples]
    validation_pairs = _adjacent_pairs(data, validation_mask)[: max(1, args.validation_samples // 2)]

    def forward(indices: torch.Tensor):
        qpos = data.qpos[indices].to(device)
        contact = data.contact[indices].to(device)
        condition = normalized_condition[indices].to(device)
        return model(
            condition,
            phase.expand(len(indices), -1),
            qpos[:, 0],
            qpos[:, -1],
            contact[:, 0],
            contact[:, -1],
        )

    for step in range(1, args.steps + 1):
        try:
            pair_indices = next(iterator)[0]
        except StopIteration:
            iterator = iter(loader)
            pair_indices = next(iterator)[0]
        left_indices, right_indices = pair_indices[:, 0], pair_indices[:, 1]
        combined_indices = torch.cat((left_indices, right_indices))
        target_qpos = data.qpos[combined_indices].to(device)
        target_contact = data.contact[combined_indices].to(device)
        output = forward(combined_indices)
        points, point_part = collision_geometry(model.fk, output.auxiliary_qpos)
        target_points, _ = collision_geometry(model.fk, target_qpos)
        collision = full_geometry_box_collision_penalty(
            points,
            point_part,
            target_contact,
            box_center=data.box_center[combined_indices].to(device),
            box_rotation=data.box_rotation[combined_indices].to(device),
            box_half_extents=data.box_half_extents[combined_indices].to(device),
            ground_height=data.ground_height[combined_indices].to(device),
        )
        contact_surface = full_geometry_contact_surface_penalty(
            points,
            target_points,
            point_part,
            target_contact,
            box_center=data.box_center[combined_indices].to(device),
            box_rotation=data.box_rotation[combined_indices].to(device),
            box_half_extents=data.box_half_extents[combined_indices].to(device),
            ground_height=data.ground_height[combined_indices].to(device),
        )
        losses = contact_aware_q_infiller_loss(
            model,
            output,
            target_qpos=target_qpos,
            target_contact=target_contact,
            collision_penalty=collision,
            contact_surface_penalty=contact_surface,
        )
        pair_count = len(left_indices)
        left_output = type(output)(*(getattr(output, item.name)[:pair_count] for item in fields(output)))
        right_output = type(output)(*(getattr(output, item.name)[pair_count:] for item in fields(output)))
        seam = constrained_infiller_seam_loss(
            left_output,
            right_output,
            left_duration=data.condition[left_indices, -1].to(device),
            right_duration=data.condition[right_indices, -1].to(device),
            q_valid=torch.ones(pair_count, device=device),
        )
        optimizer.zero_grad(set_to_none=True)
        (losses.total + 0.2 * seam.total).backward()
        gradient_norm = clip_grad_norm_(model.parameters(), 2.0)
        optimizer.step()

        if step == 1 or step % args.log_every == 0 or step == args.steps:
            record = {item.name: float(getattr(losses, item.name).detach()) for item in fields(losses)}
            record["seam"] = {item.name: float(getattr(seam, item.name).detach()) for item in fields(seam)}
            record.update(step=step, gradient_norm=float(gradient_norm), samples=len(data), pairs=len(train_pairs))
            with torch.no_grad():
                validation_output = forward(validation_indices)
                validation_qpos = data.qpos[validation_indices].to(device)
                validation_contact = data.contact[validation_indices].to(device)
                target_position, target_rotation6d = model.fk(validation_qpos)
                output_rotation = _matrix_from_rotation6d(validation_output.keypoint_rotation6d)
                target_rotation = _matrix_from_rotation6d(target_rotation6d)
                contact_step_mean, contact_step_p95 = _persistent_contact_step_cm(
                    validation_output, validation_contact
                )
                target_output = type(validation_output)(
                    target_position,
                    target_rotation6d,
                    validation_output.contact_logits,
                    validation_qpos,
                )
                target_step_mean, target_step_p95 = _persistent_contact_step_cm(target_output, validation_contact)
                validation_points, validation_part = collision_geometry(model.fk, validation_output.auxiliary_qpos)
                validation_target_points, _ = collision_geometry(model.fk, validation_qpos)
                validation_collision = full_geometry_box_collision_penalty(
                    validation_points,
                    validation_part,
                    validation_contact,
                    box_center=data.box_center[validation_indices].to(device),
                    box_rotation=data.box_rotation[validation_indices].to(device),
                    box_half_extents=data.box_half_extents[validation_indices].to(device),
                    ground_height=data.ground_height[validation_indices].to(device),
                )
                validation_contact_surface = full_geometry_contact_surface_penalty(
                    validation_points,
                    validation_target_points,
                    validation_part,
                    validation_contact,
                    box_center=data.box_center[validation_indices].to(device),
                    box_rotation=data.box_rotation[validation_indices].to(device),
                    box_half_extents=data.box_half_extents[validation_indices].to(device),
                    ground_height=data.ground_height[validation_indices].to(device),
                )
                validation_left_indices = validation_pairs[:, 0]
                validation_right_indices = validation_pairs[:, 1]
                validation_pair_count = len(validation_left_indices)
                validation_pair_output = forward(
                    torch.cat((validation_left_indices, validation_right_indices))
                )
                validation_left_output = type(validation_pair_output)(
                    *(getattr(validation_pair_output, item.name)[:validation_pair_count] for item in fields(output))
                )
                validation_right_output = type(validation_pair_output)(
                    *(getattr(validation_pair_output, item.name)[validation_pair_count:] for item in fields(output))
                )
                validation_seam = constrained_infiller_seam_loss(
                    validation_left_output,
                    validation_right_output,
                    left_duration=data.condition[validation_left_indices, -1].to(device),
                    right_duration=data.condition[validation_right_indices, -1].to(device),
                    q_valid=torch.ones(validation_pair_count, device=device),
                )
                validation = {
                    "joint_mae_rad": float(
                        (validation_output.auxiliary_qpos[..., 7:] - validation_qpos[..., 7:]).abs().mean()
                    ),
                    "keypoint_error_cm": float(
                        torch.linalg.vector_norm(validation_output.keypoint_position - target_position, dim=-1)
                        .mean()
                        .mul(100.0)
                    ),
                    "keypoint_rotation_error_deg": float(
                        _rotation_angle_degrees(output_rotation, target_rotation).mean()
                    ),
                    "persistent_contact_step_mean_cm": float(contact_step_mean),
                    "persistent_contact_step_p95_cm": float(contact_step_p95),
                    "target_contact_step_mean_cm": float(target_step_mean),
                    "target_contact_step_p95_cm": float(target_step_p95),
                    "collision_penalty": float(validation_collision),
                    "contact_surface_penalty": float(validation_contact_surface),
                    "endpoint_q_max": float(
                        (validation_output.auxiliary_qpos[:, (0, -1)] - validation_qpos[:, (0, -1)]).abs().max()
                    ),
                    "seam": {
                        item.name: float(getattr(validation_seam, item.name)) for item in fields(validation_seam)
                    },
                }
                score = (
                    validation["keypoint_error_cm"]
                    + 0.1 * validation["keypoint_rotation_error_deg"]
                    + 5.0 * validation["joint_mae_rad"]
                    + validation["persistent_contact_step_p95_cm"]
                    + 100.0 * validation["collision_penalty"]
                    + 5.0 * validation["contact_surface_penalty"]
                    + float(validation_seam.total)
                )
                record["validation"] = validation
                record["validation_score"] = score
                if score < best_score:
                    best_score = score
                    best_step = step
                    best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
                    best_validation = dict(validation)
            history.append(record)
            print(json.dumps(record), flush=True)

    if best_state is None:
        raise RuntimeError("training produced no validation checkpoint")
    checkpoint = {
        "schema": "climb00_g1_contact_aware_q_infiller_v1",
        "model": best_state,
        "condition_mean": condition_mean,
        "condition_std": condition_std,
        "condition_dim": data.condition.shape[1],
        "phase_frames": args.phase_frames,
        "manifest": str(args.manifest.resolve()),
        "samples": len(data),
        "pairs": len(train_pairs),
        "best_validation_score": best_score,
        "best_step": best_step,
        "best_validation": best_validation,
    }
    torch.save(checkpoint, args.output / "model.pt")
    (args.output / "history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
