from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from somaforge_core.contact_schema import (
    CONTACT_FORCE_PART_ORDER,
    decode_contact_force_provenance,
    diagnostic_contact_provenance,
    encode_contact_force_provenance,
)
from somaforge_core.robot_assets import (
    decode_robot_asset_json,
    encode_robot_asset_json,
)

from motion_edit.contact.layers import read_contact_graph
from motion_edit.contact_force import (
    DEFAULT_CONTACT_FORCE_PART_ORDER,
    RetargetContactForceConfig,
    retarget_contact_forces,
)


@dataclass(frozen=True)
class ContactForceBakeResult:
    output_motion_path: Path
    metadata: dict[str, Any]
    warnings: list[str]


WBT_POLICY_REF_REQUIRED_KEYS = (
    "fps",
    "joint_pos",
    "joint_vel",
    "body_pos_w",
    "body_quat_w",
    "body_lin_vel_w",
    "body_ang_vel_w",
    "body_names",
    "joint_names",
    "contact_force_part_w",
    "contact_force_part_mask",
    "contact_force_part_order",
    "robot_asset_json",
)


def validate_wbt_contact_force_policy_ref(
    path: str | Path, *, require_newton_source: bool = True
) -> dict[str, Any]:
    """Validate the canonical spherehand 8-part WBT contact-force contract."""

    ref_path = Path(path).expanduser()
    data = _load_npz_pickle_free(ref_path)
    missing = [key for key in WBT_POLICY_REF_REQUIRED_KEYS if key not in data]
    if missing:
        raise KeyError(f"{ref_path} missing WBT policy ref keys: {missing}")
    joint_names = _motion_strings(data, ("joint_names",))
    body_names = _motion_strings(data, ("body_names",))
    joint_pos = np.asarray(data["joint_pos"])
    joint_vel = np.asarray(data["joint_vel"])
    body_pos_w = np.asarray(data["body_pos_w"])
    body_quat_w = np.asarray(data["body_quat_w"])
    body_lin_vel_w = np.asarray(data["body_lin_vel_w"])
    body_ang_vel_w = np.asarray(data["body_ang_vel_w"])
    force = np.asarray(data["contact_force_part_w"])
    mask = np.asarray(data["contact_force_part_mask"])
    order = [str(item) for item in np.asarray(data["contact_force_part_order"]).reshape(-1).tolist()]
    robot_asset = decode_robot_asset_json(data["robot_asset_json"], context=f"policy ref {ref_path}")
    contact_provenance = decode_contact_force_provenance(
        data.get("contact_force_provenance_json"),
        context=f"policy ref {ref_path}",
        require_newton=require_newton_source,
    )

    n_frames = int(joint_pos.shape[0])
    if joint_pos.shape != (n_frames, len(joint_names) + 7):
        raise ValueError(f"joint_pos must be [T, len(joint_names)+7], got {joint_pos.shape} names={len(joint_names)}")
    if joint_vel.shape != (n_frames, len(joint_names) + 6):
        raise ValueError(f"joint_vel must be [T, len(joint_names)+6], got {joint_vel.shape} names={len(joint_names)}")
    expected_body_shape = (n_frames, len(body_names), 3)
    if body_pos_w.shape != expected_body_shape:
        raise ValueError(f"body_pos_w must be {expected_body_shape}, got {body_pos_w.shape}")
    if body_lin_vel_w.shape != expected_body_shape:
        raise ValueError(f"body_lin_vel_w must be {expected_body_shape}, got {body_lin_vel_w.shape}")
    if body_ang_vel_w.shape != expected_body_shape:
        raise ValueError(f"body_ang_vel_w must be {expected_body_shape}, got {body_ang_vel_w.shape}")
    if body_quat_w.shape != (n_frames, len(body_names), 4):
        raise ValueError(f"body_quat_w must be {(n_frames, len(body_names), 4)}, got {body_quat_w.shape}")
    expected_order = list(CONTACT_FORCE_PART_ORDER)
    if force.shape != (n_frames, 8, 3):
        raise ValueError(f"contact_force_part_w must be [T, 8, 3], got {force.shape}")
    if mask.shape != (n_frames, 8):
        raise ValueError(f"contact_force_part_mask must be [T, 8], got {mask.shape}")
    if order != expected_order:
        raise ValueError(f"contact_force_part_order must be {expected_order}, got {order}")
    if not np.all(np.isfinite(force)):
        raise ValueError("contact_force_part_w contains NaN or Inf")
    return {
        "path": str(ref_path),
        "frames": n_frames,
        "joint_pos_shape": tuple(int(x) for x in joint_pos.shape),
        "joint_vel_shape": tuple(int(x) for x in joint_vel.shape),
        "body_count": len(body_names),
        "contact_force_part_order": order,
        "force_norm_max": float(np.linalg.norm(force, axis=2).max(initial=0.0)),
        "contact_frame_count": int(np.count_nonzero(mask)),
        "allow_pickle_false": True,
        "robot_asset": robot_asset,
        "contact_force_provenance": contact_provenance,
    }


