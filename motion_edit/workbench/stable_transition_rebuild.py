from __future__ import annotations

from pathlib import Path

from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.schema import ContactTransitionRecord


def stable_proto_transitions_for_editor(
    *,
    graph: ContactGraph,
    motion: str,
    fps: int,
    fallback: list[ContactTransitionRecord],
) -> list[ContactTransitionRecord]:
    """Rebuild editor timeline cuts from stable contact proto masks.

    The editor may clean, split, filter, and bind contact point records before it
    opens. Its time cuts should then be recomputed from the original force/contact
    mask and resolved against the cleaned contact points, instead of inheriting
    raw legacy event-pair transitions from the source layer.
    """

    try:
        from motion_edit.contact.stable_proto import StableContactProtoConfig, transitions_from_stable_contact_anchors
        from motion_edit.force_proto import _load_masked_motion

        inputs = _load_masked_motion(Path(motion).expanduser())
        if inputs.contact is None:
            return fallback
        transitions = transitions_from_stable_contact_anchors(
            motion_id=graph.motion_id,
            anchors=graph.anchors,
            events=graph.events,
            contact_mask=inputs.contact,
            active_mask=inputs.active,
            support_mask=inputs.support,
            body_pos_w=inputs.body_pos_w,
            body_names=inputs.body_names,
            source="contact_editor_stable_proto",
            config=StableContactProtoConfig(fps=float(fps)),
        )
        return transitions or fallback
    except Exception:
        return fallback
