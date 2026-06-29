from __future__ import annotations

import unittest

import numpy as np

from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.contact_laplacian import (
    BatchContactLaplacianConfig,
    BodyPositionTrajectoryKinematicsProvider,
    ContactHandleSpec,
    InteractionMeshSpec,
    LinearPointKinematicsProvider,
    solve_batch_contact_laplacian,
)
from motion_edit.contact_laplacian.backend import build_contact_handle_specs
from motion_edit.contact_laplacian.residuals import build_uniform_laplacian_matrix


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
    def test_uniform_laplacian_matrix_matches_neighbor_mean_form(self) -> None:
        lap = build_uniform_laplacian_matrix(3, [(0, 1), (0, 2)])

        expected = np.asarray(
            [
                [1.0, -0.5, -0.5],
                [-1.0, 1.0, 0.0],
                [-1.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
        np.testing.assert_allclose(lap, expected)

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

    def test_default_semantic_body_edges_are_active(self) -> None:
        names = ("root", "torso", "left_hand", "right_hand", "left_foot", "right_foot")
        provider = BodyPositionTrajectoryKinematicsProvider(names)
        q = np.zeros((3, provider.nq), dtype=np.float64)
        prior = np.zeros_like(q)
        left_foot_x = 3 * names.index("left_foot")
        prior[:, left_foot_x] = 1.0

        result = solve_batch_contact_laplacian(
            q,
            provider,
            [],
            list(names),
            BatchContactLaplacianConfig(
                num_iters=4,
                trust_region=10.0,
                body_relative_weight=100.0,
                q_prior_weight=0.0,
                q_smooth_weight=0.0,
                temporal_laplacian_weight=0.0,
            ),
            q_prior=prior,
        )

        self.assertIn(["root", "left_foot"], result.metadata["body_edges"])
        points = result.q.reshape(3, len(names), 3)
        root_x = points[:, names.index("root"), 0]
        foot_x = points[:, names.index("left_foot"), 0]
        self.assertGreater(float(np.mean(foot_x - root_x)), 0.9)
        labels = result.metadata["iterations"][-1]["residual_norms_by_label"]
        self.assertIn("body_relative", labels)

    def test_accepted_step_reports_actual_residual_and_respects_trust_region(self) -> None:
        provider = LinearPointKinematicsProvider(
            base_points={"left_foot": np.zeros(3)},
            weights={"left_foot": np.asarray([[1.0], [0.0], [0.0]], dtype=np.float64)},
        )
        q = np.zeros((2, 1), dtype=np.float64)
        handle = ContactHandleSpec(
            anchor_id="anchor_lf",
            body="left_foot",
            semantic_name="left_foot",
            frames=np.asarray([0], dtype=np.int64),
            target_xyz=np.asarray([[1.0, 0.0, 0.0]], dtype=np.float64),
            kind="edited_contact",
            weight=1000.0,
        )
        result = solve_batch_contact_laplacian(
            q,
            provider,
            [handle],
            ["left_foot"],
            BatchContactLaplacianConfig(
                num_iters=1,
                trust_region=0.05,
                body_relative_weight=0.0,
                q_prior_weight=0.0,
                q_smooth_weight=0.0,
                temporal_laplacian_weight=0.0,
            ),
        )

        iteration = result.metadata["iterations"][0]
        self.assertTrue(iteration["accepted"])
        self.assertLessEqual(float(iteration["max_frame_step"]), 0.05 + 1.0e-9)
        self.assertLessEqual(float(iteration["objective_after"]), float(iteration["objective_before"]) + 1.0e-9)
        self.assertAlmostEqual(float(iteration["residual_norm"]) ** 2, float(iteration["objective_after"]), places=7)

    def test_contact_edit_intervals_are_half_open_and_validated(self) -> None:
        edit = ContactAnchorEditRecord(
            edit_id="edit_interval",
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            delta_world=[0.1, 0.0, 0.0],
            affected_frames=[3, 12],
        )
        edit.validate()
        self.assertEqual(list(range(*edit.affected_frames)), list(range(3, 12)))
        self.assertEqual(len(range(*edit.affected_frames)), 9)

        invalid_intervals = ([3], [3, 3], [-1, 3])
        for affected_frames in invalid_intervals:
            with self.subTest(affected_frames=affected_frames):
                invalid = ContactAnchorEditRecord(
                    edit_id="bad_interval",
                    motion_id="motion_a",
                    anchor_id="anchor_lf",
                    body="left_foot",
                    delta_world=[0.1, 0.0, 0.0],
                    affected_frames=list(affected_frames),
                )
                with self.assertRaises(ValueError):
                    invalid.validate()

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

    def test_interaction_mesh_laplacian_pulls_robot_to_reference_relation(self) -> None:
        provider = LinearPointKinematicsProvider(
            base_points={"left_foot": np.zeros(3)},
            weights={"left_foot": np.asarray([[1.0], [0.0], [0.0]], dtype=np.float64)},
        )
        q = np.zeros((4, 1), dtype=np.float64)
        q_prior = np.ones((4, 1), dtype=np.float64)
        mesh = InteractionMeshSpec(
            robot_points=("left_foot",),
            object_points=np.asarray([[0.0, 0.0, 0.0]], dtype=np.float64),
            edges=((0, 1),),
        )

        before_robot = provider.fk_points(q[0], ["left_foot"])[0]
        ref_robot = provider.fk_points(q_prior[0], ["left_foot"])[0]
        before_error = float(np.linalg.norm((before_robot - mesh.object_points[0]) - (ref_robot - mesh.object_points[0])))

        result = solve_batch_contact_laplacian(
            q,
            provider,
            [],
            ["left_foot"],
            BatchContactLaplacianConfig(
                num_iters=5,
                trust_region=10.0,
                mesh_laplacian_weight=100.0,
                q_prior_weight=0.0,
                q_smooth_weight=0.0,
                temporal_laplacian_weight=0.0,
                body_relative_weight=0.0,
            ),
            q_prior=q_prior,
            interaction_mesh=mesh,
        )

        after_robot = provider.fk_points(result.q[0], ["left_foot"])[0]
        after_error = float(np.linalg.norm((after_robot - mesh.object_points[0]) - (ref_robot - mesh.object_points[0])))
        self.assertLess(after_error, before_error * 0.1)
        self.assertTrue(result.metadata["interaction_mesh"]["active"])
        self.assertGreater(result.metadata["interaction_mesh"]["rows"], 0)
        self.assertFalse(result.warnings)

    def test_interaction_mesh_residual_coexists_with_contact_and_temporal_terms(self) -> None:
        provider = _provider_shared_root()
        q = np.zeros((10, 2), dtype=np.float64)
        q_prior = np.zeros_like(q)
        q_prior[:, 0] = 0.25
        mesh = InteractionMeshSpec(
            robot_points=("left_foot", "left_hand"),
            object_points=np.asarray([[0.0, 0.0, 0.0]], dtype=np.float64),
            edges=((0, 2), (1, 2)),
        )
        handle = ContactHandleSpec(
            anchor_id="anchor_lf",
            body="left_foot",
            semantic_name="left_foot",
            frames=np.arange(3, 6, dtype=np.int64),
            target_xyz=np.tile(np.asarray([[0.5, 0.0, 0.0]], dtype=np.float64), (3, 1)),
            kind="edited_contact",
            weight=100.0,
        )

        result = solve_batch_contact_laplacian(
            q,
            provider,
            [handle],
            ["left_foot", "left_hand"],
            BatchContactLaplacianConfig(
                num_iters=4,
                trust_region=10.0,
                mesh_laplacian_weight=10.0,
                temporal_laplacian_weight=5.0,
                q_prior_weight=0.1,
                q_smooth_weight=0.1,
                body_relative_weight=0.0,
            ),
            q_prior=q_prior,
            interaction_mesh=mesh,
        )

        labels = result.metadata["iterations"][-1]["residual_norms_by_label"]
        self.assertIn("mesh_laplacian", labels)
        self.assertIn("edited_contact", labels)
        self.assertIn("temporal_laplacian", labels)

    def test_mesh_laplacian_weight_without_mesh_spec_warns_and_skips(self) -> None:
        provider = LinearPointKinematicsProvider(
            base_points={"left_foot": np.zeros(3)},
            weights={"left_foot": np.asarray([[1.0], [0.0], [0.0]], dtype=np.float64)},
        )
        result = solve_batch_contact_laplacian(
            np.zeros((3, 1), dtype=np.float64),
            provider,
            [],
            ["left_foot"],
            BatchContactLaplacianConfig(
                num_iters=1,
                mesh_laplacian_weight=1.0,
                q_prior_weight=0.0,
                q_smooth_weight=0.0,
                temporal_laplacian_weight=0.0,
                body_relative_weight=0.0,
            ),
        )

        self.assertIn("no interaction_mesh spec", result.warnings[0])
        self.assertFalse(result.metadata["interaction_mesh"]["active"])


if __name__ == "__main__":
    unittest.main()
