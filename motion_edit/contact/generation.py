from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from motion_edit.contact.layers import read_contact_graph, write_contact_layer
from motion_edit.contact.patches import patches_from_anchors
from motion_edit.contact.plans import ContactEditPlan, validate_contact_edit_plan
from motion_edit.contact.schema import ContactAnchorEditRecord
from motion_edit.layers import write_layer
from motion_edit.paths import LAYERS_ROOT
from motion_edit.schema import SegmentRecord
from motion_edit.storage.canonical import segments_from_contact_transitions, write_motion_version_with_canonical_segments
from motion_edit.storage.io import write_motion_version
from motion_edit.storage.schema import MotionVersionRecord


@dataclass(frozen=True)
class LteGenerationResult:
    output_motion_path: Path
    output_contact_layer: str | None = None
    output_segment_layer: str | None = None
    output_motion_version_id: str | None = None
    warnings: list[str] | None = None


BODY_NAME_KEYS = (
    "body_names",
    "body_name",
    "body_pos_w_names",
    "body_pos_names",
    "contact_force_part_order",
    "contact_part_names",
    "contact_part_order",
)

CONTACT_BODY_LINK_CANDIDATES = {
    "lf": ("left_foot",),
    "rf": ("right_foot",),
    "lh": ("left_hand",),
    "rh": ("right_hand",),
    "lk": ("left_knee",),
    "rk": ("right_knee",),
    "left_foot": (
        "left_ankle_roll_sphere_1_link",
        "left_ankle_roll_sphere_2_link",
        "left_ankle_roll_sphere_3_link",
        "left_ankle_roll_sphere_4_link",
        "left_ankle_roll_sphere_5_link",
        "left_ankle_roll_link",
        "left_ankle_pitch_link",
    ),
    "right_foot": (
        "right_ankle_roll_sphere_1_link",
        "right_ankle_roll_sphere_2_link",
        "right_ankle_roll_sphere_3_link",
        "right_ankle_roll_sphere_4_link",
        "right_ankle_roll_sphere_5_link",
        "right_ankle_roll_link",
        "right_ankle_pitch_link",
    ),
    "left_hand": ("left_rubber_hand_link", "left_thumb_link", "left_pinky_link", "left_wrist_yaw_link"),
    "right_hand": ("right_rubber_hand_link", "right_thumb_link", "right_pinky_link", "right_wrist_yaw_link"),
    "left_knee": ("left_knee_link",),
    "right_knee": ("right_knee_link",),
    "left_hip": ("left_hip_yaw_link", "left_hip_roll_link", "left_hip_pitch_link"),
    "right_hip": ("right_hip_yaw_link", "right_hip_roll_link", "right_hip_pitch_link"),
    "torso": ("torso_link",),
    "root": ("pelvis",),
}


def _decode_npz_string(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.bytes_):
        return bytes(value).decode("utf-8")
    return str(value)


