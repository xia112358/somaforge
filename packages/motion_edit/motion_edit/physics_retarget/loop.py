from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Protocol

import numpy as np

from .objective import evaluate_rollout_objective
from .schema import (
    ForceGuidedRetargetConfig,
    ForceGuidedRetargetResult,
    PhysicsProjectionRequest,
    PhysicsRollout,
    ProjectionResult,
    RetargetIteration,
)


class TrajectoryProjector(Protocol):
    def project(self, request: PhysicsProjectionRequest) -> ProjectionResult: ...


class PhysicsRunner(Protocol):
    def run(self, *, motion_path: Path, iteration: int, output_dir: Path) -> PhysicsRollout: ...


def run_force_guided_retarget(
    *,
    initial_motion_path: str | Path,
    target_force_w: np.ndarray,
    target_mask: np.ndarray,
    projector: TrajectoryProjector,
    physics_runner: PhysicsRunner,
    output_motion_path: str | Path,
    work_dir: str | Path,
    target_joint_pos: np.ndarray | None = None,
    config: ForceGuidedRetargetConfig | None = None,
) -> ForceGuidedRetargetResult:
    cfg = config or ForceGuidedRetargetConfig()
    cfg.validate()
    initial = Path(initial_motion_path).expanduser().resolve()
    output = Path(output_motion_path).expanduser().resolve()
    work = Path(work_dir).expanduser().resolve()
    if not initial.is_file():
        raise FileNotFoundError(initial)
    work.mkdir(parents=True, exist_ok=True)

    target_force = np.asarray(target_force_w, dtype=np.float64)
    target_contact = np.asarray(target_mask, dtype=bool)
    if target_force.ndim != 3 or target_force.shape[2] != 3:
        raise ValueError(f"target_force_w must be [T,P,3], got {target_force.shape}")
    if target_contact.shape != target_force.shape[:2]:
        raise ValueError(f"target_mask must be {target_force.shape[:2]}, got {target_contact.shape}")
    best_candidate = initial
    best_rollout = physics_runner.run(motion_path=initial, iteration=0, output_dir=work / "iteration_00")
    best_objective, best_metrics = evaluate_rollout_objective(
        target_force_w=target_force,
        target_mask=target_contact,
        target_joint_pos=target_joint_pos,
        rollout=best_rollout,
        config=cfg,
    )
    iterations = [
        RetargetIteration(
            iteration=0,
            accepted=True,
            objective=best_objective,
            previous_best_objective=None,
            candidate_motion_path=str(initial),
            rollout_motion_path=str(best_rollout.motion_path),
            metrics=best_metrics,
            rollout_metadata=dict(best_rollout.metadata),
        )
    ]
    previous_trial_rollout: PhysicsRollout | None = None
    previous_projection_metadata: dict[str, object] = {}
    for iteration in range(1, cfg.max_iterations + 1):
        iteration_dir = work / f"iteration_{iteration:02d}"
        projection = projector.project(
            PhysicsProjectionRequest(
                current_motion_path=best_candidate,
                target_force_w=target_force,
                target_mask=target_contact,
                actual_rollout=best_rollout,
                iteration=iteration,
                output_dir=iteration_dir,
                response_rollout=previous_trial_rollout,
                response_projection_metadata=dict(previous_projection_metadata),
            )
        )
        rollout = physics_runner.run(
            motion_path=projection.motion_path,
            iteration=iteration,
            output_dir=iteration_dir,
        )
        objective, metrics = evaluate_rollout_objective(
            target_force_w=target_force,
            target_mask=target_contact,
            target_joint_pos=target_joint_pos,
            rollout=rollout,
            config=cfg,
        )
        previous = best_objective
        relative_improvement = (previous - objective) / max(abs(previous), 1.0e-12)
        accepted = objective < previous and relative_improvement >= cfg.minimum_relative_improvement
        if accepted:
            best_objective = objective
            best_metrics = metrics
            best_candidate = projection.motion_path
            best_rollout = rollout
        previous_trial_rollout = rollout
        previous_projection_metadata = dict(projection.metadata)
        iterations.append(
            RetargetIteration(
                iteration=iteration,
                accepted=accepted,
                objective=objective,
                previous_best_objective=previous,
                candidate_motion_path=str(projection.motion_path),
                rollout_motion_path=str(rollout.motion_path),
                metrics=metrics,
                projection_metadata=dict(projection.metadata),
                rollout_metadata=dict(rollout.metadata),
            )
        )

    best_rollout.validate(expected_frames=target_force.shape[0], expected_parts=target_force.shape[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_rollout.motion_path, output)
    result = ForceGuidedRetargetResult(
        output_motion_path=output,
        best_candidate_motion_path=best_candidate,
        best_rollout_motion_path=best_rollout.motion_path,
        best_objective=best_objective,
        iterations=tuple(iterations),
        metadata={
            "force_source": "newton_rollout_only",
            "force_enters_optimizer_as_cost": True,
            "objective_families": ["contact_interaction_laplacian", "temporal_laplacian", "contact_force"],
            "kinematic_force_bake_training_eligible": False,
            "best_metrics": best_metrics,
            "config": cfg.__dict__,
        },
    )
    report_path = output.with_suffix(output.suffix + ".physics_retarget.json")
    report_path.write_text(json.dumps(result.report_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
