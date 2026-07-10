from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class PreparedSegment:
    segment: np.ndarray
    valid_mask: np.ndarray
    length: int
    segment_id: str
    motion_id: str
    source_path: str
    start_frame: int
    end_frame: int
    active_body: str


def _iter_jsonl_paths(path: Path) -> list[Path]:
    path = path.expanduser().resolve()
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.glob("*.jsonl"))
    raise FileNotFoundError(path)


def _iter_records(paths: Iterable[Path]) -> Iterable[dict]:
    for path in paths:
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON") from exc


def _iter_cut_summary_records(path: Path) -> Iterable[dict]:
    path = path.expanduser().resolve()
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        raise ValueError(f"cut summary must be a list, got {type(payload).__name__}")
    for item in payload:
        if not isinstance(item, dict):
            continue
        motion_path = item.get("motion_path")
        motion_id = item.get("motion_id") or item.get("motion_asset_id") or ""
        cut_frames = item.get("cut_frames") or []
        if not motion_path or len(cut_frames) < 2:
            continue
        frames = [int(frame) for frame in cut_frames]
        for proto_index, (start, end) in enumerate(zip(frames[:-1], frames[1:])):
            yield {
                "track": "proto",
                "clip_npz": str(motion_path),
                "motion_path": str(motion_path),
                "motion_id": str(motion_id),
                "segment_id": f"{motion_id}_cut_{proto_index:04d}",
                "start_frame": int(start),
                "end_frame": int(end),
                "metadata": {
                    "cut_source": "motion_edit_cut_summary",
                    "proto_index": int(proto_index),
                    "ready_layer": item.get("ready_layer"),
                    "motion_asset_id": item.get("motion_asset_id"),
                },
            }


def _resolve_motion_path(raw_path: str, *, manifest_path: Path, motion_root: Path | None) -> Path:
    path = Path(str(raw_path)).expanduser()
    if path.is_absolute():
        return path
    candidates: list[Path] = []
    if motion_root is not None:
        candidates.append(motion_root.expanduser() / path)
    candidates.append(Path.cwd() / path)
    candidates.append(manifest_path.parent / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def _iter_motion_edit_manifest_records(path: Path, *, motion_root: Path | None = None) -> Iterable[dict]:
    path = path.expanduser().resolve()
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"motion_edit manifest must be an object, got {type(payload).__name__}")

    schema_version = int(payload.get("schema_version", 1))
    if schema_version == 1:
        motions = payload.get("motions") or []
        if not isinstance(motions, list):
            raise ValueError("motion_edit schema v1 manifest field 'motions' must be a list")
        for motion in motions:
            if not isinstance(motion, dict):
                continue
            raw_motion_path = motion.get("motion_file") or motion.get("motion_path")
            motion_id = str(motion.get("motion_id") or "")
            if not raw_motion_path:
                continue
            resolved_motion_path = _resolve_motion_path(str(raw_motion_path), manifest_path=path, motion_root=motion_root)
            for segment in motion.get("segments") or []:
                if not isinstance(segment, dict):
                    continue
                yield {
                    "track": "proto",
                    "clip_npz": str(resolved_motion_path),
                    "motion_path": str(resolved_motion_path),
                    "motion_id": motion_id,
                    "segment_id": str(segment.get("segment_id") or ""),
                    "start_frame": int(segment["start_frame"]),
                    "end_frame": int(segment["end_frame"]),
                    "metadata": {
                        "source_manifest": str(path),
                        "manifest_schema_version": schema_version,
                        "source": segment.get("source"),
                        "status": segment.get("status"),
                        "active_body": segment.get("active_body") or segment.get("active"),
                        "support_bodies": segment.get("support_bodies"),
                        "transition_type": segment.get("transition_type"),
                    },
                }
        return

    if schema_version == 2:
        raw_motion_path = payload.get("motion_path")
        if not raw_motion_path:
            raise ValueError("motion_edit schema v2 manifest requires motion_path")
        resolved_motion_path = _resolve_motion_path(str(raw_motion_path), manifest_path=path, motion_root=motion_root)
        motion_id = str(payload.get("motion_version_id") or "")
        for segment in payload.get("segments") or []:
            if not isinstance(segment, dict):
                continue
            yield {
                "track": "proto",
                "clip_npz": str(resolved_motion_path),
                "motion_path": str(resolved_motion_path),
                "motion_id": motion_id,
                "segment_id": str(segment.get("segment_id") or ""),
                "start_frame": int(segment["start_frame"]),
                "end_frame": int(segment["end_frame"]),
                "metadata": {
                    "source_manifest": str(path),
                    "manifest_schema_version": schema_version,
                    "source": segment.get("source"),
                    "status": segment.get("status"),
                    "active_body": segment.get("active_body"),
                    "support_bodies": segment.get("support_bodies"),
                    "transition_type": segment.get("transition_type"),
                },
            }
        return

    raise ValueError(f"unsupported motion_edit manifest schema_version={schema_version}")


