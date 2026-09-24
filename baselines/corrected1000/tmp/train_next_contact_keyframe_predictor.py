#!/usr/bin/env python3
"""Train an offline next-contact keyframe predictor on climb00 coverage207."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tmp/climb00_continuous_coverage/training_manifest_207.json"
DEFAULT_OUTPUT = ROOT / "tmp/climb00_next_contact_keyframe_v1"
KEY_BODIES = (
    "torso_link",
    "left_ankle_roll_link",
    "right_ankle_roll_link",
    "left_wrist_yaw_link",
    "right_wrist_yaw_link",
    "left_knee_link",
    "right_knee_link",
)


def quat_wxyz_to_matrix(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64)
    q = q / np.maximum(np.linalg.norm(q, axis=-1, keepdims=True), 1.0e-12)
    w, x, y, z = np.moveaxis(q, -1, 0)
    return np.stack(
        (
            1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
            2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
            2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y),
        ),
        axis=-1,
    ).reshape(q.shape[:-1] + (3, 3))


def matrix_to_rotation_6d(matrix: np.ndarray) -> np.ndarray:
    return np.asarray(matrix)[..., :, :2].reshape(np.asarray(matrix).shape[:-2] + (6,))


def rotation_6d_to_matrix(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=np.float64).reshape(value.shape[:-1] + (3, 2))
    first = value[..., :, 0]
    first /= np.maximum(np.linalg.norm(first, axis=-1, keepdims=True), 1.0e-12)
    second = value[..., :, 1] - np.sum(first * value[..., :, 1], axis=-1, keepdims=True) * first
    second /= np.maximum(np.linalg.norm(second, axis=-1, keepdims=True), 1.0e-12)
    third = np.cross(first, second)
    return np.stack((first, second, third), axis=-1)


def yaw_from_wxyz(q: np.ndarray) -> float:
    w, x, y, z = (float(v) for v in q)
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def yaw_inverse_matrix(yaw: float) -> np.ndarray:
    c, s = math.cos(yaw), math.sin(yaw)
    return np.asarray(((c, s, 0.0), (-s, c, 0.0), (0.0, 0.0, 1.0)), dtype=np.float64)


def grouped_touchdowns(contact: np.ndarray, merge_gap: int = 4) -> list[tuple[int, np.ndarray]]:
    contact = np.asarray(contact, dtype=bool)
    rising = contact[1:] & ~contact[:-1]
    frames = np.flatnonzero(rising.any(axis=1)) + 1
    if not len(frames):
        return []
    groups: list[list[int]] = [[int(frames[0])]]
    for frame in frames[1:]:
        if int(frame) - groups[-1][-1] <= merge_gap:
            groups[-1].append(int(frame))
        else:
            groups.append([int(frame)])
    output = []
    for group in groups:
        bits = np.any(rising[np.asarray(group) - 1], axis=0)
        output.append((group[-1], bits))
    return output


def task_condition(entry: dict) -> np.ndarray:
    plan_path = Path(entry["edit_plan_file"])
    plan = json.loads(plan_path.read_text())
    metadata = plan["metadata"]
    angle = math.radians(float(metadata["target_incidence_degrees"]))
    uv = metadata.get("surface_uv_delta") or (0.0, 0.0)
    return np.asarray(
        (
            float(metadata["height_scale"]),
            float(metadata.get("approach_distance_m", 0.0)),
            math.sin(angle),
            math.cos(angle),
            float(uv[0]),
            float(uv[1]),
        ),
        dtype=np.float32,
    )


def source_contact_schedule(entry: dict, frame_count: int) -> np.ndarray:
    """Newton labels for THIS motion, never its unmodified source timeline."""
    from somaforge_core.newton_contact_data import load_entry_contacts
    return load_entry_contacts(entry, frame_count)['contact_part_mask']


@dataclass
class Sample:
    motion_id: int
    source: str
    height: float
    current_frame: int
    target_frame: int
    x: np.ndarray
    continuous: np.ndarray
    touchdown: np.ndarray
    contact: np.ndarray


def keyframe_features(
    positions: np.ndarray,
    rotations: np.ndarray,
    frame: int,
    body_indices: np.ndarray,
    origin: np.ndarray,
    yaw_inverse: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    pos = np.einsum("ij,bj->bi", yaw_inverse, positions[frame, body_indices] - origin)
    rot = np.einsum("ij,bjk->bik", yaw_inverse, rotations[frame, body_indices])
    return pos.astype(np.float32), matrix_to_rotation_6d(rot).astype(np.float32)


def build_samples(manifest_path: Path) -> tuple[list[Sample], dict]:
    manifest = json.loads(manifest_path.read_text())
    samples: list[Sample] = []
    per_motion = []
    for motion_number, entry in enumerate(manifest["motion_files"]):
        path = Path(entry["motion_file"])
        condition = task_condition(entry)
        with np.load(path, allow_pickle=False) as loaded:
            names = loaded["body_names"].astype(str).tolist()
            body_indices = np.asarray([names.index(name) for name in KEY_BODIES], dtype=np.int64)
            positions = np.asarray(loaded["body_pos_w"], dtype=np.float64)
            rotations = quat_wxyz_to_matrix(np.asarray(loaded["body_quat_w"], dtype=np.float64))
            fps = float(np.asarray(loaded["fps"]).item())
        contact = source_contact_schedule(entry, len(positions))
        events = grouped_touchdowns(contact)
        current_frame = 0
        count = 0
        for target_frame, touchdown in events:
            if target_frame - current_frame < 5:
                continue
            torso_index = body_indices[0]
            origin = positions[current_frame, torso_index].copy()
            # Use the torso world rotation already loaded above; yaw is extracted
            # from its matrix so the entire sample is current-torso-yaw centered.
            torso_matrix = rotations[current_frame, torso_index]
            yaw_value = math.atan2(float(torso_matrix[1, 0]), float(torso_matrix[0, 0]))
            yaw_inverse = yaw_inverse_matrix(yaw_value)
            current_pos, current_rot6 = keyframe_features(
                positions, rotations, current_frame, body_indices, origin, yaw_inverse
            )
            target_pos, target_rot6 = keyframe_features(
                positions, rotations, target_frame, body_indices, origin, yaw_inverse
            )
            current_contact = contact[current_frame].astype(np.float32)
            x = np.concatenate(
                (current_pos.reshape(-1), current_rot6.reshape(-1), current_contact, condition), axis=0
            ).astype(np.float32)
            duration_s = (target_frame - current_frame) / fps
            continuous = np.concatenate(
                (target_pos.reshape(-1), target_rot6.reshape(-1), np.asarray((duration_s,), dtype=np.float32)),
                axis=0,
            ).astype(np.float32)
            samples.append(
                Sample(
                    motion_id=motion_number,
                    source=str(path),
                    height=float(condition[0]),
                    current_frame=current_frame,
                    target_frame=target_frame,
                    x=x,
                    continuous=continuous,
                    touchdown=touchdown.astype(np.float32),
                    contact=contact[target_frame].astype(np.float32),
                )
            )
            current_frame = target_frame
            count += 1
        per_motion.append(count)
    if not samples:
        raise RuntimeError("no touchdown samples extracted")
    summary = {
        "motion_count": len(manifest["motion_files"]),
        "sample_count": len(samples),
        "events_per_motion": {
            "min": int(min(per_motion)),
            "mean": float(np.mean(per_motion)),
            "max": int(max(per_motion)),
        },
        "key_bodies": list(KEY_BODIES),
        "contact_dimension": int(samples[0].contact.size),
        "input_dimension": int(samples[0].x.size),
        "continuous_output_dimension": int(samples[0].continuous.size),
    }
    return samples, summary


class ResidualBlock(nn.Module):
    def __init__(self, width: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(width), nn.Linear(width, width * 2), nn.SiLU(), nn.Linear(width * 2, width)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.net(x)


class Predictor(nn.Module):
    def __init__(self, input_dim: int, continuous_dim: int, contact_dim: int, width: int, blocks: int):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(input_dim, width),
            nn.SiLU(),
            *(ResidualBlock(width) for _ in range(blocks)),
            nn.LayerNorm(width),
        )
        self.continuous = nn.Linear(width, continuous_dim)
        self.touchdown = nn.Linear(width, contact_dim)
        self.contact = nn.Linear(width, contact_dim)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        h = self.trunk(x)
        return self.continuous(h), self.touchdown(h), self.contact(h)


def normalization(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = values.mean(axis=0)
    std = values.std(axis=0)
    std = np.where(std < 1.0e-5, 1.0, std)
    return mean.astype(np.float32), std.astype(np.float32)


def split_name(height: float) -> str:
    if height >= 1.075:
        return "test_height_110"
    if height <= 0.925:
        return "validation_height_090"
    return "train_height_095_100_105"


def angular_error_degrees(predicted: np.ndarray, target: np.ndarray) -> np.ndarray:
    relative = np.einsum("...ji,...jk->...ik", predicted, target)
    cosine = np.clip((np.trace(relative, axis1=-2, axis2=-1) - 1.0) * 0.5, -1.0, 1.0)
    return np.degrees(np.arccos(cosine))


def metrics(
    model: Predictor,
    samples: list[Sample],
    indices: np.ndarray,
    x_mean: np.ndarray,
    x_std: np.ndarray,
    y_mean: np.ndarray,
    y_std: np.ndarray,
    device: torch.device,
) -> tuple[dict, list[dict]]:
    x = np.stack([samples[i].x for i in indices])
    target = np.stack([samples[i].continuous for i in indices])
    touchdown = np.stack([samples[i].touchdown for i in indices])
    contact = np.stack([samples[i].contact for i in indices])
    with torch.no_grad():
        output, touchdown_logits, contact_logits = model(
            torch.as_tensor((x - x_mean) / x_std, dtype=torch.float32, device=device)
        )
    predicted = output.cpu().numpy() * y_std + y_mean
    touchdown_pred = (torch.sigmoid(touchdown_logits).cpu().numpy() >= 0.5)
    contact_pred = (torch.sigmoid(contact_logits).cpu().numpy() >= 0.5)
    body_count = len(KEY_BODIES)
    pos_dim = body_count * 3
    rot_dim = body_count * 6
    predicted_pos = predicted[:, :pos_dim].reshape(-1, body_count, 3)
    target_pos = target[:, :pos_dim].reshape(-1, body_count, 3)
    predicted_rot = rotation_6d_to_matrix(predicted[:, pos_dim : pos_dim + rot_dim].reshape(-1, body_count, 6))
    target_rot = rotation_6d_to_matrix(target[:, pos_dim : pos_dim + rot_dim].reshape(-1, body_count, 6))
    position_error = np.linalg.norm(predicted_pos - target_pos, axis=-1) * 100.0
    rotation_error = angular_error_degrees(predicted_rot, target_rot)
    active_position = []
    active_rotation = []
    # Contact parts are [heel,toe,heel,toe,LH,RH,LK,RK]. Map them to
    # [left foot,right foot,left hand,right hand,left knee,right knee].
    part_to_body = np.asarray((1, 1, 2, 2, 3, 4, 5, 6), dtype=np.int64)
    for row in range(len(indices)):
        active = np.unique(part_to_body[touchdown[row].astype(bool)])
        if len(active):
            active_position.extend(position_error[row, active].tolist())
            active_rotation.extend(rotation_error[row, active].tolist())
    duration_error = np.abs(predicted[:, -1] - target[:, -1]) * 50.0
    touchdown_exact = np.all(touchdown_pred == touchdown.astype(bool), axis=1)
    contact_exact = np.all(contact_pred == contact.astype(bool), axis=1)
    tp = np.count_nonzero(touchdown_pred & touchdown.astype(bool))
    fp = np.count_nonzero(touchdown_pred & ~touchdown.astype(bool))
    fn = np.count_nonzero(~touchdown_pred & touchdown.astype(bool))
    f1 = 2 * tp / max(2 * tp + fp + fn, 1)

    def stats(value: np.ndarray | list[float]) -> dict[str, float]:
        value = np.asarray(value, dtype=np.float64)
        return {
            "mean": float(value.mean()),
            "p95": float(np.quantile(value, 0.95)),
            "max": float(value.max()),
        }

    result = {
        "samples": int(len(indices)),
        "all_keypoint_position_error_cm": stats(position_error),
        "active_touchdown_position_error_cm": stats(active_position),
        "all_keypoint_rotation_error_deg": stats(rotation_error),
        "active_touchdown_rotation_error_deg": stats(active_rotation),
        "duration_error_frames_at_50hz": stats(duration_error),
        "touchdown_exact_accuracy": float(touchdown_exact.mean()),
        "touchdown_micro_f1": float(f1),
        "target_contact_exact_accuracy": float(contact_exact.mean()),
    }
    rows = []
    for local, sample_index in enumerate(indices):
        sample = samples[int(sample_index)]
        rows.append(
            {
                "motion_id": sample.motion_id,
                "height": sample.height,
                "current_frame": sample.current_frame,
                "target_frame": sample.target_frame,
                "active_position_error_cm": float(
                    np.mean(position_error[local, np.unique(part_to_body[touchdown[local].astype(bool)])])
                ),
                "torso_position_error_cm": float(position_error[local, 0]),
                "duration_error_frames": float(duration_error[local]),
                "touchdown_exact": int(touchdown_exact[local]),
                "contact_exact": int(contact_exact[local]),
            }
        )
    return result, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--blocks", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--seed", type=int, default=20260824)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device(args.device)

    samples, dataset_summary = build_samples(args.manifest)
    splits = {name: np.asarray([i for i, sample in enumerate(samples) if split_name(sample.height) == name]) for name in (
        "train_height_095_100_105", "validation_height_090", "test_height_110"
    )}
    if any(not len(indices) for indices in splits.values()):
        raise RuntimeError({name: len(indices) for name, indices in splits.items()})
    train_indices = splits["train_height_095_100_105"]
    train_x = np.stack([samples[i].x for i in train_indices])
    train_y = np.stack([samples[i].continuous for i in train_indices])
    x_mean, x_std = normalization(train_x)
    y_mean, y_std = normalization(train_y)

    x_tensor = torch.as_tensor((train_x - x_mean) / x_std, dtype=torch.float32)
    y_tensor = torch.as_tensor((train_y - y_mean) / y_std, dtype=torch.float32)
    touchdown_tensor = torch.as_tensor(np.stack([samples[i].touchdown for i in train_indices]), dtype=torch.float32)
    contact_tensor = torch.as_tensor(np.stack([samples[i].contact for i in train_indices]), dtype=torch.float32)
    generator = torch.Generator().manual_seed(args.seed)
    loader = DataLoader(
        TensorDataset(x_tensor, y_tensor, touchdown_tensor, contact_tensor),
        batch_size=args.batch_size,
        shuffle=True,
        generator=generator,
    )
    model = Predictor(
        input_dim=train_x.shape[1],
        continuous_dim=train_y.shape[1],
        contact_dim=touchdown_tensor.shape[1],
        width=args.width,
        blocks=args.blocks,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-4)
    bce = nn.BCEWithLogitsLoss()
    best_state = None
    best_validation = float("inf")
    history = []
    validation_indices = splits["validation_height_090"]
    validation_x = torch.as_tensor(
        (np.stack([samples[i].x for i in validation_indices]) - x_mean) / x_std,
        dtype=torch.float32,
        device=device,
    )
    validation_y = torch.as_tensor(
        (np.stack([samples[i].continuous for i in validation_indices]) - y_mean) / y_std,
        dtype=torch.float32,
        device=device,
    )
    for epoch in range(args.epochs):
        model.train()
        running = 0.0
        for x_batch, y_batch, touchdown_batch, contact_batch in loader:
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device)
            touchdown_batch = touchdown_batch.to(device)
            contact_batch = contact_batch.to(device)
            output, touchdown_logits, contact_logits = model(x_batch)
            continuous_loss = torch.mean((output - y_batch) ** 2)
            loss = continuous_loss + 0.25 * bce(touchdown_logits, touchdown_batch) + 0.10 * bce(contact_logits, contact_batch)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            running += float(loss.detach()) * len(x_batch)
        model.eval()
        with torch.no_grad():
            validation_output, _, _ = model(validation_x)
            validation_loss = float(torch.mean((validation_output - validation_y) ** 2))
        history.append({"epoch": epoch + 1, "train_loss": running / len(train_indices), "validation_continuous_mse": validation_loss})
        if validation_loss < best_validation:
            best_validation = validation_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    assert best_state is not None
    model.load_state_dict(best_state)
    model.eval()

    split_metrics = {}
    detail_rows = []
    for name, indices in splits.items():
        split_metrics[name], rows = metrics(model, samples, indices, x_mean, x_std, y_mean, y_std, device)
        for row in rows:
            row["split"] = name
        detail_rows.extend(rows)
    checkpoint = {
        "state_dict": best_state,
        "model": {
            "input_dim": int(train_x.shape[1]),
            "continuous_dim": int(train_y.shape[1]),
            "contact_dim": int(touchdown_tensor.shape[1]),
            "width": args.width,
            "blocks": args.blocks,
        },
        "x_mean": torch.from_numpy(x_mean),
        "x_std": torch.from_numpy(x_std),
        "y_mean": torch.from_numpy(y_mean),
        "y_std": torch.from_numpy(y_std),
        "key_bodies": KEY_BODIES,
    }
    torch.save(checkpoint, args.output / "model.pt")
    np.savez_compressed(
        args.output / "dataset.npz",
        x=np.stack([sample.x for sample in samples]),
        continuous=np.stack([sample.continuous for sample in samples]),
        touchdown=np.stack([sample.touchdown for sample in samples]),
        contact=np.stack([sample.contact for sample in samples]),
        motion_id=np.asarray([sample.motion_id for sample in samples]),
        current_frame=np.asarray([sample.current_frame for sample in samples]),
        target_frame=np.asarray([sample.target_frame for sample in samples]),
        height=np.asarray([sample.height for sample in samples]),
    )
    with (args.output / "event_predictions.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(detail_rows[0]))
        writer.writeheader()
        writer.writerows(detail_rows)
    report = {
        "schema": "climb00_next_contact_keyframe_predictor_v1",
        "manifest": str(args.manifest.resolve()),
        "dataset": dataset_summary,
        "split_definition": {
            "train": "height in {0.95,1.00,1.05}",
            "validation": "height=0.90",
            "test": "height=1.10 (held-out extrapolation)",
        },
        "split_counts": {name: int(len(indices)) for name, indices in splits.items()},
        "model": {
            "type": "residual_mlp_one_step_event_predictor",
            "width": args.width,
            "blocks": args.blocks,
            "parameters": int(sum(parameter.numel() for parameter in model.parameters())),
            "best_validation_continuous_mse": best_validation,
        },
        "metrics": split_metrics,
        "artifacts": {
            "checkpoint": str((args.output / "model.pt").resolve()),
            "dataset": str((args.output / "dataset.npz").resolve()),
            "predictions": str((args.output / "event_predictions.csv").resolve()),
        },
    }
    (args.output / "history.json").write_text(json.dumps(history, indent=2) + "\n")
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
