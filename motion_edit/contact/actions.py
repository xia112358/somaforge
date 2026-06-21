from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from motion_edit.contact.edits import make_anchor_move_edit, move_contact_anchor
from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.patches import patches_from_anchors
from motion_edit.contact.schema import ContactAnchorEditRecord


def move_anchor_in_graph(
    graph: ContactGraph,
    *,
    anchor_id: str,
    delta_world: Iterable[float] | None = None,
    new_world_position: Iterable[float] | None = None,
    source: str = "manual",
) -> tuple[ContactGraph, ContactAnchorEditRecord]:
    moved = None
    anchors = []
    for anchor in graph.anchors:
        if anchor.anchor_id == anchor_id:
            edit = make_anchor_move_edit(anchor, delta_world=delta_world, new_world_position=new_world_position, source=source)
            moved = move_contact_anchor(anchor, delta_world=delta_world, new_world_position=new_world_position, position_source=source)
            anchors.append(moved)
        else:
            anchors.append(anchor)
    if moved is None:
        raise ValueError(f"anchor not found: {anchor_id}")
    return replace(graph, anchors=anchors, patches=patches_from_anchors(anchors)), edit