def _flatten_feature(array: np.ndarray) -> np.ndarray:
    array = np.asarray(array)
    if array.ndim < 2:
        raise ValueError(f"feature slice must have at least 2 dims [T, ...], got {array.shape}")
    return array.reshape(array.shape[0], -1)


def _feature_slice(data: np.lib.npyio.NpzFile, keys: list[str], start: int, end: int) -> np.ndarray:
    parts: list[np.ndarray] = []
    for key in keys:
        if key not in data.files:
            raise KeyError(f"missing feature key {key!r}")
        part = _flatten_feature(np.asarray(data[key][start:end]))
        parts.append(part.astype(np.float32, copy=False))
    if not parts:
        raise ValueError("at least one feature key is required")
    frames = {part.shape[0] for part in parts}
    if len(frames) != 1:
        raise ValueError(f"feature keys have inconsistent frame counts: {sorted(frames)}")
    return np.concatenate(parts, axis=1) if len(parts) > 1 else parts[0]


def _prepare_record(
    record: dict,
    *,
    feature_keys: list[str],
    target_len: int,
    min_len: int,
    max_len: int,
    pad_value: float,
) -> PreparedSegment | None:
    if str(record.get("track") or "proto") != "proto":
        return None
    source = record.get("clip_npz") or record.get("motion_path")
    if not source:
        return None
    start = int(record["start_frame"])
    end = int(record["end_frame"])
    length = end - start
    if length < min_len or length > max_len:
        return None
    if length > target_len:
        return None

    path = Path(str(source)).expanduser()
    if not path.exists():
        raise FileNotFoundError(path)

    with np.load(path, allow_pickle=True) as data:
        feature = _feature_slice(data, feature_keys, start, end)
    if feature.shape[0] != length:
        raise ValueError(
            f"{record.get('segment_id', '<unknown>')}: expected {length} frames, got {feature.shape[0]}"
        )
    if not np.isfinite(feature).all():
        raise ValueError(f"{record.get('segment_id', '<unknown>')}: feature contains non-finite values")

    segment = np.full((target_len, feature.shape[1]), pad_value, dtype=np.float32)
    valid_mask = np.zeros((target_len,), dtype=np.bool_)
    segment[:length] = feature
    valid_mask[:length] = True
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}

    return PreparedSegment(
        segment=segment,
        valid_mask=valid_mask,
        length=length,
        segment_id=str(record.get("segment_id") or ""),
        motion_id=str(record.get("motion_id") or ""),
        source_path=str(path),
        start_frame=start,
        end_frame=end,
        active_body=str(metadata.get("active_body") or ""),
    )


