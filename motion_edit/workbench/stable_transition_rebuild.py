from __future__ import annotations

from collections import defaultdict

import numpy as np

from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.schema import ContactAnchorRecord, ContactTransitionRecord
from motion_edit.contact.stable_proto import STABLE_PROTO_ENDPOINT_POLICY, STABLE_PROTO_KIND, StableContactProtoConfig


_INITIAL_FRAME = 0


def _is_active_motion_body(body: str, active_parts: set[str]) -> bool:
    lowered = str(body).lower()
    if lowered in active_parts:
        return True
    return any(part in lowered for part in active_parts)


def _body_sort_key(body: str) -> tuple[int, str]:
    order = ("left_foot", "right_foot", "left_hand", "right_hand", "left_knee", "right_knee")
    lowered = str(body).lower()
    for index, name in enumerate(order):
        if lowered == name or name in lowered:
            return (index, lowered)
    return (len(order), lowered)


def _contact_bodies_at(anchors: list[ContactAnchorRecord], frame: int) -> list[str]:
    bodies = {
        anchor.body
        for anchor in anchors
        if int(anchor.start_frame) <= int(frame) < int(anchor.end_frame)
    }
    return sorted(bodies, key=_body_sort_key)


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
            if anchor.body == body and int(anchor.start_frame) <= int(frame) < int(anchor.end_frame)
        ),
        None,
    )


def _last_anchor_before(
    anchors: list[ContactAnchorRecord],
    *,
    body: str | None,
    frame: int,
) -> ContactAnchorRecord | None:
    if body is None:
        return None
    candidates = [
        anchor
        for anchor in anchors
        if anchor.body == body and int(anchor.end_frame) <= int(frame)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda anchor: (int(anchor.end_frame), int(anchor.start_frame), anchor.anchor_id))


def _cluster_contact_starts(
    anchors: list[ContactAnchorRecord],
    *,
    active_parts: set[str],
    cluster_window: int,
) -> tuple[list[int], dict[int, list[ContactAnchorRecord]]]:
    events = sorted(
        (
            (int(anchor.start_frame), anchor)
            for anchor in anchors
            if int(anchor.start_frame) > _INITIAL_FRAME and _is_active_motion_body(anchor.body, active_parts)
        ),
        key=lambda item: (item[0], _body_sort_key(item[1].body), item[1].anchor_id),
    )
    clusters: dict[int, list[ContactAnchorRecord]] = {}
    cluster_frame: int | None = None
    cluster_items: list[ContactAnchorRecord] = []
    for frame, anchor in events:
        if cluster_frame is None:
            cluster_frame = frame
            cluster_items = [anchor]
            continue
        if frame - cluster_frame <= int(cluster_window):
            cluster_frame = frame
            cluster_items.append(anchor)
            continue
        clusters[cluster_frame] = list(cluster_items)
        cluster_frame = frame
        cluster_items = [anchor]
    if cluster_frame is not None:
        clusters[cluster_frame] = list(cluster_items)
    return sorted(clusters), clusters


def stable_proto_transitions_for_editor(
    *,
    graph: ContactGraph,
    motion: str,
    fps: int,
    fallback: list[ContactTransitionRecord],
) -> list[ContactTransitionRecord]:
    """Rebuild editor timeline cuts from cleaned contact point records.

    Contact-editor cleanup has already refined, split, merged, filtered, and
    surface-bound contact points. Those cleaned contact intervals are the source
    of truth for timeline cuts; the raw force mask is not re-parsed here.
    ``motion`` and ``fps`` are kept in the signature for call-site compatibility.
    """

    _ = motion
    cfg = StableContactProtoConfig(fps=float(fps))
    anchors = sorted(graph.anchors, key=lambda anchor: (int(anchor.start_frame), int(anchor.end_frame), anchor.body, anchor.anchor_id))
    active_parts = set(cfg.active_motion_parts)
    cut_frames, anchors_by_cut = _cluster_contact_starts(
        anchors,
        active_parts=active_parts,
        cluster_window=int(cfg.stable_touchdown_cluster_window),
    )
    if not cut_frames:
        return fallback

    n_frames = max((int(anchor.end_frame) for anchor in anchors), default=0)
    stable_anchor_frames = [_INITIAL_FRAME, *cut_frames]
    if n_frames > 0:
        stable_anchor_frames.append(int(n_frames))
    stable_anchor_frames = sorted(dict.fromkeys(stable_anchor_frames))

    transitions: list[ContactTransitionRecord] = []
    previous_frame = _INITIAL_FRAME
    for proto_index, cut_frame in enumerate(cut_frames):
        cluster_anchors = sorted(anchors_by_cut[cut_frame], key=lambda anchor: (_body_sort_key(anchor.body), anchor.anchor_id))
        active_bodies = sorted({anchor.body for anchor in cluster_anchors}, key=_body_sort_key)
        active_body = active_bodies[0] if active_bodies else None
        support_bodies = [body for body in _contact_bodies_at(anchors, previous_frame) if body not in set(active_bodies)]
        free_bodies = sorted(
            {anchor.body for anchor in anchors} - set(active_bodies) - set(support_bodies),
            key=_body_sort_key,
        )
        target_anchor = cluster_anchors[0] if cluster_anchors else None
        source_anchor = _anchor_for_body_at(anchors, body=active_body, frame=previous_frame)
        if source_anchor is None:
            source_anchor = _last_anchor_before(anchors, body=active_body, frame=cut_frame)
        transition = ContactTransitionRecord(
            motion_id=graph.motion_id,
            transition_id=f"{graph.motion_id}_contact_editor_anchor_proto_{proto_index:04d}",
            start_frame=int(previous_frame),
            end_frame=int(cut_frame),
            active_body=active_body,
            support_bodies=support_bodies,
            start_event_id=None,
            end_event_id=None,
            source_anchor_id=source_anchor.anchor_id if source_anchor else None,
            target_anchor_id=target_anchor.anchor_id if target_anchor else None,
            transition_type="support_transfer" if active_bodies else "unknown",
            source="contact_editor_anchor_proto",
            metadata={
                "segmentation_kind": STABLE_PROTO_KIND,
                "endpoint_policy": STABLE_PROTO_ENDPOINT_POLICY,
                "contact_source": "cleaned_contact_points",
                "outside_policy": "copy_original",
                "proto_index": int(proto_index),
                "anchor_start": int(previous_frame),
                "anchor_end": int(cut_frame),
                "active_bodies": active_bodies,
                "support_bodies": support_bodies,
                "free_bodies": free_bodies,
                "owned_bodies": active_bodies,
                "cluster_anchor_ids": [anchor.anchor_id for anchor in cluster_anchors],
                "stable_anchor_frames": stable_anchor_frames,
                "config": {
                    "stable_touchdown_cluster_window": int(cfg.stable_touchdown_cluster_window),
                    "active_motion_parts": list(cfg.active_motion_parts),
                    "source": "cleaned_contact_points",
                },
            },
        )
        transition.validate()
        transitions.append(transition)
        previous_frame = int(cut_frame)
    return transitions or fallback
