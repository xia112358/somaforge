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
        if compiled.unresolved_semantics or compiled.unresolved_contacts:
            raise ValueError(
                f"Taskspace contains unresolved robot mappings: semantics={compiled.unresolved_semantics}, "
                f"contacts={compiled.unresolved_contacts}; regenerate from the canonical asset"
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

    raise ValueError("Legacy LTE keypoints are no longer supported; regenerate a versioned contact-aware taskspace with generate-ref")


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
    if "contact_aware_taskspace_json" not in payload:
        raise ValueError("Legacy LTE keypoints are no longer supported; regenerate with generate-ref")
    from motion_edit.generation.contract import validate_generation_metadata
    validate_generation_metadata(ContactAwareTaskspaceMotion.from_arrays(payload).metadata)
    if Path(robot_urdf).expanduser().resolve() != canonical_g1_urdf_path().resolve():
        raise ValueError("Generation requires the canonical G1 robot asset")
    collision_spec: ContactAwareTaskspaceMotion | None = None
    collision_terrain_mesh: str | None = None
    collision_source_terrain_mesh: str | None = None
    collision_reference_motion_path: str | None = None
    if "contact_aware_taskspace_json" in payload:
        collision_spec = ContactAwareTaskspaceMotion.from_arrays(payload)
        collision_metadata = dict(collision_spec.metadata)
        if (collision_metadata.get('native_hard_release') or {}).get('geometry_file'):
            # Set precision before source FK as well, independent of CLI env.
            jax.config.update('jax_enable_x64', True)
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
    support_source_root = root_source.copy()
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

    # Opt-in task condition, never inferred from or written into contact labels.
    yaw_condition = (collision_spec.metadata.get("root_yaw_condition")
                     if collision_spec is not None else None)
    yaw_enabled = yaw_condition is not None
    root_dofs = 4 if yaw_enabled else 3
    if yaw_enabled:
        yaw_degrees = float(yaw_condition["reference_delta_degrees"])
        initial_q = np.asarray(yaw_condition["initial_qpos"], dtype=np.float64)
        if not np.isfinite(yaw_degrees) or initial_q.shape != (7 + actuated_count,) or not np.isfinite(initial_q).all():
            raise ValueError("Invalid explicit root yaw/initial pose condition")
        if not np.isclose(np.linalg.norm(initial_q[3:7]), 1., atol=1.e-5):
            raise ValueError("Initial root quaternion must be normalized")
        yaw_rotation = Rotation.from_euler("z", yaw_degrees, degrees=True)
        rotations = Rotation.from_quat(root_source[:, [4, 5, 6, 3]])
        root_source[:, 3:7] = (yaw_rotation * rotations).as_quat()[:, [3, 0, 1, 2]]
        # The edited trajectory owns its initial frame too. Splicing a
        # separately prescribed root into frame zero can create a jump to
        # the independently optimized frame one.
        # The initial pose is retained as provenance, not an incompatible pin.

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
    free_surface_contacts = bool(collision_spec is not None and collision_spec.metadata.get("free_surface_contacts"))
    from motion_edit.generation.contract import validate_generation_metadata
    validate_generation_metadata(collision_spec.metadata if collision_spec else {})
    objective_version = 'consolidated_v1'
    if not free_surface_contacts:
        raise ValueError('Consolidated objective requires compiled surface contact tasks')
    from motion_edit.generation.surface_contact_loss import compile_surface_faces, surface_residual, endpoint_surface_residual
    surface_reference_ratio = float(collision_spec.metadata.get("surface_reference_ratio", 0.01)) if free_surface_contacts else 0.
    if free_surface_contacts:
        if not 0 <= surface_reference_ratio < 1:
            raise ValueError("Surface reference must be weaker than normal contact constraint")
        surface_normals_w, surface_edges_w, surface_offsets_w = compile_surface_faces(collision_spec, compiled, link_names)
    support_mask = np.zeros_like(compiled.contact_weights, dtype=bool)
    support_orientation_projectors = np.zeros((*support_mask.shape,3,3))
    support_episodes = []
    support_orientation_targets = None
    support_approach_seconds = float(collision_spec.metadata.get('support_approach_seconds', 0.0)) if free_surface_contacts else 0.0
    if not np.isfinite(support_approach_seconds) or support_approach_seconds < 0:
        raise ValueError('Support approach duration must be finite and nonnegative')
    approach_data = (np.zeros((n_frames,1),np.int32), np.zeros((n_frames,1,3)), np.zeros((n_frames,1,3)), np.zeros((n_frames,1)), np.full((n_frames,1),-1), np.zeros((n_frames,1)))
    approach_start_offsets = {}
    approach_start_rotation_offsets = {}
    approach_orientation_enabled = bool(collision_spec.metadata.get("support_approach_orientation", True)) if free_surface_contacts else False
    support_rotation_policy = collision_spec.metadata.get('support_rotation_policy', 'episode_yaw') if free_surface_contacts else None
    support_origin_policy = collision_spec.metadata.get('support_origin_policy', 'median') if free_surface_contacts else None
    if free_surface_contacts and support_rotation_policy not in ('episode_yaw', 'authored_surface'):
        raise ValueError('Unknown support rotation policy')
    support_residual_scale = float(collision_spec.metadata.get("support_residual_scale", 100.0)) if free_surface_contacts else 0.0
    if free_surface_contacts and (not np.isfinite(support_residual_scale) or support_residual_scale <= 0):
        raise ValueError("Support residual scale must be finite and positive")
    if free_surface_contacts:
        from motion_edit.generation.support_motion import compile_support_motion, authored_support_targets, orientation_completion_projectors
        source_root_rotation = Rotation.from_quat(support_source_root[:, [4, 5, 6, 3]]).as_matrix()
        source_link_rotation = Rotation.from_quat(source_fk[..., [1, 2, 3, 0]].reshape(-1,4)).as_matrix().reshape(*source_fk.shape[:2],3,3)
        source_world_rotation = source_root_rotation[:,None] @ source_link_rotation
        source_world_position = support_source_root[:,None,:3] + np.einsum('tij,tnj->tni', source_root_rotation, source_fk[...,4:7])
        authored_targets, support_edit_rotations = authored_support_targets(
            collision_spec, compiled, link_names, source_world_position, source_world_rotation,
            return_rotations=True)
        if support_rotation_policy == 'episode_yaw':
            support_edit_rotations = np.broadcast_to(
                yaw_rotation.as_matrix() if yaw_enabled else np.eye(3), support_edit_rotations.shape)
        support_targets, support_mask, support_episodes = compile_support_motion(
            compiled, link_names, source_world_position, source_world_rotation,
            support_edit_rotations, surface_normals_w, authored_targets, origin_policy=support_origin_policy)
        target_world_rotation = support_edit_rotations @ source_world_rotation[
            np.arange(len(compiled.contact_link_indices))[:, None], compiled.contact_link_indices]
        edited_root_rotation = Rotation.from_quat(root_source[:, [4, 5, 6, 3]]).as_matrix()
        target_base_rotation = edited_root_rotation[:, None].transpose(0, 1, 3, 2) @ target_world_rotation
        support_orientation_targets = Rotation.from_matrix(target_base_rotation.reshape(-1, 3, 3)).as_quat()[:, [3, 0, 1, 2]].reshape(*support_mask.shape, 4)
        compiled.contact_targets_w[:] = support_targets
        support_orientation_projectors = orientation_completion_projectors(
            compiled, link_names, source_world_position, source_world_rotation, support_mask)
        from motion_edit.generation.support_motion import compile_support_approach
        approach_data = compile_support_approach(compiled, link_names, source_world_position,
            source_world_rotation, support_edit_rotations, support_targets, support_episodes,
            round(support_approach_seconds*fps))
    from motion_edit.generation.support_motion import (
        compile_approach_orientation, blend_orientation_target, temporal_history_mask)
    approach_rotations = np.broadcast_to(np.eye(3), (*approach_data[0].shape, 3, 3)).copy()
    approach_projectors = np.zeros_like(approach_rotations)
    if free_surface_contacts and approach_orientation_enabled:
        approach_rotations, approach_projectors = compile_approach_orientation(
            approach_data, compiled, support_episodes, source_world_rotation,
            support_edit_rotations, support_orientation_projectors)
    # The consolidated surface task already enforces the finite footprint;
    # a second set of per-frame landing coordinates is unnecessary.
    convex_mode = False  # Endpoint surface tasks replace the retired convex-variable objective.
    if collision_spec.metadata.get("convex_surface_targets"):
        # Preserve the baseline temporal coefficient when eliminating only
        # its auxiliary landing coordinates.
        q_acceleration_weight = max(float(q_acceleration_weight), 2.0)
    from motion_edit.generation.surface_contact_loss import compile_bounded_face_targets, bounded_face_targets as convex_targets, contact_previous_slots, contact_temporal_residual
    cfg_stop = root_dofs + actuated_count
    coefficient_count = 0
    if convex_mode:
        convex_vertices_w, convex_valid, convex_finite, initial_logits = compile_bounded_face_targets(collision_spec, compiled)
        coefficient_shape = initial_logits.shape[1:]
        coefficient_count = int(np.prod(coefficient_shape))
        solved_logits = np.zeros_like(initial_logits[:n_frames])
        previous_slots = contact_previous_slots(collision_spec, compiled)
        solved_target_corrections_w = np.zeros((*convex_finite[:n_frames].shape,3))
        # Reuse the existing demonstration-relative joint acceleration residual.
        # Free landing points add freedom at contact transitions; retain posture
        # continuity there without extending contact activation into flight.
        q_acceleration_weight = max(float(q_acceleration_weight), 2.0)
    solve_attempts = []
    from motion_edit.generation.release_witness_loss import compile_release_witnesses, release_residual
    release_data = compile_release_witnesses(
        collision_spec.metadata if collision_spec is not None else {}, list(link_names), n_frames)
    hard_release = collision_spec.metadata.get('native_hard_release') if collision_spec else None
    hard_mask = None
    hard_query_calls = 0
    release_geometry = None
    geometry_jacobian_calls = 0
    if hard_release:
        from somaforge_core.newton_contact_data import load_contact_labels
        hard_labels = load_contact_labels(Path(source_path), Path(hard_release['source_labels']))
        hard_mask = hard_labels['contact_part_mask']
        if hard_mask.shape != (n_frames, 6):raise ValueError('Hard release source frame mismatch')
        if np.any(release_data[-1]):raise ValueError('Hard release cannot consume feedback witnesses')
        if hard_release.get('geometry_file'):
            from motion_edit.generation.native_geometry_release import GeometryRelease
            release_geometry = GeometryRelease(hard_release['geometry_file'], hard_release['model_fingerprint'], list(link_names))

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
        root_yaw_axis_base: Any,
        surface_normals_base: Any,
        surface_edges_base: Any,
        surface_offsets_base: Any,
        convex_vertices_base: Any,
        convex_valid_frame: Any,
        convex_finite_frame: Any,
        contact_previous_correction: Any,
        contact_previous_previous_correction: Any,
        contact_velocity_mask: Any,
        contact_acceleration_mask: Any,
        release_indices: Any,
        release_points: Any,
        release_targets: Any,
        release_normals: Any,
        release_weights: Any,
        support_weight: Any,
        support_orientation: Any,
        approach_indices: Any,
        approach_points: Any,
        approach_targets: Any,
        approach_weights: Any,
        approach_orientation: Any,
        history_mask: Any,
    ) -> Any:
        root_state = solve_state[:root_dofs]
        root_delta = root_state[:3]
        q_cfg = solve_state[root_dofs:cfg_stop]
        fk = robot.forward_kinematics(q_cfg)
        if yaw_enabled:
            half = root_state[3] * .5
            yaw_q = jnp.concatenate((jnp.cos(half)[None], root_yaw_axis_base * jnp.sin(half)))
            original_q = fk[:, :4]
            w = yaw_q[0] * original_q[:, :1] - jnp.sum(yaw_q[1:] * original_q[:, 1:], axis=-1, keepdims=True)
            xyz = yaw_q[0] * original_q[:, 1:] + original_q[:, :1] * yaw_q[1:] + jnp.cross(yaw_q[1:], original_q[:, 1:])
            fk = jnp.concatenate((w, xyz, quat_apply_jax(yaw_q, fk[:, 4:7])), axis=-1)
        semantic_pos = fk[semantic_indices_jax, 4:7] + root_delta
        semantic_res = ((semantic_pos - semantic_target_base) * semantic_sqrt_weight[:, None]).reshape(-1)

        contact_pose = fk[contact_link_indices]
        contact_pred = (
            contact_pose[:, 4:7]
            + quat_apply_jax(contact_pose[:, :4], contact_points_local)
            + root_delta
        )
        contact_res = ((contact_pred - contact_target_base) * contact_sqrt_weight[:, None]).reshape(-1)
        if free_surface_contacts:
            contact_res = surface_residual(contact_pred, contact_target_base, surface_normals_base,
                surface_edges_base, surface_offsets_base, contact_sqrt_weight, surface_reference_ratio, xp=jnp)
            contact_res = endpoint_surface_residual(contact_pred, contact_target_base, surface_normals_base,
                surface_edges_base, surface_offsets_base, contact_sqrt_weight, support_weight,
                surface_reference_ratio, xp=jnp)
        if convex_mode:
            target, _ = convex_targets(solve_state[cfg_stop:].reshape(coefficient_shape),
                                       convex_vertices_base, convex_valid_frame, xp=jnp)
            # Normal reference clearance remains the verified Newton source's.
            # Only the surface footprint is parametrized by convex coefficients.
            error = contact_pred-target
            tangent = error-jnp.sum(error*surface_normals_base,axis=-1)[:,None]*surface_normals_base
            landing_weight = contact_sqrt_weight * convex_finite_frame
            landing_weight = landing_weight * (support_weight <= 0)
            contact_res = jnp.concatenate((contact_res,
                (tangent*landing_weight[:,None]).reshape(-1)))
            correction = target-contact_target_base
            correction = correction-jnp.sum(correction*surface_normals_base,axis=-1)[:,None]*surface_normals_base
            # Landing-point continuity is a weak tie-breaker, not a persistent
            # pin that stores posture error until contact release. Joint-space
            # demonstration-relative smoothness remains the primary temporal term.

        approach_pose = fk[approach_indices]
        approach_pred = approach_pose[:,4:7]+quat_apply_jax(approach_pose[:,:4], approach_points)+root_delta
        approach_res = ((approach_pred-approach_targets)*approach_weights[:,None]).reshape(-1)
        approach_q = approach_pose[:, :4]
        approach_target_q = approach_orientation[:, :4]
        approach_rotation_error = (
            approach_target_q[:, :1] * approach_q[:, 1:]
            - approach_q[:, :1] * approach_target_q[:, 1:]
            - jnp.cross(approach_target_q[:, 1:], approach_q[:, 1:]))
        approach_rotation_free = jnp.einsum('nij,nj->ni',
            approach_orientation[:, 4:].reshape(-1, 3, 3), approach_rotation_error)
        approach_res = jnp.concatenate((approach_res,
            (2.0 * approach_rotation_free * approach_weights[:, None]).reshape(-1)))
        # A single material point leaves rotation unconstrained, notably for
        # spherical hands. Keep the demonstrated rigid endpoint orientation
        # during support as well; do not apply this term in flight.
        current_orientation = contact_pose[:, :4]
        target_orientation = support_orientation[:, :4]
        orientation_error = (
            target_orientation[:, :1] * current_orientation[:, 1:]
            - current_orientation[:, :1] * target_orientation[:, 1:]
            - jnp.cross(target_orientation[:, 1:], current_orientation[:, 1:])
        )
        orientation_free = jnp.einsum('nij,nj->ni',support_orientation[:,4:].reshape(-1,3,3),orientation_error)
        support_orientation_res = (2.0*orientation_free*support_weight[:,None]).reshape(-1)
        prior_res = (q_cfg - q_prior) * q_prior_scale
        velocity_res = (
            (q_cfg - q_previous) - (q_prior - q_prior_previous)
        ) * float(q_velocity_weight) * history_mask[0]
        acceleration_res = (
            (q_cfg - 2.0 * q_previous + q_previous_previous)
            - (q_prior - 2.0 * q_prior_previous + q_prior_previous_previous)
        ) * float(q_acceleration_weight) * history_mask[1]

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
        )
        # Material tasks already determine support orientation. Match by
        # endpoint so toe/heel shape switches do not reactivate a second prior.
        from motion_edit.generation.support_motion import endpoint
        endpoint_groups = jnp.asarray([
            [endpoint(name) == endpoint(link_names[index]) for name in link_names]
            for index in foot_orientation_indices])
        supported_feet = jnp.any(endpoint_groups[:, contact_link_indices] & (support_weight[None, :] > 0), axis=1)
        foot_orientation_res = foot_orientation_res * (~supported_feet[:, None])
        foot_orientation_res = foot_orientation_res.reshape(-1)
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
        root_delta_prior_res = root_state * np.sqrt(25.0)
        release_pose = fk[release_indices]
        release_pred = release_pose[:, 4:7] + quat_apply_jax(release_pose[:, :4], release_points) + root_delta
        release_res = release_residual(release_pred, release_targets, release_normals, release_weights, xp=jnp)
        root_delta_velocity_res = (
            root_state - root_delta_previous
        ) * np.sqrt(100.0) * history_mask[0]
        root_delta_acceleration_res = (
            root_state
            - 2.0 * root_delta_previous
            + root_delta_previous_previous
        ) * np.sqrt(400.0) * history_mask[1]
        # Four responsibilities: endpoint tasks, pose reference, correction
        # continuity, and collision. No duplicate support XYZ, absolute
        # motion penalty, or attraction to collision witness planes.
        endpoint_res = jnp.concatenate((contact_res, approach_res, support_orientation_res))
        pose_res = jnp.concatenate((semantic_res, prior_res, foot_orientation_res, root_delta_prior_res))
        temporal_res = jnp.concatenate((velocity_res, acceleration_res,
                                        root_delta_velocity_res, root_delta_acceleration_res))
        safety_res = jnp.concatenate((collision_deeper_res, self_collision_res, release_res))
        return jnp.concatenate((endpoint_res, pose_res, temporal_res, safety_res))

    residual_compiled = jax.jit(residual_jax)
    jac_compiled = jax.jit(jax.jacfwd(residual_jax, argnums=0))

    def native_projection(x, indices, local_points, normals, yaw_axis):
        fk = robot.forward_kinematics(x[root_dofs:cfg_stop])[indices]
        points = fk[:,4:7]+quat_apply_jax(fk[:,:4],local_points)
        if yaw_enabled:
            half=x[3]*.5
            rotation=jnp.concatenate((jnp.cos(half)[None],yaw_axis*jnp.sin(half)))
            points=quat_apply_jax(rotation,points)
        return jnp.sum((points+x[:3])*normals,axis=-1)
    native_projection_jac=jax.jit(jax.jacfwd(native_projection,argnums=0))
    if release_geometry is not None:
        geometry_fk = jax.jit(lambda cfg: robot.forward_kinematics(cfg))
        geometry_jac_capacity = int(release_geometry.allowed.size)

    out_cfg = np.zeros((n_frames, actuated_count), dtype=np.float64)
    out_root_delta_base = np.zeros((n_frames, root_dofs), dtype=np.float64)
    q_previous = cfg_source[0]
    q_previous_previous = cfg_source[0]
    root_delta_previous = np.zeros(root_dofs, dtype=np.float64)
    root_delta_previous_previous = np.zeros(root_dofs, dtype=np.float64)
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
    collision_similarity_weight_value = 0.0
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
    if yaw_enabled:
        # Existing translation limits unchanged; yaw is an additional radian DOF.
        solve_lower = np.concatenate((solve_lower[:3], [-np.pi], lower))
        solve_upper = np.concatenate((solve_upper[:3], [np.pi], upper))
    if convex_mode:
        solve_lower = np.r_[solve_lower, np.zeros(coefficient_count)]
        solve_upper = np.r_[solve_upper, np.ones(coefficient_count)]
    normal_solve_lower, normal_solve_upper = solve_lower.copy(), solve_upper.copy()
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
        if hard_release and frame % 100 == 0:
            mode='geometry-release' if release_geometry is not None else 'native-hard-release'
            print(f'{mode} frame={frame}/{n_frames} evaluations={hard_query_calls}',flush=True)
        root = root_source[frame].copy()
        root_rotation = _quat_wxyz_to_rotation(root[3:7])
        root_yaw_axis_base = root_rotation.inv().apply([0., 0., 1.])
        surface_args = (np.zeros((1, 3)), np.zeros((1, 1, 3)), np.zeros((1, 1)))
        convex_args = (np.zeros((1,3,3)),np.ones((1,3),bool),np.zeros(1,bool))
        coefficient_initial = np.empty(0)
        temporal_args = (np.zeros((1,3)),np.zeros((1,3)),np.zeros(1),np.zeros(1))
        if convex_mode:
            convex_args = (root_rotation.inv().apply((convex_vertices_w[frame]-root[:3]).reshape(-1,3)).reshape(convex_vertices_w[frame].shape),
                           convex_valid[frame],convex_finite[frame])
            warm = initial_logits[frame].copy()
            previous_correction = np.zeros((len(warm),3)); previous_previous_correction = previous_correction.copy()
            velocity_mask = np.zeros(len(warm)); acceleration_mask = velocity_mask.copy()
            if frame > 0:
                for slot, old in enumerate(previous_slots[frame]):
                    if old < 0 or not convex_finite[frame,slot] or not convex_finite[frame-1,old]: continue
                    if not np.array_equal(convex_vertices_w[frame,slot],convex_vertices_w[frame-1,old]):
                        raise ValueError('Persistent contact changed face parameterization')
                    warm[slot] = solved_logits[frame-1,old]
                    previous_correction[slot] = solved_target_corrections_w[frame-1,old]
                    velocity_mask[slot] = 1.
                    older = previous_slots[frame-1,old]
                    if frame > 1 and older >= 0 and convex_finite[frame-2,older]:
                        previous_previous_correction[slot] = solved_target_corrections_w[frame-2,older]
                        acceleration_mask[slot] = 1.
            coefficient_initial = warm.reshape(-1)
            temporal_args = (root_rotation.inv().apply(previous_correction),root_rotation.inv().apply(previous_previous_correction),velocity_mask,acceleration_mask)
        if free_surface_contacts:
            surface_args = (
                root_rotation.inv().apply(surface_normals_w[frame]),
                root_rotation.inv().apply(surface_edges_w[frame].reshape(-1, 3)).reshape(surface_edges_w[frame].shape),
                surface_offsets_w[frame]-np.sum(surface_edges_w[frame]*root[:3], axis=-1),
            )
        solve_lower, solve_upper = normal_solve_lower.copy(), normal_solve_upper.copy()
        # Frame zero must satisfy the same edited support targets as later
        # frames. Pinning it before IK creates a discontinuity at frame one.
        semantic_target_base = root_rotation.inv().apply(
            compiled.semantic_targets_w[frame] - root[:3][None, :]
        )
        contact_target_base = root_rotation.inv().apply(
            compiled.contact_targets_w[frame] - root[:3][None, :]
        )
        semantic_sqrt_weight = np.sqrt(np.maximum(compiled.semantic_weights[frame], 0.0))
        contact_sqrt_weight = np.sqrt(np.maximum(compiled.contact_weights[frame], 0.0))
        approach_goals = approach_data[2][frame].copy()
        approach_rotation_goals = approach_rotations[frame].copy()
        if np.any(approach_data[4][frame] >= 0):
            previous_frame = max(0,frame-1)
            previous_root = root_source[previous_frame].copy()
            previous_rotation = _quat_wxyz_to_rotation(previous_root[3:7])
            previous_root[:3] += previous_rotation.apply(root_delta_previous[:3])
            if yaw_enabled:
                previous_root[3:7] = (Rotation.from_rotvec([0.,0.,root_delta_previous[3]])*previous_rotation).as_quat()[[3,0,1,2]]
            previous_fk = np.asarray(robot.forward_kinematics(jnp.asarray(q_previous)))
            previous_positions,previous_quaternions = world_body_poses_from_pyroki_fk(previous_root[None],previous_fk[None])
            for slot,identity in enumerate(approach_data[4][frame]):
                if identity < 0:
                    continue
                if identity not in approach_start_offsets:
                    link = approach_data[0][frame,slot]
                    actual = previous_positions[0,link]+quat_apply_wxyz(previous_quaternions[0,link],approach_data[1][frame,slot])
                    approach_start_offsets[identity] = actual-approach_goals[slot]
                approach_goals[slot] += (1.-approach_data[5][frame,slot])*approach_start_offsets[identity]
                if identity not in approach_start_rotation_offsets:
                    link = approach_data[0][frame,slot]
                    actual_rotation = _quat_wxyz_to_rotation(previous_quaternions[0,link]).as_matrix()
                    approach_start_rotation_offsets[identity] = Rotation.from_matrix(
                        actual_rotation @ approach_rotation_goals[slot].T).as_rotvec()
                approach_rotation_goals[slot] = blend_orientation_target(
                    approach_rotation_goals[slot], approach_start_rotation_offsets[identity],
                    approach_data[5][frame,slot])

        approach_target_base = root_rotation.inv().apply(approach_goals-root[:3])
        approach_orientation_frame = np.column_stack((
            Rotation.from_matrix(root_rotation.as_matrix().T @ approach_rotation_goals).as_quat()[:, [3,0,1,2]],
            approach_projectors[frame].reshape(-1,9)))

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
                    coefficient_initial,
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
            np.asarray(root_yaw_axis_base, dtype=np.float64),
            *surface_args,
            *convex_args,
            *temporal_args,
            release_data[0][frame],
            release_data[1][frame],
            root_rotation.inv().apply(release_data[2][frame] - root[:3]),
            root_rotation.inv().apply(release_data[3][frame]),
            release_data[4][frame],
            support_residual_scale * contact_sqrt_weight * support_mask[frame],
            np.column_stack((support_orientation_targets[frame] if free_surface_contacts else source_fk[frame, compiled.contact_link_indices[frame], :4], support_orientation_projectors[frame].reshape(-1,9))),
            approach_data[0][frame], approach_data[1][frame],
            approach_target_base,
            support_residual_scale*approach_data[3][frame],
                approach_orientation_frame, temporal_history_mask(frame),
        )

        args_jax = tuple(jnp.asarray(value) for value in args)

        def fun(x: np.ndarray) -> np.ndarray:
            return np.asarray(residual_compiled(jnp.asarray(x), *args_jax))

        def jac(x: np.ndarray) -> np.ndarray:
            return np.asarray(jac_compiled(jnp.asarray(x), *args_jax))

        frame_fixed_coefficients = None
        active_solve_indices = np.arange(len(x0))
        if convex_mode:
            active_coefficients = np.flatnonzero(np.repeat(convex_finite[frame],coefficient_shape[-1]))
            active_solve_indices = np.r_[np.arange(cfg_stop), cfg_stop+active_coefficients]

        def solve_frame(start):
            nonlocal frame_fixed_coefficients
            if not convex_mode:
                # Keep the established solver path, including Jacobian layout,
                # untouched when the new landing-point variables are disabled.
                return least_squares(fun,start,jac=jac,bounds=(solve_lower,solve_upper),
                    max_nfev=int(max_nfev),xtol=1.e-5,ftol=1.e-5,gtol=1.e-5)
            original_start = start.copy()
            total_nfev = 0
            for attempt in range(0 if frame_fixed_coefficients is not None else (4 if convex_mode else 1)):
                template = start.copy()
                def expand(value):
                    full = template.copy(); full[active_solve_indices] = value
                    return full
                solved = least_squares(lambda value:fun(expand(value)),start[active_solve_indices],
                    jac=lambda value:jac(expand(value))[:,active_solve_indices],
                    bounds=(solve_lower[active_solve_indices],solve_upper[active_solve_indices]),
                    max_nfev=int(max_nfev),xtol=1.e-5,ftol=1.e-5,gtol=1.e-5)
                solved.x = expand(solved.x)
                total_nfev += int(solved.nfev)
                if convex_mode:
                    solve_attempts.append(dict(frame=frame,attempt=attempt,success=bool(solved.success),
                        status=int(solved.status),cost=float(solved.cost),nfev=int(solved.nfev)))
                if solved.success: break
                start = solved.x
            if convex_mode and (frame_fixed_coefficients is not None or not solved.success):
                # Reuse the established fixed-target pose solve. Never freeze q,
                # silently accept failure, or project the generated posture.
                if frame_fixed_coefficients is None:
                    frame_fixed_coefficients = original_start[cfg_stop:].copy()
                def reduced_fun(value):return fun(np.r_[value, frame_fixed_coefficients])
                def reduced_jac(value):return jac(np.r_[value, frame_fixed_coefficients])[:,:cfg_stop]
                reduced_start = original_start[:cfg_stop]
                for attempt in range(4):
                    reduced = least_squares(reduced_fun,reduced_start,jac=reduced_jac,
                        bounds=(solve_lower[:cfg_stop],solve_upper[:cfg_stop]),max_nfev=int(max_nfev),
                        xtol=1.e-5,ftol=1.e-5,gtol=1.e-5)
                    total_nfev += int(reduced.nfev)
                    solve_attempts.append(dict(frame=frame,attempt=attempt,mode='fixed_target_fallback',
                        success=bool(reduced.success),status=int(reduced.status),cost=float(reduced.cost),nfev=int(reduced.nfev)))
                    if reduced.success:break
                    reduced_start = reduced.x
                reduced.x = np.r_[reduced.x, frame_fixed_coefficients]
                solved = reduced
            if convex_mode and (not solved.success or not np.isfinite(solved.x).all()):
                raise RuntimeError(f'Frame {frame}: convex contact solve did not converge after retries; refusing trajectory output')
            solved.nfev = total_nfev
            return solved

        if hard_release:
            from scipy.optimize import minimize, OptimizeResult
            from somaforge_core.motion_schema import G1_29DOF_JOINT_ORDER
            from motion_edit.generation.native_release_constraint import NativeReleaseConstraint
            canonical_slots=[robot_joint_names.index(n) for n in G1_29DOF_JOINT_ORDER]

            def hard_candidate_root(x):
                value=root.copy()
                value[:3]+=root_rotation.apply(x[:3])
                if yaw_enabled:value[3:7]=(Rotation.from_rotvec([0.,0.,x[3]])*root_rotation).as_quat()[[3,0,1,2]]
                return value

            def state_to_q(x):
                return np.r_[hard_candidate_root(x),x[root_dofs:cfg_stop][canonical_slots]]

            def native_witness_jac(x, pairs, model):
                fk=np.asarray(robot.forward_kinematics(jnp.asarray(x[root_dofs:cfg_stop])))
                bp,bq=world_body_poses_from_pyroki_fk(hard_candidate_root(x)[None,:],fk[None,...])
                indices=np.zeros(6,np.int32);local=np.zeros((6,3));normals=np.zeros((6,3))
                for p,pair in enumerate(pairs):
                    if pair is None:continue
                    if 'normal_w' not in pair:raise ValueError('Native normal missing; no witness fallback')
                    body=model['body_labels'][pair['body']].rsplit('/',1)[-1]
                    i=link_names.index(body);indices[p]=i
                    normal=np.asarray(pair['normal_w'])
                    point=np.asarray(pair['solver_position_w'])+.5*pair['dist']*normal
                    local[p]=_quat_wxyz_to_rotation(bq[0,i]).inv().apply(point-bp[0,i])
                    normals[p]=root_rotation.inv().apply(normal)
                return np.asarray(native_projection_jac(jnp.asarray(x),jnp.asarray(indices),
                    jnp.asarray(local),jnp.asarray(normals),jnp.asarray(root_yaw_axis_base)),dtype=np.float64)

            native_constraint=NativeReleaseConstraint(hard_mask[frame],hard_release['model_fingerprint'],state_to_q,native_witness_jac)
            if release_geometry is not None:
                from motion_edit.generation.native_geometry_release import FastFrameGeometryConstraint
                def geometry_forward_vertices(x, shapes):
                    fk=np.asarray(geometry_fk(jnp.asarray(x[root_dofs:cfg_stop])))[release_geometry.indices[shapes]]
                    local=release_geometry.vertices[shapes]
                    q=fk[:,None,:4]; uv=np.cross(q[...,1:],local)
                    points=local+2.*(q[...,:1]*uv+np.cross(q[...,1:],uv))+fk[:,None,4:7]
                    if yaw_enabled:
                        rotation=Rotation.from_rotvec(root_yaw_axis_base*x[3])
                        points=rotation.apply(points.reshape(-1,3)).reshape(points.shape)
                    return root_rotation.apply((points+x[:3]).reshape(-1,3)).reshape(points.shape)+root[:3]

                def geometry_support_jac(x, indices, local, normals):
                    # One static executable; only cfg/root columns, never face
                    # coordinates. Inactive rows have zero derivative normals.
                    count=len(indices); capacity=geometry_jac_capacity
                    ii=np.zeros(capacity,np.int32);pp=np.zeros((capacity,3));nn=np.zeros((capacity,3))
                    ii[:count]=indices;pp[:count]=local
                    nn[:count]=root_rotation.inv().apply(normals)
                    return np.asarray(native_projection_jac(jnp.asarray(x),jnp.asarray(ii),
                        jnp.asarray(pp),jnp.asarray(nn),jnp.asarray(root_yaw_axis_base)),np.float64)[:count]

                native_constraint=FastFrameGeometryConstraint(release_geometry,hard_mask[frame],
                    cfg_stop,geometry_forward_vertices,geometry_support_jac)
            constraint_name='geometry-release' if release_geometry is not None else 'native-hard-release'
            unconstrained_solve_frame=solve_frame

            def solve_frame(start):
                initial=unconstrained_solve_frame(start)
                if native_constraint.feasible(initial.x):return initial
                slots=active_solve_indices
                template=np.asarray(initial.x,dtype=np.float64).copy()
                def expand(v):
                    full=template.copy();full[slots]=v;return full
                objective_cache={}
                def objective(v):
                    if 'v' not in objective_cache or not np.array_equal(v,objective_cache['v']):
                        x=expand(v);r=fun(x)
                        objective_cache.clear()
                        objective_cache.update(v=v.copy(),x=x,r=r,value=float(.5*np.dot(r,r)))
                    return objective_cache['value']
                def objective_jac(v):
                    objective(v)
                    if 'gradient' not in objective_cache:
                        objective_cache['gradient']=np.asarray(jac(objective_cache['x'])[:,slots].T@objective_cache['r'],dtype=np.float64)
                    return objective_cache['gradient']
                solved=minimize(objective,template[slots],jac=objective_jac,method='SLSQP',
                    bounds=list(zip(solve_lower[slots],solve_upper[slots])),
                    # Express separation in millimetres for SQP conditioning;
                    # this does not change the native activation boundary.
                    constraints=[dict(type='ineq',fun=lambda v:1000.*native_constraint.fun(expand(v)),
                        jac=lambda v:1000.*native_constraint.jac(expand(v))[:,slots])],
                    options=dict(maxiter=int(hard_release.get('sqp_maxiter', 150)),ftol=1.e-6))
                full=expand(solved.x)
                if not solved.success or not native_constraint.feasible(full):
                    # A native mesh nearest-feature switch can invalidate an
                    # SQP derivative. Continue this same constrained solve with
                    # a derivative-free method, never a generated-rollout loop.
                    print(f'{constraint_name} derivative-free frame={frame}',flush=True)
                    solved=minimize(objective,solved.x,method='COBYLA',
                        bounds=list(zip(solve_lower[slots],solve_upper[slots])),
                        constraints=[dict(type='ineq',fun=lambda v:1000.*native_constraint.fun(expand(v)))],
                        options=dict(maxiter=int(hard_release.get('cobyla_maxiter', 1500)),rhobeg=.002,tol=1.e-5,catol=1.e-9))
                    full=expand(solved.x)
                if not solved.success and native_constraint.feasible(full):
                    # COBYLA can find a feasible point before exhausting its
                    # objective budget. Refine from it with derivatives; do
                    # not equate feasibility with objective convergence.
                    solved=minimize(objective,solved.x,jac=objective_jac,method='SLSQP',
                        bounds=list(zip(solve_lower[slots],solve_upper[slots])),
                        constraints=[dict(type='ineq',fun=lambda v:1000.*native_constraint.fun(expand(v)),
                            jac=lambda v:1000.*native_constraint.jac(expand(v))[:,slots])],
                        options=dict(maxiter=int(hard_release.get('sqp_maxiter', 150)),ftol=1.e-6))
                    full=expand(solved.x)
                if not solved.success or not native_constraint.feasible(full):
                    raise RuntimeError(f'Frame {frame}: {constraint_name} infeasible/unconverged: {solved.message}; constraint_feasible={native_constraint.feasible(full)} gap={native_constraint.fun(full).tolist()} cost={solved.fun}; refusing output')
                return OptimizeResult(x=full,success=True,nfev=initial.nfev+solved.nfev,
                    cost=float(solved.fun),message=solved.message)

        result = solve_frame(x0)
        frame_nfev = int(result.nfev)
        frame_success = bool(result.success)
        candidate_root_delta = np.clip(
            result.x[:root_dofs],
            solve_lower[:root_dofs],
            solve_upper[:root_dofs],
        )
        candidate_cfg = np.clip(result.x[root_dofs:cfg_stop], lower, upper)

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
            query_root[:3] += root_rotation.apply(root_delta_base[:3])
            if yaw_enabled:
                query_root[3:7] = (Rotation.from_rotvec([0., 0., root_delta_base[3]]) * root_rotation).as_quat()[[3, 0, 1, 2]]
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
                candidate_root_delta[:3]
            )
            if yaw_enabled:
                candidate_root[3:7] = (Rotation.from_rotvec([0., 0., candidate_root_delta[3]]) * root_rotation).as_quat()[[3, 0, 1, 2]]
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
                np.asarray(root_yaw_axis_base, dtype=np.float64),
                *surface_args,
                *convex_args,
                *temporal_args,
                release_data[0][frame],
                release_data[1][frame],
                root_rotation.inv().apply(release_data[2][frame] - root[:3]),
                root_rotation.inv().apply(release_data[3][frame]),
                release_data[4][frame],
                support_residual_scale * contact_sqrt_weight * support_mask[frame],
                np.column_stack((support_orientation_targets[frame] if free_surface_contacts else source_fk[frame, compiled.contact_link_indices[frame], :4], support_orientation_projectors[frame].reshape(-1,9))),
                approach_data[0][frame], approach_data[1][frame],
                approach_target_base,
                support_residual_scale*approach_data[3][frame],
                approach_orientation_frame, temporal_history_mask(frame),
            )
            args_jax = tuple(jnp.asarray(value) for value in args)
            candidate_state = np.concatenate(
                (candidate_root_delta, candidate_cfg, result.x[cfg_stop:])
            )
            refined = solve_frame(candidate_state)
            collision_refinement_solve_count += 1
            frame_nfev += int(refined.nfev)
            frame_success = frame_success and bool(refined.success)
            candidate_root_delta = np.clip(
                refined.x[:root_dofs],
                solve_lower[:root_dofs],
                solve_upper[:root_dofs],
            )
            candidate_cfg = np.clip(refined.x[root_dofs:cfg_stop], lower, upper)
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
        if hard_release:
            if not native_constraint.feasible(result.x):raise RuntimeError(f'Frame {frame}: final hard release violated')
            hard_query_calls+=native_constraint.calls
            if release_geometry is not None:
                geometry_jacobian_calls+=native_constraint.jacobian_calls
        q_previous = candidate_cfg
        root_delta_previous_previous = root_delta_previous
        root_delta_previous = candidate_root_delta
        out_cfg[frame] = q_previous
        out_root_delta_base[frame] = root_delta_previous
        if convex_mode:
            solved_logits[frame] = result.x[cfg_stop:].reshape(coefficient_shape)
            chosen,_ = convex_targets(solved_logits[frame],convex_vertices_w[frame],convex_valid[frame])
            correction = chosen-compiled.contact_targets_w[frame]
            normal = surface_normals_w[frame]
            solved_target_corrections_w[frame] = correction-np.sum(correction*normal,axis=-1)[:,None]*normal
        success.append(frame_success)
        nfev.append(frame_nfev)
        costs.append(float(result.cost))

    solved_root = root_source[:n_frames].copy()
    solved_root[:, :3] += np.stack(
        [
            _quat_wxyz_to_rotation(root[3:7]).apply(delta[:3])
            for root, delta in zip(
                solved_root,
                out_root_delta_base,
            )
        ],
        axis=0,
    )
    if yaw_enabled:
        solved_root[:, 3:7] = (Rotation.from_rotvec(np.column_stack((
            np.zeros(n_frames), np.zeros(n_frames), out_root_delta_base[:, 3]))) *
            Rotation.from_quat(solved_root[:, [4, 5, 6, 3]])).as_quat()[:, [3, 0, 1, 2]]
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
        "release_witness_point_frames": int(np.count_nonzero(release_data[-1])),
        "native_hard_release": bool(hard_release),
        "native_hard_release_query_calls": hard_query_calls if release_geometry is None else 0,
        "native_geometry_evaluations": hard_query_calls if release_geometry is not None else 0,
        "native_geometry_jacobian_evaluations": geometry_jacobian_calls,
        "native_geometry_requires_final_audit": release_geometry is not None,
        "release_witness_contract": "native_allocated_contact_release_witness_v1",
        "release_witness_requires_native_requery": True,
        "unresolved_semantics": list(compiled.unresolved_semantics),
        "unresolved_contacts": list(compiled.unresolved_contacts),
        "least_squares_success_count": int(sum(success)),
        "least_squares_failure_count": int(len(success) - sum(success)),
        "least_squares_nfev": _stats(np.asarray(nfev, dtype=np.float64)),
        "least_squares_cost": _stats(np.asarray(costs, dtype=np.float64)),
        "augmentation_objective": objective_version,
        "temporal_history_contract": "velocity_from_frame1_acceleration_from_frame2",
        "support_approach_orientation": approach_orientation_enabled,
        "objective_groups": ["endpoint", "pose_reference", "correction_continuity", "collision"],
        "source_foot_orientation_weight": float(foot_orientation_weight),
        "source_foot_orientation_link_count": len(foot_orientation_indices),
        "source_velocity_weight": float(q_velocity_weight),
        "source_acceleration_weight": float(q_acceleration_weight),
        "root_translation_limit_m": float(root_delta_limit_m),
        "root_yaw_optimized": yaw_enabled,
        "support_motion_contract": "endpoint_episode_rigid_edit_v2" if free_surface_contacts else None,
        "support_rotation_policy": support_rotation_policy,
        "support_origin_policy": support_origin_policy,
        "support_motion_episodes": support_episodes,
        "support_residual_scale": support_residual_scale,
        "support_approach_seconds": support_approach_seconds,
        "support_approach_is_contact_truth": False,
        "support_target_error_m": _stats(contact_error_all[support_mask[:n_frames]]),
        "support_target_sample_count": int(support_mask[:n_frames].sum()),
        "support_target_is_contact_truth": False,
        "initial_pose_contract": "edited_trajectory_initial_frame" if yaw_enabled else "source_initial_frame",
        "free_surface_contacts": free_surface_contacts,
        "convex_surface_targets": convex_mode,
        "contact_weight_contract": "shape_face_mean_v1" if collision_spec is not None and collision_spec.metadata.get("normalize_contact_group_weights") else "per_point_sum",
        "convex_target_parameterization": "bounded_two_coordinate_triangle_or_quad" if convex_mode else None,
        "inactive_contact_variables_removed": convex_mode,
        "convex_contact_temporal_contract": "shape_face_matched_demonstration_relative_correction" if convex_mode else None,
        "convex_contact_temporal_residual_scale": 0.1 if convex_mode else None,
        "convex_solve_attempts": solve_attempts if convex_mode else None,
        "surface_reference_ratio": surface_reference_ratio if free_surface_contacts else None,
        "root_yaw_condition": yaw_condition,
        "root_yaw_delta_rad": _stats(out_root_delta_base[:, 3]) if yaw_enabled else None,
        "root_translation_delta_m": _stats(
            np.linalg.norm(out_root_delta_base[:, :3], axis=-1)
        ),
        "root_translation_velocity_mps": _stats(
            np.diff(out_root_delta_base[:, :3], axis=0) * float(fps)
        ),
        "root_translation_acceleration_mps2": _stats(
            np.diff(out_root_delta_base[:, :3], n=2, axis=0)
            * float(fps) ** 2
        ),
        "environment_collision_backend": (
            "newton_soft_signed_distance_integrated_frame_ik"
            if collision_terrain_mesh is not None
            else "disabled"
        ),
        "environment_collision_contract": (
            "source_relative_one_sided_penetration"
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
    convex_output = {}
    if convex_mode:
        chosen, coefficients = convex_targets(solved_logits, convex_vertices_w[:n_frames], convex_valid[:n_frames])
        convex_output = dict(optimized_surface_targets_w=chosen,
            optimized_surface_target_weights=coefficients, optimized_surface_target_mask=convex_finite[:n_frames],
            optimized_surface_target_vertices_w=convex_vertices_w[:n_frames])
    np.savez_compressed(
        output,
        **convex_output,
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
