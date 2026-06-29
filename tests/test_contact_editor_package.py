import unittest


class ContactEditorPackageTests(unittest.TestCase):
    def test_contact_editor_facade_imports_current_app(self) -> None:
        from motion_edit.viewer.contact_editor import SurfaceEditorController
        from motion_edit.viewer.contact_editor.app import build_arg_parser, run_surface_overlay_player

        self.assertTrue(callable(build_arg_parser))
        self.assertTrue(callable(run_surface_overlay_player))
        self.assertTrue(hasattr(SurfaceEditorController, "create"))


class GenerationPackageTests(unittest.TestCase):
    def test_contact_generation_facade_imports_current_generation_facade(self) -> None:
        from motion_edit.contact.generation import apply_contact_edit_plan_to_motion as legacy_apply
        from motion_edit.generation import apply_contact_edit_plan_to_motion

        self.assertIs(apply_contact_edit_plan_to_motion, legacy_apply)


if __name__ == "__main__":
    unittest.main()
