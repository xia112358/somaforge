from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

MotionVersionKind = Literal["raw", "augmented"]
TokenStatus = Literal["candidate", "accepted", "rejected", "manual"]


@dataclass(frozen=True)
class MotionAssetRecord:
    motion_asset_id: str
    motion_path: str
    source: str = "local"
    fps: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.motion_asset_id:
            raise ValueError("motion_asset_id is required")
        if not self.motion_path:
            raise ValueError(f"{self.motion_asset_id}: motion_path is required")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class MotionVersionRecord:
    motion_version_id: str
    motion_path: str
    kind: MotionVersionKind = "raw"
    base_motion_id: str | None = None
    motion_asset_id: str | None = None
    parent_motion_version_id: str | None = None
    contact_layer: str | None = None
    canonical_segment_path: str | None = None
    token_catalog_path: str | None = None
    edit_plan_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.motion_version_id:
            raise ValueError("motion_version_id is required")
        if not self.motion_path:
            raise ValueError(f"{self.motion_version_id}: motion_path is required")
        if self.kind not in {"raw", "augmented"}:
            raise ValueError(f"{self.motion_version_id}: unsupported kind {self.kind}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class SegmentIndexManifest:
    motion_version_id: str
    segment_path: str
    segment_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.motion_version_id:
            raise ValueError("motion_version_id is required")
        if self.segment_count < 0:
            raise ValueError(f"{self.motion_version_id}: segment_count must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class TokenRecord:
    token_id: str
    motion_version_id: str
    segment_id: str
    token_family: str
    active_body: str | None = None
    support_bodies: list[str] = field(default_factory=list)
    source_anchor_id: str | None = None
    target_anchor_id: str | None = None
    parent_transition_id: str | None = None
    continuous_params: dict[str, Any] = field(default_factory=dict)
    status: TokenStatus = "candidate"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.token_id:
            raise ValueError("token_id is required")
        if not self.motion_version_id:
            raise ValueError(f"{self.token_id}: motion_version_id is required")
        if not self.segment_id:
            raise ValueError(f"{self.token_id}: segment_id is required")
        if not self.token_family:
            raise ValueError(f"{self.token_id}: token_family is required")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)
