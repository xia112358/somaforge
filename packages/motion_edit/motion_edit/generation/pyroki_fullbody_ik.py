"""PyRoki trajectory IK for contact-aware task-space motions.

This backend is deliberately kinematic. Newton/MJWarp remains the authority for
collision and contact validation. The output is a PyRoki-FK-consistent preview
trajectory that must be Newton-canonicalized before training use.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from somaforge_core.robot_assets import canonical_g1_urdf_path

from motion_edit.generation.pyroki_taskspace import (
    CompiledPyrokiTaskspace,
    SEMANTIC_DEFAULT_WEIGHTS,
    SEMANTIC_LINK_ALIASES,
    compile_pyroki_taskspace,
    holosoma_body_velocities,
    holosoma_joint_velocities,
    normalize_quat_wxyz,
    quat_apply_wxyz,
    resolve_link_index,
    world_body_poses_from_pyroki_fk,
)
from motion_edit.generation.taskspace_spec import ContactAwareTaskspaceMotion


DEFAULT_ROBOT_URDF = canonical_g1_urdf_path()
TARGET_LINK_ALIASES = SEMANTIC_LINK_ALIASES
TARGET_WEIGHTS = SEMANTIC_DEFAULT_WEIGHTS
SOURCE_FOOT_ORIENTATION_LINKS = (
    ("left_ankle_roll_link", "left_ankle_roll_sphere_1_link"),
    ("right_ankle_roll_link", "right_ankle_roll_sphere_1_link"),
)


def _load_npz(path: str | Path) -> dict[str, Any]:
    with np.load(Path(path).expanduser(), allow_pickle=True) as data:
        return {key: data[key] for key in data.files}


def _decode_scalar(value: Any) -> str:
    arr = np.asarray(value, dtype=object)
    raw = arr.item() if arr.ndim == 0 else arr.reshape(-1)[0]
    if isinstance(raw, bytes):
        return raw.decode("utf-8")
    return str(raw)


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
                        return [str(item) for item in parsed]
                except json.JSONDecodeError:
                    return [item.strip() for item in raw.split(",") if item.strip()]
            if isinstance(raw, (list, tuple)):
                return [str(item) for item in raw]
            return [str(raw)]
        return [str(item) for item in arr.reshape(-1).tolist()]
    return []


def _source_motion_from_lte(lte: dict[str, Any], explicit: str | Path | None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser()
    if "source_demo" not in lte:
        raise ValueError("legacy LTE keypoint file has no source_demo; pass --source-motion")
    return Path(_decode_scalar(lte["source_demo"])).expanduser()


def _source_qpos_from_array(raw_value: Any, n_frames: int, actuated_count: int) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(raw_value, dtype=np.float64)
    if raw.ndim != 2:
        raise ValueError(f"source joint_pos must have shape [T,Q], got {raw.shape}")
    count = min(int(n_frames), raw.shape[0])
    if raw.shape[1] >= 7 + actuated_count:
        root = raw[:count, :7].copy()
        cfg = raw[:count, 7 : 7 + actuated_count].copy()
    elif raw.shape[1] == actuated_count:
        root = np.zeros((count, 7), dtype=np.float64)
        root[:, 3] = 1.0
        cfg = raw[:count, :actuated_count].copy()
    else:
        raise ValueError(
            f"source joint_pos has {raw.shape[1]} columns; expected {actuated_count} or at least {7 + actuated_count}"
        )
    root[:, 3:7] = normalize_quat_wxyz(root[:, 3:7])
    return root, cfg


def _align_source_cfg(
    cfg: np.ndarray,
    source_joint_names: list[str],
    robot_joint_names: tuple[str, ...],
) -> np.ndarray:
    if not source_joint_names:
        return cfg
    if source_joint_names == list(robot_joint_names):
        return cfg
    if all(name in source_joint_names for name in robot_joint_names):
        indices = [source_joint_names.index(name) for name in robot_joint_names]
        return cfg[:, indices]
    missing = [name for name in robot_joint_names if name not in source_joint_names]
    raise ValueError(f"source motion is missing PyRoki actuated joints: {missing}")


def _fps_from_motion(source_motion: dict[str, Any]) -> float:
    if "fps" in source_motion:
        return float(np.asarray(source_motion["fps"]).reshape(-1)[0])
    if "dt" in source_motion:
        dt = float(np.asarray(source_motion["dt"]).reshape(-1)[0])
        if dt > 0.0:
            return 1.0 / dt
    return 50.0


def _quat_wxyz_to_rotation(quat: np.ndarray) -> Rotation:
    q = normalize_quat_wxyz(np.asarray(quat, dtype=np.float64).reshape(4))
    return Rotation.from_quat([q[1], q[2], q[3], q[0]])


def _legacy_compiled_taskspace(lte: dict[str, Any], link_names: tuple[str, ...]) -> CompiledPyrokiTaskspace:
    targets = {name: np.asarray(lte[name], dtype=np.float64) for name in TARGET_LINK_ALIASES if name in lte}
    if "root" in lte and "pelvis" not in targets:
        targets["pelvis"] = np.asarray(lte["root"], dtype=np.float64)
    if not targets:
        raise ValueError("legacy LTE input has no supported PyRoki keypoints")
    n_frames = min(value.shape[0] for value in targets.values())
    names: list[str] = []
    indices: list[int] = []
    values: list[np.ndarray] = []
    unresolved: list[str] = []
    for name, target in targets.items():
        link_index = resolve_link_index(link_names, name, TARGET_LINK_ALIASES.get(name, (name,)))
        if link_index is None:
            unresolved.append(name)
            continue
        names.append(name)
        indices.append(link_index)
        values.append(target[:n_frames])
    if not indices:
        raise ValueError("PyRoki IK could not resolve any legacy target links")
    semantic_targets = np.stack(values, axis=1)
    semantic_weights = np.broadcast_to(
        np.asarray([TARGET_WEIGHTS.get(name, 1.0) for name in names], dtype=np.float64)[None, :],
        (n_frames, len(names)),
    ).copy()
    compiled = CompiledPyrokiTaskspace(
        semantic_names=tuple(names),
        semantic_link_indices=np.asarray(indices, dtype=np.int32),
        semantic_targets_w=semantic_targets,
        semantic_weights=semantic_weights,
        contact_link_indices=np.zeros((n_frames, 1), dtype=np.int32),
        contact_points_local=np.zeros((n_frames, 1, 3), dtype=np.float64),
        contact_targets_w=np.zeros((n_frames, 1, 3), dtype=np.float64),
        contact_weights=np.zeros((n_frames, 1), dtype=np.float64),
        unresolved_semantics=tuple(unresolved),
        unresolved_contacts=(),
    )
    compiled.validate()
    return compiled


def _input_problem(
    payload: dict[str, Any],
    *,
    link_names: tuple[str, ...],
    actuated_count: int,
    robot_joint_names: tuple[str, ...],
    source_motion_path: str | Path | None,
    edited_contact_weight: float,
    fixed_contact_weight: float,
    contact_ramp_frames: int,
) -> tuple[
    CompiledPyrokiTaskspace,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
    list[str],
    str | None,
    str,
]:
    if "contact_aware_taskspace_json" in payload:
        spec = ContactAwareTaskspaceMotion.from_arrays(payload)
        compiled = compile_pyroki_taskspace(
            spec,
            link_names,
            edited_contact_weight=edited_contact_weight,
            fixed_contact_weight=fixed_contact_weight,
            contact_ramp_frames=contact_ramp_frames,
        )
        root_source, cfg_source = _source_qpos_from_array(spec.source_qpos, spec.frame_count, actuated_count)
        source_names: list[str] = []
        source_path: str | None = None
        if source_motion_path is not None:
            source_path_obj = Path(source_motion_path).expanduser()
            source_motion = _load_npz(source_path_obj)
            source_names = _motion_strings(source_motion, ("joint_names", "dof_names", "joint_name", "dof_name"))
            source_path = str(source_path_obj)
        cfg_source = _align_source_cfg(cfg_source, source_names, robot_joint_names)
        source_reference = np.asarray(spec.source_reference_weights, dtype=np.float64)[:, 7 : 7 + actuated_count]
        boundary = np.asarray(spec.boundary_weights, dtype=np.float64)
        return (
            compiled,
            root_source,
            cfg_source,
            source_reference,
            boundary,
            float(spec.fps),
            source_names,
            source_path,
            "contact_aware_taskspace_motion_v1",
        )

    compiled = _legacy_compiled_taskspace(payload, link_names)
    source_path_obj = _source_motion_from_lte(payload, source_motion_path)
    source_motion = _load_npz(source_path_obj)
    source_names = _motion_strings(source_motion, ("joint_names", "dof_names", "joint_name", "dof_name"))
    root_source, cfg_source = _source_qpos_from_array(source_motion["joint_pos"], compiled.frame_count, actuated_count)
    cfg_source = _align_source_cfg(cfg_source, source_names, robot_joint_names)
    source_reference = np.ones_like(cfg_source, dtype=np.float64)
    boundary = np.zeros(cfg_source.shape[0], dtype=np.float64)
    return (
        compiled,
        root_source,
        cfg_source,
        source_reference,
        boundary,
        _fps_from_motion(source_motion),
        source_names,
        str(source_path_obj),
        "legacy_lte_keypoints",
    )


def _stats(values: np.ndarray) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size == 0:
        return {"mean": 0.0, "max": 0.0, "rms": 0.0}
    return {
        "mean": float(np.mean(array)),
        "max": float(np.max(array)),
        "rms": float(np.sqrt(np.mean(array * array))),
    }


def solve_pyroki_fullbody_ik(
    *,
    lte_path: str | Path,
    output_path: str | Path,
    robot_urdf: str | Path = DEFAULT_ROBOT_URDF,
    source_motion_path: str | Path | None = None,
    max_nfev: int = 25,
    q_prior_weight: float = 0.25,
    q_smooth_weight: float = 0.5,
    boundary_pin_weight: float = 2.0,
    edited_contact_weight: float = 100.0,
    fixed_contact_weight: float = 80.0,
    contact_ramp_frames: int = 2,
    foot_orientation_weight: float = 20.0,
    q_velocity_weight: float = 2.0,
    q_acceleration_weight: float = 1.0,
) -> Path:
    import jax
    import jax.numpy as jnp
    import pyroki
    import yourdfpy

    payload = _load_npz(lte_path)
    robot_path = Path(robot_urdf).expanduser()
    if not robot_path.exists():
        raise FileNotFoundError(f"robot URDF not found for PyRoki IK: {robot_path}")
    urdf = yourdfpy.URDF.load(str(robot_path), load_meshes=False)
    robot = pyroki.Robot.from_urdf(urdf)
    robot_joint_names = tuple(str(name) for name in robot.joints.actuated_names)
    link_names = tuple(str(name) for name in robot.links.names)
    actuated_count = int(robot.joints.num_actuated_joints)

    (
        compiled,
        root_source,
        cfg_source,
        source_reference,
        boundary_weights,
        fps,
        source_joint_names,
        source_path,
        input_schema,
    ) = _input_problem(
        payload,
        link_names=link_names,
        actuated_count=actuated_count,
        robot_joint_names=robot_joint_names,
        source_motion_path=source_motion_path,
        edited_contact_weight=edited_contact_weight,
        fixed_contact_weight=fixed_contact_weight,
        contact_ramp_frames=contact_ramp_frames,
    )
    n_frames = min(compiled.frame_count, cfg_source.shape[0])
    root_source = root_source[:n_frames].copy()
    cfg_source = cfg_source[:n_frames].copy()
    source_reference = source_reference[:n_frames]
    boundary_weights = boundary_weights[:n_frames]

    pelvis_column = compiled.semantic_names.index("pelvis") if "pelvis" in compiled.semantic_names else None
    if pelvis_column is not None:
        root_source[:, :3] = compiled.semantic_targets_w[:n_frames, pelvis_column]

    lower = np.asarray(robot.joints.lower_limits, dtype=np.float64)
    upper = np.asarray(robot.joints.upper_limits, dtype=np.float64)
    finite = np.isfinite(lower) & np.isfinite(upper)
    lower = np.where(finite, lower, -np.pi)
    upper = np.where(finite, upper, np.pi)
    cfg_source = np.clip(cfg_source, lower, upper)

    semantic_indices_jax = jnp.asarray(compiled.semantic_link_indices, dtype=jnp.int32)
    source_fk = np.asarray(robot.forward_kinematics(jnp.asarray(cfg_source)), dtype=np.float64)
    foot_orientation_indices = tuple(
        index
        for aliases in SOURCE_FOOT_ORIENTATION_LINKS
        if (index := resolve_link_index(link_names, aliases[0], aliases)) is not None
    )
    foot_orientation_indices_jax = jnp.asarray(foot_orientation_indices, dtype=jnp.int32)
    source_foot_orientations = source_fk[:, foot_orientation_indices, :4]

    def quat_apply_jax(quat: Any, vector: Any) -> Any:
        qvec = quat[..., 1:4]
        uv = jnp.cross(qvec, vector)
        uuv = jnp.cross(qvec, uv)
        return vector + 2.0 * (quat[..., :1] * uv + uuv)

    def residual_jax(
        q_cfg: Any,
        semantic_target_base: Any,
        semantic_sqrt_weight: Any,
        contact_link_indices: Any,
        contact_points_local: Any,
        contact_target_base: Any,
        contact_sqrt_weight: Any,
        q_prior: Any,
        q_previous: Any,
        q_previous_previous: Any,
        q_prior_previous: Any,
        q_prior_previous_previous: Any,
        q_prior_scale: Any,
        source_foot_orientation: Any,
    ) -> Any:
        fk = robot.forward_kinematics(q_cfg)
        semantic_pos = fk[semantic_indices_jax, 4:7]
        semantic_res = ((semantic_pos - semantic_target_base) * semantic_sqrt_weight[:, None]).reshape(-1)

        contact_pose = fk[contact_link_indices]
        contact_pred = contact_pose[:, 4:7] + quat_apply_jax(contact_pose[:, :4], contact_points_local)
        contact_res = ((contact_pred - contact_target_base) * contact_sqrt_weight[:, None]).reshape(-1)

        prior_res = (q_cfg - q_prior) * q_prior_scale
        smooth_res = (q_cfg - q_previous) * float(q_smooth_weight)
        velocity_res = (
            (q_cfg - q_previous) - (q_prior - q_prior_previous)
        ) * float(q_velocity_weight)
        acceleration_res = (
            (q_cfg - 2.0 * q_previous + q_previous_previous)
            - (q_prior - 2.0 * q_prior_previous + q_prior_previous_previous)
        ) * float(q_acceleration_weight)

        foot_pose = fk[foot_orientation_indices_jax]
        foot_quat = foot_pose[:, :4]
        target_conjugate = source_foot_orientation.at[:, 1:4].multiply(-1.0)
        aw, ax, ay, az = jnp.moveaxis(target_conjugate, -1, 0)
        bw, bx, by, bz = jnp.moveaxis(foot_quat, -1, 0)
        relative = jnp.stack(
            (
                aw * bw - ax * bx - ay * by - az * bz,
                aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
            ),
            axis=-1,
        )
        relative = jnp.where(relative[:, :1] < 0.0, -relative, relative)
        foot_orientation_res = (
            2.0 * relative[:, 1:4] * jnp.sqrt(float(foot_orientation_weight))
        ).reshape(-1)
        return jnp.concatenate(
            [
                semantic_res,
                contact_res,
                prior_res,
                smooth_res,
                velocity_res,
                acceleration_res,
                foot_orientation_res,
            ],
            axis=0,
        )

    residual_compiled = jax.jit(residual_jax)
    jac_compiled = jax.jit(jax.jacfwd(residual_jax, argnums=0))

    out_cfg = np.zeros((n_frames, actuated_count), dtype=np.float64)
    q_previous = cfg_source[0]
    q_previous_previous = cfg_source[0]
    success: list[bool] = []
    nfev: list[int] = []
    costs: list[float] = []
    for frame in range(n_frames):
        root = root_source[frame].copy()
        root_rotation = _quat_wxyz_to_rotation(root[3:7])
        semantic_target_base = root_rotation.inv().apply(
            compiled.semantic_targets_w[frame] - root[:3][None, :]
        )
        contact_target_base = root_rotation.inv().apply(
            compiled.contact_targets_w[frame] - root[:3][None, :]
        )
        semantic_sqrt_weight = np.sqrt(np.maximum(compiled.semantic_weights[frame], 0.0))
        contact_sqrt_weight = np.sqrt(np.maximum(compiled.contact_weights[frame], 0.0))
        prior_scale = (
            float(q_prior_weight) * np.maximum(source_reference[frame], 0.0)
            + float(boundary_pin_weight) * float(boundary_weights[frame])
        )
        q_prior = cfg_source[frame]
        q_prior_previous = cfg_source[max(frame - 1, 0)]
        q_prior_previous_previous = cfg_source[max(frame - 2, 0)]
        x0 = np.clip(q_previous if frame > 0 else q_prior, lower, upper)

        args = (
            np.asarray(semantic_target_base, dtype=np.float64),
            np.asarray(semantic_sqrt_weight, dtype=np.float64),
            np.asarray(compiled.contact_link_indices[frame], dtype=np.int32),
            np.asarray(compiled.contact_points_local[frame], dtype=np.float64),
            np.asarray(contact_target_base, dtype=np.float64),
            np.asarray(contact_sqrt_weight, dtype=np.float64),
            np.asarray(q_prior, dtype=np.float64),
            np.asarray(q_previous, dtype=np.float64),
            np.asarray(q_previous_previous, dtype=np.float64),
            np.asarray(q_prior_previous, dtype=np.float64),
            np.asarray(q_prior_previous_previous, dtype=np.float64),
            np.asarray(prior_scale, dtype=np.float64),
            np.asarray(source_foot_orientations[frame], dtype=np.float64),
        )

        def fun(x: np.ndarray) -> np.ndarray:
            return np.asarray(residual_compiled(jnp.asarray(x), *(jnp.asarray(value) for value in args)))

        def jac(x: np.ndarray) -> np.ndarray:
            return np.asarray(jac_compiled(jnp.asarray(x), *(jnp.asarray(value) for value in args)))

        result = least_squares(
            fun,
            x0,
            jac=jac,
            bounds=(lower, upper),
            max_nfev=int(max_nfev),
            xtol=1.0e-5,
            ftol=1.0e-5,
            gtol=1.0e-5,
        )
        q_previous_previous = q_previous
        q_previous = np.clip(result.x, lower, upper)
        out_cfg[frame] = q_previous
        success.append(bool(result.success))
        nfev.append(int(result.nfev))
        costs.append(float(result.cost))

    qpos = np.concatenate([root_source[:n_frames], out_cfg], axis=1)
    qpos[:, 3:7] = normalize_quat_wxyz(qpos[:, 3:7])
    qvel = holosoma_joint_velocities(qpos, fps)

    fk_base = np.asarray(robot.forward_kinematics(jnp.asarray(out_cfg)), dtype=np.float64)
    body_pos_w, body_quat_w = world_body_poses_from_pyroki_fk(root_source[:n_frames], fk_base)
    body_lin_vel_w, body_ang_vel_w = holosoma_body_velocities(body_pos_w, body_quat_w, fps)

    semantic_pred = body_pos_w[:, compiled.semantic_link_indices]
    semantic_error = np.linalg.norm(
        semantic_pred - compiled.semantic_targets_w[:n_frames], axis=-1
    )
    contact_pose_pos = body_pos_w[
        np.arange(n_frames)[:, None], compiled.contact_link_indices[:n_frames]
    ]
    contact_pose_quat = body_quat_w[
        np.arange(n_frames)[:, None], compiled.contact_link_indices[:n_frames]
    ]
    contact_pred = contact_pose_pos + quat_apply_wxyz(
        contact_pose_quat, compiled.contact_points_local[:n_frames]
    )
    contact_error_all = np.linalg.norm(
        contact_pred - compiled.contact_targets_w[:n_frames], axis=-1
    )
    contact_mask = compiled.contact_weights[:n_frames] > 0.0
    contact_error = contact_error_all[contact_mask]

    pelvis_index = resolve_link_index(link_names, "pelvis", ("pelvis",))
    root_position_error = 0.0
    root_quaternion_error = 0.0
    if pelvis_index is not None:
        root_position_error = float(np.max(np.abs(body_pos_w[:, pelvis_index] - qpos[:, :3])))
        quat_delta = np.minimum(
            np.max(np.abs(body_quat_w[:, pelvis_index] - qpos[:, 3:7]), axis=-1),
            np.max(np.abs(body_quat_w[:, pelvis_index] + qpos[:, 3:7]), axis=-1),
        )
        root_quaternion_error = float(np.max(quat_delta))

    diagnostics = {
        "input_schema": input_schema,
        "frame_count": int(n_frames),
        "semantic_names": list(compiled.semantic_names),
        "semantic_target_error_m": _stats(semantic_error),
        "contact_target_error_m": _stats(contact_error),
        "active_contact_point_samples": int(np.count_nonzero(contact_mask)),
        "unresolved_semantics": list(compiled.unresolved_semantics),
        "unresolved_contacts": list(compiled.unresolved_contacts),
        "least_squares_success_count": int(sum(success)),
        "least_squares_failure_count": int(len(success) - sum(success)),
        "least_squares_nfev": _stats(np.asarray(nfev, dtype=np.float64)),
        "least_squares_cost": _stats(np.asarray(costs, dtype=np.float64)),
        "contact_ramp_frames": int(contact_ramp_frames),
        "source_foot_orientation_weight": float(foot_orientation_weight),
        "source_foot_orientation_link_count": len(foot_orientation_indices),
        "source_velocity_weight": float(q_velocity_weight),
        "source_acceleration_weight": float(q_acceleration_weight),
        "root_body_position_error_max_m": root_position_error,
        "root_body_quaternion_error_max": root_quaternion_error,
        "newton_canonicalization_required": True,
    }

    output = Path(output_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        fps=np.asarray(float(fps)),
        joint_pos=qpos.astype(np.float32),
        joint_vel=qvel.astype(np.float32),
        joint_names=np.asarray(robot_joint_names, dtype=object),
        source_joint_names=np.asarray(source_joint_names, dtype=object),
        body_names=np.asarray(link_names, dtype=object),
        body_pos_w=body_pos_w.astype(np.float32),
        body_quat_w=body_quat_w.astype(np.float32),
        body_lin_vel_w=body_lin_vel_w.astype(np.float32),
        body_ang_vel_w=body_ang_vel_w.astype(np.float32),
        is_qpos=np.asarray(True),
        ik_backend=np.asarray("pyroki_contact_aware_taskspace"),
        kinematics_backend=np.asarray("pyroki_urdf_fk_preview"),
        newton_canonicalization_required=np.asarray(True),
        robot_urdf=np.asarray(str(robot_path)),
        target_names=np.asarray(compiled.semantic_names, dtype=object),
        source_motion=np.asarray(source_path or ""),
        taskspace_input=np.asarray(str(Path(lte_path).expanduser())),
        ik_diagnostics_json=np.asarray(json.dumps(diagnostics, sort_keys=True), dtype=object),
    )
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Solve contact-aware fullbody trajectory IK with PyRoki.")
    parser.add_argument("--lte", default=None, help="Legacy LTE keypoints or ContactAwareTaskspaceMotion NPZ.")
    parser.add_argument("--taskspace-spec", default=None, help="Explicit ContactAwareTaskspaceMotion NPZ.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--robot-urdf", default=str(DEFAULT_ROBOT_URDF))
    parser.add_argument("--source-motion", default=None)
    parser.add_argument("--max-nfev", type=int, default=25)
    parser.add_argument("--q-prior-weight", type=float, default=0.25)
    parser.add_argument("--q-smooth-weight", type=float, default=0.5)
    parser.add_argument("--boundary-pin-weight", type=float, default=2.0)
    parser.add_argument("--edited-contact-weight", type=float, default=100.0)
    parser.add_argument("--fixed-contact-weight", type=float, default=80.0)
    parser.add_argument("--contact-ramp-frames", type=int, default=2)
    parser.add_argument("--foot-orientation-weight", type=float, default=20.0)
    parser.add_argument("--q-velocity-weight", type=float, default=2.0)
    parser.add_argument("--q-acceleration-weight", type=float, default=1.0)
    # Compatibility arguments retained for existing callers. Contact patch points
    # replace the old contact-only toe/orientation pseudo-targets.
    parser.add_argument("--contact-foot-orientation-weight", type=float, default=80.0)
    parser.add_argument("--foot-toe-weight", type=float, default=20.0)
    parser.add_argument("--contact-foot-toe-weight", type=float, default=120.0)
    args = parser.parse_args(argv)
    input_path = args.taskspace_spec or args.lte
    if input_path is None:
        parser.error("one of --lte or --taskspace-spec is required")
    solve_pyroki_fullbody_ik(
        lte_path=input_path,
        output_path=args.out,
        robot_urdf=args.robot_urdf,
        source_motion_path=args.source_motion,
        max_nfev=args.max_nfev,
        q_prior_weight=args.q_prior_weight,
        q_smooth_weight=args.q_smooth_weight,
        boundary_pin_weight=args.boundary_pin_weight,
        edited_contact_weight=args.edited_contact_weight,
        fixed_contact_weight=args.fixed_contact_weight,
        contact_ramp_frames=args.contact_ramp_frames,
        foot_orientation_weight=args.foot_orientation_weight,
        q_velocity_weight=args.q_velocity_weight,
        q_acceleration_weight=args.q_acceleration_weight,
    )


if __name__ == "__main__":
    main()
