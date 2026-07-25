from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np


ContactTargetKind = Literal["edited_contact", "fixed_contact"]


@dataclass(frozen=True)
class ContactPatchTarget:
    """Rigid robot-local contact patch target for trajectory IK/projection.

    ``points_local`` are never optimized independently. A downstream kinematic
    solver must transform all points through one body pose so the contact patch
    remains rigid.
    """

    anchor_id: str
    kind: ContactTargetKind
    body_label: str
    shape_labels: tuple[str, ...]
    points_local: np.ndarray
    frames: np.ndarray

    surface_id: str | None = None
    surface_origin_w: np.ndarray | None = None
    surface_normal_w: np.ndarray | None = None
    surface_tangent_u_w: np.ndarray | None = None
    surface_tangent_v_w: np.ndarray | None = None
    target_uv: np.ndarray | None = None
    target_points_w: np.ndarray | None = None
    normals_local: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        points = np.asarray(self.points_local, dtype=np.float64)
        frames = np.asarray(self.frames, dtype=np.int64)
        if not self.anchor_id:
            raise ValueError("contact patch target anchor_id is required")
        if self.kind not in {"edited_contact", "fixed_contact"}:
            raise ValueError(f"{self.anchor_id}: unsupported contact target kind {self.kind!r}")
        if not self.body_label:
            raise ValueError(f"{self.anchor_id}: body_label is required")
        if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] == 0:
            raise ValueError(f"{self.anchor_id}: points_local must have shape [P,3], got {points.shape}")
        if frames.ndim != 1 or frames.size == 0:
            raise ValueError(f"{self.anchor_id}: frames must be a non-empty one-dimensional array")
        if np.any(frames < 0) or np.any(np.diff(frames) <= 0):
            raise ValueError(f"{self.anchor_id}: frames must be strictly increasing and nonnegative")
        if self.shape_labels and len(self.shape_labels) != points.shape[0]:
            raise ValueError(f"{self.anchor_id}: shape_labels count must match patch point count")
        if self.normals_local is not None:
            normals = np.asarray(self.normals_local, dtype=np.float64)
            if normals.shape != points.shape:
                raise ValueError(f"{self.anchor_id}: normals_local must have shape {points.shape}, got {normals.shape}")
        if self.target_points_w is not None:
            target_points = np.asarray(self.target_points_w, dtype=np.float64)
            expected = (frames.size, points.shape[0], 3)
            if target_points.shape != expected:
                raise ValueError(f"{self.anchor_id}: target_points_w must have shape {expected}, got {target_points.shape}")
        if self.target_uv is not None:
            target_uv = np.asarray(self.target_uv, dtype=np.float64)
            expected = (frames.size, points.shape[0], 2)
            if target_uv.shape != expected:
                raise ValueError(f"{self.anchor_id}: target_uv must have shape {expected}, got {target_uv.shape}")
            for name in ("surface_origin_w", "surface_normal_w", "surface_tangent_u_w", "surface_tangent_v_w"):
                value = getattr(self, name)
                if value is None or np.asarray(value).shape != (3,):
                    raise ValueError(f"{self.anchor_id}: {name} with shape [3] is required when target_uv is provided")
        if self.target_points_w is None and self.target_uv is None:
            raise ValueError(f"{self.anchor_id}: either target_points_w or target_uv is required")

    def resolved_target_points_w(self) -> np.ndarray:
        """Return explicit world-space targets, resolving a planar UV target if needed."""

        self.validate()
        if self.target_points_w is not None:
            return np.asarray(self.target_points_w, dtype=np.float64)
        uv = np.asarray(self.target_uv, dtype=np.float64)
        origin = np.asarray(self.surface_origin_w, dtype=np.float64)
        tangent_u = np.asarray(self.surface_tangent_u_w, dtype=np.float64)
        tangent_v = np.asarray(self.surface_tangent_v_w, dtype=np.float64)
        return origin[None, None, :] + uv[..., :1] * tangent_u[None, None, :] + uv[..., 1:] * tangent_v[None, None, :]

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "anchor_id": self.anchor_id,
            "kind": self.kind,
            "body_label": self.body_label,
            "shape_labels": list(self.shape_labels),
            "points_local": np.asarray(self.points_local, dtype=np.float64).tolist(),
            "frames": np.asarray(self.frames, dtype=np.int64).tolist(),
            "surface_id": self.surface_id,
            "surface_origin_w": _optional_array_list(self.surface_origin_w),
            "surface_normal_w": _optional_array_list(self.surface_normal_w),
            "surface_tangent_u_w": _optional_array_list(self.surface_tangent_u_w),
            "surface_tangent_v_w": _optional_array_list(self.surface_tangent_v_w),
            "target_uv": _optional_array_list(self.target_uv),
            "target_points_w": _optional_array_list(self.target_points_w),
            "normals_local": _optional_array_list(self.normals_local),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ContactPatchTarget":
        value = cls(
            anchor_id=str(raw["anchor_id"]),
            kind=str(raw["kind"]),
            body_label=str(raw["body_label"]),
            shape_labels=tuple(str(item) for item in raw.get("shape_labels", [])),
            points_local=np.asarray(raw["points_local"], dtype=np.float64),
            frames=np.asarray(raw["frames"], dtype=np.int64),
            surface_id=raw.get("surface_id"),
            surface_origin_w=_optional_array(raw.get("surface_origin_w")),
            surface_normal_w=_optional_array(raw.get("surface_normal_w")),
            surface_tangent_u_w=_optional_array(raw.get("surface_tangent_u_w")),
            surface_tangent_v_w=_optional_array(raw.get("surface_tangent_v_w")),
            target_uv=_optional_array(raw.get("target_uv")),
            target_points_w=_optional_array(raw.get("target_points_w")),
            normals_local=_optional_array(raw.get("normals_local")),
            metadata=dict(raw.get("metadata") or {}),
        )
        value.validate()
        return value