def prepare_segments(
    jsonl_path: str | Path,
    *,
    feature_keys: list[str],
    target_len: int = 32,
    min_len: int = 4,
    max_len: int = 32,
    pad_value: float = 0.0,
) -> tuple[list[PreparedSegment], dict[str, int]]:
    if target_len <= 0:
        raise ValueError("--target-len must be positive")
    if min_len <= 0:
        raise ValueError("--min-len must be positive")
    if max_len < min_len:
        raise ValueError("--max-len must be >= --min-len")
    if max_len > target_len:
        raise ValueError("--max-len must be <= --target-len when using padding")

    stats = {
        "records": 0,
        "kept": 0,
        "dropped_non_proto": 0,
        "dropped_missing_source": 0,
        "dropped_short": 0,
        "dropped_long": 0,
    }
    prepared: list[PreparedSegment] = []
    for record in _iter_records(_iter_jsonl_paths(Path(jsonl_path))):
        stats["records"] += 1
        if str(record.get("track") or "proto") != "proto":
            stats["dropped_non_proto"] += 1
            continue
        if not (record.get("clip_npz") or record.get("motion_path")):
            stats["dropped_missing_source"] += 1
            continue
        length = int(record["end_frame"]) - int(record["start_frame"])
        if length < min_len:
            stats["dropped_short"] += 1
            continue
        if length > max_len:
            stats["dropped_long"] += 1
            continue
        item = _prepare_record(
            record,
            feature_keys=feature_keys,
            target_len=target_len,
            min_len=min_len,
            max_len=max_len,
            pad_value=pad_value,
        )
        if item is not None:
            prepared.append(item)
            stats["kept"] += 1
    return prepared, stats


def prepare_cut_summary_segments(
    cut_summary: str | Path,
    *,
    feature_keys: list[str],
    target_len: int = 192,
    min_len: int = 16,
    max_len: int = 192,
    pad_value: float = 0.0,
) -> tuple[list[PreparedSegment], dict[str, int]]:
    if target_len <= 0:
        raise ValueError("--target-len must be positive")
    if min_len <= 0:
        raise ValueError("--min-len must be positive")
    if max_len < min_len:
        raise ValueError("--max-len must be >= --min-len")
    if max_len > target_len:
        raise ValueError("--max-len must be <= --target-len when using padding")

    stats = {
        "records": 0,
        "kept": 0,
        "dropped_non_proto": 0,
        "dropped_missing_source": 0,
        "dropped_short": 0,
        "dropped_long": 0,
    }
    prepared: list[PreparedSegment] = []
    for record in _iter_cut_summary_records(Path(cut_summary)):
        stats["records"] += 1
        length = int(record["end_frame"]) - int(record["start_frame"])
        if length < min_len:
            stats["dropped_short"] += 1
            continue
        if length > max_len:
            stats["dropped_long"] += 1
            continue
        item = _prepare_record(
            record,
            feature_keys=feature_keys,
            target_len=target_len,
            min_len=min_len,
            max_len=max_len,
            pad_value=pad_value,
        )
        if item is not None:
            prepared.append(item)
            stats["kept"] += 1
    return prepared, stats


def prepare_motion_edit_manifest_segments(
    manifest: str | Path,
    *,
    feature_keys: list[str],
    target_len: int = 192,
    min_len: int = 16,
    max_len: int = 192,
    pad_value: float = 0.0,
    motion_root: str | Path | None = None,
) -> tuple[list[PreparedSegment], dict[str, int]]:
    if target_len <= 0:
        raise ValueError("--target-len must be positive")
    if min_len <= 0:
        raise ValueError("--min-len must be positive")
    if max_len < min_len:
        raise ValueError("--max-len must be >= --min-len")
    if max_len > target_len:
        raise ValueError("--max-len must be <= --target-len when using padding")

    stats = {
        "records": 0,
        "kept": 0,
        "dropped_non_proto": 0,
        "dropped_missing_source": 0,
        "dropped_short": 0,
        "dropped_long": 0,
    }
    prepared: list[PreparedSegment] = []
    root = Path(motion_root).expanduser().resolve() if motion_root is not None else None
    for record in _iter_motion_edit_manifest_records(Path(manifest), motion_root=root):
        stats["records"] += 1
        if not (record.get("clip_npz") or record.get("motion_path")):
            stats["dropped_missing_source"] += 1
            continue
        length = int(record["end_frame"]) - int(record["start_frame"])
        if length < min_len:
            stats["dropped_short"] += 1
            continue
        if length > max_len:
            stats["dropped_long"] += 1
            continue
        item = _prepare_record(
            record,
            feature_keys=feature_keys,
            target_len=target_len,
            min_len=min_len,
            max_len=max_len,
            pad_value=pad_value,
        )
        if item is not None:
            prepared.append(item)
            stats["kept"] += 1
    return prepared, stats


