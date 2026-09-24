"""Exact terrain conditioning shared by offline climb trajectory generators.

This module is deliberately separate from the scan observation contract.  It
is for privileged dataset generation, not for deployment-time perception.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn


PRIVILEGED_GEOMETRY_DIM = 30


class PrivilegedGeometryEncoder(nn.Module):
    """Encode exact box/ground geometry without a sensor-shaped bottleneck."""

    def __init__(self, width: int):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(PRIVILEGED_GEOMETRY_DIM, width),
            nn.SiLU(),
            nn.Linear(width, width),
            nn.SiLU(),
            nn.Linear(width, width),
        )

    def forward(self, geometry):
        return self.network(geometry)


def privileged_geometry_array(data: dict[str, np.ndarray]) -> np.ndarray:
    """Return the exact local terrain condition already stored in a dataset."""

    count = len(data["box_origin"])
    output = np.concatenate(
        (
            data["box_origin"].reshape(count, 3),
            data["box_basis"].reshape(count, 9),
            data["box_edge_start"].reshape(count, 8),
            data["box_edge_inward"].reshape(count, 8),
            data["box_height"].reshape(count, 1),
            data["ground_height_local"].reshape(count, 1),
        ),
        axis=-1,
    ).astype(np.float32)
    if output.shape[1] != PRIVILEGED_GEOMETRY_DIM:
        raise ValueError(f"privileged geometry dimension {output.shape[1]} != {PRIVILEGED_GEOMETRY_DIM}")
    return output


def privileged_geometry_torch(
    box_origin: torch.Tensor,
    box_basis: torch.Tensor,
    box_edge_start: torch.Tensor,
    box_edge_inward: torch.Tensor,
    box_height: torch.Tensor,
) -> torch.Tensor:
    """Build the same exact geometry contract during differentiable unroll."""

    ground_height_local = box_origin[:, 2:3] - box_height[:, None]
    output = torch.cat(
        (
            box_origin.reshape(len(box_origin), 3),
            box_basis.reshape(len(box_origin), 9),
            box_edge_start.reshape(len(box_origin), 8),
            box_edge_inward.reshape(len(box_origin), 8),
            box_height[:, None],
            ground_height_local,
        ),
        dim=-1,
    )
    if output.shape[1] != PRIVILEGED_GEOMETRY_DIM:
        raise ValueError(f"privileged geometry dimension {output.shape[1]} != {PRIVILEGED_GEOMETRY_DIM}")
    return output


def privileged_geometry_from_world(
    torso_origins: np.ndarray,
    torso_yaw_axes: np.ndarray,
    top_surface: dict,
    ground_height: float,
) -> np.ndarray:
    """Express exact world terrain in each current torso-yaw frame."""

    origins = np.asarray(torso_origins, dtype=np.float32)
    axes = np.asarray(torso_yaw_axes, dtype=np.float32)
    count = len(origins)
    top_origin_world = np.asarray(top_surface["origin"], dtype=np.float32)
    top_basis_world = np.stack(
        (
            np.asarray(top_surface["tangent_u"], dtype=np.float32),
            np.asarray(top_surface["tangent_v"], dtype=np.float32),
            np.asarray(top_surface["normal"], dtype=np.float32),
        ),
        axis=-1,
    )
    world_to_local = axes.transpose(0, 2, 1)
    box_origin = np.einsum("nij,nj->ni", world_to_local, top_origin_world[None] - origins)
    box_basis = np.einsum("nij,jk->nik", world_to_local, top_basis_world)
    polygon = np.asarray(
        [
            [float(value["u"]), float(value["v"])]
            for value in top_surface["metadata"]["polygon_surface_coordinates"]
        ],
        dtype=np.float32,
    )
    if polygon.shape != (4, 2):
        raise ValueError(f"expected four box-top corners, got {polygon.shape}")
    signed_area = 0.5 * np.sum(
        polygon[:, 0] * np.roll(polygon[:, 1], -1)
        - np.roll(polygon[:, 0], -1) * polygon[:, 1]
    )
    orientation = 1.0 if signed_area >= 0.0 else -1.0
    edge = np.roll(polygon, -1, axis=0) - polygon
    inward = orientation * np.stack((-edge[:, 1], edge[:, 0]), axis=-1)
    inward /= np.maximum(np.linalg.norm(inward, axis=-1, keepdims=True), 1.0e-8)
    output = np.concatenate(
        (
            box_origin,
            box_basis.reshape(count, 9),
            np.broadcast_to(polygon.reshape(1, 8), (count, 8)),
            np.broadcast_to(inward.reshape(1, 8), (count, 8)),
            np.full((count, 1), float(top_origin_world[2] - ground_height), dtype=np.float32),
            (float(ground_height) - origins[:, 2:3]).astype(np.float32),
        ),
        axis=-1,
    )
    if output.shape[1] != PRIVILEGED_GEOMETRY_DIM:
        raise ValueError(f"privileged geometry dimension {output.shape[1]} != {PRIVILEGED_GEOMETRY_DIM}")
    return output.astype(np.float32)


def _closest_polygon_point(point: np.ndarray, polygon: np.ndarray) -> tuple[np.ndarray, bool]:
    edge = np.roll(polygon, -1, axis=0) - polygon
    signed_area = 0.5 * np.sum(
        polygon[:, 0] * np.roll(polygon[:, 1], -1)
        - np.roll(polygon[:, 0], -1) * polygon[:, 1]
    )
    orientation = 1.0 if signed_area >= 0.0 else -1.0
    inward = orientation * np.stack((-edge[:, 1], edge[:, 0]), axis=-1)
    inside = bool(np.all(np.sum((point[None] - polygon) * inward, axis=-1) >= -1.0e-6))
    if inside:
        return point.copy(), True
    length2 = np.maximum(np.sum(edge * edge, axis=-1), 1.0e-12)
    alpha = np.clip(np.sum((point[None] - polygon) * edge, axis=-1) / length2, 0.0, 1.0)
    candidates = polygon + alpha[:, None] * edge
    return candidates[np.argmin(np.sum((candidates - point[None]) ** 2, axis=-1))], False


def conform_contact_targets_to_geometry(
    target: np.ndarray,
    touchdown: np.ndarray,
    box_origin: np.ndarray,
    box_basis: np.ndarray,
    box_edge_start: np.ndarray,
    box_height: np.ndarray,
) -> np.ndarray:
    """Project predicted contacts onto the exact ground/top/side box surfaces."""

    target = np.asarray(target, dtype=np.float32)
    touchdown = np.asarray(touchdown, dtype=bool)
    single = target.ndim == 2
    if single:
        target = target[None]
        touchdown = touchdown[None]
        box_origin = np.asarray(box_origin, dtype=np.float32)[None]
        box_basis = np.asarray(box_basis, dtype=np.float32)[None]
        box_edge_start = np.asarray(box_edge_start, dtype=np.float32)[None]
        box_height = np.asarray(box_height, dtype=np.float32).reshape(1)
    else:
        box_origin = np.asarray(box_origin, dtype=np.float32)
        box_basis = np.asarray(box_basis, dtype=np.float32)
        box_edge_start = np.asarray(box_edge_start, dtype=np.float32)
        box_height = np.asarray(box_height, dtype=np.float32)
    output = target.copy()
    for row in range(len(output)):
        basis = box_basis[row]
        polygon = box_edge_start[row]
        height = float(box_height[row])
        ground_z = float(box_origin[row, 2] - height)
        for part in np.flatnonzero(touchdown[row]):
            raw = output[row, part]
            surface = (raw - box_origin[row]) @ basis
            closest_uv, inside = _closest_polygon_point(surface[:2], polygon)
            candidates = [np.asarray((raw[0], raw[1], ground_z), dtype=np.float32)]
            top_surface = np.asarray((closest_uv[0], closest_uv[1], 0.0), dtype=np.float32)
            candidates.append(box_origin[row] + basis @ top_surface)
            if part >= 2:
                side_surface = np.asarray(
                    (closest_uv[0], closest_uv[1], np.clip(surface[2], -height, 0.0)), dtype=np.float32
                )
                candidates.append(box_origin[row] + basis @ side_surface)
            candidate = np.stack(candidates)
            # A top candidate outside the footprint was clamped to its exact edge.
            # Keeping ground XY unchanged is correct whenever the point is outside.
            if inside and part < 2 and abs(surface[2]) <= abs(raw[2] - ground_z):
                output[row, part] = candidates[1]
            else:
                output[row, part] = candidate[np.argmin(np.sum((candidate - raw) ** 2, axis=-1))]
    return output[0] if single else output