def bake_retargeted_contact_forces_for_motion(
    motion_path: str | Path,
    *,
    source_force_ref_path: str | Path,
    output_motion_path: str | Path | None = None,
    target_contact_layer_path: str | Path | None = None,
    target_motion_id: str | None = None,
    force_unit_scale: float = 1.0,
    max_force_norm: float | None = 5000.0,
    smoothing_window: int = 3,
    policy_ref_compat: str = "wbt_contact_force_8part",
    overwrite: bool = False,
) -> ContactForceBakeResult:
    """Retarget source contact-force phases onto a generated kinematic reference.

    This path does not run a simulator. It keeps the generated kinematic
    reference unchanged and rewrites only the canonical part-level force fields.
    """

    source = Path(motion_path).expanduser()
    source_force_ref = Path(source_force_ref_path).expanduser()
    out = Path(output_motion_path).expanduser() if output_motion_path is not None else source
    if out.exists() and out != source and not overwrite:
        raise FileExistsError(f"{out} already exists; pass overwrite=True to replace it")
    motion = _load_motion_npz(source)
    force_ref = _load_motion_npz(source_force_ref)
    robot_asset = decode_robot_asset_json(motion.get("robot_asset_json"), context=f"motion {source}")
    decode_robot_asset_json(force_ref.get("robot_asset_json"), context=f"force reference {source_force_ref}")
    actual_fps = _fps_from_motion(motion, fallback=50.0)
    part_order = DEFAULT_CONTACT_FORCE_PART_ORDER
    target_normals, target_normal_meta = _target_contact_normals_from_layer(
        target_contact_layer_path=target_contact_layer_path,
        target_motion_id=target_motion_id,
        n_frames=_motion_frame_count(motion),
        part_order=part_order,
    )
    field = retarget_contact_forces(
        target_motion=motion,
        source_force_ref=force_ref,
        config=RetargetContactForceConfig(
            part_order=part_order,
            target_normal_w=target_normals,
            force_unit_scale=float(force_unit_scale),
            max_force_norm=max_force_norm,
            smoothing_window=int(smoothing_window),
            metadata={
                "bake_entry": "generation.contact_force_bake.retarget",
                "source_motion": str(source),
                "output_motion": str(out),
                "source_force_ref": str(source_force_ref),
                **target_normal_meta,
            },
        ),
    )
    output = dict(motion)
    if policy_ref_compat == "none":
        output.update(field.to_npz_arrays())
    elif policy_ref_compat == "wbt_contact_force_8part":
        output.update(field.to_wbt_8part_npz_arrays())
    else:
        raise ValueError("policy_ref_compat must be 'wbt_contact_force_8part' or 'none'")
    derived_motion_fields = _ensure_policy_ref_derived_motion_fields(output, fps=actual_fps)
    force_metadata = dict(field.metadata)
    force_metadata.update(
        {
            "fps": float(actual_fps),
            "policy_ref_compat": policy_ref_compat,
            "contact_force_part_w_key": "contact_force_part_w",
            "derived_motion_fields": derived_motion_fields,
            "robot_asset": robot_asset,
        }
    )
    output["motion_edit_force_metadata"] = _json_npz_value(force_metadata)
    output["robot_asset_json"] = np.asarray(encode_robot_asset_json(robot_asset))
    source_provenance = decode_contact_force_provenance(
        force_ref.get("contact_force_provenance_json"),
        context=f"force reference {source_force_ref}",
        require_newton=True,
    )
    output["contact_force_provenance_json"] = np.asarray(
        encode_contact_force_provenance(
            diagnostic_contact_provenance(
                source_backend="motion_edit_force_retarget",
                metadata={"source_newton_provenance": source_provenance, "force_metadata": force_metadata},
            )
        )
    )
    if "motion_edit_generation_metadata" in output:
        generation_metadata = _decode_json_npz(output["motion_edit_generation_metadata"])
        generation_metadata["contact_force_bake"] = force_metadata
        output["motion_edit_generation_metadata"] = _json_npz_value(generation_metadata)
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_motion_npz(out, output, policy_ref_compat=policy_ref_compat)
    warnings: list[str] = []
    if int(force_metadata.get("unmatched_target_phase_count", 0)) > 0:
        warnings.append(f"retargeted force left {force_metadata['unmatched_target_phase_count']} target contact phases unmatched")
    if force_metadata.get("target_position", {}).get("source") == "zeros_no_position_available":
        warnings.append("retargeted force used zero contact positions because target motion has no contact/body positions")
    return ContactForceBakeResult(output_motion_path=out, metadata=force_metadata, warnings=warnings)


