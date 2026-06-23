"""Backward-compatible import path for the local Viser Contact Editor.

The implementation lives in :mod:`motion_edit.viewer.contact_editor.app`.
This module aliases that implementation so existing imports and monkeypatches
against ``motion_edit.viewer.surface_overlay_player`` continue to affect the
same module object.
"""

from motion_edit.viewer.contact_editor import app as _app

import sys as _sys

_sys.modules[__name__] = _app
