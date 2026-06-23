"""Backward-compatible ContactEditPlan generation imports.

The implementation lives in :mod:`motion_edit.generation`. This module remains
so older tests and callers that import ``motion_edit.contact.generation`` keep
working.
"""

from motion_edit.generation.lte_fullbody import *  # noqa: F401,F403
