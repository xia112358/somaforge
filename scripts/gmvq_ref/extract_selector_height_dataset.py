#!/usr/bin/env python3
"""Extract offline height-scan selector samples for GMVQ segment selection."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from somaforge_core.robot_assets import decode_robot_asset_json, encode_robot_asset_json


@dataclass(frozen=True)
class Surface:
    surface_id: str
    origin: np.ndarray
    normal: np.ndarray
    tangent_u: np.ndarray
    tangent_v: np.ndarray
    bounds_u: tuple[float, float] | None
    bounds_v: tuple[float, float] | None
    polygon_uv: np.ndarray | None


def _load_surfaces(path: Path) -> list[Surface]:
    surfaces: list[Surface] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        normal = np.asarray(record["normal"], dtype=np.float64)
        if abs(float(normal[2])) < 1.0e-6:
            continue
        bounds = record.get("bounds") or {}
        metadata = record.get("metadata") or {}
        polygon = metadata.get("polygon_surface_coordinates")
        polygon_uv = None
        if polygon:
            polygon_uv = np.asarray([[p["u"], p["v"]] for p in polygon], dtype=np.float64)
        surfaces.append(
            Surface(
                surface_id=str(record.get("surface_id", "")),
                origin=np.asarray(record["origin"], dtype=np.float64),
                normal=normal,
                tangent_u=np.asarray(record["tangent_u"], dtype=np.float64),
                tangent_v=np.asarray(record["tangent_v"], dtype=np.float64),
                bounds_u=tuple(float(x) for x in bounds["u"]) if "u" in bounds else None,
                bounds_v=tuple(float(x) for x in bounds["v"]) if "v" in bounds else None,
                polygon_uv=polygon_uv,
            )
        )
    if not surfaces:
        raise ValueError(f"no usable horizontal-ish surfaces found in {path}")
    return surfaces


def _motion_surface_key(path: str) -> str:
    stem = Path(path).name
    for suffix in (".policy_ref_v1.npz", ".npz"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    marker = "_surface_jitter_"
    if marker in stem:
        stem = stem.split(marker, 1)[0]
    return stem


def _load_surface_map(
    *,
    source_paths: np.ndarray,
    surface_jsonl: Path | None,
    surface_dir: Path | None,
) -> tuple[dict[str, list[Surface]], list[str]]:
    source_strings = np.asarray(source_paths).astype(str).tolist()
    keys = sorted({_motion_surface_key(path) for path in source_strings})
    surfaces_by_key: dict[str, list[Surface]] = {}
    loaded_ids: list[str] = []
    if surface_dir is not None:
        for key in keys:
            path = surface_dir.expanduser() / f"{key}_top_ground_surfaces.jsonl"
            surfaces_by_key[key] = _load_surfaces(path)
            loaded_ids.extend([s.surface_id for s in surfaces_by_key[key]])
        return surfaces_by_key, loaded_ids
    if surface_jsonl is None:
        raise ValueError("either --surface-jsonl or --surface-dir is required")
    shared = _load_surfaces(surface_jsonl.expanduser())
    for key in keys:
        surfaces_by_key[key] = shared
    loaded_ids.extend([s.surface_id for s in shared])
    return surfaces_by_key, loaded_ids


def _points_in_polygon(points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    x = points[:, 0]
    y = points[:, 1]
    poly_x = polygon[:, 0]
    poly_y = polygon[:, 1]
    inside = np.zeros(points.shape[0], dtype=bool)
    j = polygon.shape[0] - 1
    for i in range(polygon.shape[0]):
        yi = poly_y[i]
        yj = poly_y[j]
        crosses = (yi > y) != (yj > y)
        x_at_y = (poly_x[j] - poly_x[i]) * (y - yi) / (yj - yi + 1.0e-12) + poly_x[i]
        inside ^= crosses & (x < x_at_y)
        j = i
    return inside


def _surface_contains_uv(surface: Surface, uv: np.ndarray) -> np.ndarray:
    if surface.polygon_uv is not None and len(surface.polygon_uv) >= 3:
        return _points_in_polygon(uv, surface.polygon_uv)
    mask = np.ones(uv.shape[0], dtype=bool)
    if surface.bounds_u is not None:
        mask &= (uv[:, 0] >= surface.bounds_u[0]) & (uv[:, 0] <= surface.bounds_u[1])
    if surface.bounds_v is not None:
        mask &= (uv[:, 1] >= surface.bounds_v[0]) & (uv[:, 1] <= surface.bounds_v[1])
    return mask


def _terrain_heights(points_xy: np.ndarray, surfaces: list[Surface]) -> tuple[np.ndarray, np.ndarray]:
    heights = np.full(points_xy.shape[0], -np.inf, dtype=np.float64)
    surface_indices = np.full(points_xy.shape[0], -1, dtype=np.int32)
    for surface_idx, surface in enumerate(surfaces):
        delta_xy = points_xy - surface.origin[None, :2]
        # The catalog tangents are orthonormal for current boxes/ground; dot
        # projection keeps this robust if the terrain is not axis-aligned.
        delta3 = np.zeros((points_xy.shape[0], 3), dtype=np.float64)
        delta3[:, :2] = delta_xy
        uv = np.stack((delta3 @ surface.tangent_u, delta3 @ surface.tangent_v), axis=1)
        contains = _surface_contains_uv(surface, uv)
        if not np.any(contains):
            continue
        z = surface.origin[2] - (
            surface.normal[0] * (points_xy[:, 0] - surface.origin[0])
            + surface.normal[1] * (points_xy[:, 1] - surface.origin[1])
        ) / surface.normal[2]
        update = contains & (z > heights)
        heights[update] = z[update]
        surface_indices[update] = surface_idx
    valid = np.isfinite(heights)
    heights[~valid] = 0.0
    return heights.astype(np.float32), surface_indices


def _quat_yaw_wxyz(q: np.ndarray) -> float:
    w, x, y, z = [float(v) for v in q]
    return float(np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z)))


def _rot_yaw(points: np.ndarray, yaw: float) -> np.ndarray:
    c = np.cos(yaw)
    s = np.sin(yaw)
    out = points.copy()
    out[:, 0] = c * points[:, 0] - s * points[:, 1]
    out[:, 1] = s * points[:, 0] + c * points[:, 1]
    return out


def _grid_points(scan_size: float, num_points_per_axis: int) -> np.ndarray:
    half = scan_size / 2.0
    axis = np.linspace(-half, half, num_points_per_axis, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(axis, axis, indexing="ij")
    points = np.zeros((num_points_per_axis * num_points_per_axis, 3), dtype=np.float32)
    points[:, 0] = grid_x.reshape(-1)
    points[:, 1] = grid_y.reshape(-1)
    return points


def _body_index(body_names: np.ndarray, preferred: tuple[str, ...]) -> int:
    names = [str(x) for x in np.asarray(body_names).reshape(-1)]
    for name in preferred:
        if name in names:
            return names.index(name)
    raise ValueError(f"none of {preferred} found in body_names")


def _optional_frame(data: np.lib.npyio.NpzFile, key: str, frames: np.ndarray) -> np.ndarray | None:
    if key not in data.files:
        return None
    value = np.asarray(data[key])
    if value.shape[:1] != (int(frames.max()) + 1,) and value.shape[0] <= int(frames.max()):
        return None
    return value[frames]


def _read_ref_frames(
    *,
    source_paths: np.ndarray,
    start_frames: np.ndarray,
    fallback_ref_npz: Path | None,
) -> dict[str, np.ndarray]:
    if source_paths.size == 0:
        if fallback_ref_npz is None:
            raise ValueError("latents have no source_paths and --ref-npz was not provided")
        source_paths = np.asarray([str(fallback_ref_npz)] * start_frames.shape[0], dtype=np.str_)

    unique_paths = sorted(set(np.asarray(source_paths).astype(str).tolist()))
    if not unique_paths:
        raise ValueError("no source refs available")

    out: dict[str, np.ndarray] = {}
    body_names_ref: np.ndarray | None = None
    joint_names_ref: np.ndarray | None = None
    surface_optional: dict[str, np.ndarray] = {}

    for source_path in unique_paths:
        rows = np.flatnonzero(np.asarray(source_paths).astype(str) == source_path)
        frames = start_frames[rows]
        with np.load(source_path, allow_pickle=False) as ref:
            value = ref["robot_asset_json"] if "robot_asset_json" in ref.files else None
            decode_robot_asset_json(value, context=f"selector source ref {source_path}")
            frame_count = int(ref["joint_pos"].shape[0])
            if frames.size and int(frames.max()) >= frame_count:
                raise ValueError(f"start frame {int(frames.max())} exceeds {source_path} frame count {frame_count}")

            body_names = np.asarray(ref["body_names"])
            joint_names = np.asarray(ref["joint_names"])
            if body_names_ref is None:
                body_names_ref = body_names
                joint_names_ref = joint_names
                root_idx = _body_index(body_names, ("pelvis", "torso_link", "world"))
                specs = {
                    "root_pos_w": np.asarray(ref["body_pos_w"], dtype=np.float32).shape[2:],
                    "root_quat_w": np.asarray(ref["body_quat_w"], dtype=np.float32).shape[2:],
                    "root_lin_vel_w": np.asarray(ref["body_lin_vel_w"], dtype=np.float32).shape[2:],
                    "root_ang_vel_w": np.asarray(ref["body_ang_vel_w"], dtype=np.float32).shape[2:],
                    "joint_pos": np.asarray(ref["joint_pos"], dtype=np.float32).shape[1:],
                    "joint_vel": np.asarray(ref["joint_vel"], dtype=np.float32).shape[1:],
                }
                sample_count = int(start_frames.shape[0])
                for key, shape in specs.items():
                    out[key] = np.zeros((sample_count,) + tuple(shape), dtype=np.float32)
            else:
                if [str(x) for x in body_names] != [str(x) for x in body_names_ref]:
                    raise ValueError(f"body_names mismatch in {source_path}")
                if [str(x) for x in joint_names] != [str(x) for x in joint_names_ref]:
                    raise ValueError(f"joint_names mismatch in {source_path}")
                root_idx = _body_index(body_names, ("pelvis", "torso_link", "world"))

            out["root_pos_w"][rows] = np.asarray(ref["body_pos_w"], dtype=np.float32)[frames, root_idx]
            out["root_quat_w"][rows] = np.asarray(ref["body_quat_w"], dtype=np.float32)[frames, root_idx]
            out["root_lin_vel_w"][rows] = np.asarray(ref["body_lin_vel_w"], dtype=np.float32)[frames, root_idx]
            out["root_ang_vel_w"][rows] = np.asarray(ref["body_ang_vel_w"], dtype=np.float32)[frames, root_idx]
            out["joint_pos"][rows] = np.asarray(ref["joint_pos"], dtype=np.float32)[frames]
            out["joint_vel"][rows] = np.asarray(ref["joint_vel"], dtype=np.float32)[frames]

            for key in (
                "contact_force_part_mask",
                "contact_force_part_w",
                "contact_force_part_position_w",
                "contact_force_part_position_valid",
                "contact_force_part_order",
            ):
                if key not in ref.files:
                    continue
                value = np.asarray(ref[key])
                if value.shape[:1] == (frame_count,):
                    if key not in surface_optional:
                        surface_optional[key] = np.zeros((start_frames.shape[0],) + value.shape[1:], dtype=value.dtype)
                    surface_optional[key][rows] = value[frames]
                elif key not in surface_optional:
                    surface_optional[key] = value

    assert body_names_ref is not None
    assert joint_names_ref is not None
    out["body_names"] = body_names_ref
    out["joint_names"] = joint_names_ref
    out.update(surface_optional)
    return out


def extract(args: argparse.Namespace) -> dict[str, Any]:
    with np.load(args.latents_npz, allow_pickle=True) as latents:
        start_frames = np.asarray(latents["start_frames"], dtype=np.int64)
        end_frames = np.asarray(latents["end_frames"], dtype=np.int64)
        lengths = np.asarray(latents["lengths"], dtype=np.int64)
        codes = np.asarray(latents["codes"], dtype=np.int64)
        theta = np.asarray(latents["theta"], dtype=np.float32)
        z_q = np.asarray(latents["z_q"], dtype=np.float32) if "z_q" in latents.files else np.zeros_like(theta)
        source_paths = np.asarray(latents["source_paths"]).astype(str) if "source_paths" in latents.files else np.asarray([])
        if source_paths.size == 0 and args.ref_npz is not None:
            source_paths = np.asarray([str(args.ref_npz)] * start_frames.shape[0], dtype=np.str_)
        surfaces_by_key, surface_ids = _load_surface_map(
            source_paths=source_paths,
            surface_jsonl=args.surface_jsonl,
            surface_dir=args.surface_dir,
        )
        ref_frames = _read_ref_frames(
            source_paths=source_paths,
            start_frames=start_frames,
            fallback_ref_npz=args.ref_npz,
        )

        body_names = ref_frames["body_names"]
        root_pos_w = ref_frames["root_pos_w"]
        root_quat_w = ref_frames["root_quat_w"]
        root_lin_vel_w = ref_frames["root_lin_vel_w"]
        root_ang_vel_w = ref_frames["root_ang_vel_w"]

        local_grid = _grid_points(args.scan_size, args.num_points_per_axis)
        sample_count = len(start_frames)
        point_count = local_grid.shape[0]
        scan_points_w = np.zeros((sample_count, point_count, 3), dtype=np.float32)
        terrain_height_w = np.zeros((sample_count, point_count), dtype=np.float32)
        terrain_surface_index = np.zeros((sample_count, point_count), dtype=np.int32)
        height_scan = np.zeros((sample_count, point_count), dtype=np.float32)

        for i in range(sample_count):
            surface_key = _motion_surface_key(str(source_paths[i]))
            surfaces = surfaces_by_key[surface_key]
            yaw = _quat_yaw_wxyz(root_quat_w[i])
            points_w = _rot_yaw(local_grid, yaw) + root_pos_w[i]
            heights, surface_idx = _terrain_heights(points_w[:, :2], surfaces)
            scan_points_w[i, :, :2] = points_w[:, :2]
            scan_points_w[i, :, 2] = heights
            terrain_height_w[i] = heights
            terrain_surface_index[i] = surface_idx
            height_scan[i] = heights - root_pos_w[i, 2]

        arrays: dict[str, np.ndarray] = {
            "schema": np.asarray("selector_height_dataset_v1"),
            "motion_id": np.asarray(args.motion_id),
            "start_frames": start_frames,
            "end_frames": end_frames,
            "lengths": lengths,
            "codes": codes,
            "theta": theta,
            "z_q": z_q,
            "height_scan": height_scan.astype(np.float32),
            "terrain_height_w": terrain_height_w.astype(np.float32),
            "terrain_surface_index": terrain_surface_index,
            "scan_points_w": scan_points_w.astype(np.float32),
            "local_grid": local_grid.astype(np.float32),
            "root_pos_w": root_pos_w.astype(np.float32),
            "root_quat_w": root_quat_w.astype(np.float32),
            "root_lin_vel_w": root_lin_vel_w.astype(np.float32),
            "root_ang_vel_w": root_ang_vel_w.astype(np.float32),
            "joint_pos": ref_frames["joint_pos"].astype(np.float32),
            "joint_vel": ref_frames["joint_vel"].astype(np.float32),
            "joint_names": ref_frames["joint_names"],
            "body_names": body_names,
            "surface_ids": np.asarray(surface_ids, dtype=np.str_),
            "robot_asset_json": np.asarray(encode_robot_asset_json()),
        }

        for key in (
            "segment_ids",
            "motion_ids",
            "source_paths",
            "raw_clip_paths",
            "event_start_frames",
            "event_end_frames",
            "anchor_root_pos",
            "active_bodies",
            "window_indices",
            "checkpoint",
            "source_segments_npz",
        ):
            if key in latents.files:
                arrays[key] = np.asarray(latents[key])

        for key in (
            "contact_force_part_mask",
            "contact_force_part_w",
            "contact_force_part_position_w",
            "contact_force_part_position_valid",
            "contact_force_part_order",
        ):
            if key in ref_frames:
                arrays[key] = ref_frames[key]

    args.output_npz.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output_npz, **arrays)

    manifest = {
        "schema": "selector_height_dataset_v1_manifest",
        "motion_id": args.motion_id,
        "sample_count": int(len(start_frames)),
        "scan_size": float(args.scan_size),
        "num_points_per_axis": int(args.num_points_per_axis),
        "height_scan_dim": int(height_scan.shape[1]),
        "ref_npz": str(args.ref_npz) if args.ref_npz is not None else "",
        "latents_npz": str(args.latents_npz),
        "surface_jsonl": str(args.surface_jsonl),
        "surface_dir": str(args.surface_dir) if args.surface_dir is not None else "",
        "output_npz": str(args.output_npz),
        "start_frame_min": int(start_frames.min()),
        "start_frame_max": int(start_frames.max()),
        "code_count": int(len(np.unique(codes))),
        "code_hist": np.bincount(codes, minlength=int(codes.max(initial=0)) + 1).astype(int).tolist(),
        "surface_ids": surface_ids,
        "height_scan_min": float(np.min(height_scan)),
        "height_scan_max": float(np.max(height_scan)),
        "source_ref_count": int(len(set(source_paths.tolist()))) if source_paths.size else 1,
    }
    args.output_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref-npz", type=Path, default=None)
    parser.add_argument("--latents-npz", type=Path, required=True)
    parser.add_argument("--surface-jsonl", type=Path, default=None)
    parser.add_argument("--surface-dir", type=Path, default=None)
    parser.add_argument("--motion-id", default="climb_00_z_scale_1.0")
    parser.add_argument("--output-npz", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--scan-size", type=float, default=0.6)
    parser.add_argument("--num-points-per-axis", type=int, default=7)
    args = parser.parse_args()
    manifest = extract(args)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
