"""Whole-trajectory PyRoki/JAXLS optimizer with three objective families."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from motion_edit.contact_laplacian.omniretarget_mesh import build_omniretarget_interaction_mesh


@dataclass(frozen=True)
class WholeTrajectoryConfig:
    contact_laplacian_weight: float = 10.0
    taskspace_tracking_weight: float = 20.0
    environment_anchor_tolerance_m: float = 5.0e-4
    contact_sticking_weight: float = 20.0
    joint_limit_weight: float = 10.0
    pose_prior_weight: float = 0.25
    temporal_laplacian_weight: float = 2.0
    contact_force_weight: float = 5.0
    contact_force_position_scale_m: float = 1.0e-3
    max_iterations: int = 40
    linear_solver: str = "conjugate_gradient"

    def validate(self) -> None:
        if self.contact_laplacian_weight <= 0.0:
            raise ValueError("contact_laplacian_weight must be positive")
        if self.taskspace_tracking_weight < 0.0:
            raise ValueError("taskspace_tracking_weight must be nonnegative")
        if self.contact_sticking_weight < 0.0:
            raise ValueError("contact_sticking_weight must be nonnegative")
        if self.environment_anchor_tolerance_m <= 0.0:
            raise ValueError("environment_anchor_tolerance_m must be positive")
        if self.pose_prior_weight < 0.0:
            raise ValueError("pose_prior_weight must be nonnegative")
        if self.temporal_laplacian_weight <= 0.0:
            raise ValueError("temporal_laplacian_weight must be positive")
        if self.contact_force_weight <= 0.0:
            raise ValueError("contact_force_weight must be positive")
        if self.contact_force_position_scale_m <= 0.0:
            raise ValueError("contact_force_position_scale_m must be positive")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be positive")


@dataclass(frozen=True)
class ForceLinearization:
    target_force_w: np.ndarray
    actual_force_w: np.ndarray
    contact_mask: np.ndarray
    contact_normals_w: np.ndarray
    reference_link_position_w: np.ndarray | None
    target_normal_displacement_m: np.ndarray

    def validate(self, *, frames: int, parts: int) -> None:
        expected_vector = (frames, parts, 3)
        expected_mask = (frames, parts)
        for name in ("target_force_w", "actual_force_w", "contact_normals_w"):
            value = np.asarray(getattr(self, name))
            if value.shape != expected_vector:
                raise ValueError(f"{name} must be {expected_vector}, got {value.shape}")
            if not np.all(np.isfinite(value)):
                raise ValueError(f"{name} contains NaN or Inf")
        if self.reference_link_position_w is None:
            raise ValueError("reference_link_position_w must be resolved before trajectory optimization")
        reference = np.asarray(self.reference_link_position_w)
        if reference.shape != expected_vector:
            raise ValueError(f"reference_link_position_w must be {expected_vector}, got {reference.shape}")
        if not np.all(np.isfinite(reference)):
            raise ValueError("reference_link_position_w contains NaN or Inf")
        if np.asarray(self.contact_mask).shape != expected_mask:
            raise ValueError(f"contact_mask must be {expected_mask}, got {np.asarray(self.contact_mask).shape}")
        displacement = np.asarray(self.target_normal_displacement_m)
        if displacement.shape != expected_mask:
            raise ValueError(f"target_normal_displacement_m must be {expected_mask}, got {displacement.shape}")
        if not np.all(np.isfinite(displacement)):
            raise ValueError("target_normal_displacement_m contains NaN or Inf")
        normal_norm = np.linalg.norm(np.asarray(self.contact_normals_w), axis=2)
        if np.any(normal_norm <= 1.0e-12):
            raise ValueError("contact_normals_w contains a zero normal")


@dataclass(frozen=True)
class EnvironmentContactAnchors:
    """Environment-side contact handles, one per ContactGraph anchor."""

    anchor_ids: tuple[str, ...]
    semantic_names: tuple[str, ...]
    start_frames: np.ndarray
    end_frames: np.ndarray
    representative_frames: np.ndarray
    source_position_w: np.ndarray
    target_position_w: np.ndarray
    edited: np.ndarray
    link_groups: Sequence[np.ndarray]

    def validate(self, *, frames: int) -> None:
        count = len(self.anchor_ids)
        if len(set(self.anchor_ids)) != count:
            raise ValueError("environment contact anchor_ids must be unique")
        if len(self.semantic_names) != count or len(self.link_groups) != count:
            raise ValueError("environment contact anchor metadata length mismatch")
        for name, value in (
            ("start_frames", self.start_frames),
            ("end_frames", self.end_frames),
            ("representative_frames", self.representative_frames),
        ):
            array = np.asarray(value, dtype=np.int64)
            if array.shape != (count,):
                raise ValueError(f"{name} must be {(count,)}, got {array.shape}")
        starts = np.asarray(self.start_frames, dtype=np.int64)
        ends = np.asarray(self.end_frames, dtype=np.int64)
        representative = np.asarray(self.representative_frames, dtype=np.int64)
        if np.any(starts < 0) or np.any(ends > frames) or np.any(ends <= starts):
            raise ValueError("environment contact intervals must be valid half-open trajectory intervals")
        if np.any(representative < starts) or np.any(representative >= ends):
            raise ValueError("environment contact representative frame must lie inside its interval")
        for name, value in (
            ("source_position_w", self.source_position_w),
            ("target_position_w", self.target_position_w),
        ):
            array = np.asarray(value, dtype=np.float64)
            if array.shape != (count, 3):
                raise ValueError(f"{name} must be {(count, 3)}, got {array.shape}")
            if not np.all(np.isfinite(array)):
                raise ValueError(f"{name} contains NaN or Inf")
        if np.asarray(self.edited, dtype=bool).shape != (count,):
            raise ValueError(f"edited must be {(count,)}")
        if any(np.asarray(group, dtype=np.int32).reshape(-1).size == 0 for group in self.link_groups):
            raise ValueError("environment contact link_groups must be non-empty")


@dataclass(frozen=True)
class OrientationTargets:
    link_indices: np.ndarray
    quat_wxyz: np.ndarray
    weights: np.ndarray

    def validate(self, *, frames: int) -> None:
        indices = np.asarray(self.link_indices)
        quaternions = np.asarray(self.quat_wxyz)
        weights = np.asarray(self.weights)
        count = indices.size
        if indices.shape != (count,):
            raise ValueError(f"orientation link_indices must be [O], got {indices.shape}")
        if quaternions.shape != (frames, count, 4):
            raise ValueError(f"orientation quat_wxyz must be {(frames, count, 4)}, got {quaternions.shape}")
        if weights.shape != (frames, count):
            raise ValueError(f"orientation weights must be {(frames, count)}, got {weights.shape}")
        if not np.all(np.isfinite(quaternions)) or not np.all(np.isfinite(weights)):
            raise ValueError("orientation targets contain NaN or Inf")
        if np.any(weights < 0.0):
            raise ValueError("orientation weights must be nonnegative")


@dataclass(frozen=True)
class WholeTrajectoryResult:
    root_qpos: np.ndarray
    joint_cfg: np.ndarray
    force_reference_position_w: np.ndarray
    force_solved_position_w: np.ndarray
    metadata: dict[str, Any]


def solve_whole_trajectory(
    *,
    robot: Any,
    root_qpos_init: np.ndarray,
    joint_cfg_init: np.ndarray,
    target_position_w: np.ndarray,
    target_link_groups: Sequence[np.ndarray],
    target_weights: np.ndarray,
    force_link_groups: Sequence[np.ndarray],
    force_linearization: ForceLinearization,
    environment_contacts: EnvironmentContactAnchors | None = None,
    orientation_targets: OrientationTargets | None = None,
    object_points_w: np.ndarray,
    config: WholeTrajectoryConfig | None = None,
) -> WholeTrajectoryResult:
    """Solve all frames jointly in one sparse JAXLS factor graph.

    The graph intentionally contains exactly three cost factories:
    contact/interaction Laplacian, temporal Laplacian, and contact force.
    """

    import jax
    import jax.numpy as jnp
    import jaxlie
    import jaxls

    cfg = config or WholeTrajectoryConfig()
    cfg.validate()
    root_init = np.asarray(root_qpos_init, dtype=np.float64)
    joint_init = np.asarray(joint_cfg_init, dtype=np.float64)
    targets = np.asarray(target_position_w, dtype=np.float64)
    weights = np.asarray(target_weights, dtype=np.float64)
    if root_init.ndim != 2 or root_init.shape[1] != 7:
        raise ValueError(f"root_qpos_init must be [T,7], got {root_init.shape}")
    frames = root_init.shape[0]
    if joint_init.shape != (frames, int(robot.joints.num_actuated_joints)):
        raise ValueError(
            f"joint_cfg_init must be {(frames, int(robot.joints.num_actuated_joints))}, got {joint_init.shape}"
        )
    robot_parts = len(target_link_groups)
    force_parts = len(force_link_groups)
    if targets.shape != (frames, robot_parts, 3):
        raise ValueError(f"target_position_w must be {(frames, robot_parts, 3)}, got {targets.shape}")
    if weights.shape != (frames, robot_parts):
        raise ValueError(f"target_weights must be {(frames, robot_parts)}, got {weights.shape}")
    force_linearization.validate(frames=frames, parts=force_parts)
    if environment_contacts is not None:
        environment_contacts.validate(frames=frames)
    orientations = orientation_targets or OrientationTargets(
        link_indices=np.zeros((0,), dtype=np.int32),
        quat_wxyz=np.zeros((frames, 0, 4), dtype=np.float64),
        weights=np.zeros((frames, 0), dtype=np.float64),
    )
    orientations.validate(frames=frames)

    interaction_mesh = build_omniretarget_interaction_mesh(targets, object_points_w)
    object_points = interaction_mesh.object_points_w
    target_laplacian = interaction_mesh.target_laplacian

    point_link_indices, point_local_offsets = _rigid_link_points(
        robot=robot,
        joint_cfg=joint_init,
        groups=target_link_groups,
        family="interaction",
    )
    force_link_indices, force_local_offsets = _rigid_link_points(
        robot=robot,
        joint_cfg=joint_init,
        groups=force_link_groups,
        family="contact force",
    )
    if environment_contacts is None:
        anchor_ids: tuple[str, ...] = ()
        anchor_link_indices = np.zeros((0,), dtype=np.int32)
        anchor_local_offsets = np.zeros((0, 3), dtype=np.float64)
        anchor_target_positions = np.zeros((0, 3), dtype=np.float64)
    else:
        anchor_ids = environment_contacts.anchor_ids
        anchor_link_indices, anchor_local_offsets = _environment_anchor_link_points(
            robot=robot,
            root_qpos=root_init,
            joint_cfg=joint_init,
            link_groups=environment_contacts.link_groups,
            representative_frames=np.asarray(environment_contacts.representative_frames, dtype=np.int64),
            source_position_w=np.asarray(environment_contacts.source_position_w, dtype=np.float64),
        )
        anchor_target_positions = np.asarray(environment_contacts.target_position_w, dtype=np.float64)
    lower = np.asarray(robot.joints.lower_limits, dtype=np.float64)
    upper = np.asarray(robot.joints.upper_limits, dtype=np.float64)
    lower = np.where(np.isfinite(lower), lower, -np.pi)
    upper = np.where(np.isfinite(upper), upper, np.pi)
    normals = np.asarray(force_linearization.contact_normals_w, dtype=np.float64)
    normals /= np.linalg.norm(normals, axis=2, keepdims=True)
    force_scale = max(
        float(np.sqrt(np.mean(np.square(np.asarray(force_linearization.target_force_w)[np.asarray(force_linearization.contact_mask, dtype=bool)]))))
        if np.any(force_linearization.contact_mask)
        else 0.0,
        1.0,
    )

    joint_var = robot.joint_var_cls(jnp.arange(frames, dtype=jnp.int32))
    base_var = jaxls.SE3Var(jnp.arange(frames, dtype=jnp.int32))

    def world_link_point(vals: Any, joint: Any, base: Any, link_index: Any, local_offset: Any) -> Any:
        fk = robot.forward_kinematics(vals[joint])
        link_pose = fk[link_index]
        local_point = link_pose[4:7] + _quat_apply_jax(link_pose[:4], local_offset)
        return vals[base].apply(local_point)

    @jaxls.Cost.factory(name="contact_interaction_laplacian")
    def contact_laplacian_cost(
        vals: Any,
        joint: Any,
        base: Any,
        target_position: Any,
        target_weight: Any,
        laplacian_matrix: Any,
        target_lap: Any,
        contact_mask: Any,
        contact_normal: Any,
        contact_position: Any,
        orientation_quat: Any,
        orientation_weight: Any,
        prior_joint: Any,
        prior_base_pose: Any,
    ) -> Any:
        points = jnp.stack(
            [
                world_link_point(vals, joint, base, point_link_indices[i], point_local_offsets[i])
                for i in range(robot_parts)
            ]
        )
        vertices = jnp.concatenate([points, jnp.asarray(object_points)], axis=0)
        actual_lap = laplacian_matrix @ vertices
        lap_residual = (actual_lap - target_lap) * jnp.sqrt(float(cfg.contact_laplacian_weight))
        taskspace_residual = (points - target_position) * jnp.sqrt(
            jnp.maximum(target_weight, 0.0) * float(cfg.taskspace_tracking_weight)
        )[:, None]
        q = vals[joint]
        limit_residual = jnp.concatenate(
            [jnp.maximum(q - jnp.asarray(upper), 0.0), jnp.maximum(jnp.asarray(lower) - q, 0.0)]
        ) * jnp.sqrt(float(cfg.joint_limit_weight))
        force_points = jnp.stack(
            [
                world_link_point(vals, joint, base, force_link_indices[i], force_local_offsets[i])
                for i in range(force_parts)
            ]
        )
        contact_delta = force_points - contact_position
        normal_delta = jnp.sum(contact_delta * contact_normal, axis=1, keepdims=True)
        tangential_delta = contact_delta - normal_delta * contact_normal
        sticking_residual = (
            tangential_delta
            * contact_mask[:, None]
            * jnp.sqrt(float(cfg.contact_sticking_weight))
        )
        fk = robot.forward_kinematics(vals[joint])
        local_quat = fk[jnp.asarray(orientations.link_indices), :4]
        base_quat = vals[base].wxyz_xyz[:4]
        world_quat = _quat_mul_jax(base_quat[None, :], local_quat)
        orientation_dot = jnp.sum(world_quat * orientation_quat, axis=1)
        orientation_residual = (1.0 - orientation_dot * orientation_dot) * jnp.sqrt(orientation_weight)
        prior_scale = jnp.sqrt(float(cfg.pose_prior_weight))
        joint_prior_residual = (q - prior_joint) * prior_scale
        base_prior_residual = (jaxlie.SE3(prior_base_pose).inverse() @ vals[base]).log() * prior_scale
        return jnp.concatenate(
            [
                lap_residual.reshape(-1),
                taskspace_residual.reshape(-1),
                limit_residual,
                sticking_residual.reshape(-1),
                orientation_residual,
                joint_prior_residual,
                base_prior_residual,
            ]
        )

    prior_base_array = np.concatenate([root_init[:, 3:7], root_init[:, :3]], axis=1)
    prior_base = jaxlie.SE3(jnp.asarray(prior_base_array))
    prior_joint_lap = joint_init[:-2] - 2.0 * joint_init[1:-1] + joint_init[2:]
    prior_base_prev = jaxlie.SE3(jnp.asarray(prior_base_array[:-2]))
    prior_base_curr = jaxlie.SE3(jnp.asarray(prior_base_array[1:-1]))
    prior_base_next = jaxlie.SE3(jnp.asarray(prior_base_array[2:]))
    prior_base_velocity_prev = np.asarray((prior_base_prev.inverse() @ prior_base_curr).log())
    prior_base_velocity_next = np.asarray((prior_base_curr.inverse() @ prior_base_next).log())
    prior_base_lap = prior_base_velocity_next - prior_base_velocity_prev

    @jaxls.Cost.factory(name="temporal_laplacian")
    def temporal_laplacian_cost(
        vals: Any,
        joint_prev: Any,
        joint_curr: Any,
        joint_next: Any,
        base_prev: Any,
        base_curr: Any,
        base_next: Any,
        target_joint_lap: Any,
        target_base_lap: Any,
    ) -> Any:
        joint_lap = vals[joint_prev] - 2.0 * vals[joint_curr] + vals[joint_next]
        velocity_prev = (vals[base_prev].inverse() @ vals[base_curr]).log()
        velocity_next = (vals[base_curr].inverse() @ vals[base_next]).log()
        base_lap = velocity_next - velocity_prev
        scale = jnp.sqrt(float(cfg.temporal_laplacian_weight))
        return jnp.concatenate([(joint_lap - target_joint_lap) * scale, (base_lap - target_base_lap) * scale])

    @jaxls.Cost.factory(name="contact_force")
    def contact_force_cost(
        vals: Any,
        joint: Any,
        base: Any,
        contact_mask: Any,
        normal: Any,
        reference_position: Any,
        target_normal_displacement: Any,
    ) -> Any:
        points = jnp.stack(
            [
                world_link_point(vals, joint, base, force_link_indices[i], force_local_offsets[i])
                for i in range(force_parts)
            ]
        )
        normal_delta = jnp.sum((points - reference_position) * normal, axis=1)
        displacement_residual = (
            (normal_delta - target_normal_displacement) / float(cfg.contact_force_position_scale_m)
        )
        return displacement_residual * contact_mask * jnp.sqrt(float(cfg.contact_force_weight))

    @jaxls.Cost.factory(name="environment_contact_anchor", kind="constraint_eq_zero")
    def environment_contact_anchor_constraint(
        vals: Any,
        joint: Any,
        base: Any,
        link_index: Any,
        local_offset: Any,
        target_position: Any,
    ) -> Any:
        return world_link_point(vals, joint, base, link_index, local_offset) - target_position

    costs: list[Any] = [
        contact_laplacian_cost(
            joint_var,
            base_var,
            jnp.asarray(targets),
            jnp.asarray(weights),
            jnp.asarray(interaction_mesh.laplacian_matrices),
            jnp.asarray(target_laplacian),
            jnp.asarray(force_linearization.contact_mask, dtype=jnp.float32),
            jnp.asarray(normals),
            jnp.asarray(force_linearization.reference_link_position_w),
            jnp.asarray(orientations.quat_wxyz),
            jnp.asarray(orientations.weights),
            jnp.asarray(joint_init),
            jnp.asarray(prior_base_array),
        ),
        contact_force_cost(
            joint_var,
            base_var,
            jnp.asarray(force_linearization.contact_mask, dtype=jnp.float32),
            jnp.asarray(normals),
            jnp.asarray(force_linearization.reference_link_position_w),
            jnp.asarray(force_linearization.target_normal_displacement_m),
        ),
    ]
    if frames > 2:
        costs.append(
            temporal_laplacian_cost(
                robot.joint_var_cls(jnp.arange(0, frames - 2, dtype=jnp.int32)),
                robot.joint_var_cls(jnp.arange(1, frames - 1, dtype=jnp.int32)),
                robot.joint_var_cls(jnp.arange(2, frames, dtype=jnp.int32)),
                jaxls.SE3Var(jnp.arange(0, frames - 2, dtype=jnp.int32)),
                jaxls.SE3Var(jnp.arange(1, frames - 1, dtype=jnp.int32)),
                jaxls.SE3Var(jnp.arange(2, frames, dtype=jnp.int32)),
                jnp.asarray(prior_joint_lap),
                jnp.asarray(prior_base_lap),
            )
        )
    if len(anchor_ids):
        representative = np.asarray(environment_contacts.representative_frames, dtype=np.int64)
        costs.append(
            environment_contact_anchor_constraint(
                robot.joint_var_cls(jnp.asarray(representative, dtype=jnp.int32)),
                jaxls.SE3Var(jnp.asarray(representative, dtype=jnp.int32)),
                jnp.asarray(anchor_link_indices),
                jnp.asarray(anchor_local_offsets),
                jnp.asarray(anchor_target_positions),
            )
        )
    problem = jaxls.LeastSquaresProblem(costs=costs, variables=[joint_var, base_var]).analyze(
        use_onp=True,
        schur_elimination="off",
    )
    initial_values = jaxls.VarValues.make(
        [joint_var.with_value(jnp.asarray(joint_init)), base_var.with_value(prior_base)]
    )
    solution, summary = problem.solve(
        initial_values,
        linear_solver=cfg.linear_solver,
        termination=jaxls.TerminationConfig(max_iterations=cfg.max_iterations),
        verbose=False,
        return_summary=True,
    )
    solved_joint = np.asarray(solution[joint_var], dtype=np.float64)
    solved_base = np.asarray(solution[base_var].wxyz_xyz, dtype=np.float64)
    solved_root = np.concatenate([solved_base[:, 4:7], solved_base[:, :4]], axis=1)
    force_reference_position = _world_link_points_numpy(
        robot=robot,
        root_qpos=root_init,
        joint_cfg=joint_init,
        link_indices=force_link_indices,
        local_offsets=force_local_offsets,
    )
    force_solved_position = _world_link_points_numpy(
        robot=robot,
        root_qpos=solved_root,
        joint_cfg=solved_joint,
        link_indices=force_link_indices,
        local_offsets=force_local_offsets,
    )
    if environment_contacts is None:
        anchor_solved_position = np.zeros((0, 3), dtype=np.float64)
        anchor_error = np.zeros((0,), dtype=np.float64)
    else:
        anchor_trajectory = _world_link_points_numpy(
            robot=robot,
            root_qpos=solved_root,
            joint_cfg=solved_joint,
            link_indices=anchor_link_indices,
            local_offsets=anchor_local_offsets,
        )
        representative = np.asarray(environment_contacts.representative_frames, dtype=np.int64)
        anchor_solved_position = anchor_trajectory[representative, np.arange(len(anchor_ids))]
        anchor_error = np.linalg.norm(anchor_solved_position - anchor_target_positions, axis=1)
        max_anchor_error = float(np.max(anchor_error, initial=0.0))
        if max_anchor_error > float(cfg.environment_anchor_tolerance_m):
            worst = int(np.argmax(anchor_error))
            raise ValueError(
                f"environment contact hard constraint failed for {anchor_ids[worst]}: "
                f"error={anchor_error[worst]:.6g}m tolerance={cfg.environment_anchor_tolerance_m:.6g}m"
            )
    return WholeTrajectoryResult(
        root_qpos=solved_root,
        joint_cfg=solved_joint,
        force_reference_position_w=force_reference_position,
        force_solved_position_w=force_solved_position,
        metadata={
            "solver": "pyroki_jaxls_whole_trajectory",
            "objective_families": ["contact_interaction_laplacian", "temporal_laplacian", "contact_force"],
            "whole_trajectory_joint_optimization": True,
            "whole_trajectory_base_se3_optimization": True,
            "frame_count": frames,
            "cost_term_count": frames * 2 + max(0, frames - 2),
            "constraint_term_count": int(len(anchor_ids)),
            "problem_term_count": frames * 2 + max(0, frames - 2) + len(anchor_ids),
            "iterations": int(np.asarray(summary.iterations)),
            "linear_solver": cfg.linear_solver,
            "force_scale_n": force_scale,
            "contact_force_parameterization": "normal_displacement_from_newton_force_secant",
            "contact_force_tracks_world_position": False,
            "contact_force_fixed_stiffness": False,
            "environment_contact_handle_model": "external_surface_anchor",
            "environment_contact_anchor_ids": list(anchor_ids),
            "environment_contact_edited_count": int(
                np.count_nonzero(environment_contacts.edited) if environment_contacts is not None else 0
            ),
            "hard_constraint_count": int(len(anchor_ids) * 3),
            "hard_constraint_enforcement": "jaxls_constraint_eq_zero_augmented_lagrangian",
            "environment_anchor_error_max_m": float(np.max(anchor_error, initial=0.0)),
            "environment_anchor_error_mean_m": float(np.mean(anchor_error)) if len(anchor_error) else 0.0,
            "interaction_mesh": {
                "topology": "per_frame_3d_delaunay",
                "laplacian": "uniform_vertex_minus_neighbor_mean",
                "robot_vertex_count": int(interaction_mesh.robot_vertex_count),
                "object_vertex_count": int(object_points.shape[0]),
                "vertex_count": int(interaction_mesh.vertex_count),
                "edge_count_min": int(np.min(interaction_mesh.edge_counts)),
                "edge_count_max": int(np.max(interaction_mesh.edge_counts)),
                "full_vertex_rows": True,
            },
            "config": cfg.__dict__,
        },
    )


def _rigid_link_points(
    *,
    robot: Any,
    joint_cfg: np.ndarray,
    groups: Sequence[np.ndarray],
    family: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Represent each rigid group centroid as one link-local point."""

    import jax.numpy as jnp

    normalized = [np.asarray(group, dtype=np.int32).reshape(-1) for group in groups]
    if not normalized or any(group.size == 0 for group in normalized):
        raise ValueError(f"{family} link groups must be non-empty")
    fk = np.asarray(robot.forward_kinematics(jnp.asarray(joint_cfg)), dtype=np.float64)
    link_indices = np.asarray([int(group[0]) for group in normalized], dtype=np.int32)
    offsets = np.empty((len(normalized), 3), dtype=np.float64)
    for index, group in enumerate(normalized):
        anchor = fk[:, link_indices[index]]
        centroid = np.mean(fk[:, group, 4:7], axis=1)
        local_by_frame = _quat_apply_numpy(_quat_conjugate_numpy(anchor[:, :4]), centroid - anchor[:, 4:7])
        offset = np.mean(local_by_frame, axis=0)
        max_drift = float(np.max(np.linalg.norm(local_by_frame - offset, axis=1)))
        if max_drift > 1.0e-5:
            raise ValueError(
                f"{family} group {index} spans moving links; cannot represent it as one explicit rigid point "
                f"(local drift {max_drift:.6g} m)"
            )
        offsets[index] = offset
    return link_indices, offsets


