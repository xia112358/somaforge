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
                        "active": item.active,
                        "support": item.support,
                        "contact_start": item.contact_start,
                        "contact_end": item.contact_end,
                        "transition_type": item.metadata.get("transition_type"),
                        "source_anchor_id": item.metadata.get("source_anchor_id"),
                        "target_anchor_id": item.metadata.get("target_anchor_id"),
                        "old_anchor_world": item.metadata.get("old_anchor_world"),
                        "new_anchor_world": item.metadata.get("new_anchor_world"),
                        "delta_world": item.metadata.get("delta_world"),
                        "affected_frames": item.metadata.get("affected_frames"),
                        "active_body": item.metadata.get("active_body"),
                        "support_bodies": item.metadata.get("support_bodies"),
                        "contact_metadata": {
                            "transition": item.metadata.get("contact_transition"),
                            "event_count": len(item.metadata.get("contact_events") or []),
                            "anchor_count": len(item.metadata.get("contact_anchors") or []),
                            "patch_count": len(item.metadata.get("contact_patches") or []),
                            "patches": item.metadata.get("contact_patches") or [],
                            "anchor_edit": item.metadata.get("contact_anchor_edit"),
                        },
                    }
                    for item in items
                ],
            }
        )
    out.write_text(json.dumps({"schema_version": 1, "motions": motions}, indent=2), encoding="utf-8")
    return out
