from __future__ import annotations

import json
from pathlib import Path

from motion_edit.layers import group_by_motion
from motion_edit.schema import SegmentRecord


def export_motion_manifest(path: str | Path, segments: list[SegmentRecord]) -> Path:
    out = Path(path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    motions = []
    for motion_id, items in group_by_motion(segments).items():
        motion_path = next((item.motion_path or item.clip_npz for item in items if item.motion_path or item.clip_npz), "")
        motions.append(
            {
                "motion_id": motion_id,
                "motion_file": motion_path,
                "segments": [
                    {
                        "segment_id": item.segment_id,
                        "start_frame": item.start_frame,
                        "end_frame": item.end_frame,
                        "source": item.source,
                        "status": item.status,
                    }
                    for item in items
                ],
            }
        )
    out.write_text(json.dumps({"schema_version": 1, "motions": motions}, indent=2), encoding="utf-8")
    return out
