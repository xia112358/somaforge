from __future__ import annotations

import unittest

import numpy as np

from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.contact_laplacian import (
    BatchContactLaplacianConfig,
    ContactHandleSpec,
    LinearPointKinematicsProvider,
    solve_batch_contact_laplacian,
)
from motion_edit.contact_laplacian.backend import build_contact_handle_specs


def _provider_shared_root() -> LinearPointKinematicsProvider:
    return LinearPointKinematicsProvider(
        base_points={
            "left_foot": np.zeros(3),
            "left_hand": np.zeros(3),
        },
        weights={
            "left_foot": np.asarray([[1.0, 0.0], [0.0, 0.0], [0.0, 0.0]], dtype=np.float64),
            "left_hand": np.asarray([[1.0, 1.0], [0.0, 0.0], [0.0, 0.0]], dtype=np.float64),
        },
    )


class BatchContactLaplacianTests(unittest.TestCase):
    def test_batch_solver_optimizes_whole_trajectory_not_per_frame(self) -> None:
        provider = LinearPointKinematicsProvider(
            base_points={"left_foot": np.zeros(3)},
            weights={"left_foot": np.asarray([[1.0], [0.0], [0.0]], dtype=np.float64)},
        )
        q = np.zeros((20, 1), dtype=np.float64)
        frames = np.arange(8, 12, dtype=np.int64)
        handle = ContactHandleSpec(
            anchor_id="anchor_lf",
            body="left_foot",
            semantic_name="left_foot",
            frames=frames,
            target_xyz=np.tile(np.asarray([[1.0, 0.0, 0.0]], dtype=np.float64), (len(frames), 1)),
            kind="edited_contact",
            weight=1000.0,
        )

        result = solve_batch_contact_laplacian(
            q,
            provider,
            [handle],
            ["left_foot"],
            BatchContactLaplacianConfig(
                num_iters=8,
                trust_region=10.0,
                edit_contact_weight=1000.0,
                fixed_contact_weight=1000.0,
                temporal_laplacian_weight=50.0,
                q_prior_weight=0.1,
                q_smooth_weight=0.1,
                body_relative_weight=0.0,
            ),
        )

        self.assertEqual(result.q.shape, (20, 1))
        self.assertGreater(float(result.q[8, 0]), 0.5)
        self.assertGreater(float(abs(result.q[7, 0])), 1.0e-3)
        self.assertGreater(float(abs(result.q[12, 0])), 1.0e-3)
        self.assertEqual(result.metadata["trajectory_shape"], [20, 1])

    def test_fixed_contact_handles_prevent_unedited_contact_drift(self) -> None:
        provider = _provider_shared_root()
        q = np.zeros((12, 2), dtype=np.float64)
        graph = ContactGraph(
            motion_id="motion_a",
            anchors=[
                ContactAnchorRecord("motion_a", "anchor_lf", "left_foot", 4, 8),
                ContactAnchorRecord("motion_a", "anchor_lh", "left_hand", 4, 8),
            ],
        )
        edit = ContactAnchorEditRecord(
            edit_id="edit_lf",
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            delta_world=[1.0, 0.0, 0.0],
            affected_frames=[4, 8],
            surface_id="box_top",
        )
        cfg = BatchContactLaplacianConfig(
            num_iters=8,
            trust_region=10.0,
            edit_contact_weight=1000.0,
            fixed_contact_weight=1000.0,
            temporal_laplacian_weight=1.0,
            q_prior_weight=0.01,
            q_smooth_weight=0.01,
            body_relative_weight=0.0,
        )
        handles, metadata = build_contact_handle_specs(graph=graph, edits=[edit], q_reference=q, kinematics=provider, config=cfg)

        result = solve_batch_contact_laplacian(q, provider, handles, ["left_foot", "left_hand"], cfg)
        hand = np.asarray([provider.fk_points(result.q[frame], ["left_hand"])[0, 0] for frame in range(4, 8)])
        foot = np.asarray([provider.fk_points(result.q[frame], ["left_foot"])[0, 0] for frame in range(4, 8)])

        self.assertEqual(metadata["edited_handle_count"], 1)
        self.assertEqual(metadata["fixed_handle_count"], 1)
        self.assertLess(float(np.max(np.abs(hand))), 0.05)
        self.assertGreater(float(np.mean(foot)), 0.8)

    def test_temporal_laplacian_reduces_velocity_spike(self) -> None:
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
        no_temporal = solve_batch_contact_laplacian(
            q,
            provider,
            [handle],
            ["left_foot"],
            BatchContactLaplacianConfig(num_iters=5, trust_region=10.0, temporal_laplacian_weight=0.0, q_prior_weight=0.1, q_smooth_weight=0.0, body_relative_weight=0.0),
        )
        temporal = solve_batch_contact_laplacian(
            q,
            provider,
            [handle],
            ["left_foot"],
            BatchContactLaplacianConfig(num_iters=5, trust_region=10.0, temporal_laplacian_weight=100.0, q_prior_weight=0.1, q_smooth_weight=0.0, body_relative_weight=0.0),
        )

        no_temporal_lap = np.linalg.norm(no_temporal.q[:-2] - 2.0 * no_temporal.q[1:-1] + no_temporal.q[2:])
        temporal_lap = np.linalg.norm(temporal.q[:-2] - 2.0 * temporal.q[1:-1] + temporal.q[2:])
        self.assertLess(float(temporal_lap), float(no_temporal_lap))

    def test_contact_handle_metadata_counts(self) -> None:
        provider = _provider_shared_root()
        q = np.zeros((6, 2), dtype=np.float64)
        handles = [
            ContactHandleSpec("a_edit", "left_foot", "left_foot", np.asarray([2, 3]), np.asarray([[0.5, 0, 0], [0.5, 0, 0]], dtype=np.float64), "edited_contact", 100.0),
            ContactHandleSpec("a_fixed", "left_hand", "left_hand", np.asarray([2, 3]), np.zeros((2, 3), dtype=np.float64), "fixed_contact", 100.0),
        ]

        result = solve_batch_contact_laplacian(
            q,
            provider,
            handles,
            ["left_foot", "left_hand"],
            BatchContactLaplacianConfig(num_iters=2, trust_region=10.0, temporal_laplacian_weight=1.0, body_relative_weight=0.0),
        )

        self.assertEqual(result.metadata["edited_handle_count"], 1)
        self.assertEqual(result.metadata["fixed_handle_count"], 1)
        self.assertGreaterEqual(len(result.metadata["iterations"]), 1)
        self.assertIn("weights", result.metadata)


if __name__ == "__main__":
    unittest.main()