@dataclass(frozen=True)
class ContactAwareTaskspaceMotion:
    """Task-space regeneration output consumed by trajectory IK.

    The old joint trajectory is an initializer and weak tie-breaker. The primary
    motion target is ``semantic_targets_w`` plus rigid contact patch targets.
    """

    motion_id: str
    fps: float
    frame_start: int
    frame_end: int

    semantic_names: tuple[str, ...]
    semantic_targets_w: np.ndarray
    semantic_weights: np.ndarray
    contacts: tuple[ContactPatchTarget, ...]

    source_qpos: np.ndarray
    source_qvel: np.ndarray
    source_reference_weights: np.ndarray
    boundary_weights: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def frame_count(self) -> int:
        return int(self.frame_end - self.frame_start)

    def validate(self) -> None:
        if not self.motion_id:
            raise ValueError("motion_id is required")
        if not np.isfinite(float(self.fps)) or float(self.fps) <= 0.0:
            raise ValueError("fps must be finite and positive")
        if self.frame_start < 0 or self.frame_end <= self.frame_start:
            raise ValueError("frame interval must be a non-empty half-open interval")
        frame_count = self.frame_count
        semantic = np.asarray(self.semantic_targets_w, dtype=np.float64)
        semantic_weights = np.asarray(self.semantic_weights, dtype=np.float64)
        if semantic.shape != (frame_count, len(self.semantic_names), 3):
            raise ValueError(
                f"semantic_targets_w must have shape {(frame_count, len(self.semantic_names), 3)}, got {semantic.shape}"
            )
        if semantic_weights.shape != (frame_count, len(self.semantic_names)):
            raise ValueError(
                f"semantic_weights must have shape {(frame_count, len(self.semantic_names))}, got {semantic_weights.shape}"
            )
        if not np.all(np.isfinite(semantic)) or not np.all(np.isfinite(semantic_weights)):
            raise ValueError("semantic targets and weights must be finite")
        if np.any(semantic_weights < 0.0):
            raise ValueError("semantic_weights must be nonnegative")

        qpos = np.asarray(self.source_qpos, dtype=np.float64)
        qvel = np.asarray(self.source_qvel, dtype=np.float64)
        source_weights = np.asarray(self.source_reference_weights, dtype=np.float64)
        boundary = np.asarray(self.boundary_weights, dtype=np.float64)
        if qpos.ndim != 2 or qpos.shape[0] != frame_count:
            raise ValueError(f"source_qpos must have shape [T,Q] with T={frame_count}, got {qpos.shape}")
        if qvel.ndim != 2 or qvel.shape[0] != frame_count:
            raise ValueError(f"source_qvel must have shape [T,V] with T={frame_count}, got {qvel.shape}")
        if source_weights.shape != qpos.shape:
            raise ValueError(f"source_reference_weights must have shape {qpos.shape}, got {source_weights.shape}")
        if boundary.shape != (frame_count,):
            raise ValueError(f"boundary_weights must have shape {(frame_count,)}, got {boundary.shape}")
        if np.any(source_weights < 0.0) or np.any(boundary < 0.0):
            raise ValueError("source and boundary weights must be nonnegative")

        for contact in self.contacts:
            contact.validate()
            local_frames = np.asarray(contact.frames, dtype=np.int64) - int(self.frame_start)
            if np.any(local_frames < 0) or np.any(local_frames >= frame_count):
                raise ValueError(f"{contact.anchor_id}: contact frames lie outside the task-space motion window")

    def to_arrays(self) -> dict[str, np.ndarray]:
        self.validate()
        metadata = {
            "schema": "contact_aware_taskspace_motion_v1",
            "motion_id": self.motion_id,
            "fps": float(self.fps),
            "frame_start": int(self.frame_start),
            "frame_end": int(self.frame_end),
            "semantic_names": list(self.semantic_names),
            "contacts": [contact.to_dict() for contact in self.contacts],
            "metadata": self.metadata,
        }
        return {
            "contact_aware_taskspace_json": np.asarray(json.dumps(metadata, sort_keys=True), dtype=object),
            "semantic_targets_w": np.asarray(self.semantic_targets_w, dtype=np.float32),
            "semantic_weights": np.asarray(self.semantic_weights, dtype=np.float32),
            "source_qpos": np.asarray(self.source_qpos, dtype=np.float32),
            "source_qvel": np.asarray(self.source_qvel, dtype=np.float32),
            "source_reference_weights": np.asarray(self.source_reference_weights, dtype=np.float32),
            "boundary_weights": np.asarray(self.boundary_weights, dtype=np.float32),
        }

    @classmethod
    def from_arrays(cls, arrays: dict[str, Any]) -> "ContactAwareTaskspaceMotion":
        raw = json.loads(str(np.asarray(arrays["contact_aware_taskspace_json"], dtype=object).item()))
        value = cls(
            motion_id=str(raw["motion_id"]),
            fps=float(raw["fps"]),
            frame_start=int(raw["frame_start"]),
            frame_end=int(raw["frame_end"]),
            semantic_names=tuple(str(item) for item in raw["semantic_names"]),
            semantic_targets_w=np.asarray(arrays["semantic_targets_w"], dtype=np.float64),
            semantic_weights=np.asarray(arrays["semantic_weights"], dtype=np.float64),
            contacts=tuple(ContactPatchTarget.from_dict(item) for item in raw.get("contacts", [])),
            source_qpos=np.asarray(arrays["source_qpos"], dtype=np.float64),
            source_qvel=np.asarray(arrays["source_qvel"], dtype=np.float64),
            source_reference_weights=np.asarray(arrays["source_reference_weights"], dtype=np.float64),
            boundary_weights=np.asarray(arrays["boundary_weights"], dtype=np.float64),
            metadata=dict(raw.get("metadata") or {}),
        )
        value.validate()
        return value


