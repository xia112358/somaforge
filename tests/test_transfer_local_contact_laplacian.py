from __future__ import annotations

import unittest

import numpy as np

from motion_edit.contact_laplacian import (
    BatchContactLaplacianConfig,
    ContactHandleSpec,
    LinearPointKinematicsProvider,
    TransferLocalContactLaplacianConfig,
    TransferWindowSpec,
    solve_transfer_local_contact_laplacian,
)


class TransferLocalContactLaplacianTests(unittest.TestCase):
    def test_single_contact_edit_only_changes_own_transfer_window(self) -> None:
        provider = LinearPointKinematicsProvider(
            base_points={"left_foot": np.zeros(3)},
            weights={"left_foot": np.asarray([[1.0], [0.0], [0.0]], dtype=np.float64)},
        )
        q = np.zeros((20, 1), dtype=np.float64)
        handle = ContactHandleSpec(
            anchor_id="anchor_lf",
            body="left_foot",
            semantic_name="left_foot",
            frames=np.asarray([10], dtype=np.int64),
            target_xyz=np.asarray([[1.0, 0.0, 0.0]], dtype=np.float64),
            kind="edited_contact",
            weight=1000.0,
        )

        result = solve_transfer_local_contact_laplacian(
            q,
            provider,
            [handle],
            ["left_foot"],
            [TransferWindowSpec("transfer_0", 8, 13)],
            TransferLocalContactLaplacianConfig(
                batch_config=BatchContactLaplacianConfig(
                    num_iters=5,
                    trust_region=10.0,
                    temporal_laplacian_weight=40.0,
                    q_prior_weight=0.05,
                    q_smooth_weight=0.0,
                    body_relative_weight=0.0,
                    mesh_laplacian_weight=0.0,
                ),
                boundary_pin_frames=1,
            ),
        )

        np.testing.assert_allclose(result.q[:8], 0.0)
        np.testing.assert_allclose(result.q[13:], 0.0)
        self.assertEqual(float(result.q[8, 0]), 0.0)
        self.assertEqual(float(result.q[12, 0]), 0.0)
        self.assertGreater(float(result.q[10, 0]), 0.2)
        self.assertEqual(result.metadata["solver"], "transfer_local_contact_laplacian")
        self.assertEqual(result.metadata["solved_window_count"], 1)

    def test_handle_frames_are_remapped_to_local_coordinates(self) -> None:
        provider = LinearPointKinematicsProvider(
            base_points={"left_foot": np.zeros(3)},
            weights={"left_foot": np.asarray([[1.0], [0.0], [0.0]], dtype=np.float64)},
        )
        q = np.zeros((12, 1), dtype=np.float64)
        handle = ContactHandleSpec(
            anchor_id="anchor_lf",
            body="left_foot",
            semantic_name="left_foot",
            frames=np.asarray([5, 6], dtype=np.int64),
            target_xyz=np.asarray([[0.5, 0.0, 0.0], [0.5, 0.0, 0.0]], dtype=np.float64),
            kind="edited_contact",
            weight=500.0,
        )

        result = solve_transfer_local_contact_laplacian(
            q,
            provider,
            [handle],
            ["left_foot"],
            [TransferWindowSpec("transfer_0", 4, 8)],
            TransferLocalContactLaplacianConfig(
                batch_config=BatchContactLaplacianConfig(
                    num_iters=3,
                    trust_region=10.0,
                    temporal_laplacian_weight=1.0,
                    q_prior_weight=0.01,
                    body_relative_weight=0.0,
                    mesh_laplacian_weight=0.0,
                ),
                boundary_pin_frames=0,
            ),
        )

        batch_meta = result.metadata["windows"][0]["batch_metadata"]
        self.assertEqual(batch_meta["edited_handle_count"], 1)
        self.assertGreater(float(result.q[5, 0]), 0.2)
        self.assertGreater(float(result.q[6, 0]), 0.2)

    def test_unowned_windows_are_skipped_without_changing_motion(self) -> None:
        provider = LinearPointKinematicsProvider(
            base_points={"left_foot": np.zeros(3)},
            weights={"left_foot": np.asarray([[1.0], [0.0], [0.0]], dtype=np.float64)},
        )
        q = np.zeros((15, 1), dtype=np.float64)
        handle = ContactHandleSpec(
            anchor_id="anchor_lf",
            body="left_foot",
            semantic_name="left_foot",
            frames=np.asarray([12], dtype=np.int64),
            target_xyz=np.asarray([[1.0, 0.0, 0.0]], dtype=np.float64),
            kind="edited_contact",
            weight=1000.0,
        )

        result = solve_transfer_local_contact_laplacian(
            q,
            provider,
            [handle],
            ["left_foot"],
            [TransferWindowSpec("empty_transfer", 2, 6), TransferWindowSpec("owned_transfer", 10, 14)],
            TransferLocalContactLaplacianConfig(
                batch_config=BatchContactLaplacianConfig(
                    num_iters=3,
                    trust_region=10.0,
                    temporal_laplacian_weight=10.0,
                    q_prior_weight=0.01,
                    body_relative_weight=0.0,
                    mesh_laplacian_weight=0.0,
                ),
                boundary_pin_frames=1,
            ),
        )

        self.assertFalse(result.metadata["windows"][0]["solved"])
        self.assertEqual(result.metadata["windows"][0]["reason"], "no_overlapping_contact_handles")
        np.testing.assert_allclose(result.q[:10], 0.0)
        np.testing.assert_allclose(result.q[14:], 0.0)
        self.assertGreater(float(result.q[12, 0]), 0.2)


if __name__ == "__main__":
    unittest.main()
