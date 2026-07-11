from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from motion_edit.contact.plans import ContactEditPlan
from motion_edit.generation.contact_aware import apply_contact_aware_edit_plan_to_motion
from motion_edit.generation.contact_force_bake import ContactForceBakeResult
from motion_edit.generation.lte_fullbody import LteGenerationResult


class ContactAwareGenerationTests(unittest.TestCase):
    def test_runs_generation_then_force_bake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generated = root / "generated.npz"
            force_out = root / "generated.force.npz"
            plan = ContactEditPlan(
                plan_id="plan_a",
                source_motion_path="source.npz",
                source_motion_id="motion_a",
                source_contact_layer="contact/source",
                status="validated",
            )
            calls: dict[str, Any] = {}

            def fake_generation(*args: Any, **kwargs: Any) -> LteGenerationResult:
                calls["generation"] = kwargs
                return LteGenerationResult(output_motion_path=Path(kwargs["output_motion_path"]), warnings=["gen warning"])

            def fake_force_bake(*args: Any, **kwargs: Any) -> ContactForceBakeResult:
                calls["force"] = {"args": args, "kwargs": kwargs}
                return ContactForceBakeResult(output_motion_path=Path(kwargs["output_motion_path"]), metadata={"ok": True}, warnings=["force warning"])

            result = apply_contact_aware_edit_plan_to_motion(
                plan,
                output_motion_path=generated,
                bake_force=True,
                force_output_motion_path=force_out,
                force_source_ref_path="source.force.npz",
                force_policy_ref_compat="none",
                overwrite=True,
                source_plan_path="plan.json",
                _generation_fn=fake_generation,
                _force_bake_fn=fake_force_bake,
            )

        self.assertEqual(result.output_motion_path, force_out)
        self.assertEqual(result.warnings, ["gen warning", "force warning"])
        self.assertEqual(calls["generation"]["fullbody_solver"], "batch_contact_laplacian")
        self.assertEqual(calls["generation"]["mode"], "lte_fullbody")
        self.assertEqual(calls["force"]["args"][0], generated)
        self.assertEqual(calls["force"]["kwargs"]["source_force_ref_path"], "source.force.npz")
        self.assertEqual(calls["force"]["kwargs"]["max_force_norm"], 5000.0)
        self.assertEqual(calls["force"]["kwargs"]["policy_ref_compat"], "none")
        self.assertTrue(calls["force"]["kwargs"]["overwrite"])

    def test_dry_run_skips_force_bake(self) -> None:
        plan = ContactEditPlan(
            plan_id="plan_a",
            source_motion_path="source.npz",
            source_motion_id="motion_a",
            source_contact_layer="contact/source",
            status="validated",
        )

        def fake_generation(*args: Any, **kwargs: Any) -> LteGenerationResult:
            return LteGenerationResult(output_motion_path=Path(kwargs["output_motion_path"]))

        def unexpected_force_bake(*args: Any, **kwargs: Any) -> ContactForceBakeResult:
            raise AssertionError("force bake should be skipped on dry-run")

        result = apply_contact_aware_edit_plan_to_motion(
            plan,
            output_motion_path="generated.npz",
            dry_run=True,
            _generation_fn=fake_generation,
            _force_bake_fn=unexpected_force_bake,
        )

        self.assertIsNone(result.force_bake)
        self.assertEqual(result.output_motion_path, Path("generated.npz"))

    def test_retarget_force_defaults_to_plan_source_motion(self) -> None:
        plan = ContactEditPlan(
            plan_id="plan_a",
            source_motion_path="source.npz",
            source_motion_id="motion_a",
            source_contact_layer="contact/source",
            status="validated",
        )
        calls: dict[str, Any] = {}

        def fake_generation(*args: Any, **kwargs: Any) -> LteGenerationResult:
            return LteGenerationResult(output_motion_path=Path(kwargs["output_motion_path"]))

        def fake_force_bake(*args: Any, **kwargs: Any) -> ContactForceBakeResult:
            calls["force"] = kwargs
            return ContactForceBakeResult(output_motion_path=Path(kwargs["output_motion_path"]), metadata={"ok": True}, warnings=[])

        apply_contact_aware_edit_plan_to_motion(
            plan,
            output_motion_path="generated.npz",
            bake_force=True,
            force_target_contact_layer_path="data/layers/contact/target",
            force_target_motion_id="motion_a",
            _generation_fn=fake_generation,
            _force_bake_fn=fake_force_bake,
        )

        self.assertEqual(calls["force"]["source_force_ref_path"], "source.npz")
        self.assertEqual(calls["force"]["target_contact_layer_path"], "data/layers/contact/target")
        self.assertEqual(calls["force"]["target_motion_id"], "motion_a")


if __name__ == "__main__":
    unittest.main()
