#!/usr/bin/env python3
"""Decode selector-predicted GMVQ segments back into a policy_ref_v1 motion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch
from somaforge_core.robot_assets import decode_robot_asset_json, somaforge_root

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.gmvq_ref.selector_runtime import GMVQSelectorRuntime
from scripts.gmvq_ref.train_selector_code import _build_features as build_code_features


REF_FEATURE_KEYS = (
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


def _copy_ref_arrays(source: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    copied: dict[str, np.ndarray] = {}
    for key, value in source.items():
        copied[key] = np.array(value)
    return copied


def _feature_schema(segment_pack: Path) -> list[dict[str, Any]]:
    with np.load(segment_pack.expanduser(), allow_pickle=True) as data:
        raw = str(np.asarray(data["feature_schema_json"]).item())
    schema = json.loads(raw)
    keys = schema.get("keys")
    if not isinstance(keys, list):
        raise ValueError(f"feature_schema_json has no keys list: {segment_pack}")
    return keys


def _split_decoded(decoded: np.ndarray, schema_keys: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for item in schema_keys:
        key = str(item["key"])
        start = int(item["start"])
        end = int(item["end"])
        shape = tuple(int(v) for v in item["shape"])
        out[key] = decoded[:, start:end].reshape((decoded.shape[0],) + shape)
    return out


def _select_rows(
    *,
    source_paths: np.ndarray,
    source_path: str | None,
    source_contains: str | None,
) -> tuple[np.ndarray, str]:
    values = np.asarray(source_paths).astype(str)
    if source_path:
        selected = values == str(Path(source_path).expanduser())
        if not np.any(selected):
            selected = values == source_path
        label = source_path
    elif source_contains:
        selected = np.asarray([source_contains in value for value in values], dtype=np.bool_)
        label = source_contains
    else:
        label = str(values[0])
        selected = values == label
    rows = np.flatnonzero(selected)
    if rows.size == 0:
        raise ValueError(f"no selector rows matched {label!r}")
    unique_sources = sorted(set(values[rows].tolist()))
    if len(unique_sources) != 1:
        raise ValueError(f"selection must resolve to one source motion, got {len(unique_sources)} sources")
    return rows, unique_sources[0]


@torch.no_grad()
def _decode_selected_rows(
    runtime: GMVQSelectorRuntime,
    obs: np.ndarray,
    *,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    codes: list[np.ndarray] = []
    thetas: list[np.ndarray] = []
    decoded: list[np.ndarray] = []
    for start in range(0, obs.shape[0], batch_size):
        xb = torch.from_numpy(obs[start : start + batch_size].astype(np.float32)).to(runtime.device_ref)
        out = runtime(xb)
        codes.append(out.code.cpu().numpy())
        thetas.append(out.theta.cpu().numpy())
        x_hat = out.x_hat
        if runtime.gmvq_codec.norm_stats is not None:
            stats = runtime.gmvq_codec.norm_stats
            x_hat = x_hat * stats.std.to(x_hat.device) + stats.mean.to(x_hat.device)
        decoded.append(x_hat.cpu().numpy())
    return np.concatenate(codes), np.concatenate(thetas), np.concatenate(decoded, axis=0)


def _write_decoded_segments(
    *,
    source_ref: dict[str, np.ndarray],
    decoded_segments: np.ndarray,
    schema_keys: list[dict[str, Any]],
    start_frames: np.ndarray,
    end_frames: np.ndarray,
    lengths: np.ndarray,
    anchor_root_pos: np.ndarray,
    blend_overlaps: bool,
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    out = _copy_ref_arrays(source_ref)
    accum: dict[str, np.ndarray] = {}
    counts: dict[str, np.ndarray] = {}
    for key in REF_FEATURE_KEYS:
        if key in out:
            accum[key] = np.zeros_like(out[key], dtype=np.float64)
            counts[key] = np.zeros(out[key].shape[:1] + (1,) * (out[key].ndim - 1), dtype=np.float64)

    written_frames = np.zeros(int(out["joint_pos"].shape[0]), dtype=np.bool_)
    for row, decoded in enumerate(decoded_segments):
        length = min(int(lengths[row]), int(end_frames[row] - start_frames[row]), decoded.shape[0])
        if length <= 0:
            continue
        frame_start = int(start_frames[row])
        frame_end = min(frame_start + length, int(out["joint_pos"].shape[0]))
        local_len = frame_end - frame_start
        if local_len <= 0:
            continue

        split = _split_decoded(decoded[:local_len], schema_keys)
        anchor = anchor_root_pos[row].astype(np.float32)
        if "joint_pos" in split and split["joint_pos"].shape[1] >= 3:
            split["joint_pos"] = split["joint_pos"].copy()
            split["joint_pos"][:, :3] += anchor[None, :]
        if "body_pos_w" in split:
            split["body_pos_w"] = split["body_pos_w"] + anchor[None, None, :]

        for key, value in split.items():
            if key not in accum:
                continue
            if blend_overlaps:
                accum[key][frame_start:frame_end] += value.astype(np.float64)
                counts[key][frame_start:frame_end] += 1.0
            else:
                accum[key][frame_start:frame_end] = value.astype(np.float64)
                counts[key][frame_start:frame_end] = 1.0
        written_frames[frame_start:frame_end] = True

    for key, value in accum.items():
        mask = counts[key] > 0
        if np.any(mask):
            decoded_value = value / np.maximum(counts[key], 1.0)
            out[key] = np.where(mask, decoded_value, out[key]).astype(source_ref[key].dtype, copy=False)

    if "policy_ref_schema" not in out:
        out["policy_ref_schema"] = np.asarray("policy_ref_v1")
    out["gmvq_selector_decode_report_json"] = np.asarray(
        json.dumps(
            {
                "schema": "gmvq_selector_decoded_ref_v1",
                "written_frame_count": int(written_frames.sum()),
                "total_frame_count": int(written_frames.shape[0]),
                "blend_overlaps": bool(blend_overlaps),
            },
            sort_keys=True,
        )
    )
    return out, {"written_frame_count": int(written_frames.sum()), "total_frame_count": int(written_frames.shape[0])}


def _resolve_manifest_path(path_value: str, manifest_path: Path) -> str:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (manifest_path.parent / path).resolve()
    return str(path)


def _write_manifest(
    *,
    base_manifest: Path,
    output_manifest: Path,
    motion_file: Path,
    terrain_id: int | None,
) -> Path:
    base = json.loads(base_manifest.expanduser().read_text(encoding="utf-8"))
    terrains = []
    for terrain in base.get("terrains", []):
        item = dict(terrain)
        if terrain_id is not None and int(item.get("terrain_id", -1)) != int(terrain_id):
            continue
        if item.get("terrain_file"):
            item["terrain_file"] = _resolve_manifest_path(str(item["terrain_file"]), base_manifest)
        if item.get("source_urdf"):
            item["source_urdf"] = _resolve_manifest_path(str(item["source_urdf"]), base_manifest)
        terrains.append(item)
    if not terrains:
        raise ValueError(f"no terrain selected from {base_manifest}")
    if terrain_id is None:
        terrain_id = int(terrains[0].get("terrain_id", 0))

    manifest = {
        "schema_version": 1,
        "description": "Selector-decoded GMVQ policy_ref_v1 manifest.",
        "terrains": terrains,
        "motion_files": [
            {
                "motion_file": str(motion_file.expanduser().resolve()),
                "terrain_id": int(terrain_id),
                "weight": 1.0,
            }
        ],
    }
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_manifest


def decode_selector_ref(args: argparse.Namespace) -> dict[str, Any]:
    output_ref = args.output_ref.expanduser().resolve()
    output_ref.parent.mkdir(parents=True, exist_ok=True)

    runtime = GMVQSelectorRuntime(
        code_checkpoint=args.code_selector,
        theta_checkpoint=args.theta_selector,
        gmvq_checkpoint=args.gmvq_checkpoint,
        device=args.device,
    )
    schema_keys = _feature_schema(args.segment_pack)

    with np.load(args.selector_dataset.expanduser(), allow_pickle=False) as data:
        rows, selected_source = _select_rows(
            source_paths=data["source_paths"],
            source_path=args.source_path,
            source_contains=args.source_contains,
        )
        obs, obs_keys = build_code_features(data, ["height", "root", "joint"])
        obs = obs[rows]
        start_frames = np.asarray(data["start_frames"][rows], dtype=np.int64)
        end_frames = np.asarray(data["end_frames"][rows], dtype=np.int64)
        lengths = np.asarray(data["lengths"][rows], dtype=np.int64)
        anchor_root_pos = np.asarray(data["anchor_root_pos"][rows], dtype=np.float32)
        segment_ids = np.asarray(data["segment_ids"][rows]).astype(str)

    source_ref_path = Path(selected_source).expanduser()
    source_ref = _load_npz(source_ref_path, allow_pickle=False)
    decode_robot_asset_json(source_ref.get("robot_asset_json"), context=f"selector source ref {source_ref_path}")
    codes, theta, decoded_segments = _decode_selected_rows(runtime, obs, batch_size=args.batch_size)
    decoded_ref, write_stats = _write_decoded_segments(
        source_ref=source_ref,
        decoded_segments=decoded_segments,
        schema_keys=schema_keys,
        start_frames=start_frames,
        end_frames=end_frames,
        lengths=lengths,
        anchor_root_pos=anchor_root_pos,
        blend_overlaps=not args.no_blend_overlaps,
    )
    np.savez(output_ref, **decoded_ref)

    manifest_path = None
    if args.output_manifest:
        manifest_path = _write_manifest(
            base_manifest=args.base_manifest,
            output_manifest=args.output_manifest.expanduser().resolve(),
            motion_file=output_ref,
            terrain_id=args.terrain_id,
        )

    summary = {
        "schema": "gmvq_selector_decoded_ref_summary_v1",
        "source_ref": str(source_ref_path),
        "output_ref": str(output_ref),
        "output_manifest": None if manifest_path is None else str(manifest_path),
        "selector_dataset": str(args.selector_dataset.expanduser()),
        "segment_pack": str(args.segment_pack.expanduser()),
        "segment_count": int(rows.shape[0]),
        "segment_ids_first": segment_ids[:5].tolist(),
        "obs_keys": obs_keys,
        "code_hist": [int(v) for v in np.bincount(codes, minlength=runtime.num_codes).tolist()],
        "theta_shape": list(theta.shape),
        "decoded_segment_shape": list(decoded_segments.shape),
        **write_stats,
    }
    summary_path = output_ref.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def parse_args() -> argparse.Namespace:
    base = somaforge_root() / "tmp/gmvq_play"
    selector_base = base / "selector_dataset_v1/raw29_large_mixed_n64_codes16_height"
    gmvq_base = base / "gmvq_aug_full_ref_t192_raw29_large_mixed_n64_codes16_12k"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-dataset", type=Path, default=selector_base / "selector_height_code_theta_dataset.npz")
    parser.add_argument("--segment-pack", type=Path, default=base / "motion_edit_aug_full_ref_relative_t192_raw29_large_mixed_n64_full.npz")
    parser.add_argument("--gmvq-checkpoint", type=Path, default=gmvq_base / "checkpoint.pt")
    parser.add_argument("--code-selector", type=Path, default=selector_base / "code_selector_mlp_hrootjoint_80e/checkpoint.pt")
    parser.add_argument("--theta-selector", type=Path, default=selector_base / "theta_selector_mlp_hrootjoint_code_100e/checkpoint.pt")
    parser.add_argument("--source-path", default=None, help="Exact policy_ref_v1 source path to decode.")
    parser.add_argument(
        "--source-contains",
        default="climb_00_z_scale_1.0_surface_jitter_0000",
        help="Substring used to choose one source motion when --source-path is omitted.",
    )
    parser.add_argument("--output-ref", type=Path, default=base / "selector_decoded_refs/climb00_surface_jitter_0000_selector.policy_ref_v1.npz")
    parser.add_argument("--output-manifest", type=Path, default=base / "selector_decoded_refs/climb00_surface_jitter_0000_selector_manifest.json")
    parser.add_argument("--base-manifest", type=Path, default=REPO_ROOT / "runtime/current/manifests/climb00_motion_edit_ref.json")
    parser.add_argument("--terrain-id", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--no-blend-overlaps", action="store_true")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def main() -> None:
    decode_selector_ref(parse_args())


if __name__ == "__main__":
    main()
