#!/usr/bin/env python3
"""Deployment-matched local terrain scan helpers for climb contact models.

Exact terrain geometry may be used here to render a sensor observation for an
offline training sample.  Only the resulting forward-local height values are model
inputs; polygon corners, surface IDs and edit parameters are never returned.
"""

from __future__ import annotations

import numpy as np
import torch

SCAN_FORWARD_MIN_M = -0.20
SCAN_FORWARD_MAX_M = 0.75
SCAN_LATERAL_MIN_M = -0.40
SCAN_LATERAL_MAX_M = 0.40
SCAN_RESOLUTION_M = 0.05
SCAN_ROWS = 20
SCAN_COLS = 17
# The torso reaches roughly 1.1 m above the far-side ground during climb00.
# A 1 m clip erased the ground plane exactly where the terminal foot contact
# had to be generated, making surface-consistent landing impossible.
SCAN_CLIP_M = 1.5
PERSISTENT_CONTACT_MAX_SHIFT_M = 0.10


def clamp_persistent_contact_shift(
    target: np.ndarray,
    current: np.ndarray,
    persistent: np.ndarray,
    maximum_shift_m: float = PERSISTENT_CONTACT_MAX_SHIFT_M,
) -> np.ndarray:
    """Allow support rolling/sliding without permitting an anchor jump."""
    output = np.asarray(target, dtype=np.float32).copy()
    current = np.asarray(current, dtype=np.float32)
    persistent = np.asarray(persistent, dtype=bool)
    delta = output - current
    distance = np.linalg.norm(delta, axis=-1, keepdims=True)
    scale = np.minimum(1.0, maximum_shift_m / np.maximum(distance, 1.0e-8))
    limited = current + delta * scale
    output[persistent] = limited[persistent]
    return output


def local_scan_grid() -> np.ndarray:
    forward = np.linspace(SCAN_FORWARD_MIN_M, SCAN_FORWARD_MAX_M, SCAN_ROWS, dtype=np.float32)
    lateral = np.linspace(SCAN_LATERAL_MIN_M, SCAN_LATERAL_MAX_M, SCAN_COLS, dtype=np.float32)
    x, y = np.meshgrid(forward, lateral, indexing="ij")
    return np.stack((x.reshape(-1), y.reshape(-1), np.zeros(x.size, dtype=np.float32)), axis=-1)


def _scan_edge_points(scan: np.ndarray, obstacle: np.ndarray) -> np.ndarray:
    """Return collision-safe outer samples beside observed height edges.

    A midpoint is geometrically ambiguous at finite scan resolution and can
    lie just inside a rotated box.  The ground-side sample is observed to be
    outside the footprint, so it is a conservative contact anchor without
    consulting privileged polygon geometry.
    """
    grid = local_scan_grid().reshape(SCAN_ROWS, SCAN_COLS, 3)
    mask = obstacle.reshape(SCAN_ROWS, SCAN_COLS)
    points: list[np.ndarray] = []
    for axis in (0, 1):
        left = [slice(None), slice(None)]
        right = [slice(None), slice(None)]
        left[axis] = slice(None, -1)
        right[axis] = slice(1, None)
        changed = mask[tuple(left)] != mask[tuple(right)]
        if np.any(changed):
            left_grid = grid[tuple(left)][changed, :2]
            right_grid = grid[tuple(right)][changed, :2]
            left_is_obstacle = mask[tuple(left)][changed]
            outside = np.where(left_is_obstacle[:, None], right_grid, left_grid)
            points.append(outside)
    if not points:
        return np.empty((0, 2), dtype=np.float32)
    return np.unique(np.concatenate(points, axis=0), axis=0).astype(np.float32)


def conform_contact_targets_to_scan(
    target: np.ndarray,
    touchdown: np.ndarray,
    height_scan: np.ndarray,
) -> np.ndarray:
    """Map predicted contacts onto surfaces represented by the height scan.

    Feet use the observed height at their predicted horizontal location.  For
    hands and knees the closest of ground, obstacle top and an observed height
    discontinuity is used.  This is the selector's output parameterization,
    not a trajectory repair: the infiller receives only the resulting valid
    contact command.
    """
    target = np.asarray(target, dtype=np.float32)
    touchdown = np.asarray(touchdown, dtype=bool)
    height_scan = np.asarray(height_scan, dtype=np.float32)
    single = target.ndim == 2
    if single:
        target = target[None]
        touchdown = touchdown[None]
        height_scan = height_scan[None]
    expected = SCAN_ROWS * SCAN_COLS
    if target.ndim != 3 or target.shape[1:] != (6, 3):
        raise ValueError(f"contact targets must be [B,6,3], got {target.shape}")
    if touchdown.shape != target.shape[:2]:
        raise ValueError(f"touchdown shape {touchdown.shape} != {target.shape[:2]}")
    if height_scan.shape != (len(target), expected):
        raise ValueError(f"height scan must be [B,{expected}], got {height_scan.shape}")

    output = target.copy()
    grid_xy = local_scan_grid()[:, :2]
    scale = np.asarray((SCAN_RESOLUTION_M, SCAN_RESOLUTION_M), dtype=np.float32)
    for row in range(len(output)):
        scan = height_scan[row]
        ground = float(scan.min())
        top = float(scan.max())
        has_obstacle = top - ground >= 0.05
        obstacle = scan > 0.5 * (ground + top) if has_obstacle else np.zeros_like(scan, dtype=bool)
        edge_points = _scan_edge_points(scan, obstacle) if has_obstacle else np.empty((0, 2), np.float32)
        for part in np.flatnonzero(touchdown[row]):
            raw = output[row, part].copy()
            distance = np.sum(((grid_xy - raw[:2]) / scale) ** 2, axis=-1)
            nearest = int(np.argmin(distance))
            if part < 2:
                # Feet always land on a horizontal support surface.  Select
                # ground versus obstacle top from the regressed height, not a
                # quantized edge cell, then make that surface exact.
                output[row, part, 2] = (
                    top if has_obstacle and abs(raw[2] - top) < abs(raw[2] - ground) else ground
                )
                continue

            candidates: list[np.ndarray] = []
            if not obstacle[nearest]:
                candidates.append(np.asarray((raw[0], raw[1], ground), dtype=np.float32))
            if has_obstacle and obstacle[nearest]:
                candidates.append(np.asarray((raw[0], raw[1], top), dtype=np.float32))
            if len(edge_points):
                edge = edge_points[np.argmin(np.sum((edge_points - raw[:2]) ** 2, axis=-1))]
                candidates.append(
                    np.asarray((edge[0], edge[1], np.clip(raw[2], ground, top)), dtype=np.float32)
                )
            if not candidates:
                candidates.append(np.asarray((raw[0], raw[1], ground), dtype=np.float32))
            candidate = np.stack(candidates)
            output[row, part] = candidate[np.argmin(np.sum((candidate - raw) ** 2, axis=-1))]
    return output[0] if single else output


