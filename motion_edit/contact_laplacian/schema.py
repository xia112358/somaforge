from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np


@dataclass(frozen=True)
class BatchContactLaplacianConfig:
    num_iters: int = 5
    damping: float = 1.0e-4
    trust_region: float = 0.05
    edit_contact_weight: float = 1000.0
    fixed_contact_weight: float = 1000.0
    temporal_laplacian_weight: float = 10.0
    body_relative_weight: float = 10.0
    q_prior_weight: float = 1.0
    q_smooth_weight: float = 1.0
    mesh_laplacian_weight: float = 0.0
    finite_difference_eps: float = 1.0e-4
    line_search_max_steps: int = 8
    relative_cost_tolerance: float = 1.0e-8
    step_tolerance: float = 1.0e-10


@dataclass(frozen=True)
class ContactHandleSpec:
    anchor_id: str
    body: str
    semantic_name: str
    frames: np.ndarray
    target_xyz: np.ndarray
    kind: Literal["edited_contact", "fixed_contact"]
    weight: float
    surface_id: str | None = None
    object_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        frames = np.asarray(self.frames, dtype=np.int64)
        target = np.asarray(self.target_xyz, dtype=np.float64)
        if frames.ndim != 1:
            raise ValueError(f"{self.anchor_id}: frames must be one-dimensional")
        if target.shape != (len(frames), 3):
            raise ValueError(f"{self.anchor_id}: target_xyz must have shape {(len(frames), 3)}, got {target.shape}")
        if self.kind not in {"edited_contact", "fixed_contact"}:
            raise ValueError(f"{self.anchor_id}: unsupported handle kind {self.kind!r}")
        if not np.all(np.isfinite(target)):
            raise ValueError(f"{self.anchor_id}: target_xyz contains NaN or Inf")
        if float(self.weight) < 0.0 or not np.isfinite(float(self.weight)):
            raise ValueError(f"{self.anchor_id}: weight must be finite and nonnegative")


@dataclass(frozen=True)
class ContactLaplacianSolveResult:
    q: np.ndarray
    metadata: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InteractionMeshSpec:
    """Lightweight interaction mesh for the experimental batch solver.

    Vertices are ordered as ``robot_points`` followed by fixed
    ``object_points``. Edges may be provided explicitly; otherwise callers may
    request KNN edges over the reference vertices.
    """

    robot_points: tuple[str, ...]
    object_points: np.ndarray
    edges: tuple[tuple[int, int], ...] = ()
    knn_k: int = 0
    reference_robot_points: np.ndarray | None = None
    reference_object_points: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.robot_points:
            raise ValueError("interaction mesh requires at least one robot point")
        object_points = np.asarray(self.object_points, dtype=np.float64)
        if object_points.ndim != 2 or object_points.shape[1] != 3:
            raise ValueError(f"object_points must have shape [N, 3], got {object_points.shape}")
        if not np.all(np.isfinite(object_points)):
            raise ValueError("object_points contains NaN or Inf")
        total_vertices = len(self.robot_points) + len(object_points)
        for edge in self.edges:
            if len(edge) != 2:
                raise ValueError(f"mesh edge must have two vertices, got {edge!r}")
            a, b = int(edge[0]), int(edge[1])
            if a == b or a < 0 or b < 0 or a >= total_vertices or b >= total_vertices:
                raise ValueError(f"mesh edge {edge!r} outside vertex range 0..{total_vertices - 1}")
        if int(self.knn_k) < 0:
            raise ValueError("knn_k must be nonnegative")
        if self.reference_robot_points is not None:
            ref_robot = np.asarray(self.reference_robot_points, dtype=np.float64)
            if ref_robot.ndim not in {2, 3} or ref_robot.shape[-2:] != (len(self.robot_points), 3):
                raise ValueError(
                    "reference_robot_points must have shape [R, 3] or [T, R, 3], "
                    f"got {ref_robot.shape}"
                )
        if self.reference_object_points is not None:
            ref_object = np.asarray(self.reference_object_points, dtype=np.float64)
            if ref_object.shape != object_points.shape:
                raise ValueError(f"reference_object_points must have shape {object_points.shape}, got {ref_object.shape}")
