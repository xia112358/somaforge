from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np


CONTACT_LOAD_PART_ALIASES = {
    "left_foot": "left_foot",
    "right_foot": "right_foot",
    "left_hand": "left_hand",
    "right_hand": "right_hand",
    "left_knee": "left_knee",
    "right_knee": "right_knee",
    "lf": "left_foot",
    "rf": "right_foot",
    "lh": "left_hand",
    "rh": "right_hand",
    "lk": "left_knee",
    "rk": "right_knee",
}


@dataclass(frozen=True)
class ContactLoadProfile:
    """Contact-local load multiplier over normalized phase.

    ``phase`` is local to one contact handle, not global motion time. Solver
    code compiles this profile to per-frame weights only after the target
    contact interval is known. The default builder normalizes ``strength`` to
    mean one so force redistributes constraint emphasis within the contact
    phase without changing the handle's total stiffness.
    """

    phase: np.ndarray
    strength: np.ndarray
    force_local: np.ndarray | None = None
    force_w: np.ndarray | None = None
    source_frames: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        phase = np.asarray(self.phase, dtype=np.float64)
        strength = np.asarray(self.strength, dtype=np.float64)
        if phase.ndim != 1 or strength.ndim != 1:
            raise ValueError("ContactLoadProfile phase and strength must be one-dimensional")
        if phase.shape != strength.shape:
            raise ValueError(f"ContactLoadProfile phase/strength shape mismatch: {phase.shape} vs {strength.shape}")
        if len(phase) == 0:
            raise ValueError("ContactLoadProfile cannot be empty")
        if not np.all(np.isfinite(phase)) or not np.all(np.isfinite(strength)):
            raise ValueError("ContactLoadProfile phase/strength contains NaN or Inf")
        if np.any(phase < -1.0e-9) or np.any(phase > 1.0 + 1.0e-9):
            raise ValueError("ContactLoadProfile phase must lie in [0, 1]")
        if np.any(np.diff(phase) < -1.0e-9):
            raise ValueError("ContactLoadProfile phase must be sorted")
        if np.any(strength < 0.0):
            raise ValueError("ContactLoadProfile strength must be nonnegative")
        if self.force_local is not None:
            force_local = np.asarray(self.force_local, dtype=np.float64)
            if force_local.shape != (len(phase), 3):
                raise ValueError(f"force_local must have shape {(len(phase), 3)}, got {force_local.shape}")
        if self.force_w is not None:
            force_w = np.asarray(self.force_w, dtype=np.float64)
            if force_w.shape != (len(phase), 3):
                raise ValueError(f"force_w must have shape {(len(phase), 3)}, got {force_w.shape}")
        if self.source_frames is not None:
            source_frames = np.asarray(self.source_frames)
            if source_frames.shape != (len(phase),):
                raise ValueError(f"source_frames must have shape {(len(phase),)}, got {source_frames.shape}")

    def evaluate(self, phase_query: Sequence[float] | np.ndarray) -> np.ndarray:
        self.validate()
        query = np.asarray(phase_query, dtype=np.float64)
        if query.size == 0:
            return np.zeros_like(query, dtype=np.float64)
        clipped = np.clip(query, 0.0, 1.0)
        return np.interp(clipped, np.asarray(self.phase, dtype=np.float64), np.asarray(self.strength, dtype=np.float64))


def contact_local_phase(count: int) -> np.ndarray:
    n = int(count)
    if n <= 0:
        return np.zeros((0,), dtype=np.float64)
    if n == 1:
        return np.asarray([0.5], dtype=np.float64)
    return np.linspace(0.0, 1.0, n, dtype=np.float64)


