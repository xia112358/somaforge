from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from motion_edit.generation.taskspace_spec import ContactAwareTaskspaceMotion
from somaforge_core.kinematics import angular_velocity_wxyz, body_velocities_from_pose


SEMANTIC_LINK_ALIASES: dict[str, tuple[str, ...]] = {
    "pelvis": ("pelvis",),
    "left_hip": ("left_hip_roll_link", "left_hip_pitch_link", "left_hip_yaw_link"),
    "left_knee": ("left_knee_link",),
    "left_foot": ("left_ankle_roll_link", "left_ankle_roll_sphere_1_link"),
    "right_hip": ("right_hip_roll_link", "right_hip_pitch_link", "right_hip_yaw_link"),
    "right_knee": ("right_knee_link",),
    "right_foot": ("right_ankle_roll_link", "right_ankle_roll_sphere_1_link"),
    "torso": ("torso_link",),
    "left_shoulder": ("left_shoulder_roll_link", "left_shoulder_pitch_link"),
    "left_elbow": ("left_elbow_link",),
    "left_hand": ("left_sphere_hand_tip_link", "left_sphere_hand_link", "left_rubber_hand_link", "left_wrist_yaw_link"),
    "right_shoulder": ("right_shoulder_roll_link", "right_shoulder_pitch_link"),
    "right_elbow": ("right_elbow_link",),
    "right_hand": ("right_sphere_hand_tip_link", "right_sphere_hand_link", "right_rubber_hand_link", "right_wrist_yaw_link"),
}

SEMANTIC_DEFAULT_WEIGHTS: dict[str, float] = {
    "pelvis": 10.0,
    "torso": 5.0,
    "left_hip": 2.0,
    "right_hip": 2.0,
    "left_knee": 4.0,
    "right_knee": 4.0,
    "left_foot": 8.0,
    "right_foot": 8.0,
    "left_shoulder": 2.0,
    "right_shoulder": 2.0,
    "left_elbow": 3.0,
    "right_elbow": 3.0,
    "left_hand": 5.0,
    "right_hand": 5.0,
}


@dataclass(frozen=True)
class CompiledPyrokiTaskspace:
    semantic_names: tuple[str, ...]
    semantic_link_indices: np.ndarray
    semantic_targets_w: np.ndarray
    semantic_weights: np.ndarray

    contact_link_indices: np.ndarray
    contact_points_local: np.ndarray
    contact_targets_w: np.ndarray
    contact_weights: np.ndarray

    unresolved_semantics: tuple[str, ...]
    unresolved_contacts: tuple[str, ...]

    @property
    def frame_count(self) -> int:
        return int(self.semantic_targets_w.shape[0])

    @property
    def max_contact_points_per_frame(self) -> int:
        return int(self.contact_points_local.shape[1])

    def validate(self) -> None:
        t = self.frame_count
        k = len(self.semantic_names)
        if self.semantic_link_indices.shape != (k,):
            raise ValueError("semantic_link_indices must have shape [K]")
        if self.semantic_targets_w.shape != (t, k, 3):
            raise ValueError("semantic_targets_w must have shape [T,K,3]")
        if self.semantic_weights.shape != (t, k):
            raise ValueError("semantic_weights must have shape [T,K]")
        c = self.max_contact_points_per_frame
        if self.contact_link_indices.shape != (t, c):
            raise ValueError("contact_link_indices must have shape [T,C]")
        if self.contact_points_local.shape != (t, c, 3):
            raise ValueError("contact_points_local must have shape [T,C,3]")
        if self.contact_targets_w.shape != (t, c, 3):
            raise ValueError("contact_targets_w must have shape [T,C,3]")
        if self.contact_weights.shape != (t, c):
            raise ValueError("contact_weights must have shape [T,C]")
        for value in (
            self.semantic_targets_w,
            self.semantic_weights,
            self.contact_points_local,
            self.contact_targets_w,
            self.contact_weights,
        ):
            if not np.all(np.isfinite(value)):
                raise ValueError("compiled task-space targets contain non-finite values")
        if np.any(self.semantic_weights < 0.0) or np.any(self.contact_weights < 0.0):
            raise ValueError("compiled task-space weights must be nonnegative")


