from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from motion_edit.generation.pyroki_fullbody_ik import DEFAULT_ROBOT_URDF, solve_pyroki_fullbody_ik
from motion_edit.generation.pyroki_trajectory_optimizer import ForceLinearization, WholeTrajectoryConfig

from .force_response import (
    NewtonForceResponseConfig,
    estimate_force_displacement_secant,
    force_directions,
    force_matching_displacement,
    normal_force,
)
from .schema import PhysicsProjectionRequest, ProjectionResult


class WholeTrajectoryPhysicsProjector:
    """Project one Newton force rollout through the three-family JAXLS graph."""

    def __init__(
        self,
        *,
        lte_path: str | Path,
        robot_urdf: str | Path = DEFAULT_ROBOT_URDF,
        config: WholeTrajectoryConfig | None = None,
        force_response_config: NewtonForceResponseConfig | None = None,
    ) -> None:
        self.lte_path = Path(lte_path).expanduser().resolve()
        self.robot_urdf = Path(robot_urdf).expanduser().resolve()
        self.config = config or WholeTrajectoryConfig()
        self.force_response_config = force_response_config or NewtonForceResponseConfig()
        self._response_n_per_m: np.ndarray | None = None
        self._response_valid: np.ndarray | None = None
        self._pending_baseline_force_n: np.ndarray | None = None
        self._pending_achieved_displacement_m: np.ndarray | None = None
        self._pending_contact_mask: np.ndarray | None = None
        if not self.lte_path.is_file():
            raise FileNotFoundError(self.lte_path)
        if not self.robot_urdf.is_file():
            raise FileNotFoundError(self.robot_urdf)
        self.config.validate()
        self.force_response_config.validate()
        with np.load(self.lte_path, allow_pickle=True) as lte:
            if "environment_contact_anchor_ids" not in lte.files:
                raise ValueError(
                    "physics retarget requires environment contact anchors; regenerate the initial motion "
                    "from its ContactGraph instead of using a legacy robot-part handle LTE"
                )
            if np.asarray(lte["environment_contact_anchor_ids"]).size == 0:
                raise ValueError("physics retarget requires at least one environment contact anchor")

    def project(self, request: PhysicsProjectionRequest) -> ProjectionResult:
        rollout = request.actual_rollout
        target_force = np.asarray(request.target_force_w, dtype=np.float64)
        target_mask = np.asarray(request.target_mask, dtype=bool)
        actual_force = np.asarray(rollout.force_w, dtype=np.float64)
        if actual_force.shape != target_force.shape:
            raise ValueError(f"actual/target force shape mismatch: {actual_force.shape} vs {target_force.shape}")
        if target_mask.shape != target_force.shape[:2]:
            raise ValueError(f"target_mask must be {target_force.shape[:2]}, got {target_mask.shape}")
        normals = force_directions(target_force, target_mask)
        target_force_n = normal_force(target_force, normals)
        actual_force_n = normal_force(actual_force, normals)
        self._update_newton_response(request=request, normals=normals)
        response = (
            self._response_n_per_m
            if self._response_n_per_m is not None
            else np.full_like(target_force_n, np.nan)
        )
        response_valid = (
            self._response_valid
            if self._response_valid is not None
            else np.zeros_like(target_mask, dtype=bool)
        )
        target_displacement = force_matching_displacement(
            target_force_n=target_force_n,
            actual_force_n=actual_force_n,
            response_n_per_m=response,
            response_valid=response_valid,
            contact_mask=target_mask,
            config=self.force_response_config,
        )

        request.output_dir.mkdir(parents=True, exist_ok=True)
        output = request.output_dir / "candidate_motion.npz"
        solve_pyroki_fullbody_ik(
            lte_path=self.lte_path,
            output_path=output,
            robot_urdf=self.robot_urdf,
            source_motion_path=request.current_motion_path,
            force_linearization_override=ForceLinearization(
                target_force_w=target_force,
                actual_force_w=actual_force,
                contact_mask=target_mask,
                contact_normals_w=normals,
                reference_link_position_w=None,
                target_normal_displacement_m=target_displacement,
            ),
            whole_trajectory_config=self.config,
        )
        with np.load(output, allow_pickle=True) as data:
            reference_position = np.asarray(
                data["physics_retarget_force_reference_position_w"], dtype=np.float64
            )
            solved_position = np.asarray(
                data["physics_retarget_force_solved_position_w"], dtype=np.float64
            )
            solver_metadata = json.loads(str(np.asarray(data["ik_metadata_json"]).item()))
        achieved_displacement = np.sum((solved_position - reference_position) * normals, axis=2)
        self._pending_baseline_force_n = actual_force_n.copy()
        self._pending_achieved_displacement_m = achieved_displacement
        self._pending_contact_mask = target_mask.copy()
        return ProjectionResult(
            motion_path=output,
            metadata={
                "projector": "pyroki_jaxls_whole_trajectory",
                "objective_families": [
                    "contact_interaction_laplacian",
                    "temporal_laplacian",
                    "contact_force",
                ],
                "hard_constraint_count": int(solver_metadata.get("hard_constraint_count", 0)),
                "environment_contact_handle_model": solver_metadata.get(
                    "environment_contact_handle_model", "missing"
                ),
                "environment_anchor_error_max_m": float(
                    solver_metadata.get("environment_anchor_error_max_m", 0.0)
                ),
                "force_linearized_from_newton_iteration": int(request.iteration - 1),
                "force_constraint_source": "newton_mujoco_warp_black_box_response",
                "fixed_contact_stiffness": False,
                "response_valid_ratio": float(np.mean(response_valid[target_mask])) if np.any(target_mask) else 0.0,
                "requested_normal_displacement_max_m": float(np.max(np.abs(target_displacement), initial=0.0)),
                "achieved_normal_displacement_max_m": float(np.max(np.abs(achieved_displacement), initial=0.0)),
            },
        )

    def _update_newton_response(self, *, request: PhysicsProjectionRequest, normals: np.ndarray) -> None:
        if (
            request.response_rollout is None
            or self._pending_baseline_force_n is None
            or self._pending_achieved_displacement_m is None
            or self._pending_contact_mask is None
        ):
            return
        response_force = np.asarray(request.response_rollout.force_w, dtype=np.float64)
        response_force_n = normal_force(response_force, normals)
        response, valid = estimate_force_displacement_secant(
            baseline_force_n=self._pending_baseline_force_n,
            response_force_n=response_force_n,
            achieved_displacement_m=self._pending_achieved_displacement_m,
            contact_mask=self._pending_contact_mask,
            config=self.force_response_config,
            previous_response_n_per_m=self._response_n_per_m,
        )
        self._response_n_per_m = response
        self._response_valid = valid
