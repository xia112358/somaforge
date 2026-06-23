import unittest


class ContactEditorPackageTests(unittest.TestCase):
    def test_contact_editor_facade_imports_current_app(self) -> None:
        from motion_edit.viewer.contact_editor import SurfaceEditorController
        from motion_edit.viewer.contact_editor.app import build_arg_parser, run_surface_overlay_player

        self.assertTrue(callable(build_arg_parser))
        self.assertTrue(callable(run_surface_overlay_player))
        self.assertTrue(hasattr(SurfaceEditorController, "create"))


if __name__ == "__main__":
    unittest.main()
