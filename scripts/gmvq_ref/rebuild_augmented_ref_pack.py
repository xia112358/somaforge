#!/usr/bin/env python3
"""Rebuild augmented policy_ref_v1 files and the matching GMVQ segment pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gmvq_ref.build_segment_pack_from_metadata import (  # noqa: E402
    FEATURE_KEYS,
    _flatten_frame,
    _relative_feature,
    _schema_json,
    _schema_keys_from_ref,
)
from scripts.gmvq_ref.canonicalize_policy_ref import canonicalize  # noqa: E402


def _load_npz(path: Path, *, allow_pickle: bool = False) -> dict[str, np.ndarray]:
    with np.load(path.expanduser(), allow_pickle=allow_pickle) as data:
        return {key: np.asarray(data[key]) for key in data.files}


def _output_ref_path(raw_path: Path, output_dir: Path) -> Path:
    return output_dir / f"{raw_path.stem}.policy_ref_v1.npz"


def _canonicalize_directory(raw_dir: Path, output_dir: Path, *, limit: int | None = None) -> list[Path]:
    raw_paths = sorted(raw_dir.expanduser().glob("*.npz"))
    if limit is not None:
        raw_paths = raw_paths[:limit]
    if not raw_paths:
        raise FileNotFoundError(f"no .npz files found under {raw_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []
    for index, raw_path in enumerate(raw_paths, start=1):
        out_path = _output_ref_path(raw_path, output_dir)
        report = canonicalize(raw_path, out_path)
        if int(report["joint_vel_dim"]) != 35:
            raise ValueError(f"{out_path} has unexpected joint_vel_dim={report['joint_vel_dim']}")
        out_paths.append(out_path)
        if index == 1 or index % 100 == 0 or index == len(raw_paths):
            print(f"canonicalized {index}/{len(raw_paths)}: {out_path.name}", flush=True)
    return out_paths


def _fixed_ref_lookup(output_dir: Path) -> dict[str, Path]:
    return {path.name: path for path in sorted(output_dir.glob("*.policy_ref_v1.npz"))}


def _metadata_array(template: dict[str, np.ndarray], key: str, rows: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    if key in template:
        return np.asarray(template[key][rows])
    return fallback


def _build_pack_from_template(
    template_pack: Path,
    fixed_ref_dir: Path,
    output_pack: Path,
    *,
    limit_sources: int | None = None,
) -> dict[str, Any]:
    template = _load_npz(template_pack, allow_pickle=True)
    fixed_refs = _fixed_ref_lookup(fixed_ref_dir)
    if not fixed_refs:
        raise FileNotFoundError(f"no fixed policy_ref_v1 files found under {fixed_ref_dir}")

    source_paths_all = np.asarray(template["source_paths"]).astype(str)
    unique_source_paths = [path for path in sorted(set(source_paths_all.tolist())) if Path(path).name in fixed_refs]
    if limit_sources is not None:
        unique_source_paths = unique_source_paths[:limit_sources]
    if not unique_source_paths:
        raise ValueError("no template source rows match the fixed refs")
    selected_source_set = set(unique_source_paths)
    selected_rows = np.flatnonzero(np.asarray([path in selected_source_set for path in source_paths_all], dtype=np.bool_))
    source_paths = source_paths_all[selected_rows]

    first_ref = _load_npz(next(iter(fixed_refs.values())))
    schema_keys = _schema_keys_from_ref(first_ref, FEATURE_KEYS)
    feature_dim = int(schema_keys[-1]["end"])
    target_len = int(template["segments"].shape[1])
    row_count = int(source_paths.shape[0])

    segments = np.zeros((row_count, target_len, feature_dim), dtype=np.float32)
    valid_mask = np.zeros((row_count, target_len), dtype=np.bool_)
    lengths = np.asarray(template["lengths"][selected_rows], dtype=np.int64).copy()
    start_frames = np.asarray(template["start_frames"][selected_rows], dtype=np.int64).copy()
    end_frames = np.asarray(template["end_frames"][selected_rows], dtype=np.int64).copy()
    anchor_root_pos = np.zeros((row_count, 3), dtype=np.float32)
    output_source_paths = [""] * row_count

    for source_i, source_path in enumerate(unique_source_paths, start=1):
        source_name = Path(source_path).name
        fixed_ref_path = fixed_refs.get(source_name)
        if fixed_ref_path is None:
            raise FileNotFoundError(f"fixed ref for {source_name} not found under {fixed_ref_dir}")
        ref = _load_npz(fixed_ref_path)
        ref_schema = _schema_keys_from_ref(ref, FEATURE_KEYS)
        if ref_schema != schema_keys:
            raise ValueError(f"{fixed_ref_path} schema differs from first ref")
        rows = np.flatnonzero(source_paths == source_path)
        for row in rows:
            start = int(start_frames[row])
            length = min(int(lengths[row]), target_len, int(ref["joint_pos"].shape[0]) - start)
            if length <= 0:
                lengths[row] = 0
                end_frames[row] = start
                continue
            end = start + length
            anchor = np.asarray(ref["joint_pos"][start, :3], dtype=np.float32)
            feature = _flatten_frame(ref, schema_keys, start, end)
            feature = _relative_feature(feature, anchor=anchor, schema_keys=schema_keys)
            segments[row, :length] = feature
            valid_mask[row, :length] = True
            lengths[row] = length
            end_frames[row] = end
            anchor_root_pos[row] = anchor
            output_source_paths[int(row)] = str(fixed_ref_path)
        if source_i == 1 or source_i % 100 == 0 or source_i == len(unique_source_paths):
            print(f"packed {source_i}/{len(unique_source_paths)} refs", flush=True)

    stats = {
        "schema": "augmented_policy_ref_segment_pack_v2",
        "template_pack": str(template_pack.expanduser()),
        "fixed_ref_dir": str(fixed_ref_dir.expanduser()),
        "output_pack": str(output_pack.expanduser()),
        "row_count": row_count,
        "source_count": len(unique_source_paths),
        "target_len": target_len,
        "feature_dim": feature_dim,
        "length_min": int(lengths.min()),
        "length_max": int(lengths.max()),
        "feature_schema_keys": [(item["key"], item["shape"]) for item in schema_keys],
    }

    output_pack.parent.mkdir(parents=True, exist_ok=True)
    rows = np.arange(row_count)
    np.savez(
        output_pack,
        segments=segments,
        valid_mask=valid_mask,
        lengths=lengths,
        segment_ids=np.asarray(template["segment_ids"][selected_rows]),
        motion_ids=np.asarray(template["motion_ids"][selected_rows]),
        source_paths=np.asarray(output_source_paths, dtype=np.str_),
        raw_clip_paths=np.asarray(template["raw_clip_paths"][selected_rows]) if "raw_clip_paths" in template else np.asarray([]),
        start_frames=start_frames,
        end_frames=end_frames,
        event_start_frames=np.asarray(template["event_start_frames"][selected_rows]) if "event_start_frames" in template else start_frames,
        event_end_frames=np.asarray(template["event_end_frames"][selected_rows]) if "event_end_frames" in template else end_frames,
        anchor_root_pos=anchor_root_pos,
        active_bodies=np.asarray(template["active_bodies"][selected_rows]) if "active_bodies" in template else np.asarray([]),
        window_indices=np.asarray(template["window_indices"][selected_rows]) if "window_indices" in template else rows,
        feature_schema_json=np.asarray(_schema_json(schema_keys)),
        body_names=np.asarray(first_ref["body_names"]),
        joint_names=np.asarray(first_ref["joint_names"]),
        fps=np.asarray(first_ref["fps"]),
        stats_json=np.asarray(json.dumps(stats, sort_keys=True)),
    )
    summary_path = output_pack.with_suffix(output_pack.suffix + ".summary.json")
    summary_path.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2, sort_keys=True))
    return stats


def parse_args() -> argparse.Namespace:
    base = Path("/home/xiaz/holosoma_isaaclab3_newton/tmp/gmvq_play")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=base / "clean_source_aug_full/generated_raw29_large_mixed_n64_clean32",
    )
    parser.add_argument(
        "--template-pack",
        type=Path,
        default=base / "motion_edit_aug_full_ref_relative_t192_raw29_large_mixed_n64_full.npz",
    )
    parser.add_argument(
        "--fixed-ref-dir",
        type=Path,
        default=base / "policy_ref_v1_clean_source/raw29_large_mixed_n64_clean32",
    )
    parser.add_argument(
        "--output-pack",
        type=Path,
        default=base / "motion_edit_aug_full_ref_relative_t192_raw29_large_mixed_n64_clean32.npz",
    )
    parser.add_argument("--limit", type=int, default=None, help="Only rebuild the first N raw files for smoke tests.")
    parser.add_argument("--skip-canonicalize", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.skip_canonicalize:
        _canonicalize_directory(args.raw_dir.expanduser(), args.fixed_ref_dir.expanduser(), limit=args.limit)
    _build_pack_from_template(
        args.template_pack.expanduser(),
        args.fixed_ref_dir.expanduser(),
        args.output_pack.expanduser(),
        limit_sources=args.limit,
    )


if __name__ == "__main__":
    main()
