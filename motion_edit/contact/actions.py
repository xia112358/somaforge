from __future__ import annotations

from dataclasses import replace
import math
from typing import Iterable

from motion_edit.contact.edits import make_anchor_move_edit, move_contact_anchor_free, move_contact_anchor_on_surface
from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.io import write_contact_jsonl
from motion_edit.contact.layers import read_contact_graph, write_contact_layer
from motion_edit.contact.patches import patches_from_anchors
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord

DEFAULT_MERGE_CLASSES = {"top", "ground"}


def move_anchor_in_graph(
    graph: ContactGraph,
    *,
    anchor_id: str,
    delta_world: Iterable[float] | None = None,
    tangent_delta: Iterable[float] | None = None,
    new_world_position: Iterable[float] | None = None,
    mode: str = "reject",
    allow_free_3d: bool = False,
    source: str = "manual",
) -> tuple[ContactGraph, ContactAnchorEditRecord]:
    moved = None
    anchors = []
    for anchor in graph.anchors:
        if anchor.anchor_id == anchor_id:
            if allow_free_3d:
                edit = make_anchor_move_edit(anchor, delta_world=delta_world, new_world_position=new_world_position, source=source)
                moved = move_contact_anchor_free(anchor, delta_world=delta_world, new_world_position=new_world_position, position_source=source)
            else:
                requested_world_delta = delta_world
                if requested_world_delta is None and new_world_position is not None:
                    if anchor.world_position is None:
                        raise ValueError("new_world_position requires anchor.world_position")
                    new_position = [float(item) for item in new_world_position]
                    old_position = [float(item) for item in anchor.world_position]
                    requested_world_delta = [new_position[index] - old_position[index] for index in range(3)]
                moved, edit = move_contact_anchor_on_surface(
                    anchor,
                    tangent_delta=tangent_delta,
                    requested_world_delta=requested_world_delta,
                    mode=mode,
                    source=source,
                )
            anchors.append(moved)
        else:
            anchors.append(anchor)
    if moved is None:
        raise ValueError(f"anchor not found: {anchor_id}")
    return replace(graph, anchors=anchors, patches=patches_from_anchors(anchors)), edit


def move_anchor_in_contact_layer(
    source_root,
    destination_root,
    *,
    motion_id: str,
    anchor_id: str,
    delta_world: Iterable[float] | None = None,
    tangent_delta: Iterable[float] | None = None,
    new_world_position: Iterable[float] | None = None,
    mode: str = "reject",
    allow_free_3d: bool = False,
    source: str = "manual",
) -> tuple[ContactGraph, ContactAnchorEditRecord]:
    graph = read_contact_graph(source_root, motion_id)
    moved_graph, edit = move_anchor_in_graph(
        graph,
        anchor_id=anchor_id,
        delta_world=delta_world,
        tangent_delta=tangent_delta,
        new_world_position=new_world_position,
        mode=mode,
        allow_free_3d=allow_free_3d,
        source=source,
    )
    out = write_contact_layer(destination_root, moved_graph)
    write_contact_jsonl(out / "edits" / f"{motion_id}.jsonl", [edit])
    return moved_graph, edit


def merge_nearby_contact_anchors(
    graph: ContactGraph,
    *,
    max_gap: int = 3,
    max_distance: float = 0.06,
    merge_classes: set[str] | None = None,
    same_class_only: bool = True,
    source: str = "merge_contact_anchors",
) -> tuple[ContactGraph, list[dict]]:
    allowed_classes = DEFAULT_MERGE_CLASSES if merge_classes is None else set(merge_classes)
    anchors = sorted(graph.anchors, key=lambda anchor: (anchor.body, anchor.start_frame, anchor.end_frame, anchor.anchor_id))
    merged: list[ContactAnchorRecord] = []
    events: list[dict] = []
    for anchor in anchors:
        if not merged:
            merged.append(anchor)
            continue
        previous = merged[-1]
        if _should_merge_anchor_pair(
            previous,
            anchor,
            max_gap=max_gap,
            max_distance=max_distance,
            allowed_classes=allowed_classes,
            same_class_only=same_class_only,
        ):
            merged_anchor = _merge_anchor_pair(previous, anchor, source=source, max_gap=max_gap, max_distance=max_distance)
            events.append(
                {
                    "kind": "merge_contact_anchors",
                    "source": source,
                    "body": previous.body,
                    "anchor_ids": [previous.anchor_id, anchor.anchor_id],
                    "merged_anchor_id": merged_anchor.anchor_id,
                    "start_frame": merged_anchor.start_frame,
                    "end_frame": merged_anchor.end_frame,
                    "gap": anchor.start_frame - previous.end_frame,
                    "distance": _anchor_distance(previous, anchor),
                    "binding_candidate_class": _binding_candidate_class(merged_anchor),
                }
            )
            merged[-1] = merged_anchor
        else:
            merged.append(anchor)
    merged = sorted(merged, key=lambda anchor: (anchor.start_frame, anchor.end_frame, anchor.body, anchor.anchor_id))
    return replace(graph, anchors=merged, patches=patches_from_anchors(merged)), events


