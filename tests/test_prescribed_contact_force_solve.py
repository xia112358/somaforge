from __future__ import annotations

import unittest

import numpy as np

from motion_edit.contact_force import ContactForceSample, PrescribedContactSolveConfig, solve_prescribed_contact_forces


class FakePrescribedBackend:
    def __init__(self, samples_by_frame: dict[int, list[ContactForceSample]]) -> None:
        self.samples_by_frame = samples_by_frame
        self.calls: list[tuple[int, np.ndarray, np.ndarray | None, np.ndarray | None]] = []

    def solve_frame(
        self,
        *,
        frame_index: int,
        qpos: np.ndarray,
        qvel: np.ndarray | None,
        qacc: np.ndarray | None,
        config: PrescribedContactSolveConfig,
    ) -> list[ContactForceSample]:
        self.calls.append(
            (
                int(frame_index),
                np.asarray(qpos, dtype=np.float64).copy(),
                None if qvel is None else np.asarray(qvel, dtype=np.float64).copy(),
                None if qacc is None else np.asarray(qacc, dtype=np.float64).copy(),
            )
        )
        return list(self.samples_by_frame.get(int(frame_index), []))


class PrescribedContactForceSolveTests(unittest.TestCase):
    def test_prescribed_solver_aggregates_samples_without_integrating_state(self) -> None:
        parts = ("left_foot", "right_hand")
        qpos = np.arange(4, dtype=np.float64).reshape(4, 1)
        qvel = np.full((4, 1), 2.0, dtype=np.float64)
        qacc = np.full((4, 1), 3.0, dtype=np.float64)
        contact_mask = np.zeros((4, 2), dtype=bool)
        contact_mask[1, 0] = True
        contact_mask[2, 1] = True
        position_prior = np.zeros((4, 2, 3), dtype=np.float64)
        position_prior[:, 0, :] = np.asarray([0.0, 0.0, 0.0])
        position_prior[:, 1, :] = np.asarray([1.0, 0.0, 0.0])
        backend = FakePrescribedBackend(
            {
                1: [
                    ContactForceSample(
                        frame_index=1,
                        part_hint="left_foot",
                        position_w=np.asarray([0.1, 0.0, 0.0]),
                        force_w=np.asarray([0.0, 0.0, 10.0]),
                    )
                ],
                2: [
                    ContactForceSample(
                        frame_index=2,
                        position_w=np.asarray([1.02, 0.0, 0.0]),
                        force_w=np.asarray([0.0, 5.0, 0.0]),
                        geom1_name="unknown_geom",
                        geom2_name="terrain",
                    )
                ],
                3: [
                    ContactForceSample(
                        frame_index=3,
                        part_hint="left_foot",
                        position_w=np.asarray([0.0, 0.0, 0.0]),
                        force_w=np.asarray([0.0, 0.0, 99.0]),
                    )
                ],
            }
        )

        field = solve_prescribed_contact_forces(
            qpos,
            backend,
            PrescribedContactSolveConfig(part_order=parts, metadata={"backend": "fake"}),
            qvel_ref=qvel,
            qacc_ref=qacc,
            contact_mask=contact_mask,
            contact_part_position_w=position_prior,
        )

        np.testing.assert_allclose(field.force_w[1, 0], [0.0, 0.0, 10.0])
        np.testing.assert_allclose(field.force_w[2, 1], [0.0, 5.0, 0.0])
        np.testing.assert_allclose(field.force_w[3, 0], [0.0, 0.0, 0.0])
        np.testing.assert_array_equal(field.mask, contact_mask)
        np.testing.assert_allclose(field.position_w[1, 0], [0.1, 0.0, 0.0])
        np.testing.assert_allclose(field.position_w[0, 0], position_prior[0, 0])
        self.assertEqual(field.metadata["force_source"], "prescribed_motion_contact_solve")
        self.assertFalse(field.metadata["force_applied_to_body"])
        self.assertFalse(field.metadata["integrated"])
        self.assertEqual(field.metadata["used_sample_count"], 2)
        self.assertEqual(field.metadata["skipped_by_intended_mask_count"], 1)
        self.assertEqual(field.metadata["backend"], "fake")
        self.assertEqual([call[0] for call in backend.calls], [0, 1, 2, 3])
        np.testing.assert_allclose(backend.calls[2][1], qpos[2])
        np.testing.assert_allclose(backend.calls[2][2], qvel[2])
        np.testing.assert_allclose(backend.calls[2][3], qacc[2])

    def test_schema_exports_npz_arrays(self) -> None:
        parts = ("left_foot",)
        backend = FakePrescribedBackend(
            {
                0: [
                    ContactForceSample(
                        frame_index=0,
                        part_hint="left_foot",
                        position_w=np.asarray([0.0, 0.0, 0.0]),
                        force_w=np.asarray([1.0, 2.0, 3.0]),
                    )
                ]
            }
        )
        field = solve_prescribed_contact_forces(
            np.zeros((2, 1), dtype=np.float64),
            backend,
            PrescribedContactSolveConfig(part_order=parts),
        )

        arrays = field.to_npz_arrays()
        self.assertEqual(tuple(arrays["contact_force_part_order"].tolist()), parts)
        self.assertEqual(arrays["contact_force_part_force_w"].shape, (2, 1, 3))
        self.assertEqual(arrays["contact_force_part_position_w"].shape, (2, 1, 3))
        self.assertEqual(arrays["contact_force_part_mask"].shape, (2, 1))
        np.testing.assert_allclose(arrays["contact_force_part_force_w"][0, 0], [1.0, 2.0, 3.0])

    def test_unassigned_samples_are_reported(self) -> None:
        backend = FakePrescribedBackend(
            {
                0: [
                    ContactForceSample(
                        frame_index=0,
                        position_w=np.asarray([10.0, 0.0, 0.0]),
                        force_w=np.asarray([1.0, 0.0, 0.0]),
                        geom1_name="unknown",
                        geom2_name="terrain",
                    )
                ]
            }
        )

        field = solve_prescribed_contact_forces(
            np.zeros((1, 1), dtype=np.float64),
            backend,
            PrescribedContactSolveConfig(part_order=("left_foot",), assignment_max_distance=0.01),
            contact_part_position_w=np.zeros((1, 1, 3), dtype=np.float64),
        )

        np.testing.assert_allclose(field.force_w, 0.0)
        self.assertEqual(field.metadata["unknown_sample_count"], 1)
        self.assertEqual(field.metadata["used_sample_count"], 0)


if __name__ == "__main__":
    unittest.main()
