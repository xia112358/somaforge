"""PyRoki fullbody IK backend for contact-Laplacian task-space motions."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial.transform import Rotation
from somaforge_core.contact_schema import (
    CONTACT_FORCE_PART_BODY_NAMES,
    CONTACT_FORCE_PART_ORDER,
    canonical_contact_part_id,
)
from somaforge_core.robot_assets import canonical_g1_urdf_path
from somaforge_core.robot_assets import encode_robot_asset_json

from .pyroki_trajectory_optimizer import (
    EnvironmentContactAnchors,
    ForceLinearization,
    OrientationTargets,
    WholeTrajectoryConfig,
    solve_whole_trajectory,
)


DEFAULT_ROBOT_URDF = canonical_g1_urdf_path()

TARGET_LINK_GROUPS: dict[str, tuple[str, ...]] = {
    "pelvis": ("pelvis",),
    "torso": ("torso_link",),
    "left_knee": ("left_knee_link",),
    "right_knee": ("right_knee_link",),
    "left_foot": ("left_ankle_roll_link",),
    "right_foot": ("right_ankle_roll_link",),
    "left_heel": ("left_ankle_roll_sphere_1_link", "left_ankle_roll_sphere_2_link"),
    "left_toe": ("left_ankle_roll_sphere_3_link", "left_ankle_roll_sphere_4_link", "left_ankle_roll_sphere_5_link"),
    "right_heel": ("right_ankle_roll_sphere_1_link", "right_ankle_roll_sphere_2_link"),
    "right_toe": ("right_ankle_roll_sphere_3_link", "right_ankle_roll_sphere_4_link", "right_ankle_roll_sphere_5_link"),
    "left_hand": CONTACT_FORCE_PART_BODY_NAMES["LH"],
    "right_hand": CONTACT_FORCE_PART_BODY_NAMES["RH"],
}

TARGET_WEIGHTS: dict[str, float] = {
    "pelvis": 10.0,
    "torso": 4.0,
    "left_knee": 4.0,
    "right_knee": 4.0,
    "left_foot": 8.0,
    "right_foot": 8.0,
    "left_heel": 20.0,
    "left_toe": 20.0,
    "right_heel": 20.0,
    "right_toe": 20.0,
    "left_hand": 5.0,
    "right_hand": 5.0,
}


def _load_npz(path: str | Path) -> dict[str, Any]:
    with np.load(Path(path).expanduser(), allow_pickle=True) as data:
        return {key: data[key] for key in data.files}


def _decode_scalar(value: Any) -> str:
    arr = np.asarray(value, dtype=object)
    raw = arr.item() if arr.ndim == 0 else arr.reshape(-1)[0]
    if isinstance(raw, bytes):
        return raw.decode("utf-8")
    return str(raw)


def _motion_strings(data: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        if key not in data:
            continue
        arr = np.asarray(data[key], dtype=object)
        if arr.ndim == 0:
            raw = arr.item()
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item) for item in parsed]
                except json.JSONDecodeError:
                    return [item.strip() for item in raw.split(",") if item.strip()]
            if isinstance(raw, (list, tuple)):
                return [str(item) for item in raw]
            return [str(raw)]
        return [str(item) for item in arr.reshape(-1).tolist()]
    return []


def _resolve_link_groups(link_names: tuple[str, ...], targets: dict[str, np.ndarray]) -> tuple[list[str], list[np.ndarray], np.ndarray]:
    names: list[str] = []
    groups: list[np.ndarray] = []
    weights: list[float] = []
    lowered = {name.lower(): index for index, name in enumerate(link_names)}
    for target_name, aliases in TARGET_LINK_GROUPS.items():
        if target_name not in targets:
            continue
        resolved: list[int] = []
        for alias in aliases:
            if alias in link_names:
                resolved.append(link_names.index(alias))
            elif alias.lower() in lowered:
                resolved.append(lowered[alias.lower()])
        if not resolved:
            continue
        names.append(target_name)
        groups.append(np.asarray(resolved, dtype=np.int32))
        weights.append(float(TARGET_WEIGHTS[target_name]))
    if not groups:
        raise ValueError("PyRoki IK could not resolve any target links from LTE keypoints")
    return names, groups, np.asarray(weights, dtype=np.float64)


def _resolve_named_link_group(link_names: tuple[str, ...], semantic_name: str) -> np.ndarray:
    aliases = TARGET_LINK_GROUPS.get(str(semantic_name))
    if aliases is None:
        raise ValueError(f"unsupported environment contact semantic name: {semantic_name!r}")
    lowered = {name.lower(): index for index, name in enumerate(link_names)}
    resolved = [
        link_names.index(alias) if alias in link_names else lowered[alias.lower()]
        for alias in aliases
        if alias in link_names or alias.lower() in lowered
    ]
    if not resolved:
        raise ValueError(f"canonical robot has no links for environment contact {semantic_name!r}")
    return np.asarray(resolved, dtype=np.int32)


def _environment_contacts_from_lte(
    lte: dict[str, Any],
    *,
    n_frames: int,
    link_names: tuple[str, ...],
) -> EnvironmentContactAnchors | None:
    prefix = "environment_contact_anchor_"
    required = (
        f"{prefix}ids",
        f"{prefix}semantic_names",
        f"{prefix}start_frames",
        f"{prefix}end_frames",
        f"{prefix}representative_frames",
        f"{prefix}source_position_w",
        f"{prefix}target_position_w",
        f"{prefix}edited",
    )
    present = [key for key in required if key in lte]
    if not present:
        return None
    missing = [key for key in required if key not in lte]
    if missing:
        raise ValueError(f"incomplete environment contact anchor payload; missing={missing}")
    anchor_ids = tuple(_motion_strings(lte, (f"{prefix}ids",)))
    semantic_names = tuple(_motion_strings(lte, (f"{prefix}semantic_names",)))
    contacts = EnvironmentContactAnchors(
        anchor_ids=anchor_ids,
        semantic_names=semantic_names,
        start_frames=np.asarray(lte[f"{prefix}start_frames"], dtype=np.int64),
        end_frames=np.asarray(lte[f"{prefix}end_frames"], dtype=np.int64),
        representative_frames=np.asarray(lte[f"{prefix}representative_frames"], dtype=np.int64),
        source_position_w=np.asarray(lte[f"{prefix}source_position_w"], dtype=np.float64),
        target_position_w=np.asarray(lte[f"{prefix}target_position_w"], dtype=np.float64),
        edited=np.asarray(lte[f"{prefix}edited"], dtype=bool),
        link_groups=[_resolve_named_link_group(link_names, name) for name in semantic_names],
    )
    contacts.validate(frames=n_frames)
    return contacts


def _source_motion_from_lte(lte: dict[str, Any], explicit: str | Path | None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser()
    if "source_demo" not in lte:
        raise ValueError("LTE keypoint file has no source_demo; pass --source-motion")
    return Path(_decode_scalar(lte["source_demo"])).expanduser()


def _source_qpos(source_motion: dict[str, Any], n_frames: int, actuated_names: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if "joint_pos" not in source_motion:
        raise ValueError("source motion must contain joint_pos for PyRoki IK warm start")
    raw = np.asarray(source_motion["joint_pos"], dtype=np.float64)
    if raw.ndim != 2:
        raise ValueError(f"source joint_pos must have shape [T,Q], got {raw.shape}")
    actuated_count = len(actuated_names)
    count = min(n_frames, raw.shape[0])
    if raw.shape[1] >= 7 + actuated_count:
        root = raw[:count, :7].copy()
        cfg = raw[:count, 7 : 7 + actuated_count].copy()
    elif raw.shape[1] == actuated_count:
        root = np.zeros((count, 7), dtype=np.float64)
        root[:, 3] = 1.0
        cfg = raw[:count, :actuated_count].copy()
    else:
        raise ValueError(
            f"source joint_pos has {raw.shape[1]} columns; expected {actuated_count} or at least {7 + actuated_count}"
        )
    names = _motion_strings(source_motion, ("joint_names", "dof_names", "joint_name", "dof_name"))
    if names:
        if len(names) != actuated_count:
            raise ValueError(f"source joint_names has {len(names)} entries; expected {actuated_count}")
        missing = [name for name in actuated_names if name not in names]
        if missing:
            raise ValueError(f"source motion is missing PyRoki joints: {missing}")
        cfg = cfg[:, [names.index(name) for name in actuated_names]]
    return root, cfg, names


def _quat_mul_wxyz(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aw, ax, ay, az = np.moveaxis(np.asarray(a, dtype=np.float64), -1, 0)
    bw, bx, by, bz = np.moveaxis(np.asarray(b, dtype=np.float64), -1, 0)
    return np.stack(
        [
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ],
        axis=-1,
    )


def _world_body_poses(root_qpos: np.ndarray, link_tf_base: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    root = np.asarray(root_qpos, dtype=np.float64)
    transforms = np.asarray(link_tf_base, dtype=np.float64)
    root_rotation = _quat_wxyz_to_rotation(root[3:7])
    position_w = root_rotation.apply(transforms[:, 4:7]) + root[:3]
    quat_w = _quat_mul_wxyz(np.broadcast_to(root[3:7], transforms[:, :4].shape), transforms[:, :4])
    quat_w /= np.maximum(np.linalg.norm(quat_w, axis=-1, keepdims=True), 1.0e-12)
    return position_w, quat_w


def _world_body_poses_batch(root_qpos: np.ndarray, link_tf_base: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    root = np.asarray(root_qpos, dtype=np.float64)
    transforms = np.asarray(link_tf_base, dtype=np.float64)
    root_xyzw = root[:, [4, 5, 6, 3]]
    body_count = transforms.shape[1]
    root_rotation = Rotation.from_quat(np.repeat(root_xyzw, body_count, axis=0))
    rotated = root_rotation.apply(transforms[..., 4:7].reshape(-1, 3)).reshape(root.shape[0], body_count, 3)
    position_w = rotated + root[:, None, :3]
    quat_w = _quat_mul_wxyz(root[:, None, 3:7], transforms[..., :4])
    quat_w /= np.maximum(np.linalg.norm(quat_w, axis=-1, keepdims=True), 1.0e-12)
    return position_w, quat_w


def _fps_from_motion(source_motion: dict[str, Any]) -> float:
    if "fps" in source_motion:
        return float(np.asarray(source_motion["fps"]).reshape(-1)[0])
    if "dt" in source_motion:
        dt = float(np.asarray(source_motion["dt"]).reshape(-1)[0])
        if dt > 0.0:
            return 1.0 / dt
    return 50.0


def _linear_velocity(qpos: np.ndarray, fps: float) -> np.ndarray:
    if qpos.shape[0] <= 1:
        return np.zeros_like(qpos)
    dt = 1.0 / float(fps)
    vel = np.zeros_like(qpos, dtype=np.float64)
    vel[1:-1] = (qpos[2:] - qpos[:-2]) / (2.0 * dt)
    vel[0] = (qpos[1] - qpos[0]) / dt
    vel[-1] = (qpos[-1] - qpos[-2]) / dt
    return vel


def _quat_wxyz_to_rotation(quat: np.ndarray) -> Rotation:
    q = np.asarray(quat, dtype=np.float64).reshape(4)
    norm = np.linalg.norm(q)
    if norm <= 1.0e-12:
        q = np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    else:
        q = q / norm
    return Rotation.from_quat([q[1], q[2], q[3], q[0]])


def _resolve_force_link_groups(link_names: tuple[str, ...]) -> list[np.ndarray]:
    groups: list[np.ndarray] = []
    for part_id in CONTACT_FORCE_PART_ORDER:
        indices = [link_names.index(name) for name in CONTACT_FORCE_PART_BODY_NAMES[part_id] if name in link_names]
        if not indices:
            raise ValueError(f"canonical robot is missing the {part_id} contact links")
        groups.append(np.asarray(indices, dtype=np.int32))
    return groups


def _source_part_indices(source_motion: dict[str, Any], width: int) -> list[int]:
    raw_order = _motion_strings(
        source_motion,
        ("contact_force_part_order", "contact_part_order", "part_order", "contact_part_names"),
    )
    if not raw_order:
        if width != len(CONTACT_FORCE_PART_ORDER):
            raise ValueError(f"contact force has {width} parts but no part order")
        return list(range(width))
    normalized = [canonical_contact_part_id(item) for item in raw_order]
    missing = [part for part in CONTACT_FORCE_PART_ORDER if part not in normalized]
    if missing:
        raise ValueError(f"source contact force is missing canonical parts: {missing}")
    return [normalized.index(part) for part in CONTACT_FORCE_PART_ORDER]


def _group_positions_w(
    *,
    robot: Any,
    root_qpos: np.ndarray,
    joint_cfg: np.ndarray,
    groups: list[np.ndarray],
) -> np.ndarray:
    import jax.numpy as jnp

    fk = np.asarray(robot.forward_kinematics(jnp.asarray(joint_cfg)), dtype=np.float64)
    positions = np.empty((joint_cfg.shape[0], len(groups), 3), dtype=np.float64)
    for frame in range(joint_cfg.shape[0]):
        root_rotation = _quat_wxyz_to_rotation(root_qpos[frame, 3:7])
        for part, group in enumerate(groups):
            local = np.mean(fk[frame, group, 4:7], axis=0)
            positions[frame, part] = root_rotation.apply(local) + root_qpos[frame, :3]
    return positions


def _force_linearization_from_source(
    *,
    source_motion: dict[str, Any],
    robot: Any,
    root_qpos: np.ndarray,
    joint_cfg: np.ndarray,
    force_groups: list[np.ndarray],
) -> ForceLinearization:
    frames = joint_cfg.shape[0]
    positions = _group_positions_w(
        robot=robot,
        root_qpos=root_qpos,
        joint_cfg=joint_cfg,
        groups=force_groups,
    )
    force_key = "contact_force_part_w" if "contact_force_part_w" in source_motion else "contact_force_part_force_w"
    if force_key not in source_motion:
        zeros = np.zeros_like(positions)
        normals = np.zeros_like(positions)
        normals[..., 2] = 1.0
        return ForceLinearization(
            target_force_w=zeros,
            actual_force_w=zeros,
            contact_mask=np.zeros(positions.shape[:2], dtype=bool),
            contact_normals_w=normals,
            reference_link_position_w=positions,
            target_normal_displacement_m=np.zeros(positions.shape[:2], dtype=np.float64),
        )

    raw_force = np.asarray(source_motion[force_key], dtype=np.float64)[:frames]
    if raw_force.ndim != 3 or raw_force.shape[2] != 3:
        raise ValueError(f"{force_key} must be [T,P,3], got {raw_force.shape}")
    indices = _source_part_indices(source_motion, raw_force.shape[1])
    force = raw_force[:, indices]
    raw_mask = np.asarray(
        source_motion.get("contact_force_part_mask", source_motion.get("contact_part_mask", np.linalg.norm(raw_force, axis=2) > 0.0)),
        dtype=bool,
    )[:frames, indices]
    if "contact_force_part_normal_w" in source_motion:
        normals = np.asarray(source_motion["contact_force_part_normal_w"], dtype=np.float64)[:frames, indices]
    else:
        normals = np.zeros_like(force)
    normal_magnitude = np.linalg.norm(normals, axis=2, keepdims=True)
    force_magnitude = np.linalg.norm(force, axis=2, keepdims=True)
    force_direction = force / np.maximum(force_magnitude, 1.0e-8)
    fallback = np.zeros_like(force)
    fallback[..., 2] = 1.0
    normals = np.where(
        normal_magnitude > 1.0e-8,
        normals / np.maximum(normal_magnitude, 1.0e-8),
        np.where(force_magnitude > 1.0e-8, force_direction, fallback),
    )
    return ForceLinearization(
        target_force_w=force,
        actual_force_w=force,
        contact_mask=raw_mask,
        contact_normals_w=normals,
        reference_link_position_w=positions,
        target_normal_displacement_m=np.zeros(positions.shape[:2], dtype=np.float64),
    )


def solve_pyroki_fullbody_ik(
    *,
    lte_path: str | Path,
    output_path: str | Path,
    robot_urdf: str | Path = DEFAULT_ROBOT_URDF,
    source_motion_path: str | Path | None = None,
    max_nfev: int = 25,
    q_prior_weight: float = 0.25,
    q_smooth_weight: float = 0.5,
    foot_orientation_weight: float = 20.0,
    contact_foot_orientation_weight: float = 80.0,
    foot_toe_weight: float = 20.0,
    contact_foot_toe_weight: float = 120.0,
    force_linearization_override: ForceLinearization | None = None,
    whole_trajectory_config: WholeTrajectoryConfig | None = None,
) -> Path:
    import jax.numpy as jnp
    import pyroki
    import yourdfpy

    lte = _load_npz(lte_path)
    targets = {name: np.asarray(lte[name], dtype=np.float64) for name in TARGET_LINK_GROUPS if name in lte}
    if "root" in lte and "pelvis" not in targets:
        targets["pelvis"] = np.asarray(lte["root"], dtype=np.float64)
    if not targets:
        raise ValueError(f"{lte_path} has no supported PyRoki IK keypoints")
    n_frames = min(arr.shape[0] for arr in targets.values())

    robot_path = Path(robot_urdf).expanduser()
    if not robot_path.exists():
        raise FileNotFoundError(f"robot URDF not found for PyRoki IK: {robot_path}")
    urdf = yourdfpy.URDF.load(str(robot_path), load_meshes=False)
    robot = pyroki.Robot.from_urdf(urdf)
    actuated_count = int(robot.joints.num_actuated_joints)
    target_names, link_groups, target_weights = _resolve_link_groups(robot.links.names, targets)

    source_path = _source_motion_from_lte(lte, source_motion_path)
    source_motion = _load_npz(source_path)
    actuated_names = tuple(robot.joints.actuated_names)
    root_source, cfg_source, source_joint_names = _source_qpos(source_motion, n_frames, actuated_names)
    n_frames = min(n_frames, cfg_source.shape[0])
    root_source = root_source[:n_frames]
    cfg_source = cfg_source[:n_frames]

    lower = np.asarray(robot.joints.lower_limits, dtype=np.float64)
    upper = np.asarray(robot.joints.upper_limits, dtype=np.float64)
    finite = np.isfinite(lower) & np.isfinite(upper)
    lower = np.where(finite, lower, -np.pi)
    upper = np.where(finite, upper, np.pi)
    cfg_source = np.clip(cfg_source, lower, upper)

    frame_target_weights = np.broadcast_to(target_weights, (n_frames, len(target_names))).copy()
    for target_index, target_name in enumerate(target_names):
        if target_name not in {"left_heel", "left_toe", "right_heel", "right_toe"}:
            continue
        contact = np.asarray(lte.get(f"contact_weight_{target_name}", np.zeros(n_frames)), dtype=np.float64)[:n_frames]
        frame_target_weights[:, target_index] = np.where(contact > 0.0, contact_foot_toe_weight, foot_toe_weight)

    link_name_to_index = {name: index for index, name in enumerate(robot.links.names)}
    orientation_specs: list[tuple[int, np.ndarray, np.ndarray]] = []
    for side in ("left", "right"):
        key = f"orientation_target_{side}_foot"
        link_name = f"{side}_ankle_roll_link"
        if key not in lte or link_name not in link_name_to_index:
            continue
        target_orientation = np.asarray(lte[key], dtype=np.float64)[:n_frames]
        contact = np.maximum(
            np.asarray(lte.get(f"contact_weight_{side}_heel", np.zeros(n_frames)), dtype=np.float64)[:n_frames],
            np.asarray(lte.get(f"contact_weight_{side}_toe", np.zeros(n_frames)), dtype=np.float64)[:n_frames],
        )
        orientation_weight = np.where(contact > 0.0, contact_foot_orientation_weight, foot_orientation_weight)
        orientation_specs.append((link_name_to_index[link_name], target_orientation, orientation_weight))

    orientation_targets = OrientationTargets(
        link_indices=np.asarray([item[0] for item in orientation_specs], dtype=np.int32),
        quat_wxyz=(
            np.stack([item[1] for item in orientation_specs], axis=1)
            if orientation_specs
            else np.zeros((n_frames, 0, 4), dtype=np.float64)
        ),
        weights=(
            np.stack([item[2] for item in orientation_specs], axis=1)
            if orientation_specs
            else np.zeros((n_frames, 0), dtype=np.float64)
        ),
    )
    force_groups = _resolve_force_link_groups(tuple(robot.links.names))
    source_force_linearization = _force_linearization_from_source(
        source_motion=source_motion,
        robot=robot,
        root_qpos=root_source,
        joint_cfg=cfg_source,
        force_groups=force_groups,
    )
    force_linearization = (
        replace(
            force_linearization_override,
            reference_link_position_w=source_force_linearization.reference_link_position_w,
        )
        if force_linearization_override is not None
        else source_force_linearization
    )
    environment_contacts = _environment_contacts_from_lte(
        lte,
        n_frames=n_frames,
        link_names=tuple(robot.links.names),
    )
    target_position_w = np.stack([targets[name][:n_frames] for name in target_names], axis=1)
    object_points = None
    for key in ("interaction_object_points_w", "surface_object_points_w", "object_points_w"):
        if key in lte:
            candidate = np.asarray(lte[key], dtype=np.float64)
            object_points = candidate[0] if candidate.ndim == 3 else candidate
            break
    solution = solve_whole_trajectory(
        robot=robot,
        root_qpos_init=root_source,
        joint_cfg_init=cfg_source,
        target_position_w=target_position_w,
        target_link_groups=link_groups,
        target_weights=frame_target_weights,
        force_link_groups=force_groups,
        force_linearization=force_linearization,
        environment_contacts=environment_contacts,
        orientation_targets=orientation_targets,
        object_points_w=object_points,
        config=whole_trajectory_config
        or WholeTrajectoryConfig(
            pose_prior_weight=max(float(q_prior_weight), 0.0),
            temporal_laplacian_weight=max(float(q_smooth_weight), 1.0e-8),
            max_iterations=int(max_nfev),
        ),
    )
    root_source = solution.root_qpos
    out_cfg = solution.joint_cfg
    qpos = np.concatenate([root_source, out_cfg], axis=1)
    fps = _fps_from_motion(source_motion)
    qvel = _linear_velocity(qpos, fps)
    body_names = _motion_strings(source_motion, ("body_names", "body_name"))
    missing_bodies = [name for name in body_names if name not in link_name_to_index]
    if not body_names or missing_bodies:
        raise ValueError(f"source body_names cannot be represented by PyRoki FK; missing={missing_bodies}")
    body_link_indices = [link_name_to_index[name] for name in body_names]
    fk_base = np.asarray(robot.forward_kinematics(jnp.asarray(out_cfg)), dtype=np.float64)[:, body_link_indices]
    body_pos_w, body_quat_w = _world_body_poses_batch(root_source, fk_base)
    output = Path(output_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output,
        joint_pos=qpos.astype(np.float32),
        joint_vel=qvel.astype(np.float32),
        joint_names=np.asarray(tuple(robot.joints.actuated_names)),
        body_pos_w=body_pos_w.astype(np.float32),
        body_quat_w=body_quat_w.astype(np.float32),
        body_names=np.asarray(body_names),
        source_joint_names=np.asarray(source_joint_names),
        is_qpos=np.asarray(True),
        ik_backend=np.asarray("pyroki_internal"),
        ik_solver=np.asarray("pyroki_jaxls_whole_trajectory"),
        ik_objective_families=np.asarray(solution.metadata["objective_families"]),
        ik_metadata_json=np.asarray(json.dumps(solution.metadata, sort_keys=True)),
        physics_retarget_force_reference_position_w=solution.force_reference_position_w.astype(np.float32),
        physics_retarget_force_solved_position_w=solution.force_solved_position_w.astype(np.float32),
        robot_urdf=np.asarray(str(robot_path)),
        robot_asset_json=np.asarray(encode_robot_asset_json()),
        target_names=np.asarray(target_names),
        source_motion=np.asarray(str(source_path)),
        fps=np.asarray(fps),
    )
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Solve fullbody IK for motion_edit LTE keypoints with PyRoki.")
    parser.add_argument("--lte", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--robot-urdf", default=str(DEFAULT_ROBOT_URDF))
    parser.add_argument("--source-motion", default=None)
    parser.add_argument("--max-nfev", type=int, default=25)
    parser.add_argument("--q-prior-weight", type=float, default=0.25)
    parser.add_argument("--q-smooth-weight", type=float, default=0.5)
    parser.add_argument("--foot-orientation-weight", type=float, default=20.0)
    parser.add_argument("--contact-foot-orientation-weight", type=float, default=80.0)
    parser.add_argument("--foot-toe-weight", type=float, default=20.0)
    parser.add_argument("--contact-foot-toe-weight", type=float, default=120.0)
    args = parser.parse_args(argv)
    solve_pyroki_fullbody_ik(
        lte_path=args.lte,
        output_path=args.out,
        robot_urdf=args.robot_urdf,
        source_motion_path=args.source_motion,
        max_nfev=args.max_nfev,
        q_prior_weight=args.q_prior_weight,
        q_smooth_weight=args.q_smooth_weight,
        foot_orientation_weight=args.foot_orientation_weight,
        contact_foot_orientation_weight=args.contact_foot_orientation_weight,
        foot_toe_weight=args.foot_toe_weight,
        contact_foot_toe_weight=args.contact_foot_toe_weight,
    )


if __name__ == "__main__":
    main()
