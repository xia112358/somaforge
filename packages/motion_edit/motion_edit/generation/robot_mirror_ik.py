"""Whole-trajectory IK for leading-side mirror augmentation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial.transform import Rotation
from scipy.signal import savgol_filter
from somaforge_core.robot_assets import canonical_g1_urdf_path

from motion_edit.contact import read_contact_graph
from motion_edit.contact_laplacian.omniretarget_mesh import sample_terrain_mesh_points
from motion_edit.generation.lte_fullbody import _semantic_keypoints_from_motion
from motion_edit.generation.pyroki_fullbody_ik import (
    _force_linearization_from_source,
    _resolve_force_link_groups,
    _resolve_link_groups,
    _resolve_named_link_group,
)
from motion_edit.generation.pyroki_trajectory_optimizer import (
    EnvironmentContactAnchors,
    WholeTrajectoryConfig,
    _quat_apply_numpy,
    _quat_conjugate_numpy,
    solve_whole_trajectory,
)
from motion_edit.robot_mirror import (
    ROBOT_MIRROR_SCHEMA,
    _canonicalize_quaternion_hemisphere_wxyz,
    _finite_difference_angular,
    _finite_difference_linear,
    _recompute_named_body_arrays,
    _reflect_root_local_points,
    project_contact_to_surface,
    swap_left_right_name,
)
from motion_edit.workbench.edit_handles import build_contact_episode_handles


ROBOT_MIRROR_IK_SCHEMA = "motion_edit_robot_mirror_whole_trajectory_ik_v2"
_CONTACT_PART_BY_SEMANTIC = {
    "left_hand": "LH",
    "right_hand": "RH",
}


def _dominant_rigid_contact_proxy(
    *,
    recorded_points_w: np.ndarray,
    recorded_root_qpos: np.ndarray,
    recorded_fk: np.ndarray,
    link_group: np.ndarray,
    active_frames: np.ndarray,
) -> tuple[int, np.ndarray]:
    """Choose one collision link and one robust local point for an episode."""

    group = np.asarray(link_group, dtype=np.int32).reshape(-1)
    active = np.asarray(active_frames, dtype=np.int64).reshape(-1)
    if group.size == 0 or active.size == 0:
        raise ValueError("rigid contact proxy requires links and active frames")
    nearest_links: list[int] = []
    points_base: list[np.ndarray] = []
    for frame in active:
        point_base = _quat_apply_numpy(
            _quat_conjugate_numpy(recorded_root_qpos[frame, 3:7]),
            recorded_points_w[frame] - recorded_root_qpos[frame, :3],
        )
        poses = recorded_fk[frame, group]
        nearest = int(np.argmin(np.linalg.norm(poses[:, 4:7] - point_base[None, :], axis=1)))
        nearest_links.append(int(group[nearest]))
        points_base.append(point_base)
    unique, counts = np.unique(np.asarray(nearest_links, dtype=np.int32), return_counts=True)
    dominant_link = int(unique[np.argmax(counts)])
    local_offsets = []
    for frame, nearest_link, point_base in zip(active, nearest_links, points_base, strict=True):
        if nearest_link != dominant_link:
            continue
        pose = recorded_fk[frame, dominant_link]
        local_offsets.append(
            _quat_apply_numpy(
                _quat_conjugate_numpy(pose[:4]),
                point_base - pose[4:7],
            )
        )
    if not local_offsets:
        raise ValueError("dominant collision link has no local contact samples")
    return dominant_link, np.median(np.asarray(local_offsets, dtype=np.float64), axis=0)


def _blended_contact_target(
    *,
    source_trajectory_w: np.ndarray,
    target_position_w: np.ndarray,
    contact_start: int,
    contact_end: int,
    fade_frames: int,
) -> tuple[np.ndarray, int, int]:
    """Keep contact fixed while smoothly entering and leaving the hard target."""

    source = np.asarray(source_trajectory_w, dtype=np.float64)
    target = np.asarray(target_position_w, dtype=np.float64)
    frames = int(source.shape[0])
    start = max(0, min(frames, int(contact_start)))
    end = max(start, min(frames, int(contact_end)))
    fade = max(0, int(fade_frames))
    constraint_start = max(0, start - fade)
    constraint_end = min(frames, end + fade)
    result = source.copy()
    result[start:end] = target
    pre_count = start - constraint_start
    if pre_count:
        phase = np.linspace(0.0, 1.0, pre_count + 1, dtype=np.float64)[:-1]
        weight = phase * phase * (3.0 - 2.0 * phase)
        result[constraint_start:start] = (
            source[constraint_start:start]
            + weight[:, None] * (target[None, :] - source[constraint_start:start])
        )
    post_count = constraint_end - end
    if post_count:
        phase = np.linspace(1.0, 0.0, post_count + 1, dtype=np.float64)[1:]
        weight = phase * phase * (3.0 - 2.0 * phase)
        result[end:constraint_end] = (
            source[end:constraint_end]
            + weight[:, None] * (target[None, :] - source[end:constraint_end])
        )
    return result, constraint_start, constraint_end


def _smoothed_contact_trajectory(
    *,
    recorded_positions_w: np.ndarray,
    active_frames: np.ndarray,
    contact_start: int,
    contact_end: int,
    handle_position_w: np.ndarray,
    surface_origin_w: np.ndarray,
    surface_normal_w: np.ndarray,
    smoothing_window: int = 51,
) -> np.ndarray:
    """Interpolate contact dropouts and smooth the trajectory represented by one handle."""

    recorded = np.asarray(recorded_positions_w, dtype=np.float64)
    active = np.asarray(active_frames, dtype=np.int64).reshape(-1)
    start = int(contact_start)
    end = int(contact_end)
    if end <= start or active.size == 0:
        raise ValueError("contact trajectory requires a non-empty interval and active samples")
    frame_axis = np.arange(start, end, dtype=np.float64)
    trajectory = np.stack(
        [np.interp(frame_axis, active, recorded[active, axis]) for axis in range(3)],
        axis=1,
    )
    max_window = len(trajectory) if len(trajectory) % 2 == 1 else len(trajectory) - 1
    window = min(max(3, int(smoothing_window) | 1), max_window)
    if window >= 5:
        trajectory = savgol_filter(trajectory, window_length=window, polyorder=3, axis=0, mode="interp")

    origin = np.asarray(surface_origin_w, dtype=np.float64)
    normal = np.asarray(surface_normal_w, dtype=np.float64)
    normal /= np.linalg.norm(normal)
    trajectory -= np.einsum("ti,i->t", trajectory - origin, normal)[:, None] * normal[None, :]
    handle = np.asarray(handle_position_w, dtype=np.float64)
    translation = handle - np.mean(trajectory, axis=0)
    translation -= float(np.dot(translation, normal)) * normal
    trajectory += translation
    return trajectory


def _project_trajectory_to_surface(
    trajectory_w: np.ndarray,
    *,
    surface_origin_w: np.ndarray,
    surface_normal_w: np.ndarray,
) -> np.ndarray:
    trajectory = np.asarray(trajectory_w, dtype=np.float64).copy()
    origin = np.asarray(surface_origin_w, dtype=np.float64)
    normal = np.asarray(surface_normal_w, dtype=np.float64)
    normal /= np.linalg.norm(normal)
    signed_distance = np.einsum("ti,i->t", trajectory - origin, normal)
    trajectory -= signed_distance[:, None] * normal[None, :]
    return trajectory


def _interpolate_smooth_vectors(
    *,
    values: np.ndarray,
    active_frames: np.ndarray,
    start_frame: int,
    end_frame: int,
    smoothing_window: int = 51,
) -> np.ndarray:
    value = np.asarray(values, dtype=np.float64)
    active = np.asarray(active_frames, dtype=np.int64).reshape(-1)
    start = int(start_frame)
    end = int(end_frame)
    if active.size == 0 or end <= start:
        raise ValueError("vector interpolation requires active samples and a non-empty interval")
    frame_axis = np.arange(start, end, dtype=np.float64)
    result = np.stack(
        [np.interp(frame_axis, active, value[active, axis]) for axis in range(value.shape[1])],
        axis=1,
    )
    max_window = len(result) if len(result) % 2 == 1 else len(result) - 1
    window = min(max(3, int(smoothing_window) | 1), max_window)
    if window >= 5:
        result = savgol_filter(result, window_length=window, polyorder=3, axis=0, mode="interp")
    return result


def _stabilized_hand_force(
    *,
    recorded_force: dict[str, Any],
    graph: Any,
    end_frame: int | None,
    smoothing_window: int = 51,
) -> dict[str, Any]:
    """Fill short hand-contact mask gaps and smooth force directions per episode."""

    payload = {key: np.asarray(value).copy() for key, value in recorded_force.items()}
    part_order = [str(value) for value in np.asarray(payload["contact_force_part_order"]).reshape(-1)]
    force = np.asarray(payload["contact_force_part_w"], dtype=np.float64).copy()
    mask = np.asarray(payload["contact_force_part_mask"], dtype=bool).copy()
    valid = np.asarray(payload["contact_force_part_position_valid"], dtype=bool)
    frames = int(force.shape[0])
    handles = [
        handle
        for handle in build_contact_episode_handles(
            graph.anchors,
            max_gap_frames=10,
            min_duration_frames=20,
        )
        if handle.body in _CONTACT_PART_BY_SEMANTIC
        and (end_frame is None or int(handle.start_frame) < int(end_frame))
    ]
    for handle in handles:
        part_name = _CONTACT_PART_BY_SEMANTIC[handle.body]
        if part_name not in part_order:
            raise ValueError(f"recorded contact force has no {part_name!r} part")
        part_index = part_order.index(part_name)
        start = max(0, int(handle.start_frame))
        end = min(frames, int(handle.end_frame), frames if end_frame is None else int(end_frame))
        active = mask[:, part_index] & valid[:, part_index]
        active_frames = np.flatnonzero(active[start:end]) + start
        force[start:end, part_index] = _interpolate_smooth_vectors(
            values=force[:, part_index],
            active_frames=active_frames,
            start_frame=start,
            end_frame=end,
            smoothing_window=smoothing_window,
        )
        mask[start:end, part_index] = True
    payload["contact_force_part_w"] = force
    payload["contact_force_part_mask"] = mask
    return payload


def _blended_contact_trajectory(
    *,
    source_trajectory_w: np.ndarray,
    contact_target_w: np.ndarray,
    contact_start: int,
    contact_end: int,
    fade_frames: int,
) -> tuple[np.ndarray, int, int]:
    """Blend a time-varying contact trajectory into and out of the source motion."""

    source = np.asarray(source_trajectory_w, dtype=np.float64)
    contact_target = np.asarray(contact_target_w, dtype=np.float64)
    start = int(contact_start)
    end = int(contact_end)
    if contact_target.shape != (end - start, 3):
        raise ValueError("contact target must contain one xyz point per contact frame")
    fade = max(0, int(fade_frames))
    constraint_start = max(0, start - fade)
    constraint_end = min(len(source), end + fade)
    result = source.copy()
    result[start:end] = contact_target

    def hermite(
        p0: np.ndarray,
        v0: np.ndarray,
        p1: np.ndarray,
        v1: np.ndarray,
        steps: int,
    ) -> np.ndarray:
        phase = np.linspace(0.0, 1.0, steps + 1, dtype=np.float64)[:, None]
        h00 = 2.0 * phase**3 - 3.0 * phase**2 + 1.0
        h10 = phase**3 - 2.0 * phase**2 + phase
        h01 = -2.0 * phase**3 + 3.0 * phase**2
        h11 = phase**3 - phase**2
        return h00 * p0 + h10 * (steps * v0) + h01 * p1 + h11 * (steps * v1)

    pre_steps = start - constraint_start
    if pre_steps:
        source_velocity = source[min(constraint_start + 1, len(source) - 1)] - source[constraint_start]
        contact_velocity = (
            contact_target[1] - contact_target[0]
            if len(contact_target) > 1
            else np.zeros(3, dtype=np.float64)
        )
        result[constraint_start:start] = hermite(
            source[constraint_start],
            source_velocity,
            contact_target[0],
            contact_velocity,
            pre_steps,
        )[:-1]
    post_steps = constraint_end - end
    if post_steps:
        contact_velocity = (
            contact_target[-1] - contact_target[-2]
            if len(contact_target) > 1
            else np.zeros(3, dtype=np.float64)
        )
        source_velocity = source[constraint_end - 1] - source[max(0, constraint_end - 2)]
        result[end:constraint_end] = hermite(
            contact_target[-1],
            contact_velocity,
            source[constraint_end - 1],
            source_velocity,
            post_steps,
        )[1:]
    return result, constraint_start, constraint_end


def _load_npz(path: str | Path) -> dict[str, Any]:
    with np.load(Path(path).expanduser(), allow_pickle=True) as source:
        return {key: np.asarray(source[key]) for key in source.files}


def _stable_mirrored_contacts(
    *,
    graph: Any,
    root_qpos: np.ndarray,
    link_names: tuple[str, ...],
) -> EnvironmentContactAnchors:
    handles = build_contact_episode_handles(
        graph.anchors,
        max_gap_frames=10,
        min_duration_frames=20,
    )
    if not handles:
        raise ValueError("robot mirror IK requires stable environment contact episodes")
    frames = int(root_qpos.shape[0])
    starts = np.asarray([handle.start_frame for handle in handles], dtype=np.int64)
    ends = np.asarray([handle.end_frame for handle in handles], dtype=np.int64)
    representatives = starts + (ends - starts - 1) // 2
    original_positions = np.asarray([handle.world_position for handle in handles], dtype=np.float64)
    source_trajectories = np.empty((len(handles), frames, 3), dtype=np.float64)
    target_trajectories = np.empty_like(source_trajectories)
    target_positions = np.empty_like(original_positions)
    for index, original in enumerate(original_positions):
        repeated = np.broadcast_to(original, (frames, 3))
        source_trajectories[index] = _reflect_root_local_points(repeated, root_qpos)
        target, _, _ = project_contact_to_surface(
            handles[index], source_trajectories[index, representatives[index]]
        )
        target_positions[index] = target
        target_trajectories[index] = np.broadcast_to(target, (frames, 3))
    semantic_names = tuple(swap_left_right_name(handle.body) for handle in handles)
    contacts = EnvironmentContactAnchors(
        anchor_ids=tuple(f"mirror_lr::{handle.handle_id}" for handle in handles),
        semantic_names=semantic_names,
        start_frames=starts,
        end_frames=ends,
        representative_frames=representatives,
        source_position_w=source_trajectories[np.arange(len(handles)), representatives],
        target_position_w=target_positions,
        edited=np.ones(len(handles), dtype=bool),
        link_groups=[_resolve_named_link_group(link_names, name) for name in semantic_names],
        source_trajectory_w=source_trajectories,
        target_trajectory_w=target_trajectories,
    )
    contacts.validate(frames=frames)
    return contacts


def _recorded_surface_contacts(
    *,
    graph: Any,
    robot: Any,
    link_names: tuple[str, ...],
    initial_root_qpos: np.ndarray,
    initial_joint_cfg: np.ndarray,
    recorded_root_qpos: np.ndarray,
    recorded_joint_cfg: np.ndarray,
    recorded_force: dict[str, Any],
    end_frame: int | None = None,
    fade_frames: int = 12,
    smoothing_window: int = 51,
    target_mode: str = "recorded_smoothed",
) -> EnvironmentContactAnchors:
    """Attach stable surface handles to the recorded collision point on each hand.

    The contact recording and reference motion are different trajectories.  A
    recorded surface point therefore cannot be treated as if it were already
    attached to the reference robot.  This maps the recorded collision-point
    offset through the matching link into the initial mirrored trajectory, then
    moves that physical point to one stable handle for the whole episode.
    """

    import jax.numpy as jnp

    frames = int(initial_root_qpos.shape[0])
    if recorded_root_qpos.shape[0] != frames or recorded_joint_cfg.shape[0] != frames:
        raise ValueError("recorded contact trajectory must match the initial motion frame count")
    handles = [
        handle
        for handle in build_contact_episode_handles(
            graph.anchors,
            max_gap_frames=10,
            min_duration_frames=20,
        )
        if handle.body in _CONTACT_PART_BY_SEMANTIC
        and (end_frame is None or int(handle.start_frame) < int(end_frame))
    ]
    if not handles:
        raise ValueError("obstacle mirror IK requires at least one stable hand contact episode")

    part_order = [str(value) for value in np.asarray(recorded_force["contact_force_part_order"]).reshape(-1)]
    positions = np.asarray(recorded_force["contact_force_part_position_w"], dtype=np.float64)
    mask = np.asarray(recorded_force["contact_force_part_mask"], dtype=bool)
    position_valid = np.asarray(recorded_force["contact_force_part_position_valid"], dtype=bool)
    if positions.shape != (frames, len(part_order), 3):
        raise ValueError("recorded contact positions must have shape [T,P,3]")
    if mask.shape != positions.shape[:2] or position_valid.shape != mask.shape:
        raise ValueError("recorded contact mask and validity must have shape [T,P]")

    initial_fk = np.asarray(robot.forward_kinematics(jnp.asarray(initial_joint_cfg)), dtype=np.float64)
    recorded_fk = np.asarray(robot.forward_kinematics(jnp.asarray(recorded_joint_cfg)), dtype=np.float64)
    contact_starts = np.asarray([max(0, int(handle.start_frame)) for handle in handles], dtype=np.int64)
    contact_ends = np.asarray([min(frames, int(handle.end_frame)) for handle in handles], dtype=np.int64)
    if end_frame is not None:
        contact_ends = np.minimum(contact_ends, int(end_frame))
    representatives = contact_starts + (contact_ends - contact_starts - 1) // 2
    starts = np.zeros(len(handles), dtype=np.int64)
    ends = np.zeros(len(handles), dtype=np.int64)
    source_trajectories = np.zeros((len(handles), frames, 3), dtype=np.float64)
    target_trajectories = np.zeros_like(source_trajectories)
    source_positions = np.zeros((len(handles), 3), dtype=np.float64)
    target_positions = np.asarray([handle.world_position for handle in handles], dtype=np.float64)
    link_groups: list[np.ndarray] = []

    for episode_index, handle in enumerate(handles):
        group = _resolve_named_link_group(link_names, handle.body)
        part_name = _CONTACT_PART_BY_SEMANTIC[handle.body]
        if part_name not in part_order:
            raise ValueError(f"recorded contact force has no {part_name!r} part")
        part_index = part_order.index(part_name)
        active = mask[:, part_index] & position_valid[:, part_index]
        active_indices = (
            np.flatnonzero(active[contact_starts[episode_index] : contact_ends[episode_index]])
            + contact_starts[episode_index]
        )
        if active_indices.size == 0:
            raise ValueError(f"{handle.handle_id}: stable episode has no valid recorded contact positions")
        link_index, local_offset = _dominant_rigid_contact_proxy(
            recorded_points_w=positions[:, part_index],
            recorded_root_qpos=recorded_root_qpos,
            recorded_fk=recorded_fk,
            link_group=group,
            active_frames=active_indices,
        )
        link_groups.append(np.asarray([link_index], dtype=np.int32))
        initial_link_pose = initial_fk[:, link_index]
        initial_point_b = initial_link_pose[:, 4:7] + _quat_apply_numpy(
            initial_link_pose[:, :4],
            np.broadcast_to(local_offset, (frames, 3)),
        )
        source_trajectories[episode_index] = (
            _quat_apply_numpy(initial_root_qpos[:, 3:7], initial_point_b)
            + initial_root_qpos[:, :3]
        )
        if target_mode == "recorded_smoothed":
            contact_target = _smoothed_contact_trajectory(
                recorded_positions_w=positions[:, part_index],
                active_frames=active_indices,
                contact_start=int(contact_starts[episode_index]),
                contact_end=int(contact_ends[episode_index]),
                handle_position_w=target_positions[episode_index],
                surface_origin_w=np.asarray(handle.surface_origin, dtype=np.float64),
                surface_normal_w=np.asarray(handle.surface_normal, dtype=np.float64),
                smoothing_window=smoothing_window,
            )
        elif target_mode == "initial_surface_projection":
            contact_target = _project_trajectory_to_surface(
                source_trajectories[
                    episode_index,
                    contact_starts[episode_index] : contact_ends[episode_index],
                ],
                surface_origin_w=np.asarray(handle.surface_origin, dtype=np.float64),
                surface_normal_w=np.asarray(handle.surface_normal, dtype=np.float64),
            )
            target_positions[episode_index] = np.mean(contact_target, axis=0)
        else:
            raise ValueError(f"unsupported contact target mode: {target_mode!r}")
        target_trajectory, constraint_start, constraint_end = _blended_contact_trajectory(
            source_trajectory_w=source_trajectories[episode_index],
            contact_target_w=contact_target,
            contact_start=int(contact_starts[episode_index]),
            contact_end=int(contact_ends[episode_index]),
            fade_frames=int(fade_frames),
        )
        starts[episode_index] = constraint_start
        ends[episode_index] = constraint_end
        target_trajectories[episode_index] = target_trajectory
        source_positions[episode_index] = source_trajectories[
            episode_index, representatives[episode_index]
        ]

    contacts = EnvironmentContactAnchors(
        anchor_ids=tuple(f"obstacle_mirror::{handle.handle_id}" for handle in handles),
        semantic_names=tuple(handle.body for handle in handles),
        start_frames=starts,
        end_frames=ends,
        representative_frames=representatives,
        source_position_w=source_positions,
        target_position_w=target_positions,
        edited=np.ones(len(handles), dtype=bool),
        link_groups=link_groups,
        source_trajectory_w=source_trajectories,
        target_trajectory_w=target_trajectories,
    )
    contacts.validate(frames=frames)
    return contacts


def solve_robot_mirror_ik(
    *,
    initial_motion_path: str | Path,
    mirrored_force_path: str | Path,
    source_contact_layer_root: str | Path,
    terrain_mesh_path: str | Path,
    output_path: str | Path,
    motion_id: str,
    max_iterations: int = 80,
    contact_mode: str = "root_local_projection",
    contact_end_frame: int | None = None,
    contact_fade_frames: int = 12,
    contact_smoothing_window: int = 51,
    contact_target_mode: str = "initial_surface_projection",
    lock_root_trajectory: bool = True,
) -> Path:
    """Fit mirrored limbs to unchanged world contacts."""

    import pyroki
    import yourdfpy

    initial_path = Path(initial_motion_path).expanduser().resolve()
    force_path = Path(mirrored_force_path).expanduser().resolve()
    initial = _load_npz(initial_path)
    force = _load_npz(force_path)
    graph = read_contact_graph(Path(source_contact_layer_root).expanduser(), motion_id)
    robot = pyroki.Robot.from_urdf(yourdfpy.URDF.load(str(canonical_g1_urdf_path()), load_meshes=False))
    link_names = tuple(robot.links.names)
    actuated_names = tuple(robot.joints.actuated_names)
    source_joint_names = [str(value) for value in np.asarray(initial["joint_names"]).reshape(-1).tolist()]
    missing = [name for name in actuated_names if name not in source_joint_names]
    if missing:
        raise ValueError(f"initial mirror motion misses canonical joints: {missing}")
    qpos = np.asarray(initial["joint_pos"], dtype=np.float64)
    root_qpos = qpos[:, :7].copy()
    joint_cfg = np.stack([qpos[:, 7 + source_joint_names.index(name)] for name in actuated_names], axis=1)
    force_qpos = np.asarray(force["joint_pos"], dtype=np.float64)
    force_joint_names = [str(value) for value in np.asarray(force["joint_names"]).reshape(-1).tolist()]
    missing_force_joints = [name for name in actuated_names if name not in force_joint_names]
    if missing_force_joints:
        raise ValueError(f"recorded contact motion misses canonical joints: {missing_force_joints}")
    force_root_qpos = force_qpos[:, :7].copy()
    force_joint_cfg = np.stack(
        [force_qpos[:, 7 + force_joint_names.index(name)] for name in actuated_names], axis=1
    )

    keypoints = _semantic_keypoints_from_motion(initial)
    target_names, target_groups, target_weight_values = _resolve_link_groups(link_names, keypoints)
    target_positions = np.stack([keypoints[name] for name in target_names], axis=1)
    target_weights = np.broadcast_to(target_weight_values, target_positions.shape[:2]).copy()
    for index, name in enumerate(target_names):
        target_weights[:, index] *= 0.5 if name in {"left_hand", "right_hand"} else 1.0

    force_groups = _resolve_force_link_groups(link_names)
    force_for_solver = (
        _stabilized_hand_force(
            recorded_force=force,
            graph=graph,
            end_frame=contact_end_frame,
            smoothing_window=contact_smoothing_window,
        )
        if contact_mode == "recorded_surface"
        else force
    )
    force_linearization = _force_linearization_from_source(
        source_motion=force_for_solver,
        robot=robot,
        root_qpos=root_qpos,
        joint_cfg=joint_cfg,
        force_groups=force_groups,
    )
    if contact_mode == "root_local_projection":
        contacts = _stable_mirrored_contacts(
            graph=graph,
            root_qpos=root_qpos,
            link_names=link_names,
        )
    elif contact_mode == "recorded_surface":
        contacts = _recorded_surface_contacts(
            graph=graph,
            robot=robot,
            link_names=link_names,
            initial_root_qpos=root_qpos,
            initial_joint_cfg=joint_cfg,
            recorded_root_qpos=force_root_qpos,
            recorded_joint_cfg=force_joint_cfg,
            recorded_force=force,
            end_frame=contact_end_frame,
            fade_frames=contact_fade_frames,
            smoothing_window=contact_smoothing_window,
            target_mode=contact_target_mode,
        )
    else:
        raise ValueError(f"unsupported mirror IK contact mode: {contact_mode!r}")
    object_points = sample_terrain_mesh_points(terrain_mesh_path, count=100, seed=0)
    config = WholeTrajectoryConfig(
        contact_laplacian_weight=10.0,
        taskspace_tracking_weight=12.0,
        environment_anchor_tolerance_m=1.0e-3,
        contact_sticking_weight=20.0,
        joint_limit_weight=20.0,
        pose_prior_weight=12.0 if contact_mode == "recorded_surface" else 2.0,
        temporal_laplacian_weight=60.0 if contact_mode == "recorded_surface" else 4.0,
        contact_force_weight=2.0,
        max_iterations=int(max_iterations),
        lock_root_trajectory=bool(lock_root_trajectory),
    )
    result = solve_whole_trajectory(
        robot=robot,
        root_qpos_init=root_qpos,
        joint_cfg_init=joint_cfg,
        target_position_w=target_positions,
        target_link_groups=target_groups,
        target_weights=target_weights,
        force_link_groups=force_groups,
        force_linearization=force_linearization,
        environment_contacts=contacts,
        object_points_w=object_points,
        config=config,
    )
    root_error = float(np.max(np.abs(result.root_qpos - root_qpos)))
    if lock_root_trajectory and root_error != 0.0:
        raise ValueError(f"root-locked mirror changed root trajectory by {root_error:.6g}")

    payload = dict(initial)
    solved_root_qpos = np.asarray(result.root_qpos, dtype=np.float64).copy()
    solved_root_qpos[:, 3:7] = _canonicalize_quaternion_hemisphere_wxyz(solved_root_qpos[:, 3:7])
    solved_qpos = np.concatenate([solved_root_qpos, result.joint_cfg], axis=1)
    payload["joint_pos"] = solved_qpos.astype(np.float32)
    payload["joint_names"] = np.asarray(actuated_names)
    fps = float(np.asarray(payload.get("fps", 50.0)).reshape(-1)[0])
    velocity = np.zeros((len(root_qpos), 6 + len(actuated_names)), dtype=np.float64)
    velocity[:, :3] = _finite_difference_linear(solved_root_qpos[:, :3], fps)
    root_rotation = Rotation.from_quat(solved_root_qpos[:, [4, 5, 6, 3]]).as_matrix()
    velocity[:, 3:6] = _finite_difference_angular(root_rotation[:, None], fps)[:, 0]
    velocity[:, 6:] = _finite_difference_linear(result.joint_cfg, fps)
    payload["joint_vel"] = velocity.astype(np.float32)
    _recompute_named_body_arrays(payload)
    metadata = {
        "schema": ROBOT_MIRROR_IK_SCHEMA,
        "mirror_schema": ROBOT_MIRROR_SCHEMA,
        "initial_motion_path": str(initial_path),
        "mirrored_force_path": str(force_path),
        "source_contact_layer_root": str(Path(source_contact_layer_root).expanduser().resolve()),
        "terrain_mesh_path": str(Path(terrain_mesh_path).expanduser().resolve()),
        "root_transform": "identity",
        "root_max_abs_error": root_error,
        "root_trajectory_locked": bool(lock_root_trajectory),
        "contact_mode": contact_mode,
        "contact_fade_frames": int(contact_fade_frames),
        "contact_smoothing_window": int(contact_smoothing_window),
        "contact_target_mode": contact_target_mode,
        "stable_contact_episode_count": len(contacts.anchor_ids),
        "solver": result.metadata,
    }
    payload["motion_edit_robot_mirror_ik_json"] = np.asarray(json.dumps(metadata, sort_keys=True))
    from somaforge_core.support_evidence import reference_only_support
    reference_only_support(payload, reason='mirror IK output has no measured execution support', retain_force_targets=True)
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **payload)
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-motion", required=True)
    parser.add_argument("--mirrored-force", required=True)
    parser.add_argument("--source-contact-layer-root", required=True)
    parser.add_argument("--terrain-mesh", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--motion-id", required=True)
    parser.add_argument("--max-iterations", type=int, default=80)
    parser.add_argument(
        "--contact-mode",
        choices=("root_local_projection", "recorded_surface"),
        default="root_local_projection",
    )
    parser.add_argument("--contact-end-frame", type=int)
    parser.add_argument("--contact-fade-frames", type=int, default=12)
    parser.add_argument("--contact-smoothing-window", type=int, default=51)
    parser.add_argument(
        "--contact-target-mode",
        choices=("recorded_smoothed", "initial_surface_projection"),
        default="initial_surface_projection",
    )
    parser.add_argument("--unlock-root-trajectory", action="store_true")
    args = parser.parse_args(argv)
    print(
        solve_robot_mirror_ik(
            initial_motion_path=args.initial_motion,
            mirrored_force_path=args.mirrored_force,
            source_contact_layer_root=args.source_contact_layer_root,
            terrain_mesh_path=args.terrain_mesh,
            output_path=args.output,
            motion_id=args.motion_id,
            max_iterations=args.max_iterations,
            contact_mode=args.contact_mode,
            contact_end_frame=args.contact_end_frame,
            contact_fade_frames=args.contact_fade_frames,
            contact_smoothing_window=args.contact_smoothing_window,
            contact_target_mode=args.contact_target_mode,
            lock_root_trajectory=not args.unlock_root_trajectory,
        )
    )


if __name__ == "__main__":
    main()