def compile_pyroki_taskspace(
    spec: ContactAwareTaskspaceMotion,
    link_names: Sequence[str],
    *,
    edited_contact_weight: float = 100.0,
    fixed_contact_weight: float = 80.0,
) -> CompiledPyrokiTaskspace:
    """Resolve a contact-aware task-space motion against one PyRoki link list."""

    spec.validate()
    links = tuple(str(name) for name in link_names)
    semantic_names: list[str] = []
    semantic_indices: list[int] = []
    semantic_columns: list[int] = []
    unresolved_semantics: list[str] = []
    for column, name in enumerate(spec.semantic_names):
        index = resolve_link_index(links, name, SEMANTIC_LINK_ALIASES.get(name, (name,)))
        if index is None:
            unresolved_semantics.append(name)
            continue
        semantic_names.append(name)
        semantic_indices.append(index)
        semantic_columns.append(column)
    if not semantic_indices:
        raise ValueError("no task-space semantic targets resolve against the PyRoki robot links")

    semantic_targets = np.asarray(spec.semantic_targets_w, dtype=np.float64)[:, semantic_columns, :]
    semantic_weights = np.asarray(spec.semantic_weights, dtype=np.float64)[:, semantic_columns]
    semantic_weights = semantic_weights * np.asarray(
        [SEMANTIC_DEFAULT_WEIGHTS.get(name, 1.0) for name in semantic_names], dtype=np.float64
    )[None, :]

    per_frame: list[list[tuple[int, np.ndarray, np.ndarray, float]]] = [list() for _ in range(spec.frame_count)]
    unresolved_contacts: list[str] = []
    for contact in spec.contacts:
        link_index = resolve_link_index(links, contact.body_label, (contact.body_label,))
        if link_index is None:
            unresolved_contacts.append(f"{contact.anchor_id}:{contact.body_label}")
            continue
        targets_w = contact.resolved_target_points_w()
        points_local = np.asarray(contact.points_local, dtype=np.float64)
        points_local_by_frame = (
            np.asarray(contact.points_local_by_frame, dtype=np.float64)
            if contact.points_local_by_frame is not None
            else None
        )
        local_frames = np.asarray(contact.frames, dtype=np.int64) - int(spec.frame_start)
        weight = float(edited_contact_weight if contact.kind == "edited_contact" else fixed_contact_weight)
        for contact_frame_index, local_frame in enumerate(local_frames.tolist()):
            if not 0 <= local_frame < spec.frame_count:
                raise ValueError(f"{contact.anchor_id}: frame {local_frame} lies outside the solve window")
            for point_index in range(points_local.shape[0]):
                per_frame[local_frame].append(
                    (
                        link_index,
                        (
                            points_local_by_frame[contact_frame_index, point_index]
                            if points_local_by_frame is not None
                            else points_local[point_index]
                        ),
                        targets_w[contact_frame_index, point_index],
                        weight,
                    )
                )

    max_contacts = max(1, max((len(items) for items in per_frame), default=0))
    contact_link_indices = np.zeros((spec.frame_count, max_contacts), dtype=np.int32)
    contact_points_local = np.zeros((spec.frame_count, max_contacts, 3), dtype=np.float64)
    contact_targets_w = np.zeros((spec.frame_count, max_contacts, 3), dtype=np.float64)
    contact_weights = np.zeros((spec.frame_count, max_contacts), dtype=np.float64)
    for frame, items in enumerate(per_frame):
        for index, (link_index, point_local, target_w, weight) in enumerate(items):
            contact_link_indices[frame, index] = int(link_index)
            contact_points_local[frame, index] = point_local
            contact_targets_w[frame, index] = target_w
            contact_weights[frame, index] = weight

    compiled = CompiledPyrokiTaskspace(
        semantic_names=tuple(semantic_names),
        semantic_link_indices=np.asarray(semantic_indices, dtype=np.int32),
        semantic_targets_w=semantic_targets,
        semantic_weights=semantic_weights,
        contact_link_indices=contact_link_indices,
        contact_points_local=contact_points_local,
        contact_targets_w=contact_targets_w,
        contact_weights=contact_weights,
        unresolved_semantics=tuple(unresolved_semantics),
        unresolved_contacts=tuple(unresolved_contacts),
    )
    compiled.validate()
    return compiled