def write_npz(path: str | Path, prepared: list[PreparedSegment], *, feature_keys: list[str], stats: dict[str, int]) -> Path:
    if not prepared:
        raise ValueError("no segments matched the requested filters")
    out = Path(path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    segments = np.stack([item.segment for item in prepared], axis=0).astype(np.float32, copy=False)
    valid_mask = np.stack([item.valid_mask for item in prepared], axis=0)
    lengths = np.asarray([item.length for item in prepared], dtype=np.int64)
    np.savez(
        out,
        segments=segments,
        valid_mask=valid_mask,
        lengths=lengths,
        feature_keys=np.asarray(feature_keys),
        segment_ids=np.asarray([item.segment_id for item in prepared]),
        motion_ids=np.asarray([item.motion_id for item in prepared]),
        source_paths=np.asarray([item.source_path for item in prepared]),
        start_frames=np.asarray([item.start_frame for item in prepared], dtype=np.int64),
        end_frames=np.asarray([item.end_frame for item in prepared], dtype=np.int64),
        active_bodies=np.asarray([item.active_body for item in prepared]),
        stats_json=np.asarray(json.dumps(stats, sort_keys=True)),
    )
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare motion_edit proto segments for GMVQ training.")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--segments", type=str, help="A .segments.jsonl file or directory of JSONL files.")
    source.add_argument("--cut-summary", type=str, help="motion_edit raw_contact_29_cut_summary.json path.")
    source.add_argument("--motion-edit-manifest", type=str, help="motion_edit export-manifest JSON path.")
    p.add_argument("--output", type=str, required=True, help="Output .npz path.")
    p.add_argument(
        "--feature-key",
        action="append",
        default=None,
        help="Motion npz array to flatten and concatenate. May be repeated. Default: joint_pos.",
    )
    p.add_argument("--target-len", type=int, default=32)
    p.add_argument("--min-len", type=int, default=4)
    p.add_argument("--max-len", type=int, default=32)
    p.add_argument("--pad-value", type=float, default=0.0)
    p.add_argument("--motion-root", type=str, default=None, help="Root used to resolve relative motion paths from a motion_edit manifest.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    feature_keys = args.feature_key or ["joint_pos"]
    if args.motion_edit_manifest:
        prepared, stats = prepare_motion_edit_manifest_segments(
            args.motion_edit_manifest,
            feature_keys=feature_keys,
            target_len=args.target_len,
            min_len=args.min_len,
            max_len=args.max_len,
            pad_value=args.pad_value,
            motion_root=args.motion_root,
        )
    elif args.cut_summary:
        prepared, stats = prepare_cut_summary_segments(
            args.cut_summary,
            feature_keys=feature_keys,
            target_len=args.target_len,
            min_len=args.min_len,
            max_len=args.max_len,
            pad_value=args.pad_value,
        )
    else:
        prepared, stats = prepare_segments(
            args.segments,
            feature_keys=feature_keys,
            target_len=args.target_len,
            min_len=args.min_len,
            max_len=args.max_len,
            pad_value=args.pad_value,
        )
    out = write_npz(args.output, prepared, feature_keys=feature_keys, stats=stats)
    shape = prepared[0].segment.shape
    print(
        f"wrote {out} segments={len(prepared)} shape=[{len(prepared)}, {shape[0]}, {shape[1]}] "
        f"features={','.join(feature_keys)} stats={json.dumps(stats, sort_keys=True)}"
    )


if __name__ == "__main__":
    main()
