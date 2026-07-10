"""Backward-compatible ContactEditPlan generation imports.

The implementation lives in :mod:`motion_edit.generation`. This module remains
so older tests and callers that import ``motion_edit.contact.generation`` keep
working with the same public facade and editor-default solver selection.
"""

from motion_edit.generation import *  # noqa: F401,F403
