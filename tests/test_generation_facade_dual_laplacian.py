from __future__ import annotations

import unittest
from unittest import mock

import motion_edit.generation as generation


class GenerationFacadeDualLaplacianTests(unittest.TestCase):
    def test_editor_generation_defaults_to_batch_contact_laplacian(self) -> None:
        sentinel = object()
        with mock.patch.object(generation, "_apply_contact_edit_plan_to_motion", return_value=sentinel) as apply_mock:
            result = generation.apply_contact_edit_plan_to_motion(
                object(),
                output_motion_path="out.npz",
                mode="lte_fullbody",
                source_plan_path="plan.json",
            )

        self.assertIs(result, sentinel)
        self.assertEqual(apply_mock.call_args.kwargs["fullbody_solver"], "batch_contact_laplacian")

    def test_explicit_solver_is_preserved(self) -> None:
        sentinel = object()
        with mock.patch.object(generation, "_apply_contact_edit_plan_to_motion", return_value=sentinel) as apply_mock:
            result = generation.apply_contact_edit_plan_to_motion(
                object(),
                output_motion_path="out.npz",
                mode="lte_fullbody",
                source_plan_path="plan.json",
                fullbody_solver="ik_subprocess",
            )

        self.assertIs(result, sentinel)
        self.assertEqual(apply_mock.call_args.kwargs["fullbody_solver"], "ik_subprocess")

    def test_legacy_direct_call_keeps_underlying_default(self) -> None:
        sentinel = object()
        with mock.patch.object(generation, "_apply_contact_edit_plan_to_motion", return_value=sentinel) as apply_mock:
            result = generation.apply_contact_edit_plan_to_motion(
                object(),
                output_motion_path="out.npz",
                mode="lte_fullbody",
            )

        self.assertIs(result, sentinel)
        self.assertNotIn("fullbody_solver", apply_mock.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
