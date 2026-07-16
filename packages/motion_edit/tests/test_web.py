from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.web.motion_data import load_contact_force_payload, load_motion_sequence
from motion_edit.web.server import WEB_DIST, create_app
from motion_edit.segmentation.cli import build_parser as build_segmentation_parser


class WebMotionDataTests(unittest.TestCase):
    def test_loads_named_motion_and_eight_part_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion.npz"
            qpos = np.zeros((3, 9), dtype=np.float32)
            force = np.zeros((3, 8, 3), dtype=np.float32)
            force[1, 0, 2] = 100.0
            np.savez(
                path,
                fps=np.asarray(50),
                joint_pos=qpos,
                joint_names=np.asarray(["joint_a", "joint_b"]),
                contact_force_part_order=np.asarray(["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"]),
                contact_force_part_w=force,
                contact_force_part_mask=np.linalg.norm(force, axis=-1) > 0,
                contact_force_part_position_w=np.zeros_like(force),
            )
            loaded, fps, names = load_motion_sequence(path)
            contacts = load_contact_force_payload(path, frame_count=3)
        self.assertEqual(loaded.shape, (3, 9))
        self.assertEqual(fps, 50)
        self.assertEqual(names, ("joint_a", "joint_b"))
        self.assertEqual(len(contacts["part_order"]), 8)
        self.assertTrue(contacts["masks"][1][0])

    def test_single_port_app_includes_api_and_built_frontend(self) -> None:
        app = create_app()
        paths = {route.path for route in app.routes}
        self.assertIn("/api/assets", paths)
        self.assertIn("/api/session/load", paths)
        self.assertIn("/api/session/move", paths)
        self.assertIn("/api/session/undo", paths)
        self.assertIn("/api/session/redo", paths)
        self.assertIn("/api/session/reset", paths)
        self.assertIn("/api/session/discard", paths)
        self.assertIn("/api/session/restore-anchor", paths)
        self.assertIn("/api/session/validate", paths)
        self.assertIn("/api/session/settings", paths)
        self.assertTrue((WEB_DIST / "index.html").is_file())

    def test_segmentation_cli_no_longer_imports_removed_cutter(self) -> None:
        parser = build_segmentation_parser()
        subparsers = next(action for action in parser._actions if action.dest == "cmd")
        self.assertNotIn("cutter", subparsers.choices)
        self.assertIn("start", subparsers.choices)


if __name__ == "__main__":
    unittest.main()
