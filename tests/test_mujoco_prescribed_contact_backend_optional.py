from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.contact_force import MuJoCoPrescribedContactBackend, PrescribedContactSolveConfig, solve_prescribed_contact_forces


MJCF = """
<mujoco model="prescribed_contact_smoke">
  <option timestep="0.01" gravity="0 0 -9.81"/>
  <worldbody>
    <geom name="ground" type="plane" size="1 1 0.1"/>
    <body name="left_foot" pos="0 0 0.02">
      <freejoint/>
      <geom name="left_foot_geom" type="sphere" size="0.05"/>
    </body>
  </worldbody>
</mujoco>
""".strip()


class MuJoCoPrescribedBackendOptionalTests(unittest.TestCase):
    def test_mujoco_backend_queries_contacts_without_stepping(self) -> None:
        try:
            import mujoco  # noqa: F401
        except ImportError:
            self.skipTest("optional mujoco package is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.xml"
            model_path.write_text(MJCF, encoding="utf-8")
            backend = MuJoCoPrescribedContactBackend(model_path)
            qpos = np.asarray([[0.0, 0.0, 0.02, 1.0, 0.0, 0.0, 0.0]], dtype=np.float64)
            field = solve_prescribed_contact_forces(
                qpos,
                backend,
                PrescribedContactSolveConfig(part_order=("left_foot",)),
                contact_mask=np.asarray([[True]], dtype=bool),
                contact_part_position_w=np.asarray([[[0.0, 0.0, 0.0]]], dtype=np.float64),
            )

        self.assertEqual(field.metadata["force_source"], "prescribed_motion_contact_solve")
        self.assertFalse(field.metadata["force_applied_to_body"])
        self.assertFalse(field.metadata["integrated"])
        self.assertGreaterEqual(field.metadata["backend_sample_count"], 1)
        self.assertEqual(field.force_w.shape, (1, 1, 3))


if __name__ == "__main__":
    unittest.main()