def conform_contact_targets_to_scan_torch(
    target: torch.Tensor,
    touchdown: torch.Tensor,
    height_scan: torch.Tensor,
) -> torch.Tensor:
    """Straight-through Torch wrapper for the scan-surface parameterization."""

    conformed = conform_contact_targets_to_scan(
        target.detach().cpu().numpy(),
        touchdown.detach().cpu().numpy(),
        height_scan.detach().cpu().numpy(),
    )
    exact = torch.as_tensor(conformed, dtype=target.dtype, device=target.device)
    return target + (exact - target).detach()


def scans_from_local_box(
    box_origin: np.ndarray,
    box_basis: np.ndarray,
    edge_start: np.ndarray,
    edge_inward: np.ndarray,
    box_height: np.ndarray,
) -> np.ndarray:
    """Render local height scans from offline box labels.

    Inputs use each sample's torso-yaw frame.  The output matches the runtime
    convention used by GMVQ/WBT scans: terrain height minus torso height.
    """
    box_origin = np.asarray(box_origin, dtype=np.float32)
    box_basis = np.asarray(box_basis, dtype=np.float32)
    edge_start = np.asarray(edge_start, dtype=np.float32)
    edge_inward = np.asarray(edge_inward, dtype=np.float32)
    box_height = np.asarray(box_height, dtype=np.float32)
    grid = local_scan_grid()
    count = len(box_origin)
    points = np.broadcast_to(grid[None], (count, len(grid), 3)).copy()
    relative = points - box_origin[:, None]
    coordinates = np.einsum("bpj,bjk->bpk", relative, box_basis)
    edge_depth = np.einsum(
        "bpvi,bvi->bpv", coordinates[..., None, :2] - edge_start[:, None], edge_inward
    ).min(axis=-1)
    on_top = edge_depth >= 0.0
    ground_height = box_origin[:, 2] - box_height
    heights = np.where(on_top, box_origin[:, None, 2], ground_height[:, None])
    return np.clip(heights, -SCAN_CLIP_M, SCAN_CLIP_M).astype(np.float32)


def scan_from_world_box(
    torso_position: np.ndarray,
    torso_yaw_axes: np.ndarray,
    top_surface: dict,
) -> np.ndarray:
    """Render one runtime-equivalent scan; geometry stays outside model input."""
    origin_w = np.asarray(top_surface["origin"], dtype=np.float32)
    tangent_u_w = np.asarray(top_surface["tangent_u"], dtype=np.float32)
    tangent_v_w = np.asarray(top_surface["tangent_v"], dtype=np.float32)
    normal_w = np.asarray(top_surface["normal"], dtype=np.float32)
    inverse = np.asarray(torso_yaw_axes, dtype=np.float32).T
    box_origin = inverse @ (origin_w - np.asarray(torso_position, dtype=np.float32))
    box_basis = np.stack(
        (inverse @ tangent_u_w, inverse @ tangent_v_w, inverse @ normal_w), axis=-1
    )
    polygon = np.asarray(
        [[float(v["u"]), float(v["v"])] for v in top_surface["metadata"]["polygon_surface_coordinates"]],
        dtype=np.float32,
    )
    signed_area = 0.5 * np.sum(
        polygon[:, 0] * np.roll(polygon[:, 1], -1)
        - np.roll(polygon[:, 0], -1) * polygon[:, 1]
    )
    orientation = 1.0 if signed_area >= 0.0 else -1.0
    edge = np.roll(polygon, -1, axis=0) - polygon
    inward = orientation * np.stack((-edge[:, 1], edge[:, 0]), axis=-1)
    inward /= np.maximum(np.linalg.norm(inward, axis=-1, keepdims=True), 1.0e-8)
    return scans_from_local_box(
        box_origin[None], box_basis[None], polygon[None], inward[None],
        np.asarray([origin_w[2]], dtype=np.float32),
    )[0]


__all__ = [
    "SCAN_CLIP_M",
    "SCAN_COLS",
    "SCAN_FORWARD_MAX_M",
    "SCAN_FORWARD_MIN_M",
    "SCAN_LATERAL_MAX_M",
    "SCAN_LATERAL_MIN_M",
    "SCAN_RESOLUTION_M",
    "SCAN_ROWS",
    "conform_contact_targets_to_scan",
    "conform_contact_targets_to_scan_torch",
    "local_scan_grid",
    "scan_from_world_box",
    "scans_from_local_box",
]
