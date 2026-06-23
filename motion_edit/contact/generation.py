from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, replace
import importlib.util
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

LTE_FULLBODY_KEYPOINT_LINKS = {
    "pelvis": ("pelvis",),
    "left_hip": ("left_hip_roll_link", "left_hip_pitch_link"),
    "left_knee": ("left_knee_link",),
    "left_foot": ("left_ankle_roll_link", "left_ankle_roll_sphere_1_link"),
    "right_hip": ("right_hip_roll_link", "right_hip_pitch_link"),
    "right_knee": ("right_knee_link",),
    "right_foot": ("right_ankle_roll_link", "right_ankle_roll_sphere_1_link"),
    "torso": ("torso_link",),
    "left_shoulder": ("left_shoulder_roll_link", "left_shoulder_pitch_link"),
    "left_elbow": ("left_elbow_link",),
    "left_hand": ("left_wrist_yaw_link", "left_rubber_hand_link"),
    "right_shoulder": ("right_shoulder_roll_link", "right_shoulder_pitch_link"),
    "right_elbow": ("right_elbow_link",),
    "right_hand": ("right_wrist_yaw_link", "right_rubber_hand_link"),
}

LTE_FULLBODY_CONTACT_NAMES = ("left_hand", "right_hand", "left_foot", "right_foot")
LTE_HANDLE_KEYPOINT_NAMES = ("root", "torso", "left_hand", "right_hand", "left_foot", "right_foot")

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


def _index_by_alias(names: list[str], aliases: tuple[str, ...]) -> int:
    lowered = [name.lower() for name in names]
    for alias in aliases:
        if alias in names:
            return names.index(alias)
        if alias.lower() in lowered:
            return lowered.index(alias.lower())
    raise ValueError(f"cannot resolve any of {aliases}; available bodies={names}")


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


