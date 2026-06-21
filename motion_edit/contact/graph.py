from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from motion_edit.contact.schema import ContactAnchorRecord, ContactEventRecord, ContactTransitionRecord
from motion_edit.contact.transitions import transitions_from_event_pairs, transitions_from_proto_indices


@dataclass(frozen=True)
class ContactGraph:
    motion_id: str
    events: list[ContactEventRecord] = field(default_factory=list)
    anchors: list[ContactAnchorRecord] = field(default_factory=list)
    transitions: list[ContactTransitionRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "motion_id": self.motion_id,
            "events": [event.to_dict() for event in self.events],
            "anchors": [anchor.to_dict() for anchor in self.anchors],
            "transitions": [transition.to_dict() for transition in self.transitions],
        }


def contact_graph_from_masks(
    *,
    motion_id: str,
    contact_mask: np.ndarray | None,
    active_mask: np.ndarray | None = None,
    support_mask: np.ndarray | None = None,
    proto_starts: Iterable[int] | None = None,
    proto_ends: Iterable[int] | None = None,
    body_names: Iterable[str] | None = None,
    source: str = "contact_mask",
) -> ContactGraph:
    starts = list(proto_starts) if proto_starts is not None else []
    ends = list(proto_ends) if proto_ends is not None else []
    events, anchors, transitions = transitions_from_proto_indices(
        motion_id=motion_id,
        starts=starts,
        ends=ends,
        contact_mask=contact_mask,
        active_mask=active_mask,
        support_mask=support_mask,
        body_names=body_names,
        source=source,
    )
    if not transitions:
        transitions = transitions_from_event_pairs(
            motion_id=motion_id,
            events=events,
            anchors=anchors,
            source=source,
        )
    return ContactGraph(motion_id=motion_id, events=events, anchors=anchors, transitions=transitions)
