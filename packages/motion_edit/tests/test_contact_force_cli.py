from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from motion_edit.contact_force.cli import build_parser, main
from motion_edit.contact_force.cli import _load_name_part_map


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
        self.assertEqual(args.policy_ref_compat, "wbt_contact_force_8part")

    def test_parser_accepts_retarget_force_args_without_mujoco(self) -> None:
        args = build_parser().parse_args(
            [
                "--motion",
                "motion.npz",
                "--output-motion",
                "motion.force.npz",
                "--solve-mode",
                "retarget",
                "--source-force-ref",
                "source.force.npz",
                "--target-contact-layer",
                "data/layers/contact/target",
                "--target-motion-id",
                "motion_a",
            ]
        )

        self.assertEqual(args.solve_mode, "retarget")
        self.assertEqual(args.source_force_ref, "source.force.npz")
        self.assertEqual(args.target_contact_layer, "data/layers/contact/target")
        self.assertEqual(args.target_motion_id, "motion_a")
        self.assertIsNone(args.mujoco_model)

    def test_parser_accepts_part_map_files(self) -> None:
        args = build_parser().parse_args(
            [
                "--motion",
                "motion.npz",
                "--output-motion",
                "motion.force.npz",
                "--mujoco-model",
                "robot.xml",
                "--geom-part-map",
                "geom.json",
                "--body-part-map",
                "body.json",
            ]
        )

        self.assertEqual(args.geom_part_map, "geom.json")
        self.assertEqual(args.body_part_map, "body.json")

    def test_load_name_part_map_requires_string_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "map.json"
            path.write_text('{"left_toe_geom": "left_foot"}', encoding="utf-8")

            self.assertEqual(_load_name_part_map(str(path), label="geom-part-map"), {"left_toe_geom": "left_foot"})

            path.write_text('["left_toe_geom"]', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                _load_name_part_map(str(path), label="geom-part-map")

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

    def test_retarget_requires_source_force_ref_before_running_backend(self) -> None:
        with self.assertRaisesRegex(ValueError, "--source-force-ref"):
            main(["--motion", "motion.npz", "--output-motion", "motion.force.npz", "--solve-mode", "retarget"])


if __name__ == "__main__":
    unittest.main()
