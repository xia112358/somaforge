from __future__ import annotations

import unittest

from motion_edit.generation.contact_aware_cli import build_parser, main


class ContactAwareCliTests(unittest.TestCase):
    def test_parser_accepts_contact_aware_args(self) -> None:
        args = build_parser().parse_args(
            [
                "--plan",
                "plan.json",
                "--output-motion",
                "out.npz",
                "--force-mujoco-model",
                "robot.xml",
                "--force-solve-mode",
                "inverse",
            ]
        )

        self.assertEqual(args.plan, "plan.json")
        self.assertEqual(args.output_motion, "out.npz")
        self.assertEqual(args.force_mujoco_model, "robot.xml")
        self.assertEqual(args.force_solve_mode, "inverse")

    def test_force_bake_requires_model_unless_disabled(self) -> None:
        with self.assertRaisesRegex(ValueError, "force baking requires"):
            main(["--plan", "plan.json", "--output-motion", "out.npz"])

    def test_dry_run_does_not_require_force_model(self) -> None:
        args = build_parser().parse_args(["--plan", "plan.json", "--output-motion", "out.npz", "--dry-run"])
        self.assertTrue(args.dry_run)
        self.assertIsNone(args.force_mujoco_model)


if __name__ == "__main__":
    unittest.main()
