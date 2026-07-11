from __future__ import annotations

import unittest

from motion_edit.contact_force.cli import build_parser, main


class ContactForceBakeCliTests(unittest.TestCase):
    def test_parser_only_accepts_newton_force_retarget(self) -> None:
        args = build_parser().parse_args(
            [
                "--motion",
                "motion.npz",
                "--output-motion",
                "motion.force.npz",
                "--source-force-ref",
                "source.force.npz",
            ]
        )

        self.assertEqual(args.source_force_ref, "source.force.npz")
        self.assertFalse(hasattr(args, "mujoco_model"))

    def test_requires_output_or_in_place(self) -> None:
        with self.assertRaisesRegex(ValueError, "--output-motion or --in-place"):
            main(["--motion", "motion.npz", "--source-force-ref", "source.force.npz"])

    def test_output_and_in_place_are_mutually_exclusive(self) -> None:
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            main(
                [
                    "--motion",
                    "motion.npz",
                    "--output-motion",
                    "motion.force.npz",
                    "--in-place",
                    "--source-force-ref",
                    "source.force.npz",
                ]
            )

    def test_retarget_requires_source_force_ref(self) -> None:
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--motion", "motion.npz", "--output-motion", "motion.force.npz"])


if __name__ == "__main__":
    unittest.main()
