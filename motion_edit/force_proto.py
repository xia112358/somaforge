from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import numpy as np

from .contact import contact_graph_from_masks, mask_string, segment_from_contact_transition
from .contact.graph import ContactGraph
from .schema import SegmentRecord


def _optional_mask(data: np.lib.npyio.NpzFile, key: str) -> np.ndarray | None:
    return np.asarray(data[key], dtype=bool) if key in data else None


def _body_names(data: np.lib.npyio.NpzFile) -> list[str] | None:
    for key in ("contact_body_names", "body_names", "contact_part_names", "part_names"):
        if key not in data:
            continue
        values = np.asarray(data[key]).reshape(-1)
        return [str(value.item() if hasattr(value, "item") else value) for value in values]
    return None


class _MaskedMotion(NamedTuple):
    starts: np.ndarray
    ends: np.ndarray
    contact: np.ndarray | None
    active: np.ndarray | None
    support: np.ndarray | None
    body_names: list[str] | None


def _load_masked_motion(path: Path) -> _MaskedMotion:
    with np.load(path, allow_pickle=True) as data:
        return _MaskedMotion(
            starts=np.asarray(data["proto_start_idx"], dtype=np.int64),
            ends=np.asarray(data["proto_end_idx"], dtype=np.int64),
            contact=_optional_mask(data, "contact_part_mask"),
            active=_optional_mask(data, "active_part_mask"),
            support=_optional_mask(data, "support_part_mask"),
            body_names=_body_names(data),
        )


def contact_graph_from_masked_motion(path: Path, *, source: str = "force_contact") -> ContactGraph:
    inputs = _load_masked_motion(path)
    return contact_graph_from_masks(
        motion_id=path.stem,
        proto_starts=inputs.starts,
        proto_ends=inputs.ends,
        contact_mask=inputs.contact,
        active_mask=inputs.active,
        support_mask=inputs.support,
        body_names=inputs.body_names,
        source=source,
    )


def segments_from_masked_motion(path: Path, *, source: str = "force_contact", status: str = "candidate") -> list[SegmentRecord]:
    inputs = _load_masked_motion(path)
    motion_id = path.stem
    graph = contact_graph_from_masks(
        motion_id=motion_id,
        proto_starts=inputs.starts,
        proto_ends=inputs.ends,
        contact_mask=inputs.contact,
        active_mask=inputs.active,
        support_mask=inputs.support,
        body_names=inputs.body_names,
        source=source,
    )
    segments: list[SegmentRecord] = []
    for proto_id, transition in enumerate(graph.transitions):
        start_i = transition.start_frame
        end_i = transition.end_frame
        end_frame = max(start_i, end_i - 1)
        segment = segment_from_contact_transition(
            transition=transition,
            segment_id=f"{motion_id}_{source}_{proto_id:04d}",
            source=source,
            status=status,
            track="proto",
            motion_path=str(path),
            clip_npz=str(path),
            clip_output_dir=str(Path("motion_edit/data/exports/clips") / motion_id),
            clip_file_name=path.name,
            atom_label=f"{source}_{proto_id:02d}",
            contact_start=mask_string(inputs.contact[start_i]) if inputs.contact is not None else None,
            contact_end=mask_string(inputs.contact[end_frame]) if inputs.contact is not None else None,
            active=mask_string(inputs.active[start_i]) if inputs.active is not None else None,
            support=mask_string(inputs.support[start_i]) if inputs.support is not None else None,
            events=graph.events,
            anchors=graph.anchors,
            metadata={"proto_index": proto_id},
        )
        segment.validate()
        segments.append(segment)

    if not graph.transitions:
        for proto_id, (start, end) in enumerate(zip(inputs.starts, inputs.ends)):
            start_i = int(start)
            end_i = int(end)
            end_frame = max(start_i, end_i - 1)
            segment = SegmentRecord(
                motion_id=motion_id,
                segment_id=f"{motion_id}_{source}_{proto_id:04d}",
                start_frame=start_i,
                end_frame=end_i,
                source=source,
                status=status,  # type: ignore[arg-type]
                track="proto",
                motion_path=str(path),
                clip_npz=str(path),
                clip_output_dir=str(Path("motion_edit/data/exports/clips") / motion_id),
                clip_file_name=path.name,
                atom_label=f"{source}_{proto_id:02d}",
                contact_start=mask_string(inputs.contact[start_i]) if inputs.contact is not None else None,
                contact_end=mask_string(inputs.contact[end_frame]) if inputs.contact is not None else None,
                active=mask_string(inputs.active[start_i]) if inputs.active is not None else None,
                support=mask_string(inputs.support[start_i]) if inputs.support is not None else None,
                metadata={"proto_index": proto_id},
            )
            segment.validate()
            segments.append(segment)
    return segments
