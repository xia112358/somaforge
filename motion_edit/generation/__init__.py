"""Motion generation backends.

The public generation entry is ContactEditPlan -> ``lte_fullbody``. The
compatibility implementation currently lives in ``motion_edit.contact.generation``
and is re-exported here while the backend is split incrementally.
"""

from motion_edit.generation.lte_fullbody import LteGenerationResult, apply_contact_edit_plan_to_motion, resolve_body_index

__all__ = [
    "LteGenerationResult",
    "apply_contact_edit_plan_to_motion",
    "resolve_body_index",
]
