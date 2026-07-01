from __future__ import annotations

import unittest

from motion_edit.contact_force.cli import build_parser, main


class ContactForceBakeCliTests(unittest.TestCase):
    def test_parser_accepts_required_force_bake_args(self) -> None:
        args = build_parser().parse_args(
            [
                "--motion",
                "motion.npz",
                "--output-motion",
                "motion.force.npz",
                "--mujoco-model",
                "robot.xml",
            ]
        )

        self.assertEqual(args.motion, "motion.npz")
        self.assertEqual(args.output_motion, "motion.force.npz")
        self.assertEqual(args.mujoco_model, "robot.xml")
        self.assertEqual(args.solve_mode, "forward")

    def test_requires_output_or_in_place_before_running_backend(self) -> None:
        with self.assertRaisesRegex(ValueError, "--output-motion or --in-place"):
            main(["--motion", "motion.npz", "--mujoco-model", "robot.xml"])

    def test_output_and_in_place_are_mutually_exclusive(self) -> None:
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            main(
                [
                    "--motion",
                    "motion.npz",
                    "--output-motion",
                    "motion.force.npz",
                    "--in-place",
                    "--mujoco-model",
                    "robot.xml",
                ]
            )


if __name__ == "__main__":
    unittest.main()