def _import_legacy_lte_module(lte_repo_root: str | Path | None) -> Any:
    root = Path(lte_repo_root or "/home/xiaz/lte").expanduser()
    module_path = root / "contact_handle_lte.py"
    if not module_path.exists():
        raise FileNotFoundError(f"missing legacy LTE module: {module_path}")
    spec = importlib.util.spec_from_file_location("motion_edit_legacy_contact_handle_lte", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import legacy LTE module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _semantic_keypoints_from_motion(motion: dict[str, Any]) -> dict[str, np.ndarray]:
    if "body_pos_w" not in motion:
        raise ValueError("lte_fullbody requires source motion body_pos_w")
    body_pos = np.asarray(motion["body_pos_w"], dtype=np.float64)
    if body_pos.ndim != 3 or body_pos.shape[2] != 3:
        raise ValueError(f"body_pos_w must have shape [T,B,3], got {body_pos.shape}")
    names = _motion_strings(motion, ("body_names", "body_name", "body_pos_w_names", "body_pos_names"))
    if not names:
        raise ValueError("lte_fullbody requires body_names metadata")
    return {name: body_pos[:, _index_by_alias(names, aliases), :3].copy() for name, aliases in LTE_FULLBODY_KEYPOINT_LINKS.items()}


def _contact_mask_for_keypoint(motion: dict[str, Any], keypoint: str, n_frames: int) -> np.ndarray:
    mask = np.zeros(n_frames, dtype=bool)
    if "part_order" not in motion or "contact_part_mask" not in motion:
        return mask
    part_order = _motion_strings(motion, ("part_order",))
    if keypoint not in part_order:
        return mask
    raw = np.asarray(motion["contact_part_mask"], dtype=bool)
    if raw.ndim != 2:
        return mask
    count = min(n_frames, raw.shape[0])
    mask[:count] = raw[:count, part_order.index(keypoint)]
    return mask


def _keypoint_contact_weights(motion: dict[str, Any], keypoint: str, n_frames: int) -> np.ndarray:
    mask = _contact_mask_for_keypoint(motion, keypoint, n_frames)
    return mask.astype(np.float64)


def _handles_from_contact_edits(edits: list[ContactAnchorEditRecord], keypoints: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    handles: list[dict[str, Any]] = []
    n_frames = len(next(iter(keypoints.values())))
    for edit in edits:
        name = str(edit.body)
        if name not in keypoints:
            aliases = CONTACT_BODY_LINK_CANDIDATES.get(name.lower(), ())
            matching = [candidate for candidate in aliases if candidate in keypoints]
            name = matching[0] if matching else name
        if name not in keypoints:
            raise ValueError(f"{edit.edit_id}: LTE fullbody edit body {edit.body!r} is not a supported semantic keypoint")
        start, end = _edit_interval(edit, type("AnchorInterval", (), {"start_frame": 0, "end_frame": n_frames})())
        start = max(0, min(n_frames, start))
        end = max(start, min(n_frames, end))
        if end <= start:
            raise ValueError(f"{edit.edit_id}: empty LTE fullbody edit interval [{start}, {end}]")
        frames = np.arange(start, end, dtype=np.int64)
        delta = _edit_delta(edit)
        handles.append(
            {
                "name": name,
                "frames": frames,
                "target": keypoints[name][frames] + delta[None, :],
                "mode": "xyz",
                "weight": float(edit.metadata.get("lte_handle_weight", 1.0)) if isinstance(edit.metadata, dict) else 1.0,
                "ramp": int(edit.metadata.get("lte_handle_ramp", 0)) if isinstance(edit.metadata, dict) else 0,
            }
        )
    return handles


def _legacy_lte_solver_keypoints(keypoints: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {
        "root": keypoints["pelvis"],
        "torso": keypoints["torso"],
        "left_hand": keypoints["left_hand"],
        "right_hand": keypoints["right_hand"],
        "left_foot": keypoints["left_foot"],
        "right_foot": keypoints["right_foot"],
    }


def _merge_solver_keypoints(original: dict[str, np.ndarray], solver_edited: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    edited = {name: value.copy() for name, value in original.items()}
    if "root" in solver_edited:
        edited["pelvis"] = np.asarray(solver_edited["root"], dtype=np.float64)
    for name in ("torso", "left_hand", "right_hand", "left_foot", "right_foot"):
        if name in solver_edited:
            edited[name] = np.asarray(solver_edited[name], dtype=np.float64)
    return edited


def _save_lte_keypoints(path: Path, *, keypoints: dict[str, np.ndarray], motion: dict[str, Any], source_motion: Path, edits: list[ContactAnchorEditRecord]) -> None:
    n_frames = len(next(iter(keypoints.values())))
    arrays: dict[str, Any] = {name: np.asarray(value, dtype=np.float64) for name, value in keypoints.items()}
    arrays["source_demo"] = np.asarray(str(source_motion.expanduser().resolve()))
    arrays["source_frame_index"] = np.arange(n_frames, dtype=np.float64)
    if edits:
        arrays["terrain_shift"] = np.asarray(_edit_delta(edits[0]), dtype=np.float64)
    for name in LTE_FULLBODY_CONTACT_NAMES:
        arrays[f"contact_mask_{name}"] = _contact_mask_for_keypoint(motion, name, n_frames)
        arrays[f"contact_weight_{name}"] = _keypoint_contact_weights(motion, name, n_frames)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, **arrays)


def _semantic_body_weights(body_names: list[str], keypoint_names: list[str]) -> np.ndarray:
    weights = np.zeros((len(body_names), len(keypoint_names)), dtype=np.float64)
    sem = {name: index for index, name in enumerate(keypoint_names)}
    for index, name in enumerate(body_names):
        if name == "world":
            continue
        if name in {"pelvis", "pelvis_contour_link"} or name.startswith(("left_hip", "right_hip")):
            weights[index, sem["pelvis"]] = 1.0
        elif name.startswith(("waist", "torso")) or "shoulder" in name:
            weights[index, sem["torso"]] = 1.0
        elif name.startswith("left_"):
            if any(token in name for token in ("knee", "ankle")):
                weights[index, sem["pelvis"]] = 0.35
                weights[index, sem["left_foot"]] = 0.65
            elif any(token in name for token in ("elbow", "wrist", "rubber_hand", "thumb", "pinky")):
                weights[index, sem["torso"]] = 0.25
                weights[index, sem["left_hand"]] = 0.75
            else:
                weights[index, sem["torso"]] = 1.0
        elif name.startswith("right_"):
            if any(token in name for token in ("knee", "ankle")):
                weights[index, sem["pelvis"]] = 0.35
                weights[index, sem["right_foot"]] = 0.65
            elif any(token in name for token in ("elbow", "wrist", "rubber_hand", "thumb", "pinky")):
                weights[index, sem["torso"]] = 0.25
                weights[index, sem["right_hand"]] = 0.75
            else:
                weights[index, sem["torso"]] = 1.0
        else:
            weights[index, sem["pelvis"]] = 1.0
    missing = weights.sum(axis=1) <= 0.0
    weights[missing, sem["pelvis"]] = 1.0
    return weights / weights.sum(axis=1, keepdims=True)


def _dense_taskspace_from_keypoints(motion: dict[str, Any], original: dict[str, np.ndarray], edited: dict[str, np.ndarray], source_motion: Path, lte_path: Path) -> dict[str, Any]:
    raw_body_pos = np.asarray(motion["body_pos_w"], dtype=np.float64)
    n_frames = len(next(iter(edited.values())))
    body_pos = raw_body_pos[:n_frames].copy()
    body_names_arr = np.asarray(motion["body_names"])
    body_names = [str(item) for item in body_names_arr.reshape(-1).tolist()]
    keypoint_names = list(LTE_FULLBODY_KEYPOINT_LINKS)
    offsets = np.stack([edited[name] - original[name] for name in keypoint_names], axis=1)
    dense_offset = np.einsum("tsc,bs->tbc", offsets, _semantic_body_weights(body_names, keypoint_names))
    edited_body_pos = body_pos + dense_offset
    fps = np.asarray(motion["fps"]) if "fps" in motion else np.asarray([50], dtype=np.int64)
    arrays: dict[str, Any] = {
        "body_names": body_names_arr,
        "fps": fps,
        "source_demo": np.asarray(str(source_motion.expanduser().resolve())),
        "source_lte": np.asarray(str(lte_path.expanduser().resolve())),
        "algorithm": np.asarray("motion_edit_lte_fullbody_taskspace"),
        "is_qpos": np.asarray(False),
        "note": np.asarray("body_pos_w is generated from ContactEditPlan LTE keypoint offsets; joint fields come from fullbody IK."),
        "body_pos_w": edited_body_pos.astype(np.float64),
        "body_lin_vel_w": _recompute_linear_velocity(edited_body_pos, float(np.asarray(fps).reshape(-1)[0]), np.dtype(np.float64)),
    }
    if "body_quat_w" in motion:
        arrays["body_quat_w"] = np.asarray(motion["body_quat_w"])[:n_frames]
    for key in ("part_order", "contact_part_mask", "active_part_mask", "support_part_mask", "free_part_mask"):
        if key in motion:
            arr = np.asarray(motion[key])
            arrays[key] = arr[:n_frames] if arr.shape[:1] == (n_frames,) or arr.shape[:1] == (raw_body_pos.shape[0],) else arr
    for name in keypoint_names:
        arrays[f"keypoint_{name}"] = np.asarray(edited[name], dtype=np.float64)
        arrays[f"offset_{name}"] = np.asarray(edited[name] - original[name], dtype=np.float64)
    return arrays


def _run_fullbody_ik_subprocess(
    *,
    lte_path: Path,
    ik_output_path: Path,
    lte_repo_root: str | Path | None,
    ik_script: str | Path | None,
    ik_conda_env: str,
    ik_max_nfev: int | None,
) -> None:
    repo = Path(lte_repo_root or "/home/xiaz/lte").expanduser()
    script = Path(ik_script).expanduser() if ik_script else repo / "scripts" / "solve_lte_fullbody_ik.py"
    cmd = ["conda", "run", "-n", str(ik_conda_env), "python", str(script.resolve()), "--lte", str(lte_path.resolve()), "--out", str(ik_output_path.resolve())]
    if ik_max_nfev is not None:
        cmd.extend(["--max-nfev", str(int(ik_max_nfev))])
    subprocess.run(cmd, cwd=str(repo), check=True)


def _legacy_lte_paths(plan: ContactEditPlan) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    legacy = plan.metadata.get("legacy_lte") if isinstance(plan.metadata, dict) else None
    if isinstance(legacy, dict):
        for key in ("fullbody_ik_motion", "taskspace_motion", "keypoints"):
            if legacy.get(key):
                paths[key] = Path(str(legacy[key])).expanduser()
    for raw_edit in plan.edits:
        metadata = raw_edit.get("metadata") if isinstance(raw_edit, dict) else None
        if not isinstance(metadata, dict):
            continue
        for key in ("fullbody_ik_motion", "taskspace_motion", "keypoints"):
            if key not in paths and metadata.get(key):
                paths[key] = Path(str(metadata[key])).expanduser()
    if "fullbody_ik_motion" not in paths and "taskspace_motion" not in paths:
        raise ValueError("lte_legacy_fullbody requires legacy_lte.fullbody_ik_motion or taskspace_motion in the ContactEditPlan metadata")
    return paths


def _load_legacy_lte_motion_payload(paths: dict[str, Path]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    base_path = paths.get("taskspace_motion") or paths.get("fullbody_ik_motion")
    if base_path is None:
        raise ValueError("legacy LTE motion paths are empty")
    if not base_path.exists():
        raise FileNotFoundError(base_path)
    payload = _load_motion_npz(base_path)
    fullbody_path = paths.get("fullbody_ik_motion")
    if fullbody_path is not None:
        if not fullbody_path.exists():
            raise FileNotFoundError(fullbody_path)
        fullbody = _load_motion_npz(fullbody_path)
        for key in ("joint_pos", "joint_vel", "joint_names", "is_qpos"):
            if key in fullbody:
                payload[key] = fullbody[key]
    if "taskspace_motion" in paths and "fullbody_ik_motion" in paths:
        warnings.append("legacy taskspace motion reused with fullbody IK joint fields merged")
    elif "fullbody_ik_motion" in paths:
        warnings.append("legacy fullbody IK motion reused; no local LTE solve was run")
    else:
        warnings.append("legacy taskspace motion reused; no local LTE solve was run")
    return payload, warnings


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
    lte_repo_root: str | Path | None = None,
    ik_script: str | Path | None = None,
    ik_conda_env: str = "env_pyroki_climb_projection",
    ik_max_nfev: int | None = None,
    intermediate_dir: str | Path | None = None,
    layers_root: Path = LAYERS_ROOT,
) -> LteGenerationResult:
    if mode not in {"lte_windowed", "lte_legacy_fullbody", "lte_fullbody"}:
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
    graph = read_contact_graph(layers_root / (source_contact_layer or plan.source_contact_layer), plan.source_motion_id)
    edits = [ContactAnchorEditRecord(**raw) for raw in plan.edits]
    if mode == "lte_fullbody":
        motion = _load_motion_npz(source_motion)
        original_keypoints = _semantic_keypoints_from_motion(motion)
        solver_keypoints = _legacy_lte_solver_keypoints(original_keypoints)
        handles = _handles_from_contact_edits(edits, solver_keypoints)
        legacy_lte = _import_legacy_lte_module(lte_repo_root)
        result = legacy_lte.deform_demo_with_contact_handles_lte(
            solver_keypoints,
            handles,
            weights={"handle_weight": 1100.0, "body_relative_weight": 40.0, "smooth_offset_weight": 5.0},
            config={"names": LTE_HANDLE_KEYPOINT_NAMES, "fix_start_root": True, "use_body_relative_edges": True},
        )
        edited_keypoints = _merge_solver_keypoints(original_keypoints, result["edited_keypoints"])
        work_dir = Path(intermediate_dir).expanduser() if intermediate_dir is not None else out.with_suffix("")
        lte_path = work_dir / f"{out.stem}.lte_keypoints.npz"
        taskspace_path = work_dir / f"{out.stem}.taskspace_motion.npz"
        ik_path = work_dir / f"{out.stem}.fullbody_ik_motion.npz"
        if dry_run:
            return LteGenerationResult(
                output_motion_path=out,
                output_contact_layer=output_contact_layer,
                output_segment_layer=output_segment_layer,
                output_motion_version_id=output_motion_version_id,
                warnings=[f"would write LTE keypoints {lte_path}", f"would run fullbody IK to {ik_path}"],
            )
        work_dir.mkdir(parents=True, exist_ok=True)
        _save_lte_keypoints(lte_path, keypoints=edited_keypoints, motion=motion, source_motion=source_motion, edits=edits)
        taskspace = _dense_taskspace_from_keypoints(motion, original_keypoints, edited_keypoints, source_motion, lte_path)
        np.savez(taskspace_path, **taskspace)
        _run_fullbody_ik_subprocess(
            lte_path=lte_path,
            ik_output_path=ik_path,
            lte_repo_root=lte_repo_root,
            ik_script=ik_script,
            ik_conda_env=ik_conda_env,
            ik_max_nfev=ik_max_nfev,
        )
        if not ik_path.exists():
            raise FileNotFoundError(f"fullbody IK did not produce {ik_path}")
        generated = dict(taskspace)
        fullbody = _load_motion_npz(ik_path)
        for key in ("joint_pos", "joint_vel", "joint_names", "is_qpos"):
            if key in fullbody:
                generated[key] = fullbody[key]
        warnings = ["lte_fullbody generated taskspace keypoints and ran fullbody IK"]
        metadata = {
            "source_plan": str(Path(source_plan_path).expanduser()) if source_plan_path is not None else plan.plan_id,
            "source_plan_id": plan.plan_id,
            "source_motion": str(source_motion),
            "generation_mode": mode,
            "lte_keypoints": str(lte_path),
            "taskspace_motion": str(taskspace_path),
            "fullbody_ik_motion": str(ik_path),
            "ik_conda_env": ik_conda_env,
            "ik_script": str(Path(ik_script).expanduser()) if ik_script else str((Path(lte_repo_root or "/home/xiaz/lte").expanduser() / "scripts" / "solve_lte_fullbody_ik.py")),
            "num_edits": len(edits),
            "warnings": warnings,
            "edits": [edit.to_dict() for edit in edits],
            "lte_debug": result.get("debug", {}),
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
    if mode == "lte_legacy_fullbody":
        legacy_paths = _legacy_lte_paths(plan)
        base_motion_path = legacy_paths.get("taskspace_motion") or legacy_paths.get("fullbody_ik_motion")
        if base_motion_path is None:
            raise ValueError("legacy LTE motion paths are empty")
        if dry_run:
            return LteGenerationResult(
                output_motion_path=out,
                output_contact_layer=output_contact_layer,
                output_segment_layer=output_segment_layer,
                output_motion_version_id=output_motion_version_id,
                warnings=["legacy LTE motion will be reused as the augmented motion"],
            )
        generated, warnings = _load_legacy_lte_motion_payload(legacy_paths)
        metadata = {
            "source_plan": str(Path(source_plan_path).expanduser()) if source_plan_path is not None else plan.plan_id,
            "source_plan_id": plan.plan_id,
            "source_motion": str(source_motion),
            "generation_mode": mode,
            "legacy_fullbody_ik_motion": str(legacy_paths["fullbody_ik_motion"]) if "fullbody_ik_motion" in legacy_paths else None,
            "legacy_taskspace_motion": str(legacy_paths["taskspace_motion"]) if "taskspace_motion" in legacy_paths else None,
            "legacy_keypoints": str(legacy_paths["keypoints"]) if "keypoints" in legacy_paths else None,
            "num_edits": len(edits),
            "warnings": warnings,
            "edits": [edit.to_dict() for edit in edits],
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
    motion = _load_motion_npz(source_motion)
    if "body_pos_w" not in motion:
        raise ValueError("LTE augmentation requires body_pos_w or a supported world-space body position array.")
    body_pos = np.asarray(motion["body_pos_w"])
    if body_pos.ndim != 3 or body_pos.shape[2] != 3:
        raise ValueError(f"body_pos_w must have shape [T,B,3], got {body_pos.shape}")
    n_frames, n_bodies, _ = body_pos.shape
    anchors_by_id = {anchor.anchor_id: anchor for anchor in graph.anchors}
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
