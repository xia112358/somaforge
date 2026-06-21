from __future__ import annotations

from pathlib import Path

import numpy as np

from .contact import mask_string, segment_from_contact_transition, transitions_from_proto_indices
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


def segments_from_masked_motion(path: Path, *, source: str = "force_contact", status: str = "candidate") -> list[SegmentRecord]:
    with np.load(path, allow_pickle=True) as data:
        starts = np.asarray(data["proto_start_idx"], dtype=np.int64)
        ends = np.asarray(data["proto_end_idx"], dtype=np.int64)
        contact = _optional_mask(data, "contact_part_mask")
        active = _optional_mask(data, "active_part_mask")
        support = _optional_mask(data, "support_part_mask")
        body_names = _body_names(data)

    motion_id = path.stem
    events, anchors, transitions = transitions_from_proto_indices(
        motion_id=motion_id,
        starts=starts,
        ends=ends,
        contact_mask=contact,
        active_mask=active,
        support_mask=support,
        body_names=body_names,
        source=source,
    )
    segments: list[SegmentRecord] = []
    for proto_id, transition in enumerate(transitions):
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
            contact_start=mask_string(contact[start_i]) if contact is not None else None,
            contact_end=mask_string(contact[end_frame]) if contact is not None else None,
            active=mask_string(active[start_i]) if active is not None else None,
            support=mask_string(support[start_i]) if support is not None else None,
            events=events,
            anchors=anchors,
            metadata={"proto_index": proto_id},
        )
        segment.validate()
        segments.append(segment)

    if not transitions:
        for proto_id, (start, end) in enumerate(zip(starts, ends)):
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
                contact_start=mask_string(contact[start_i]) if contact is not None else None,
                contact_end=mask_string(contact[end_frame]) if contact is not None else None,
                active=mask_string(active[start_i]) if active is not None else None,
                support=mask_string(support[start_i]) if support is not None else None,
                metadata={"proto_index": proto_id},
            )
            segment.validate()
            segments.append(segment)
    return segments
