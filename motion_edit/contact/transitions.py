from __future__ import annotations

from typing import Iterable

import numpy as np

from motion_edit.contact.anchors import anchors_from_contact_mask
from motion_edit.contact.events import bodies_from_mask, body_names_for_mask, detect_contact_events
from motion_edit.contact.patches import patches_from_anchors
from motion_edit.contact.schema import ContactAnchorRecord, ContactEventRecord, ContactTransitionRecord
from motion_edit.schema import SegmentRecord


def mask_string(mask: np.ndarray) -> str:
    return "".join("1" if bool(value) else "0" for value in np.asarray(mask).reshape(-1))


def _as_2d_bool(mask: np.ndarray | None) -> np.ndarray | None:
    if mask is None:
        return None
    arr = np.asarray(mask, dtype=bool)
    if arr.ndim == 1:
        return arr.reshape(arr.shape[0], 1)
    if arr.ndim != 2:
        raise ValueError(f"mask must be 1D or 2D, got shape={arr.shape}")
    return arr


def _event_at_or_after(events: list[ContactEventRecord], start: int, end: int) -> ContactEventRecord | None:
    return next((event for event in events if start <= event.frame < end), None)


def _event_at_or_before(events: list[ContactEventRecord], start: int, end: int) -> ContactEventRecord | None:
    return next((event for event in reversed(events) if start < event.frame <= end), None)


def _anchor_for_body_at(
    anchors: list[ContactAnchorRecord],
    *,
    body: str | None,
    frame: int,
) -> ContactAnchorRecord | None:
    if body is None:
        return None
    return next(
        (
            anchor
            for anchor in anchors
            if anchor.body == body and anchor.start_frame <= frame < anchor.end_frame
        ),
        None,
    )


def _first_body(mask: np.ndarray | None, frame: int, names: list[str]) -> str | None:
    if mask is None or mask.shape[0] == 0:
        return None
    row = mask[max(0, min(frame, mask.shape[0] - 1))]
    bodies = bodies_from_mask(row, names)
    return bodies[0] if bodies else None


def transitions_from_proto_indices(
    *,
    motion_id: str,
    starts: Iterable[int],
    ends: Iterable[int],
    contact_mask: np.ndarray | None,
    active_mask: np.ndarray | None = None,
    support_mask: np.ndarray | None = None,
    body_pos_w: np.ndarray | None = None,
    body_names: Iterable[str] | None = None,
    source: str = "force_contact",
) -> tuple[list[ContactEventRecord], list[ContactAnchorRecord], list[ContactTransitionRecord]]:
    contact = _as_2d_bool(contact_mask)
    active = _as_2d_bool(active_mask)
    support = _as_2d_bool(support_mask)
    reference = next((mask for mask in (contact, active, support) if mask is not None), None)
    names = body_names_for_mask(reference, body_names) if reference is not None else list(body_names or [])
    events = (
        detect_contact_events(
            motion_id=motion_id,
            contact_mask=contact,
            active_mask=active,
            support_mask=support,
            body_names=names,
            source=source,
        )
        if reference is not None
        else []
    )
    anchors = (
        anchors_from_contact_mask(
            motion_id=motion_id,
            contact_mask=contact,
            active_mask=active,
            support_mask=support,
            body_pos_w=body_pos_w,
            body_names=names,
            source=source,
        )
        if contact is not None
        else []
    )
    transitions: list[ContactTransitionRecord] = []
    for index, (start, end) in enumerate(zip(starts, ends)):
        start_i = int(start)
        end_i = int(end)
        if end_i <= start_i:
            continue
        end_sample = max(start_i, end_i - 1)
        active_body = _first_body(active, start_i, names)
        support_bodies = bodies_from_mask(support[start_i], names) if support is not None else []
        start_event = _event_at_or_after(events, start_i, end_i)
        end_event = _event_at_or_before(events, start_i, end_i)
        source_anchor = _anchor_for_body_at(anchors, body=active_body, frame=start_i)
        target_anchor = _anchor_for_body_at(anchors, body=active_body, frame=end_sample)
        transition = ContactTransitionRecord(
            motion_id=motion_id,
            transition_id=f"{motion_id}_{source}_transition_{index:04d}",
            start_frame=start_i,
            end_frame=end_i,
            active_body=active_body,
            support_bodies=support_bodies,
            start_event_id=start_event.event_id if start_event else None,
            end_event_id=end_event.event_id if end_event else None,
            source_anchor_id=source_anchor.anchor_id if source_anchor else None,
            target_anchor_id=target_anchor.anchor_id if target_anchor else None,
            transition_type="support_transfer" if start_event or end_event else "unknown",
            source=source,
            metadata={
                "body_names": names,
                "contact_start": mask_string(contact[start_i]) if contact is not None else None,
                "contact_end": mask_string(contact[end_sample]) if contact is not None else None,
            },
        )
        transition.validate()
        transitions.append(transition)
    return events, anchors, transitions


