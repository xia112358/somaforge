from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from motion_edit.contact.bindings import bind_segment_to_contact_graph
from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.transitions import segment_from_contact_transition
from motion_edit.layers import read_layer
from motion_edit.paths import LAYERS_ROOT
from motion_edit.schema import SegmentRecord
from motion_edit.storage.io import canonical_segment_path, read_canonical_segments, write_canonical_segments, write_motion_version
from motion_edit.storage.schema import MotionVersionRecord


def _parent_transition_id(segment: SegmentRecord) -> str | None:
    transition = segment.metadata.get("contact_transition")
    if isinstance(transition, dict):
        return transition.get("transition_id")
    return segment.metadata.get("parent_transition_id")


def canonicalize_segment(
    segment: SegmentRecord,
    *,
    motion_version_id: str,
    motion_path: str,
    cut_source: str,
) -> SegmentRecord:
    metadata = dict(segment.metadata)
    metadata["motion_version_id"] = motion_version_id
    metadata.setdefault("base_motion_id", segment.motion_id)
    metadata["cut_source"] = cut_source
    parent_transition_id = _parent_transition_id(segment)
    if parent_transition_id:
        metadata["parent_transition_id"] = parent_transition_id
    return replace(segment, motion_path=segment.motion_path or motion_path, clip_npz=segment.clip_npz or motion_path, metadata=metadata)


def segments_from_contact_transitions(
    graph: ContactGraph,
    *,
    motion_version_id: str,
    motion_path: str,
    source: str = "canonical",
    status: str = "candidate",
    cut_source: str = "contact_auto",
) -> list[SegmentRecord]:
    segments: list[SegmentRecord] = []
    for index, transition in enumerate(graph.transitions):
        segment = segment_from_contact_transition(
            transition=transition,
            segment_id=f"{motion_version_id}_seg_{index:04d}",
            source=source,
            status=status,
            track="contact",
            motion_path=motion_path,
            clip_npz=motion_path,
            clip_output_dir=None,
            clip_file_name=None,
            atom_label="",
            contact_start=transition.metadata.get("contact_start"),
            contact_end=transition.metadata.get("contact_end"),
            active=transition.active_body,
            support=",".join(transition.support_bodies),
            events=graph.events,
            anchors=graph.anchors,
            metadata={"parent_transition_id": transition.transition_id, "cut_source": cut_source},
        )
        segments.append(canonicalize_segment(segment, motion_version_id=motion_version_id, motion_path=motion_path, cut_source=cut_source))
    return segments


def load_source_segments_for_motion(source: str | None, motion_id: str) -> list[SegmentRecord]:
    if not source:
        return []
    path = LAYERS_ROOT / source / f"{motion_id}.jsonl"
    if not path.exists():
        return []
    default_status = "candidate" if source.startswith("candidates/") else "manual"
    return read_layer(path, default_source=source.split("/", 1)[-1], default_status=default_status)


def build_canonical_segments(
    *,
    motion_version_id: str,
    motion_path: str,
    graph: ContactGraph,
    source_segments: list[SegmentRecord] | None = None,
    cut_source: str = "contact_auto",
) -> list[SegmentRecord]:
    source_items = source_segments or []
    if source_items:
        rebound = [bind_segment_to_contact_graph(segment, graph) for segment in source_items]
        return [
            canonicalize_segment(segment, motion_version_id=motion_version_id, motion_path=motion_path, cut_source=cut_source)
            for segment in rebound
        ]
    return segments_from_contact_transitions(
        graph,
        motion_version_id=motion_version_id,
        motion_path=motion_path,
        cut_source=cut_source,
    )


def write_motion_version_with_canonical_segments(
    *,
    motion_version_id: str,
    motion_path: str,
    contact_layer: str,
    segments: list[SegmentRecord],
    kind: str = "raw",
    base_motion_id: str | None = None,
) -> tuple[MotionVersionRecord, Path]:
    segment_path = write_canonical_segments(motion_version_id, segments)
    record = MotionVersionRecord(
        motion_version_id=motion_version_id,
        base_motion_id=base_motion_id,
        kind=kind,  # type: ignore[arg-type]
        motion_path=motion_path,
        contact_layer=contact_layer,
        canonical_segment_path=str(canonical_segment_path(motion_version_id)),
    )
    write_motion_version(record)
    return record, segment_path


def mark_canonical_segment_status(
    *,
    motion_version_id: str,
    segment_id: str,
    status: str,
) -> list[SegmentRecord]:
    segments = read_canonical_segments(motion_version_id)
    updated: list[SegmentRecord] = []
    found = False
    for segment in segments:
        if segment.segment_id == segment_id:
            metadata = dict(segment.metadata)
            history = list(metadata.get("status_history") or [])
            history.append({"old_status": segment.status, "new_status": status, "source": "mark_segment_status"})
            metadata["status_history"] = history
            updated.append(replace(segment, status=status, metadata=metadata))  # type: ignore[arg-type]
            found = True
        else:
            updated.append(segment)
    if not found:
        raise ValueError(f"segment not found in canonical segmentation: {segment_id}")
    write_canonical_segments(motion_version_id, updated)
    return updated
