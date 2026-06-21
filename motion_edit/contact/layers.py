from __future__ import annotations

from pathlib import Path

from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.io import (
    read_contact_anchors,
    read_contact_events,
    read_contact_transitions,
    write_contact_jsonl,
)


def write_contact_layer(root: str | Path, graph: ContactGraph) -> Path:
    layer_root = Path(root).expanduser()
    write_contact_jsonl(layer_root / "events" / f"{graph.motion_id}.jsonl", graph.events)
    write_contact_jsonl(layer_root / "anchors" / f"{graph.motion_id}.jsonl", graph.anchors)
    write_contact_jsonl(layer_root / "transitions" / f"{graph.motion_id}.jsonl", graph.transitions)
    return layer_root


def read_contact_graph(root: str | Path, motion_id: str) -> ContactGraph:
    layer_root = Path(root).expanduser()
    return ContactGraph(
        motion_id=motion_id,
        events=read_contact_events(layer_root / "events" / f"{motion_id}.jsonl"),
        anchors=read_contact_anchors(layer_root / "anchors" / f"{motion_id}.jsonl"),
        transitions=read_contact_transitions(layer_root / "transitions" / f"{motion_id}.jsonl"),
    )

