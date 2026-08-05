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

STALE_CONTACT_PREFIXES = (
    "contact_force",
    "raw_contact",
)


def _load_npz(path: Path, *, allow_pickle: bool = False) -> dict[str, np.ndarray]:
    with np.load(path.expanduser(), allow_pickle=allow_pickle) as data:
        return {key: np.asarray(data[key]) for key in data.files}


def _copy_ref_arrays(source: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    copied: dict[str, np.ndarray] = {}
    for key, value in source.items():
        copied[key] = np.array(value)
    return copied


def _strip_stale_contact_arrays(source: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], list[str]]:
    """Drop contact observations that no longer match a decoded q trajectory."""
    removed = sorted(
        key
        for key in source
        if any(key.startswith(prefix) for prefix in STALE_CONTACT_PREFIXES)
    )
    return {key: value for key, value in source.items() if key not in removed}, removed


def _normalize_quaternions(array: np.ndarray, *, context: str) -> tuple[np.ndarray, float]:
    value = np.asarray(array)
    norms = np.linalg.norm(value, axis=-1, keepdims=True)
    if not np.isfinite(norms).all() or float(norms.min()) < 1.0e-8:
        raise ValueError(f"{context} contains a non-finite or zero-length quaternion")
    normalized = value / norms
    correction = float(np.max(np.abs(norms - 1.0)))
    return normalized.astype(value.dtype, copy=False), correction


def _quat_conjugate_wxyz(quaternion: np.ndarray) -> np.ndarray:
    out = np.asarray(quaternion).copy()
    out[..., 1:] *= -1.0
    return out


