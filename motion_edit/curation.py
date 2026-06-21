from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from motion_edit.layers import group_by_motion, iter_layer_files, read_layer, write_layer
from motion_edit.paths import LAYERS_ROOT
from motion_edit.schema import SegmentRecord


def load_layer_segments(source: str) -> list[SegmentRecord]:
    source_path = LAYERS_ROOT / source
    if source_path.is_file():
        return read_layer(source_path, default_source=source_path.stem, default_status="candidate")
    segments: list[SegmentRecord] = []
    for path in iter_layer_files(source_path):
        default_status = "candidate" if "candidates" in source_path.parts else source_path.name
        segments.extend(read_layer(path, default_source=source_path.name, default_status=default_status))
    return segments


def filter_segments(
    segments: list[SegmentRecord],
    *,
    motion_id: str | None = None,
    segment_ids: set[str] | None = None,
    indices: set[int] | None = None,
) -> list[SegmentRecord]:
    by_motion = group_by_motion(segments)
    selected: list[SegmentRecord] = []
    for mid, items in by_motion.items():
        if motion_id is not None and mid != motion_id:
            continue
        for index, segment in enumerate(items):
            if segment_ids is not None and segment.segment_id not in segment_ids:
                continue
            if indices is not None and index not in indices:
                continue
            selected.append(segment)
    return selected


def write_status_layer(status: str, layer_name: str, segments: list[SegmentRecord]) -> Path:
    root = LAYERS_ROOT / status / layer_name
    root.mkdir(parents=True, exist_ok=True)
    changed = [replace(segment, status=status) for segment in segments]
    for motion_id, items in group_by_motion(changed).items():
        write_layer(root / f"{motion_id}.jsonl", items)
    return root
