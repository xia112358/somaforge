#!/usr/bin/env python3
"""Prototype: add canonical-G1 q structure to the proven scan/action deformer."""

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
from climb00_pipeline.fullbody_dataset import _matrix_quaternion_wxyz, _quaternion_matrix_wxyz, _resample_qpos
from climb00_pipeline.neural_infiller import (
    CanonicalG1CollisionPoints,
    CanonicalG1ForwardKinematics,
    G1ActionMedoidQDeformer,
    _matrix_from_rotation6d,
    _rotation_chordal_error,
    full_geometry_box_penetration,
    full_geometry_contact_surface_penalty,
)
from climb00_scan_observation import SCAN_COLS, SCAN_ROWS, scans_from_local_box
from somaforge_core import G1_29DOF_JOINT_ORDER
from somaforge_core.robot_assets import decode_robot_asset_json
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from train_climb00_contact_conditioned_infiller import BODY_NAMES, build_dataset
from train_climb00_contact_event_predictor import split_name
from train_climb00_scan_contact_selector import ScanEncoder
from train_climb00_scan_q_boundary_selector import ScanQBoundarySelector
from train_climb00_scan_trajectory_deformer import action_medoid_bases, predicted_boundaries, source_bases

ROOT = Path(__file__).absolute().parents[1]


class ScanActionQDeformer(nn.Module):
    """Keep the original scan conditioning and deform a selected real q medoid."""

    def __init__(self, condition_dim: int, width: int, layers: int, heads: int, ffn: int):
        super().__init__()
        self.scan = ScanEncoder(width, SCAN_ROWS, SCAN_COLS)
        self.model = G1ActionMedoidQDeformer(
            condition_dim + width, width=width, layers=layers, heads=heads, ffn_width=ffn
        )

    @property
    def fk(self):
        return self.model.fk

    def forward(self, condition, scan, *args):
        return self.model(torch.cat((condition, self.scan(scan)), dim=-1), *args)