def _quat_multiply_wxyz(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    lw, lx, ly, lz = np.moveaxis(np.asarray(left), -1, 0)
    rw, rx, ry, rz = np.moveaxis(np.asarray(right), -1, 0)
    return np.stack(
        (
            lw * rw - lx * rx - ly * ry - lz * rz,
            lw * rx + lx * rw + ly * rz - lz * ry,
            lw * ry - lx * rz + ly * rw + lz * rx,
            lw * rz + lx * ry - ly * rx + lz * rw,
        ),
        axis=-1,
    )


def _quat_rotate_wxyz(quaternion: np.ndarray, vector: np.ndarray) -> np.ndarray:
    q = np.asarray(quaternion)
    v = np.asarray(vector)
    xyz = q[..., 1:]
    uv = np.cross(xyz, v)
    uuv = np.cross(xyz, uv)
    return v + 2.0 * (q[..., :1] * uv + uuv)


def _continuous_quaternions(quaternion: np.ndarray, *, context: str) -> np.ndarray:
    out, _ = _normalize_quaternions(quaternion, context=context)
    out = out.copy()
    for frame in range(1, out.shape[0]):
        flip = np.sum(out[frame - 1] * out[frame], axis=-1) < 0.0
        out[frame] = np.where(flip[..., None], -out[frame], out[frame])
    return out


def _compose_quaternion_trajectory(base: np.ndarray, decoded: np.ndarray, *, context: str) -> np.ndarray:
    local = _continuous_quaternions(decoded, context=context)
    first_inv = _quat_conjugate_wxyz(local[0])
    alignment = _quat_multiply_wxyz(base, first_inv)
    composed = _quat_multiply_wxyz(alignment[None, ...], local)
    return _continuous_quaternions(composed, context=f"{context} composed")


def _chain_pose_segment(
    split: dict[str, np.ndarray],
    *,
    base_joint_pose: np.ndarray,
    base_body_pos: np.ndarray | None,
    base_body_quat: np.ndarray | None,
    rotate_root_translation: bool = True,
    rebase_articulated_joints: bool = True,
) -> None:
    joint = split.get("joint_pos")
    if joint is None:
        raise ValueError("chain-relative decoding requires joint_pos")
    joint = np.asarray(joint).copy()
    if joint.ndim != 2 or joint.shape[1] < 7:
        raise ValueError(f"joint_pos must have shape [T,7+J], got {joint.shape}")
    base_joint = np.asarray(base_joint_pose)
    if base_joint.shape != joint.shape[1:]:
        raise ValueError(f"base joint pose has shape {base_joint.shape}, expected {joint.shape[1:]}")

    decoded_root_quat = _continuous_quaternions(joint[:, 3:7], context="decoded segment root")
    base_root_quat, _ = _normalize_quaternions(base_joint[3:7], context="chain base root")
    root_alignment = _quat_multiply_wxyz(base_root_quat, _quat_conjugate_wxyz(decoded_root_quat[0]))
    root_delta = joint[:, :3] - joint[0, :3]
    if rotate_root_translation:
        root_delta = _quat_rotate_wxyz(root_alignment, root_delta)
    joint[:, :3] = base_joint[:3] + root_delta
    joint[:, 3:7] = _quat_multiply_wxyz(root_alignment, decoded_root_quat)
    if joint.shape[1] > 7 and rebase_articulated_joints:
        unwrapped = np.unwrap(joint[:, 7:], axis=0)
        joint[:, 7:] = base_joint[7:] + (unwrapped - unwrapped[0])
    split["joint_pos"] = joint

    body_pos = split.get("body_pos_w")
    if body_pos is not None and base_body_pos is not None:
        body_pos = np.asarray(body_pos).copy()
        base_pos = np.asarray(base_body_pos)
        if base_pos.shape != body_pos.shape[1:]:
            raise ValueError(f"base body positions have shape {base_pos.shape}, expected {body_pos.shape[1:]}")
        split["body_pos_w"] = base_pos[None, ...] + (body_pos - body_pos[0:1])

    body_quat = split.get("body_quat_w")
    if body_quat is not None and base_body_quat is not None:
        base_quat = np.asarray(base_body_quat)
        if base_quat.shape != np.asarray(body_quat).shape[1:]:
            raise ValueError(f"base body quaternions have shape {base_quat.shape}, expected {np.asarray(body_quat).shape[1:]}")
        split["body_quat_w"] = _compose_quaternion_trajectory(
            base_quat,
            np.asarray(body_quat),
            context="decoded segment bodies",
        )


def _finite_difference(values: np.ndarray, fps: float) -> np.ndarray:
    value = np.asarray(values)
    if value.shape[0] <= 1:
        return np.zeros_like(value)
    return np.gradient(value, 1.0 / fps, axis=0)


def _angular_velocity_wxyz(quaternion: np.ndarray, fps: float) -> np.ndarray:
    q = _continuous_quaternions(quaternion, context="velocity quaternion")
    if q.shape[0] <= 1:
        return np.zeros(q.shape[:-1] + (3,), dtype=q.dtype)
    delta = _quat_multiply_wxyz(q[1:], _quat_conjugate_wxyz(q[:-1]))
    delta = _continuous_quaternions(delta, context="velocity quaternion delta")
    xyz = delta[..., 1:]
    sin_half = np.linalg.norm(xyz, axis=-1)
    angle = 2.0 * np.arctan2(sin_half, np.clip(delta[..., 0], -1.0, 1.0))
    scale = np.zeros_like(angle)
    valid = sin_half > 1.0e-8
    scale[valid] = angle[valid] / sin_half[valid]
    interval = xyz * scale[..., None] * float(fps)
    velocity = np.empty(q.shape[:-1] + (3,), dtype=q.dtype)
    velocity[0] = interval[0]
    velocity[-1] = interval[-1]
    if q.shape[0] > 2:
        velocity[1:-1] = 0.5 * (interval[:-1] + interval[1:])
    return velocity


def _recompute_velocities(out: dict[str, np.ndarray]) -> None:
    fps = float(np.asarray(out["fps"]).reshape(-1)[0])
    joint = np.asarray(out["joint_pos"])
    out["joint_vel"] = np.concatenate(
        (
            _finite_difference(joint[:, :3], fps),
            _angular_velocity_wxyz(joint[:, 3:7], fps),
            _finite_difference(joint[:, 7:], fps),
        ),
        axis=1,
    ).astype(np.asarray(out["joint_vel"]).dtype, copy=False)
    if "body_pos_w" in out and "body_lin_vel_w" in out:
        out["body_lin_vel_w"] = _finite_difference(out["body_pos_w"], fps).astype(
            np.asarray(out["body_lin_vel_w"]).dtype,
            copy=False,
        )
    if "body_quat_w" in out and "body_ang_vel_w" in out:
        out["body_ang_vel_w"] = _angular_velocity_wxyz(out["body_quat_w"], fps).astype(
            np.asarray(out["body_ang_vel_w"]).dtype,
            copy=False,
        )


def _feature_schema(
    segment_pack: Path,
    source_ref: dict[str, np.ndarray] | None = None,
) -> list[dict[str, Any]]:
    with np.load(segment_pack.expanduser(), allow_pickle=True) as data:
        if "feature_schema_json" in data.files:
            raw = str(np.asarray(data["feature_schema_json"]).item())
            schema = json.loads(raw)
            keys = schema.get("keys")
            if not isinstance(keys, list):
                raise ValueError(f"feature_schema_json has no keys list: {segment_pack}")
            return keys
        if "feature_keys" not in data.files:
            raise ValueError(f"segment pack has neither feature_schema_json nor feature_keys: {segment_pack}")
        feature_keys = [str(value) for value in np.asarray(data["feature_keys"]).reshape(-1)]
        feature_width = int(np.asarray(data["segments"]).shape[-1])

    if source_ref is None:
        raise ValueError(f"feature_keys-only segment pack requires a selected source ref: {segment_pack}")
    keys = []
    offset = 0
    for key in feature_keys:
        if key not in source_ref:
            raise KeyError(f"source ref is missing packed feature {key!r}")
        shape = tuple(int(value) for value in np.asarray(source_ref[key]).shape[1:])
        width = int(np.prod(shape, dtype=np.int64))
        keys.append({"key": key, "start": offset, "end": offset + width, "shape": list(shape)})
        offset += width
    if offset != feature_width:
        raise ValueError(
            f"source-derived feature width {offset} does not match packed width {feature_width}: {segment_pack}"
        )
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
    lengths: np.ndarray,
    *,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    codes: list[np.ndarray] = []
    thetas: list[np.ndarray] = []
    decoded: list[np.ndarray] = []
    for start in range(0, obs.shape[0], batch_size):
        xb = torch.from_numpy(obs[start : start + batch_size].astype(np.float32)).to(runtime.device_ref)
        length = torch.from_numpy(lengths[start : start + batch_size].astype(np.int64)).to(runtime.device_ref)
        out = runtime(xb, lengths=length)
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
    chain_relative_segments: bool = True,
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    out = _copy_ref_arrays(source_ref)
    accum: dict[str, np.ndarray] = {}
    counts: dict[str, np.ndarray] = {}
    for key in REF_FEATURE_KEYS:
        if key in out:
            accum[key] = np.zeros_like(out[key], dtype=np.float64)
            counts[key] = np.zeros(out[key].shape[:1] + (1,) * (out[key].ndim - 1), dtype=np.float64)

    written_frames = np.zeros(int(out["joint_pos"].shape[0]), dtype=np.bool_)
    previous_end = -1
    previous_joint_pose: np.ndarray | None = None
    previous_body_pos: np.ndarray | None = None
    previous_body_quat: np.ndarray | None = None

    def chain_source_gap(frame_start: int, frame_end: int) -> None:
        """Carry source motion increments through an undecoded interval."""
        nonlocal previous_joint_pose, previous_end
        if previous_joint_pose is None or frame_start >= frame_end:
            return
        source_chunk = np.asarray(source_ref["joint_pos"][frame_start - 1 : frame_end]).copy()
        split = {"joint_pos": source_chunk}
        _chain_pose_segment(
            split,
            base_joint_pose=previous_joint_pose,
            base_body_pos=None,
            base_body_quat=None,
        )
        carried = np.asarray(split["joint_pos"])[1:]
        accum["joint_pos"][frame_start:frame_end] = carried.astype(np.float64)
        counts["joint_pos"][frame_start:frame_end] = 1.0
        written_frames[frame_start:frame_end] = True
        previous_joint_pose = carried[-1].copy()
        previous_end = frame_end

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
        if chain_relative_segments:
            if frame_start < previous_end:
                raise ValueError("chain-relative decoded segments must not overlap")
            if previous_joint_pose is not None and frame_start > previous_end:
                chain_source_gap(previous_end, frame_start)
            contiguous = previous_joint_pose is not None and frame_start == previous_end
            base_joint = (
                previous_joint_pose
                if contiguous
                else np.asarray(source_ref["joint_pos"][frame_start])
            )
            base_body_pos = (
                previous_body_pos
                if contiguous
                else (
                    np.asarray(source_ref["body_pos_w"][frame_start])
                    if "body_pos_w" in source_ref
                    else None
                )
            )
            base_body_quat = (
                previous_body_quat
                if contiguous
                else (
                    np.asarray(source_ref["body_quat_w"][frame_start])
                    if "body_quat_w" in source_ref
                    else None
                )
            )
            _chain_pose_segment(
                split,
                base_joint_pose=base_joint,
                base_body_pos=base_body_pos,
                base_body_quat=base_body_quat,
            )
            previous_joint_pose = np.asarray(split["joint_pos"][-1]).copy()
            previous_body_pos = (
                np.asarray(split["body_pos_w"][-1]).copy()
                if "body_pos_w" in split
                else None
            )
            previous_body_quat = (
                np.asarray(split["body_quat_w"][-1]).copy()
                if "body_quat_w" in split
                else None
            )
            previous_end = frame_end
        else:
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

    if chain_relative_segments and previous_joint_pose is not None and previous_end < written_frames.shape[0]:
        chain_source_gap(previous_end, written_frames.shape[0])

    for key, value in accum.items():
        mask = counts[key] > 0
        if np.any(mask):
            decoded_value = value / np.maximum(counts[key], 1.0)
            out[key] = np.where(mask, decoded_value, out[key]).astype(source_ref[key].dtype, copy=False)

    if chain_relative_segments:
        _recompute_velocities(out)

    quaternion_correction: dict[str, float] = {}
    if "joint_pos" in out:
        out["joint_pos"] = out["joint_pos"].copy()
        root_quat, correction = _normalize_quaternions(
            out["joint_pos"][:, 3:7],
            context="decoded root pose",
        )
        out["joint_pos"][:, 3:7] = root_quat
        quaternion_correction["root_quaternion_norm_correction_max"] = correction
    if "body_quat_w" in out:
        out["body_quat_w"], correction = _normalize_quaternions(
            out["body_quat_w"],
            context="decoded body pose",
        )
        quaternion_correction["body_quaternion_norm_correction_max"] = correction

    if "policy_ref_schema" not in out:
        out["policy_ref_schema"] = np.asarray("policy_ref_v1")
    out["gmvq_selector_decode_report_json"] = np.asarray(
        json.dumps(
            {
                "schema": "gmvq_selector_decoded_ref_v1",
                "written_frame_count": int(written_frames.sum()),
                "total_frame_count": int(written_frames.shape[0]),
                "blend_overlaps": bool(blend_overlaps),
                "chain_relative_segments": bool(chain_relative_segments),
                **quaternion_correction,
            },
            sort_keys=True,
        )
    )
    return out, {
        "written_frame_count": int(written_frames.sum()),
        "total_frame_count": int(written_frames.shape[0]),
        "chain_relative_segments": bool(chain_relative_segments),
        **quaternion_correction,
    }


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
    source_ref = _load_npz(source_ref_path, allow_pickle=True)
    decode_robot_asset_json(source_ref.get("robot_asset_json"), context=f"selector source ref {source_ref_path}")
    schema_keys = _feature_schema(args.segment_pack, source_ref)
    codes, theta, decoded_segments = _decode_selected_rows(
        runtime,
        obs,
        lengths,
        batch_size=args.batch_size,
    )
    kinematic_source_ref, removed_contact_fields = _strip_stale_contact_arrays(source_ref)
    decoded_ref, write_stats = _write_decoded_segments(
        source_ref=kinematic_source_ref,
        decoded_segments=decoded_segments,
        schema_keys=schema_keys,
        start_frames=start_frames,
        end_frames=end_frames,
        lengths=lengths,
        anchor_root_pos=anchor_root_pos,
        blend_overlaps=not args.no_blend_overlaps,
        chain_relative_segments=True,
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
        "removed_stale_contact_fields": removed_contact_fields,
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
