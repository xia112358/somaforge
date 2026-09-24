"""Regenerate a sparse teacher with private full-body qpos, without IK."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch
from somaforge_core import G1_29DOF_JOINT_ORDER

from .contracts import BODY_NAMES, CONTACT_PARTS
from .fullbody_dataset import (
    _matrix_quaternion_wxyz,
    _phase_resample,
    _quaternion_matrix_wxyz,
    _resample_qpos,
    _resample_rotation6d,
)
from .neural_infiller import (
    CanonicalG1CollisionPoints,
    G1ConstrainedKeypointInfiller,
    _matrix_from_rotation6d,
    full_geometry_box_penetration,
)


def _condition_from_geometry(geometry: np.ndarray, duration: np.ndarray) -> tuple[np.ndarray, ...]:
    origin = geometry[:, :3]
    basis = geometry[:, 3:12].reshape(-1, 3, 3)
    polygon = geometry[:, 12:20].reshape(-1, 4, 2)
    height = geometry[:, 28]
    ground = geometry[:, 29]
    first_edge = polygon[:, 1] - polygon[:, 0]
    second_edge = polygon[:, 2] - polygon[:, 1]
    first_length = np.linalg.norm(first_edge, axis=-1)
    second_length = np.linalg.norm(second_edge, axis=-1)
    first_uv = first_edge / first_length[:, None]
    second_uv = second_edge / second_length[:, None]
    axis_x = np.einsum("bij,bj->bi", basis[:, :, :2], first_uv)
    axis_y = np.einsum("bij,bj->bi", basis[:, :, :2], second_uv)
    axis_z = basis[:, :, 2]
    top_center = origin + np.einsum("bij,bj->bi", basis[:, :, :2], polygon.mean(axis=1))
    center = top_center - 0.5 * height[:, None] * axis_z
    rotation = np.stack((axis_x, axis_y, axis_z), axis=-1).astype(np.float32)
    half_extents = np.stack((0.5 * first_length, 0.5 * second_length, 0.5 * height), axis=-1).astype(np.float32)
    condition = np.concatenate(
        (center, rotation[:, :, :2].reshape(-1, 6), half_extents, ground[:, None], duration[:, None]),
        axis=-1,
    ).astype(np.float32)
    return condition, center.astype(np.float32), rotation, half_extents, ground.astype(np.float32)


def _yaw_frame(position: np.ndarray, quaternion: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rotation = _quaternion_matrix_wxyz(quaternion.astype(np.float64))
    yaw = math.atan2(float(rotation[1, 0]), float(rotation[0, 0]))
    cosine, sine = math.cos(yaw), math.sin(yaw)
    axes = np.asarray(((cosine, -sine, 0), (sine, cosine, 0), (0, 0, 1)), dtype=np.float32)
    return position.astype(np.float32), axes


def _world_keypoints(
    local_position: np.ndarray, local_rotation6d: np.ndarray, origin: np.ndarray, axes: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    position = origin[None, None] + np.einsum("ij,tbj->tbi", axes, local_position)
    local_rotation = _matrix_from_rotation6d(torch.from_numpy(local_rotation6d)).numpy()
    rotation = np.einsum("ij,tbjk->tbik", axes, local_rotation)
    return position.astype(np.float32), _matrix_quaternion_wxyz(rotation)


def _world_qpos(local_qpos: np.ndarray, origin: np.ndarray, axes: np.ndarray) -> np.ndarray:
    output = local_qpos.copy()
    output[:, :3] = origin[None] + np.einsum("ij,tj->ti", axes, local_qpos[:, :3])
    local_rotation = _quaternion_matrix_wxyz(local_qpos[:, 3:7].astype(np.float64))
    output[:, 3:7] = _matrix_quaternion_wxyz(np.einsum("ij,tjk->tik", axes, local_rotation))
    return output.astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--maximum-mesh-points", type=int, default=32)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = json.loads((args.source / "report.json").read_text(encoding="utf-8"))
    with np.load(args.source / "teacher_events.npz", allow_pickle=False) as loaded:
        events = {name: np.asarray(loaded[name]) for name in loaded.files}
    checkpoint = torch.load(args.checkpoint, map_location=args.device, weights_only=False)
    model = G1ConstrainedKeypointInfiller(int(checkpoint["condition_dim"])).to(args.device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    collision_geometry = CanonicalG1CollisionPoints(args.maximum_mesh_points).to(args.device)
    phase_count = int(checkpoint["phase_frames"])
    phase = torch.linspace(0.0, 1.0, phase_count, device=args.device)[None]
    condition_mean = checkpoint["condition_mean"].to(args.device)
    condition_std = checkpoint["condition_std"].to(args.device)
    output_rows = []
    maximum_public_seam = 0.0
    maximum_q_joint_seam = 0.0
    maximum_q_root_seam = 0.0
    public_boundary_position_steps = []
    public_boundary_rotation_steps = []
    q_boundary_joint_steps = []
    maximum_proxy_penetration = 0.0
    fk_consistency_sum = 0.0
    fk_consistency_count = 0

    for trajectory_id, source_row in enumerate(report["samples"]):
        source_path = Path(source_row["motion_file"])
        with np.load(source_path, allow_pickle=False) as loaded:
            source_motion = {name: np.asarray(loaded[name]) for name in loaded.files}
        selected = np.flatnonzero(events["trajectory_id"].astype(np.int64) == trajectory_id)
        selected = selected[np.argsort(events["event_index"][selected])]
        boundary = source_motion["boundary_frames"].astype(np.int64)
        geometry = events["geometry"][selected].astype(np.float32)
        duration = events["duration"][selected].astype(np.float32)
        condition, center, box_rotation, half_extents, ground = _condition_from_geometry(geometry, duration)
        normalized = (torch.from_numpy(condition).to(args.device) - condition_mean) / condition_std
        phase_batch = phase.expand(len(selected), -1)
        start_position = torch.from_numpy(events["start_position"][selected].astype(np.float32)).to(args.device)
        start_rotation = torch.from_numpy(events["start_rotation"][selected].astype(np.float32)).to(args.device)
        end_position = torch.from_numpy(events["end_position"][selected].astype(np.float32)).to(args.device)
        end_rotation = torch.from_numpy(events["end_rotation"][selected].astype(np.float32)).to(args.device)
        start_contact = torch.from_numpy(events["start_contact"][selected].astype(np.float32)).to(args.device)
        end_contact = torch.from_numpy(events["end_contact"][selected].astype(np.float32)).to(args.device)
        with torch.no_grad():
            generated = model(
                normalized,
                phase_batch,
                start_position,
                start_rotation,
                end_position,
                end_rotation,
                start_contact,
                end_contact,
            )
            fk_position, _ = model.fk(generated.auxiliary_qpos)
            fk_consistency_sum += float(
                torch.linalg.vector_norm(generated.keypoint_position - fk_position, dim=-1).sum()
            )
            fk_consistency_count += int(generated.keypoint_position.shape[0] * phase_count * len(BODY_NAMES))
            points, point_part = collision_geometry(model.fk, generated.auxiliary_qpos)
            phase_contact = []
            for event in range(len(selected)):
                first, last = int(boundary[event]), int(boundary[event + 1])
                contact = source_motion["contact_force_part_mask"][first : last + 1].astype(np.float32)
                phase_contact.append(_phase_resample(contact, phase_count))
            phase_contact_tensor = torch.from_numpy(np.asarray(phase_contact)).to(args.device)
            penetration = full_geometry_box_penetration(
                points,
                point_part,
                phase_contact_tensor,
                box_center=torch.from_numpy(center).to(args.device),
                box_rotation=torch.from_numpy(box_rotation).to(args.device),
                box_half_extents=torch.from_numpy(half_extents).to(args.device),
                ground_height=torch.from_numpy(ground).to(args.device),
            )
            maximum_proxy_penetration = max(maximum_proxy_penetration, float(penetration.max()))

        local_position_phase = generated.keypoint_position.cpu().numpy()
        local_rotation_phase = generated.keypoint_rotation6d.cpu().numpy()
        local_qpos_phase = generated.auxiliary_qpos.cpu().numpy()
        output_position, output_quaternion, output_contact, output_qpos = [], [], [], []
        output_boundary = [0]
        previous_position = None
        previous_quaternion = None
        previous_qpos = None
        for event in range(len(selected)):
            first, last = int(boundary[event]), int(boundary[event + 1])
            length = last - first + 1
            local_position = _phase_resample(local_position_phase[event], length)
            local_rotation = _resample_rotation6d(local_rotation_phase[event], length)
            local_qpos = _resample_qpos(local_qpos_phase[event], length)
            torso_index = tuple(source_motion["body_names"].astype(str)).index(BODY_NAMES[0])
            origin, axes = _yaw_frame(
                source_motion["body_pos_w"][first, torso_index],
                source_motion["body_quat_w"][first, torso_index],
            )
            world_position, world_quaternion = _world_keypoints(local_position, local_rotation, origin, axes)
            world_qpos = _world_qpos(local_qpos, origin, axes)
            event_last_position = world_position[-1].copy()
            event_last_quaternion = world_quaternion[-1].copy()
            event_last_qpos = world_qpos[-1].copy()
            contact = source_motion["contact_force_part_mask"][first : last + 1].astype(bool)
            if previous_position is not None:
                maximum_public_seam = max(
                    maximum_public_seam, float(np.linalg.norm(world_position[0] - previous_position, axis=-1).max())
                )
                maximum_q_root_seam = max(
                    maximum_q_root_seam, float(np.linalg.norm(world_qpos[0, :3] - previous_qpos[:3]))
                )
                maximum_q_joint_seam = max(
                    maximum_q_joint_seam, float(np.abs(world_qpos[0, 7:] - previous_qpos[7:]).max())
                )
                public_boundary_position_steps.extend(
                    np.linalg.norm(world_position[1] - previous_position, axis=-1).tolist()
                )
                quaternion_dot = np.abs(np.sum(world_quaternion[1] * previous_quaternion, axis=-1)).clip(0.0, 1.0)
                public_boundary_rotation_steps.extend(np.degrees(2.0 * np.arccos(quaternion_dot)).tolist())
                q_boundary_joint_steps.extend(np.abs(world_qpos[1, 7:] - previous_qpos[7:]).tolist())
                world_position = world_position[1:]
                world_quaternion = world_quaternion[1:]
                world_qpos = world_qpos[1:]
                contact = contact[1:]
            output_position.append(world_position)
            output_quaternion.append(world_quaternion)
            output_qpos.append(world_qpos)
            output_contact.append(contact)
            previous_position = event_last_position
            previous_quaternion = event_last_quaternion
            previous_qpos = event_last_qpos
            output_boundary.append(output_boundary[-1] + length - 1)
        motion_path = args.output / f"teacher_{trajectory_id:04d}.npz"
        np.savez_compressed(
            motion_path,
            body_names=np.asarray(BODY_NAMES),
            body_pos_w=np.concatenate(output_position),
            body_quat_w=np.concatenate(output_quaternion),
            contact_force_part_mask=np.concatenate(output_contact),
            contact_force_part_order=np.asarray(CONTACT_PARTS),
            joint_pos=np.concatenate(output_qpos),
            joint_names=np.asarray(G1_29DOF_JOINT_ORDER),
            fps=source_motion["fps"],
            boundary_frames=np.asarray(output_boundary, dtype=np.int64),
            robot_asset_json=source_motion["robot_asset_json"],
            generation_json=np.asarray(
                json.dumps(
                    {
                        "schema": "climb00_single_forward_fullbody_teacher_v1",
                        "checkpoint": str(args.checkpoint.resolve()),
                        "ik": False,
                    },
                    sort_keys=True,
                )
            ),
        )
        row = dict(source_row)
        row["motion_file"] = str(motion_path.resolve())
        row["fullbody_qpos"] = True
        output_rows.append(row)
        if (trajectory_id + 1) % 64 == 0:
            print(json.dumps({"generated": trajectory_id + 1, "total": len(report["samples"])}), flush=True)

    np.savez_compressed(args.output / "teacher_events.npz", **events)
    output_report = dict(report)
    output_report["samples"] = output_rows
    output_report["fullbody_generation"] = {
        "schema": "climb00_single_forward_fullbody_teacher_v1",
        "checkpoint": str(args.checkpoint.resolve()),
        "ik": False,
        "maximum_public_seam_m": maximum_public_seam,
        "maximum_q_root_seam_m": maximum_q_root_seam,
        "maximum_q_joint_seam_rad": maximum_q_joint_seam,
        "maximum_proxy_penetration_m": maximum_proxy_penetration,
        "mean_public_fk_consistency_m": fk_consistency_sum / max(fk_consistency_count, 1),
        "actual_boundary_step": {
            "public_position_cm_p95": float(100.0 * np.percentile(public_boundary_position_steps, 95)),
            "public_position_cm_max": float(100.0 * np.max(public_boundary_position_steps)),
            "public_rotation_deg_p95": float(np.percentile(public_boundary_rotation_steps, 95)),
            "public_rotation_deg_max": float(np.max(public_boundary_rotation_steps)),
            "q_joint_rad_p95": float(np.percentile(q_boundary_joint_steps, 95)),
            "q_joint_rad_max": float(np.max(q_boundary_joint_steps)),
        },
    }
    (args.output / "report.json").write_text(json.dumps(output_report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output_report["fullbody_generation"]), flush=True)


if __name__ == "__main__":
    main()
