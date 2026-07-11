from __future__ import annotations

import unittest

from motion_edit.generation.contact_aware_cli import build_parser, main


class ContactAwareCliTests(unittest.TestCase):
    def test_parser_only_exposes_force_retarget(self) -> None:
        args = build_parser().parse_args(
            [
                "--plan",
                "plan.json",
                "--output-motion",
                "out.npz",
                "--force-source-ref",
                "source.force.npz",
            ]
        )

        self.assertFalse(hasattr(args, "force_solve_mode"))
        self.assertEqual(args.force_source_ref, "source.force.npz")
        self.assertFalse(hasattr(args, "force_mujoco_model"))

    def test_force_retarget_requires_source_unless_disabled(self) -> None:
        with self.assertRaisesRegex(ValueError, "force retargeting requires"):
            main(["--plan", "plan.json", "--output-motion", "out.npz"])

    def test_dry_run_does_not_require_force_source(self) -> None:
        args = build_parser().parse_args(["--plan", "plan.json", "--output-motion", "out.npz", "--dry-run"])
        self.assertTrue(args.dry_run)


if __name__ == "__main__":
    unittest.main()
