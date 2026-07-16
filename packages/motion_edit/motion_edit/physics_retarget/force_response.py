from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class NewtonForceResponseConfig:
    probe_displacement_m: float = 5.0e-4
    max_displacement_m: float = 3.0e-3
    force_error_scale_n: float = 50.0
    minimum_response_n_per_m: float = 10.0
    maximum_response_n_per_m: float = 1.0e7
    temporal_median_radius: int = 2

    def validate(self) -> None:
        for name in (
            "probe_displacement_m",
            "max_displacement_m",
            "force_error_scale_n",
            "minimum_response_n_per_m",
            "maximum_response_n_per_m",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
        if self.probe_displacement_m > self.max_displacement_m:
            raise ValueError("probe_displacement_m cannot exceed max_displacement_m")
        if self.minimum_response_n_per_m >= self.maximum_response_n_per_m:
            raise ValueError("minimum_response_n_per_m must be below maximum_response_n_per_m")
        if int(self.temporal_median_radius) < 0:
            raise ValueError("temporal_median_radius must be nonnegative")


def force_directions(force_w: np.ndarray, contact_mask: np.ndarray) -> np.ndarray:
    """Derive contact directions only from the target Newton force time series."""

    force = np.asarray(force_w, dtype=np.float64)
    mask = np.asarray(contact_mask, dtype=bool)
    if force.ndim != 3 or force.shape[2] != 3 or mask.shape != force.shape[:2]:
        raise ValueError("force_w and contact_mask must have matching [T,P,3]/[T,P] shapes")
    magnitude = np.linalg.norm(force, axis=2, keepdims=True)
    if np.any(~np.isfinite(force)):
        raise ValueError("force_w contains NaN or Inf")
    nonzero = magnitude[..., 0] > 1.0e-8
    directions = np.zeros_like(force)
    directions[..., 2] = 1.0
    directions[nonzero] = force[nonzero] / magnitude[nonzero]

    frame_axis = np.arange(force.shape[0], dtype=np.float64)
    for part in range(force.shape[1]):
        missing = mask[:, part] & ~nonzero[:, part]
        if not np.any(missing):
            continue
        known_frames = np.flatnonzero(nonzero[:, part])
        if known_frames.size == 0:
            raise ValueError(f"active target contact part {part} has no nonzero target force sample")
        interpolated = np.column_stack(
            [
                np.interp(frame_axis[missing], known_frames, directions[known_frames, part, axis])
                for axis in range(3)
            ]
        )
        interpolated_norm = np.linalg.norm(interpolated, axis=1, keepdims=True)
        if np.any(interpolated_norm <= 1.0e-8):
            raise ValueError(f"target force directions cancel during interpolation for contact part {part}")
        directions[missing, part] = interpolated / interpolated_norm
    return directions


def normal_force(force_w: np.ndarray, normals_w: np.ndarray) -> np.ndarray:
    force = np.asarray(force_w, dtype=np.float64)
    normals = np.asarray(normals_w, dtype=np.float64)
    if force.shape != normals.shape or force.ndim != 3 or force.shape[2] != 3:
        raise ValueError(f"force_w and normals_w must have matching [T,P,3] shape, got {force.shape}/{normals.shape}")
    norm = np.linalg.norm(normals, axis=2, keepdims=True)
    if np.any(~np.isfinite(normals)) or np.any(norm <= 1.0e-12):
        raise ValueError("normals_w must be finite and nonzero")
    return np.sum(force * (normals / norm), axis=2)


def probe_normal_displacement(
    *,
    target_force_n: np.ndarray,
    actual_force_n: np.ndarray,
    contact_mask: np.ndarray,
    config: NewtonForceResponseConfig,
) -> np.ndarray:
    """Choose a bounded overlap probe using force error direction only."""

    config.validate()
    target, actual, mask = _force_inputs(target_force_n, actual_force_n, contact_mask)
    normalized_error = (target - actual) / float(config.force_error_scale_n)
    displacement = -float(config.probe_displacement_m) * np.tanh(normalized_error)
    return np.where(mask, displacement, 0.0)


def estimate_force_displacement_secant(
    *,
    baseline_force_n: np.ndarray,
    response_force_n: np.ndarray,
    achieved_displacement_m: np.ndarray,
    contact_mask: np.ndarray,
    config: NewtonForceResponseConfig,
    previous_response_n_per_m: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate the black-box Newton force response dF_n/dx_n."""

    config.validate()
    baseline, response, mask = _force_inputs(baseline_force_n, response_force_n, contact_mask)
    displacement = np.asarray(achieved_displacement_m, dtype=np.float64)
    if displacement.shape != baseline.shape:
        raise ValueError(f"achieved_displacement_m must be {baseline.shape}, got {displacement.shape}")
    finite_probe = np.isfinite(displacement) & (np.abs(displacement) >= 1.0e-6)
    raw = np.divide(
        response - baseline,
        displacement,
        out=np.full_like(baseline, np.nan),
        where=finite_probe,
    )
    valid = (
        mask
        & np.isfinite(raw)
        & (np.abs(raw) >= float(config.minimum_response_n_per_m))
        & (np.abs(raw) <= float(config.maximum_response_n_per_m))
    )
    estimate = np.where(valid, raw, np.nan)
    estimate = _fill_temporal_part_response(estimate, valid, radius=int(config.temporal_median_radius))
    filled = np.isfinite(estimate)
    if previous_response_n_per_m is not None:
        previous = np.asarray(previous_response_n_per_m, dtype=np.float64)
        if previous.shape != baseline.shape:
            raise ValueError(f"previous_response_n_per_m must be {baseline.shape}, got {previous.shape}")
        estimate = np.where(filled, estimate, previous)
        filled |= np.isfinite(previous)
    return estimate, filled & mask


def force_matching_displacement(
    *,
    target_force_n: np.ndarray,
    actual_force_n: np.ndarray,
    response_n_per_m: np.ndarray,
    response_valid: np.ndarray,
    contact_mask: np.ndarray,
    config: NewtonForceResponseConfig,
) -> np.ndarray:
    """Convert Newton force error to a trust-limited normal displacement."""

    config.validate()
    target, actual, mask = _force_inputs(target_force_n, actual_force_n, contact_mask)
    response = np.asarray(response_n_per_m, dtype=np.float64)
    valid = np.asarray(response_valid, dtype=bool)
    if response.shape != target.shape or valid.shape != target.shape:
        raise ValueError("response and response_valid must match force [T,P] shape")
    correction = np.divide(
        target - actual,
        response,
        out=np.zeros_like(target),
        where=valid & np.isfinite(response) & (np.abs(response) > 0.0),
    )
    correction = np.clip(correction, -float(config.max_displacement_m), float(config.max_displacement_m))
    probe = probe_normal_displacement(
        target_force_n=target,
        actual_force_n=actual,
        contact_mask=mask & ~valid,
        config=config,
    )
    return np.where(mask, np.where(valid, correction, probe), 0.0)


def _force_inputs(
    target_force_n: np.ndarray,
    actual_force_n: np.ndarray,
    contact_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    target = np.asarray(target_force_n, dtype=np.float64)
    actual = np.asarray(actual_force_n, dtype=np.float64)
    mask = np.asarray(contact_mask, dtype=bool)
    if target.shape != actual.shape or mask.shape != target.shape or target.ndim != 2:
        raise ValueError("target_force_n, actual_force_n, and contact_mask must have matching [T,P] shape")
    if not np.all(np.isfinite(target)) or not np.all(np.isfinite(actual)):
        raise ValueError("force inputs contain NaN or Inf")
    return target, actual, mask


def _fill_temporal_part_response(values: np.ndarray, valid: np.ndarray, *, radius: int) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64).copy()
    frames, parts = result.shape
    for part in range(parts):
        part_valid = np.asarray(valid[:, part], dtype=bool)
        if not np.any(part_valid):
            continue
        source = result[:, part].copy()
        for frame in range(frames):
            start = max(0, frame - radius)
            end = min(frames, frame + radius + 1)
            local = source[start:end][part_valid[start:end]]
            if local.size:
                result[frame, part] = float(np.median(local))
        missing = ~np.isfinite(result[:, part])
        result[missing, part] = float(np.median(source[part_valid]))
    return result
