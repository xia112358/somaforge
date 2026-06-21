from __future__ import annotations

from pathlib import Path

import numpy as np

from .schema import SegmentRecord


def _mask_string(mask: np.ndarray) -> str:
    return "".join("1" if bool(value) else "0" for value in np.asarray(mask).reshape(-1))


def segments_from_masked_motion(path: Path, *, source: str = "force_contact", status: str = "candidate") -> list[SegmentRecord]:
    with np.load(path, allow_pickle=True) as data:
        starts = np.asarray(data["proto_start_idx"], dtype=np.int64)
        ends = np.asarray(data["proto_end_idx"], dtype=np.int64)
        contact = np.asarray(data["contact_part_mask"], dtype=bool) if "contact_part_mask" in data else None
        active = np.asarray(data["active_part_mask"], dtype=bool) if "active_part_mask" in data else None
        support = np.asarray(data["support_part_mask"], dtype=bool) if "support_part_mask" in data else None

    motion_id = path.stem
    segments: list[SegmentRecord] = []
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
            contact_start=_mask_string(contact[start_i]) if contact is not None else None,
            contact_end=_mask_string(contact[end_frame]) if contact is not None else None,
            active=_mask_string(active[start_i]) if active is not None else None,
            support=_mask_string(support[start_i]) if support is not None else None,
            metadata={"proto_index": proto_id},
        )
        segment.validate()
        segments.append(segment)
    return segments
