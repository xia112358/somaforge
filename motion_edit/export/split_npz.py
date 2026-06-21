from __future__ import annotations

from pathlib import Path
import json

import numpy as np

from motion_edit.adapters.holosoma_npz import load_motion_npz, subset_arrays
from motion_edit.schema import SegmentRecord


def export_split_npz(output_dir: str | Path, segments: list[SegmentRecord]) -> list[Path]:
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for segment in segments:
        source = segment.motion_path or segment.clip_npz
        if not source:
            continue
        arrays = load_motion_npz(source)
        clipped = subset_arrays(arrays, segment.start_frame, segment.end_frame)
        clipped["motion_edit_segment_id"] = np.asarray(segment.segment_id)
        clipped["motion_edit_source_motion"] = np.asarray(str(source))
        clipped["motion_edit_contact_transition"] = np.asarray(
            json.dumps(segment.metadata.get("contact_transition"), sort_keys=True)
            if segment.metadata.get("contact_transition") is not None
            else ""
        )
        clipped["motion_edit_active_body"] = np.asarray(str(segment.metadata.get("active_body") or ""))
        clipped["motion_edit_support_bodies"] = np.asarray(
            json.dumps(segment.metadata.get("support_bodies") or [], sort_keys=True)
        )
        clipped["motion_edit_source_anchor_id"] = np.asarray(str(segment.metadata.get("source_anchor_id") or ""))
        clipped["motion_edit_target_anchor_id"] = np.asarray(str(segment.metadata.get("target_anchor_id") or ""))
        out = root / f"{segment.segment_id}_frames_{segment.start_frame:04d}_{segment.end_frame:04d}.npz"
        np.savez(out, **clipped)
        written.append(out)
    return written