def _environment_anchor_link_points(
    *,
    robot: Any,
    root_qpos: np.ndarray,
    joint_cfg: np.ndarray,
    link_groups: Sequence[np.ndarray],
    representative_frames: np.ndarray,
    source_position_w: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Attach each environment handle to the nearest robot collision link point."""

    import jax.numpy as jnp

    groups = [np.asarray(group, dtype=np.int32).reshape(-1) for group in link_groups]
    frames = np.asarray(representative_frames, dtype=np.int64)
    source = np.asarray(source_position_w, dtype=np.float64)
    fk = np.asarray(robot.forward_kinematics(jnp.asarray(joint_cfg)), dtype=np.float64)
    root = np.asarray(root_qpos, dtype=np.float64)
    link_indices = np.empty((len(groups),), dtype=np.int32)
    local_offsets = np.empty((len(groups), 3), dtype=np.float64)
    for index, (group, frame) in enumerate(zip(groups, frames, strict=True)):
        source_base = _quat_apply_numpy(
            _quat_conjugate_numpy(root[frame, 3:7]),
            source[index] - root[frame, :3],
        )
        link_poses = fk[frame, group]
        nearest = int(np.argmin(np.linalg.norm(link_poses[:, 4:7] - source_base[None, :], axis=1)))
        link_index = int(group[nearest])
        link_pose = fk[frame, link_index]
        link_indices[index] = link_index
        local_offsets[index] = _quat_apply_numpy(
            _quat_conjugate_numpy(link_pose[:4]),
            source_base - link_pose[4:7],
        )
    return link_indices, local_offsets


def _quat_mul_jax(a: Any, b: Any) -> Any:
    import jax.numpy as jnp

    aw, ax, ay, az = jnp.moveaxis(a, -1, 0)
    bw, bx, by, bz = jnp.moveaxis(b, -1, 0)
    return jnp.stack(
        [
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ],
        axis=-1,
    )


def _quat_apply_jax(quat: Any, vector: Any) -> Any:
    import jax.numpy as jnp

    xyz = quat[..., 1:4]
    twice_cross = 2.0 * jnp.cross(xyz, vector)
    return vector + quat[..., :1] * twice_cross + jnp.cross(xyz, twice_cross)


def _quat_conjugate_numpy(quat: np.ndarray) -> np.ndarray:
    value = np.asarray(quat, dtype=np.float64).copy()
    value[..., 1:4] *= -1.0
    return value


def _quat_apply_numpy(quat: np.ndarray, vector: np.ndarray) -> np.ndarray:
    q = np.asarray(quat, dtype=np.float64)
    v = np.asarray(vector, dtype=np.float64)
    xyz = q[..., 1:4]
    twice_cross = 2.0 * np.cross(xyz, v)
    return v + q[..., :1] * twice_cross + np.cross(xyz, twice_cross)


def _world_link_points_numpy(
    *,
    robot: Any,
    root_qpos: np.ndarray,
    joint_cfg: np.ndarray,
    link_indices: np.ndarray,
    local_offsets: np.ndarray,
) -> np.ndarray:
    import jax.numpy as jnp

    fk = np.asarray(robot.forward_kinematics(jnp.asarray(joint_cfg)), dtype=np.float64)
    link_pose = fk[:, np.asarray(link_indices, dtype=np.int32)]
    local_points = link_pose[..., 4:7] + _quat_apply_numpy(link_pose[..., :4], local_offsets[None])
    root = np.asarray(root_qpos, dtype=np.float64)
    return _quat_apply_numpy(root[:, None, 3:7], local_points) + root[:, None, :3]
