"""Contact Editor application facade.

The implementation still lives in ``motion_edit.viewer.surface_overlay_player``
for compatibility with existing tests and imports. New code should import from
this package so the module can be split further without changing callers.
"""

from motion_edit.viewer.surface_overlay_player import build_arg_parser, main, run_contact_editor_setup_player, run_surface_overlay_player

__all__ = [
    "build_arg_parser",
    "main",
    "run_contact_editor_setup_player",
    "run_surface_overlay_player",
]
