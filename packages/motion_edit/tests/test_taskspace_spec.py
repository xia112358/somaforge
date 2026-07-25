from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.generation.taskspace_spec import (
    ContactAwareTaskspaceMotion,
    ContactPatchTarget,
    make_boundary_weights,
    read_contact_aware_taskspace_motion,
    write_contact_aware_taskspace_motion,
)


class ContactAwareTaskspaceMotionTests(unittest.TestCase):
    def _motion(self) -> ContactAwareTaskspaceMotion:
        frame_count = 4
        contact = ContactPatchTarget(
            anchor_id="anchor_lf",
            kind="edited_contact",
            body_label="left_ankle_roll_link",
            shape_labels=("heel", "toe"),
            points_local=np.asarray([[0.0, 0.0, -0.1], [0.1, 0.0, -0.1]], dtype=np.float64),
            frames=np.asarray([1, 2], dtype=np.int64),
            surface_id="box_top",
            surface_origin_w=np.asarray([0.0, 0.0, 0.5], dtype=np.float64),
            surface_normal_w=np.asarray([0.0, 0.0, 1.0], dtype=np.float64),
            surface_tangent_u_w=np.asarray([1.0, 0.0, 0.0], dtype=np.float64),
            surface_tangent_v_w=np.asarray([0.0, 1.0, 0.0], dtype=np.float64),
            target_uv=np.asarray(
                [
                    [[0.2, 0.0], [0.3, 0.0]],
                    [[0.2, 0.0], [0.3, 0.0]],
                ],
                dtype=np.float64,
            ),
        )
        return ContactAwareTaskspaceMotion(
            motion_id="motion_a",
            fps=50.0,
            frame_start=0,
            frame_end=frame_count,
            semantic_names=("pelvis", "torso", "left_foot"),
            semantic_targets_w=np.zeros((frame_count, 3, 3), dtype=np.float64),
            semantic_weights=np.ones((frame_count, 3), dtype=np.float64),
            contacts=(contact,),
            source_qpos=np.zeros((frame_count, 36), dtype=np.float64),
            source_qvel=np.zeros((frame_count, 35), dtype=np.float64),
            source_reference_weights=np.full((frame_count, 36), 0.01, dtype=np.float64),
            boundary_weights=make_boundary_weights(frame_count, ramp_frames=1),
            metadata={"source": "unit_test"},
        )

    def test_uv_target_resolves_to_world_patch_points(self) -> None:
        contact = self._motion().contacts[0]
        target = contact.resolved_target_points_w()

        expected = np.asarray(
            [
                [[0.2, 0.0, 0.5], [0.3, 0.0, 0.5]],
                [[0.2, 0.0, 0.5], [0.3, 0.0, 0.5]],
            ],
            dtype=np.float64,
        )
        np.testing.assert_allclose(target, expected)

    def test_npz_roundtrip_preserves_taskspace_and_contact_contract(self) -> None:
        motion = self._motion()
        motion.validate()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "taskspace.npz"
            write_contact_aware_taskspace_motion(path, motion)
            loaded = read_contact_aware_taskspace_motion(path)

        self.assertEqual(loaded.motion_id, motion.motion_id)
        self.assertEqual(loaded.semantic_names, motion.semantic_names)
        self.assertEqual(loaded.contacts[0].shape_labels, ("heel", "toe"))
        np.testing.assert_allclose(loaded.semantic_targets_w, motion.semantic_targets_w)
        np.testing.assert_allclose(loaded.contacts[0].points_local, motion.contacts[0].points_local)
        np.testing.assert_allclose(loaded.contacts[0].resolved_target_points_w(), motion.contacts[0].resolved_target_points_w())

    def test_source_reference_weights_are_explicit_and_weak(self) -> None:
        motion = self._motion()
        motion.validate()
        self.assertTrue(np.all(motion.source_reference_weights == 0.01))
        self.assertGreater(float(motion.boundary_weights[0]), 0.0)
        self.assertGreater(float(motion.boundary_weights[-1]), 0.0)
        self.assertEqual(float(motion.boundary_weights[1]), 0.0)


if __name__ == "__main__":
    unittest.main()
