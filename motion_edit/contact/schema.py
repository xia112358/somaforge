from __future__ import annotations

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
    patch_id: str | None = None
    editable: bool = True
    position_source: str | None = None
    source: str = "contact_mask"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.start_frame < 0:
            raise ValueError(f"{self.anchor_id}: start_frame must be >= 0")
        if self.end_frame <= self.start_frame:
            raise ValueError(f"{self.anchor_id}: end_frame must be > start_frame")

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
    edit_id: str
    motion_id: str
    anchor_id: str
    body: str
    edit_type: str = "move_contact_anchor"
    old_world_position: list[float] | None = None
    new_world_position: list[float] | None = None
    delta_world: list[float] | None = None
    delta_object: list[float] | None = None
    affected_frames: list[int] | None = None
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
