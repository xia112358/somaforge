"""Content and shape contracts shared by trajectory compilation and geometry."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np

@dataclass(frozen=True)
class ForceLinearization:
    target_force_w: np.ndarray
    actual_force_w: np.ndarray
    contact_mask: np.ndarray
    contact_normals_w: np.ndarray
    reference_link_position_w: np.ndarray | None
    target_normal_displacement_m: np.ndarray

    def validate(self, *, frames: int, parts: int) -> None:
        expected_vector = (frames, parts, 3)
        expected_mask = (frames, parts)
        for name in ("target_force_w", "actual_force_w", "contact_normals_w"):
            value = np.asarray(getattr(self, name))
            if value.shape != expected_vector:
                raise ValueError(f"{name} must be {expected_vector}, got {value.shape}")
            if not np.all(np.isfinite(value)):
                raise ValueError(f"{name} contains NaN or Inf")
        if self.reference_link_position_w is None:
            raise ValueError("reference_link_position_w must be resolved before trajectory optimization")
        reference = np.asarray(self.reference_link_position_w)
        if reference.shape != expected_vector:
            raise ValueError(f"reference_link_position_w must be {expected_vector}, got {reference.shape}")
        if not np.all(np.isfinite(reference)):
            raise ValueError("reference_link_position_w contains NaN or Inf")
        if np.asarray(self.contact_mask).shape != expected_mask:
            raise ValueError(f"contact_mask must be {expected_mask}, got {np.asarray(self.contact_mask).shape}")
        displacement = np.asarray(self.target_normal_displacement_m)
        if displacement.shape != expected_mask:
            raise ValueError(f"target_normal_displacement_m must be {expected_mask}, got {displacement.shape}")
        if not np.all(np.isfinite(displacement)):
            raise ValueError("target_normal_displacement_m contains NaN or Inf")
        normal_norm = np.linalg.norm(np.asarray(self.contact_normals_w), axis=2)
        if np.any(normal_norm <= 1.0e-12):
            raise ValueError("contact_normals_w contains a zero normal")

@dataclass(frozen=True)
class EnvironmentContactAnchors:
    """Environment-side handles, one per continuous contact episode."""

    anchor_ids: tuple[str, ...]
    semantic_names: tuple[str, ...]
    start_frames: np.ndarray
    end_frames: np.ndarray
    representative_frames: np.ndarray
    source_position_w: np.ndarray
    target_position_w: np.ndarray
    edited: np.ndarray
    link_groups: Sequence[np.ndarray]
    source_trajectory_w: np.ndarray | None = None
    target_trajectory_w: np.ndarray | None = None
    contact_source_trajectory_w: np.ndarray | None = None
    contact_target_trajectory_w: np.ndarray | None = None
    force_trajectory_w: np.ndarray | None = None
    contact_mask: np.ndarray | None = None

    def validate(self, *, frames: int) -> None:
        count = len(self.anchor_ids)
        if len(set(self.anchor_ids)) != count:
            raise ValueError("environment contact anchor_ids must be unique")
        if len(self.semantic_names) != count or len(self.link_groups) != count:
            raise ValueError("environment contact anchor metadata length mismatch")
        for name, value in (
            ("start_frames", self.start_frames),
            ("end_frames", self.end_frames),
            ("representative_frames", self.representative_frames),
        ):
            array = np.asarray(value, dtype=np.int64)
            if array.shape != (count,):
                raise ValueError(f"{name} must be {(count,)}, got {array.shape}")
        starts = np.asarray(self.start_frames, dtype=np.int64)
        ends = np.asarray(self.end_frames, dtype=np.int64)
        representative = np.asarray(self.representative_frames, dtype=np.int64)
        if np.any(starts < 0) or np.any(ends > frames) or np.any(ends <= starts):
            raise ValueError("environment contact intervals must be valid half-open trajectory intervals")
        if np.any(representative < starts) or np.any(representative >= ends):
            raise ValueError("environment contact representative frame must lie inside its interval")
        for name, value in (
            ("source_position_w", self.source_position_w),
            ("target_position_w", self.target_position_w),
        ):
            array = np.asarray(value, dtype=np.float64)
            if array.shape != (count, 3):
                raise ValueError(f"{name} must be {(count, 3)}, got {array.shape}")
            if not np.all(np.isfinite(array)):
                raise ValueError(f"{name} contains NaN or Inf")
        if np.asarray(self.edited, dtype=bool).shape != (count,):
            raise ValueError(f"edited must be {(count,)}")
        if any(np.asarray(group, dtype=np.int32).reshape(-1).size == 0 for group in self.link_groups):
            raise ValueError("environment contact link_groups must be non-empty")
        for name, value in (
            ("source_trajectory_w", self.source_trajectory_w),
            ("target_trajectory_w", self.target_trajectory_w),
            ("contact_source_trajectory_w", self.contact_source_trajectory_w),
            ("contact_target_trajectory_w", self.contact_target_trajectory_w),
            ("force_trajectory_w", self.force_trajectory_w),
        ):
            if value is None:
                continue
            array = np.asarray(value, dtype=np.float64)
            if array.shape != (count, frames, 3):
                raise ValueError(f"{name} must be {(count, frames, 3)}, got {array.shape}")
            if not np.all(np.isfinite(array)):
                raise ValueError(f"{name} contains NaN or Inf")
        if self.contact_mask is not None:
            mask = np.asarray(self.contact_mask, dtype=bool)
            if mask.shape != (count, frames):
                raise ValueError(f"contact_mask must be {(count, frames)}, got {mask.shape}")

def _quat_conjugate_numpy(quat: np.ndarray) -> np.ndarray:
    value = np.asarray(quat, dtype=np.float64).copy()
    value[..., 1:4] *= -1.0
    return value

def _quat_apply_numpy(quat: np.ndarray, vector: np.ndarray) -> np.ndarray:
    q = np.asarray(quat, dtype=np.float64)
    v = np.asarray(vector, dtype=np.float64)
    xyz = q[..., 1:4]
    twice_cross = 2.0 * np.cross(xyz, v)
    return v + q[..., :1] * twice_cross + np.cross(xyz, twice_cross)

@dataclass(frozen=True)
class FootPoseEpisode:
    """One semantic foot contact episode assembled from heel/toe/sole anchors."""

    side: str
    start_frame: int
    end_frame: int
    translation_w: np.ndarray
    anchor_ids: tuple[str, ...]

def _edited_environment_contacts(
    contacts: EnvironmentContactAnchors | None,
) -> EnvironmentContactAnchors | None:
    if contacts is None:
        return None
    selected = np.flatnonzero(np.asarray(contacts.edited, dtype=bool))
    if selected.size == 0:
        return None
    indices = selected.tolist()
    return EnvironmentContactAnchors(
        anchor_ids=tuple(contacts.anchor_ids[index] for index in indices),
        semantic_names=tuple(contacts.semantic_names[index] for index in indices),
        start_frames=np.asarray(contacts.start_frames, dtype=np.int64)[selected],
        end_frames=np.asarray(contacts.end_frames, dtype=np.int64)[selected],
        representative_frames=np.asarray(contacts.representative_frames, dtype=np.int64)[selected],
        source_position_w=np.asarray(contacts.source_position_w, dtype=np.float64)[selected],
        target_position_w=np.asarray(contacts.target_position_w, dtype=np.float64)[selected],
        edited=np.ones(selected.size, dtype=bool),
        link_groups=[contacts.link_groups[index] for index in indices],
        source_trajectory_w=(
            None
            if contacts.source_trajectory_w is None
            else np.asarray(contacts.source_trajectory_w, dtype=np.float64)[selected]
        ),
        target_trajectory_w=(
            None
            if contacts.target_trajectory_w is None
            else np.asarray(contacts.target_trajectory_w, dtype=np.float64)[selected]
        ),
        contact_source_trajectory_w=(
            None
            if contacts.contact_source_trajectory_w is None
            else np.asarray(contacts.contact_source_trajectory_w, dtype=np.float64)[selected]
        ),
        contact_target_trajectory_w=(
            None
            if contacts.contact_target_trajectory_w is None
            else np.asarray(contacts.contact_target_trajectory_w, dtype=np.float64)[selected]
        ),
        force_trajectory_w=(
            None
            if contacts.force_trajectory_w is None
            else np.asarray(contacts.force_trajectory_w, dtype=np.float64)[selected]
        ),
        contact_mask=(
            None
            if contacts.contact_mask is None
            else np.asarray(contacts.contact_mask, dtype=bool)[selected]
        ),
    )

def _edited_foot_pose_episodes(
    contacts: EnvironmentContactAnchors,
    *,
    frames: int,
    max_gap_frames: int = 10,
    min_duration_frames: int = 20,
) -> list[FootPoseEpisode]:
    """Merge heel/toe/sole fragments into rigid left/right-foot episodes."""

    semantic_side = {
        "left_foot": "left",
        "left_heel": "left",
        "left_toe": "left",
        "right_foot": "right",
        "right_heel": "right",
        "right_toe": "right",
    }
    starts = np.asarray(contacts.start_frames, dtype=np.int64)
    ends = np.asarray(contacts.end_frames, dtype=np.int64)
    source = np.asarray(contacts.source_position_w, dtype=np.float64)
    target = np.asarray(contacts.target_position_w, dtype=np.float64)
    edited = np.asarray(contacts.edited, dtype=bool)
    episodes: list[FootPoseEpisode] = []
    for side in ("left", "right"):
        indices = [
            index
            for index, semantic_name in enumerate(contacts.semantic_names)
            if edited[index] and semantic_side.get(str(semantic_name)) == side
        ]
        if not indices:
            continue
        active = np.zeros(int(frames), dtype=bool)
        for index in indices:
            active[int(starts[index]) : int(ends[index])] = True
        active_indices = np.flatnonzero(active)
        if active_indices.size == 0:
            continue
        gaps = np.flatnonzero(np.diff(active_indices) > 1)
        for gap_index in gaps:
            gap_start = int(active_indices[gap_index]) + 1
            gap_end = int(active_indices[gap_index + 1])
            if gap_end - gap_start <= int(max_gap_frames):
                active[gap_start:gap_end] = True
        padded = np.pad(active.astype(np.int8), (1, 1))
        transitions = np.diff(padded)
        run_starts = np.flatnonzero(transitions == 1)
        run_ends = np.flatnonzero(transitions == -1)
        for start, end in zip(run_starts, run_ends, strict=True):
            if int(end - start) < int(min_duration_frames):
                continue
            overlapping = [
                index
                for index in indices
                if int(starts[index]) < int(end) and int(ends[index]) > int(start)
            ]
            translations = target[overlapping] - source[overlapping]
            translation = np.median(translations, axis=0)
            if float(np.max(np.linalg.norm(translations - translation[None, :], axis=1))) > 1.0e-4:
                continue
            episodes.append(
                FootPoseEpisode(
                    side=side,
                    start_frame=int(start),
                    end_frame=int(end),
                    translation_w=translation,
                    anchor_ids=tuple(contacts.anchor_ids[index] for index in overlapping),
                )
            )
    return episodes

def _environment_contact_constraint_samples(
    contacts: EnvironmentContactAnchors,
) -> tuple[tuple[str, ...], np.ndarray, np.ndarray, np.ndarray, list[np.ndarray]]:
    """Expand one episode handle into one constraint sample per contact frame."""

    source_trajectory = (
        None
        if contacts.source_trajectory_w is None
        else np.asarray(contacts.source_trajectory_w, dtype=np.float64)
    )
    target_trajectory = (
        None
        if contacts.target_trajectory_w is None
        else np.asarray(contacts.target_trajectory_w, dtype=np.float64)
    )
    sample_ids: list[str] = []
    sample_frames: list[int] = []
    sample_source: list[np.ndarray] = []
    sample_target: list[np.ndarray] = []
    sample_groups: list[np.ndarray] = []
    for index, anchor_id in enumerate(contacts.anchor_ids):
        start = int(contacts.start_frames[index])
        end = int(contacts.end_frames[index])
        for frame in range(start, end):
            sample_ids.append(anchor_id)
            sample_frames.append(frame)
            sample_source.append(
                np.asarray(contacts.source_position_w[index], dtype=np.float64)
                if source_trajectory is None
                else source_trajectory[index, frame]
            )
            sample_target.append(
                np.asarray(contacts.target_position_w[index], dtype=np.float64)
                if target_trajectory is None
                else target_trajectory[index, frame]
            )
            sample_groups.append(np.asarray(contacts.link_groups[index], dtype=np.int32))
    return (
        tuple(sample_ids),
        np.asarray(sample_frames, dtype=np.int64),
        np.asarray(sample_source, dtype=np.float64).reshape(-1, 3),
        np.asarray(sample_target, dtype=np.float64).reshape(-1, 3),
        sample_groups,
    )
