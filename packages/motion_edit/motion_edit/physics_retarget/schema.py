from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ForceGuidedRetargetConfig:
    max_iterations: int = 4
    force_weight: float = 1.0
    tangential_force_weight: float = 0.25
    unexpected_contact_weight: float = 0.5
    contact_state_weight: float = 0.25
    tracking_weight: float = 0.1
    minimum_relative_improvement: float = 1.0e-3
    force_epsilon_n: float = 1.0

    def validate(self) -> None:
        if self.max_iterations < 0:
            raise ValueError("max_iterations must be nonnegative")
        for name in (
            "force_weight",
            "tangential_force_weight",
            "unexpected_contact_weight",
            "contact_state_weight",
            "tracking_weight",
            "minimum_relative_improvement",
            "force_epsilon_n",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")


@dataclass(frozen=True)
class ProjectionResult:
    motion_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhysicsProjectionRequest:
    current_motion_path: Path
    target_force_w: np.ndarray
    target_mask: np.ndarray
    actual_rollout: "PhysicsRollout"
    iteration: int
    output_dir: Path
    response_rollout: "PhysicsRollout | None" = None
    response_projection_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhysicsRollout:
    motion_path: Path
    force_w: np.ndarray
    mask: np.ndarray
    joint_pos: np.ndarray | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self, *, expected_frames: int | None = None, expected_parts: int = 8) -> None:
        force = np.asarray(self.force_w)
        mask = np.asarray(self.mask)
        if force.ndim != 3 or force.shape[1:] != (expected_parts, 3):
            raise ValueError(f"rollout force_w must be [T,{expected_parts},3], got {force.shape}")
        if mask.shape != force.shape[:2]:
            raise ValueError(f"rollout mask must be {force.shape[:2]}, got {mask.shape}")
        if expected_frames is not None and force.shape[0] != expected_frames:
            raise ValueError(f"rollout has {force.shape[0]} frames, expected {expected_frames}")
        if not np.all(np.isfinite(force)):
            raise ValueError("rollout force_w contains NaN or Inf")
        if self.provenance.get("training_eligible") is not True:
            raise ValueError("physics rollout is not marked training eligible")


@dataclass(frozen=True)
class RetargetIteration:
    iteration: int
    accepted: bool
    objective: float
    previous_best_objective: float | None
    candidate_motion_path: str
    rollout_motion_path: str
    metrics: dict[str, float] = field(default_factory=dict)
    projection_metadata: dict[str, Any] = field(default_factory=dict)
    rollout_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ForceGuidedRetargetResult:
    output_motion_path: Path
    best_candidate_motion_path: Path
    best_rollout_motion_path: Path
    best_objective: float
    iterations: tuple[RetargetIteration, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def report_dict(self) -> dict[str, Any]:
        return {
            "schema": "somaforge_force_guided_physics_retarget_v1",
            "output_motion_path": str(self.output_motion_path),
            "best_candidate_motion_path": str(self.best_candidate_motion_path),
            "best_rollout_motion_path": str(self.best_rollout_motion_path),
            "best_objective": float(self.best_objective),
            "iterations": [item.to_dict() for item in self.iterations],
            "metadata": self.metadata,
        }
