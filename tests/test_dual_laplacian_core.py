from __future__ import annotations

import unittest

import numpy as np

from motion_edit.contact_laplacian import (
    BatchContactLaplacianConfig,
    ContactHandleSpec,
    InteractionMeshSpec,
    LinearPointKinematicsProvider,
    solve_batch_contact_laplacian,
)


class DualLaplacianCoreTests(unittest.TestCase):
    def test_legacy_generation_weight_signature_migrates_to_core_profile(self) -> None:
        config = BatchContactLaplacianConfig(
            edit_contact_weight=1000.0,
            fixed_contact_weight=1000.0,
            temporal_laplacian_weight=10.0,
            body_relative_weight=10.0,
            q_prior_weight=1.0,
            q_smooth_weight=1.0,
            mesh_laplacian_weight=0.0,
        )

        self.assertEqual(config.temporal_laplacian_weight, 40.0)
        self.assertEqual(config.body_relative_weight, 10.0)
        self.assertEqual(config.q_prior_weight, 0.02)
        self.assertEqual(config.q_smooth_weight, 0.0)
        self.assertEqual(config.mesh_laplacian_weight, 1.0)

    def test_temporal_laplacian_propagates_contact_deformation_before_window(self) -> None:
        provider = LinearPointKinematicsProvider(
            base_points={"left_foot": np.zeros(3)},
            weights={"left_foot": np.asarray([[1.0], [0.0], [0.0]], dtype=np.float64)},
        )
        q = np.zeros((40, 1), dtype=np.float64)
        frames = np.arange(18, 24, dtype=np.int64)
        handle = ContactHandleSpec(
            anchor_id="anchor_lf",
            body="left_foot",
            semantic_name="left_foot",
            frames=frames,
            target_xyz=np.tile(np.asarray([[0.1, 0.0, 0.0]], dtype=np.float64), (len(frames), 1)),
            kind="edited_contact",
            weight=1000.0,
        )
        mesh = InteractionMeshSpec(
            robot_points=("left_foot",),
            object_points=np.asarray([[0.0, 0.0, 0.0]], dtype=np.float64),
            edges=((0, 1),),
        )

        result = solve_batch_contact_laplacian(
            q,
            provider,
            [handle],
            ["left_foot"],
            BatchContactLaplacianConfig(trust_region=1.0),
            q_prior=q,
            interaction_mesh=mesh,
        )

        # The handle is only active from frame 18, but the temporal Laplacian
        # solves a deformation field that has already moved before frame 18.
        self.assertGreater(float(result.q[17, 0]), 0.05)
        self.assertLess(float(abs(result.q[18, 0] - result.q[17, 0])), 0.03)
        self.assertLess(float(abs(result.q[20, 0] - 0.1)), 0.01)
        self.assertEqual(result.metadata["objective_profile"], "dual_laplacian_contact_deformation")
        self.assertTrue(result.metadata["temporal_laplacian_active"])
        self.assertTrue(result.metadata["spatial_laplacian_active"])
        self.assertTrue(result.metadata["interaction_mesh"]["active"])

    def test_default_profile_has_no_first_difference_q_smoothing(self) -> None:
        config = BatchContactLaplacianConfig()

        self.assertEqual(config.q_smooth_weight, 0.0)
        self.assertLess(config.q_prior_weight, config.temporal_laplacian_weight)
        self.assertGreater(config.mesh_laplacian_weight, 0.0)


if __name__ == "__main__":
    unittest.main()