def _load_q_motion(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as loaded:
        if "joint_pos" not in loaded or "robot_asset_json" not in loaded:
            raise ValueError(f"{path} lacks canonical qpos metadata")
        if tuple(loaded["joint_names"].astype(str)) != G1_29DOF_JOINT_ORDER:
            raise ValueError(f"{path} does not use canonical G1 joint order")
        decode_robot_asset_json(str(np.asarray(loaded["robot_asset_json"]).item()), context=str(path))
        names = loaded["body_names"].astype(str).tolist()
        torso = names.index(BODY_NAMES[0])
        # Materialize compressed members once.  Keeping only NpzFile open is
        # insufficient: each loaded[key] access decompresses that member.
        return {
            "joint_pos": np.asarray(loaded["joint_pos"], np.float32),
            "torso_pos": np.asarray(loaded["body_pos_w"][:, torso], np.float64),
            "torso_quat": np.asarray(loaded["body_quat_w"][:, torso], np.float64),
        }


def _local_q_segment_from_loaded(
    loaded: dict[str, np.ndarray], path: Path, first: int, last: int, frames: int
) -> np.ndarray:
    if "joint_pos" not in loaded:
        raise ValueError(f"{path} lacks canonical qpos metadata")
    qpos = np.asarray(loaded["joint_pos"][first : last + 1], np.float32).copy()
    origin = loaded["torso_pos"][first]
    torso_rotation = _quaternion_matrix_wxyz(loaded["torso_quat"][first])
    heading = math.atan2(float(torso_rotation[1, 0]), float(torso_rotation[0, 0]))
    cosine, sine = math.cos(heading), math.sin(heading)
    world_to_local = np.asarray(((cosine, sine, 0), (-sine, cosine, 0), (0, 0, 1)), np.float64)
    qpos[:, :3] = np.einsum("ij,tj->ti", world_to_local, qpos[:, :3] - origin)
    root_rotation = _quaternion_matrix_wxyz(qpos[:, 3:7].astype(np.float64))
    qpos[:, 3:7] = _matrix_quaternion_wxyz(np.einsum("ij,tjk->tik", world_to_local, root_rotation))
    return _resample_qpos(qpos, frames).astype(np.float32)


def _local_q_segment(path: Path, first: int, last: int, frames: int) -> np.ndarray:
    return _local_q_segment_from_loaded(_load_q_motion(path), path, first, last, frames)


def q_segments(manifest_path: Path, samples, frames: int) -> tuple[np.ndarray, np.ndarray]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = np.zeros((len(samples), frames, 36), np.float32)
    source = np.zeros_like(target)
    source_cache: dict[Path, dict[str, np.ndarray]] = {}
    rows_by_motion: dict[int, list[tuple[int, object]]] = {}
    for row, sample in enumerate(samples):
        rows_by_motion.setdefault(int(sample.motion_id), []).append((row, sample))
    for motion_id, rows in rows_by_motion.items():
        entry = manifest["motion_files"][motion_id]
        target_path = Path(entry["motion_file"])
        plan = json.loads(Path(entry["edit_plan_file"]).read_text(encoding="utf-8"))
        source_path = Path(plan["source_motion_path"])
        # Loading once per motion avoids opening/decompressing the same NPZ
        # once per contact event (thousands of redundant reads here).
        target_loaded = _load_q_motion(target_path)
        if source_path not in source_cache:
            source_cache[source_path] = _load_q_motion(source_path)
        source_loaded = source_cache[source_path]
        for row, sample in rows:
            target[row] = _local_q_segment_from_loaded(
                target_loaded, target_path, sample.current_frame, sample.target_frame, frames
            )
            source[row] = _local_q_segment_from_loaded(
                source_loaded, source_path, sample.current_frame, sample.target_frame, frames
            )
    return target, source


def box_obbs(data: dict[str, np.ndarray]) -> tuple[np.ndarray, ...]:
    polygon = data["box_edge_start"]
    if polygon.ndim != 3 or polygon.shape[1:] != (4, 2):
        raise ValueError(f"box top polygons must have shape [N,4,2], got {polygon.shape}")

    # Surface tangent coordinates are an arbitrary orthonormal chart; they are
    # not guaranteed to align with the rectangular terrain edges.  Taking UV
    # min/max therefore constructs a circumscribed rectangle (twice the true
    # area for a 45-degree diamond).  Use adjacent polygon edges as the OBB
    # axes so the returned prism matches the actual terrain mesh.
    edge_u = polygon[:, 1] - polygon[:, 0]
    edge_v = polygon[:, 2] - polygon[:, 1]
    length_u = np.linalg.norm(edge_u, axis=-1)
    length_v = np.linalg.norm(edge_v, axis=-1)
    if np.any(length_u <= 1.0e-8) or np.any(length_v <= 1.0e-8):
        raise ValueError("box top polygons contain a degenerate edge")
    axis_u = edge_u / length_u[:, None]
    axis_v = edge_v / length_v[:, None]
    if np.any(np.abs(np.sum(axis_u * axis_v, axis=-1)) > 1.0e-4):
        raise ValueError("box top polygons must be rectangular")

    uv_center = polygon.mean(axis=1)
    top_center = data["box_origin"] + np.einsum("bij,bj->bi", data["box_basis"][:, :, :2], uv_center)
    world_u = np.einsum("bij,bj->bi", data["box_basis"][:, :, :2], axis_u)
    world_v = np.einsum("bij,bj->bi", data["box_basis"][:, :, :2], axis_v)
    rotation = np.stack((world_u, world_v, data["box_basis"][:, :, 2]), axis=-1)
    center = top_center - 0.5 * data["box_height"][:, None] * data["box_basis"][:, :, 2]
    half = np.stack((0.5 * length_u, 0.5 * length_v, 0.5 * data["box_height"]), axis=-1)
    ground = data["box_origin"][:, 2] - data["box_height"]
    return (
        center.astype(np.float32),
        rotation.astype(np.float32),
        half.astype(np.float32),
        ground.astype(np.float32),
    )


def residual_rms(qpos: torch.Tensor) -> torch.Tensor:
    phase = torch.linspace(0.0, 1.0, qpos.shape[1], dtype=qpos.dtype, device=qpos.device)[None, :, None]
    linear = (1.0 - phase) * qpos[:, :1, 7:] + phase * qpos[:, -1:, 7:]
    return (qpos[..., 7:] - linear).square().mean(dim=(1, 2)).sqrt()


def project_endpoint_q(
    initial_q: np.ndarray,
    target_position: np.ndarray,
    target_rotation6d: np.ndarray,
    device: torch.device,
    *,
    steps: int,
    batch_size: int = 256,
) -> tuple[np.ndarray, dict[str, float]]:
    """Offline-only canonical FK projection used as endpoint-q supervision."""

    fk = CanonicalG1ForwardKinematics().to(device)
    output = np.zeros_like(initial_q, dtype=np.float32)
    errors = []
    for begin in range(0, len(initial_q), batch_size):
        selected = slice(begin, min(begin + batch_size, len(initial_q)))
        original = torch.from_numpy(initial_q[selected]).to(device)
        target_p = torch.from_numpy(target_position[selected]).to(device)
        target_r = _matrix_from_rotation6d(torch.from_numpy(target_rotation6d[selected]).to(device))
        raw = original.clone().requires_grad_(True)
        optimizer = torch.optim.Adam((raw,), lr=0.02)
        for _ in range(steps):
            qpos = torch.cat(
                (
                    raw[:, :3],
                    F.normalize(raw[:, 3:7], dim=-1),
                    torch.maximum(torch.minimum(raw[:, 7:], fk.joint_upper), fk.joint_lower),
                ),
                dim=-1,
            )
            position, rotation6d = fk(qpos)
            position_loss = ((position - target_p) / 0.01).square().mean()
            rotation_loss = _rotation_chordal_error(_matrix_from_rotation6d(rotation6d), target_r).mean()
            regularization = ((qpos[:, 7:] - original[:, 7:]) / 0.5).square().mean()
            loss = position_loss + 2.0 * rotation_loss + 1.0e-4 * regularization
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
        with torch.no_grad():
            qpos = torch.cat(
                (
                    raw[:, :3],
                    F.normalize(raw[:, 3:7], dim=-1),
                    torch.maximum(torch.minimum(raw[:, 7:], fk.joint_upper), fk.joint_lower),
                ),
                dim=-1,
            )
            position, _ = fk(qpos)
            errors.append(torch.linalg.vector_norm(position - target_p, dim=-1).mean(dim=-1).cpu().numpy())
            output[selected] = qpos.cpu().numpy()
    error = np.concatenate(errors) * 100.0
    return output, {
        "mean_cm": float(error.mean()),
        "p95_cm": float(np.quantile(error, 0.95)),
        "max_cm": float(error.max()),
    }


@torch.no_grad()
def predicted_q_boundaries(
    checkpoint_path: Path,
    data: dict[str, np.ndarray],
    scans: np.ndarray,
    current_q: np.ndarray,
    device: torch.device,
) -> tuple[np.ndarray, ...]:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    if checkpoint.get("schema") != "climb00_scan_q_boundary_selector_v1":
        raise ValueError("predicted_q_boundaries requires a q-boundary selector")
    config = checkpoint["config"]
    model = ScanQBoundarySelector(
        int(checkpoint["condition_dim"]),
        len(checkpoint["action_touchdown_masks"]),
        checkpoint["action_base_start_qpos"],
        checkpoint["action_base_end_qpos"],
        width=int(config["width"]),
        blocks=int(config["blocks"]),
        action_embedding_dim=int(config["action_embedding_dim"]),
        transition_end_contact_masks=checkpoint["action_end_contact_masks"],
    ).to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    sparse_state = np.concatenate(
        (
            data["start_contacts"],
            data["positions"][:, 0].reshape(len(scans), -1),
            data["rotations"][:, 0].reshape(len(scans), -1),
        ),
        axis=-1,
    ).astype(np.float32)
    state = sparse_state
    outputs: list[list[np.ndarray]] = [[] for _ in range(7)]
    for begin in range(0, len(scans), 256):
        selected = slice(begin, min(begin + 256, len(scans)))
        state_value = torch.from_numpy(state[selected]).to(device)
        scan_value = torch.from_numpy(scans[selected]).to(device)
        output = model(
            (state_value - checkpoint["state_mean"].to(device)) / checkpoint["state_std"].to(device),
            (scan_value - checkpoint["scan_mean"].to(device)) / checkpoint["scan_std"].to(device),
            torch.from_numpy(current_q[selected]).to(device),
        )
        action = output[0].argmax(dim=-1)
        duration = torch.exp(output[3] * float(checkpoint["duration_std"]) + float(checkpoint["duration_mean"]))
        values = (
            output[5],
            output[6],
            action,
            duration,
            checkpoint["action_touchdown_masks"].to(device)[action],
            checkpoint["action_end_contact_masks"].to(device)[action],
            output[4],
        )
        for destination, value in zip(outputs, values, strict=True):
            destination.append(value.cpu().numpy())
    return tuple(np.concatenate(value, axis=0) for value in outputs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path, default=ROOT / "tmp/climb00_continuous_coverage/training_manifest_207.json"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/climb00_scan_action_q_deformer_probe_v1")
    parser.add_argument(
        "--selector-checkpoint",
        type=Path,
        default=ROOT / "tmp/climb00_scan_full_boundary_selector_heading_clean1024_v10/model.pt",
    )
    parser.add_argument("--q-cache", type=Path, default=ROOT / "tmp/climb00_action_q_segments_64_v1.npz")
    parser.add_argument(
        "--endpoint-q-cache", type=Path, default=ROOT / "tmp/climb00_selector_endpoint_q_projection_v1.npz"
    )
    parser.add_argument("--endpoint-projection-steps", type=int, default=150)
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--phase-frames", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--width", type=int, default=192)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--heads", type=int, default=6)
    parser.add_argument("--ffn", type=int, default=768)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--maximum-mesh-points", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device(args.device)

    data, samples, summary = build_dataset(args.manifest, args.phase_frames)
    source_p, source_r = source_bases(args.manifest, samples, args.phase_frames)
    if args.q_cache.exists():
        with np.load(args.q_cache, allow_pickle=False) as cached:
            if int(cached["phase_frames"]) != args.phase_frames:
                raise ValueError("q cache phase length does not match")
            if str(cached["manifest"].item()) != str(args.manifest.resolve()):
                raise ValueError("q cache manifest does not match")
            target_q = np.asarray(cached["target_q"], np.float32)
            source_q = np.asarray(cached["source_q"], np.float32)
    else:
        target_q, source_q = q_segments(args.manifest, samples, args.phase_frames)
        np.savez_compressed(
            args.q_cache,
            target_q=target_q,
            source_q=source_q,
            phase_frames=np.asarray(args.phase_frames, np.int64),
            manifest=np.asarray(str(args.manifest.resolve())),
        )
    scans = scans_from_local_box(
        data["box_origin"],
        data["box_basis"],
        data["box_edge_start"],
        data["box_edge_inward"],
        data["box_height"],
    )
    train = np.asarray(
        [i for i, sample in enumerate(samples) if split_name(sample.height) == "train_height_095_100_105"], np.int64
    )
    validation = np.asarray(
        [i for i, sample in enumerate(samples) if split_name(sample.height) == "validation_height_090"], np.int64
    )
    medoid = action_medoid_bases(data, samples, source_p, source_r, train, return_indices=True)
    medoid_p, medoid_r, medoid_c, labels, touchdown_masks, end_masks, counts, medoid_indices = medoid
    action_base_q = source_q[medoid_indices]
    selector_checkpoint = torch.load(args.selector_checkpoint, map_location="cpu", weights_only=False)
    if selector_checkpoint.get("schema") == "climb00_scan_q_boundary_selector_v1":
        predicted = predicted_q_boundaries(args.selector_checkpoint, data, scans, target_q[:, 0], device)
        (
            predicted_p,
            predicted_r,
            predicted_action,
            predicted_duration,
            predicted_touchdown,
            predicted_end_contact,
            projected_end_q,
        ) = predicted
        projection_metrics = {
            "method": "selector_direct_canonical_q",
            "mean_cm": 0.0,
            "p95_cm": 0.0,
            "max_cm": 0.0,
        }
    else:
        predicted = predicted_boundaries(args.selector_checkpoint, data, scans, device)
        predicted_p, predicted_r, predicted_action, predicted_duration, predicted_touchdown, predicted_end_contact = (
            predicted
        )
        if args.endpoint_q_cache.exists():
            with np.load(args.endpoint_q_cache, allow_pickle=False) as cached:
                if str(cached["selector"].item()) != str(args.selector_checkpoint.resolve()):
                    raise ValueError("endpoint q cache selector does not match")
                projected_end_q = np.asarray(cached["projected_end_q"], np.float32)
                projection_metrics = json.loads(str(cached["metrics"].item()))
        else:
            projected_end_q, projection_metrics = project_endpoint_q(
                target_q[:, -1],
                predicted_p,
                predicted_r,
                device,
                steps=args.endpoint_projection_steps,
            )
            np.savez_compressed(
                args.endpoint_q_cache,
                projected_end_q=projected_end_q,
                selector=np.asarray(str(args.selector_checkpoint.resolve())),
                metrics=np.asarray(json.dumps(projection_metrics)),
            )
    base_q = action_base_q[predicted_action]
    style_q = np.where((predicted_action == labels)[:, None, None], target_q, base_q)
    start = np.concatenate(
        (data["positions"][:, 0].reshape(len(samples), -1), data["rotations"][:, 0].reshape(len(samples), -1)),
        axis=-1,
    )
    end = np.concatenate((predicted_p.reshape(len(samples), -1), predicted_r.reshape(len(samples), -1)), axis=-1)
    condition = np.concatenate(
        (
            start,
            end,
            data["start_contacts"],
            predicted_end_contact,
            predicted_touchdown,
            predicted_duration[:, None],
        ),
        axis=-1,
    ).astype(np.float32)
    action_contact = medoid_c[predicted_action]
    condition_mean = condition[train].mean(0).astype(np.float32)
    condition_std = np.maximum(condition[train].std(0), 1.0e-5).astype(np.float32)
    scan_mean = scans[train].mean(0).astype(np.float32)
    scan_std = np.maximum(scans[train].std(0), 1.0e-3).astype(np.float32)
    center, box_rotation, half_extents, ground = box_obbs(data)
    arrays = (
        (condition - condition_mean) / condition_std,
        (scans - scan_mean) / scan_std,
        base_q,
        target_q,
        style_q,
        data["positions"],
        data["rotations"],
        predicted_p,
        predicted_r,
        projected_end_q,
        action_contact,
        center,
        box_rotation,
        half_extents,
        ground,
    )
    loader = DataLoader(
        TensorDataset(*[torch.from_numpy(value[train]) for value in arrays]),
        batch_size=args.batch_size,
        shuffle=True,
        drop_last=True,
    )
    validation_loader = DataLoader(
        TensorDataset(*[torch.from_numpy(value[validation]) for value in arrays]), batch_size=64
    )
    iterator = iter(loader)
    model = ScanActionQDeformer(condition.shape[1], args.width, args.layers, args.heads, args.ffn).to(device)
    collision_geometry = CanonicalG1CollisionPoints(args.maximum_mesh_points).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-4)
    phase = torch.linspace(0.0, 1.0, args.phase_frames, device=device)[None]

    def losses(batch):
        c, scan, bq, start_q, style_q_batch, tp, tr, end_p, end_r, projected_q, contact, bc, br, bh, gh = (
            value.to(device) for value in batch
        )
        ph = phase.expand(len(c), -1)
        output = model(
            c,
            scan,
            ph,
            bq,
            start_q[:, 0],
            tp[:, 0],
            tr[:, 0],
            end_p,
            end_r,
            contact[:, 0],
            contact[:, -1],
            projected_q,
        )
        predicted_rotation = _matrix_from_rotation6d(output.keypoint_rotation6d)
        endpoint_position = ((output.keypoint_position[:, -1] - end_p) / 0.01).square().mean()
        endpoint_rotation = _rotation_chordal_error(predicted_rotation[:, -1], _matrix_from_rotation6d(end_r)).mean()
        endpoint_q = (
            ((output.auxiliary_qpos[:, -1, :3] - projected_q[:, :3]) / 0.005).square().mean()
            + 10.0 * (1.0 - (output.auxiliary_qpos[:, -1, 3:7] * projected_q[:, 3:7]).sum(dim=-1).abs()).mean()
            + ((output.auxiliary_qpos[:, -1, 7:] - projected_q[:, 7:]) / 0.03).square().mean()
        )
        pose = ((output.keypoint_position - tp) / 0.05).square().mean()
        q_velocity = output.auxiliary_qpos[:, 1:, 7:] - output.auxiliary_qpos[:, :-1, 7:]
        target_velocity = style_q_batch[:, 1:, 7:] - style_q_batch[:, :-1, 7:]
        style = ((q_velocity - target_velocity) / 0.08).square().mean()
        acceleration = (
            output.auxiliary_qpos[:, 2:, 7:]
            - 2 * output.auxiliary_qpos[:, 1:-1, 7:]
            + output.auxiliary_qpos[:, :-2, 7:]
        )
        target_acceleration = style_q_batch[:, 2:, 7:] - 2 * style_q_batch[:, 1:-1, 7:] + style_q_batch[:, :-2, 7:]
        smooth = ((acceleration - target_acceleration) / 0.04).square().mean()
        points, point_part = collision_geometry(model.fk, output.auxiliary_qpos)
        target_points, _ = collision_geometry(model.fk, start_q)
        penetration = full_geometry_box_penetration(
            points,
            point_part,
            contact,
            box_center=bc,
            box_rotation=br,
            box_half_extents=bh,
            ground_height=gh,
        )
        target_penetration = full_geometry_box_penetration(
            target_points,
            point_part,
            contact,
            box_center=bc,
            box_rotation=br,
            box_half_extents=bh,
            ground_height=gh,
        )
        excess_penetration = F.relu(penetration - target_penetration - 0.002)
        collision = (excess_penetration / 0.01).square().mean()
        collision = collision + (excess_penetration.amax(dim=(1, 2)) / 0.01).square().mean()
        surface = full_geometry_contact_surface_penalty(
            points,
            target_points,
            point_part,
            contact,
            box_center=bc,
            box_rotation=br,
            box_half_extents=bh,
            ground_height=gh,
        )
        total = 24.0 * endpoint_position + 4.0 * endpoint_rotation + 2.0 * endpoint_q + 0.08 * pose
        total = total + 0.15 * style + 0.05 * smooth + 8.0 * collision + 2.0 * surface
        return (
            output,
            total,
            (endpoint_position, endpoint_rotation, endpoint_q, pose, style, smooth, collision, surface),
            style_q_batch,
        )

    @torch.no_grad()
    def evaluate():
        model.eval()
        metrics = []
        for batch in validation_loader:
            output, total, terms, target = losses(batch)
            endpoint_cm = torch.linalg.vector_norm(output.keypoint_position[:, -1] - batch[7].to(device), dim=-1)
            retained = residual_rms(output.auxiliary_qpos) / residual_rms(target).clamp_min(1.0e-6)
            metrics.append(
                (
                    float(total),
                    float(endpoint_cm.mean() * 100),
                    float(endpoint_cm.max() * 100),
                    float(retained.mean()),
                    *(float(value) for value in terms),
                )
            )
        model.train()
        values = np.asarray(metrics)
        names = (
            "loss",
            "endpoint_cm_mean",
            "endpoint_cm_max",
            "action_residual_retained",
            "endpoint_position",
            "endpoint_rotation",
            "endpoint_q",
            "pose",
            "style",
            "smooth",
            "collision",
            "surface",
        )
        return {name: float(values[:, index].mean()) for index, name in enumerate(names)}

    history = []
    best_state = None
    best_score = math.inf
    for step in range(1, args.steps + 1):
        try:
            batch = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            batch = next(iterator)
        _, total, _, _ = losses(batch)
        optimizer.zero_grad(set_to_none=True)
        total.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        optimizer.step()
        if step == 1 or step % 100 == 0 or step == args.steps:
            validation_metrics = evaluate()
            record = {"step": step, "train_loss": float(total.detach()), "validation": validation_metrics}
            print(json.dumps(record))
            history.append(record)
            score = validation_metrics["endpoint_cm_mean"] + 0.05 * validation_metrics["collision"]
            if score < best_score:
                best_score = score
                best_state = copy.deepcopy(model.state_dict())
    assert best_state is not None
    checkpoint = {
        "schema": "climb00_scan_action_q_deformer_v1",
        "model": best_state,
        "condition_dim": condition.shape[1],
        "condition_mean": torch.from_numpy(condition_mean),
        "condition_std": torch.from_numpy(condition_std),
        "scan_mean": torch.from_numpy(scan_mean),
        "scan_std": torch.from_numpy(scan_std),
        "phase_frames": args.phase_frames,
        "action_base_qpos": torch.from_numpy(action_base_q),
        "action_base_contact": torch.from_numpy(medoid_c),
        "action_base_position": torch.from_numpy(medoid_p),
        "action_base_rotation": torch.from_numpy(medoid_r),
        "action_touchdown_masks": torch.from_numpy(touchdown_masks),
        "action_end_contact_masks": torch.from_numpy(end_masks),
        "selector_checkpoint": str(args.selector_checkpoint.resolve()),
        "config": vars(args),
    }
    torch.save(checkpoint, args.output / "model.pt")
    (args.output / "report.json").write_text(
        json.dumps(
            {
                "schema": "climb00_scan_action_q_deformer_report_v1",
                "dataset": summary,
                "train_samples": len(train),
                "validation_samples": len(validation),
                "action_base_counts": counts,
                "endpoint_projection": projection_metrics,
                "best_score": best_score,
                "history": history,
            },
            indent=2,
            default=str,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
