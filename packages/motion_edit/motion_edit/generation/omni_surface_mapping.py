from __future__ import annotations

from typing import Any

import numpy as np

from motion_edit.generation import omni_contact_graph as omni


def _basis_vector(raw: dict[str, Any], name: str) -> np.ndarray:
    value = np.asarray(raw[name], dtype=np.float64)
    if value.shape != (3,) or not np.all(np.isfinite(value)):
        raise ValueError(f"surface {name} must be a finite 3-vector")
    return value


def _inside_bounds(
    values: np.ndarray,
    bounds: Any,
    *,
    tolerance: float,
) -> np.ndarray:
    if not isinstance(bounds, dict):
        return np.ones(values.shape[0], dtype=bool)
    mask = np.ones(values.shape[0], dtype=bool)
    for column, axis in enumerate(("u", "v")):
        interval = bounds.get(axis)
        if not isinstance(interval, (list, tuple)) or len(interval) != 2:
            continue
        lower, upper = float(interval[0]), float(interval[1])
        mask &= values[:, column] >= lower - tolerance
        mask &= values[:, column] <= upper + tolerance
    return mask


def _surface_follow_points(
    points: np.ndarray,
    source_surface: dict[str, Any],
    target_surface: dict[str, Any],
    *,
    plane_tolerance: float = 2.0e-3,
    bounds_tolerance: float = 2.0e-3,
) -> tuple[np.ndarray, np.ndarray]:
    source_origin = _basis_vector(source_surface, "origin")
    source_normal = _basis_vector(source_surface, "normal")
    source_u = _basis_vector(source_surface, "tangent_u")
    source_v = _basis_vector(source_surface, "tangent_v")
    target_origin = _basis_vector(target_surface, "origin")
    target_u = _basis_vector(target_surface, "tangent_u")
    target_v = _basis_vector(target_surface, "tangent_v")

    source_normal = source_normal / max(float(np.linalg.norm(source_normal)), 1.0e-12)
    source_u = source_u / max(float(np.linalg.norm(source_u)), 1.0e-12)
    source_v = source_v / max(float(np.linalg.norm(source_v)), 1.0e-12)
    target_u = target_u / max(float(np.linalg.norm(target_u)), 1.0e-12)
    target_v = target_v / max(float(np.linalg.norm(target_v)), 1.0e-12)

    relative = np.asarray(points, dtype=np.float64) - source_origin[None, :]
    plane_distance = np.abs(relative @ source_normal)
    uv = np.stack((relative @ source_u, relative @ source_v), axis=1)
    mask = plane_distance <= float(plane_tolerance)
    mask &= _inside_bounds(
        uv,
        source_surface.get("bounds"),
        tolerance=float(bounds_tolerance),
    )

    mapped = np.asarray(points, dtype=np.float64).copy()
    mapped[mask] = (
        target_origin[None, :]
        + uv[mask, :1] * target_u[None, :]
        + uv[mask, 1:] * target_v[None, :]
    )
    return mapped, mask


def _target_object_points_from_plan(
    plan: Any,
    source_points: np.ndarray,
) -> tuple[np.ndarray, list[str]]:
    points = np.asarray(source_points, dtype=np.float64)
    target = points.copy()
    transforms = list(getattr(plan, "surface_transforms", ()) or ())
    if not transforms:
        return target, []

    warnings: list[str] = []
    for raw in transforms:
        transform_id = str(raw.get("transform_id") or "surface_transform")
        source_surface = raw.get("source_surface")
        target_surface = raw.get("target_surface")
        if isinstance(source_surface, dict) and isinstance(target_surface, dict):
            mapped, mask = _surface_follow_points(
                points,
                source_surface,
                target_surface,
            )
            if np.any(mask):
                target[mask] = mapped[mask]
            else:
                warnings.append(
                    f"{transform_id}: no interaction-mesh object vertices matched "
                    "the source surface; object vertices were not moved"
                )
            continue

        # Compatibility for old plans that only persisted a global translation.
        translation = raw.get("translation_world")
        if translation is None:
            warnings.append(
                f"{transform_id}: missing source/target surfaces and translation_world; "
                "object vertices were not moved"
            )
            continue
        delta = np.asarray(translation, dtype=np.float64)
        if delta.shape != (3,) or not np.all(np.isfinite(delta)):
            raise ValueError(f"{transform_id}: translation_world must be a finite 3-vector")
        target += delta[None, :]

    return target, warnings


def install_surface_specific_object_mapping() -> None:
    """Map only vertices bound to transformed surfaces, leaving ground vertices fixed."""

    omni._target_object_points_from_plan = _target_object_points_from_plan