def _should_merge_anchor_pair(
    left: ContactAnchorRecord,
    right: ContactAnchorRecord,
    *,
    max_gap: int,
    max_distance: float,
    allowed_classes: set[str],
    same_class_only: bool,
) -> bool:
    if left.body != right.body:
        return False
    if right.start_frame < left.end_frame:
        return False
    gap = right.start_frame - left.end_frame
    if gap > max_gap:
        return False
    left_class = _binding_candidate_class(left)
    right_class = _binding_candidate_class(right)
    if same_class_only and left_class != right_class:
        return False
    if allowed_classes and (left_class not in allowed_classes or right_class not in allowed_classes):
        return False
    distance = _anchor_distance(left, right)
    return distance is not None and distance <= max_distance


def _binding_candidate_class(anchor: ContactAnchorRecord) -> str | None:
    refinement = anchor.metadata.get("raw_contact_position_refinement")
    if isinstance(refinement, dict) and refinement.get("binding_candidate_class"):
        return str(refinement["binding_candidate_class"])
    return None


def _anchor_distance(left: ContactAnchorRecord, right: ContactAnchorRecord) -> float | None:
    if left.world_position is None or right.world_position is None:
        return None
    return math.sqrt(sum((float(left.world_position[index]) - float(right.world_position[index])) ** 2 for index in range(3)))


def _merge_anchor_pair(left: ContactAnchorRecord, right: ContactAnchorRecord, *, source: str, max_gap: int, max_distance: float) -> ContactAnchorRecord:
    start_frame = min(left.start_frame, right.start_frame)
    end_frame = max(left.end_frame, right.end_frame)
    world_position = _weighted_position(left, right)
    metadata = dict(left.metadata)
    parent_ids = _parent_anchor_ids(left) + _parent_anchor_ids(right)
    metadata["merged_anchor_ids"] = parent_ids
    merges = list(metadata.get("contact_anchor_merges") or [])
    merges.append(
        {
            "source": source,
            "merged_anchor_ids": [left.anchor_id, right.anchor_id],
            "old_bounds": [
                {"start_frame": left.start_frame, "end_frame": left.end_frame},
                {"start_frame": right.start_frame, "end_frame": right.end_frame},
            ],
            "new_bounds": {"start_frame": start_frame, "end_frame": end_frame},
            "gap": right.start_frame - left.end_frame,
            "distance": _anchor_distance(left, right),
            "max_gap": max_gap,
            "max_distance": max_distance,
        }
    )
    metadata["contact_anchor_merges"] = merges
    return replace(
        left,
        anchor_id=f"{left.motion_id}_anchor_{left.body}_{start_frame:06d}_{end_frame:06d}",
        start_frame=start_frame,
        end_frame=end_frame,
        world_position=world_position,
        metadata=metadata,
    )


def _parent_anchor_ids(anchor: ContactAnchorRecord) -> list[str]:
    existing = anchor.metadata.get("merged_anchor_ids")
    if isinstance(existing, list) and existing:
        return [str(item) for item in existing]
    return [anchor.anchor_id]


def _weighted_position(left: ContactAnchorRecord, right: ContactAnchorRecord) -> list[float] | None:
    if left.world_position is None:
        return right.world_position
    if right.world_position is None:
        return left.world_position
    left_weight = max(1, left.end_frame - left.start_frame)
    right_weight = max(1, right.end_frame - right.start_frame)
    total = left_weight + right_weight
    return [
        (float(left.world_position[index]) * left_weight + float(right.world_position[index]) * right_weight) / total
        for index in range(3)
    ]