def build_load_profile_from_force_phase(
    force_w: np.ndarray,
    *,
    normal_w: Sequence[float] | np.ndarray | None = None,
    source_frames: Sequence[int] | np.ndarray | None = None,
    min_strength: float = 0.05,
    normalize_mean: bool = True,
    max_strength: float | None = 2.5,
    metadata: dict[str, Any] | None = None,
) -> ContactLoadProfile:
    force = np.asarray(force_w, dtype=np.float64)
    if force.ndim != 2 or force.shape[1] != 3:
        raise ValueError(f"force_w must have shape [K, 3], got {force.shape}")
    if not np.all(np.isfinite(force)):
        raise ValueError("force_w contains NaN or Inf")
    if not 0.0 <= float(min_strength) <= 1.0:
        raise ValueError("min_strength must lie in [0, 1]")
    if max_strength is not None and float(max_strength) <= 0.0:
        raise ValueError("max_strength must be positive when provided")
    meta = dict(metadata or {})
    if normal_w is not None:
        normal = np.asarray(normal_w, dtype=np.float64)
        if normal.shape != (3,) or not np.all(np.isfinite(normal)):
            raise ValueError(f"normal_w must have shape (3,), got {normal.shape}")
        norm = float(np.linalg.norm(normal))
        if norm <= 1.0e-12:
            load = np.linalg.norm(force, axis=1)
            meta["load_component"] = "force_norm_zero_normal_fallback"
        else:
            normal = normal / norm
            load = np.maximum(0.0, force @ normal)
            meta["load_component"] = "positive_normal_projection"
            meta["normal_w"] = normal.astype(float).tolist()
    else:
        load = np.linalg.norm(force, axis=1)
        meta["load_component"] = "force_norm_no_normal"

    peak = float(np.max(load)) if load.size else 0.0
    if peak <= 1.0e-12:
        strength = np.ones(force.shape[0], dtype=np.float64)
        meta["load_normalization"] = "uniform_zero_load_fallback"
    else:
        normalized = load / peak
        strength = float(min_strength) + (1.0 - float(min_strength)) * normalized
        meta["load_normalization"] = "phase_peak_min_blend"
        meta["source_load_peak"] = peak
        meta["min_strength"] = float(min_strength)
    if normalize_mean and strength.size:
        mean_before = float(np.mean(strength))
        if mean_before > 1.0e-12:
            strength = strength / mean_before
            meta["strength_mean_before_normalization"] = mean_before
            meta["strength_mean_normalization"] = "mean_one"
        if max_strength is not None:
            clipped = np.minimum(strength, float(max_strength))
            if not np.allclose(clipped, strength):
                clipped_mean = float(np.mean(clipped))
                strength = clipped / clipped_mean if clipped_mean > 1.0e-12 else clipped
                meta["strength_peak_clamp"] = float(max_strength)
                meta["strength_mean_after_clamp_before_renormalization"] = clipped_mean
    meta["strength_mean"] = float(np.mean(strength)) if strength.size else 0.0
    meta["strength_max"] = float(np.max(strength)) if strength.size else 0.0

    frames = None if source_frames is None else np.asarray(source_frames, dtype=np.int64)
    profile = ContactLoadProfile(
        phase=contact_local_phase(force.shape[0]),
        strength=strength,
        force_w=force,
        source_frames=frames,
        metadata=meta,
    )
    profile.validate()
    return profile


def load_profile_from_motion_force(
    motion: dict[str, Any],
    *,
    body: str,
    start_frame: int,
    end_frame: int,
    normal_w: Sequence[float] | np.ndarray | None = None,
    min_strength: float = 0.05,
) -> ContactLoadProfile | None:
    force_key = "contact_force_part_w" if "contact_force_part_w" in motion else "contact_force_part_force_w"
    if force_key not in motion or "contact_force_part_order" not in motion:
        return None
    force = np.asarray(motion[force_key], dtype=np.float64)
    if force.ndim != 3 or force.shape[2] != 3:
        return None
    part_order = [str(item) for item in np.asarray(motion["contact_force_part_order"]).reshape(-1).tolist()]
    part_index = _part_index_for_body(body, part_order)
    if part_index is None or part_index >= force.shape[1]:
        return None
    start = max(0, min(force.shape[0], int(start_frame)))
    end = max(start, min(force.shape[0], int(end_frame)))
    if end <= start:
        return None
    segment_force = force[start:end, part_index].copy()
    if "contact_force_part_mask" in motion:
        mask = np.asarray(motion["contact_force_part_mask"], dtype=bool)
        if mask.shape[:2] == force.shape[:2]:
            segment_force[~mask[start:end, part_index]] = 0.0
    return build_load_profile_from_force_phase(
        segment_force,
        normal_w=normal_w,
        source_frames=np.arange(start, end, dtype=np.int64),
        min_strength=min_strength,
        metadata={
            "source": "motion_contact_force_part",
            "force_key": force_key,
            "body": str(body),
            "part": part_order[part_index],
            "source_frame_start": int(start),
            "source_frame_end": int(end),
        },
    )


def _part_index_for_body(body: str, part_order: Sequence[str]) -> int | None:
    canonical = _canonical_part_name(body)
    if canonical is None:
        return None
    for index, raw in enumerate(part_order):
        if _canonical_part_name(str(raw)) == canonical:
            return int(index)
    return None


def _canonical_part_name(name: str) -> str | None:
    key = str(name).strip().lower()
    if key in CONTACT_LOAD_PART_ALIASES:
        return CONTACT_LOAD_PART_ALIASES[key]
    for token, canonical in CONTACT_LOAD_PART_ALIASES.items():
        if token and token in key:
            return canonical
    return None
