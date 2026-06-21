from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord


def _vector3(value: Iterable[float] | None, *, name: str) -> list[float] | None:
    if value is None:
        return None
    out = [float(item) for item in value]
    if len(out) != 3:
        raise ValueError(f"{name} must have length 3")
    return out


def _add3(a: list[float], b: list[float]) -> list[float]:
    return [a[index] + b[index] for index in range(3)]


def _sub3(a: list[float], b: list[float]) -> list[float]:
    return [a[index] - b[index] for index in range(3)]


def move_contact_anchor(
    anchor: ContactAnchorRecord,
    *,
    delta_world: Iterable[float] | None = None,
    new_world_position: Iterable[float] | None = None,
    position_source: str = "manual",
) -> ContactAnchorRecord:
    if delta_world is None and new_world_position is None:
        raise ValueError("move_contact_anchor requires delta_world or new_world_position")
    old_position = anchor.world_position
    delta = _vector3(delta_world, name="delta_world")
    new_position = _vector3(new_world_position, name="new_world_position")
    if new_position is None:
        if old_position is None:
            raise ValueError("delta_world requires anchor.world_position")
        new_position = _add3([float(item) for item in old_position], delta or [0.0, 0.0, 0.0])
    elif delta is None and old_position is not None:
        delta = _sub3(new_position, [float(item) for item in old_position])
    metadata = dict(anchor.metadata)
    edits = list(metadata.get("contact_anchor_edits") or [])
    edits.append(
        {
            "kind": "move_contact_anchor",
            "old_world_position": old_position,
            "new_world_position": new_position,
            "delta_world": delta,
            "source": position_source,
        }
    )
    metadata["contact_anchor_edits"] = edits
    return replace(anchor, world_position=new_position, position_source=position_source, metadata=metadata)


def make_anchor_move_edit(
    anchor: ContactAnchorRecord,
    *,
    delta_world: Iterable[float] | None = None,
    new_world_position: Iterable[float] | None = None,
    affected_frames: Iterable[int] | None = None,
    source: str = "manual",
    edit_id: str | None = None,
) -> ContactAnchorEditRecord:
    moved = move_contact_anchor(
        anchor,
        delta_world=delta_world,
        new_world_position=new_world_position,
        position_source=source,
    )
    old_position = anchor.world_position
    new_position = moved.world_position
    delta = _vector3(delta_world, name="delta_world")
    if delta is None and old_position is not None and new_position is not None:
        delta = _sub3(new_position, [float(item) for item in old_position])
    record = ContactAnchorEditRecord(
        edit_id=edit_id or f"{anchor.anchor_id}_move_contact_anchor",
        motion_id=anchor.motion_id,
        anchor_id=anchor.anchor_id,
        body=anchor.body,
        old_world_position=old_position,
        new_world_position=new_position,
        delta_world=delta,
        affected_frames=[int(frame) for frame in affected_frames] if affected_frames is not None else [anchor.start_frame, anchor.end_frame],
        source=source,
    )
    record.validate()
    return record
