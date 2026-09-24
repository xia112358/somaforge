#!/usr/bin/env python3
"""Train a scan selector whose next boundary is a canonical-G1 q state."""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from climb00_pipeline.neural_infiller import (
    CanonicalG1ForwardKinematics,
    _matrix_from_rotation6d,
    _quaternion_multiply_wxyz,
    _rotation_chordal_error,
)
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from train_climb00_contact_event_predictor import split_name
from train_climb00_scan_contact_selector import (
    DEFAULT_MANIFEST,
    ROOT,
    ScanContactSelector,
    arrays,
    contact_stats,
    transition_labels,
    transition_vocabulary,
)
from train_climb00_scan_trajectory_deformer import action_medoid_bases, source_bases


class ScanQBoundarySelector(ScanContactSelector):
    """Select an action and a realizable full-body boundary in canonical q."""

    def __init__(
        self,
        state_dim: int,
        action_count: int,
        action_base_start_qpos: torch.Tensor,
        action_base_end_qpos: torch.Tensor,
        *,
        maximum_root_translation_m: float = 0.5,
        maximum_root_quaternion_delta: float = 0.7,
        maximum_joint_delta_rad: float = 1.0,
        **kwargs,
    ) -> None:
        super().__init__(state_dim, action_count, **kwargs)
        width = self.duration.in_features
        self.fk = CanonicalG1ForwardKinematics()
        self.register_buffer("action_base_start_qpos", action_base_start_qpos.float())
        self.register_buffer("action_base_end_qpos", action_base_end_qpos.float())
        self.maximum_root_translation_m = float(maximum_root_translation_m)
        self.maximum_root_quaternion_delta = float(maximum_root_quaternion_delta)
        self.maximum_joint_delta_rad = float(maximum_joint_delta_rad)
        self.q_boundary = nn.Sequential(nn.Linear(width, width), nn.SiLU(), nn.Linear(width, 36))

    def aligned_action_endpoint(self, action_index: torch.Tensor, current_qpos: torch.Tensor) -> torch.Tensor:
        base_start = self.action_base_start_qpos[action_index]
        base_end = self.action_base_end_qpos[action_index]
        root_position = base_end[:, :3] + current_qpos[:, :3] - base_start[:, :3]
        start_quaternion = F.normalize(base_start[:, 3:7], dim=-1)
        inverse_start = torch.cat((start_quaternion[:, :1], -start_quaternion[:, 1:]), dim=-1)
        correction = _quaternion_multiply_wxyz(F.normalize(current_qpos[:, 3:7], dim=-1), inverse_start)
        root_quaternion = F.normalize(
            _quaternion_multiply_wxyz(correction, F.normalize(base_end[:, 3:7], dim=-1)), dim=-1
        )
        joints = base_end[:, 7:] + current_qpos[:, 7:] - base_start[:, 7:]
        joints = torch.maximum(torch.minimum(joints, self.fk.joint_upper), self.fk.joint_lower)
        return torch.cat((root_position, root_quaternion, joints), dim=-1)

    def decode_q_boundary(
        self, hidden: torch.Tensor, action_index: torch.Tensor, current_qpos: torch.Tensor
    ) -> torch.Tensor:
        value = self.parameter_trunk(torch.cat((hidden, self.action_embedding(action_index)), dim=-1)).detach()
        residual = self.q_boundary(value)
        base = self.aligned_action_endpoint(action_index, current_qpos)
        root_position = base[:, :3] + self.maximum_root_translation_m * torch.tanh(residual[:, :3])
        root_quaternion = F.normalize(
            base[:, 3:7] + self.maximum_root_quaternion_delta * torch.tanh(residual[:, 3:7]), dim=-1
        )
        joints = base[:, 7:] + self.maximum_joint_delta_rad * torch.tanh(residual[:, 7:])
        joints = torch.maximum(torch.minimum(joints, self.fk.joint_upper), self.fk.joint_lower)
        return torch.cat((root_position, root_quaternion, joints), dim=-1)

    def forward(
        self,
        state: torch.Tensor,
        scan: torch.Tensor,
        current_qpos: torch.Tensor,
        action_index: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, ...]:
        hidden, action_logits = self.encode(state, scan)
        if action_index is None:
            action_index = action_logits.argmax(dim=-1)
        end_contact, target_contact, duration = super().decode_parameters(hidden, action_index)
        qpos = self.decode_q_boundary(hidden, action_index, current_qpos)
        position, rotation6d = self.fk(qpos)
        return action_logits, end_contact, target_contact, duration, qpos, position, rotation6d


def initialize_from_sparse_selector(model: ScanQBoundarySelector, checkpoint: dict) -> None:
    """Warm-start the unchanged sparse selector and leave only the new q head random."""

    source = checkpoint["model"]
    target = model.state_dict()
    copied = {}
    for name, value in source.items():
        if name not in target:
            continue
        if target[name].shape == value.shape:
            copied[name] = value
            continue
        if name == "state.0.weight" and target[name].shape[0] == value.shape[0]:
            expanded = torch.zeros_like(target[name])
            expanded[:, : value.shape[1]] = value
            copied[name] = expanded
    model.load_state_dict(copied, strict=False)


