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
