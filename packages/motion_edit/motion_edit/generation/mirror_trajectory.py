"""Pure mirror trajectory helpers, without a dedicated IK backend."""
from __future__ import annotations
from typing import Any
import numpy as np
from scipy.signal import savgol_filter
from motion_edit.robot_mirror import project_contact_to_surface
from motion_edit.workbench.edit_handles import build_contact_episode_handles
from .trajectory_types import _quat_apply_numpy, _quat_conjugate_numpy

_CONTACT_PART_BY_SEMANTIC = {"left_hand": "LH", "right_hand": "RH"}

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