def _load_motion_npz(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=True) as data:
        return {key: data[key] for key in data.files}


def _load_npz_pickle_free(path: Path) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    try:
        with np.load(path, allow_pickle=False) as data:
            for key in data.files:
                try:
                    arrays[key] = np.asarray(data[key])
                except ValueError as exc:
                    raise ValueError(
                        f"{path} contains an object-dtype array at key '{key}'; "
                        "WBT policy refs must load with allow_pickle=False"
                    ) from exc
    except ValueError as exc:
        if "Object arrays cannot be loaded when allow_pickle=False" in str(exc):
            raise ValueError(f"{path} is not pickle-free: {exc}") from exc
        raise
    object_keys = [key for key, value in arrays.items() if value.dtype == object]
    if object_keys:
        raise ValueError(f"{path} contains object-dtype arrays: {object_keys}")
    return arrays


def _write_motion_npz(path: Path, payload: dict[str, Any], *, policy_ref_compat: str) -> None:
    output = _pickle_free_npz_payload(payload) if policy_ref_compat == "wbt_contact_force_8part" else dict(payload)
    np.savez(path, **output)


def _pickle_free_npz_payload(payload: dict[str, Any]) -> dict[str, np.ndarray]:
    return {key: _pickle_free_npz_value(value) for key, value in payload.items()}


def _pickle_free_npz_value(value: Any) -> np.ndarray:
    arr = np.asarray(value)
    if arr.dtype != object:
        return arr
    obj = np.asarray(value, dtype=object)
    if obj.ndim == 0:
        return np.asarray(_pickle_free_scalar(obj.item()))
    flat = [_pickle_free_scalar(item) for item in obj.reshape(-1).tolist()]
    if all(isinstance(item, (bool, np.bool_)) for item in flat):
        return np.asarray(flat, dtype=bool).reshape(obj.shape)
    if all(isinstance(item, (int, np.integer)) and not isinstance(item, (bool, np.bool_)) for item in flat):
        return np.asarray(flat, dtype=np.int64).reshape(obj.shape)
    if all(isinstance(item, (int, np.integer, float, np.floating)) and not isinstance(item, (bool, np.bool_)) for item in flat):
        return np.asarray(flat, dtype=np.float64).reshape(obj.shape)
    return np.asarray([_string_npz_item(item) for item in flat], dtype=np.str_).reshape(obj.shape)


