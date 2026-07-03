#!/usr/bin/env python3
"""Build a GMVQ relative segment pack from existing segment metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


FEATURE_KEYS = (
    "joint_pos",
    "joint_vel",
    "body_pos_w",
    "body_quat_w",
    "body_lin_vel_w",
    "body_ang_vel_w",
)


def _load_npz(path: Path, *, allow_pickle: bool = False) -> dict[str, np.ndarray]:
    with np.load(path.expanduser(), allow_pickle=allow_pickle) as data:
        return {key: np.asarray(data[key]) for key in data.files}


def _schema_keys_from_ref(source_ref: dict[str, np.ndarray], feature_keys: tuple[str, ...] = FEATURE_KEYS) -> list[dict[str, Any]]:
    schema: list[dict[str, Any]] = []
    cursor = 0
    frame_count = int(np.asarray(source_ref["joint_pos"]).shape[0])
    for key in feature_keys:
        if key not in source_ref:
            raise KeyError(f"ref is missing feature key {key!r}")
        value = np.asarray(source_ref[key])
        if value.ndim < 2 or int(value.shape[0]) != frame_count:
            raise ValueError(f"{key} must have shape [T, ...] with T={frame_count}, got {value.shape}")
        flat_dim = int(np.prod(value.shape[1:]))
        schema.append(
            {
                "key": key,
                "shape": [int(v) for v in value.shape[1:]],
                "start": cursor,
                "end": cursor + flat_dim,
            }
        )
        cursor += flat_dim
    return schema


def _schema_json(schema_keys: list[dict[str, Any]]) -> str:
    return json.dumps({"keys": schema_keys}, sort_keys=True)


def _flatten_frame(data: dict[str, np.ndarray], schema_keys: list[dict[str, Any]], start: int, end: int) -> np.ndarray:
    parts: list[np.ndarray] = []
    for item in schema_keys:
        key = str(item["key"])
        value = np.asarray(data[key][start:end], dtype=np.float32)
        parts.append(value.reshape(value.shape[0], -1))
    return np.concatenate(parts, axis=1).astype(np.float32)


def _relative_feature(
    feature: np.ndarray,
    *,
    anchor: np.ndarray,
    schema_keys: list[dict[str, Any]],
) -> np.ndarray:
    out = feature.copy()
    for item in schema_keys:
        key = str(item["key"])
        start = int(item["start"])
        end = int(item["end"])
        shape = tuple(int(v) for v in item["shape"])
        view = out[:, start:end].reshape((out.shape[0],) + shape)
        if key == "joint_pos" and view.shape[1] >= 3:
            view[:, :3] -= anchor[None, :]
        elif key == "body_pos_w":
            view -= anchor[None, None, :]
    return out


def build_pack(args: argparse.Namespace) -> dict[str, Any]:
    source_ref = _load_npz(args.ref_npz)
    template = _load_npz(args.template_pack, allow_pickle=True)
    schema_keys = _schema_keys_from_ref(source_ref)

    source_paths = np.asarray(template["source_paths"]).astype(str)
    if args.source_contains:
        rows = np.flatnonzero(np.asarray([args.source_contains in value for value in source_paths], dtype=np.bool_))
    else:
        first = source_paths[0]
        rows = np.flatnonzero(source_paths == first)
    if rows.size == 0:
        raise ValueError(f"no rows selected by source_contains={args.source_contains!r}")

    target_len = int(template["segments"].shape[1])
    feature_dim = int(schema_keys[-1]["end"])
    segments = np.zeros((rows.size, target_len, feature_dim), dtype=np.float32)
    valid_mask = np.zeros((rows.size, target_len), dtype=np.bool_)
    lengths = np.asarray(template["lengths"][rows], dtype=np.int64).copy()
    start_frames = np.asarray(template["start_frames"][rows], dtype=np.int64).copy()
    end_frames = np.asarray(template["end_frames"][rows], dtype=np.int64).copy()
    anchor_root_pos = np.zeros((rows.size, 3), dtype=np.float32)

    for out_i, row in enumerate(rows):
        start = int(start_frames[out_i])
        length = min(int(lengths[out_i]), target_len, int(source_ref["joint_pos"].shape[0]) - start)
        end = start + length
        if length <= 0:
            continue
        anchor = np.asarray(source_ref["joint_pos"][start, :3], dtype=np.float32)
        feature = _flatten_frame(source_ref, schema_keys, start, end)
        feature = _relative_feature(feature, anchor=anchor, schema_keys=schema_keys)
        segments[out_i, :length] = feature
        valid_mask[out_i, :length] = True
        lengths[out_i] = length
        end_frames[out_i] = end
        anchor_root_pos[out_i] = anchor

    stats = {
        "schema": "gmvq_segment_pack_from_metadata_v1",
        "ref_npz": str(args.ref_npz.expanduser()),
        "template_pack": str(args.template_pack.expanduser()),
        "output": str(args.output.expanduser()),
        "row_count": int(rows.size),
        "target_len": target_len,
        "feature_dim": feature_dim,
        "feature_schema_keys": [(item["key"], item["shape"]) for item in schema_keys],
        "length_min": int(lengths.min()),
        "length_max": int(lengths.max()),
    }
    output = args.output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output,
        segments=segments,
        valid_mask=valid_mask,
        lengths=lengths,
        segment_ids=np.asarray(template["segment_ids"][rows]),
        motion_ids=np.asarray(template["motion_ids"][rows]),
        source_paths=np.asarray([str(args.ref_npz.expanduser())] * rows.size, dtype=np.str_),
        raw_clip_paths=np.asarray(template["raw_clip_paths"][rows]) if "raw_clip_paths" in template else np.asarray([]),
        start_frames=start_frames,
        end_frames=end_frames,
        event_start_frames=np.asarray(template["event_start_frames"][rows]) if "event_start_frames" in template else start_frames,
        event_end_frames=np.asarray(template["event_end_frames"][rows]) if "event_end_frames" in template else end_frames,
        anchor_root_pos=anchor_root_pos,
        active_bodies=np.asarray(template["active_bodies"][rows]) if "active_bodies" in template else np.asarray([]),
        window_indices=np.asarray(template["window_indices"][rows]) if "window_indices" in template else rows,
        feature_schema_json=np.asarray(_schema_json(schema_keys)),
        body_names=np.asarray(source_ref["body_names"]),
        joint_names=np.asarray(source_ref["joint_names"]),
        fps=np.asarray(source_ref["fps"]),
        stats_json=np.asarray(json.dumps(stats, sort_keys=True)),
    )
    print(json.dumps(stats, indent=2, sort_keys=True))
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref-npz", type=Path, required=True)
    parser.add_argument("--template-pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-contains", default="climb_00_z_scale_1.0_surface_jitter_0000")
    return parser.parse_args()


def main() -> None:
    build_pack(parse_args())


if __name__ == "__main__":
    main()
