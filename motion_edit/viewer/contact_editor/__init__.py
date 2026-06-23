"""Local Viser Contact Editor entry points.

The public UI workflow should enter through ``motion-edit contact-editor``.
This package provides the structured import surface for that editor while the
legacy ``surface_overlay_player`` module remains as the compatibility
implementation during the incremental split.
"""

from motion_edit.viewer.contact_editor.app import build_arg_parser, main, run_contact_editor_setup_player, run_surface_overlay_player
from motion_edit.viewer.contact_editor.controller import SurfaceEditorController, SurfaceOverlayEditorState

__all__ = [
    "SurfaceEditorController",
    "SurfaceOverlayEditorState",
    "build_arg_parser",
    "main",
    "run_contact_editor_setup_player",
    "run_surface_overlay_player",
]