def _pickle_free_scalar(item: Any) -> Any:
    if isinstance(item, bytes):
        return item.decode("utf-8")
    if isinstance(item, np.generic):
        return item.item()
    if isinstance(item, (str, bool, int, float)):
        return item
    if item is None:
        return ""
    return json.dumps(_json_safe(item), sort_keys=True)


def _string_npz_item(item: Any) -> str:
    if isinstance(item, bytes):
        return item.decode("utf-8")
    if isinstance(item, str):
        return item
    if isinstance(item, (bool, int, float, np.generic)):
        return str(item)
    if item is None:
        return ""
    return json.dumps(_json_safe(item), sort_keys=True)


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _decode_npz_string(value: Any) -> str:
    raw = np.asarray(value, dtype=object)
    item = raw.item() if raw.ndim == 0 else raw.reshape(-1)[0]
    if isinstance(item, bytes):
        return item.decode("utf-8")
    return str(item)


def _decode_json_npz(value: Any) -> dict[str, Any]:
    try:
        raw = _decode_npz_string(value)
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _json_npz_value(payload: dict[str, Any]) -> np.ndarray:
    return np.asarray(json.dumps(payload, sort_keys=True), dtype=np.str_)


def _fps_from_motion(motion: dict[str, Any], *, fallback: float) -> float:
    if "fps" in motion:
        return float(np.asarray(motion["fps"]).reshape(-1)[0])
    if "dt" in motion:
        dt = float(np.asarray(motion["dt"]).reshape(-1)[0])
        if dt > 0.0:
            return 1.0 / dt
    return float(fallback)


def _motion_strings(motion: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        if key not in motion:
            continue
        arr = np.asarray(motion[key], dtype=object)
        if arr.ndim == 0:
            item = arr.item()
            if isinstance(item, str):
                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, list):
                        return [str(value) for value in parsed]
                except json.JSONDecodeError:
                    return [value.strip() for value in item.split(",") if value.strip()]
            if isinstance(item, (list, tuple)):
                return [str(value) for value in item]
            return [str(item)]
        return [str(value) for value in arr.reshape(-1).tolist()]
    return []


def _motion_frame_count(motion: dict[str, Any]) -> int:
    for key in ("joint_pos", "body_pos_w", "contact_force_part_mask", "contact_part_mask", "contact_force_part_w"):
        if key in motion:
            arr = np.asarray(motion[key])
            if arr.ndim >= 1:
                return int(arr.shape[0])
    raise ValueError("motion has no frame-indexed arrays")


def _target_contact_normals_from_layer(
    *,
    target_contact_layer_path: str | Path | None,
    target_motion_id: str | None,
    n_frames: int,
    part_order: tuple[str, ...],
) -> tuple[np.ndarray | None, dict[str, Any]]:
    if target_contact_layer_path is None:
        return None, {"target_normal_source": "default_up"}
    if not target_motion_id:
        raise ValueError("target_motion_id is required when target_contact_layer_path is provided")
    graph = read_contact_graph(Path(target_contact_layer_path).expanduser(), str(target_motion_id))
    normals = np.full((int(n_frames), len(part_order), 3), np.nan, dtype=np.float64)
    filled = np.zeros((int(n_frames), len(part_order)), dtype=bool)
    skipped = 0
    for anchor in graph.anchors:
        part_index = _part_index_for_body(getattr(anchor, "body", ""), part_order)
        if part_index is None:
            skipped += 1
            continue
        normal = getattr(anchor, "surface_normal", None) or getattr(anchor, "normal", None)
        if normal is None:
            skipped += 1
            continue
        unit = _unit_vector3(normal)
        start = max(0, min(int(n_frames), int(anchor.start_frame)))
        end = max(start, min(int(n_frames), int(anchor.end_frame)))
        if end <= start:
            continue
        normals[start:end, part_index] = unit[None, :]
        filled[start:end, part_index] = True
    return normals, {
        "target_normal_source": "contact_layer",
        "target_contact_layer": str(Path(target_contact_layer_path).expanduser()),
        "target_motion_id": str(target_motion_id),
        "target_normal_frame_count": int(np.count_nonzero(filled)),
        "target_normal_skipped_anchor_count": int(skipped),
    }


