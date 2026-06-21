from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from motion_edit.adapters.holosoma_npz import motion_length
from motion_edit.io import write_jsonl
from motion_edit.paths import CATALOGS_ROOT, layer_dir
from motion_edit.schema import EditRecord, MotionRef, SegmentRecord
from motion_edit.layers import write_layer


def import_lte_catalog(catalog_path: str | Path, *, layer_name: str = "lte") -> tuple[int, int]:
    path = Path(catalog_path).expanduser().resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    samples = data.get("samples", [])
    out_dir = CATALOGS_ROOT / "lte" / layer_name
    out_dir.mkdir(parents=True, exist_ok=True)
    motion_refs: list[MotionRef] = []
    edits: list[EditRecord] = []
    segments: list[SegmentRecord] = []
    for sample in samples:
        sample_name = str(sample["sample"])
        motion_path = str(sample.get("fullbody_ik_motion") or sample.get("taskspace_motion") or "")
        if not motion_path:
            continue
        metadata = {
            "keypoints": sample.get("keypoints"),
            "taskspace_motion": sample.get("taskspace_motion"),
            "distance_offset_m": sample.get("distance_offset_m"),
            "height_offset_m": sample.get("height_offset_m"),
            "terrain_shift": sample.get("terrain_shift"),
            "max_offset_jump": sample.get("max_offset_jump"),
            "max_offset_acceleration": sample.get("max_offset_acceleration"),
            "catalog": str(path),
        }
        motion_refs.append(MotionRef(motion_id=sample_name, path=motion_path, metadata=metadata))
        edits.append(
            EditRecord(
                edit_id=f"{sample_name}_lte",
                kind="lte",
                source="lte_catalog",
                params=metadata,
                output_motion_id=sample_name,
            )
        )
        try:
            n = motion_length(motion_path)
        except Exception:
            n = 0
        if n > 0:
            segments.append(
                SegmentRecord(
                    motion_id=sample_name,
                    segment_id=f"{sample_name}_full",
                    start_frame=0,
                    end_frame=n,
                    source="lte",
                    status="candidate",
                    track="full_motion",
                    motion_path=motion_path,
                    clip_npz=motion_path,
                    clip_file_name=Path(motion_path).name,
                    atom_label="lte_full",
                    metadata=metadata,
                )
            )
    write_jsonl(out_dir / "motions.jsonl", (asdict(item) for item in motion_refs))
    write_jsonl(out_dir / "edits.jsonl", (asdict(item) for item in edits))
    layer_root = layer_dir("candidate", layer_name)
    write_layer(layer_root / "full_motion.jsonl", segments)
    return len(motion_refs), len(segments)
