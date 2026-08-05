"""ContactEditPlan-driven fullbody LTE generation implementation."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import numpy as np
from somaforge_core.contact_schema import (
    CONTACT_BODY_NAMES_BY_PART,
    CONTACT_KINEMATIC_BODY_NAMES_BY_PART,
    canonical_contact_part_name,
)
from somaforge_core.robot_assets import (
    canonical_g1_urdf_path,
    canonical_g1_source_metadata,
    decode_robot_asset_json,
    encode_robot_asset_json,
)

from motion_edit.contact.dynamics import build_load_profile_from_force_phase, load_profile_from_motion_force
from motion_edit.contact.io import read_contact_surfaces
from motion_edit.contact.layers import read_contact_graph, write_contact_layer
from motion_edit.contact.patches import patches_from_anchors
from motion_edit.contact.plans import ContactEditPlan, validate_contact_edit_plan
from motion_edit.contact.schema import ContactAnchorEditRecord, PoseEditRecord
from motion_edit.contact.surface_frame import map_points_between_surface_frames
from motion_edit.contact_laplacian.kinematics import BodyPositionTrajectoryKinematicsProvider
from motion_edit.contact_laplacian.omniretarget_mesh import sample_terrain_mesh_points
from motion_edit.contact_laplacian.schema import BatchContactLaplacianConfig, ContactHandleSpec, InteractionMeshSpec
from motion_edit.contact_laplacian.solver import solve_batch_contact_laplacian
from motion_edit.generation.contact_episodes import build_contact_episode_trajectories
from motion_edit.layers import write_layer
from motion_edit.paths import LAYERS_ROOT
from motion_edit.schema import SegmentRecord
from motion_edit.storage.canonical import (
    segments_from_contact_transitions,
    write_motion_version_with_canonical_segments,
)
from motion_edit.storage.io import write_motion_version
from motion_edit.storage.schema import MotionVersionRecord


@dataclass(frozen=True)
class LteGenerationResult:
    output_motion_path: Path
    output_contact_layer: str | None = None
    output_segment_layer: str | None = None
    output_motion_version_id: str | None = None
    warnings: list[str] | None = None


BODY_NAME_KEYS = (
    "body_names",
    "body_name",
    "body_pos_w_names",
    "body_pos_names",
    "contact_force_part_order",
    "contact_part_names",
    "contact_part_order",
)

LTE_FULLBODY_KEYPOINT_LINKS = {
    "pelvis": ("pelvis",),
    "left_hip": ("left_hip_roll_link", "left_hip_pitch_link"),
    "left_knee": ("left_knee_link",),
    "left_foot": ("left_ankle_roll_link", "left_ankle_roll_sphere_1_link"),
    "right_hip": ("right_hip_roll_link", "right_hip_pitch_link"),
    "right_knee": ("right_knee_link",),
    "right_foot": ("right_ankle_roll_link", "right_ankle_roll_sphere_1_link"),
    "torso": ("torso_link",),
    "left_shoulder": ("left_shoulder_roll_link", "left_shoulder_pitch_link"),
    "left_elbow": ("left_elbow_link",),
    "left_hand": (*CONTACT_BODY_NAMES_BY_PART["left_hand"], "left_wrist_yaw_link"),
    "right_shoulder": ("right_shoulder_roll_link", "right_shoulder_pitch_link"),
    "right_elbow": ("right_elbow_link",),
    "right_hand": (*CONTACT_BODY_NAMES_BY_PART["right_hand"], "right_wrist_yaw_link"),
}

LTE_FOOT_CONTACT_GROUP_LINKS = {
    part_name: CONTACT_BODY_NAMES_BY_PART[part_name]
    for part_name in ("left_heel", "left_toe", "right_heel", "right_toe")
}

LTE_FULLBODY_CONTACT_NAMES = (
    "left_heel",
    "left_toe",
    "right_heel",
    "right_toe",
    "left_hand",
    "right_hand",
    "left_knee",
    "right_knee",
)
LTE_HANDLE_KEYPOINT_NAMES = ("root", "torso", *LTE_FULLBODY_CONTACT_NAMES)

CONTACT_BODY_LINK_CANDIDATES = {
    "lf": ("left_foot",),
    "rf": ("right_foot",),
    "lhee": ("left_heel",),
    "ltoe": ("left_toe",),
    "rhee": ("right_heel",),
    "rtoe": ("right_toe",),
    "left_heel": ("left_heel",),
    "left_foot_heel": ("left_heel",),
    "left_toe": ("left_toe",),
    "left_foot_toe": ("left_toe",),
    "right_heel": ("right_heel",),
    "right_foot_heel": ("right_heel",),
    "right_toe": ("right_toe",),
    "right_foot_toe": ("right_toe",),
    "lh": ("left_hand",),
    "rh": ("right_hand",),
    "lk": ("left_knee",),
    "rk": ("right_knee",),
    "left_foot": (
        *CONTACT_BODY_NAMES_BY_PART["left_heel"],
        *CONTACT_BODY_NAMES_BY_PART["left_toe"],
        "left_ankle_roll_link",
    ),
    "right_foot": (
        *CONTACT_BODY_NAMES_BY_PART["right_heel"],
        *CONTACT_BODY_NAMES_BY_PART["right_toe"],
        "right_ankle_roll_link",
    ),
    "left_hand": CONTACT_BODY_NAMES_BY_PART["left_hand"],
    "right_hand": CONTACT_BODY_NAMES_BY_PART["right_hand"],
    "left_knee": CONTACT_BODY_NAMES_BY_PART["left_knee"],
    "right_knee": CONTACT_BODY_NAMES_BY_PART["right_knee"],
    "left_hip": ("left_hip_yaw_link", "left_hip_roll_link", "left_hip_pitch_link"),
    "right_hip": ("right_hip_yaw_link", "right_hip_roll_link", "right_hip_pitch_link"),
    "torso": ("torso_link",),
    "root": ("pelvis",),
}


def _decode_npz_string(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.bytes_):
        return bytes(value).decode("utf-8")
    return str(value)


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
                        return [_decode_npz_string(item) for item in parsed]
                except json.JSONDecodeError:
                    return [item.strip() for item in raw.split(",") if item.strip()]
            if isinstance(raw, (list, tuple)):
                return [_decode_npz_string(item) for item in raw]
            return [_decode_npz_string(raw)]
        return [_decode_npz_string(item) for item in arr.reshape(-1).tolist()]
    return []


def _index_by_alias(names: list[str], aliases: tuple[str, ...]) -> int:
    lowered = [name.lower() for name in names]
    for alias in aliases:
        if alias in names:
            return names.index(alias)
        if alias.lower() in lowered:
            return lowered.index(alias.lower())
    raise ValueError(f"cannot resolve any of {aliases}; available bodies={names}")


def _index_by_alias_or_none(names: list[str], aliases: tuple[str, ...]) -> int | None:
    try:
        return _index_by_alias(names, aliases)
    except ValueError:
        return None


def resolve_body_index(motion_data: dict[str, Any], body_name: str) -> int:
    names = _motion_strings(motion_data, BODY_NAME_KEYS)
    if not names:
        raise ValueError(
            f"cannot resolve body index for {body_name!r}: motion npz has no body name metadata "
            f"({', '.join(BODY_NAME_KEYS)})"
        )
    if body_name in names:
        return names.index(body_name)
    lowered = [name.lower() for name in names]
    if body_name.lower() in lowered:
        return lowered.index(body_name.lower())
    aliases = CONTACT_BODY_LINK_CANDIDATES.get(body_name.lower(), ())
    for alias in aliases:
        if alias in names:
            return names.index(alias)
        if alias.lower() in lowered:
            return lowered.index(alias.lower())
    raise ValueError(f"cannot resolve body index for {body_name!r}; available bodies={names}")


def _fps_from_motion(data: dict[str, Any], fallback: float) -> float:
    if "fps" in data:
        return float(np.asarray(data["fps"]).reshape(-1)[0])
    if "dt" in data:
        dt = float(np.asarray(data["dt"]).reshape(-1)[0])
        if dt > 0:
            return 1.0 / dt
    return float(fallback)


def _window_weights(n_frames: int, start: int, end: int, *, falloff_before: int, falloff_after: int) -> np.ndarray:
    if end <= start:
        raise ValueError(f"invalid affected frame interval [{start}, {end}]")
    weights = np.zeros(n_frames, dtype=np.float64)
    start = max(0, min(n_frames, int(start)))
    end = max(start, min(n_frames, int(end)))
    weights[start:end] = 1.0
    before0 = max(0, start - max(0, int(falloff_before)))
    if start > before0:
        span = start - before0
        for frame in range(before0, start):
            alpha = (frame - before0 + 1) / (span + 1)
            weights[frame] = 0.5 * (1.0 - np.cos(np.pi * alpha))
    after1 = min(n_frames, end + max(0, int(falloff_after)))
    if after1 > end:
        span = after1 - end
        for frame in range(end, after1):
            alpha = (frame - end + 1) / (span + 1)
            weights[frame] = 0.5 * (1.0 + np.cos(np.pi * alpha))
    return weights


def _edit_interval(edit: ContactAnchorEditRecord, anchor: Any) -> tuple[int, int]:
    if edit.affected_frames is not None:
        return int(edit.affected_frames[0]), int(edit.affected_frames[1])
    return int(anchor.start_frame), int(anchor.end_frame)


def _edit_delta(edit: ContactAnchorEditRecord) -> np.ndarray:
    if edit.delta_world is not None:
        return np.asarray(edit.delta_world, dtype=np.float64)
    if edit.old_world_position is not None and edit.new_world_position is not None:
        return np.asarray(edit.new_world_position, dtype=np.float64) - np.asarray(edit.old_world_position, dtype=np.float64)
    raise ValueError(f"{edit.edit_id}: delta_world or old/new_world_position is required")


def _surface_transform_anchor_edits(plan: ContactEditPlan, graph: Any) -> list[ContactAnchorEditRecord]:
    edits: list[ContactAnchorEditRecord] = []
    explicit_anchor_ids = {
        str(raw.get("anchor_id"))
        for raw in plan.edits
        if raw.get("anchor_id") is not None
    }
    for transform in plan.surface_transforms:
        source_surface = dict(transform["source_surface"])
        target_surface = dict(transform["target_surface"])
        source_surface_id = str(source_surface["surface_id"])
        target_surface_id = str(target_surface["surface_id"])
        for anchor in graph.anchors:
            if anchor.surface_id != source_surface_id:
                continue
            if anchor.anchor_id in explicit_anchor_ids:
                continue
            if anchor.world_position is None or anchor.surface_coordinates is None:
                raise ValueError(f"{anchor.anchor_id}: surface-follow anchor must be fully bound")
            old_position = np.asarray(anchor.world_position, dtype=np.float64)
            new_position = map_points_between_surface_frames(
                old_position,
                source_surface,
                target_surface,
            )
            delta = new_position - old_position
            edits.append(
                ContactAnchorEditRecord(
                    edit_id=f"{transform['transform_id']}::{anchor.anchor_id}",
                    motion_id=anchor.motion_id,
                    anchor_id=anchor.anchor_id,
                    body=anchor.body,
                    old_world_position=old_position.tolist(),
                    new_world_position=new_position.tolist(),
                    requested_delta_world=delta.tolist(),
                    delta_world=delta.tolist(),
                    affected_frames=[int(anchor.start_frame), int(anchor.end_frame)],
                    surface_id=target_surface_id,
                    surface_normal=list(target_surface["normal"]),
                    surface_coordinates_before=dict(anchor.surface_coordinates),
                    surface_coordinates_after=dict(anchor.surface_coordinates),
                    constraint_mode="surface_transform",
                    source="task_surface_follow_expansion",
                    metadata={
                        "surface_transform": {
                            **transform,
                            "relative_surface_normal_offset_m": 0.0,
                        }
                    },
                )
            )
    return edits


def _json_npz_value(payload: dict[str, Any]) -> np.ndarray:
    return np.asarray(json.dumps(payload, sort_keys=True), dtype=object)


def _recompute_linear_velocity(position: np.ndarray, fps: float, dtype: np.dtype) -> np.ndarray:
    if position.shape[0] <= 1:
        return np.zeros_like(position, dtype=dtype)
    dt = 1.0 / float(fps)
    vel = np.zeros_like(position, dtype=np.float64)
    vel[1:-1] = (position[2:] - position[:-2]) / (2.0 * dt)
    vel[0] = (position[1] - position[0]) / dt
    vel[-1] = (position[-1] - position[-2]) / dt
    return vel.astype(dtype, copy=False)


def _load_motion_npz(path: str | Path) -> dict[str, Any]:
    with np.load(Path(path).expanduser(), allow_pickle=True) as data:
        return {key: data[key] for key in data.files}


def _validate_source_robot_asset(path: Path) -> None:
    with np.load(path, allow_pickle=False) as data:
        value = data["robot_asset_json"] if "robot_asset_json" in data.files else None
    decode_robot_asset_json(value, context=f"source motion {path}")


def _stamp_robot_asset(payload: dict[str, Any]) -> dict[str, Any]:
    output = dict(payload)
    metadata = canonical_g1_source_metadata()
    output["robot_asset_json"] = np.asarray(encode_robot_asset_json(metadata))
    if "motion_edit_generation_metadata" in output:
        generation_metadata = json.loads(np.asarray(output["motion_edit_generation_metadata"]).item())
        generation_metadata["robot_asset"] = metadata
        output["motion_edit_generation_metadata"] = _json_npz_value(generation_metadata)
    return output


def _import_legacy_lte_module(lte_repo_root: str | Path | None) -> Any:
    root = Path(lte_repo_root or "/home/xiaz/lte").expanduser()
    module_path = root / "contact_handle_lte.py"
    if not module_path.exists():
        raise FileNotFoundError(f"missing legacy LTE module: {module_path}")
    spec = importlib.util.spec_from_file_location("motion_edit_legacy_contact_handle_lte", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import legacy LTE module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _semantic_keypoints_from_motion(motion: dict[str, Any]) -> dict[str, np.ndarray]:
    if "body_pos_w" not in motion:
        raise ValueError("lte_fullbody requires body_pos_w in source motion")
    body_pos = np.asarray(motion["body_pos_w"], dtype=np.float64)
    if body_pos.ndim != 3 or body_pos.shape[2] != 3:
        raise ValueError(f"body_pos_w must have shape [T,B,3], got {body_pos.shape}")
    names = _motion_strings(motion, ("body_names", "body_name", "body_pos_w_names", "body_pos_names"))
    if not names:
        raise ValueError("lte_fullbody requires body_names metadata")
    return {
        name: body_pos[:, _index_by_alias(names, aliases), :3].copy()
        for name, aliases in LTE_FULLBODY_KEYPOINT_LINKS.items()
    }


def _contact_part_kinematic_trajectory(
    motion: dict[str, Any],
    *,
    body_pos: np.ndarray,
    body_names: list[str],
    part_name: str,
    existing: np.ndarray | None,
) -> np.ndarray:
    if part_name not in CONTACT_BODY_NAMES_BY_PART and existing is not None:
        return np.asarray(existing, dtype=np.float64).copy()
    physical_names = CONTACT_BODY_NAMES_BY_PART[part_name]
    physical_indices = [_index_by_alias_or_none(body_names, (name,)) for name in physical_names]
    if physical_indices and all(index is not None for index in physical_indices):
        return np.mean(body_pos[:, [int(index) for index in physical_indices], :3], axis=1)

    if part_name in LTE_FOOT_CONTACT_GROUP_LINKS:
        reconstructed = _foot_contact_group_from_canonical_urdf(
            motion,
            body_pos=body_pos,
            body_names=body_names,
            part_name=part_name,
        )
        if reconstructed is not None:
            return reconstructed

    kinematic_names = CONTACT_KINEMATIC_BODY_NAMES_BY_PART[part_name]
    kinematic_indices = [
        index
        for name in kinematic_names
        if (index := _index_by_alias_or_none(body_names, (name,))) is not None
    ]
    if kinematic_indices:
        return np.mean(body_pos[:, kinematic_indices, :3], axis=1)
    if existing is not None:
        return np.asarray(existing, dtype=np.float64).copy()
    raise ValueError(
        f"cannot resolve canonical contact trajectory for {part_name!r}; "
        f"available bodies={body_names}"
    )


def _foot_contact_group_from_canonical_urdf(
    motion: dict[str, Any],
    *,
    body_pos: np.ndarray,
    body_names: list[str],
    part_name: str,
) -> np.ndarray | None:
    side = "left" if part_name.startswith("left_") else "right"
    ankle_name = f"{side}_ankle_roll_link"
    ankle_index = _index_by_alias_or_none(body_names, (ankle_name,))
    if ankle_index is None or "body_quat_w" not in motion:
        return None
    body_quat = np.asarray(motion["body_quat_w"], dtype=np.float64)
    if body_quat.shape != (*body_pos.shape[:2], 4):
        return None
    offsets = _canonical_g1_contact_link_offsets()
    group_offsets = np.asarray(
        [offsets[name] for name in CONTACT_BODY_NAMES_BY_PART[part_name]],
        dtype=np.float64,
    )
    ankle_position = body_pos[:, ankle_index, :3]
    ankle_quaternion = body_quat[:, ankle_index, :4]
    rotated = _rotate_vectors_wxyz(
        ankle_quaternion[:, None, :],
        np.broadcast_to(group_offsets[None, :, :], (body_pos.shape[0], len(group_offsets), 3)),
    )
    return ankle_position + np.mean(rotated, axis=1)


@lru_cache(maxsize=1)
def _canonical_g1_contact_link_offsets() -> dict[str, np.ndarray]:
    root = ET.parse(canonical_g1_urdf_path()).getroot()  # noqa: S314 - trusted canonical local asset
    offsets: dict[str, np.ndarray] = {}
    required = {
        name
        for part_name in LTE_FOOT_CONTACT_GROUP_LINKS
        for name in CONTACT_BODY_NAMES_BY_PART[part_name]
    }
    for joint in root.findall("joint"):
        child = joint.find("child")
        parent = joint.find("parent")
        if child is None or parent is None:
            continue
        child_name = str(child.get("link") or "")
        if child_name not in required:
            continue
        side = "left" if child_name.startswith("left_") else "right"
        expected_parent = f"{side}_ankle_roll_link"
        if parent.get("link") != expected_parent or joint.get("type") != "fixed":
            raise ValueError(f"canonical contact link {child_name} must be fixed to {expected_parent}")
        origin = joint.find("origin")
        xyz = "0 0 0" if origin is None else str(origin.get("xyz") or "0 0 0")
        value = np.fromstring(xyz, sep=" ", dtype=np.float64)
        if value.shape != (3,) or not np.all(np.isfinite(value)):
            raise ValueError(f"canonical contact link {child_name} has invalid joint origin {xyz!r}")
        offsets[child_name] = value
    missing = sorted(required - offsets.keys())
    if missing:
        raise ValueError(f"canonical G1 URDF is missing contact-link offsets: {missing}")
    return offsets


def _rotate_vectors_wxyz(quaternion: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    quat = np.asarray(quaternion, dtype=np.float64)
    vec = np.asarray(vectors, dtype=np.float64)
    norm = np.linalg.norm(quat, axis=-1, keepdims=True)
    quat = quat / np.where(norm > 1.0e-12, norm, 1.0)
    scalar = quat[..., :1]
    axis = quat[..., 1:4]
    return vec + 2.0 * np.cross(axis, np.cross(axis, vec) + scalar * vec)


def _overlay_recorded_contact_part_positions(
    motion: dict[str, Any],
    keypoints: dict[str, np.ndarray],
) -> None:
    if "contact_force_part_position_w" not in motion or "contact_force_part_position_valid" not in motion:
        return
    order_key = next(
        (key for key in ("contact_force_part_order", "part_order", "contact_part_names") if key in motion),
        None,
    )
    if order_key is None:
        return
    try:
        part_order = [canonical_contact_part_name(name) for name in _motion_strings(motion, (order_key,))]
    except ValueError:
        return
    positions = np.asarray(motion["contact_force_part_position_w"], dtype=np.float64)
    valid = np.asarray(motion["contact_force_part_position_valid"], dtype=bool)
    if positions.ndim != 3 or positions.shape[2] != 3 or valid.shape != positions.shape[:2]:
        raise ValueError(
            "contact_force_part_position_w/valid must have shapes [T,P,3] and [T,P]"
        )
    for part_name in LTE_FULLBODY_CONTACT_NAMES:
        if part_name not in part_order or part_name not in keypoints:
            continue
        part_index = part_order.index(part_name)
        count = min(keypoints[part_name].shape[0], positions.shape[0])
        use = valid[:count, part_index] & np.all(np.isfinite(positions[:count, part_index]), axis=1)
        keypoints[part_name][:count][use] = positions[:count, part_index][use]


def _contact_mask_for_keypoint(motion: dict[str, Any], keypoint: str, n_frames: int) -> np.ndarray:
    mask = np.zeros(n_frames, dtype=bool)
    order_key = next((key for key in ("contact_force_part_order", "part_order", "contact_part_names") if key in motion), None)
    mask_key = next((key for key in ("contact_force_part_mask", "contact_part_mask") if key in motion), None)
    if order_key is None or mask_key is None:
        return mask
    try:
        part_order = [canonical_contact_part_name(name) for name in _motion_strings(motion, (order_key,))]
    except ValueError:
        return mask
    if keypoint not in part_order:
        return mask
    raw = np.asarray(motion[mask_key], dtype=bool)
    if raw.ndim != 2:
        return mask
    count = min(n_frames, raw.shape[0])
    mask[:count] = raw[:count, part_order.index(keypoint)]
    return mask


def _keypoint_contact_weights(motion: dict[str, Any], keypoint: str, n_frames: int) -> np.ndarray:
    mask = _contact_mask_for_keypoint(motion, keypoint, n_frames)
    return mask.astype(np.float64)


def _resolve_lte_handle_name(body: str, keypoints: dict[str, np.ndarray]) -> str | None:
    name = str(body)
    if name in keypoints:
        return name
    aliases = CONTACT_BODY_LINK_CANDIDATES.get(name.lower(), ())
    for candidate in aliases:
        if candidate in keypoints:
            return candidate
    lowered = name.lower()
    for candidate in keypoints:
        if candidate in lowered or lowered in candidate:
            return candidate
    return None


def _handles_from_contact_edits(
    edits: list[ContactAnchorEditRecord],
    keypoints: dict[str, np.ndarray],
    graph: Any | None = None,
) -> list[dict[str, Any]]:
    handles: list[dict[str, Any]] = []
    n_frames = len(next(iter(keypoints.values())))
    edited_anchor_ids: set[str] = set()
    zero_delta_anchor_ids: set[str] = set()
    for edit in edits:
        name = _resolve_lte_handle_name(edit.body, keypoints)
        if name not in keypoints:
            raise ValueError(f"{edit.edit_id}: LTE fullbody edit body {edit.body!r} is not a supported semantic keypoint")
        start, end = _edit_interval(edit, type("AnchorInterval", (), {"start_frame": 0, "end_frame": n_frames})())
        start = max(0, min(n_frames, start))
        end = max(start, min(n_frames, end))
        if end <= start:
            raise ValueError(f"{edit.edit_id}: empty LTE fullbody edit interval [{start}, {end}]")
        frames = np.arange(start, end, dtype=np.int64)
        delta = _edit_delta(edit)
        if float(np.linalg.norm(delta)) <= 1.0e-9:
            zero_delta_anchor_ids.add(edit.anchor_id)
            continue
        edited_anchor_ids.add(edit.anchor_id)
        handles.append(
            {
                "name": name,
                "frames": frames,
                "target": keypoints[name][frames] + delta[None, :],
                "mode": "xyz",
                "weight": float(edit.metadata.get("lte_handle_weight", 1.0)) if isinstance(edit.metadata, dict) else 1.0,
                "ramp": int(edit.metadata.get("lte_handle_ramp", 0)) if isinstance(edit.metadata, dict) else 0,
                "kind": "edited_contact",
                "anchor_id": edit.anchor_id,
            }
        )
    if graph is not None:
        for anchor in graph.anchors:
            if anchor.anchor_id in edited_anchor_ids:
                continue
            name = _resolve_lte_handle_name(anchor.body, keypoints)
            if name not in keypoints:
                continue
            start = max(0, min(n_frames, int(anchor.start_frame)))
            end = max(start, min(n_frames, int(anchor.end_frame)))
            if end <= start:
                continue
            frames = np.arange(start, end, dtype=np.int64)
            handles.append(
                {
                    "name": name,
                    "frames": frames,
                    "target": keypoints[name][frames],
                    "mode": "xyz",
                    "weight": 1.0,
                    "ramp": 0,
                    "kind": "fixed_contact",
                    "anchor_id": anchor.anchor_id,
                    "zero_delta_edit": anchor.anchor_id in zero_delta_anchor_ids,
                }
            )
    return handles


def _legacy_lte_solver_keypoints(keypoints: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    solver_keypoints = {
        "root": keypoints["pelvis"],
        "torso": keypoints["torso"],
        "left_foot": keypoints["left_foot"],
        "right_foot": keypoints["right_foot"],
    }
    solver_keypoints.update({name: keypoints[name] for name in LTE_FULLBODY_CONTACT_NAMES})
    return solver_keypoints


def _merge_solver_keypoints(original: dict[str, np.ndarray], solver_edited: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    edited = {name: value.copy() for name, value in original.items()}
    if "root" in solver_edited:
        edited["pelvis"] = np.asarray(solver_edited["root"], dtype=np.float64)
    for name in ("torso", "left_foot", "right_foot", *LTE_FULLBODY_CONTACT_NAMES):
        if name in solver_edited:
            edited[name] = np.asarray(solver_edited[name], dtype=np.float64)
    return edited


def _save_lte_keypoints(path: Path, *, keypoints: dict[str, np.ndarray], motion: dict[str, Any], source_motion: Path, edits: list[ContactAnchorEditRecord], graph: Any | None = None) -> None:
    n_frames = len(next(iter(keypoints.values())))
    arrays: dict[str, Any] = {name: np.asarray(value, dtype=np.float64) for name, value in keypoints.items()}
    arrays["source_demo"] = np.asarray(str(source_motion.expanduser().resolve()))
    arrays["source_frame_index"] = np.arange(n_frames, dtype=np.float64)
    if edits:
        arrays["terrain_shift"] = np.asarray(_edit_delta(edits[0]), dtype=np.float64)
    for name in LTE_FULLBODY_CONTACT_NAMES:
        arrays[f"contact_mask_{name}"] = _contact_mask_for_keypoint(motion, name, n_frames)
        arrays[f"contact_weight_{name}"] = _keypoint_contact_weights(motion, name, n_frames)
    arrays.update(_foot_orientation_target_arrays(motion, n_frames))
    if "interaction_object_points_w" in motion:
        arrays["interaction_object_points_w"] = np.asarray(
            motion["interaction_object_points_w"], dtype=np.float64
        )
    if graph is not None:
        arrays.update(
            _environment_contact_anchor_arrays(
                graph=graph,
                edits=edits,
                keypoints=keypoints,
                n_frames=n_frames,
                contact_motion=motion,
                contact_positions_are_target=True,
            )
        )
        foot_summaries = {
            anchor.anchor_id: anchor.metadata.get("raw_contact_position_refinement", {}).get("foot_contact_summary")
            for anchor in graph.anchors
            if anchor.metadata.get("raw_contact_position_refinement", {}).get("foot_contact_summary") is not None
        }
        if foot_summaries:
            arrays["motion_edit_foot_contact_summaries"] = _json_npz_value(foot_summaries)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, **arrays)


def _environment_contact_anchor_arrays(
    *,
    graph: Any,
    edits: list[ContactAnchorEditRecord],
    keypoints: dict[str, np.ndarray],
    n_frames: int,
    contact_motion: dict[str, Any] | None = None,
    contact_positions_are_target: bool = False,
) -> dict[str, np.ndarray]:
    """Serialize one environment constraint per continuous editor episode."""

    episodes = build_contact_episode_trajectories(
        anchors=list(graph.anchors),
        edits=edits,
        keypoints=keypoints,
        n_frames=n_frames,
        contact_motion=contact_motion,
        contact_positions_are_target=contact_positions_are_target,
    )
    if not episodes:
        return {}
    source_trajectories = np.zeros((len(episodes), n_frames, 3), dtype=np.float64)
    target_trajectories = np.zeros_like(source_trajectories)
    contact_source_trajectories = np.zeros_like(source_trajectories)
    contact_target_trajectories = np.zeros_like(source_trajectories)
    force_trajectories = np.zeros_like(source_trajectories)
    contact_masks = np.zeros((len(episodes), n_frames), dtype=bool)
    source_positions = np.zeros((len(episodes), 3), dtype=np.float64)
    target_positions = np.zeros_like(source_positions)
    contact_source_positions = np.zeros_like(source_positions)
    contact_target_positions = np.zeros_like(source_positions)
    for index, episode in enumerate(episodes):
        start = int(episode.start_frame)
        end = int(episode.end_frame)
        local_representative = int(episode.representative_frame) - start
        source_position = episode.source_semantic_xyz[local_representative]
        target_position = episode.target_semantic_xyz[local_representative]
        contact_source_position = episode.source_contact_xyz[local_representative]
        contact_target_position = episode.target_contact_xyz[local_representative]
        source_positions[index] = source_position
        target_positions[index] = target_position
        contact_source_positions[index] = contact_source_position
        contact_target_positions[index] = contact_target_position
        source_trajectories[index] = np.broadcast_to(source_position, (n_frames, 3))
        target_trajectories[index] = np.broadcast_to(target_position, (n_frames, 3))
        contact_source_trajectories[index] = np.broadcast_to(contact_source_position, (n_frames, 3))
        contact_target_trajectories[index] = np.broadcast_to(contact_target_position, (n_frames, 3))
        source_trajectories[index, start:end] = episode.source_semantic_xyz
        target_trajectories[index, start:end] = episode.target_semantic_xyz
        contact_source_trajectories[index, start:end] = episode.source_contact_xyz
        contact_target_trajectories[index, start:end] = episode.target_contact_xyz
        force_trajectories[index, start:end] = episode.contact_force_w
        contact_masks[index, start:end] = episode.contact_mask
    return {
        "environment_contact_anchor_schema": np.asarray("motion_edit_contact_episode_trajectory_v1"),
        "environment_contact_anchor_ids": np.asarray([item.episode_id for item in episodes]),
        "environment_contact_anchor_bodies": np.asarray([item.body for item in episodes]),
        "environment_contact_anchor_semantic_names": np.asarray([item.semantic_name for item in episodes]),
        "environment_contact_anchor_start_frames": np.asarray([item.start_frame for item in episodes], dtype=np.int64),
        "environment_contact_anchor_end_frames": np.asarray([item.end_frame for item in episodes], dtype=np.int64),
        "environment_contact_anchor_representative_frames": np.asarray(
            [item.representative_frame for item in episodes], dtype=np.int64
        ),
        "environment_contact_anchor_source_position_w": source_positions,
        "environment_contact_anchor_target_position_w": target_positions,
        "environment_contact_anchor_source_trajectory_w": source_trajectories,
        "environment_contact_anchor_target_trajectory_w": target_trajectories,
        "environment_contact_anchor_contact_source_position_w": contact_source_positions,
        "environment_contact_anchor_contact_target_position_w": contact_target_positions,
        "environment_contact_anchor_contact_source_trajectory_w": contact_source_trajectories,
        "environment_contact_anchor_contact_target_trajectory_w": contact_target_trajectories,
        "environment_contact_anchor_force_trajectory_w": force_trajectories,
        "environment_contact_anchor_contact_mask": contact_masks,
        "environment_contact_anchor_edited": np.asarray([item.edited for item in episodes], dtype=bool),
        "environment_contact_anchor_surface_ids": np.asarray([item.surface_id or "" for item in episodes]),
        "environment_contact_anchor_object_ids": np.asarray([item.object_id or "" for item in episodes]),
        "environment_contact_anchor_member_anchor_ids_json": _json_npz_value(
            {item.episode_id: list(item.member_anchor_ids) for item in episodes}
        ),
        "environment_contact_anchor_member_edit_ids_json": _json_npz_value(
            {item.episode_id: list(item.member_edit_ids) for item in episodes}
        ),
    }


def _foot_orientation_target_arrays(motion: dict[str, Any], n_frames: int) -> dict[str, np.ndarray]:
    if "body_quat_w" not in motion or "joint_pos" not in motion:
        return {}
    names = _motion_strings(motion, ("body_names", "body_name", "body_pos_w_names", "body_pos_names"))
    if not names:
        return {}
    body_quat = np.asarray(motion["body_quat_w"], dtype=np.float64)
    joint_pos = np.asarray(motion["joint_pos"], dtype=np.float64)
    if body_quat.ndim != 3 or body_quat.shape[2] != 4:
        return {}
    if joint_pos.ndim != 2 or joint_pos.shape[1] < 7:
        return {}
    out: dict[str, np.ndarray] = {}
    for foot_name, link_name in (("left_foot", "left_ankle_roll_link"), ("right_foot", "right_ankle_roll_link")):
        index = _index_by_alias_or_none(names, (link_name, f"{foot_name}_contact_point"))
        if index is not None:
            foot_world = _normalize_quat_wxyz(body_quat[:n_frames, index, :4])
            out[f"orientation_target_{foot_name}"] = foot_world
    return out


def _normalize_quat_wxyz(quat: np.ndarray) -> np.ndarray:
    q = np.asarray(quat, dtype=np.float64).copy()
    norm = np.linalg.norm(q, axis=-1, keepdims=True)
    norm = np.where(norm > 1.0e-12, norm, 1.0)
    return q / norm


def _quat_conj_wxyz(quat: np.ndarray) -> np.ndarray:
    q = np.asarray(quat, dtype=np.float64).copy()
    q[..., 1:4] *= -1.0
    return q


def _quat_mul_wxyz(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aw, ax, ay, az = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    bw, bx, by, bz = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    out = np.stack(
        [
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ],
        axis=-1,
    )
    return _normalize_quat_wxyz(out)


def _semantic_body_weights(body_names: list[str], keypoint_names: list[str]) -> np.ndarray:
    weights = np.zeros((len(body_names), len(keypoint_names)), dtype=np.float64)
    sem = {name: index for index, name in enumerate(keypoint_names)}
    for index, name in enumerate(body_names):
        if name == "world":
            continue
        if name in {"pelvis", "pelvis_contour_link"} or name.startswith(("left_hip", "right_hip")):
            weights[index, sem["pelvis"]] = 1.0
        elif name.startswith(("waist", "torso")) or "shoulder" in name:
            weights[index, sem["torso"]] = 1.0
        elif name.startswith("left_"):
            if any(token in name for token in ("foot_contact", "toe", "heel", "sole")):
                weights[index, sem["left_foot"]] = 1.0
            elif any(token in name for token in ("foot", "ankle")):
                weights[index, sem["pelvis"]] = 0.35
                weights[index, sem["left_foot"]] = 0.65
            elif any(token in name for token in ("hand_contact", "palm", "finger", "rubber_hand", "thumb", "pinky")):
                weights[index, sem["left_hand"]] = 1.0
            elif any(token in name for token in ("hand", "elbow", "wrist")):
                weights[index, sem["torso"]] = 0.25
                weights[index, sem["left_hand"]] = 0.75
            else:
                weights[index, sem["torso"]] = 1.0
        elif name.startswith("right_"):
            if any(token in name for token in ("foot_contact", "toe", "heel", "sole")):
                weights[index, sem["right_foot"]] = 1.0
            elif any(token in name for token in ("foot", "ankle")):
                weights[index, sem["pelvis"]] = 0.35
                weights[index, sem["right_foot"]] = 0.65
            elif any(token in name for token in ("hand_contact", "palm", "finger", "rubber_hand", "thumb", "pinky")):
                weights[index, sem["right_hand"]] = 1.0
            elif any(token in name for token in ("hand", "elbow", "wrist")):
                weights[index, sem["torso"]] = 0.25
                weights[index, sem["right_hand"]] = 0.75
            else:
                weights[index, sem["torso"]] = 1.0
        else:
            weights[index, sem["pelvis"]] = 1.0
    missing = weights.sum(axis=1) <= 0.0
    weights[missing, sem["pelvis"]] = 1.0
    return weights / weights.sum(axis=1, keepdims=True)


def _dense_taskspace_from_keypoints(motion: dict[str, Any], original: dict[str, np.ndarray], edited: dict[str, np.ndarray], source_motion: Path, lte_path: Path) -> dict[str, Any]:
    raw_body_pos = np.asarray(motion["body_pos_w"], dtype=np.float64)
    n_frames = len(next(iter(edited.values())))
    body_pos = raw_body_pos[:n_frames].copy()
    body_names_arr = np.asarray(motion["body_names"])
    body_names = [str(item) for item in body_names_arr.reshape(-1).tolist()]
    keypoint_names = [
        name
        for name in (*LTE_FULLBODY_KEYPOINT_LINKS, *LTE_FOOT_CONTACT_GROUP_LINKS)
        if name in original and name in edited
    ]
    offsets = np.stack([edited[name] - original[name] for name in keypoint_names], axis=1)
    dense_offset = np.einsum("tsc,bs->tbc", offsets, _semantic_body_weights(body_names, keypoint_names))
    edited_body_pos = body_pos + dense_offset
    fps = np.asarray(motion["fps"]) if "fps" in motion else np.asarray([50], dtype=np.int64)
    arrays: dict[str, Any] = {
        "body_names": body_names_arr,
        "fps": fps,
        "source_demo": np.asarray(str(source_motion.expanduser().resolve())),
        "source_lte": np.asarray(str(lte_path.expanduser().resolve())),
        "algorithm": np.asarray("motion_edit_lte_fullbody_taskspace"),
        "is_qpos": np.asarray(False),
        "note": np.asarray("body_pos_w is generated from ContactEditPlan LTE keypoint offsets; joint fields come from fullbody IK."),
        "body_pos_w": edited_body_pos.astype(np.float64),
        "body_lin_vel_w": _recompute_linear_velocity(edited_body_pos, float(np.asarray(fps).reshape(-1)[0]), np.dtype(np.float64)),
    }
    if "body_quat_w" in motion:
        arrays["body_quat_w"] = np.asarray(motion["body_quat_w"])[:n_frames]
    for key in ("part_order", "contact_part_mask", "active_part_mask", "support_part_mask", "free_part_mask"):
        if key in motion:
            arr = np.asarray(motion[key])
            arrays[key] = arr[:n_frames] if arr.shape[:1] == (n_frames,) or arr.shape[:1] == (raw_body_pos.shape[0],) else arr
    for name in keypoint_names:
        arrays[f"keypoint_{name}"] = np.asarray(edited[name], dtype=np.float64)
        arrays[f"offset_{name}"] = np.asarray(edited[name] - original[name], dtype=np.float64)
    return arrays


def _copy_contact_force_payload_with_edits(
    arrays: dict[str, Any],
    *,
    motion: dict[str, Any],
    edits: list[ContactAnchorEditRecord],
    n_frames: int,
) -> None:
    """Carry Newton force data forward and translate its bound contact points."""

    source_frame_count = (
        int(np.asarray(motion["contact_force_part_w"]).shape[0])
        if "contact_force_part_w" in motion and np.asarray(motion["contact_force_part_w"]).ndim > 0
        else int(n_frames)
    )
    for key, value in motion.items():
        if not key.startswith("contact_force_"):
            continue
        source = np.asarray(value)
        arrays[key] = (
            source[:n_frames].copy()
            if key != "contact_force_part_order"
            and source.ndim > 0
            and source.shape[0] == source_frame_count
            else source.copy()
        )
    if "contact_force_part_order" not in arrays:
        return
    try:
        part_names = [
            canonical_contact_part_name(name)
            for name in _motion_strings(arrays, ("contact_force_part_order",))
        ]
    except ValueError:
        return
    parent_parts = {
        "left_foot": ("left_heel", "left_toe"),
        "right_foot": ("right_heel", "right_toe"),
    }
    applied: list[dict[str, Any]] = []
    for edit in edits:
        edit_parts = parent_parts.get(str(edit.body), (str(edit.body),))
        delta = _edit_delta(edit)
        start, end = _edit_interval(
            edit,
            type("ContactForceInterval", (), {"start_frame": 0, "end_frame": n_frames})(),
        )
        start = max(0, min(n_frames, int(start)))
        end = max(start, min(n_frames, int(end)))
        if end <= start or float(np.linalg.norm(delta)) <= 1.0e-12:
            continue
        for part_name in edit_parts:
            try:
                canonical_name = canonical_contact_part_name(part_name)
            except ValueError:
                continue
            if canonical_name not in part_names:
                continue
            part_index = part_names.index(canonical_name)
            if "contact_force_part_position_w" in arrays:
                positions = np.asarray(arrays["contact_force_part_position_w"]).copy()
                segment = positions[start:end, part_index]
                valid = (
                    np.asarray(arrays["contact_force_part_position_valid"], dtype=bool)[start:end, part_index]
                    if "contact_force_part_position_valid" in arrays
                    else np.ones(segment.shape[0], dtype=bool)
                )
                segment[valid] += delta
                positions[start:end, part_index] = segment
                arrays["contact_force_part_position_w"] = positions
            if "contact_force_part_position_history_w" in arrays:
                history = np.asarray(arrays["contact_force_part_position_history_w"]).copy()
                segment = history[start:end, :, part_index]
                valid = (
                    np.asarray(arrays["contact_force_part_position_valid_history"], dtype=bool)[
                        start:end, :, part_index
                    ]
                    if "contact_force_part_position_valid_history" in arrays
                    else np.ones(segment.shape[:2], dtype=bool)
                )
                segment[valid] += delta
                history[start:end, :, part_index] = segment
                arrays["contact_force_part_position_history_w"] = history
            applied.append(
                {
                    "anchor_id": edit.anchor_id,
                    "part": canonical_name,
                    "start_frame": start,
                    "end_frame": end,
                    "delta_world": delta.tolist(),
                }
            )
    if applied:
        arrays["contact_force_part_position_source"] = np.asarray(
            "motion_edit_translated_source_contact_position"
        )
        arrays["motion_edit_contact_position_edits_json"] = _json_npz_value(applied)
        if "contact_force_provenance_json" in arrays:
            try:
                provenance = json.loads(_decode_npz_string(arrays["contact_force_provenance_json"]))
            except (json.JSONDecodeError, TypeError, ValueError):
                provenance = {}
            provenance["motion_edit_contact_position_translation"] = applied
            arrays["contact_force_provenance_json"] = np.asarray(json.dumps(provenance, sort_keys=True))


def _batch_contact_laplacian_proxy_motion(
    *,
    motion: dict[str, Any],
    force_motion: dict[str, Any] | None,
    force_source_path: str | Path | None,
    source_motion: Path,
    graph: Any,
    contact_layer_root: Path,
    edits: list[ContactAnchorEditRecord],
    config: BatchContactLaplacianConfig,
    source_plan_path: str | Path | None,
    plan: ContactEditPlan,
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    """Generate an experimental task-space proxy motion with batch contact-Laplacian.

    This uses semantic ``body_pos_w`` keypoints as optimization variables. It is
    useful for validating contact/mesh propagation on real rollouts before a
    true joint-space robot kinematics provider is available.
    """

    original_keypoints = _semantic_keypoints_from_motion(motion)
    solver_keypoints = _legacy_lte_solver_keypoints(original_keypoints)
    provider = BodyPositionTrajectoryKinematicsProvider(tuple(solver_keypoints))
    q_init = np.stack([solver_keypoints[name] for name in provider.point_names], axis=1).reshape(len(next(iter(solver_keypoints.values()))), -1)
    contact_handles = _contact_laplacian_handles_from_edits(
        edits,
        solver_keypoints,
        graph=graph,
        config=config,
        source_motion=force_motion,
    )
    pose_handles = _pose_edit_handles_from_plan(plan, solver_keypoints, config=config)
    handles = [*contact_handles, *pose_handles]
    surfaces = _read_contact_layer_surfaces(contact_layer_root, graph.motion_id)
    mesh, mesh_warnings = _interaction_mesh_from_motion_and_graph(
        graph=graph,
        surfaces=surfaces,
        robot_points=tuple(provider.point_names),
    )
    result = solve_batch_contact_laplacian(
        q_init,
        provider,
        handles,
        list(provider.point_names),
        config,
        q_prior=q_init,
        interaction_mesh=mesh if float(config.mesh_laplacian_weight) > 0.0 else None,
    )
    edited_solver = {
        name: result.q.reshape(q_init.shape[0], len(provider.point_names), 3)[:, index, :]
        for index, name in enumerate(provider.point_names)
    }
    evaluation = _contact_laplacian_evaluation_summary(
        q_before=q_init,
        q_after=result.q,
        provider=provider,
        handles=handles,
        semantic_points=tuple(provider.point_names),
    )
    edited_keypoints = _merge_solver_keypoints(original_keypoints, edited_solver)
    arrays = _dense_taskspace_from_keypoints(motion, original_keypoints, edited_keypoints, source_motion, source_motion.with_suffix(".batch_contact_laplacian_proxy.npz"))
    _copy_contact_force_payload_with_edits(
        arrays,
        motion=force_motion if force_motion is not None else motion,
        edits=edits,
        n_frames=len(next(iter(edited_keypoints.values()))),
    )
    arrays["interaction_object_points_w"] = np.asarray(mesh.object_points, dtype=np.float64)
    warnings = [
        "batch_contact_laplacian generated an experimental body_pos_w proxy motion; joint/orientation fields are preserved",
        *mesh_warnings,
        *result.warnings,
    ]
    metadata = {
        "source_plan": str(Path(source_plan_path).expanduser()) if source_plan_path is not None else plan.plan_id,
        "source_plan_id": plan.plan_id,
        "source_motion": str(source_motion),
        "force_source_motion": str(force_source_path or ""),
        "generation_mode": "lte_fullbody",
        "fullbody_solver": "batch_contact_laplacian",
        "proxy_kinematics": "body_pos_w_semantic_points",
        "num_edits": len(edits),
        "surface_transform_count": len(plan.surface_transforms),
        "pose_edit_count": len(plan.pose_edits),
        "pose_handle_count": len(pose_handles),
        "contact_constraint_unit": "continuous_contact_episode",
        "contact_episode_count": len(contact_handles),
        "contact_episode_source_anchor_count": sum(
            len(handle.metadata.get("member_anchor_ids", [])) for handle in contact_handles
        ),
        "moving_contact_handle_count": sum(1 for handle in contact_handles if handle.kind == "edited_contact"),
        "fixed_contact_handle_count": sum(1 for handle in contact_handles if handle.kind == "fixed_contact"),
        "force_load_profile_count": sum(1 for handle in handles if handle.load_profile is not None),
        "force_load_profiles_active": any(handle.load_profile is not None for handle in handles),
        "force_load_profile_interval_mapping": "same_frame_interval",
        "contact_laplacian_config": config.__dict__,
        "solver_metadata": result.metadata,
        "evaluation_summary": evaluation,
        "warnings": warnings,
        "edits": [edit.to_dict() for edit in edits],
        "pose_edits": list(plan.pose_edits),
    }
    arrays["motion_edit_generation_metadata"] = _json_npz_value(metadata)
    arrays["source_motion_path"] = np.asarray(str(source_motion), dtype=object)
    arrays["source_contact_edit_plan"] = np.asarray(plan.plan_id, dtype=object)
    for key in ("joint_pos", "joint_vel", "joint_names"):
        if key in motion:
            arrays[key] = np.asarray(motion[key])
    return arrays, warnings, metadata


def _contact_laplacian_evaluation_summary(
    *,
    q_before: np.ndarray,
    q_after: np.ndarray,
    provider: BodyPositionTrajectoryKinematicsProvider,
    handles: list[ContactHandleSpec],
    semantic_points: tuple[str, ...],
) -> dict[str, Any]:
    edited_before: list[float] = []
    edited_after: list[float] = []
    fixed_drift: list[float] = []
    for handle in handles:
        frames = np.asarray(handle.frames, dtype=np.int64)
        target = np.asarray(handle.target_xyz, dtype=np.float64)
        before = np.asarray([provider.fk_points(q_before[int(frame)], [handle.semantic_name])[0] for frame in frames], dtype=np.float64)
        after = np.asarray([provider.fk_points(q_after[int(frame)], [handle.semantic_name])[0] for frame in frames], dtype=np.float64)
        if handle.kind == "edited_contact":
            edited_before.extend(np.linalg.norm(target - before, axis=1).tolist())
            edited_after.extend(np.linalg.norm(target - after, axis=1).tolist())
        elif handle.kind == "fixed_contact":
            fixed_drift.extend(np.linalg.norm(after - before, axis=1).tolist())
    before_points = q_before.reshape(q_before.shape[0], len(semantic_points), 3)
    after_points = q_after.reshape(q_after.shape[0], len(semantic_points), 3)
    deltas = np.linalg.norm(after_points - before_points, axis=2)
    return {
        "edited_contact_target_error_before": _stats(edited_before),
        "edited_contact_target_error_after": _stats(edited_after),
        "fixed_contact_drift_max": float(max(fixed_drift)) if fixed_drift else 0.0,
        "fixed_contact_drift_mean": float(np.mean(fixed_drift)) if fixed_drift else 0.0,
        "body_pos_delta_max_by_semantic": {
            name: float(np.max(deltas[:, index])) for index, name in enumerate(semantic_points)
        },
    }


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "max": 0.0}
    arr = np.asarray(values, dtype=np.float64)
    return {"mean": float(np.mean(arr)), "max": float(np.max(arr))}


def _write_contact_laplacian_intermediates(
    *,
    out: Path,
    intermediate_dir: str | Path | None,
    proxy_taskspace: dict[str, Any],
    metadata: dict[str, Any],
    graph: Any,
) -> tuple[Path, Path, Path]:
    work_dir = Path(intermediate_dir).expanduser() if intermediate_dir is not None else out.with_suffix("")
    work_dir.mkdir(parents=True, exist_ok=True)
    lte_path = work_dir / f"{out.stem}.contact_laplacian_keypoints.npz"
    taskspace_path = work_dir / f"{out.stem}.contact_laplacian_taskspace_motion.npz"
    ik_path = work_dir / f"{out.stem}.contact_laplacian_fullbody_ik_motion.npz"
    keypoint_arrays = {
        key[len("keypoint_") :]: np.asarray(value)
        for key, value in proxy_taskspace.items()
        if key.startswith("keypoint_")
    }
    source_motion = Path(str(metadata.get("source_motion", out)))
    edits = [ContactAnchorEditRecord(**raw) for raw in metadata.get("edits", [])]
    motion_for_masks = {key: value for key, value in proxy_taskspace.items()}
    _save_lte_keypoints(
        lte_path,
        keypoints=keypoint_arrays,
        motion=motion_for_masks,
        source_motion=source_motion,
        edits=edits,
        graph=graph,
    )
    taskspace_payload = dict(proxy_taskspace)
    taskspace_payload["algorithm"] = np.asarray("motion_edit_batch_contact_laplacian_taskspace")
    np.savez(taskspace_path, **taskspace_payload)
    return lte_path, taskspace_path, ik_path


def _merge_contact_laplacian_ik_output(
    *,
    proxy_taskspace: dict[str, Any],
    ik_motion: dict[str, Any],
    metadata: dict[str, Any],
    lte_path: Path,
    taskspace_path: Path,
    ik_path: Path,
    ik_conda_env: str,
    ik_script: str | Path | None,
    lte_repo_root: str | Path | None,
) -> dict[str, Any]:
    if "joint_pos" not in ik_motion:
        raise ValueError(f"batch_contact_laplacian IK output missing required joint_pos: {ik_path}")
    if ik_script:
        resolved_ik_script = str(Path(ik_script).expanduser())
    elif lte_repo_root:
        resolved_ik_script = str((Path(lte_repo_root).expanduser() / "scripts" / "solve_lte_fullbody_ik.py"))
    else:
        resolved_ik_script = str(Path(__file__).with_name("pyroki_fullbody_ik.py"))
    generated = dict(proxy_taskspace)
    for key in ("joint_pos", "joint_vel", "joint_names", "body_pos_w", "body_quat_w", "body_names", "is_qpos"):
        if key in ik_motion:
            generated[key] = ik_motion[key]
    final_metadata = {
        **metadata,
        "output_kind": "fullbody_ik_after_contact_laplacian_proxy",
        "joint_consistency": "fullbody_ik_subprocess",
        "contact_laplacian_keypoints": str(lte_path),
        "contact_laplacian_taskspace_motion": str(taskspace_path),
        "contact_laplacian_fullbody_ik_motion": str(ik_path),
        "ik_conda_env": ik_conda_env,
        "ik_script": resolved_ik_script,
    }
    warnings = list(final_metadata.get("warnings", []))
    warnings.append("batch_contact_laplacian ran fullbody IK after body-space proxy solve")
    final_metadata["warnings"] = warnings
    generated["motion_edit_generation_metadata"] = _json_npz_value(final_metadata)
    return generated


def _contact_laplacian_handles_from_edits(
    edits: list[ContactAnchorEditRecord],
    keypoints: dict[str, np.ndarray],
    *,
    graph: Any,
    config: BatchContactLaplacianConfig,
    source_motion: dict[str, Any] | None = None,
) -> list[ContactHandleSpec]:
    n_frames = len(next(iter(keypoints.values())))
    episodes = build_contact_episode_trajectories(
        anchors=list(graph.anchors),
        edits=edits,
        keypoints=keypoints,
        n_frames=n_frames,
        contact_motion=source_motion,
    )
    handles: list[ContactHandleSpec] = []
    for episode in episodes:
        frames = np.arange(episode.start_frame, episode.end_frame, dtype=np.int64)
        load_profile = build_load_profile_from_force_phase(
            episode.contact_force_w,
            source_frames=frames,
            metadata={
                "source": "contact_episode_force",
                "episode_id": episode.episode_id,
                "member_anchor_ids": list(episode.member_anchor_ids),
            },
        )
        handles.append(
            ContactHandleSpec(
                anchor_id=episode.episode_id,
                body=episode.body,
                semantic_name=episode.semantic_name,
                frames=frames,
                target_xyz=episode.target_semantic_xyz,
                kind="edited_contact" if episode.edited else "fixed_contact",
                weight=(
                    float(config.edit_contact_weight)
                    if episode.edited
                    else float(config.fixed_contact_weight)
                ),
                surface_id=episode.surface_id,
                object_id=episode.object_id,
                load_profile=load_profile,
                metadata={
                    "constraint_unit": "continuous_contact_episode",
                    "member_anchor_ids": list(episode.member_anchor_ids),
                    "member_edit_ids": list(episode.member_edit_ids),
                    "source_frame_start": int(episode.start_frame),
                    "source_frame_end": int(episode.end_frame),
                    "target_frame_start": int(episode.start_frame),
                    "target_frame_end": int(episode.end_frame),
                    "source_target_interval_mapping": "same_frame_interval",
                },
            )
        )
    return handles


def _pose_edit_handles_from_plan(
    plan: ContactEditPlan,
    keypoints: dict[str, np.ndarray],
    *,
    config: BatchContactLaplacianConfig,
) -> list[ContactHandleSpec]:
    handles: list[ContactHandleSpec] = []
    n_frames = len(next(iter(keypoints.values())))
    for raw_pose_edit in plan.pose_edits:
        pose_edit = PoseEditRecord(**raw_pose_edit)
        pose_edit.validate()
        start = max(0, min(n_frames, int(pose_edit.affected_frames[0])))
        end = max(start, min(n_frames, int(pose_edit.affected_frames[1])))
        if end <= start:
            raise ValueError(f"{pose_edit.edit_id}: empty pose edit interval [{start}, {end}]")
        frames = np.arange(start, end, dtype=np.int64)
        translation = np.asarray(pose_edit.translation_world, dtype=np.float64)
        for semantic_name in pose_edit.semantic_names:
            if semantic_name not in keypoints:
                raise ValueError(
                    f"{pose_edit.edit_id}: unsupported pose semantic {semantic_name!r}; "
                    f"available={sorted(keypoints)}"
                )
            handles.append(
                ContactHandleSpec(
                    anchor_id=f"{pose_edit.edit_id}::{semantic_name}",
                    body=semantic_name,
                    semantic_name=semantic_name,
                    frames=frames,
                    target_xyz=keypoints[semantic_name][frames] + translation[None, :],
                    kind="edited_contact",
                    weight=float(config.edit_contact_weight) * float(pose_edit.weight_scale),
                    metadata={
                        "constraint_role": "approach_pose",
                        "pose_edit_id": pose_edit.edit_id,
                        "source_frame_start": start,
                        "source_frame_end": end,
                    },
                )
            )
    return handles


def _contact_load_profile_for_interval(
    *,
    source_motion: dict[str, Any] | None,
    body: str,
    start: int,
    end: int,
    normal: list[float] | None,
):
    if source_motion is None:
        return None
    return load_profile_from_motion_force(
        source_motion,
        body=body,
        start_frame=start,
        end_frame=end,
        normal_w=normal,
        metadata={
            "target_frame_start": int(start),
            "target_frame_end": int(end),
            "source_target_interval_mapping": "same_frame_interval",
        },
    )


def _read_contact_layer_surfaces(contact_layer_root: Path, motion_id: str) -> list[Any]:
    path = contact_layer_root / "surfaces" / f"{motion_id}.jsonl"
    if not path.exists():
        return []
    return read_contact_surfaces(path)


def _interaction_mesh_from_motion_and_graph(
    *,
    graph: Any,
    surfaces: list[Any],
    robot_points: tuple[str, ...],
) -> tuple[InteractionMeshSpec, list[str]]:
    warnings: list[str] = []
    mesh_paths = {
        str(surface.metadata["mesh_path"])
        for surface in surfaces
        if isinstance(surface.metadata, dict) and surface.metadata.get("mesh_path")
    }
    if len(mesh_paths) != 1:
        raise ValueError(f"interaction mesh requires exactly one terrain mesh path, got {sorted(mesh_paths)}")
    mesh_path = next(iter(mesh_paths))
    object_points = sample_terrain_mesh_points(mesh_path, count=100, seed=0)
    warnings.append(f"sampled 100 deterministic OmniRetarget interaction points from {mesh_path}")
    return InteractionMeshSpec(
        robot_points=robot_points,
        object_points=object_points,
        topology="omniretarget_delaunay",
    ), warnings

def _run_fullbody_ik_subprocess(
    *,
    lte_path: Path,
    ik_output_path: Path,
    lte_repo_root: str | Path | None,
    ik_script: str | Path | None,
    ik_conda_env: str,
    ik_max_nfev: int | None,
    ik_q_prior_weight: float = 12.0,
    ik_q_smooth_weight: float = 60.0,
    foot_orientation_weight: float = 20.0,
    contact_foot_orientation_weight: float = 80.0,
    foot_toe_weight: float = 20.0,
    contact_foot_toe_weight: float = 120.0,
) -> None:
    package_root = Path(__file__).resolve().parents[2]
    workspace_packages = package_root.parent
    python_paths = [package_root, workspace_packages / "somaforge_core"]
    subprocess_env = os.environ.copy()
    inherited_python_path = subprocess_env.get("PYTHONPATH")
    subprocess_env["PYTHONPATH"] = os.pathsep.join(
        [*(str(path) for path in python_paths), *((inherited_python_path,) if inherited_python_path else ())]
    )
    repo = Path(lte_repo_root or "/home/xiaz/lte").expanduser()
    if ik_script is not None:
        script = Path(ik_script).expanduser()
        cwd = repo
    elif lte_repo_root is not None:
        script = repo / "scripts" / "solve_lte_fullbody_ik.py"
        cwd = repo
    else:
        script = Path(__file__).with_name("pyroki_fullbody_ik.py")
        cwd = Path(__file__).resolve().parents[2]
    target_env = str(ik_conda_env)
    current_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    current_env_name = Path(current_env).name if current_env else ""
    interpreter = (
        [sys.executable]
        if target_env in {current_env, current_env_name}
        else ["conda", "run", "-n", target_env, "python"]
    )
    cmd = [
        *interpreter,
        str(script.resolve()),
        "--lte",
        str(lte_path.resolve()),
        "--out",
        str(ik_output_path.resolve()),
    ]
    if ik_max_nfev is not None:
        cmd.extend(["--max-nfev", str(int(ik_max_nfev))])
    cmd.extend(
        [
            "--q-prior-weight",
            str(float(ik_q_prior_weight)),
            "--q-smooth-weight",
            str(float(ik_q_smooth_weight)),
        ]
    )
    cmd.extend(
        [
            "--foot-orientation-weight",
            str(float(foot_orientation_weight)),
            "--contact-foot-orientation-weight",
            str(float(contact_foot_orientation_weight)),
            "--foot-toe-weight",
            str(float(foot_toe_weight)),
            "--contact-foot-toe-weight",
            str(float(contact_foot_toe_weight)),
        ]
    )
    subprocess.run(cmd, cwd=str(cwd), env=subprocess_env, check=True)


def _apply_anchor_edits_to_graph(graph: Any, edits: list[ContactAnchorEditRecord]) -> Any:
    edits_by_anchor = {edit.anchor_id: edit for edit in edits}
    anchors = []
    for anchor in graph.anchors:
        edit = edits_by_anchor.get(anchor.anchor_id)
        if edit is None:
            anchors.append(anchor)
            continue
        metadata = dict(anchor.metadata)
        history = list(metadata.get("motion_edit_contact_edits") or [])
        history.append(edit.to_dict())
        metadata["motion_edit_contact_edits"] = history
        metadata["contact_graph_source"] = "source_graph_with_anchor_edits"
        metadata["surface_editor_status"] = "edited"
        new_world_position = edit.new_world_position or anchor.world_position
        new_surface_coordinates = edit.surface_coordinates_after or anchor.surface_coordinates
        surface_transform = edit.metadata.get("surface_transform") if isinstance(edit.metadata, dict) else None
        target_surface = (
            surface_transform.get("target_surface")
            if isinstance(surface_transform, dict) and isinstance(surface_transform.get("target_surface"), dict)
            else {}
        )
        bindings = list(metadata.get("surface_bindings") or [])
        if bindings and new_world_position is not None:
            latest_binding = dict(bindings[-1])
            current_position = [float(item) for item in new_world_position]
            latest_binding["original_world_position"] = current_position
            latest_binding["projected_world_position"] = current_position
            latest_binding["bound_world_position"] = current_position
            latest_binding["signed_surface_distance"] = 0.0
            if new_surface_coordinates is not None:
                current_coordinates = {
                    str(key): float(value) for key, value in new_surface_coordinates.items()
                }
                latest_binding["raw_surface_coordinates"] = current_coordinates
                latest_binding["surface_coordinates"] = current_coordinates
            bindings[-1] = latest_binding
            metadata["surface_bindings"] = bindings
        anchors.append(
            replace(
                anchor,
                world_position=new_world_position,
                object_id=str(target_surface.get("object_id")) if target_surface.get("object_id") else anchor.object_id,
                surface_id=edit.surface_id or anchor.surface_id,
                surface_origin=list(target_surface.get("origin")) if target_surface.get("origin") else anchor.surface_origin,
                surface_normal=list(target_surface.get("normal")) if target_surface.get("normal") else anchor.surface_normal,
                surface_tangent_u=(
                    list(target_surface.get("tangent_u")) if target_surface.get("tangent_u") else anchor.surface_tangent_u
                ),
                surface_tangent_v=(
                    list(target_surface.get("tangent_v")) if target_surface.get("tangent_v") else anchor.surface_tangent_v
                ),
                surface_bounds=dict(target_surface.get("bounds")) if target_surface.get("bounds") else anchor.surface_bounds,
                surface_coordinates=new_surface_coordinates,
                position_source="motion_edit_generated",
                metadata=metadata,
            )
        )
    return replace(graph, anchors=anchors, patches=patches_from_anchors(anchors))


def _segments_from_anchor_intervals(graph: Any, *, motion_path: str, source: str) -> list[SegmentRecord]:
    segments: list[SegmentRecord] = []
    for index, anchor in enumerate(graph.anchors):
        metadata = {
            "cut_source": source,
            "source_anchor_id": anchor.anchor_id,
            "active_body": anchor.body,
            "source_anchor": anchor.to_dict(),
        }
        segments.append(
            SegmentRecord(
                motion_id=graph.motion_id,
                segment_id=f"{graph.motion_id}_{source}_anchor_{index:04d}",
                start_frame=int(anchor.start_frame),
                end_frame=int(anchor.end_frame),
                source=source,
                status="candidate",
                track="contact_anchor",
                motion_path=motion_path,
                clip_npz=motion_path,
                active=anchor.body,
                metadata=metadata,
            )
        )
    return segments


def _candidate_segments_from_graph(
    graph: Any,
    *,
    motion_path: str,
    motion_version_id: str | None,
    plan_id: str,
    source: str,
    fullbody_solver: str | None = None,
) -> list[SegmentRecord]:
    if graph.transitions:
        segments = segments_from_contact_transitions(
            graph,
            motion_version_id=motion_version_id or graph.motion_id,
            motion_path=motion_path,
            source=source,
            status="candidate",
            cut_source=source,
        )
    else:
        segments = _segments_from_anchor_intervals(graph, motion_path=motion_path, source=source)
    output: list[SegmentRecord] = []
    for segment in segments:
        meta = dict(segment.metadata)
        meta["source_contact_edit_plan"] = plan_id
        if fullbody_solver is not None:
            meta["fullbody_solver"] = fullbody_solver
        output.append(replace(segment, motion_id=graph.motion_id, metadata=meta))
    return output


def apply_contact_edit_plan_to_motion(
    plan: ContactEditPlan,
    *,
    output_motion_path: str | Path,
    mode: str = "lte_fullbody",
    source_plan_path: str | Path | None = None,
    source_contact_layer: str | None = None,
    force_source_motion_path: str | Path | None = None,
    output_contact_layer: str | None = None,
    output_segment_layer: str | None = None,
    output_motion_version_id: str | None = None,
    falloff_before: int = 20,
    falloff_after: int = 20,
    global_weight: float = 0.35,
    edited_body_weight: float = 1.0,
    fps: float = 50.0,
    overwrite: bool = False,
    dry_run: bool = False,
    register_motion_version: bool = False,
    build_canonical: bool = False,
    allow_draft: bool = False,
    allow_free: bool = False,
    fullbody_solver: str = "ik_subprocess",
    contact_laplacian_iters: int = 8,
    contact_laplacian_damping: float = 1.0e-4,
    contact_laplacian_trust: float = 0.05,
    edit_contact_weight: float = 1000.0,
    fixed_contact_weight: float = 1000.0,
    temporal_laplacian_weight: float = 40.0,
    body_relative_weight: float = 10.0,
    q_prior_weight: float = 0.02,
    q_smooth_weight: float = 0.0,
    mesh_laplacian_weight: float = 1.0,
    contact_laplacian_proxy_only: bool = False,
    lte_repo_root: str | Path | None = None,
    ik_script: str | Path | None = None,
    ik_conda_env: str = "env_somaforge",
    ik_max_nfev: int | None = None,
    ik_q_prior_weight: float = 12.0,
    ik_q_smooth_weight: float = 60.0,
    intermediate_dir: str | Path | None = None,
    layers_root: Path = LAYERS_ROOT,
    progress_callback: Callable[[str], None] | None = None,
) -> LteGenerationResult:
    def report(stage: str) -> None:
        if progress_callback is not None:
            progress_callback(stage)

    report("validating")
    if mode not in {"lte_windowed", "lte_fullbody"}:
        raise NotImplementedError(f"unsupported LTE generation mode: {mode}")
    if plan.status not in {"validated", "locked"} and not allow_draft:
        raise ValueError("contact edit plan must be validated or locked; pass allow_draft=True to override")
    validate_contact_edit_plan(plan, allow_free=allow_free)
    out = Path(output_motion_path).expanduser().resolve()
    if out.exists() and not overwrite and not dry_run:
        raise FileExistsError(f"{out} already exists; pass --overwrite to replace it")
    source_motion = Path(plan.source_motion_path).expanduser()
    if not source_motion.exists():
        raise FileNotFoundError(source_motion)
    _validate_source_robot_asset(source_motion)
    graph = read_contact_graph(layers_root / (source_contact_layer or plan.source_contact_layer), plan.source_motion_id)
    edits = [ContactAnchorEditRecord(**raw) for raw in plan.edits]
    edits.extend(_surface_transform_anchor_edits(plan, graph))
    if mode == "lte_fullbody":
        if fullbody_solver not in {"ik_subprocess", "batch_contact_laplacian"}:
            raise ValueError("fullbody_solver must be 'ik_subprocess' or 'batch_contact_laplacian'")
        batch_config = BatchContactLaplacianConfig(
            num_iters=int(contact_laplacian_iters),
            damping=float(contact_laplacian_damping),
            trust_region=float(contact_laplacian_trust),
            edit_contact_weight=float(edit_contact_weight),
            fixed_contact_weight=float(fixed_contact_weight),
            temporal_laplacian_weight=float(temporal_laplacian_weight),
            body_relative_weight=float(body_relative_weight),
            q_prior_weight=float(q_prior_weight),
            q_smooth_weight=float(q_smooth_weight),
            mesh_laplacian_weight=float(mesh_laplacian_weight),
        )
        if fullbody_solver == "batch_contact_laplacian":
            if dry_run:
                return LteGenerationResult(
                    output_motion_path=out,
                    output_contact_layer=output_contact_layer,
                    output_segment_layer=output_segment_layer,
                    output_motion_version_id=output_motion_version_id,
                    warnings=[
                        "would run experimental body_pos_w proxy batch contact-Laplacian",
                        f"iters={batch_config.num_iters} trust={batch_config.trust_region} mesh_weight={batch_config.mesh_laplacian_weight}",
                    ],
                )
            report("loading_motion")
            motion = _load_motion_npz(source_motion)
            resolved_force_source = force_source_motion_path or plan.metadata.get("contact_force_source_path")
            force_motion = _load_motion_npz(resolved_force_source) if resolved_force_source else None
            if force_motion is not None:
                force_frames = np.asarray(force_motion.get("joint_pos", force_motion.get("qpos"))).shape[0]
                motion_frames = np.asarray(motion.get("joint_pos", motion.get("qpos"))).shape[0]
                if force_frames != motion_frames:
                    raise ValueError(
                        f"force source frame count {force_frames} does not match clean motion {motion_frames}"
                    )
            report("contact_laplacian")
            generated, warnings, _batch_metadata = _batch_contact_laplacian_proxy_motion(
                motion=motion,
                force_motion=force_motion,
                force_source_path=resolved_force_source,
                source_motion=source_motion,
                graph=graph,
                contact_layer_root=layers_root / (source_contact_layer or plan.source_contact_layer),
                edits=edits,
                config=batch_config,
                source_plan_path=source_plan_path,
                plan=plan,
            )
            if contact_laplacian_proxy_only:
                proxy_metadata = json.loads(generated["motion_edit_generation_metadata"].item())
                proxy_metadata["output_kind"] = "bodyspace_proxy_only"
                proxy_metadata["joint_consistency"] = "not guaranteed"
                proxy_warnings = list(warnings)
                proxy_warnings.append(
                    "experimental body_pos_w proxy output; joint/orientation "
                    "fields are not regenerated"
                )
                proxy_warnings.append("contact-Laplacian proxy-only output is not q/joint consistent")
                proxy_metadata["warnings"] = proxy_warnings
                generated["motion_edit_generation_metadata"] = _json_npz_value(proxy_metadata)
                warnings = proxy_warnings
            else:
                report("writing_intermediates")
                proxy_metadata = json.loads(generated["motion_edit_generation_metadata"].item())
                lte_path, taskspace_path, ik_path = _write_contact_laplacian_intermediates(
                    out=out,
                    intermediate_dir=intermediate_dir,
                    proxy_taskspace=generated,
                    metadata=proxy_metadata,
                    graph=graph,
                )
                report("fullbody_ik")
                _run_fullbody_ik_subprocess(
                    lte_path=lte_path,
                    ik_output_path=ik_path,
                    lte_repo_root=lte_repo_root,
                    ik_script=ik_script,
                    ik_conda_env=ik_conda_env,
                    ik_max_nfev=ik_max_nfev,
                    ik_q_prior_weight=ik_q_prior_weight,
                    ik_q_smooth_weight=ik_q_smooth_weight,
                )
                if not ik_path.exists():
                    raise FileNotFoundError(f"fullbody IK did not produce {ik_path}")
                ik_motion = _load_motion_npz(ik_path)
                report("merging_ik")
                generated = _merge_contact_laplacian_ik_output(
                    proxy_taskspace=generated,
                    ik_motion=ik_motion,
                    metadata=proxy_metadata,
                    lte_path=lte_path,
                    taskspace_path=taskspace_path,
                    ik_path=ik_path,
                    ik_conda_env=ik_conda_env,
                    ik_script=ik_script,
                    lte_repo_root=lte_repo_root,
                )
                final_metadata = json.loads(generated["motion_edit_generation_metadata"].item())
                final_metadata["ik_backend"] = str(np.asarray(ik_motion.get("ik_backend", np.asarray("pyroki_internal"))).reshape(-1)[0])
                final_metadata["fullbody_ik_regularization"] = {
                    "pose_prior_weight": float(ik_q_prior_weight),
                    "temporal_laplacian_weight": float(ik_q_smooth_weight),
                }
                generated["motion_edit_generation_metadata"] = _json_npz_value(final_metadata)
                warnings = final_metadata.get("warnings", warnings)
            report("writing_output")
            out.parent.mkdir(parents=True, exist_ok=True)
            np.savez(out, **_stamp_robot_asset(generated))
            edited_graph = _apply_anchor_edits_to_graph(graph, edits)
            if output_contact_layer:
                write_contact_layer(layers_root / output_contact_layer, edited_graph)
            if output_segment_layer:
                segments = _candidate_segments_from_graph(
                    edited_graph,
                    motion_path=str(out),
                    motion_version_id=output_motion_version_id,
                    plan_id=plan.plan_id,
                    source=mode,
                    fullbody_solver=fullbody_solver,
                )
                write_layer(layers_root / output_segment_layer / f"{edited_graph.motion_id}.jsonl", segments)
            if register_motion_version:
                report("registering")
                if not output_motion_version_id:
                    raise ValueError("--output-motion-version-id is required with --register-motion-version")
                write_motion_version(
                    MotionVersionRecord(
                        motion_version_id=output_motion_version_id,
                        motion_path=str(out),
                        kind="augmented",
                        base_motion_id=plan.source_motion_id,
                        contact_layer=output_contact_layer,
                        edit_plan_id=plan.plan_id,
                        metadata={"source_contact_edit_plan": plan.plan_id, "generation_mode": mode, "fullbody_solver": fullbody_solver},
                    )
                )
            report("complete")
            return LteGenerationResult(
                output_motion_path=out,
                output_contact_layer=output_contact_layer,
                output_segment_layer=output_segment_layer,
                output_motion_version_id=output_motion_version_id,
                warnings=warnings,
            )
        motion = _load_motion_npz(source_motion)
        original_keypoints = _semantic_keypoints_from_motion(motion)
        solver_keypoints = _legacy_lte_solver_keypoints(original_keypoints)
        handles = _handles_from_contact_edits(edits, solver_keypoints, graph=graph)
        legacy_lte = _import_legacy_lte_module(lte_repo_root)
        result = legacy_lte.deform_demo_with_contact_handles_lte(
            solver_keypoints,
            handles,
            weights={"handle_weight": 1100.0, "body_relative_weight": 40.0, "smooth_offset_weight": 5.0},
            config={"names": LTE_HANDLE_KEYPOINT_NAMES, "fix_start_root": True, "use_body_relative_edges": True},
        )
        edited_keypoints = _merge_solver_keypoints(original_keypoints, result["edited_keypoints"])
        work_dir = Path(intermediate_dir).expanduser() if intermediate_dir is not None else out.with_suffix("")
        lte_path = work_dir / f"{out.stem}.lte_keypoints.npz"
        taskspace_path = work_dir / f"{out.stem}.taskspace_motion.npz"
        ik_path = work_dir / f"{out.stem}.fullbody_ik_motion.npz"
        if dry_run:
            return LteGenerationResult(
                output_motion_path=out,
                output_contact_layer=output_contact_layer,
                output_segment_layer=output_segment_layer,
                output_motion_version_id=output_motion_version_id,
                warnings=[f"would write LTE keypoints {lte_path}", f"would run fullbody IK to {ik_path}"],
            )
        work_dir.mkdir(parents=True, exist_ok=True)
        _save_lte_keypoints(lte_path, keypoints=edited_keypoints, motion=motion, source_motion=source_motion, edits=edits, graph=graph)
        taskspace = _dense_taskspace_from_keypoints(motion, original_keypoints, edited_keypoints, source_motion, lte_path)
        _copy_contact_force_payload_with_edits(
            taskspace,
            motion=motion,
            edits=edits,
            n_frames=len(next(iter(edited_keypoints.values()))),
        )
        np.savez(taskspace_path, **taskspace)
        _run_fullbody_ik_subprocess(
            lte_path=lte_path,
            ik_output_path=ik_path,
            lte_repo_root=lte_repo_root,
            ik_script=ik_script,
            ik_conda_env=ik_conda_env,
            ik_max_nfev=ik_max_nfev,
            ik_q_prior_weight=ik_q_prior_weight,
            ik_q_smooth_weight=ik_q_smooth_weight,
        )
        if not ik_path.exists():
            raise FileNotFoundError(f"fullbody IK did not produce {ik_path}")
        generated = dict(taskspace)
        fullbody = _load_motion_npz(ik_path)
        for key in ("joint_pos", "joint_vel", "joint_names", "is_qpos"):
            if key in fullbody:
                generated[key] = fullbody[key]
        warnings = ["lte_fullbody generated taskspace keypoints and ran fullbody IK"]
        metadata = {
            "source_plan": str(Path(source_plan_path).expanduser()) if source_plan_path is not None else plan.plan_id,
            "source_plan_id": plan.plan_id,
            "source_motion": str(source_motion),
            "generation_mode": mode,
            "lte_keypoints": str(lte_path),
            "taskspace_motion": str(taskspace_path),
            "fullbody_ik_motion": str(ik_path),
            "ik_conda_env": ik_conda_env,
            "ik_script": str(Path(ik_script).expanduser()) if ik_script else str((Path(lte_repo_root or "/home/xiaz/lte").expanduser() / "scripts" / "solve_lte_fullbody_ik.py")),
            "num_edits": len(edits),
            "fullbody_solver": fullbody_solver,
            "contact_laplacian_config": batch_config.__dict__,
            "moving_contact_handle_count": sum(1 for handle in handles if handle.get("kind") == "edited_contact"),
            "fixed_contact_handle_count": sum(1 for handle in handles if handle.get("kind") == "fixed_contact"),
            "zero_delta_fixed_handle_count": sum(1 for handle in handles if handle.get("zero_delta_edit")),
            "foot_orientation_targets": [key for key in ("orientation_target_left_foot", "orientation_target_right_foot") if key in _foot_orientation_target_arrays(motion, len(next(iter(edited_keypoints.values()))))],
            "foot_stabilization": {
                "foot_orientation_weight": 20.0,
                "contact_foot_orientation_weight": 80.0,
                "foot_toe_weight": 20.0,
                "contact_foot_toe_weight": 120.0,
            },
            "warnings": warnings,
            "edits": [edit.to_dict() for edit in edits],
            "lte_debug": result.get("debug", {}),
        }
        generated["motion_edit_generation_metadata"] = _json_npz_value(metadata)
        generated["source_motion_path"] = np.asarray(str(source_motion), dtype=object)
        generated["source_contact_edit_plan"] = np.asarray(plan.plan_id, dtype=object)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez(out, **_stamp_robot_asset(generated))
        edited_graph = _apply_anchor_edits_to_graph(graph, edits)
        if output_contact_layer:
            write_contact_layer(layers_root / output_contact_layer, edited_graph)
        if output_segment_layer:
            segments = _candidate_segments_from_graph(
                edited_graph,
                motion_path=str(out),
                motion_version_id=output_motion_version_id,
                plan_id=plan.plan_id,
                source=mode,
                fullbody_solver=fullbody_solver,
            )
            write_layer(layers_root / output_segment_layer / f"{edited_graph.motion_id}.jsonl", segments)
        if register_motion_version:
            if not output_motion_version_id:
                raise ValueError("--output-motion-version-id is required with --register-motion-version")
            write_motion_version(
                MotionVersionRecord(
                    motion_version_id=output_motion_version_id,
                    motion_path=str(out),
                    kind="augmented",
                    base_motion_id=plan.source_motion_id,
                    contact_layer=output_contact_layer,
                    edit_plan_id=plan.plan_id,
                    metadata={"source_contact_edit_plan": plan.plan_id, "generation_mode": mode, "fullbody_solver": fullbody_solver},
                )
            )
        return LteGenerationResult(
            output_motion_path=out,
            output_contact_layer=output_contact_layer,
            output_segment_layer=output_segment_layer,
            output_motion_version_id=output_motion_version_id,
            warnings=warnings,
        )
    motion = _load_motion_npz(source_motion)
    if "body_pos_w" not in motion:
        raise ValueError("LTE augmentation requires body_pos_w or a supported world-space body position array.")
    body_pos = np.asarray(motion["body_pos_w"])
    if body_pos.ndim != 3 or body_pos.shape[2] != 3:
        raise ValueError(f"body_pos_w must have shape [T,B,3], got {body_pos.shape}")
    n_frames, n_bodies, _ = body_pos.shape
    anchors_by_id = {anchor.anchor_id: anchor for anchor in graph.anchors}
    warnings: list[str] = []
    displacement = np.zeros((n_frames, n_bodies, 3), dtype=np.float64)
    edit_summaries: list[dict[str, Any]] = []
    for edit in edits:
        anchor = anchors_by_id.get(edit.anchor_id)
        if anchor is None:
            raise ValueError(f"{edit.edit_id}: anchor not found in source contact graph: {edit.anchor_id}")
        body = edit.body or anchor.body
        body_index = resolve_body_index(motion, body)
        start, end = _edit_interval(edit, anchor)
        if start < 0 or end > n_frames:
            raise ValueError(f"{edit.edit_id}: affected frames [{start}, {end}] outside motion length {n_frames}")
        delta = _edit_delta(edit)
        weights = _window_weights(n_frames, start, end, falloff_before=falloff_before, falloff_after=falloff_after)
        displacement += weights[:, None, None] * delta[None, None, :] * float(global_weight)
        body_extra = float(edited_body_weight) - float(global_weight)
        displacement[:, body_index, :] += weights[:, None] * delta[None, :] * body_extra
        max_delta = float(np.linalg.norm(delta))
        if max_delta > 0.5:
            warnings.append(f"{edit.edit_id}: large requested displacement {max_delta:.3f}m")
        edit_summaries.append(
            {
                "edit_id": edit.edit_id,
                "anchor_id": edit.anchor_id,
                "body": body,
                "body_index": body_index,
                "affected_frames": [start, end],
                "delta_world": delta.tolist(),
                "surface_id": edit.surface_id,
                "object_id": anchor.object_id,
            }
        )
    if dry_run:
        return LteGenerationResult(
            output_motion_path=out,
            output_contact_layer=output_contact_layer,
            output_segment_layer=output_segment_layer,
            output_motion_version_id=output_motion_version_id,
            warnings=warnings,
        )
    generated = dict(motion)
    edited_body_pos = (body_pos.astype(np.float64, copy=False) + displacement).astype(body_pos.dtype, copy=False)
    generated["body_pos_w"] = edited_body_pos
    actual_fps = _fps_from_motion(motion, fps)
    if "body_lin_vel_w" in generated:
        generated["body_lin_vel_w"] = _recompute_linear_velocity(edited_body_pos.astype(np.float64), actual_fps, np.asarray(generated["body_lin_vel_w"]).dtype)
    if "ref_pos_w" in generated and np.asarray(generated["ref_pos_w"]).shape == body_pos.shape:
        generated["ref_pos_w"] = edited_body_pos.astype(np.asarray(generated["ref_pos_w"]).dtype, copy=False)
    elif "ref_pos_w" in generated:
        warnings.append("ref_pos_w preserved because its body mapping/shape is not compatible with body_pos_w")
    if "body_quat_w" in generated or "body_ang_vel_w" in generated:
        warnings.append("orientation fields preserved; position-only LTE augmentation")
    if "joint_pos" in generated or "joint_vel" in generated:
        warnings.append("joint trajectories are preserved; generated motion is a reference deformation, not IK-retargeted motion")
    metadata = {
        "source_plan": str(Path(source_plan_path).expanduser()) if source_plan_path is not None else plan.plan_id,
        "source_plan_id": plan.plan_id,
        "source_motion": str(source_motion),
        "generation_mode": mode,
        "num_edits": len(edits),
        "falloff_before": int(falloff_before),
        "falloff_after": int(falloff_after),
        "global_weight": float(global_weight),
        "edited_body_weight": float(edited_body_weight),
        "warnings": warnings,
        "edits": edit_summaries,
    }
    generated["motion_edit_generation_metadata"] = _json_npz_value(metadata)
    generated["source_motion_path"] = np.asarray(str(source_motion), dtype=object)
    generated["source_contact_edit_plan"] = np.asarray(plan.plan_id, dtype=object)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out, **_stamp_robot_asset(generated))

    edited_graph = _apply_anchor_edits_to_graph(graph, edits)
    if output_contact_layer:
        write_contact_layer(layers_root / output_contact_layer, edited_graph)
    if output_segment_layer:
        segments = _candidate_segments_from_graph(
            edited_graph,
            motion_path=str(out),
            motion_version_id=output_motion_version_id,
            plan_id=plan.plan_id,
            source=mode,
        )
        write_layer(layers_root / output_segment_layer / f"{edited_graph.motion_id}.jsonl", segments)
    if register_motion_version:
        if not output_motion_version_id:
            raise ValueError("--output-motion-version-id is required with --register-motion-version")
        if build_canonical:
            canonical_segments = _candidate_segments_from_graph(
                edited_graph,
                motion_path=str(out),
                motion_version_id=output_motion_version_id,
                plan_id=plan.plan_id,
                source=mode,
            )
            record, _segment_path = write_motion_version_with_canonical_segments(
                motion_version_id=output_motion_version_id,
                motion_path=str(out),
                contact_layer=output_contact_layer or "",
                segments=canonical_segments,
                kind="augmented",
                base_motion_id=plan.source_motion_id,
                source=mode,
                reason=f"build canonical from ContactEditPlan {plan.plan_id}",
            )
            write_motion_version(
                MotionVersionRecord(
                    motion_version_id=record.motion_version_id,
                    motion_path=record.motion_path,
                    kind="augmented",
                    base_motion_id=plan.source_motion_id,
                    motion_asset_id=record.motion_asset_id,
                    parent_motion_version_id=record.parent_motion_version_id,
                    contact_layer=record.contact_layer,
                    canonical_segment_path=record.canonical_segment_path,
                    token_catalog_path=record.token_catalog_path,
                    edit_plan_id=plan.plan_id,
                    metadata={"source_contact_edit_plan": plan.plan_id, "generation_mode": mode},
                )
            )
        else:
            write_motion_version(
                MotionVersionRecord(
                    motion_version_id=output_motion_version_id,
                    motion_path=str(out),
                    kind="augmented",
                    base_motion_id=plan.source_motion_id,
                    contact_layer=output_contact_layer,
                    edit_plan_id=plan.plan_id,
                    metadata={"source_contact_edit_plan": plan.plan_id, "generation_mode": mode},
                )
            )
    return LteGenerationResult(
        output_motion_path=out,
        output_contact_layer=output_contact_layer,
        output_segment_layer=output_segment_layer,
        output_motion_version_id=output_motion_version_id,
        warnings=warnings,
    )