def transitions_from_event_pairs(
    *,
    motion_id: str,
    events: list[ContactEventRecord],
    anchors: list[ContactAnchorRecord],
    source: str = "contact_mask",
) -> list[ContactTransitionRecord]:
    transitions: list[ContactTransitionRecord] = []
    liftoffs = [event for event in events if event.event_type == "liftoff"]
    touchdowns = [event for event in events if event.event_type == "touchdown"]
    for index, start_event in enumerate(liftoffs):
        end_event = next(
            (
                event
                for event in touchdowns
                if event.body == start_event.body and event.frame > start_event.frame
            ),
            None,
        )
        if end_event is None:
            continue
        source_anchor = _anchor_for_body_at(anchors, body=start_event.body, frame=max(0, start_event.frame - 1))
        target_anchor = _anchor_for_body_at(anchors, body=start_event.body, frame=end_event.frame)
        transition = ContactTransitionRecord(
            motion_id=motion_id,
            transition_id=f"{motion_id}_{source}_event_transition_{index:04d}",
            start_frame=start_event.frame,
            end_frame=end_event.frame,
            active_body=start_event.body,
            support_bodies=end_event.contact_after,
            start_event_id=start_event.event_id,
            end_event_id=end_event.event_id,
            source_anchor_id=source_anchor.anchor_id if source_anchor else None,
            target_anchor_id=target_anchor.anchor_id if target_anchor else None,
            transition_type="step",
            source=source,
        )
        transition.validate()
        transitions.append(transition)
    return transitions


def segment_from_contact_transition(
    *,
    transition: ContactTransitionRecord,
    segment_id: str,
    source: str,
    status: str,
    track: str,
    motion_path: str | None,
    clip_npz: str | None,
    clip_output_dir: str | None,
    clip_file_name: str | None,
    atom_label: str,
    contact_start: str | None,
    contact_end: str | None,
    active: str | None,
    support: str | None,
    events: list[ContactEventRecord],
    anchors: list[ContactAnchorRecord],
    metadata: dict | None = None,
) -> SegmentRecord:
    transition_events = [
        event.to_dict()
        for event in events
        if transition.start_frame <= event.frame < transition.end_frame
    ]
    overlapping_anchors = [
        anchor
        for anchor in anchors
        if anchor.start_frame < transition.end_frame and anchor.end_frame > transition.start_frame
    ]
    meta = dict(metadata or {})
    meta.update(
        {
            "contact_transition": transition.to_dict(),
            "contact_events": transition_events,
            "contact_anchors": [anchor.to_dict() for anchor in overlapping_anchors],
            "contact_patches": [patch.to_dict() for patch in patches_from_anchors(overlapping_anchors)],
            "source_anchor_id": transition.source_anchor_id,
            "target_anchor_id": transition.target_anchor_id,
            "active_body": transition.active_body,
            "support_bodies": transition.support_bodies,
            "transition_type": transition.transition_type,
        }
    )
    segment = SegmentRecord(
        motion_id=transition.motion_id,
        segment_id=segment_id,
        start_frame=transition.start_frame,
        end_frame=transition.end_frame,
        source=source,
        status=status,  # type: ignore[arg-type]
        track=track,
        motion_path=motion_path,
        clip_npz=clip_npz,
        clip_output_dir=clip_output_dir,
        clip_file_name=clip_file_name,
        atom_label=atom_label,
        contact_start=contact_start,
        contact_end=contact_end,
        active=active,
        support=support,
        metadata=meta,
    )
    segment.validate()
    return segment
