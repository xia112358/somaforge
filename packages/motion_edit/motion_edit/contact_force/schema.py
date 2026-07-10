from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np


DEFAULT_CONTACT_FORCE_PART_ORDER = (
    "left_foot",
    "right_foot",
    "left_hand",
    "right_hand",
    "left_knee",
    "right_knee",
)

WBT_6PART_CONTACT_FORCE_PART_ORDER = (
    "LF",
    "RF",
    "LH",
    "RH",
    "LK",
    "RK",
)

WBT_6PART_CANONICAL_TO_SHORT = {
    "left_foot": "LF",
    "right_foot": "RF",
    "left_hand": "LH",
    "right_hand": "RH",
    "left_knee": "LK",
    "right_knee": "RK",
    "LF": "LF",
    "RF": "RF",
    "LH": "LH",
    "RH": "RH",
    "LK": "LK",
    "RK": "RK",
}


@dataclass(frozen=True)
class ContactForceSample:
    """One contact-force sample returned by a prescribed-state backend.

    ``force_w`` is the translational contact force in world coordinates. The
    sample is already detached from simulation integration: it is a force query
    for the prescribed frame, not a force that will advance the next state.
    """

    frame_index: int
    position_w: np.ndarray
    force_w: np.ndarray
    part_hint: str | None = None
    geom1_name: str | None = None
    geom2_name: str | None = None
    body1_name: str | None = None
    body2_name: str | None = None
    distance: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        pos = np.asarray(self.position_w, dtype=np.float64)
        force = np.asarray(self.force_w, dtype=np.float64)
        if pos.shape != (3,):
            raise ValueError(f"contact sample position_w must have shape (3,), got {pos.shape}")
        if force.shape != (3,):
            raise ValueError(f"contact sample force_w must have shape (3,), got {force.shape}")
        if not np.all(np.isfinite(pos)):
            raise ValueError("contact sample position_w contains NaN or Inf")
        if not np.all(np.isfinite(force)):
            raise ValueError("contact sample force_w contains NaN or Inf")


@dataclass(frozen=True)
class CanonicalContactForceField:
    """Part-level force reference used by force-aware tracking policies."""

    part_order: tuple[str, ...]
    force_w: np.ndarray
    position_w: np.ndarray
    mask: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        force = np.asarray(self.force_w, dtype=np.float64)
        position = np.asarray(self.position_w, dtype=np.float64)
        mask = np.asarray(self.mask, dtype=bool)
        if force.ndim != 3 or force.shape[2] != 3:
            raise ValueError(f"force_w must have shape [T, P, 3], got {force.shape}")
        if position.shape != force.shape:
            raise ValueError(f"position_w must have shape {force.shape}, got {position.shape}")
        if mask.shape != force.shape[:2]:
            raise ValueError(f"mask must have shape {force.shape[:2]}, got {mask.shape}")
        if len(self.part_order) != force.shape[1]:
            raise ValueError(f"part_order length {len(self.part_order)} does not match force width {force.shape[1]}")
        if not np.all(np.isfinite(force)):
            raise ValueError("force_w contains NaN or Inf")
        finite_positions = np.isfinite(position) | ~mask[..., None]
        if not bool(np.all(finite_positions)):
            raise ValueError("position_w contains NaN or Inf for active contact frames")

    def to_npz_arrays(self) -> dict[str, np.ndarray]:
        self.validate()
        return {
            "contact_force_part_order": np.asarray(self.part_order, dtype=np.str_),
            "contact_force_part_w": np.asarray(self.force_w, dtype=np.float64),
            "contact_force_part_force_w": np.asarray(self.force_w, dtype=np.float64),
            "contact_force_part_position_w": np.asarray(self.position_w, dtype=np.float64),
            "contact_force_part_mask": np.asarray(self.mask, dtype=bool),
        }

    def to_wbt_6part_npz_arrays(self) -> dict[str, np.ndarray]:
        self.validate()
        source_index = {
            WBT_6PART_CANONICAL_TO_SHORT.get(str(part), str(part)): index
            for index, part in enumerate(self.part_order)
        }
        force = np.zeros((self.force_w.shape[0], len(WBT_6PART_CONTACT_FORCE_PART_ORDER), 3), dtype=np.float64)
        position = np.zeros_like(force)
        mask = np.zeros((self.force_w.shape[0], len(WBT_6PART_CONTACT_FORCE_PART_ORDER)), dtype=bool)
        for dst_i, part in enumerate(WBT_6PART_CONTACT_FORCE_PART_ORDER):
            src_i = source_index.get(part)
            if src_i is None:
                continue
            force[:, dst_i] = np.asarray(self.force_w[:, src_i], dtype=np.float64)
            position[:, dst_i] = np.asarray(self.position_w[:, src_i], dtype=np.float64)
            mask[:, dst_i] = np.asarray(self.mask[:, src_i], dtype=bool)
        return {
            "contact_force_part_order": np.asarray(WBT_6PART_CONTACT_FORCE_PART_ORDER, dtype=np.str_),
            "contact_force_part_w": force,
            "contact_force_part_force_w": force,
            "contact_force_part_position_w": position,
            "contact_force_part_mask": mask,
        }


@dataclass(frozen=True)
class PrescribedContactSolveConfig:
    """Configuration for kinematic contact-force baking.

    The intended state policy is prescribed playback: each frame overwrites the
    simulator state with qpos/qvel/qacc from the reference, solves contacts, and
    records forces without integrating or applying them back to the body state.
    """

    part_order: tuple[str, ...] = DEFAULT_CONTACT_FORCE_PART_ORDER
    solve_mode: Literal["forward", "inverse"] = "forward"
    assignment_max_distance: float = 0.35
    force_norm_eps: float = 1.0e-8
    zero_inactive_contacts: bool = True
    force_unit_scale: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.solve_mode not in {"forward", "inverse"}:
            raise ValueError("solve_mode must be 'forward' or 'inverse'")
        for name in ("assignment_max_distance", "force_norm_eps", "force_unit_scale"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative")
