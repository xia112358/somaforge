from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.physics_retarget.loop import run_force_guided_retarget
from motion_edit.physics_retarget.schema import (
    ForceGuidedRetargetConfig,
    PhysicsProjectionRequest,
    PhysicsRollout,
    ProjectionResult,
)


class _Projector:
    def __init__(self) -> None:
        self.requests: list[PhysicsProjectionRequest] = []

    def project(self, request: PhysicsProjectionRequest) -> ProjectionResult:
        self.requests.append(request)
        request.output_dir.mkdir(parents=True, exist_ok=True)
        output = request.output_dir / "candidate.npz"
        shutil.copy2(request.current_motion_path, output)
        return ProjectionResult(
            motion_path=output,
            metadata={"objective_families": ["contact_interaction_laplacian", "temporal_laplacian", "contact_force"]},
        )


class _Runner:
    def __init__(self, target_force: np.ndarray) -> None:
        self.target_force = target_force

    def run(self, *, motion_path: Path, iteration: int, output_dir: Path) -> PhysicsRollout:
        force = np.zeros_like(self.target_force) if iteration == 0 else self.target_force.copy()
        output_dir.mkdir(parents=True, exist_ok=True)
        rollout_path = output_dir / "rollout.npz"
        np.savez(rollout_path, joint_pos=np.full((3, 1), iteration + 1.0))
        return PhysicsRollout(
            motion_path=rollout_path,
            force_w=force,
            mask=np.linalg.norm(force, axis=2) > 0.0,
            provenance={"training_eligible": True},
        )


class PhysicsRetargetLoopTests(unittest.TestCase):
    def test_newton_rollout_is_passed_directly_to_projector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initial = root / "initial.npz"
            np.savez(initial, joint_pos=np.zeros((3, 1)))
            target_force = np.zeros((3, 8, 3), dtype=np.float64)
            target_force[:, 0, 2] = 100.0
            target_mask = np.zeros((3, 8), dtype=bool)
            target_mask[:, 0] = True
            projector = _Projector()

            result = run_force_guided_retarget(
                initial_motion_path=initial,
                target_force_w=target_force,
                target_mask=target_mask,
                projector=projector,
                physics_runner=_Runner(target_force),
                output_motion_path=root / "output.npz",
                work_dir=root / "work",
                config=ForceGuidedRetargetConfig(max_iterations=1),
            )

            self.assertEqual(len(projector.requests), 1)
            self.assertEqual(projector.requests[0].current_motion_path, initial.resolve())
            self.assertNotEqual(
                projector.requests[0].current_motion_path,
                projector.requests[0].actual_rollout.motion_path,
            )
            np.testing.assert_array_equal(projector.requests[0].target_force_w, target_force)
            np.testing.assert_array_equal(projector.requests[0].actual_rollout.force_w, np.zeros_like(target_force))
            self.assertTrue(result.iterations[1].accepted)
            self.assertEqual(
                result.metadata["objective_families"],
                ["contact_interaction_laplacian", "temporal_laplacian", "contact_force"],
            )


if __name__ == "__main__":
    unittest.main()
