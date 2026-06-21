from __future__ import annotations

from pathlib import Path

from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.io import (
    read_contact_anchors,
    read_contact_events,
    read_contact_patches,
    read_contact_transitions,
    write_contact_jsonl,
)
from motion_edit.contact.patches import patches_from_anchors


def write_contact_layer(root: str | Path, graph: ContactGraph) -> Path:
    layer_root = Path(root).expanduser()
    write_contact_jsonl(layer_root / "events" / f"{graph.motion_id}.jsonl", graph.events)
    write_contact_jsonl(layer_root / "anchors" / f"{graph.motion_id}.jsonl", graph.anchors)
    write_contact_jsonl(layer_root / "patches" / f"{graph.motion_id}.jsonl", graph.patches)
    write_contact_jsonl(layer_root / "transitions" / f"{graph.motion_id}.jsonl", graph.transitions)
    return layer_root


def read_contact_graph(root: str | Path, motion_id: str) -> ContactGraph:
    layer_root = Path(root).expanduser()
    anchors = read_contact_anchors(layer_root / "anchors" / f"{motion_id}.jsonl")
    patch_path = layer_root / "patches" / f"{motion_id}.jsonl"
    patches = read_contact_patches(patch_path) if patch_path.exists() else patches_from_anchors(anchors)
    return ContactGraph(
        motion_id=motion_id,
        events=read_contact_events(layer_root / "events" / f"{motion_id}.jsonl"),
        anchors=anchors,
        patches=patches,
        transitions=read_contact_transitions(layer_root / "transitions" / f"{motion_id}.jsonl"),
    )
