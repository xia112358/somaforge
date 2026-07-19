from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ContactEventType = Literal[
    "touchdown",
    "liftoff",
    "support_switch",
    "active_change",
    "contact_gain",
    "contact_loss",
]
ContactAnchorRole = Literal["active", "support", "transition", "unknown"]
ContactTransitionType = Literal[
    "step",
    "reach",
    "pull",
    "support_transfer",
    "recovery",
    "micro_adjust",
    "unknown",
]
ContactSurfaceType = Literal["plane", "box_face", "mesh_face", "heightfield", "unknown"]
FRAME_INTERVAL_SEMANTICS = "half_open_[start_frame,end_frame)"


@dataclass(frozen=True)
class ContactSurfaceRecord:
    motion_id: str
    surface_id: str
    object_id: str | None
    surface_type: ContactSurfaceType
    origin: list[float]
    normal: list[float]
    tangent_u: list[float]
    tangent_v: list[float]
    bounds: dict[str, Any] | None = None
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.surface_id:
            raise ValueError("surface_id is required")
        for name in ("origin", "normal", "tangent_u", "tangent_v"):
            value = getattr(self, name)
            if len(value) != 3:
                raise ValueError(f"{self.surface_id}: {name} must have length 3")
        for name in ("normal", "tangent_u", "tangent_v"):
            value = getattr(self, name)
            norm = sum(float(item) * float(item) for item in value) ** 0.5
            if abs(norm - 1.0) > 1e-6:
                raise ValueError(f"{self.surface_id}: {name} must be normalized")
        normal = [float(item) for item in self.normal]
        tangent_u = [float(item) for item in self.tangent_u]
        tangent_v = [float(item) for item in self.tangent_v]
        dot_nu = sum(normal[index] * tangent_u[index] for index in range(3))
        dot_nv = sum(normal[index] * tangent_v[index] for index in range(3))
        if abs(dot_nu) > 1e-6:
            raise ValueError(f"{self.surface_id}: tangent_u must be orthogonal to normal")
        if abs(dot_nv) > 1e-6:
            raise ValueError(f"{self.surface_id}: tangent_v must be orthogonal to normal")
        if self.bounds is not None:
            for axis in ("u", "v"):
                value = self.bounds.get(axis)
                if not isinstance(value, list) or len(value) != 2:
                    raise ValueError(f"{self.surface_id}: bounds[{axis!r}] must be a two-item list")
                if float(value[1]) < float(value[0]):
                    raise ValueError(f"{self.surface_id}: bounds[{axis!r}] max must be >= min")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class ContactEventRecord:
    motion_id: str
    event_id: str
    frame: int
    body: str
    event_type: ContactEventType
    contact_before: list[str] = field(default_factory=list)
    contact_after: list[str] = field(default_factory=list)
    source: str = "contact_mask"
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.frame < 0:
            raise ValueError(f"{self.event_id}: frame must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class ContactAnchorRecord:
    """Contact interval using the repository-wide half-open ``[start, end)`` convention."""

    motion_id: str
    anchor_id: str
    body: str
    start_frame: int
    end_frame: int
    role: ContactAnchorRole = "unknown"
    world_position: list[float] | None = None
    object_position: list[float] | None = None
    object_id: str | None = None
    normal: list[float] | None = None
    surface_id: str | None = None
    surface_type: ContactSurfaceType = "unknown"
    surface_normal: list[float] | None = None
    surface_origin: list[float] | None = None
    surface_tangent_u: list[float] | None = None
    surface_tangent_v: list[float] | None = None
    surface_bounds: dict[str, Any] | None = None
    surface_coordinates: dict[str, Any] | None = None
    surface_binding_source: str | None = None
    patch_id: str | None = None
    editable: bool = True
    position_source: str | None = None
    source: str = "contact_mask"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.start_frame < 0:
            raise ValueError(f"{self.anchor_id}: start_frame must be >= 0")
        if self.end_frame <= self.start_frame:
            raise ValueError(f"{self.anchor_id}: end_frame must be > start_frame for half-open intervals")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class ContactPatchRecord:
    motion_id: str
    patch_id: str
    body: str
    start_frame: int
    end_frame: int
    patch_type: str = "unknown"
    patch_center_world: list[float] | None = None
    link_names: list[str] | None = None
    sphere_ids: list[str] | None = None
    anchor_id: str | None = None
    slip_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.start_frame < 0:
            raise ValueError(f"{self.patch_id}: start_frame must be >= 0")
        if self.end_frame <= self.start_frame:
            raise ValueError(f"{self.patch_id}: end_frame must be > start_frame")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class ContactAnchorEditRecord:
    """Anchor edit whose ``affected_frames`` interval is half-open ``[start, end)``."""

    edit_id: str
    motion_id: str
    anchor_id: str
    body: str
    edit_type: str = "move_contact_anchor"
    old_world_position: list[float] | None = None
    new_world_position: list[float] | None = None
    requested_delta_world: list[float] | None = None
    delta_world: list[float] | None = None
    tangent_delta: list[float] | None = None
    delta_object: list[float] | None = None
    affected_frames: list[int] | None = None
    surface_id: str | None = None
    surface_normal: list[float] | None = None
    surface_coordinates_before: dict[str, Any] | None = None
    surface_coordinates_after: dict[str, Any] | None = None
    constraint_mode: str | None = None
    clamped: bool = False
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.edit_type != "move_contact_anchor":
            raise ValueError(f"{self.edit_id}: unsupported edit_type {self.edit_type}")
        if self.new_world_position is not None and len(self.new_world_position) != 3:
            raise ValueError(f"{self.edit_id}: new_world_position must have length 3")
        if self.old_world_position is not None and len(self.old_world_position) != 3:
            raise ValueError(f"{self.edit_id}: old_world_position must have length 3")
        if self.delta_world is not None and len(self.delta_world) != 3:
            raise ValueError(f"{self.edit_id}: delta_world must have length 3")
        if self.requested_delta_world is not None and len(self.requested_delta_world) != 3:
            raise ValueError(f"{self.edit_id}: requested_delta_world must have length 3")
        if self.tangent_delta is not None and len(self.tangent_delta) != 2:
            raise ValueError(f"{self.edit_id}: tangent_delta must have length 2")
        if self.delta_object is not None and len(self.delta_object) != 3:
            raise ValueError(f"{self.edit_id}: delta_object must have length 3")
        if self.surface_normal is not None and len(self.surface_normal) != 3:
            raise ValueError(f"{self.edit_id}: surface_normal must have length 3")
        if self.affected_frames is not None:
            if len(self.affected_frames) != 2:
                raise ValueError(f"{self.edit_id}: affected_frames must be [start_frame, end_frame)")
            start, end = int(self.affected_frames[0]), int(self.affected_frames[1])
            if start < 0:
                raise ValueError(f"{self.edit_id}: affected_frames start must be >= 0")
            if end <= start:
                raise ValueError(f"{self.edit_id}: affected_frames must be a non-empty half-open interval")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class PoseEditRecord:
    """Task-space pose translation over a half-open frame interval."""

    edit_id: str
    motion_id: str
    affected_frames: list[int]
    translation_world: list[float]
    semantic_names: list[str]
    edit_type: str = "translate_pose"
    weight_scale: float = 1.0
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.edit_type != "translate_pose":
            raise ValueError(f"{self.edit_id}: unsupported pose edit type {self.edit_type!r}")
        if len(self.affected_frames) != 2:
            raise ValueError(f"{self.edit_id}: affected_frames must be [start_frame, end_frame)")
        start, end = (int(value) for value in self.affected_frames)
        if start < 0 or end <= start:
            raise ValueError(f"{self.edit_id}: affected_frames must be a non-empty half-open interval")
        if len(self.translation_world) != 3:
            raise ValueError(f"{self.edit_id}: translation_world must have length 3")
        if not all(math.isfinite(float(value)) for value in self.translation_world):
            raise ValueError(f"{self.edit_id}: translation_world must be finite")
        if not self.semantic_names or any(not str(name) for name in self.semantic_names):
            raise ValueError(f"{self.edit_id}: semantic_names must be non-empty")
        if not math.isfinite(float(self.weight_scale)) or float(self.weight_scale) <= 0.0:
            raise ValueError(f"{self.edit_id}: weight_scale must be finite and positive")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class ContactTransitionRecord:
    motion_id: str
    transition_id: str
    start_frame: int
    end_frame: int
    active_body: str | None = None
    support_bodies: list[str] = field(default_factory=list)
    start_event_id: str | None = None
    end_event_id: str | None = None
    source_anchor_id: str | None = None
    target_anchor_id: str | None = None
    transition_type: ContactTransitionType = "unknown"
    source: str = "contact_mask"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.start_frame < 0:
            raise ValueError(f"{self.transition_id}: start_frame must be >= 0")
        if self.end_frame <= self.start_frame:
            raise ValueError(f"{self.transition_id}: end_frame must be > start_frame")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)
