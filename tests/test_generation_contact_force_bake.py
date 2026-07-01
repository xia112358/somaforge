from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.contact_force import ContactForceSample, PrescribedContactSolveConfig
from motion_edit.generation import bake_prescribed_contact_forces_for_motion


class FakeBackend:
    def solve_frame(
        self,
        *,
        frame_index: int,
        qpos: np.ndarray,
        qvel: np.ndarray | None,
        qacc: np.ndarray | None,
        config: PrescribedContactSolveConfig,
    ) -> list[ContactForceSample]:
        if int(frame_index) == 1:
            return [
                ContactForceSample(
                    frame_index=1,
                    part_hint="left_foot",
                    position_w=np.asarray([0.25, 0.0, 0.0]),
                    force_w=np.asarray([0.0, 0.0, 12.0]),
                )
            ]
        return []


class GenerationContactForceBakeTests(unittest.TestCase):
    def test_bakes_prescribed_forces_into_motion_npz(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "motion.npz"
            output = root / "motion_force.npz"
            metadata = {"generation_mode": "test"}
            np.savez(
                source,
                joint_pos=np.zeros((3, 1), dtype=np.float64),
                joint_vel=np.zeros((3, 1), dtype=np.float64),
                fps=np.asarray(50.0),
                contact_force_part_order=np.asarray(["left_foot", "right_hand"], dtype=object),
                contact_force_part_mask=np.asarray([[False, False], [True, False], [False, False]], dtype=bool),
                contact_force_part_position_w=np.zeros((3, 2, 3), dtype=np.float64),
                motion_edit_generation_metadata=np.asarray(json.dumps(metadata), dtype=object),
            )

            result = bake_prescribed_contact_forces_for_motion(
                source,
                output_motion_path=output,
                backend=FakeBackend(),
                overwrite=True,
            )
            with np.load(output, allow_pickle=True) as data:
                self.assertIn("contact_force_part_force_w", data.files)
                self.assertIn("motion_edit_force_metadata", data.files)
                np.testing.assert_allclose(data["contact_force_part_force_w"][1, 0], [0.0, 0.0, 12.0])
                np.testing.assert_array_equal(data["contact_force_part_mask"], [[False, False], [True, False], [False, False]])
                force_meta = json.loads(str(data["motion_edit_force_metadata"].item()))
                gen_meta = json.loads(str(data["motion_edit_generation_metadata"].item()))

        self.assertEqual(result.output_motion_path, output)
        self.assertEqual(force_meta["force_source"], "prescribed_motion_contact_solve")
        self.assertFalse(force_meta["force_applied_to_body"])
        self.assertEqual(gen_meta["generation_mode"], "test")
        self.assertIn("contact_force_bake", gen_meta)

    def test_missing_joint_pos_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "motion.npz"
            np.savez(source, body_pos_w=np.zeros((2, 1, 3), dtype=np.float64))
            with self.assertRaisesRegex(ValueError, "missing joint_pos"):
                bake_prescribed_contact_forces_for_motion(source, backend=FakeBackend())


if __name__ == "__main__":
    unittest.main()
