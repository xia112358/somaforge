from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from motion_edit.adapters.holosoma_npz import motion_length
from motion_edit.contact.schema import ContactAnchorEditRecord
from motion_edit.io import write_jsonl
from motion_edit.paths import CATALOGS_ROOT, layer_dir
from motion_edit.schema import EditRecord, MotionRef, SegmentRecord
from motion_edit.layers import write_layer


CONTACT_LTE_FIELDS = (
    "contact_edits",
    "source_anchor_id",
    "target_anchor_id",
    "old_anchor_world",
    "new_anchor_world",
    "affected_frames",
    "body",
    "patch_id",
)


def _contact_lte_metadata(sample: dict) -> dict:
    return {key: sample.get(key) for key in CONTACT_LTE_FIELDS if key in sample}


def _sub3(a: list[float], b: list[float]) -> list[float]:
    return [a[index] - b[index] for index in range(3)]


def _anchor_edit_from_sample(sample_name: str, contact_lte: dict) -> ContactAnchorEditRecord | None:
    anchor_id = contact_lte.get("source_anchor_id") or contact_lte.get("target_anchor_id")
    body = contact_lte.get("body")
    old_world = contact_lte.get("old_anchor_world")
    new_world = contact_lte.get("new_anchor_world")
    if not anchor_id or not body or new_world is None:
        return None
    delta_world = _sub3([float(item) for item in new_world], [float(item) for item in old_world]) if old_world is not None else None
    record = ContactAnchorEditRecord(
        edit_id=f"{sample_name}_move_contact_anchor",
        motion_id=sample_name,
        anchor_id=str(anchor_id),
        body=str(body),
        old_world_position=[float(item) for item in old_world] if old_world is not None else None,
        new_world_position=[float(item) for item in new_world],
        delta_world=delta_world,
        affected_frames=[int(frame) for frame in contact_lte.get("affected_frames")] if contact_lte.get("affected_frames") is not None else None,
        source="lte",
        metadata={
            "target_anchor_id": contact_lte.get("target_anchor_id"),
            "patch_id": contact_lte.get("patch_id"),
            "contact_edits": contact_lte.get("contact_edits"),
            "catalog_sample": sample_name,
        },
    )
    record.validate()
    return record


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
        contact_lte = _contact_lte_metadata(sample)
        if contact_lte:
            anchor_edit = _anchor_edit_from_sample(sample_name, contact_lte)
            metadata["contact_lte"] = {
                "kind": "contact_lte",
                "source_anchor_id": contact_lte.get("source_anchor_id"),
                "target_anchor_id": contact_lte.get("target_anchor_id"),
                "contact_edits": contact_lte.get("contact_edits"),
                "old_anchor_world": contact_lte.get("old_anchor_world"),
                "new_anchor_world": contact_lte.get("new_anchor_world"),
                "affected_frames": contact_lte.get("affected_frames"),
                "body": contact_lte.get("body"),
                "patch_id": contact_lte.get("patch_id"),
            }
            if anchor_edit is not None:
                metadata["contact_lte"]["anchor_edit"] = anchor_edit.to_dict()
                metadata["contact_anchor_edit"] = anchor_edit.to_dict()
                metadata["old_anchor_world"] = anchor_edit.old_world_position
                metadata["new_anchor_world"] = anchor_edit.new_world_position
                metadata["delta_world"] = anchor_edit.delta_world
                metadata["affected_frames"] = anchor_edit.affected_frames
            metadata["source_anchor_id"] = contact_lte.get("source_anchor_id")
            metadata["target_anchor_id"] = contact_lte.get("target_anchor_id")
            metadata["active_body"] = contact_lte.get("body")
        motion_refs.append(MotionRef(motion_id=sample_name, path=motion_path, metadata=metadata))
        edits.append(
            EditRecord(
                edit_id=f"{sample_name}_lte",
                kind="contact_lte" if contact_lte else "lte",
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
