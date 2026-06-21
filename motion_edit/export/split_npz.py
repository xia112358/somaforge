from __future__ import annotations

from pathlib import Path

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
        out = root / f"{segment.segment_id}_frames_{segment.start_frame:04d}_{segment.end_frame:04d}.npz"
        np.savez(out, **clipped)
        written.append(out)
    return written