def _part_index_for_body(body: str, part_order: tuple[str, ...]) -> int | None:
    canonical = _canonical_contact_part(body)
    if canonical is None:
        return None
    for index, part in enumerate(part_order):
        if _canonical_contact_part(part) == canonical:
            return int(index)
    return None


def _canonical_contact_part(name: str) -> str | None:
    key = str(name).strip().lower()
    aliases = {
        "lhee": "left_heel",
        "ltoe": "left_toe",
        "rhee": "right_heel",
        "rtoe": "right_toe",
        "lh": "left_hand",
        "rh": "right_hand",
        "lk": "left_knee",
        "rk": "right_knee",
        "left_heel": "left_heel",
        "left_toe": "left_toe",
        "right_heel": "right_heel",
        "right_toe": "right_toe",
        "left_hand": "left_hand",
        "right_hand": "right_hand",
        "left_knee": "left_knee",
        "right_knee": "right_knee",
    }
    if key in aliases:
        return aliases[key]
    for token, canonical in aliases.items():
        if token and token in key:
            return canonical
    return None


def _unit_vector3(value: Any) -> np.ndarray:
    vec = np.asarray(value, dtype=np.float64)
    if vec.shape != (3,) or not np.all(np.isfinite(vec)):
        raise ValueError(f"normal must have shape (3,), got {vec.shape}")
    norm = float(np.linalg.norm(vec))
    if norm <= 1.0e-12:
        raise ValueError("normal must be nonzero")
    return vec / norm


def _ensure_policy_ref_derived_motion_fields(output: dict[str, Any], *, fps: float) -> list[str]:
    derived: list[str] = []
    joint_names = _motion_strings(output, ("joint_names",))
    if "joint_pos" in output:
        joint_pos = np.asarray(output["joint_pos"], dtype=np.float64)
        expected_joint_vel_shape = (int(joint_pos.shape[0]), len(joint_names) + 6) if joint_pos.ndim == 2 else None
        current_joint_vel = np.asarray(output["joint_vel"]) if "joint_vel" in output else None
        if expected_joint_vel_shape is not None and (
            current_joint_vel is None or tuple(current_joint_vel.shape) != expected_joint_vel_shape
        ):
            output["joint_vel"] = _derive_policy_joint_velocity_from_qpos(joint_pos, joint_names=joint_names, fps=float(fps))
            derived.append("joint_vel")
    if "body_lin_vel_w" not in output and "body_pos_w" in output:
        output["body_lin_vel_w"] = _recompute_linear_velocity(np.asarray(output["body_pos_w"], dtype=np.float64), fps=float(fps))
        derived.append("body_lin_vel_w")
    if "body_ang_vel_w" not in output and "body_quat_w" in output:
        output["body_ang_vel_w"] = _recompute_body_angular_velocity(np.asarray(output["body_quat_w"], dtype=np.float64), fps=float(fps))
        derived.append("body_ang_vel_w")
    return derived