def q_loss(output_q: torch.Tensor, target_q: torch.Tensor) -> torch.Tensor:
    return (
        ((output_q[:, :3] - target_q[:, :3]) / 0.01).square().mean()
        + 10.0 * (1.0 - (output_q[:, 3:7] * target_q[:, 3:7]).sum(dim=-1).abs()).mean()
        + ((output_q[:, 7:] - target_q[:, 7:]) / 0.05).square().mean()
    )


@torch.no_grad()
def evaluate(model, loader, stats, device) -> dict[str, float]:
    model.eval()
    state_mean, state_std, scan_mean, scan_std, contact_mean, contact_std, duration_mean, duration_std = stats
    action_correct = []
    position_errors = []
    rotation_errors = []
    q_joint_errors = []
    contact_errors = []
    duration_errors = []
    for batch in loader:
        state, scan, current_q, label, target_contact, touchdown, duration, target_q, target_p, target_r = [
            value.to(device) for value in batch
        ]
        output = model(
            (state - state_mean) / state_std,
            (scan - scan_mean) / scan_std,
            current_q,
        )
        action = output[0].argmax(dim=-1)
        action_correct.append((action == label).cpu().numpy())
        position_errors.append(torch.linalg.vector_norm(output[5] - target_p, dim=-1).cpu().numpy() * 100.0)
        relative = _matrix_from_rotation6d(output[6]).transpose(-1, -2) @ _matrix_from_rotation6d(target_r)
        cosine = ((relative.diagonal(dim1=-2, dim2=-1).sum(dim=-1) - 1.0) * 0.5).clamp(-1.0, 1.0)
        rotation_errors.append(torch.rad2deg(torch.acos(cosine)).cpu().numpy())
        q_joint_errors.append((output[4][:, 7:] - target_q[:, 7:]).abs().cpu().numpy())
        predicted_contact = output[2] * contact_std + contact_mean
        active = touchdown > 0.5
        contact_errors.append(
            torch.linalg.vector_norm(predicted_contact - target_contact, dim=-1)[active].cpu().numpy()
        )
        predicted_duration = torch.exp(output[3] * duration_std + duration_mean)
        duration_errors.append((predicted_duration - duration).abs().cpu().numpy() * 50.0)
    position = np.concatenate(position_errors)
    rotation = np.concatenate(rotation_errors)
    joint = np.concatenate(q_joint_errors)
    contact = np.concatenate(contact_errors) * 100.0
    return {
        "action_accuracy": float(np.concatenate(action_correct).mean()),
        "boundary_position_cm_mean": float(position.mean()),
        "boundary_position_cm_p95": float(np.quantile(position, 0.95)),
        "boundary_position_cm_max": float(position.max()),
        "boundary_rotation_deg_mean": float(rotation.mean()),
        "joint_error_rad_mean": float(joint.mean()),
        "contact_error_cm_mean": float(contact.mean()),
        "duration_error_frames": float(np.concatenate(duration_errors).mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--q-cache", type=Path, default=ROOT / "tmp/climb00_action_q_segments_64_v1.npz")
    parser.add_argument(
        "--initial-checkpoint",
        type=Path,
        default=ROOT / "tmp/climb00_scan_full_boundary_selector_heading_clean1024_v10/model.pt",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/climb00_scan_q_boundary_selector_v1")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--blocks", type=int, default=4)
    parser.add_argument("--action-embedding-dim", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=1.0e-4)
    parser.add_argument("--seed", type=int, default=20260829)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device(args.device)

    data, samples, event_summary, sparse_state, scan = arrays(args.manifest)
    with np.load(args.q_cache, allow_pickle=False) as cached:
        if str(cached["manifest"].item()) != str(args.manifest.resolve()):
            raise ValueError("q cache manifest does not match")
        target_q = np.asarray(cached["target_q"], np.float32)
        source_q = np.asarray(cached["source_q"], np.float32)
    splits = {
        name: np.asarray([i for i, sample in enumerate(samples) if split_name(sample.height) == name], np.int64)
        for name in ("train_height_095_100_105", "validation_height_090", "test_height_110")
    }
    train = splits["train_height_095_100_105"]
    touchdown_masks, end_masks = transition_vocabulary(data["touchdown"][train], data["end_contact"][train])
    labels = transition_labels(data["touchdown"], data["end_contact"], touchdown_masks, end_masks)
    source_p, source_r = source_bases(args.manifest, samples, target_q.shape[1])
    medoid = action_medoid_bases(data, samples, source_p, source_r, train, return_indices=True)
    _, _, _, _, _, _, counts, medoid_indices = medoid
    action_base_q = source_q[medoid_indices]

    state = sparse_state.astype(np.float32)
    state_mean = torch.from_numpy(state[train].mean(0).astype(np.float32)).to(device)
    state_std = torch.from_numpy(np.maximum(state[train].std(0), 1.0e-3).astype(np.float32)).to(device)
    scan_mean = torch.from_numpy(scan[train].mean(0).astype(np.float32)).to(device)
    scan_std = torch.from_numpy(np.maximum(scan[train].std(0), 1.0e-3).astype(np.float32)).to(device)
    contact_mean_np, contact_std_np = contact_stats(data["target_contacts"], data["touchdown"], train)
    contact_mean = torch.from_numpy(contact_mean_np).to(device)
    contact_std = torch.from_numpy(contact_std_np).to(device)
    duration_mean = torch.tensor(float(np.log(data["duration"][train]).mean()), device=device)
    duration_std = torch.tensor(float(max(np.log(data["duration"][train]).std(), 1.0e-3)), device=device)
    tensors = (
        torch.from_numpy(state),
        torch.from_numpy(scan.astype(np.float32)),
        torch.from_numpy(target_q[:, 0]),
        torch.from_numpy(labels),
        torch.from_numpy(data["target_contacts"]),
        torch.from_numpy(data["touchdown"]),
        torch.from_numpy(data["duration"]),
        torch.from_numpy(target_q[:, -1]),
        torch.from_numpy(data["positions"][:, -1]),
        torch.from_numpy(data["rotations"][:, -1]),
    )

    def dataset(indices: np.ndarray, *, shuffle: bool) -> DataLoader:
        values = TensorDataset(*(value[indices] for value in tensors))
        return DataLoader(values, batch_size=args.batch_size, shuffle=shuffle, drop_last=shuffle)

    train_loader = dataset(train, shuffle=True)
    validation_loader = dataset(splits["validation_height_090"], shuffle=False)
    model = ScanQBoundarySelector(
        state.shape[1],
        len(touchdown_masks),
        torch.from_numpy(action_base_q[:, 0]),
        torch.from_numpy(action_base_q[:, -1]),
        width=args.width,
        blocks=args.blocks,
        action_embedding_dim=args.action_embedding_dim,
        transition_end_contact_masks=torch.from_numpy(end_masks),
    ).to(device)
    initial = torch.load(args.initial_checkpoint, map_location="cpu", weights_only=False)
    initialize_from_sparse_selector(model, initial)
    optimizer = torch.optim.AdamW(model.q_boundary.parameters(), lr=args.learning_rate, weight_decay=1.0e-4)
    stats = (state_mean, state_std, scan_mean, scan_std, contact_mean, contact_std, duration_mean, duration_std)
    history = []
    best_score = math.inf
    best_state = None
    for epoch in range(1, args.epochs + 1):
        model.train()
        running = []
        for batch in train_loader:
            state_b, scan_b, current_q, label, _, _, _, target_q_end, target_p, target_r = [
                value.to(device) for value in batch
            ]
            indices = label
            output = model(
                (state_b - state_mean) / state_std,
                (scan_b - scan_mean) / scan_std,
                current_q,
                indices,
            )
            position_loss = ((output[5] - target_p) / 0.01).square().mean()
            rotation_loss = _rotation_chordal_error(
                _matrix_from_rotation6d(output[6]), _matrix_from_rotation6d(target_r)
            ).mean()
            loss = 2.0 * q_loss(output[4], target_q_end) + 2.0 * position_loss + rotation_loss
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.q_boundary.parameters(), 2.0)
            optimizer.step()
            running.append(float(loss.detach()))
        if epoch == 1 or epoch % 10 == 0 or epoch == args.epochs:
            metric = evaluate(model, validation_loader, stats, device)
            record = {"epoch": epoch, "train_loss": float(np.mean(running)), "validation": metric}
            print(json.dumps(record))
            history.append(record)
            score = metric["boundary_position_cm_mean"] + 5.0 * (1.0 - metric["action_accuracy"])
            if score < best_score:
                best_score = score
                best_state = copy.deepcopy(model.state_dict())
    assert best_state is not None
    model.load_state_dict(best_state)
    metrics = {
        name: evaluate(model, dataset(indices, shuffle=False), stats, device) for name, indices in splits.items()
    }
    checkpoint = {
        "schema": "climb00_scan_q_boundary_selector_v1",
        "model": best_state,
        "condition_dim": state.shape[1],
        "sparse_state_dim": sparse_state.shape[1],
        "action_touchdown_masks": torch.from_numpy(touchdown_masks),
        "action_end_contact_masks": torch.from_numpy(end_masks),
        "action_base_start_qpos": torch.from_numpy(action_base_q[:, 0]),
        "action_base_end_qpos": torch.from_numpy(action_base_q[:, -1]),
        "state_mean": state_mean.cpu(),
        "state_std": state_std.cpu(),
        "scan_mean": scan_mean.cpu(),
        "scan_std": scan_std.cpu(),
        "contact_mean": contact_mean.cpu(),
        "contact_std": contact_std.cpu(),
        "duration_mean": float(duration_mean.item()),
        "duration_std": float(duration_std.item()),
        "config": vars(args),
    }
    torch.save(checkpoint, args.output / "model.pt")
    (args.output / "report.json").write_text(
        json.dumps(
            {
                "schema": "climb00_scan_q_boundary_selector_report_v1",
                "event_dataset": event_summary,
                "action_base_counts": counts,
                "metrics": metrics,
                "history": history,
            },
            indent=2,
            default=str,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