def write_contact_aware_taskspace_motion(path: str | Path, motion: ContactAwareTaskspaceMotion) -> Path:
    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **motion.to_arrays())
    return output


def read_contact_aware_taskspace_motion(path: str | Path) -> ContactAwareTaskspaceMotion:
    with np.load(Path(path).expanduser(), allow_pickle=True) as data:
        arrays = {key: data[key] for key in data.files}
    return ContactAwareTaskspaceMotion.from_arrays(arrays)


def make_boundary_weights(frame_count: int, ramp_frames: int) -> np.ndarray:
    """Cosine weights that pin only the two window boundaries strongly."""

    count = int(frame_count)
    ramp = max(0, min(int(ramp_frames), count // 2))
    weights = np.zeros(count, dtype=np.float64)
    if ramp == 0:
        return weights
    phase = np.linspace(1.0, 0.0, ramp, endpoint=False, dtype=np.float64)
    edge = 0.5 * (1.0 - np.cos(np.pi * phase))
    weights[:ramp] = edge
    weights[-ramp:] = edge[::-1]
    return weights


def _optional_array(value: Any) -> np.ndarray | None:
    return None if value is None else np.asarray(value, dtype=np.float64)


def _optional_array_list(value: Any) -> Any:
    return None if value is None else np.asarray(value).tolist()