def _derive_policy_joint_velocity_from_qpos(qpos: np.ndarray, *, joint_names: list[str], fps: float) -> np.ndarray:
    q = np.asarray(qpos, dtype=np.float64)
    if q.ndim != 2:
        raise ValueError(f"joint_pos must have shape [T, nq], got {q.shape}")
    expected_qpos_width = len(joint_names) + 7
    if q.shape[1] != expected_qpos_width:
        raise ValueError(f"joint_pos must be [T, len(joint_names)+7], got {q.shape} names={len(joint_names)}")
    root_lin_vel = _recompute_linear_velocity(q[:, 0:3], fps=float(fps))
    root_ang_vel = _recompute_body_angular_velocity(q[:, None, 3:7], fps=float(fps))[:, 0, :]
    joint_vel = _recompute_linear_velocity(q[:, 7:], fps=float(fps))
    return np.concatenate([root_lin_vel, root_ang_vel, joint_vel], axis=1)


def _recompute_linear_velocity(position: np.ndarray, *, fps: float) -> np.ndarray:
    pos = np.asarray(position, dtype=np.float64)
    vel = np.zeros_like(pos, dtype=np.float64)
    if pos.shape[0] <= 1:
        return vel
    dt = 1.0 / float(fps)
    vel[1:-1] = (pos[2:] - pos[:-2]) / (2.0 * dt)
    vel[0] = (pos[1] - pos[0]) / dt
    vel[-1] = (pos[-1] - pos[-2]) / dt
    return vel


def _recompute_body_angular_velocity(quat_wxyz: np.ndarray, *, fps: float) -> np.ndarray:
    quat = _normalize_quat_wxyz(np.asarray(quat_wxyz, dtype=np.float64))
    if quat.ndim != 3 or quat.shape[2] != 4:
        raise ValueError(f"body_quat_w must have shape [T, B, 4], got {quat.shape}")
    out = np.zeros(quat.shape[:2] + (3,), dtype=np.float64)
    if quat.shape[0] <= 1:
        return out
    dt = 1.0 / float(fps)
    out[0] = _relative_quat_to_angular_velocity(_quat_mul_wxyz(quat[1], _quat_conj_wxyz(quat[0])), dt)
    out[-1] = _relative_quat_to_angular_velocity(_quat_mul_wxyz(quat[-1], _quat_conj_wxyz(quat[-2])), dt)
    if quat.shape[0] > 2:
        rel = _quat_mul_wxyz(quat[2:], _quat_conj_wxyz(quat[:-2]))
        out[1:-1] = _relative_quat_to_angular_velocity(rel, 2.0 * dt)
    return out


def _relative_quat_to_angular_velocity(delta_quat: np.ndarray, dt: float) -> np.ndarray:
    dq = _normalize_quat_wxyz(np.asarray(delta_quat, dtype=np.float64))
    dq = np.where(dq[..., :1] < 0.0, -dq, dq)
    vec = dq[..., 1:4]
    vec_norm = np.linalg.norm(vec, axis=-1, keepdims=True)
    angle = 2.0 * np.arctan2(vec_norm, np.clip(dq[..., :1], -1.0, 1.0))
    axis = np.divide(vec, vec_norm, out=np.zeros_like(vec), where=vec_norm > 1.0e-12)
    rotvec = np.where(vec_norm > 1.0e-12, axis * angle, 2.0 * vec)
    return rotvec / float(dt)


def _normalize_quat_wxyz(quat: np.ndarray) -> np.ndarray:
    q = np.asarray(quat, dtype=np.float64).copy()
    norm = np.linalg.norm(q, axis=-1, keepdims=True)
    norm = np.where(norm > 1.0e-12, norm, 1.0)
    return q / norm


def _quat_conj_wxyz(quat: np.ndarray) -> np.ndarray:
    q = np.asarray(quat, dtype=np.float64).copy()
    q[..., 1:4] *= -1.0
    return q


def _quat_mul_wxyz(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aw, ax, ay, az = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    bw, bx, by, bz = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return _normalize_quat_wxyz(
        np.stack(
            [
                aw * bw - ax * bx - ay * by - az * bz,
                aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
            ],
            axis=-1,
        )
    )
