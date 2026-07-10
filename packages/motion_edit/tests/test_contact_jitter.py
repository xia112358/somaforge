from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from motion_edit.contact.jitter import generate_contact_jitter_plans


class ContactJitterPlanTests(unittest.TestCase):
    def test_generate_contact_jitter_plans_writes_surface_constrained_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layers = root / "data" / "layers"
            contact = layers / "contact" / "test_ready"
            motion_id = "motion_a"
            for name in ("anchors", "events", "patches", "transitions"):
                (contact / name).mkdir(parents=True, exist_ok=True)
                (contact / name / f"{motion_id}.jsonl").write_text("", encoding="utf-8")

            anchor = {
                "motion_id": motion_id,
                "anchor_id": "anchor_left_foot_0000_0010",
                "body": "left_foot",
                "start_frame": 0,
                "end_frame": 10,
                "editable": True,
                "world_position": [0.5, 0.5, 0.0],
                "surface_id": "box_top",
                "surface_type": "mesh_face",
                "surface_normal": [0.0, 0.0, 1.0],
                "surface_origin": [0.0, 0.0, 0.0],
                "surface_tangent_u": [1.0, 0.0, 0.0],
                "surface_tangent_v": [0.0, 1.0, 0.0],
                "surface_bounds": {"u": [0.0, 1.0], "v": [0.0, 1.0]},
                "surface_coordinates": {"u": 0.5, "v": 0.5},
                "metadata": {
                    "surface_bindings": [
                        {
                            "polygon_surface_coordinates": [
                                {"u": 0.0, "v": 0.0},
                                {"u": 1.0, "v": 0.0},
                                {"u": 1.0, "v": 1.0},
                                {"u": 0.0, "v": 1.0},
                            ]
                        }
                    ]
                },
            }
            (contact / "anchors" / f"{motion_id}.jsonl").write_text(
                json.dumps(anchor) + "\n",
                encoding="utf-8",
            )
            cut_summary = root / "cut_summary.json"
            cut_summary.write_text(
                json.dumps(
                    [
                        {
                            "status": "ok",
                            "motion_id": motion_id,
                            "motion_asset_id": "asset_a",
                            "motion_path": str(root / "motion.npz"),
                            "ready_layer": "contact/test_ready",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            with mock.patch("motion_edit.contact.jitter.LAYERS_ROOT", layers):
                results, stats = generate_contact_jitter_plans(
                    cut_summary,
                    root / "plans",
                    augmentations_per_motion=1,
                    offset_radius=0.05,
                    edit_probability=1.0,
                    seed=7,
                )

            self.assertEqual(stats["plan_count"], 1)
            self.assertEqual(len(results), 1)
            plan = json.loads(results[0].plan_path.read_text(encoding="utf-8"))
            self.assertEqual(plan["status"], "validated")
            self.assertEqual(len(plan["edits"]), 1)
            edit = plan["edits"][0]
            self.assertEqual(edit["constraint_mode"], "reject")
            self.assertFalse(edit["clamped"])
            self.assertEqual(edit["surface_id"], "box_top")
            self.assertAlmostEqual(edit["delta_world"][2], 0.0)
            after = edit["surface_coordinates_after"]
            self.assertGreaterEqual(after["u"], 0.0)
            self.assertLessEqual(after["u"], 1.0)
            self.assertGreaterEqual(after["v"], 0.0)
            self.assertLessEqual(after["v"], 1.0)


if __name__ == "__main__":
    unittest.main()