def _motion_strings(data: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        if key not in data:
            continue
        arr = np.asarray(data[key], dtype=object)
        if arr.ndim == 0:
            raw = arr.item()
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [_decode_npz_string(item) for item in parsed]
                except json.JSONDecodeError:
                    return [item.strip() for item in raw.split(",") if item.strip()]
            if isinstance(raw, (list, tuple)):
                return [_decode_npz_string(item) for item in raw]
            return [_decode_npz_string(raw)]
        return [_decode_npz_string(item) for item in arr.reshape(-1).tolist()]
    return []


def resolve_body_index(motion_data: dict[str, Any], body_name: str) -> int:
    names = _motion_strings(motion_data, BODY_NAME_KEYS)
    if not names:
        raise ValueError(
            f"cannot resolve body index for {body_name!r}: motion npz has no body name metadata "
            f"({', '.join(BODY_NAME_KEYS)})"
        )
    if body_name in names:
        return names.index(body_name)
    lowered = [name.lower() for name in names]
    if body_name.lower() in lowered:
        return lowered.index(body_name.lower())
    aliases = CONTACT_BODY_LINK_CANDIDATES.get(body_name.lower(), ())
    for alias in aliases:
        if alias in names:
            return names.index(alias)
        if alias.lower() in lowered:
            return lowered.index(alias.lower())
    raise ValueError(f"cannot resolve body index for {body_name!r}; available bodies={names}")


def _fps_from_motion(data: dict[str, Any], fallback: float) -> float:
    if "fps" in data:
        return float(np.asarray(data["fps"]).reshape(-1)[0])
    if "dt" in data:
        dt = float(np.asarray(data["dt"]).reshape(-1)[0])
        if dt > 0:
            return 1.0 / dt
    return float(fallback)


def _window_weights(n_frames: int, start: int, end: int, *, falloff_before: int, falloff_after: int) -> np.ndarray:
    if end <= start:
        raise ValueError(f"invalid affected frame interval [{start}, {end}]")
    weights = np.zeros(n_frames, dtype=np.float64)
    start = max(0, min(n_frames, int(start)))
    end = max(start, min(n_frames, int(end)))
    weights[start:end] = 1.0
    before0 = max(0, start - max(0, int(falloff_before)))
    if start > before0:
        span = start - before0
        for frame in range(before0, start):
            alpha = (frame - before0 + 1) / (span + 1)
            weights[frame] = 0.5 * (1.0 - np.cos(np.pi * alpha))
    after1 = min(n_frames, end + max(0, int(falloff_after)))
    if after1 > end:
        span = after1 - end
        for frame in range(end, after1):
            alpha = (frame - end + 1) / (span + 1)
            weights[frame] = 0.5 * (1.0 + np.cos(np.pi * alpha))
    return weights


def _edit_interval(edit: ContactAnchorEditRecord, anchor: Any) -> tuple[int, int]:
    if edit.affected_frames is not None:
        return int(edit.affected_frames[0]), int(edit.affected_frames[1])
    return int(anchor.start_frame), int(anchor.end_frame)


def _edit_delta(edit: ContactAnchorEditRecord) -> np.ndarray:
    if edit.delta_world is not None:
        return np.asarray(edit.delta_world, dtype=np.float64)
    if edit.old_world_position is not None and edit.new_world_position is not None:
        return np.asarray(edit.new_world_position, dtype=np.float64) - np.asarray(edit.old_world_position, dtype=np.float64)
    raise ValueError(f"{edit.edit_id}: delta_world or old/new_world_position is required")


def _json_npz_value(payload: dict[str, Any]) -> np.ndarray:
    return np.asarray(json.dumps(payload, sort_keys=True), dtype=object)


def _recompute_linear_velocity(position: np.ndarray, fps: float, dtype: np.dtype) -> np.ndarray:
    if position.shape[0] <= 1:
        return np.zeros_like(position, dtype=dtype)
    dt = 1.0 / float(fps)
    vel = np.zeros_like(position, dtype=np.float64)
    vel[1:-1] = (position[2:] - position[:-2]) / (2.0 * dt)
    vel[0] = (position[1] - position[0]) / dt
    vel[-1] = (position[-1] - position[-2]) / dt
    return vel.astype(dtype, copy=False)


def _load_motion_npz(path: str | Path) -> dict[str, Any]:
    with np.load(Path(path).expanduser(), allow_pickle=True) as data:
        return {key: data[key] for key in data.files}


def _apply_anchor_edits_to_graph(graph: Any, edits: list[ContactAnchorEditRecord]) -> Any:
    edits_by_anchor = {edit.anchor_id: edit for edit in edits}
    anchors = []
    for anchor in graph.anchors:
        edit = edits_by_anchor.get(anchor.anchor_id)
        if edit is None:
            anchors.append(anchor)
            continue
        metadata = dict(anchor.metadata)
        history = list(metadata.get("motion_edit_contact_edits") or [])
        history.append(edit.to_dict())
        metadata["motion_edit_contact_edits"] = history
        metadata["contact_graph_source"] = "source_graph_with_anchor_edits"
        anchors.append(
            replace(
                anchor,
                world_position=edit.new_world_position or anchor.world_position,
                surface_id=anchor.surface_id or edit.surface_id,
                surface_coordinates=edit.surface_coordinates_after or anchor.surface_coordinates,
                metadata=metadata,
            )
        )
    return replace(graph, anchors=anchors, patches=patches_from_anchors(anchors))


def _segments_from_anchor_intervals(graph: Any, *, motion_path: str, source: str = "lte_windowed") -> list[SegmentRecord]:
    segments: list[SegmentRecord] = []
    for index, anchor in enumerate(graph.anchors):
        metadata = {
            "cut_source": source,
            "source_anchor_id": anchor.anchor_id,
            "active_body": anchor.body,
            "source_anchor": anchor.to_dict(),
        }
        segments.append(
            SegmentRecord(
                motion_id=graph.motion_id,
                segment_id=f"{graph.motion_id}_{source}_anchor_{index:04d}",
                start_frame=int(anchor.start_frame),
                end_frame=int(anchor.end_frame),
                source=source,
                status="candidate",
                track="contact_anchor",
                motion_path=motion_path,
                clip_npz=motion_path,
                active=anchor.body,
                metadata=metadata,
            )
        )
    return segments


def _candidate_segments_from_graph(
    graph: Any,
    *,
    motion_path: str,
    motion_version_id: str | None,
    plan_id: str,
) -> list[SegmentRecord]:
    if graph.transitions:
        segments = segments_from_contact_transitions(
            graph,
            motion_version_id=motion_version_id or graph.motion_id,
            motion_path=motion_path,
            source="lte_windowed",
            status="candidate",
            cut_source="lte_windowed",
        )
    else:
        segments = _segments_from_anchor_intervals(graph, motion_path=motion_path)
    output: list[SegmentRecord] = []
    for segment in segments:
        meta = dict(segment.metadata)
        meta["source_contact_edit_plan"] = plan_id
        output.append(replace(segment, motion_id=graph.motion_id, metadata=meta))
    return output


def apply_contact_edit_plan_to_motion(
    plan: ContactEditPlan,
    *,
    output_motion_path: str | Path,
    mode: str = "lte_windowed",
    source_plan_path: str | Path | None = None,
    source_contact_layer: str | None = None,
    output_contact_layer: str | None = None,
    output_segment_layer: str | None = None,
    output_motion_version_id: str | None = None,
    falloff_before: int = 20,
    falloff_after: int = 20,
    global_weight: float = 0.35,
    edited_body_weight: float = 1.0,
    fps: float = 50.0,
    overwrite: bool = False,
    dry_run: bool = False,
    register_motion_version: bool = False,
    build_canonical: bool = False,
    allow_draft: bool = False,
    allow_free: bool = False,
    layers_root: Path = LAYERS_ROOT,
) -> LteGenerationResult:
    if mode != "lte_windowed":
        raise NotImplementedError(f"unsupported LTE generation mode: {mode}")
    if plan.status not in {"validated", "locked"} and not allow_draft:
        raise ValueError("contact edit plan must be validated or locked; pass allow_draft=True to override")
    validate_contact_edit_plan(plan, allow_free=allow_free)
    out = Path(output_motion_path).expanduser()
    if out.exists() and not overwrite and not dry_run:
        raise FileExistsError(f"{out} already exists; pass --overwrite to replace it")
    source_motion = Path(plan.source_motion_path).expanduser()
    if not source_motion.exists():
        raise FileNotFoundError(source_motion)
    motion = _load_motion_npz(source_motion)
    if "body_pos_w" not in motion:
        raise ValueError("LTE augmentation requires body_pos_w or a supported world-space body position array.")
    body_pos = np.asarray(motion["body_pos_w"])
    if body_pos.ndim != 3 or body_pos.shape[2] != 3:
        raise ValueError(f"body_pos_w must have shape [T,B,3], got {body_pos.shape}")
    n_frames, n_bodies, _ = body_pos.shape
    graph = read_contact_graph(layers_root / (source_contact_layer or plan.source_contact_layer), plan.source_motion_id)
    anchors_by_id = {anchor.anchor_id: anchor for anchor in graph.anchors}
    edits = [ContactAnchorEditRecord(**raw) for raw in plan.edits]
    warnings: list[str] = []
    displacement = np.zeros((n_frames, n_bodies, 3), dtype=np.float64)
    edit_summaries: list[dict[str, Any]] = []
    for edit in edits:
        anchor = anchors_by_id.get(edit.anchor_id)
        if anchor is None:
            raise ValueError(f"{edit.edit_id}: anchor not found in source contact graph: {edit.anchor_id}")
        body = edit.body or anchor.body
        body_index = resolve_body_index(motion, body)
        start, end = _edit_interval(edit, anchor)
        if start < 0 or end > n_frames:
            raise ValueError(f"{edit.edit_id}: affected frames [{start}, {end}] outside motion length {n_frames}")
        delta = _edit_delta(edit)
        weights = _window_weights(n_frames, start, end, falloff_before=falloff_before, falloff_after=falloff_after)
        displacement += weights[:, None, None] * delta[None, None, :] * float(global_weight)
        body_extra = float(edited_body_weight) - float(global_weight)
        displacement[:, body_index, :] += weights[:, None] * delta[None, :] * body_extra
        max_delta = float(np.linalg.norm(delta))
        if max_delta > 0.5:
            warnings.append(f"{edit.edit_id}: large requested displacement {max_delta:.3f}m")
        edit_summaries.append(
            {
                "edit_id": edit.edit_id,
                "anchor_id": edit.anchor_id,
                "body": body,
                "body_index": body_index,
                "affected_frames": [start, end],
                "delta_world": delta.tolist(),
                "surface_id": edit.surface_id,
                "object_id": anchor.object_id,
            }
        )
    if dry_run:
        return LteGenerationResult(
            output_motion_path=out,
            output_contact_layer=output_contact_layer,
            output_segment_layer=output_segment_layer,
            output_motion_version_id=output_motion_version_id,
            warnings=warnings,
        )
    generated = dict(motion)
    edited_body_pos = (body_pos.astype(np.float64, copy=False) + displacement).astype(body_pos.dtype, copy=False)
    generated["body_pos_w"] = edited_body_pos
    actual_fps = _fps_from_motion(motion, fps)
    if "body_lin_vel_w" in generated:
        generated["body_lin_vel_w"] = _recompute_linear_velocity(edited_body_pos.astype(np.float64), actual_fps, np.asarray(generated["body_lin_vel_w"]).dtype)
    if "ref_pos_w" in generated and np.asarray(generated["ref_pos_w"]).shape == body_pos.shape:
        generated["ref_pos_w"] = edited_body_pos.astype(np.asarray(generated["ref_pos_w"]).dtype, copy=False)
    elif "ref_pos_w" in generated:
        warnings.append("ref_pos_w preserved because its body mapping/shape is not compatible with body_pos_w")
    if "body_quat_w" in generated or "body_ang_vel_w" in generated:
        warnings.append("orientation fields preserved; position-only LTE augmentation")
    if "joint_pos" in generated or "joint_vel" in generated:
        warnings.append("joint trajectories are preserved; generated motion is a reference deformation, not IK-retargeted motion")
    metadata = {
        "source_plan": str(Path(source_plan_path).expanduser()) if source_plan_path is not None else plan.plan_id,
        "source_plan_id": plan.plan_id,
        "source_motion": str(source_motion),
        "generation_mode": mode,
        "num_edits": len(edits),
        "falloff_before": int(falloff_before),
        "falloff_after": int(falloff_after),
        "global_weight": float(global_weight),
        "edited_body_weight": float(edited_body_weight),
        "warnings": warnings,
        "edits": edit_summaries,
    }
    generated["motion_edit_generation_metadata"] = _json_npz_value(metadata)
    generated["source_motion_path"] = np.asarray(str(source_motion), dtype=object)
    generated["source_contact_edit_plan"] = np.asarray(plan.plan_id, dtype=object)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out, **generated)

    edited_graph = _apply_anchor_edits_to_graph(graph, edits)
    if output_contact_layer:
        write_contact_layer(layers_root / output_contact_layer, edited_graph)
    if output_segment_layer:
        segments = _candidate_segments_from_graph(
            edited_graph,
            motion_path=str(out),
            motion_version_id=output_motion_version_id,
            plan_id=plan.plan_id,
        )
        write_layer(layers_root / output_segment_layer / f"{edited_graph.motion_id}.jsonl", segments)
    if register_motion_version:
        if not output_motion_version_id:
            raise ValueError("--output-motion-version-id is required with --register-motion-version")
        if build_canonical:
            canonical_segments = _candidate_segments_from_graph(
                edited_graph,
                motion_path=str(out),
                motion_version_id=output_motion_version_id,
                plan_id=plan.plan_id,
            )
            record, _segment_path = write_motion_version_with_canonical_segments(
                motion_version_id=output_motion_version_id,
                motion_path=str(out),
                contact_layer=output_contact_layer or "",
                segments=canonical_segments,
                kind="augmented",
                base_motion_id=plan.source_motion_id,
                source="lte_windowed",
                reason=f"build canonical from ContactEditPlan {plan.plan_id}",
            )
            write_motion_version(
                MotionVersionRecord(
                    motion_version_id=record.motion_version_id,
                    motion_path=record.motion_path,
                    kind="augmented",
                    base_motion_id=plan.source_motion_id,
                    motion_asset_id=record.motion_asset_id,
                    parent_motion_version_id=record.parent_motion_version_id,
                    contact_layer=record.contact_layer,
                    canonical_segment_path=record.canonical_segment_path,
                    token_catalog_path=record.token_catalog_path,
                    edit_plan_id=plan.plan_id,
                    metadata={"source_contact_edit_plan": plan.plan_id, "generation_mode": mode},
                )
            )
        else:
            write_motion_version(
                MotionVersionRecord(
                    motion_version_id=output_motion_version_id,
                    motion_path=str(out),
                    kind="augmented",
                    base_motion_id=plan.source_motion_id,
                    contact_layer=output_contact_layer,
                    edit_plan_id=plan.plan_id,
                    metadata={"source_contact_edit_plan": plan.plan_id, "generation_mode": mode},
                )
            )
    return LteGenerationResult(
        output_motion_path=out,
        output_contact_layer=output_contact_layer,
        output_segment_layer=output_segment_layer,
        output_motion_version_id=output_motion_version_id,
        warnings=warnings,
    )
