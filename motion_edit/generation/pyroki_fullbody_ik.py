"""PyRoki fullbody IK backend for contact-Laplacian task-space motions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


DEFAULT_ROBOT_URDF = Path(
    "/home/xiaz/holosoma_isaaclab3_newton/OmniRetarget_Dataset/models/g1/g1_29dof_spherehand.urdf"
)

TARGET_LINK_ALIASES: dict[str, tuple[str, ...]] = {
    "pelvis": ("pelvis",),
    "torso": ("torso_link",),
    "left_foot": ("left_ankle_roll_link", "left_ankle_roll_sphere_1_link"),
    "right_foot": ("right_ankle_roll_link", "right_ankle_roll_sphere_1_link"),
    "left_hand": ("left_sphere_hand_tip_link", "left_sphere_hand_link", "left_wrist_yaw_link"),
    "right_hand": ("right_sphere_hand_tip_link", "right_sphere_hand_link", "right_wrist_yaw_link"),
}

TARGET_WEIGHTS: dict[str, float] = {
    "pelvis": 10.0,
    "torso": 4.0,
    "left_foot": 8.0,
    "right_foot": 8.0,
    "left_hand": 5.0,
    "right_hand": 5.0,
}


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


def _resolve_link_indices(link_names: tuple[str, ...], targets: dict[str, np.ndarray]) -> tuple[list[str], np.ndarray, np.ndarray]:
    names: list[str] = []
    indices: list[int] = []
    weights: list[float] = []
    lowered = {name.lower(): index for index, name in enumerate(link_names)}
    for target_name, aliases in TARGET_LINK_ALIASES.items():
        if target_name not in targets:
            continue
        resolved = None
        for alias in aliases:
            if alias in link_names:
                resolved = link_names.index(alias)
                break
            if alias.lower() in lowered:
                resolved = lowered[alias.lower()]
                break
        if resolved is None:
            continue
        names.append(target_name)
        indices.append(int(resolved))
        weights.append(float(TARGET_WEIGHTS[target_name]))
    if not indices:
        raise ValueError("PyRoki IK could not resolve any target links from LTE keypoints")
    return names, np.asarray(indices, dtype=np.int32), np.asarray(weights, dtype=np.float64)


def _source_motion_from_lte(lte: dict[str, Any], explicit: str | Path | None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser()
    if "source_demo" not in lte:
        raise ValueError("LTE keypoint file has no source_demo; pass --source-motion")
    return Path(_decode_scalar(lte["source_demo"])).expanduser()


def _source_qpos(source_motion: dict[str, Any], n_frames: int, actuated_count: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if "joint_pos" not in source_motion:
        raise ValueError("source motion must contain joint_pos for PyRoki IK warm start")
    raw = np.asarray(source_motion["joint_pos"], dtype=np.float64)
    if raw.ndim != 2:
        raise ValueError(f"source joint_pos must have shape [T,Q], got {raw.shape}")
    count = min(n_frames, raw.shape[0])
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
    names = _motion_strings(source_motion, ("joint_names", "dof_names", "joint_name", "dof_name"))
    return root, cfg, names


def _fps_from_motion(source_motion: dict[str, Any]) -> float:
    if "fps" in source_motion:
        return float(np.asarray(source_motion["fps"]).reshape(-1)[0])
    if "dt" in source_motion:
        dt = float(np.asarray(source_motion["dt"]).reshape(-1)[0])
        if dt > 0.0:
            return 1.0 / dt
    return 50.0


def _linear_velocity(qpos: np.ndarray, fps: float) -> np.ndarray:
    if qpos.shape[0] <= 1:
        return np.zeros_like(qpos)
    dt = 1.0 / float(fps)
    vel = np.zeros_like(qpos, dtype=np.float64)
    vel[1:-1] = (qpos[2:] - qpos[:-2]) / (2.0 * dt)
    vel[0] = (qpos[1] - qpos[0]) / dt
    vel[-1] = (qpos[-1] - qpos[-2]) / dt
    return vel


def _quat_wxyz_to_rotation(quat: np.ndarray) -> Rotation:
    q = np.asarray(quat, dtype=np.float64).reshape(4)
    norm = np.linalg.norm(q)
    if norm <= 1.0e-12:
        q = np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    else:
        q = q / norm
    return Rotation.from_quat([q[1], q[2], q[3], q[0]])


def solve_pyroki_fullbody_ik(
    *,
    lte_path: str | Path,
    output_path: str | Path,
    robot_urdf: str | Path = DEFAULT_ROBOT_URDF,
    source_motion_path: str | Path | None = None,
    max_nfev: int = 25,
    q_prior_weight: float = 0.25,
    q_smooth_weight: float = 0.5,
) -> Path:
    import jax
    import jax.numpy as jnp
    import pyroki
    import yourdfpy

    lte = _load_npz(lte_path)
    targets = {name: np.asarray(lte[name], dtype=np.float64) for name in TARGET_LINK_ALIASES if name in lte}
    if "root" in lte and "pelvis" not in targets:
        targets["pelvis"] = np.asarray(lte["root"], dtype=np.float64)
    if not targets:
        raise ValueError(f"{lte_path} has no supported PyRoki IK keypoints")
    n_frames = min(arr.shape[0] for arr in targets.values())

    robot_path = Path(robot_urdf).expanduser()
    if not robot_path.exists():
        raise FileNotFoundError(f"robot URDF not found for PyRoki IK: {robot_path}")
    urdf = yourdfpy.URDF.load(str(robot_path), load_meshes=False)
    robot = pyroki.Robot.from_urdf(urdf)
    actuated_count = int(robot.joints.num_actuated_joints)
    target_names, link_indices, target_weights = _resolve_link_indices(robot.links.names, targets)

    source_path = _source_motion_from_lte(lte, source_motion_path)
    source_motion = _load_npz(source_path)
    root_source, cfg_source, source_joint_names = _source_qpos(source_motion, n_frames, actuated_count)
    n_frames = min(n_frames, cfg_source.shape[0])
    root_source = root_source[:n_frames]
    cfg_source = cfg_source[:n_frames]

    lower = np.asarray(robot.joints.lower_limits, dtype=np.float64)
    upper = np.asarray(robot.joints.upper_limits, dtype=np.float64)
    finite = np.isfinite(lower) & np.isfinite(upper)
    lower = np.where(finite, lower, -np.pi)
    upper = np.where(finite, upper, np.pi)
    cfg_source = np.clip(cfg_source, lower, upper)

    link_indices_jax = jnp.asarray(link_indices, dtype=jnp.int32)
    weights_jax = jnp.asarray(target_weights, dtype=jnp.float32)

    def residual_jax(q_cfg: Any, target_pos_base: Any, q_prior: Any, q_prev: Any) -> Any:
        fk = robot.forward_kinematics(q_cfg)
        pos = fk[link_indices_jax, 4:7]
        pos_res = ((pos - target_pos_base) * weights_jax[:, None]).reshape(-1)
        prior_res = (q_cfg - q_prior) * float(q_prior_weight)
        smooth_res = (q_cfg - q_prev) * float(q_smooth_weight)
        return jnp.concatenate([pos_res, prior_res, smooth_res], axis=0)

    residual_compiled = jax.jit(residual_jax)
    jac_compiled = jax.jit(jax.jacfwd(residual_jax, argnums=0))

    out_cfg = np.zeros((n_frames, actuated_count), dtype=np.float64)
    q_prev = cfg_source[0]
    for frame in range(n_frames):
        root = root_source[frame].copy()
        if "pelvis" in targets:
            root[:3] = np.asarray(targets["pelvis"][frame], dtype=np.float64)
        root_rot = _quat_wxyz_to_rotation(root[3:7])
        target_world = np.stack([targets[name][frame] for name in target_names], axis=0)
        target_base = root_rot.inv().apply(target_world - root[:3][None, :])
        q_prior = cfg_source[frame]
        x0 = np.clip(q_prev if frame > 0 else q_prior, lower, upper)

        def fun(x: np.ndarray) -> np.ndarray:
            return np.asarray(residual_compiled(jnp.asarray(x), jnp.asarray(target_base), jnp.asarray(q_prior), jnp.asarray(q_prev)))

        def jac(x: np.ndarray) -> np.ndarray:
            return np.asarray(jac_compiled(jnp.asarray(x), jnp.asarray(target_base), jnp.asarray(q_prior), jnp.asarray(q_prev)))

        result = least_squares(fun, x0, jac=jac, bounds=(lower, upper), max_nfev=int(max_nfev), xtol=1.0e-5, ftol=1.0e-5, gtol=1.0e-5)
        q_prev = np.clip(result.x, lower, upper)
        out_cfg[frame] = q_prev
        root_source[frame] = root

    qpos = np.concatenate([root_source[:n_frames], out_cfg], axis=1)
    fps = _fps_from_motion(source_motion)
    qvel = _linear_velocity(qpos, fps)
    output = Path(output_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output,
        joint_pos=qpos.astype(np.float32),
        joint_vel=qvel.astype(np.float32),
        joint_names=np.asarray(tuple(robot.joints.actuated_names), dtype=object),
        source_joint_names=np.asarray(source_joint_names, dtype=object),
        is_qpos=np.asarray(True),
        ik_backend=np.asarray("pyroki_internal"),
        robot_urdf=np.asarray(str(robot_path)),
        target_names=np.asarray(target_names, dtype=object),
        source_motion=np.asarray(str(source_path)),
        fps=np.asarray(fps),
    )
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Solve fullbody IK for motion_edit LTE keypoints with PyRoki.")
    parser.add_argument("--lte", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--robot-urdf", default=str(DEFAULT_ROBOT_URDF))
    parser.add_argument("--source-motion", default=None)
    parser.add_argument("--max-nfev", type=int, default=25)
    parser.add_argument("--q-prior-weight", type=float, default=0.25)
    parser.add_argument("--q-smooth-weight", type=float, default=0.5)
    parser.add_argument("--foot-orientation-weight", type=float, default=20.0)
    parser.add_argument("--contact-foot-orientation-weight", type=float, default=80.0)
    parser.add_argument("--foot-toe-weight", type=float, default=20.0)
    parser.add_argument("--contact-foot-toe-weight", type=float, default=120.0)
    args = parser.parse_args(argv)
    solve_pyroki_fullbody_ik(
        lte_path=args.lte,
        output_path=args.out,
        robot_urdf=args.robot_urdf,
        source_motion_path=args.source_motion,
        max_nfev=args.max_nfev,
        q_prior_weight=args.q_prior_weight,
        q_smooth_weight=args.q_smooth_weight,
    )


if __name__ == "__main__":
    main()
