"""PyRoki trajectory IK for contact-aware task-space motions.

This backend is deliberately kinematic. Newton/MJWarp remains the authority for
collision and contact validation. The output is a PyRoki-FK-consistent preview
trajectory that must be Newton-canonicalized before training use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from somaforge_core.contact_schema import (
    CONTACT_FORCE_PART_BODY_NAMES,
    CONTACT_FORCE_PART_ORDER,
    canonical_contact_part_id,
)
from somaforge_core.robot_assets import canonical_g1_urdf_path

from motion_edit.generation.pyroki_taskspace import (
    CompiledPyrokiTaskspace,
    SEMANTIC_DEFAULT_WEIGHTS,
    SEMANTIC_LINK_ALIASES,
    compile_pyroki_taskspace,
    holosoma_body_velocities,
    holosoma_joint_velocities,
    normalize_quat_wxyz,
    quat_apply_wxyz,
    resolve_link_index,
    world_body_poses_from_pyroki_fk,
)
from motion_edit.generation.newton_collision import DirectNewtonCollisionScene
from motion_edit.generation.pyroki_trajectory_optimizer import (
    EnvironmentContactAnchors,
    ForceLinearization,
)
from motion_edit.generation.taskspace_spec import ContactAwareTaskspaceMotion


DEFAULT_ROBOT_URDF = canonical_g1_urdf_path()
COLLISION_REFERENCE_CACHE_SCHEMA = "newton_collision_reference_v1"
TARGET_LINK_ALIASES = SEMANTIC_LINK_ALIASES
TARGET_WEIGHTS = SEMANTIC_DEFAULT_WEIGHTS
_PYROKI_ROBOT_CACHE: dict[
    tuple[str, int, int],
    tuple[Any, tuple[str, ...], tuple[str, ...], int],
] = {}
_NEWTON_COLLISION_SCENE_CACHE: dict[
    tuple[str | None, str],
    DirectNewtonCollisionScene,
] = {}
SOURCE_FOOT_ORIENTATION_LINKS = (
    ("left_ankle_roll_link", "left_ankle_roll_sphere_1_link"),
    ("right_ankle_roll_link", "right_ankle_roll_sphere_1_link"),
)

# Compatibility surface for the whole-trajectory workflow that predates the
# contact-aware task-space solver. The production v2 solve below continues to
# use SEMANTIC_LINK_ALIASES and rigid patch constraints.
TARGET_LINK_GROUPS: dict[str, tuple[str, ...]] = {
    "pelvis": ("pelvis",),
    "torso": ("torso_link",),
    "left_knee": ("left_knee_link",),
    "right_knee": ("right_knee_link",),
    "left_foot": ("left_ankle_roll_link",),
    "right_foot": ("right_ankle_roll_link",),
    "left_heel": (
        "left_ankle_roll_sphere_1_link",
        "left_ankle_roll_sphere_2_link",
    ),
    "left_toe": (
        "left_ankle_roll_sphere_3_link",
        "left_ankle_roll_sphere_4_link",
        "left_ankle_roll_sphere_5_link",
    ),
    "right_heel": (
        "right_ankle_roll_sphere_1_link",
        "right_ankle_roll_sphere_2_link",
    ),
    "right_toe": (
        "right_ankle_roll_sphere_3_link",
        "right_ankle_roll_sphere_4_link",
        "right_ankle_roll_sphere_5_link",
    ),
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


def self_collision_barrier_residual(
    signed_distance: Any,
    sqrt_weight: Any,
    *,
    array_module: Any = np,
) -> Any:
    """One-sided zero-clearance residual for unfiltered robot body pairs."""

    return (
        array_module.minimum(signed_distance, 0.0)
        * sqrt_weight
    )


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


def _resolve_named_link_group(
    link_names: tuple[str, ...],
    semantic_name: str,
) -> np.ndarray:
    aliases = TARGET_LINK_GROUPS.get(str(semantic_name))
    if aliases is None:
        raise ValueError(
            f"unsupported environment contact semantic name: {semantic_name!r}"
        )
    lowered = {name.lower(): index for index, name in enumerate(link_names)}
    resolved = [
        link_names.index(alias)
        if alias in link_names
        else lowered[alias.lower()]
        for alias in aliases
        if alias in link_names or alias.lower() in lowered
    ]
    if not resolved:
        raise ValueError(
            f"canonical robot has no links for environment contact "
            f"{semantic_name!r}"
        )
    return np.asarray(resolved, dtype=np.int32)


def _resolve_link_groups(
    link_names: tuple[str, ...],
    targets: dict[str, np.ndarray],
) -> tuple[list[str], list[np.ndarray], np.ndarray]:
    names: list[str] = []
    groups: list[np.ndarray] = []
    weights: list[float] = []
    for target_name in TARGET_LINK_GROUPS:
        if target_name not in targets:
            continue
        try:
            group = _resolve_named_link_group(link_names, target_name)
        except ValueError:
            continue
        names.append(target_name)
        groups.append(group)
        weights.append(float(TARGET_WEIGHTS[target_name]))
    if not groups:
        raise ValueError(
            "PyRoki IK could not resolve any target links from LTE keypoints"
        )
    return names, groups, np.asarray(weights, dtype=np.float64)


def _environment_contacts_from_lte(
    lte: dict[str, Any],
    *,
    n_frames: int,
    link_names: tuple[str, ...],
) -> EnvironmentContactAnchors | None:
    """Decode legacy external-surface anchors without changing v2 patches."""

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
        raise ValueError(
            f"incomplete environment contact anchor payload; missing={missing}"
        )
    anchor_ids = tuple(_motion_strings(lte, (f"{prefix}ids",)))
    semantic_names = tuple(
        _motion_strings(lte, (f"{prefix}semantic_names",))
    )
    start_frames = np.asarray(lte[f"{prefix}start_frames"], dtype=np.int64)
    end_frames = np.asarray(lte[f"{prefix}end_frames"], dtype=np.int64)
    source_position_w = np.asarray(
        lte[f"{prefix}source_position_w"],
        dtype=np.float64,
    )
    target_position_w = np.asarray(
        lte[f"{prefix}target_position_w"],
        dtype=np.float64,
    )
    edited = np.asarray(lte[f"{prefix}edited"], dtype=bool)
    serialized_source = lte.get(f"{prefix}source_trajectory_w")
    serialized_target = lte.get(f"{prefix}target_trajectory_w")
    if serialized_source is not None and serialized_target is not None:
        source_trajectory = np.asarray(serialized_source, dtype=np.float64)
        target_trajectory = np.asarray(serialized_target, dtype=np.float64)
    else:
        source_items: list[np.ndarray] = []
        target_items: list[np.ndarray] = []
        for index, semantic_name in enumerate(semantic_names):
            candidate = np.asarray(
                lte.get(semantic_name, np.empty((0, 3))),
                dtype=np.float64,
            )
            if (
                candidate.ndim == 2
                and candidate.shape[0] >= n_frames
                and candidate.shape[1] == 3
            ):
                target_item = candidate[:n_frames].copy()
                source_item = target_item.copy()
                if edited[index]:
                    delta = target_position_w[index] - source_position_w[index]
                    source_item[
                        start_frames[index] : end_frames[index]
                    ] -= delta[None, :]
            else:
                source_item = np.broadcast_to(
                    source_position_w[index],
                    (n_frames, 3),
                ).copy()
                target_item = np.broadcast_to(
                    target_position_w[index],
                    (n_frames, 3),
                ).copy()
            source_items.append(source_item)
            target_items.append(target_item)
        source_trajectory = np.stack(source_items)
        target_trajectory = np.stack(target_items)
    contacts = EnvironmentContactAnchors(
        anchor_ids=anchor_ids,
        semantic_names=semantic_names,
        start_frames=start_frames,
        end_frames=end_frames,
        representative_frames=np.asarray(
            lte[f"{prefix}representative_frames"],
            dtype=np.int64,
        ),
        source_position_w=source_position_w,
        target_position_w=target_position_w,
        edited=edited,
        link_groups=[
            _resolve_named_link_group(link_names, name)
            for name in semantic_names
        ],
        source_trajectory_w=source_trajectory,
        target_trajectory_w=target_trajectory,
        contact_source_trajectory_w=(
            None
            if f"{prefix}contact_source_trajectory_w" not in lte
            else np.asarray(
                lte[f"{prefix}contact_source_trajectory_w"],
                dtype=np.float64,
            )
        ),
        contact_target_trajectory_w=(
            None
            if f"{prefix}contact_target_trajectory_w" not in lte
            else np.asarray(
                lte[f"{prefix}contact_target_trajectory_w"],
                dtype=np.float64,
            )
        ),
        force_trajectory_w=(
            None
            if f"{prefix}force_trajectory_w" not in lte
            else np.asarray(
                lte[f"{prefix}force_trajectory_w"],
                dtype=np.float64,
            )
        ),
        contact_mask=(
            None
            if f"{prefix}contact_mask" not in lte
            else np.asarray(lte[f"{prefix}contact_mask"], dtype=bool)
        ),
    )
    contacts.validate(frames=n_frames)
    return contacts


def _source_motion_from_lte(lte: dict[str, Any], explicit: str | Path | None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser()
    if "source_demo" not in lte:
        raise ValueError("legacy LTE keypoint file has no source_demo; pass --source-motion")
    return Path(_decode_scalar(lte["source_demo"])).expanduser()


def _source_qpos_from_array(raw_value: Any, n_frames: int, actuated_count: int) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(raw_value, dtype=np.float64)
    if raw.ndim != 2:
        raise ValueError(f"source joint_pos must have shape [T,Q], got {raw.shape}")
    count = min(int(n_frames), raw.shape[0])
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
    root[:, 3:7] = normalize_quat_wxyz(root[:, 3:7])
    return root, cfg


def _align_source_cfg(
    cfg: np.ndarray,
    source_joint_names: list[str],
    robot_joint_names: tuple[str, ...],
) -> np.ndarray:
    if not source_joint_names:
        return cfg
    if source_joint_names == list(robot_joint_names):
        return cfg
    if all(name in source_joint_names for name in robot_joint_names):
        indices = [source_joint_names.index(name) for name in robot_joint_names]
        return cfg[:, indices]
    missing = [name for name in robot_joint_names if name not in source_joint_names]
    raise ValueError(f"source motion is missing PyRoki actuated joints: {missing}")


def _source_qpos(
    source_motion: dict[str, Any],
    n_frames: int,
    actuated_names: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if "joint_pos" not in source_motion:
        raise ValueError(
            "source motion must contain joint_pos for PyRoki IK warm start"
        )
    root, cfg = _source_qpos_from_array(
        source_motion["joint_pos"],
        n_frames,
        len(actuated_names),
    )
    names = _motion_strings(
        source_motion,
        ("joint_names", "dof_names", "joint_name", "dof_name"),
    )
    return root, _align_source_cfg(cfg, names, actuated_names), names


def _world_body_poses(
    root_qpos: np.ndarray,
    link_tf_base: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    root = np.asarray(root_qpos, dtype=np.float64).reshape(1, 7)
    transforms = np.asarray(link_tf_base, dtype=np.float64)[None, ...]
    position_w, quaternion_w = world_body_poses_from_pyroki_fk(
        root,
        transforms,
    )
    return position_w[0].astype(np.float64), quaternion_w[0].astype(np.float64)


def _fps_from_motion(source_motion: dict[str, Any]) -> float:
    if "fps" in source_motion:
        return float(np.asarray(source_motion["fps"]).reshape(-1)[0])
    if "dt" in source_motion:
        dt = float(np.asarray(source_motion["dt"]).reshape(-1)[0])
        if dt > 0.0:
            return 1.0 / dt
    return 50.0


def _quat_wxyz_to_rotation(quat: np.ndarray) -> Rotation:
    q = normalize_quat_wxyz(np.asarray(quat, dtype=np.float64).reshape(4))
    return Rotation.from_quat([q[1], q[2], q[3], q[0]])


def _resolve_force_link_groups(
    link_names: tuple[str, ...],
) -> list[np.ndarray]:
    groups: list[np.ndarray] = []
    for part_id in CONTACT_FORCE_PART_ORDER:
        indices = [
            link_names.index(name)
            for name in CONTACT_FORCE_PART_BODY_NAMES[part_id]
            if name in link_names
        ]
        if not indices:
            raise ValueError(
                f"canonical robot is missing the {part_id} contact links"
            )
        groups.append(np.asarray(indices, dtype=np.int32))
    return groups


def _source_part_indices(
    source_motion: dict[str, Any],
    width: int,
) -> list[int]:
    raw_order = _motion_strings(
        source_motion,
        (
            "contact_force_part_order",
            "contact_part_order",
            "part_order",
            "contact_part_names",
        ),
    )
    if not raw_order:
        if width != len(CONTACT_FORCE_PART_ORDER):
            raise ValueError(f"contact force has {width} parts but no part order")
        return list(range(width))
    normalized = [canonical_contact_part_id(item) for item in raw_order]
    missing = [
        part for part in CONTACT_FORCE_PART_ORDER if part not in normalized
    ]
    if missing:
        raise ValueError(
            f"source contact force is missing canonical parts: {missing}"
        )
    return [normalized.index(part) for part in CONTACT_FORCE_PART_ORDER]


def _group_positions_w(
    *,
    robot: Any,
    root_qpos: np.ndarray,
    joint_cfg: np.ndarray,
    groups: list[np.ndarray],
) -> np.ndarray:
    import jax.numpy as jnp

    fk = np.asarray(
        robot.forward_kinematics(jnp.asarray(joint_cfg)),
        dtype=np.float64,
    )
    positions = np.empty(
        (joint_cfg.shape[0], len(groups), 3),
        dtype=np.float64,
    )
    for frame in range(joint_cfg.shape[0]):
        root_rotation = _quat_wxyz_to_rotation(root_qpos[frame, 3:7])
        for part, group in enumerate(groups):
            local = np.mean(fk[frame, group, 4:7], axis=0)
            positions[frame, part] = (
                root_rotation.apply(local) + root_qpos[frame, :3]
            )
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
    force_key = (
        "contact_force_part_w"
        if "contact_force_part_w" in source_motion
        else "contact_force_part_force_w"
    )
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
            target_normal_displacement_m=np.zeros(
                positions.shape[:2],
                dtype=np.float64,
            ),
        )
    raw_force = np.asarray(
        source_motion[force_key],
        dtype=np.float64,
    )[:frames]
    if raw_force.ndim != 3 or raw_force.shape[2] != 3:
        raise ValueError(f"{force_key} must be [T,P,3], got {raw_force.shape}")
    indices = _source_part_indices(source_motion, raw_force.shape[1])
    force = raw_force[:, indices]
    raw_mask = np.asarray(
        source_motion.get(
            "contact_force_part_mask",
            source_motion.get(
                "contact_part_mask",
                np.linalg.norm(raw_force, axis=2) > 0.0,
            ),
        ),
        dtype=bool,
    )[:frames, indices]
    if "contact_force_part_normal_w" in source_motion:
        normals = np.asarray(
            source_motion["contact_force_part_normal_w"],
            dtype=np.float64,
        )[:frames, indices]
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
        target_normal_displacement_m=np.zeros(
            positions.shape[:2],
            dtype=np.float64,
        ),
    )


def _legacy_compiled_taskspace(lte: dict[str, Any], link_names: tuple[str, ...]) -> CompiledPyrokiTaskspace:
    targets = {name: np.asarray(lte[name], dtype=np.float64) for name in TARGET_LINK_ALIASES if name in lte}
    if "root" in lte and "pelvis" not in targets:
        targets["pelvis"] = np.asarray(lte["root"], dtype=np.float64)
    if not targets:
        raise ValueError("legacy LTE input has no supported PyRoki keypoints")
    n_frames = min(value.shape[0] for value in targets.values())
    names: list[str] = []
    indices: list[int] = []
    values: list[np.ndarray] = []
    unresolved: list[str] = []
    for name, target in targets.items():
        link_index = resolve_link_index(link_names, name, TARGET_LINK_ALIASES.get(name, (name,)))
        if link_index is None:
            unresolved.append(name)
            continue
        names.append(name)
        indices.append(link_index)
        values.append(target[:n_frames])
    if not indices:
        raise ValueError("PyRoki IK could not resolve any legacy target links")
    semantic_targets = np.stack(values, axis=1)
    semantic_weights = np.broadcast_to(
        np.asarray([TARGET_WEIGHTS.get(name, 1.0) for name in names], dtype=np.float64)[None, :],
        (n_frames, len(names)),
    ).copy()
    compiled = CompiledPyrokiTaskspace(
        semantic_names=tuple(names),
        semantic_link_indices=np.asarray(indices, dtype=np.int32),
        semantic_targets_w=semantic_targets,
        semantic_weights=semantic_weights,
        contact_link_indices=np.zeros((n_frames, 1), dtype=np.int32),
        contact_points_local=np.zeros((n_frames, 1, 3), dtype=np.float64),
        contact_targets_w=np.zeros((n_frames, 1, 3), dtype=np.float64),
        contact_weights=np.zeros((n_frames, 1), dtype=np.float64),
        unresolved_semantics=tuple(unresolved),
        unresolved_contacts=(),
    )
    compiled.validate()
    return compiled


def _input_problem(
    payload: dict[str, Any],
    *,
    link_names: tuple[str, ...],
    actuated_count: int,
    robot_joint_names: tuple[str, ...],
    source_motion_path: str | Path | None,
    edited_contact_weight: float,
    fixed_contact_weight: float,
) -> tuple[
    CompiledPyrokiTaskspace,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
    list[str],
    str | None,
    str,
]:
    if "contact_aware_taskspace_json" in payload:
        spec = ContactAwareTaskspaceMotion.from_arrays(payload)
        compiled = compile_pyroki_taskspace(
            spec,
            link_names,
            edited_contact_weight=edited_contact_weight,
            fixed_contact_weight=fixed_contact_weight,
        )
        root_source, cfg_source = _source_qpos_from_array(spec.source_qpos, spec.frame_count, actuated_count)
        source_names: list[str] = []
        source_path: str | None = None
        if source_motion_path is not None:
            source_path_obj = Path(source_motion_path).expanduser()
            source_motion = _load_npz(source_path_obj)
            source_names = _motion_strings(source_motion, ("joint_names", "dof_names", "joint_name", "dof_name"))
            source_path = str(source_path_obj)
        cfg_source = _align_source_cfg(cfg_source, source_names, robot_joint_names)
        source_reference = np.asarray(spec.source_reference_weights, dtype=np.float64)[:, 7 : 7 + actuated_count]
        boundary = np.asarray(spec.boundary_weights, dtype=np.float64)
        return (
            compiled,
            root_source,
            cfg_source,
            source_reference,
            boundary,
            float(spec.fps),
            source_names,
            source_path,
            "contact_aware_taskspace_motion_v1",
        )

    compiled = _legacy_compiled_taskspace(payload, link_names)
    source_path_obj = _source_motion_from_lte(payload, source_motion_path)
    source_motion = _load_npz(source_path_obj)
    source_names = _motion_strings(source_motion, ("joint_names", "dof_names", "joint_name", "dof_name"))
    root_source, cfg_source = _source_qpos_from_array(source_motion["joint_pos"], compiled.frame_count, actuated_count)
    cfg_source = _align_source_cfg(cfg_source, source_names, robot_joint_names)
    source_reference = np.ones_like(cfg_source, dtype=np.float64)
    boundary = np.zeros(cfg_source.shape[0], dtype=np.float64)
    return (
        compiled,
        root_source,
        cfg_source,
        source_reference,
        boundary,
        _fps_from_motion(source_motion),
        source_names,
        str(source_path_obj),
        "legacy_lte_keypoints",
    )


def _stats(values: np.ndarray) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size == 0:
        return {"mean": 0.0, "max": 0.0, "rms": 0.0}
    return {
        "mean": float(np.mean(array)),
        "max": float(np.max(array)),
        "rms": float(np.sqrt(np.mean(array * array))),
    }


def _least_squares_sqrt_weight(weight: float) -> float:
    """Convert an objective weight to its residual-space coefficient."""

    value = float(weight)
    if value < 0.0:
        raise ValueError("least-squares weight must be non-negative")
    return float(np.sqrt(value))


CONTACT_CAPABLE_COLLISION_PARTS = frozenset(
    {"LF", "RF", "LH", "RH", "LK", "RK"}
)
FULLBODY_DEEPER_WEIGHT_MULTIPLIER = 4.0
CONTACT_CAPABLE_DEEPER_WEIGHT_MULTIPLIER = 4.0
CONTACT_REFERENCE_BODY_BY_PART = {
    "LF": "left_ankle_roll_link",
    "RF": "right_ankle_roll_link",
    "LH": "left_sphere_hand_link",
    "RH": "right_sphere_hand_link",
    "LK": "left_knee_link",
    "RK": "right_knee_link",
}


def _environment_deeper_weight_for_body(
    body_name: str,
    base_weight: float,
    *,
    is_active_contact: bool = False,
) -> float:
    """Prioritize physical contact-capable bodies while protecting all bodies."""

    if is_active_contact:
        return float(base_weight)
    part_name = _contact_part_for_body_name(body_name)
    multiplier = (
        CONTACT_CAPABLE_DEEPER_WEIGHT_MULTIPLIER
        if part_name in CONTACT_CAPABLE_COLLISION_PARTS
        else 1.0
    )
    return (
        float(base_weight)
        * FULLBODY_DEEPER_WEIGHT_MULTIPLIER
        * float(multiplier)
    )


def _robot_penetration_depth_by_body(contacts: Any) -> dict[str, float]:
    """Return true geometry overlap depth for each robot body in one frame."""

    return {
        body_name: max(0.0, -signed_distance)
        for body_name, signed_distance in (
            _robot_min_geometry_distance_by_body(contacts).items()
        )
    }


def _robot_min_geometry_distance_by_body(
    contacts: Any,
) -> dict[str, float]:
    """Return the closest signed geometry distance for each robot body."""

    closest: dict[str, float] = {}
    for local_index, contact_index in enumerate(
        np.asarray(contacts.robot_body_indices, dtype=np.int64).tolist()
    ):
        body_name = str(contacts.robot_body_names[local_index])
        signed_distance = float(
            contacts.geometry_distance_m[int(contact_index)]
        )
        closest[body_name] = min(
            closest.get(body_name, np.inf),
            signed_distance,
        )
    return closest


def _terrain_surface_key(
    contacts: Any,
    *,
    local_index: int,
    contact_index: int,
) -> str:
    """Return a stable ground/top/side identity for one robot-terrain witness."""

    index = int(contact_index)
    body0 = int(contacts.body0[index])
    body1 = int(contacts.body1[index])
    if (body0 >= 0) == (body1 >= 0):
        raise ValueError("surface identity requires exactly one terrain-side body")
    terrain_shape = (
        int(contacts.shape0[index])
        if body0 < 0
        else int(contacts.shape1[index])
    )
    shape_labels = tuple(str(item) for item in contacts.shape_labels)
    shape_label = (
        shape_labels[terrain_shape]
        if 0 <= terrain_shape < len(shape_labels)
        else f"shape:{terrain_shape}"
    )
    if "ground" in shape_label.lower():
        return f"{shape_label}:ground"
    outward = np.asarray(
        contacts.outward_normals_w[int(local_index)],
        dtype=np.float64,
    )
    if float(outward[2]) > np.sqrt(0.5):
        orientation = "top"
    elif float(outward[2]) < -np.sqrt(0.5):
        orientation = "bottom"
    else:
        orientation = "side"
    return f"{shape_label}:{orientation}"


def _surface_class(value: str | None) -> str | None:
    """Reduce an anchor/simulator surface identity to ground/top/side/bottom."""

    if value is None:
        return None
    lowered = str(value).lower()
    if "ground" in lowered:
        return "ground"
    for surface_class in ("top", "side", "bottom"):
        if (
            f":{surface_class}" in lowered
            or f"_{surface_class}" in lowered
            or f"-{surface_class}" in lowered
        ):
            return surface_class
    return None


def _contact_target_surface_class(contact: Any) -> str | None:
    """Return the environment surface class explicitly bound to one patch."""

    metadata = dict(getattr(contact, "metadata", {}) or {})
    return _surface_class(
        getattr(contact, "surface_id", None)
        or metadata.get("target_surface_id")
    )


def _robot_min_geometry_distance_by_body_surface(
    contacts: Any,
) -> dict[tuple[str, str], float]:
    """Return the closest signed distance for each robot body and surface."""

    closest: dict[tuple[str, str], float] = {}
    for local_index, contact_index in enumerate(
        np.asarray(contacts.robot_body_indices, dtype=np.int64).tolist()
    ):
        body_name = str(contacts.robot_body_names[local_index])
        surface_key = _terrain_surface_key(
            contacts,
            local_index=local_index,
            contact_index=int(contact_index),
        )
        key = (body_name, surface_key)
        signed_distance = float(
            contacts.geometry_distance_m[int(contact_index)]
        )
        closest[key] = min(
            closest.get(key, np.inf),
            signed_distance,
        )
    return closest


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).expanduser().resolve().open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cached_pyroki_robot(
    robot_path: Path,
    *,
    pyroki: Any,
    yourdfpy: Any,
) -> tuple[Any, tuple[str, ...], tuple[str, ...], int]:
    resolved = robot_path.expanduser().resolve()
    stat = resolved.stat()
    key = (str(resolved), int(stat.st_mtime_ns), int(stat.st_size))
    cached = _PYROKI_ROBOT_CACHE.get(key)
    if cached is not None:
        return cached
    urdf = yourdfpy.URDF.load(str(resolved), load_meshes=False)
    robot = pyroki.Robot.from_urdf(urdf)
    value = (
        robot,
        tuple(str(name) for name in robot.joints.actuated_names),
        tuple(str(name) for name in robot.links.names),
        int(robot.joints.num_actuated_joints),
    )
    _PYROKI_ROBOT_CACHE.clear()
    _PYROKI_ROBOT_CACHE[key] = value
    return value


def _cached_newton_collision_scene(
    terrain_mesh: str | Path | None,
    *,
    device: str = "cpu",
) -> DirectNewtonCollisionScene:
    resolved = (
        None
        if terrain_mesh is None
        else str(Path(terrain_mesh).expanduser().resolve())
    )
    key = (resolved, str(device))
    cached = _NEWTON_COLLISION_SCENE_CACHE.get(key)
    if cached is None:
        cached = DirectNewtonCollisionScene(resolved, device=device)
        _NEWTON_COLLISION_SCENE_CACHE[key] = cached
    return cached


def _collision_reference_cache_metadata(
    *,
    source_terrain_mesh: str | Path,
    reference_qpos: np.ndarray,
    robot_urdf: str | Path,
) -> dict[str, Any]:
    qpos = np.ascontiguousarray(reference_qpos, dtype=np.float64)
    return {
        "schema": COLLISION_REFERENCE_CACHE_SCHEMA,
        "source_terrain_mesh": str(
            Path(source_terrain_mesh).expanduser().resolve()
        ),
        "source_terrain_sha256": _sha256_file(source_terrain_mesh),
        "reference_qpos_sha256": hashlib.sha256(qpos.tobytes()).hexdigest(),
        "robot_urdf": str(Path(robot_urdf).expanduser().resolve()),
        "robot_urdf_sha256": _sha256_file(robot_urdf),
        "frame_count": int(qpos.shape[0]),
    }


def _load_collision_reference_cache(
    path: str | Path,
    *,
    expected_metadata: dict[str, Any],
) -> list[dict[tuple[str, str], float]] | None:
    cache_path = Path(path).expanduser()
    if not cache_path.is_file():
        return None
    try:
        with np.load(cache_path, allow_pickle=False) as payload:
            metadata = json.loads(str(payload["metadata_json"].item()))
            if metadata != expected_metadata:
                return None
            offsets = np.asarray(payload["frame_offsets"], dtype=np.int64)
            body_names = np.asarray(payload["body_names"], dtype=np.str_)
            surface_keys = np.asarray(payload["surface_keys"], dtype=np.str_)
            distances = np.asarray(payload["signed_distances_m"], dtype=np.float64)
    except (KeyError, OSError, ValueError, json.JSONDecodeError):
        return None
    frame_count = int(expected_metadata["frame_count"])
    if (
        offsets.shape != (frame_count + 1,)
        or offsets[0] != 0
        or offsets[-1] != len(distances)
        or body_names.shape != distances.shape
        or surface_keys.shape != distances.shape
        or np.any(np.diff(offsets) < 0)
        or not np.isfinite(distances).all()
    ):
        return None
    result: list[dict[tuple[str, str], float]] = []
    for frame in range(frame_count):
        start = int(offsets[frame])
        end = int(offsets[frame + 1])
        result.append(
            {
                (str(body_names[index]), str(surface_keys[index])): float(
                    distances[index]
                )
                for index in range(start, end)
            }
        )
    return result


def _write_collision_reference_cache(
    path: str | Path,
    *,
    metadata: dict[str, Any],
    frames: list[dict[tuple[str, str], float]],
) -> None:
    cache_path = Path(path).expanduser()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    offsets = [0]
    body_names: list[str] = []
    surface_keys: list[str] = []
    distances: list[float] = []
    for frame in frames:
        for (body_name, surface_key), distance in sorted(frame.items()):
            body_names.append(body_name)
            surface_keys.append(surface_key)
            distances.append(float(distance))
        offsets.append(len(distances))
    temporary = cache_path.with_name(
        f".{cache_path.name}.{os.getpid()}.tmp"
    )
    with temporary.open("wb") as stream:
        np.savez_compressed(
            stream,
            metadata_json=np.asarray(json.dumps(metadata, sort_keys=True)),
            frame_offsets=np.asarray(offsets, dtype=np.int64),
            body_names=np.asarray(body_names, dtype=np.str_),
            surface_keys=np.asarray(surface_keys, dtype=np.str_),
            signed_distances_m=np.asarray(distances, dtype=np.float64),
        )
    temporary.replace(cache_path)


def _contact_part_for_body_name(body_name: str) -> str | None:
    value = str(body_name).lower()
    side = "L" if value.startswith("left_") else "R" if value.startswith("right_") else ""
    if not side:
        return None
    if "ankle" in value or "foot" in value:
        return f"{side}F"
    if "wrist" in value or "hand" in value:
        return f"{side}H"
    if "knee" in value:
        return f"{side}K"
    if "hip" in value:
        return f"{side}HIP"
    return None


def _is_contact_reference_body(
    body_name: str,
    part_name: str,
) -> bool:
    """Keep the mature six-part depth tracking contract unchanged."""

    expected = CONTACT_REFERENCE_BODY_BY_PART.get(str(part_name))
    return expected == str(body_name)


def solve_pyroki_fullbody_ik(
    *,
    lte_path: str | Path,
    output_path: str | Path,
    robot_urdf: str | Path = DEFAULT_ROBOT_URDF,
    source_motion_path: str | Path | None = None,
    max_nfev: int = 25,
    q_prior_weight: float = 0.25,
    q_smooth_weight: float = 0.5,
    boundary_pin_weight: float = 2.0,
    edited_contact_weight: float = 100.0,
    fixed_contact_weight: float = 80.0,
    foot_orientation_weight: float = 20.0,
    q_velocity_weight: float = 2.0,
    q_acceleration_weight: float = 1.0,
    collision_similarity_weight: float = 25.0,
    collision_max_refinements: int = 1,
    self_collision_weight: float = 20_000.0,
    collision_reference_cache_path: str | Path | None = None,
) -> Path:
    import jax
    import jax.numpy as jnp
    import pyroki
    import yourdfpy

    payload = _load_npz(lte_path)
    collision_spec: ContactAwareTaskspaceMotion | None = None
    collision_terrain_mesh: str | None = None
    collision_source_terrain_mesh: str | None = None
    collision_reference_motion_path: str | None = None
    if "contact_aware_taskspace_json" in payload:
        collision_spec = ContactAwareTaskspaceMotion.from_arrays(payload)
        collision_metadata = dict(collision_spec.metadata)
        raw_terrain_mesh = collision_metadata.get("target_terrain_mesh")
        if raw_terrain_mesh:
            collision_terrain_mesh = str(
                Path(raw_terrain_mesh).expanduser().resolve()
            )
            raw_source_terrain = collision_metadata.get("source_terrain_mesh")
            raw_reference_motion = collision_metadata.get(
                "collision_reference_motion"
            )
            if not raw_source_terrain or not raw_reference_motion:
                raise ValueError(
                    "target-terrain collision IK requires source_terrain_mesh "
                    "and collision_reference_motion; a fixed penetration "
                    "allowance is not supported"
                )
            collision_source_terrain_mesh = str(
                Path(raw_source_terrain).expanduser().resolve()
            )
            collision_reference_motion_path = str(
                Path(raw_reference_motion).expanduser().resolve()
            )
    robot_path = Path(robot_urdf).expanduser()
    if not robot_path.exists():
        raise FileNotFoundError(f"robot URDF not found for PyRoki IK: {robot_path}")
    (
        robot,
        robot_joint_names,
        link_names,
        actuated_count,
    ) = _cached_pyroki_robot(
        robot_path,
        pyroki=pyroki,
        yourdfpy=yourdfpy,
    )

    (
        compiled,
        root_source,
        cfg_source,
        source_reference,
        boundary_weights,
        fps,
        source_joint_names,
        source_path,
        input_schema,
    ) = _input_problem(
        payload,
        link_names=link_names,
        actuated_count=actuated_count,
        robot_joint_names=robot_joint_names,
        source_motion_path=source_motion_path,
        edited_contact_weight=edited_contact_weight,
        fixed_contact_weight=fixed_contact_weight,
    )
    n_frames = min(compiled.frame_count, cfg_source.shape[0])
    root_source = root_source[:n_frames].copy()
    cfg_source = cfg_source[:n_frames].copy()
    source_reference = source_reference[:n_frames]
    boundary_weights = boundary_weights[:n_frames]

    collision_reference_qpos: np.ndarray | None = None
    collision_reference_force_confidence: dict[str, np.ndarray] = {}
    if collision_terrain_mesh is not None:
        assert collision_reference_motion_path is not None
        reference_motion = _load_npz(collision_reference_motion_path)
        if "joint_pos" not in reference_motion:
            raise ValueError(
                "collision reference motion is missing joint_pos: "
                f"{collision_reference_motion_path}"
            )
        reference_root, reference_cfg = _source_qpos_from_array(
            reference_motion["joint_pos"],
            n_frames,
            actuated_count,
        )
        reference_joint_names = _motion_strings(
            reference_motion,
            ("joint_names", "dof_names", "joint_name", "dof_name"),
        )
        reference_cfg = _align_source_cfg(
            reference_cfg,
            reference_joint_names,
            robot_joint_names,
        )
        if reference_root.shape[0] != n_frames:
            raise ValueError(
                "collision reference motion is shorter than the IK task: "
                f"{reference_root.shape[0]} != {n_frames}"
            )
        reference_fps = _fps_from_motion(reference_motion)
        if not np.isclose(reference_fps, fps, atol=1.0e-6, rtol=0.0):
            raise ValueError(
                "collision reference motion fps differs from the IK task: "
                f"{reference_fps} != {fps}"
            )
        collision_reference_qpos = np.concatenate(
            (reference_root, reference_cfg),
            axis=1,
        )
        if (
            "contact_force_part_w" in reference_motion
            and "contact_force_part_order" in reference_motion
        ):
            force_w = np.asarray(
                reference_motion["contact_force_part_w"],
                dtype=np.float64,
            )[:n_frames]
            part_order = _motion_strings(
                reference_motion,
                ("contact_force_part_order",),
            )
            if force_w.ndim == 3 and force_w.shape[1] == len(part_order):
                grouped_parts = {
                    "LF": ("LHEE", "LTOE"),
                    "RF": ("RHEE", "RTOE"),
                    "LH": ("LH",),
                    "RH": ("RH",),
                    "LK": ("LK",),
                    "RK": ("RK",),
                }
                for part_name, source_parts in grouped_parts.items():
                    source_indices = [
                        part_order.index(source_part)
                        for source_part in source_parts
                        if source_part in part_order
                    ]
                    if not source_indices:
                        continue
                    combined_force = np.sum(
                        force_w[:, source_indices],
                        axis=1,
                    )
                    values = np.linalg.norm(combined_force, axis=-1)
                    positive = values[values > 0.0]
                    scale = (
                        float(np.median(positive))
                        if positive.size
                        else 1.0
                    )
                    collision_reference_force_confidence[part_name] = (
                        values / (values + max(scale, np.finfo(np.float64).eps))
                    )

    pelvis_column = compiled.semantic_names.index("pelvis") if "pelvis" in compiled.semantic_names else None
    if pelvis_column is not None:
        root_source[:, :3] = compiled.semantic_targets_w[:n_frames, pelvis_column]

    lower = np.asarray(robot.joints.lower_limits, dtype=np.float64)
    upper = np.asarray(robot.joints.upper_limits, dtype=np.float64)
    finite = np.isfinite(lower) & np.isfinite(upper)
    lower = np.where(finite, lower, -np.pi)
    upper = np.where(finite, upper, np.pi)
    cfg_source = np.clip(cfg_source, lower, upper)
    semantic_indices_jax = jnp.asarray(compiled.semantic_link_indices, dtype=jnp.int32)
    source_fk = np.asarray(robot.forward_kinematics(jnp.asarray(cfg_source)), dtype=np.float64)
    foot_orientation_indices = tuple(
        index
        for aliases in SOURCE_FOOT_ORIENTATION_LINKS
        if (index := resolve_link_index(link_names, aliases[0], aliases)) is not None
    )
    foot_orientation_indices_jax = jnp.asarray(foot_orientation_indices, dtype=jnp.int32)
    source_foot_orientations = source_fk[:, foot_orientation_indices, :4]

    def quat_apply_jax(quat: Any, vector: Any) -> Any:
        qvec = quat[..., 1:4]
        uv = jnp.cross(qvec, vector)
        uuv = jnp.cross(qvec, uv)
        return vector + 2.0 * (quat[..., :1] * uv + uuv)

    def residual_jax(
        solve_state: Any,
        semantic_target_base: Any,
        semantic_sqrt_weight: Any,
        contact_link_indices: Any,
        contact_points_local: Any,
        contact_target_base: Any,
        contact_sqrt_weight: Any,
        q_prior: Any,
        q_previous: Any,
        q_previous_previous: Any,
        q_prior_previous: Any,
        q_prior_previous_previous: Any,
        q_prior_scale: Any,
        source_foot_orientation: Any,
        collision_link_indices: Any,
        collision_points_local: Any,
        collision_normals_base: Any,
        collision_terrain_points_base: Any,
        collision_similarity_weight: Any,
        collision_deeper_weight: Any,
        self_collision_link_a: Any,
        self_collision_point_a_local: Any,
        self_collision_link_b: Any,
        self_collision_point_b_local: Any,
        self_collision_normals_base: Any,
        self_collision_sqrt_weight: Any,
        root_delta_previous: Any,
        root_delta_previous_previous: Any,
    ) -> Any:
        root_delta = solve_state[:3]
        q_cfg = solve_state[3:]
        fk = robot.forward_kinematics(q_cfg)
        semantic_pos = fk[semantic_indices_jax, 4:7] + root_delta
        semantic_res = ((semantic_pos - semantic_target_base) * semantic_sqrt_weight[:, None]).reshape(-1)

        contact_pose = fk[contact_link_indices]
        contact_pred = (
            contact_pose[:, 4:7]
            + quat_apply_jax(contact_pose[:, :4], contact_points_local)
            + root_delta
        )
        contact_res = ((contact_pred - contact_target_base) * contact_sqrt_weight[:, None]).reshape(-1)

        prior_res = (q_cfg - q_prior) * q_prior_scale
        smooth_res = (q_cfg - q_previous) * float(q_smooth_weight)
        velocity_res = (
            (q_cfg - q_previous) - (q_prior - q_prior_previous)
        ) * float(q_velocity_weight)
        acceleration_res = (
            (q_cfg - 2.0 * q_previous + q_previous_previous)
            - (q_prior - 2.0 * q_prior_previous + q_prior_previous_previous)
        ) * float(q_acceleration_weight)

        foot_pose = fk[foot_orientation_indices_jax]
        foot_quat = foot_pose[:, :4]
        target_conjugate = source_foot_orientation.at[:, 1:4].multiply(-1.0)
        aw, ax, ay, az = jnp.moveaxis(target_conjugate, -1, 0)
        bw, bx, by, bz = jnp.moveaxis(foot_quat, -1, 0)
        relative = jnp.stack(
            (
                aw * bw - ax * bx - ay * by - az * bz,
                aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
            ),
            axis=-1,
        )
        relative = jnp.where(relative[:, :1] < 0.0, -relative, relative)
        foot_orientation_res = (
            2.0 * relative[:, 1:4] * jnp.sqrt(float(foot_orientation_weight))
        ).reshape(-1)
        collision_pose = fk[collision_link_indices]
        collision_point = (
            collision_pose[:, 4:7]
            + quat_apply_jax(
                collision_pose[:, :4],
                collision_points_local,
            )
            + root_delta
        )
        collision_signed_distance = jnp.sum(
            (
                collision_point
                - collision_terrain_points_base
            )
            * collision_normals_base,
            axis=-1,
        )
        collision_similarity_res = (
            collision_signed_distance * collision_similarity_weight
        )
        collision_deeper_res = (
            jnp.minimum(collision_signed_distance, 0.0)
            * collision_deeper_weight
        )
        self_pose_a = fk[self_collision_link_a]
        self_pose_b = fk[self_collision_link_b]
        self_point_a = (
            self_pose_a[:, 4:7]
            + quat_apply_jax(
                self_pose_a[:, :4],
                self_collision_point_a_local,
            )
        )
        self_point_b = (
            self_pose_b[:, 4:7]
            + quat_apply_jax(
                self_pose_b[:, :4],
                self_collision_point_b_local,
            )
        )
        self_signed_distance = jnp.sum(
            (self_point_b - self_point_a)
            * self_collision_normals_base,
            axis=-1,
        )
        self_collision_res = self_collision_barrier_residual(
            self_signed_distance,
            self_collision_sqrt_weight,
            array_module=jnp,
        )
        root_delta_prior_res = root_delta * np.sqrt(25.0)
        root_delta_velocity_res = (
            root_delta - root_delta_previous
        ) * np.sqrt(100.0)
        root_delta_acceleration_res = (
            root_delta
            - 2.0 * root_delta_previous
            + root_delta_previous_previous
        ) * np.sqrt(400.0)
        return jnp.concatenate(
            [
                semantic_res,
                contact_res,
                prior_res,
                smooth_res,
                velocity_res,
                acceleration_res,
                foot_orientation_res,
                collision_similarity_res,
                collision_deeper_res,
                self_collision_res,
                root_delta_prior_res,
                root_delta_velocity_res,
                root_delta_acceleration_res,
            ],
            axis=0,
        )

    residual_compiled = jax.jit(residual_jax)
    jac_compiled = jax.jit(jax.jacfwd(residual_jax, argnums=0))

    out_cfg = np.zeros((n_frames, actuated_count), dtype=np.float64)
    out_root_delta_base = np.zeros((n_frames, 3), dtype=np.float64)
    q_previous = cfg_source[0]
    q_previous_previous = cfg_source[0]
    root_delta_previous = np.zeros(3, dtype=np.float64)
    root_delta_previous_previous = np.zeros(3, dtype=np.float64)
    success: list[bool] = []
    nfev: list[int] = []
    costs: list[float] = []
    collision_slots = len(link_names)
    inactive_collision_args = (
        np.zeros(collision_slots, dtype=np.int32),
        np.zeros((collision_slots, 3), dtype=np.float64),
        np.zeros((collision_slots, 3), dtype=np.float64),
        np.zeros((collision_slots, 3), dtype=np.float64),
        np.zeros(collision_slots, dtype=np.float64),
        np.zeros(collision_slots, dtype=np.float64),
        np.zeros(collision_slots, dtype=np.int32),
        np.zeros((collision_slots, 3), dtype=np.float64),
        np.zeros(collision_slots, dtype=np.int32),
        np.zeros((collision_slots, 3), dtype=np.float64),
        np.zeros((collision_slots, 3), dtype=np.float64),
        np.zeros(collision_slots, dtype=np.float64),
    )
    collision_similarity_weight_value = float(collision_similarity_weight)
    collision_deeper_weight_value = 100.0
    collision_max_refinements_value = int(collision_max_refinements)
    self_collision_weight_value = float(self_collision_weight)
    if collision_similarity_weight_value < 0.0:
        raise ValueError("collision_similarity_weight must be non-negative")
    if collision_max_refinements_value < 0:
        raise ValueError("collision_max_refinements must be non-negative")
    if self_collision_weight_value < 0.0:
        raise ValueError("self_collision_weight must be non-negative")
    root_delta_limit_m = 0.04
    solve_lower = np.concatenate(
        (np.full(3, -root_delta_limit_m), lower)
    )
    solve_upper = np.concatenate(
        (np.full(3, root_delta_limit_m), upper)
    )
    collision_scene = (
        _cached_newton_collision_scene(
            collision_terrain_mesh,
            device="cpu",
        )
        if collision_terrain_mesh is not None
        else None
    )
    collision_reference_scene = None
    collision_reference_signed_distances: list[
        dict[tuple[str, str], float]
    ] = []
    collision_reference_cache_hit = False
    collision_reference_max_m = 0.0
    collision_reference_proximity_frames = 0
    if collision_source_terrain_mesh is not None:
        assert collision_reference_qpos is not None
        cache_metadata = _collision_reference_cache_metadata(
            source_terrain_mesh=collision_source_terrain_mesh,
            reference_qpos=collision_reference_qpos,
            robot_urdf=robot_path,
        )
        cached = (
            _load_collision_reference_cache(
                collision_reference_cache_path,
                expected_metadata=cache_metadata,
            )
            if collision_reference_cache_path is not None
            else None
        )
        if cached is not None:
            collision_reference_signed_distances = cached
            collision_reference_cache_hit = True
        else:
            collision_reference_scene = _cached_newton_collision_scene(
                collision_source_terrain_mesh,
                device="cpu",
            )
            for frame in range(n_frames):
                reference_contacts = collision_reference_scene.query_qpos(
                    collision_reference_qpos[frame]
                )
                collision_reference_signed_distances.append(
                    _robot_min_geometry_distance_by_body_surface(
                        reference_contacts
                    )
                )
            if collision_reference_cache_path is not None:
                _write_collision_reference_cache(
                    collision_reference_cache_path,
                    metadata=cache_metadata,
                    frames=collision_reference_signed_distances,
                )
        for signed_distances in collision_reference_signed_distances:
            frame_max = max(
                (
                    max(0.0, -signed_distance)
                    for signed_distance in signed_distances.values()
                ),
                default=0.0,
            )
            collision_reference_max_m = max(
                collision_reference_max_m,
                frame_max,
            )
            if signed_distances:
                collision_reference_proximity_frames += 1
    else:
        collision_reference_signed_distances = [
            {} for _ in range(n_frames)
        ]
    collision_initial_active_frames = 0
    collision_final_active_frames = 0
    collision_initial_raw_max_m = 0.0
    collision_final_raw_max_m = 0.0
    collision_initial_excess_max_m = 0.0
    collision_final_excess_max_m = 0.0
    collision_initial_similarity_error_max_m = 0.0
    collision_final_similarity_error_max_m = 0.0
    collision_initial_similarity_errors: list[float] = []
    collision_final_similarity_errors: list[float] = []
    collision_refinement_solve_count = 0
    self_collision_initial_active_frames = 0
    self_collision_final_active_frames = 0
    self_collision_initial_max_m = 0.0
    self_collision_final_max_m = 0.0
    self_collision_initial_pairs: set[tuple[str, str]] = set()
    self_collision_final_pairs: set[tuple[str, str]] = set()
    link_index_by_name = {
        name: index for index, name in enumerate(link_names)
    }
    active_contact_surface_weight: list[
        dict[tuple[str, str], float]
    ] = [dict() for _ in range(n_frames)]
    if collision_spec is not None:
        for contact in collision_spec.contacts:
            part_name = _contact_part_for_body_name(contact.body_label)
            surface_class = _contact_target_surface_class(contact)
            if part_name is None or surface_class is None:
                continue
            weight = float(
                edited_contact_weight
                if contact.kind == "edited_contact"
                else fixed_contact_weight
            )
            for absolute_frame in np.asarray(
                contact.frames,
                dtype=np.int64,
            ).tolist():
                frame = int(absolute_frame) - int(collision_spec.frame_start)
                if not 0 <= frame < n_frames:
                    continue
                key = (part_name, surface_class)
                active_contact_surface_weight[frame][key] = max(
                    active_contact_surface_weight[frame].get(key, 0.0),
                    weight,
                )

    for frame in range(n_frames):
        root = root_source[frame].copy()
        root_rotation = _quat_wxyz_to_rotation(root[3:7])
        semantic_target_base = root_rotation.inv().apply(
            compiled.semantic_targets_w[frame] - root[:3][None, :]
        )
        contact_target_base = root_rotation.inv().apply(
            compiled.contact_targets_w[frame] - root[:3][None, :]
        )
        semantic_sqrt_weight = np.sqrt(np.maximum(compiled.semantic_weights[frame], 0.0))
        contact_sqrt_weight = np.sqrt(np.maximum(compiled.contact_weights[frame], 0.0))
        active_surface_weight = active_contact_surface_weight[frame]
        prior_scale = (
            float(q_prior_weight) * np.maximum(source_reference[frame], 0.0)
            + float(boundary_pin_weight) * float(boundary_weights[frame])
        )
        q_prior = cfg_source[frame]
        q_prior_previous = cfg_source[max(frame - 1, 0)]
        q_prior_previous_previous = cfg_source[max(frame - 2, 0)]
        x0 = np.clip(
            np.concatenate(
                (
                    root_delta_previous,
                    q_previous if frame > 0 else q_prior,
                )
            ),
            solve_lower,
            solve_upper,
        )

        args = (
            np.asarray(semantic_target_base, dtype=np.float64),
            np.asarray(semantic_sqrt_weight, dtype=np.float64),
            np.asarray(compiled.contact_link_indices[frame], dtype=np.int32),
            np.asarray(compiled.contact_points_local[frame], dtype=np.float64),
            np.asarray(contact_target_base, dtype=np.float64),
            np.asarray(contact_sqrt_weight, dtype=np.float64),
            np.asarray(q_prior, dtype=np.float64),
            np.asarray(q_previous, dtype=np.float64),
            np.asarray(q_previous_previous, dtype=np.float64),
            np.asarray(q_prior_previous, dtype=np.float64),
            np.asarray(q_prior_previous_previous, dtype=np.float64),
            np.asarray(prior_scale, dtype=np.float64),
            np.asarray(source_foot_orientations[frame], dtype=np.float64),
            *inactive_collision_args,
            np.asarray(root_delta_previous, dtype=np.float64),
            np.asarray(
                root_delta_previous_previous,
                dtype=np.float64,
            ),
        )

        args_jax = tuple(jnp.asarray(value) for value in args)

        def fun(x: np.ndarray) -> np.ndarray:
            return np.asarray(residual_compiled(jnp.asarray(x), *args_jax))

        def jac(x: np.ndarray) -> np.ndarray:
            return np.asarray(jac_compiled(jnp.asarray(x), *args_jax))

        result = least_squares(
            fun,
            x0,
            jac=jac,
            bounds=(solve_lower, solve_upper),
            max_nfev=int(max_nfev),
            xtol=1.0e-5,
            ftol=1.0e-5,
            gtol=1.0e-5,
        )
        frame_nfev = int(result.nfev)
        frame_success = bool(result.success)
        candidate_root_delta = np.clip(
            result.x[:3],
            solve_lower[:3],
            solve_upper[:3],
        )
        candidate_cfg = np.clip(result.x[3:], lower, upper)

        def active_collision_contacts(
            q_cfg: np.ndarray,
            root_delta_base: np.ndarray,
        ) -> tuple[
            Any | None,
            list[
                tuple[
                    int,
                    int,
                    float,
                    float,
                    float,
                    float,
                    float,
                    float,
                ]
            ],
            float,
            float,
            list[float],
        ]:
            if collision_scene is None:
                return None, [], 0.0, 0.0, []
            query_root = root.copy()
            query_root[:3] += root_rotation.apply(root_delta_base)
            qpos_query = np.concatenate([query_root, q_cfg], axis=0)
            contacts = collision_scene.query_qpos(qpos_query)
            reference_signed_by_body_surface = (
                collision_reference_signed_distances[frame]
            )
            closest_target_by_body_surface: dict[
                tuple[str, str],
                tuple[int, int, float],
            ] = {}
            raw_max = 0.0
            excess_max = 0.0
            for local_index, contact_index in enumerate(
                contacts.robot_body_indices.tolist()
            ):
                signed_distance = float(
                    contacts.geometry_distance_m[int(contact_index)]
                )
                body_name = contacts.robot_body_names[local_index]
                surface_key = _terrain_surface_key(
                    contacts,
                    local_index=local_index,
                    contact_index=int(contact_index),
                )
                body_surface_key = (body_name, surface_key)
                surface_class = _surface_class(surface_key)
                depth = max(0.0, -signed_distance)
                raw_max = max(raw_max, depth)
                previous_contact = closest_target_by_body_surface.get(
                    body_surface_key
                )
                if (
                    previous_contact is None
                    or signed_distance < previous_contact[2]
                ):
                    closest_target_by_body_surface[body_surface_key] = (
                        local_index,
                        int(contact_index),
                        signed_distance,
                    )
            selected: list[
                tuple[
                    int,
                    int,
                    float,
                    float,
                    float,
                    float,
                    float,
                    float,
                ]
            ] = []
            similarity_errors: list[float] = []
            for (body_name, surface_key), (
                local_index,
                contact_index,
                signed_distance,
            ) in closest_target_by_body_surface.items():
                if body_name not in link_index_by_name:
                    continue
                part_name = _contact_part_for_body_name(body_name)
                reference_signed = reference_signed_by_body_surface.get(
                    (body_name, surface_key)
                )
                is_active_contact = (
                    surface_class is not None
                    and (part_name, surface_class)
                    in active_surface_weight
                    and reference_signed is not None
                    and part_name is not None
                    and _is_contact_reference_body(
                        body_name,
                        part_name,
                    )
                )
                similarity_weight = 0.0
                target_signed = 0.0
                if is_active_contact:
                    assert reference_signed is not None
                    assert part_name is not None
                    target_signed = float(reference_signed)
                    force_curve = collision_reference_force_confidence.get(
                        part_name
                    )
                    force_confidence = (
                        float(force_curve[frame])
                        if force_curve is not None
                        else 0.5
                    )
                    similarity_weight = (
                        collision_similarity_weight_value
                        * force_confidence
                    )
                    similarity_errors.append(
                        abs(signed_distance - target_signed)
                    )
                depth = max(0.0, -signed_distance)
                reference_depth = max(0.0, -target_signed)
                excess_depth = max(0.0, depth - reference_depth)
                excess_max = max(excess_max, excess_depth)
                if not is_active_contact and depth <= 0.0:
                    continue
                selected.append(
                    (
                        local_index,
                        contact_index,
                        signed_distance,
                        target_signed,
                        similarity_weight,
                        _environment_deeper_weight_for_body(
                            body_name,
                            collision_deeper_weight_value,
                            is_active_contact=is_active_contact,
                        ),
                        abs(signed_distance - target_signed),
                        excess_depth,
                    )
                )
            return (
                contacts,
                selected,
                raw_max,
                excess_max,
                similarity_errors,
            )

        def active_self_collision_contacts(
            contacts: Any | None,
        ) -> tuple[list[tuple[int, str, str, float]], float]:
            if contacts is None:
                return [], 0.0
            closest_by_pair: dict[
                tuple[str, str],
                tuple[int, str, str, float],
            ] = {}
            for contact_index in range(len(contacts.geometry_distance_m)):
                body_a = int(contacts.body0[contact_index])
                body_b = int(contacts.body1[contact_index])
                if body_a < 0 or body_b < 0 or body_a == body_b:
                    continue
                name_a = collision_scene.body_names[body_a]
                name_b = collision_scene.body_names[body_b]
                if (
                    name_a not in link_index_by_name
                    or name_b not in link_index_by_name
                ):
                    continue
                signed_distance = float(
                    contacts.geometry_distance_m[contact_index]
                )
                if signed_distance >= 0.0:
                    continue
                key = tuple(sorted((name_a, name_b)))
                previous = closest_by_pair.get(key)
                if previous is None or signed_distance < previous[3]:
                    closest_by_pair[key] = (
                        contact_index,
                        name_a,
                        name_b,
                        signed_distance,
                    )
            selected = sorted(
                closest_by_pair.values(),
                key=lambda item: item[3],
            )
            maximum = max(
                (-item[3] for item in selected),
                default=0.0,
            )
            return selected, maximum

        (
            initial_contacts,
            active_contacts,
            initial_raw_max,
            initial_excess_max,
            initial_similarity_errors,
        ) = active_collision_contacts(
            candidate_cfg,
            candidate_root_delta,
        )
        active_self_contacts, initial_self_max = (
            active_self_collision_contacts(initial_contacts)
        )
        self_collision_initial_max_m = max(
            self_collision_initial_max_m,
            initial_self_max,
        )
        if active_self_contacts:
            self_collision_initial_active_frames += 1
            self_collision_initial_pairs.update(
                tuple(sorted((item[1], item[2])))
                for item in active_self_contacts
            )
        collision_initial_raw_max_m = max(
            collision_initial_raw_max_m,
            initial_raw_max,
        )
        collision_initial_excess_max_m = max(
            collision_initial_excess_max_m,
            initial_excess_max,
        )
        collision_initial_similarity_errors.extend(
            initial_similarity_errors
        )
        collision_initial_similarity_error_max_m = max(
            collision_initial_similarity_error_max_m,
            max(initial_similarity_errors, default=0.0),
        )
        final_raw_max = initial_raw_max
        final_excess_max = initial_excess_max
        final_similarity_errors = initial_similarity_errors
        final_self_max = initial_self_max
        if active_contacts:
            collision_initial_active_frames += 1

        for _ in range(collision_max_refinements_value):
            if initial_contacts is None or (
                not active_contacts and not active_self_contacts
            ):
                break
            collision_link_indices = np.zeros(
                collision_slots,
                dtype=np.int32,
            )
            collision_points_local = np.zeros(
                (collision_slots, 3),
                dtype=np.float64,
            )
            collision_normals_base = np.zeros(
                (collision_slots, 3),
                dtype=np.float64,
            )
            collision_terrain_points_base = np.zeros(
                (collision_slots, 3),
                dtype=np.float64,
            )
            collision_similarity_weight = np.zeros(
                collision_slots,
                dtype=np.float64,
            )
            collision_deeper_weight = np.zeros(
                collision_slots,
                dtype=np.float64,
            )
            self_collision_link_a = np.zeros(
                collision_slots,
                dtype=np.int32,
            )
            self_collision_point_a_local = np.zeros(
                (collision_slots, 3),
                dtype=np.float64,
            )
            self_collision_link_b = np.zeros(
                collision_slots,
                dtype=np.int32,
            )
            self_collision_point_b_local = np.zeros(
                (collision_slots, 3),
                dtype=np.float64,
            )
            self_collision_normals_base = np.zeros(
                (collision_slots, 3),
                dtype=np.float64,
            )
            self_collision_sqrt_weight = np.zeros(
                collision_slots,
                dtype=np.float64,
            )

            fk_frame = np.asarray(
                robot.forward_kinematics(jnp.asarray(candidate_cfg)),
                dtype=np.float64,
            )
            candidate_root = root.copy()
            candidate_root[:3] += root_rotation.apply(
                candidate_root_delta
            )
            body_position_w, body_quaternion_w = (
                world_body_poses_from_pyroki_fk(
                    candidate_root[None, :],
                    fk_frame[None, ...],
                )
            )
            for slot, (
                local_index,
                _contact_index,
                _signed_distance,
                target_signed_distance,
                similarity_weight,
                deeper_weight,
                _similarity_error,
                _excess_depth,
            ) in enumerate(active_contacts[:collision_slots]):
                body_name = initial_contacts.robot_body_names[local_index]
                link_index = link_index_by_name[body_name]
                link_rotation = _quat_wxyz_to_rotation(
                    body_quaternion_w[0, link_index]
                )
                point_local = link_rotation.inv().apply(
                    initial_contacts.robot_points_w[local_index]
                    - body_position_w[0, link_index]
                )
                normal_base = root_rotation.inv().apply(
                    initial_contacts.outward_normals_w[local_index]
                )
                terrain_point_base = root_rotation.inv().apply(
                    initial_contacts.terrain_points_w[local_index]
                    - root[:3]
                )
                # The shifted witness plane makes zero residual correspond to
                # the source rollout's signed geometry distance. A finite
                # weight encourages similarity without imposing equality.
                terrain_point_base = (
                    terrain_point_base
                    + target_signed_distance * normal_base
                )
                collision_link_indices[slot] = int(link_index)
                collision_points_local[slot] = point_local
                collision_normals_base[slot] = normal_base
                collision_terrain_points_base[slot] = terrain_point_base
                collision_similarity_weight[slot] = _least_squares_sqrt_weight(
                    similarity_weight
                )
                collision_deeper_weight[slot] = _least_squares_sqrt_weight(
                    deeper_weight
                )

            for slot, (
                contact_index,
                body_a_name,
                body_b_name,
                _signed_distance,
            ) in enumerate(active_self_contacts[:collision_slots]):
                link_a = link_index_by_name[body_a_name]
                link_b = link_index_by_name[body_b_name]
                rotation_a = _quat_wxyz_to_rotation(
                    body_quaternion_w[0, link_a]
                )
                rotation_b = _quat_wxyz_to_rotation(
                    body_quaternion_w[0, link_b]
                )
                self_collision_link_a[slot] = int(link_a)
                self_collision_link_b[slot] = int(link_b)
                self_collision_point_a_local[slot] = rotation_a.inv().apply(
                    initial_contacts.point0_w[contact_index]
                    - body_position_w[0, link_a]
                )
                self_collision_point_b_local[slot] = rotation_b.inv().apply(
                    initial_contacts.point1_w[contact_index]
                    - body_position_w[0, link_b]
                )
                self_collision_normals_base[slot] = (
                    root_rotation.inv().apply(
                        initial_contacts.normal_a_to_b_w[contact_index]
                    )
                )
                self_collision_sqrt_weight[slot] = np.sqrt(
                    self_collision_weight_value
                )

            args = (
                np.asarray(semantic_target_base, dtype=np.float64),
                np.asarray(semantic_sqrt_weight, dtype=np.float64),
                np.asarray(
                    compiled.contact_link_indices[frame],
                    dtype=np.int32,
                ),
                np.asarray(
                    compiled.contact_points_local[frame],
                    dtype=np.float64,
                ),
                np.asarray(contact_target_base, dtype=np.float64),
                np.asarray(contact_sqrt_weight, dtype=np.float64),
                np.asarray(q_prior, dtype=np.float64),
                np.asarray(q_previous, dtype=np.float64),
                np.asarray(q_previous_previous, dtype=np.float64),
                np.asarray(q_prior_previous, dtype=np.float64),
                np.asarray(
                    q_prior_previous_previous,
                    dtype=np.float64,
                ),
                np.asarray(prior_scale, dtype=np.float64),
                np.asarray(
                    source_foot_orientations[frame],
                    dtype=np.float64,
                ),
                collision_link_indices,
                collision_points_local,
                collision_normals_base,
                collision_terrain_points_base,
                collision_similarity_weight,
                collision_deeper_weight,
                self_collision_link_a,
                self_collision_point_a_local,
                self_collision_link_b,
                self_collision_point_b_local,
                self_collision_normals_base,
                self_collision_sqrt_weight,
                np.asarray(root_delta_previous, dtype=np.float64),
                np.asarray(
                    root_delta_previous_previous,
                    dtype=np.float64,
                ),
            )
            args_jax = tuple(jnp.asarray(value) for value in args)
            candidate_state = np.concatenate(
                (candidate_root_delta, candidate_cfg)
            )
            refined = least_squares(
                fun,
                candidate_state,
                jac=jac,
                bounds=(solve_lower, solve_upper),
                max_nfev=int(max_nfev),
                xtol=1.0e-5,
                ftol=1.0e-5,
                gtol=1.0e-5,
            )
            collision_refinement_solve_count += 1
            frame_nfev += int(refined.nfev)
            frame_success = frame_success and bool(refined.success)
            candidate_root_delta = np.clip(
                refined.x[:3],
                solve_lower[:3],
                solve_upper[:3],
            )
            candidate_cfg = np.clip(refined.x[3:], lower, upper)
            result = refined
            (
                initial_contacts,
                active_contacts,
                final_raw_max,
                final_excess_max,
                final_similarity_errors,
            ) = active_collision_contacts(
                candidate_cfg,
                candidate_root_delta,
            )
            active_self_contacts, final_self_max = (
                active_self_collision_contacts(initial_contacts)
            )

        collision_final_raw_max_m = max(
            collision_final_raw_max_m,
            final_raw_max,
        )
        collision_final_excess_max_m = max(
            collision_final_excess_max_m,
            final_excess_max,
        )
        collision_final_similarity_errors.extend(final_similarity_errors)
        collision_final_similarity_error_max_m = max(
            collision_final_similarity_error_max_m,
            max(final_similarity_errors, default=0.0),
        )
        if active_contacts:
            collision_final_active_frames += 1
        self_collision_final_max_m = max(
            self_collision_final_max_m,
            final_self_max,
        )
        if active_self_contacts:
            self_collision_final_active_frames += 1
            self_collision_final_pairs.update(
                tuple(sorted((item[1], item[2])))
                for item in active_self_contacts
            )
        q_previous_previous = q_previous
        q_previous = candidate_cfg
        root_delta_previous_previous = root_delta_previous
        root_delta_previous = candidate_root_delta
        out_cfg[frame] = q_previous
        out_root_delta_base[frame] = root_delta_previous
        success.append(frame_success)
        nfev.append(frame_nfev)
        costs.append(float(result.cost))

    solved_root = root_source[:n_frames].copy()
    solved_root[:, :3] += np.stack(
        [
            _quat_wxyz_to_rotation(root[3:7]).apply(delta)
            for root, delta in zip(
                solved_root,
                out_root_delta_base,
            )
        ],
        axis=0,
    )
    qpos = np.concatenate([solved_root, out_cfg], axis=1)
    qpos[:, 3:7] = normalize_quat_wxyz(qpos[:, 3:7])
    qvel = holosoma_joint_velocities(qpos, fps)

    fk_base = np.asarray(robot.forward_kinematics(jnp.asarray(out_cfg)), dtype=np.float64)
    body_pos_w, body_quat_w = world_body_poses_from_pyroki_fk(
        solved_root,
        fk_base,
    )
    body_lin_vel_w, body_ang_vel_w = holosoma_body_velocities(body_pos_w, body_quat_w, fps)

    semantic_pred = body_pos_w[:, compiled.semantic_link_indices]
    semantic_error = np.linalg.norm(
        semantic_pred - compiled.semantic_targets_w[:n_frames], axis=-1
    )
    contact_pose_pos = body_pos_w[
        np.arange(n_frames)[:, None], compiled.contact_link_indices[:n_frames]
    ]
    contact_pose_quat = body_quat_w[
        np.arange(n_frames)[:, None], compiled.contact_link_indices[:n_frames]
    ]
    contact_pred = contact_pose_pos + quat_apply_wxyz(
        contact_pose_quat, compiled.contact_points_local[:n_frames]
    )
    contact_error_all = np.linalg.norm(
        contact_pred - compiled.contact_targets_w[:n_frames], axis=-1
    )
    contact_mask = compiled.contact_weights[:n_frames] > 0.0
    contact_error = contact_error_all[contact_mask]

    pelvis_index = resolve_link_index(link_names, "pelvis", ("pelvis",))
    root_position_error = 0.0
    root_quaternion_error = 0.0
    if pelvis_index is not None:
        root_position_error = float(np.max(np.abs(body_pos_w[:, pelvis_index] - qpos[:, :3])))
        quat_delta = np.minimum(
            np.max(np.abs(body_quat_w[:, pelvis_index] - qpos[:, 3:7]), axis=-1),
            np.max(np.abs(body_quat_w[:, pelvis_index] + qpos[:, 3:7]), axis=-1),
        )
        root_quaternion_error = float(np.max(quat_delta))

    diagnostics = {
        "input_schema": input_schema,
        "frame_count": int(n_frames),
        "semantic_names": list(compiled.semantic_names),
        "semantic_target_error_m": _stats(semantic_error),
        "contact_target_error_m": _stats(contact_error),
        "active_contact_point_samples": int(np.count_nonzero(contact_mask)),
        "unresolved_semantics": list(compiled.unresolved_semantics),
        "unresolved_contacts": list(compiled.unresolved_contacts),
        "least_squares_success_count": int(sum(success)),
        "least_squares_failure_count": int(len(success) - sum(success)),
        "least_squares_nfev": _stats(np.asarray(nfev, dtype=np.float64)),
        "least_squares_cost": _stats(np.asarray(costs, dtype=np.float64)),
        "source_foot_orientation_weight": float(foot_orientation_weight),
        "source_foot_orientation_link_count": len(foot_orientation_indices),
        "source_velocity_weight": float(q_velocity_weight),
        "source_acceleration_weight": float(q_acceleration_weight),
        "root_translation_limit_m": float(root_delta_limit_m),
        "root_translation_delta_m": _stats(
            np.linalg.norm(out_root_delta_base, axis=-1)
        ),
        "root_translation_velocity_mps": _stats(
            np.diff(out_root_delta_base, axis=0) * float(fps)
        ),
        "root_translation_acceleration_mps2": _stats(
            np.diff(out_root_delta_base, n=2, axis=0)
            * float(fps) ** 2
        ),
        "environment_collision_backend": (
            "newton_soft_signed_distance_integrated_frame_ik"
            if collision_terrain_mesh is not None
            else "disabled"
        ),
        "environment_collision_contract": (
            "source_rollout_soft_signed_distance_similarity"
            if collision_terrain_mesh is not None
            else "disabled"
        ),
        "environment_collision_reference_motion": (
            collision_reference_motion_path or ""
        ),
        "environment_collision_source_terrain_mesh": (
            collision_source_terrain_mesh or ""
        ),
        "environment_collision_target_terrain_mesh": (
            collision_terrain_mesh or ""
        ),
        "environment_collision_reference_proximity_frame_count": int(
            collision_reference_proximity_frames
        ),
        "environment_collision_reference_cache_path": (
            str(Path(collision_reference_cache_path).expanduser().resolve())
            if collision_reference_cache_path is not None
            else None
        ),
        "environment_collision_reference_cache_hit": bool(
            collision_reference_cache_hit
        ),
        "environment_collision_reference_penetration_max_m": float(
            collision_reference_max_m
        ),
        "environment_collision_initial_active_frame_count": int(
            collision_initial_active_frames
        ),
        "environment_collision_final_active_frame_count": int(
            collision_final_active_frames
        ),
        "environment_collision_initial_penetration_max_m": float(
            collision_initial_raw_max_m
        ),
        "environment_collision_penetration_max_m": float(
            collision_final_raw_max_m
        ),
        "environment_collision_initial_excess_penetration_max_m": float(
            collision_initial_excess_max_m
        ),
        "environment_collision_excess_penetration_max_m": float(
            collision_final_excess_max_m
        ),
        "environment_collision_initial_signed_distance_error_m": _stats(
            np.asarray(
                collision_initial_similarity_errors,
                dtype=np.float64,
            )
        ),
        "environment_collision_signed_distance_error_m": _stats(
            np.asarray(
                collision_final_similarity_errors,
                dtype=np.float64,
            )
        ),
        "environment_collision_initial_signed_distance_error_max_m": float(
            collision_initial_similarity_error_max_m
        ),
        "environment_collision_signed_distance_error_max_m": float(
            collision_final_similarity_error_max_m
        ),
        "environment_collision_refinement_solve_count": int(
            collision_refinement_solve_count
        ),
        "environment_collision_similarity_base_weight": float(
            collision_similarity_weight_value
        ),
        "environment_collision_max_refinements": int(
            collision_max_refinements_value
        ),
        "environment_collision_deeper_weight": float(
            collision_deeper_weight_value
        ),
        "environment_collision_fullbody_deeper_weight_multiplier": float(
            FULLBODY_DEEPER_WEIGHT_MULTIPLIER
        ),
        "environment_collision_contact_capable_deeper_weight_multiplier": float(
            CONTACT_CAPABLE_DEEPER_WEIGHT_MULTIPLIER
        ),
        "environment_collision_active_contact_deeper_weight_multiplier": 1.0,
        "environment_collision_active_contact_parts": sorted(
            CONTACT_CAPABLE_COLLISION_PARTS
        ),
        "environment_collision_contact_reference_body_by_part": dict(
            CONTACT_REFERENCE_BODY_BY_PART
        ),
        "environment_collision_similarity_force_weighting": (
            "force_norm_over_force_norm_plus_positive_median"
        ),
        "environment_collision_fixed_distance_tolerance_m": None,
        "self_collision_backend": (
            "newton_filtered_geometry_soft_barrier"
            if collision_scene is not None
            else "disabled"
        ),
        "self_collision_contract": (
            "zero_geometry_clearance_one_sided_barrier"
            if collision_scene is not None
            else "disabled"
        ),
        "self_collision_weight": float(self_collision_weight_value),
        "self_collision_initial_active_frame_count": int(
            self_collision_initial_active_frames
        ),
        "self_collision_active_frame_count": int(
            self_collision_final_active_frames
        ),
        "self_collision_initial_penetration_max_m": float(
            self_collision_initial_max_m
        ),
        "self_collision_penetration_max_m": float(
            self_collision_final_max_m
        ),
        "self_collision_initial_pairs": [
            list(pair) for pair in sorted(self_collision_initial_pairs)
        ],
        "self_collision_unresolved_pairs": [
            list(pair) for pair in sorted(self_collision_final_pairs)
        ],
        "root_body_position_error_max_m": root_position_error,
        "root_body_quaternion_error_max": root_quaternion_error,
        "newton_canonicalization_required": True,
    }

    output = Path(output_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        fps=np.asarray(float(fps)),
        joint_pos=qpos.astype(np.float32),
        joint_vel=qvel.astype(np.float32),
        joint_names=np.asarray(robot_joint_names, dtype=object),
        source_joint_names=np.asarray(source_joint_names, dtype=object),
        body_names=np.asarray(link_names, dtype=object),
        body_pos_w=body_pos_w.astype(np.float32),
        body_quat_w=body_quat_w.astype(np.float32),
        body_lin_vel_w=body_lin_vel_w.astype(np.float32),
        body_ang_vel_w=body_ang_vel_w.astype(np.float32),
        is_qpos=np.asarray(True),
        ik_backend=np.asarray("pyroki_contact_aware_taskspace"),
        kinematics_backend=np.asarray("pyroki_urdf_fk_preview"),
        newton_canonicalization_required=np.asarray(True),
        robot_urdf=np.asarray(str(robot_path)),
        target_names=np.asarray(compiled.semantic_names, dtype=object),
        source_motion=np.asarray(source_path or ""),
        taskspace_input=np.asarray(str(Path(lte_path).expanduser())),
        ik_diagnostics_json=np.asarray(json.dumps(diagnostics, sort_keys=True), dtype=object),
    )
    return output


def main(argv: list[str] | None = None) -> None:
    effective_argv = list(argv) if argv is not None else list(sys.argv[1:])
    if "--worker-socket" in effective_argv:
        index = effective_argv.index("--worker-socket")
        try:
            worker_name = effective_argv[index + 1]
        except IndexError as exc:
            raise ValueError("--worker-socket requires a name") from exc
        address = (
            "\0" + worker_name[1:]
            if worker_name.startswith("@")
            else worker_name
        )
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(address)
            server.listen(1)
            while True:
                connection, _ = server.accept()
                with connection:
                    request_stream = connection.makefile("r", encoding="utf-8")
                    response_stream = connection.makefile("w", encoding="utf-8")
                    request = json.loads(request_stream.readline())
                    if request.get("ping"):
                        response_stream.write(
                            json.dumps({"ok": True, "pong": True}) + "\n"
                        )
                        response_stream.flush()
                        continue
                    if request.get("shutdown"):
                        response_stream.write(
                            json.dumps({"ok": True, "shutdown": True}) + "\n"
                        )
                        response_stream.flush()
                        return
                    try:
                        if request.get("op") == "canonicalize":
                            from motion_edit.generation.newton_direct_fk import (
                                canonicalize_motion_with_direct_newton_fk,
                            )

                            canonical = canonicalize_motion_with_direct_newton_fk(
                                **dict(request["kwargs"])
                            )
                            response = {
                                "ok": True,
                                "canonical": {
                                    "output_path": str(canonical.output_path),
                                    "body_names": list(canonical.body_names),
                                    "joint_names": list(canonical.joint_names),
                                    "frame_count": canonical.frame_count,
                                    "backend_metadata": canonical.backend_metadata,
                                },
                            }
                            response_stream.write(
                                json.dumps(response) + "\n"
                            )
                            response_stream.flush()
                            continue
                        output = solve_pyroki_fullbody_ik(
                            **dict(request["kwargs"])
                        )
                    except Exception:
                        response = {
                            "ok": False,
                            "traceback": traceback.format_exc(),
                        }
                    else:
                        response = {"ok": True, "output": str(output)}
                    response_stream.write(json.dumps(response) + "\n")
                    response_stream.flush()
        return
    parser = argparse.ArgumentParser(description="Solve contact-aware fullbody trajectory IK with PyRoki.")
    parser.add_argument("--lte", default=None, help="Legacy LTE keypoints or ContactAwareTaskspaceMotion NPZ.")
    parser.add_argument("--taskspace-spec", default=None, help="Explicit ContactAwareTaskspaceMotion NPZ.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--robot-urdf", default=str(DEFAULT_ROBOT_URDF))
    parser.add_argument("--source-motion", default=None)
    parser.add_argument("--max-nfev", type=int, default=25)
    parser.add_argument("--q-prior-weight", type=float, default=0.25)
    parser.add_argument("--q-smooth-weight", type=float, default=0.5)
    parser.add_argument("--boundary-pin-weight", type=float, default=2.0)
    parser.add_argument("--edited-contact-weight", type=float, default=100.0)
    parser.add_argument("--fixed-contact-weight", type=float, default=80.0)
    parser.add_argument("--foot-orientation-weight", type=float, default=20.0)
    parser.add_argument("--q-velocity-weight", type=float, default=2.0)
    parser.add_argument("--q-acceleration-weight", type=float, default=1.0)
    parser.add_argument(
        "--collision-similarity-weight",
        "--collision-penetration-depth-weight",
        dest="collision_similarity_weight",
        metavar="WEIGHT",
        type=float,
        default=25.0,
    )
    parser.add_argument(
        "--collision-max-refinements",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--self-collision-weight",
        type=float,
        default=20_000.0,
    )
    parser.add_argument(
        "--collision-reference-cache",
        default=None,
        help=(
            "Reusable fail-closed cache for source-rollout Newton signed "
            "distances. Share this path across variants of one source."
        ),
    )
    # Compatibility arguments retained for existing callers. Contact patch points
    # replace the old contact-only toe/orientation pseudo-targets.
    parser.add_argument("--contact-foot-orientation-weight", type=float, default=80.0)
    parser.add_argument("--foot-toe-weight", type=float, default=20.0)
    parser.add_argument("--contact-foot-toe-weight", type=float, default=120.0)
    args = parser.parse_args(argv)
    input_path = args.taskspace_spec or args.lte
    if input_path is None:
        parser.error("one of --lte or --taskspace-spec is required")
    solve_pyroki_fullbody_ik(
        lte_path=input_path,
        output_path=args.out,
        robot_urdf=args.robot_urdf,
        source_motion_path=args.source_motion,
        max_nfev=args.max_nfev,
        q_prior_weight=args.q_prior_weight,
        q_smooth_weight=args.q_smooth_weight,
        boundary_pin_weight=args.boundary_pin_weight,
        edited_contact_weight=args.edited_contact_weight,
        fixed_contact_weight=args.fixed_contact_weight,
        foot_orientation_weight=args.foot_orientation_weight,
        q_velocity_weight=args.q_velocity_weight,
        q_acceleration_weight=args.q_acceleration_weight,
        collision_similarity_weight=args.collision_similarity_weight,
        collision_max_refinements=args.collision_max_refinements,
        self_collision_weight=args.self_collision_weight,
        collision_reference_cache_path=args.collision_reference_cache,
    )


if __name__ == "__main__":
    main()
