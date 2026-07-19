"""Continuous contact-episode trajectories shared by geometry and IK generation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from somaforge_core.contact_schema import canonical_contact_part_name

from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.workbench.edit_handles import build_contact_episode_handles


CONTACT_EPISODE_MAX_GAP_FRAMES = 10
CONTACT_EPISODE_MIN_STABLE_FRAMES = 20

_CONTACT_PARTS_BY_EPISODE_BODY = {
    "left_foot": ("left_heel", "left_toe"),
    "right_foot": ("right_heel", "right_toe"),
    "left_hand": ("left_hand",),
    "right_hand": ("right_hand",),
    "left_knee": ("left_knee",),
    "right_knee": ("right_knee",),
}


@dataclass(frozen=True)
class ContactEpisodeTrajectory:
    """One editable episode with per-frame contact, force, and provenance."""

    episode_id: str
    body: str
    semantic_name: str
    start_frame: int
    end_frame: int
    representative_frame: int
    source_semantic_xyz: np.ndarray
    target_semantic_xyz: np.ndarray
    source_contact_xyz: np.ndarray
    target_contact_xyz: np.ndarray
    contact_force_w: np.ndarray
    contact_mask: np.ndarray
    edited: bool
    delta_world: np.ndarray
    surface_id: str | None
    object_id: str | None
    member_anchor_ids: tuple[str, ...]
    member_edit_ids: tuple[str, ...]

    def validate(self, *, n_frames: int) -> None:
        start = int(self.start_frame)
        end = int(self.end_frame)
        count = end - start
        if start < 0 or end > int(n_frames) or count <= 0:
            raise ValueError(f"{self.episode_id}: invalid episode interval [{start}, {end})")
        if not start <= int(self.representative_frame) < end:
            raise ValueError(f"{self.episode_id}: representative frame is outside the episode")
        for name in (
            "source_semantic_xyz",
            "target_semantic_xyz",
            "source_contact_xyz",
            "target_contact_xyz",
            "contact_force_w",
        ):
            value = np.asarray(getattr(self, name), dtype=np.float64)
            if value.shape != (count, 3):
                raise ValueError(f"{self.episode_id}: {name} must have shape {(count, 3)}, got {value.shape}")
            if not np.all(np.isfinite(value)):
                raise ValueError(f"{self.episode_id}: {name} contains NaN or Inf")
        if np.asarray(self.contact_mask, dtype=bool).shape != (count,):
            raise ValueError(f"{self.episode_id}: contact_mask must have shape {(count,)}")
        delta = np.asarray(self.delta_world, dtype=np.float64)
        if delta.shape != (3,) or not np.all(np.isfinite(delta)):
            raise ValueError(f"{self.episode_id}: delta_world must be finite xyz")
        if not self.member_anchor_ids:
            raise ValueError(f"{self.episode_id}: episode has no source anchors")


def _edit_delta(edit: ContactAnchorEditRecord) -> np.ndarray:
    if edit.new_world_position is not None and edit.old_world_position is not None:
        return np.asarray(edit.new_world_position, dtype=np.float64) - np.asarray(
            edit.old_world_position, dtype=np.float64
        )
    if edit.delta_world is not None:
        return np.asarray(edit.delta_world, dtype=np.float64)
    if edit.requested_delta_world is not None:
        return np.asarray(edit.requested_delta_world, dtype=np.float64)
    return np.zeros(3, dtype=np.float64)


def _clipped_edited_anchors(
    anchors: list[ContactAnchorRecord],
    edits_by_anchor: dict[str, ContactAnchorEditRecord],
    *,
    n_frames: int,
) -> list[ContactAnchorRecord]:
    clipped: list[ContactAnchorRecord] = []
    for anchor in anchors:
        edit = edits_by_anchor.get(anchor.anchor_id)
        if edit is None:
            continue
        start = max(0, int(anchor.start_frame))
        end = min(int(n_frames), int(anchor.end_frame))
        if edit.affected_frames is not None:
            start = max(start, int(edit.affected_frames[0]))
            end = min(end, int(edit.affected_frames[1]))
        if end > start:
            clipped.append(replace(anchor, start_frame=start, end_frame=end))
    return clipped


def _phase_delta(
    member_anchor_ids: list[str],
    edits_by_anchor: dict[str, ContactAnchorEditRecord],
) -> tuple[np.ndarray, tuple[str, ...]]:
    member_edits = [edits_by_anchor[anchor_id] for anchor_id in member_anchor_ids if anchor_id in edits_by_anchor]
    if not member_edits:
        return np.zeros(3, dtype=np.float64), ()
    deltas = np.stack([_edit_delta(edit) for edit in member_edits])
    delta = np.median(deltas, axis=0)
    disagreement = float(np.max(np.linalg.norm(deltas - delta[None, :], axis=1)))
    if disagreement > 1.0e-4:
        raise ValueError(
            "contact episode contains divergent fragment edits; move the episode handle as one unit "
            f"instead (max delta disagreement {disagreement:.6g} m)"
        )
    return delta, tuple(edit.edit_id for edit in member_edits)


def _motion_strings(value: Any) -> list[str]:
    return [str(item.decode("utf-8") if isinstance(item, bytes) else item) for item in np.asarray(value).reshape(-1)]


def _contact_point_force_trajectory(
    *,
    contact_motion: dict[str, Any] | None,
    body: str,
    start: int,
    end: int,
    fallback_semantic_xyz: np.ndarray,
    fallback_world_position: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    count = int(end - start)
    fallback = np.asarray(fallback_semantic_xyz, dtype=np.float64).copy()
    representative = count // 2
    fallback += fallback_world_position[None, :] - fallback[representative][None, :]
    if contact_motion is None:
        return fallback, np.zeros((count, 3), dtype=np.float64), np.zeros(count, dtype=bool)
    required = {
        "contact_force_part_order",
        "contact_force_part_w",
        "contact_force_part_mask",
        "contact_force_part_position_w",
    }
    if not required.issubset(contact_motion):
        return fallback, np.zeros((count, 3), dtype=np.float64), np.zeros(count, dtype=bool)
    try:
        order = [canonical_contact_part_name(name) for name in _motion_strings(contact_motion["contact_force_part_order"])]
    except ValueError:
        return fallback, np.zeros((count, 3), dtype=np.float64), np.zeros(count, dtype=bool)
    wanted = _CONTACT_PARTS_BY_EPISODE_BODY.get(body, (body,))
    part_indices = [order.index(name) for name in wanted if name in order]
    if not part_indices:
        return fallback, np.zeros((count, 3), dtype=np.float64), np.zeros(count, dtype=bool)
    force = np.asarray(contact_motion["contact_force_part_w"], dtype=np.float64)
    mask = np.asarray(contact_motion["contact_force_part_mask"], dtype=bool)
    positions = np.asarray(contact_motion["contact_force_part_position_w"], dtype=np.float64)
    valid = np.asarray(
        contact_motion.get("contact_force_part_position_valid", mask), dtype=bool
    )
    if force.ndim != 3 or positions.shape != force.shape or mask.shape != force.shape[:2] or valid.shape != mask.shape:
        return fallback, np.zeros((count, 3), dtype=np.float64), np.zeros(count, dtype=bool)
    trajectory = np.full((count, 3), np.nan, dtype=np.float64)
    force_trajectory = np.zeros((count, 3), dtype=np.float64)
    phase_mask = np.zeros(count, dtype=bool)
    for local_frame, frame in enumerate(range(start, end)):
        if frame >= force.shape[0]:
            continue
        active = [index for index in part_indices if mask[frame, index] and valid[frame, index]]
        if not active:
            continue
        weights = np.linalg.norm(force[frame, active], axis=1)
        if float(np.sum(weights)) <= 1.0e-8:
            weights = np.ones(len(active), dtype=np.float64)
        trajectory[local_frame] = np.average(positions[frame, active], axis=0, weights=weights)
        force_trajectory[local_frame] = np.sum(force[frame, active], axis=0)
        phase_mask[local_frame] = True
    known = np.flatnonzero(phase_mask)
    if known.size:
        axis = np.arange(count, dtype=np.float64)
        for coordinate in range(3):
            trajectory[:, coordinate] = np.interp(axis, known, trajectory[known, coordinate])
        for coordinate in range(3):
            force_trajectory[:, coordinate] = np.interp(axis, known, force_trajectory[known, coordinate])
    else:
        trajectory = fallback
    return trajectory, force_trajectory, phase_mask


def build_contact_episode_trajectories(
    *,
    anchors: list[ContactAnchorRecord],
    edits: list[ContactAnchorEditRecord],
    keypoints: dict[str, np.ndarray],
    n_frames: int,
    contact_motion: dict[str, Any] | None = None,
    contact_positions_are_target: bool = False,
) -> list[ContactEpisodeTrajectory]:
    """Collapse source fragments into the same episode handles used by the editor."""

    edits_by_anchor = {edit.anchor_id: edit for edit in edits}
    edited_anchors = _clipped_edited_anchors(anchors, edits_by_anchor, n_frames=n_frames)
    surface_follow = bool(edited_anchors) and all(
        "surface_transform" in edits_by_anchor[anchor.anchor_id].metadata for anchor in edited_anchors
    )
    edited_handles = build_contact_episode_handles(
        edited_anchors,
        max_gap_frames=CONTACT_EPISODE_MAX_GAP_FRAMES,
        min_duration_frames=(CONTACT_EPISODE_MIN_STABLE_FRAMES if surface_follow else 1),
    )
    fixed_handles = build_contact_episode_handles(
        [anchor for anchor in anchors if anchor.anchor_id not in edits_by_anchor],
        max_gap_frames=CONTACT_EPISODE_MAX_GAP_FRAMES,
        min_duration_frames=CONTACT_EPISODE_MIN_STABLE_FRAMES,
    )
    episodes: list[ContactEpisodeTrajectory] = []
    for handle, edited in [*((item, True) for item in edited_handles), *((item, False) for item in fixed_handles)]:
        semantic_name = handle.body
        if semantic_name not in keypoints:
            continue
        start = max(0, int(handle.start_frame))
        end = min(int(n_frames), int(handle.end_frame))
        if end <= start:
            continue
        delta, edit_ids = _phase_delta(handle.member_anchor_ids, edits_by_anchor) if edited else (
            np.zeros(3, dtype=np.float64),
            (),
        )
        serialized_semantic = np.asarray(keypoints[semantic_name][start:end], dtype=np.float64)
        if edited and contact_positions_are_target:
            target_semantic = serialized_semantic
            source_semantic = serialized_semantic - delta[None, :]
        else:
            source_semantic = serialized_semantic
            target_semantic = serialized_semantic + delta[None, :]
        recorded_contact, force, phase_mask = _contact_point_force_trajectory(
            contact_motion=contact_motion,
            body=handle.body,
            start=start,
            end=end,
            fallback_semantic_xyz=source_semantic,
            fallback_world_position=np.asarray(handle.world_position, dtype=np.float64),
        )
        if edited and contact_positions_are_target:
            target_contact = recorded_contact
            source_contact = recorded_contact - delta[None, :]
        else:
            source_contact = recorded_contact
            target_contact = recorded_contact + delta[None, :]
        representative = start + (end - start - 1) // 2
        episode = ContactEpisodeTrajectory(
            episode_id=handle.handle_id,
            body=handle.body,
            semantic_name=semantic_name,
            start_frame=start,
            end_frame=end,
            representative_frame=representative,
            source_semantic_xyz=source_semantic,
            target_semantic_xyz=target_semantic,
            source_contact_xyz=source_contact,
            target_contact_xyz=target_contact,
            contact_force_w=force,
            contact_mask=phase_mask,
            edited=edited and float(np.linalg.norm(delta)) > 1.0e-9,
            delta_world=delta,
            surface_id=handle.surface_id,
            object_id=handle.object_id,
            member_anchor_ids=tuple(handle.member_anchor_ids),
            member_edit_ids=edit_ids,
        )
        episode.validate(n_frames=n_frames)
        episodes.append(episode)
    return sorted(
        episodes,
        key=lambda item: (item.start_frame, item.end_frame, item.body, item.episode_id),
    )


__all__ = [
    "CONTACT_EPISODE_MAX_GAP_FRAMES",
    "CONTACT_EPISODE_MIN_STABLE_FRAMES",
    "ContactEpisodeTrajectory",
    "build_contact_episode_trajectories",
]
