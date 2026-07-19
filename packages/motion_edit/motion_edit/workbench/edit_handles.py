from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from typing import Any

from motion_edit.contact.schema import ContactAnchorRecord

FOOT_PARENT_BY_BODY = {
    "left_heel": "left_foot",
    "left_toe": "left_foot",
    "left_sole": "left_foot",
    "right_heel": "right_foot",
    "right_toe": "right_foot",
    "right_sole": "right_foot",
}

POSITION_OFFSET_EPSILON = 1.0e-6


@dataclass(frozen=True)
class ContactEpisodeHandle:
    handle_id: str
    motion_id: str
    body: str
    start_frame: int
    end_frame: int
    member_anchor_ids: list[str]
    world_position: list[float]
    surface_id: str
    object_id: str | None
    surface_coordinates: dict[str, float]
    surface_origin: list[float]
    surface_normal: list[float]
    surface_tangent_u: list[float]
    surface_tangent_v: list[float]
    surface_bounds: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def contact_episode_handle_payloads(
    handles: Iterable[ContactEpisodeHandle],
    initial_handles: Iterable[ContactEpisodeHandle],
) -> list[dict[str, Any]]:
    """Serialize handles with their read-only displacement from session start."""
    initial_by_id = {handle.handle_id: handle for handle in initial_handles}
    payloads: list[dict[str, Any]] = []
    for handle in handles:
        payload = handle.to_dict()
        initial = initial_by_id.get(handle.handle_id, handle)
        initial_position = [float(value) for value in initial.world_position]
        delta = [float(handle.world_position[index]) - initial_position[index] for index in range(3)]
        tangent_u = [float(value) for value in handle.surface_tangent_u]
        tangent_v = [float(value) for value in handle.surface_tangent_v]
        offset_u = sum(delta[index] * tangent_u[index] for index in range(3))
        offset_v = sum(delta[index] * tangent_v[index] for index in range(3))
        payload.update(
            initial_world_position=initial_position,
            position_offset={"u": offset_u, "v": offset_v},
            has_position_offset=max(abs(offset_u), abs(offset_v)) > POSITION_OFFSET_EPSILON,
        )
        payloads.append(payload)
    return payloads


def parent_contact_body(body: str) -> str:
    return FOOT_PARENT_BY_BODY.get(str(body), str(body))


def _weighted_vector(members: list[ContactAnchorRecord], field_name: str) -> list[float]:
    values: list[tuple[list[float], float]] = []
    for anchor in members:
        value = getattr(anchor, field_name)
        if value is None:
            continue
        values.append(([float(item) for item in value], float(max(1, anchor.end_frame - anchor.start_frame))))
    if not values:
        raise ValueError(f"contact episode has no {field_name}")
    total = sum(weight for _, weight in values)
    return [sum(value[index] * weight for value, weight in values) / total for index in range(3)]


def _weighted_surface_coordinates(members: list[ContactAnchorRecord]) -> dict[str, float]:
    values: list[tuple[float, float, float]] = []
    for anchor in members:
        coordinates = anchor.surface_coordinates
        if not coordinates or "u" not in coordinates or "v" not in coordinates:
            continue
        weight = float(max(1, anchor.end_frame - anchor.start_frame))
        values.append((float(coordinates["u"]), float(coordinates["v"]), weight))
    if not values:
        # Legacy graphs may have a surface id and world point without cached
        # UV coordinates. Episode generation still uses the world trajectory;
        # UV remains a neutral display fallback until the layer is rebound.
        return {"u": 0.0, "v": 0.0}
    total = sum(weight for _, _, weight in values)
    return {
        "u": sum(u * weight for u, _, weight in values) / total,
        "v": sum(v * weight for _, v, weight in values) / total,
    }


def _episode_handle(members: list[ContactAnchorRecord]) -> ContactEpisodeHandle:
    ordered = sorted(members, key=lambda item: (item.start_frame, item.end_frame, item.anchor_id))
    first = ordered[0]
    if not first.surface_id:
        raise ValueError(f"{first.anchor_id}: contact episode requires a bound surface")
    digest = sha1(
        "\n".join(item.anchor_id for item in ordered).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()[:10]
    body = parent_contact_body(first.body)
    start_frame = min(item.start_frame for item in ordered)
    end_frame = max(item.end_frame for item in ordered)
    source_bodies = sorted({item.body for item in ordered})
    patch_roles = sorted(
        {str(item.metadata.get("patch_role")) for item in ordered if item.metadata.get("patch_role") is not None}
    )
    statuses = [
        str(item.metadata.get("surface_editor_status"))
        for item in ordered
        if item.metadata.get("surface_editor_status")
    ]
    return ContactEpisodeHandle(
        handle_id=f"{first.motion_id}_episode_{body}_{start_frame:06d}_{end_frame:06d}_{digest}",
        motion_id=first.motion_id,
        body=body,
        start_frame=start_frame,
        end_frame=end_frame,
        member_anchor_ids=[item.anchor_id for item in ordered],
        world_position=_weighted_vector(ordered, "world_position"),
        surface_id=first.surface_id,
        object_id=first.object_id,
        surface_coordinates=_weighted_surface_coordinates(ordered),
        surface_origin=[float(item) for item in (first.surface_origin or [0.0, 0.0, 0.0])],
        surface_normal=[float(item) for item in (first.surface_normal or [0.0, 0.0, 1.0])],
        surface_tangent_u=[float(item) for item in (first.surface_tangent_u or [1.0, 0.0, 0.0])],
        surface_tangent_v=[float(item) for item in (first.surface_tangent_v or [0.0, 1.0, 0.0])],
        surface_bounds=first.surface_bounds,
        metadata={
            "kind": "contact_episode",
            "member_count": len(ordered),
            "source_bodies": source_bodies,
            "patch_roles": patch_roles,
            "surface_editor_status": "edited" if "edited" in statuses else "bound",
        },
    )


def build_contact_episode_handles(
    anchors: Iterable[ContactAnchorRecord],
    *,
    max_gap_frames: int = 0,
    min_duration_frames: int = 1,
) -> list[ContactEpisodeHandle]:
    grouped: dict[tuple[str, str | None, str | None], list[ContactAnchorRecord]] = {}
    for anchor in anchors:
        if not anchor.editable or anchor.world_position is None or not anchor.surface_id:
            continue
        key = (parent_contact_body(anchor.body), anchor.surface_id, anchor.object_id)
        grouped.setdefault(key, []).append(anchor)

    episodes: list[ContactEpisodeHandle] = []
    for members in grouped.values():
        ordered = sorted(members, key=lambda item: (item.start_frame, item.end_frame, item.anchor_id))
        connected: list[ContactAnchorRecord] = []
        connected_end = -1
        for anchor in ordered:
            if connected and anchor.start_frame <= connected_end + max(0, int(max_gap_frames)):
                connected.append(anchor)
                connected_end = max(connected_end, anchor.end_frame)
                continue
            if connected:
                episode = _episode_handle(connected)
                if episode.end_frame - episode.start_frame >= max(1, int(min_duration_frames)):
                    episodes.append(episode)
            connected = [anchor]
            connected_end = anchor.end_frame
        if connected:
            episode = _episode_handle(connected)
            if episode.end_frame - episode.start_frame >= max(1, int(min_duration_frames)):
                episodes.append(episode)
    return sorted(episodes, key=lambda item: (item.start_frame, item.end_frame, item.body, item.handle_id))