def resolve_link_index(link_names: Sequence[str], label: str, aliases: Sequence[str]) -> int | None:
    links = tuple(str(name) for name in link_names)
    lowered = [name.lower() for name in links]
    candidates: list[str] = []
    for value in (label, *aliases):
        leaf = str(value).rstrip("/").split("/")[-1]
        if leaf and leaf not in candidates:
            candidates.append(leaf)
    for candidate in candidates:
        key = candidate.lower()
        if key in lowered:
            return lowered.index(key)
    for candidate in candidates:
        key = candidate.lower()
        for index, name in enumerate(lowered):
            if key and (key in name or name in key):
                return index
    return None


def quat_mul_wxyz(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    aw, ax, ay, az = np.moveaxis(a, -1, 0)
    bw, bx, by, bz = np.moveaxis(b, -1, 0)
    out = np.stack(
        (
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ),
        axis=-1,
    )
    return normalize_quat_wxyz(out)


def quat_apply_wxyz(quat: np.ndarray, vector: np.ndarray) -> np.ndarray:
    q = normalize_quat_wxyz(np.asarray(quat, dtype=np.float64))
    v = np.asarray(vector, dtype=np.float64)
    qvec = q[..., 1:4]
    uv = np.cross(qvec, v)
    uuv = np.cross(qvec, uv)
    return v + 2.0 * (q[..., :1] * uv + uuv)


def normalize_quat_wxyz(quat: np.ndarray) -> np.ndarray:
    q = np.asarray(quat, dtype=np.float64)
    return q / np.maximum(np.linalg.norm(q, axis=-1, keepdims=True), 1.0e-12)


def world_body_poses_from_pyroki_fk(root_qpos: np.ndarray, link_poses_base_wxyz_xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compose PyRoki base-frame link poses with Holosoma floating-root poses."""

    root = np.asarray(root_qpos, dtype=np.float64)
    fk = np.asarray(link_poses_base_wxyz_xyz, dtype=np.float64)
    if root.ndim != 2 or root.shape[1] != 7:
        raise ValueError(f"root_qpos must have shape [T,7], got {root.shape}")
    if fk.ndim != 3 or fk.shape[0] != root.shape[0] or fk.shape[2] != 7:
        raise ValueError(f"link_poses_base_wxyz_xyz must have shape [T,B,7], got {fk.shape}")
    root_quat = normalize_quat_wxyz(root[:, 3:7])
    link_quat = normalize_quat_wxyz(fk[:, :, :4])
    link_pos = fk[:, :, 4:7]
    body_quat_w = quat_mul_wxyz(root_quat[:, None, :], link_quat)
    body_pos_w = root[:, None, :3] + quat_apply_wxyz(root_quat[:, None, :], link_pos)
    return body_pos_w.astype(np.float32), body_quat_w.astype(np.float32)


def holosoma_joint_velocities(qpos: np.ndarray, fps: float) -> np.ndarray:
    """Differentiate Holosoma qpos into [root linear, root angular, joints]."""

    q = np.asarray(qpos, dtype=np.float64)
    if q.ndim != 2 or q.shape[1] < 7:
        raise ValueError(f"qpos must have shape [T,7+J], got {q.shape}")
    if not np.isfinite(fps) or fps <= 0.0:
        raise ValueError(f"fps must be finite and positive, got {fps}")
    if q.shape[0] == 1:
        return np.zeros((1, q.shape[1] - 1), dtype=np.float32)
    dt = 1.0 / float(fps)
    root_lin = np.gradient(q[:, :3], dt, axis=0)
    root_ang = angular_velocity_wxyz(normalize_quat_wxyz(q[:, 3:7]), dt)
    joint_vel = np.gradient(q[:, 7:], dt, axis=0)
    return np.concatenate([root_lin, root_ang, joint_vel], axis=1).astype(np.float32)


def holosoma_body_velocities(body_pos_w: np.ndarray, body_quat_w: np.ndarray, fps: float) -> tuple[np.ndarray, np.ndarray]:
    if np.asarray(body_pos_w).shape[0] == 1:
        shape = np.asarray(body_pos_w).shape
        return np.zeros(shape, dtype=np.float32), np.zeros(shape, dtype=np.float32)
    return body_velocities_from_pose(body_pos_w, body_quat_w, fps)
