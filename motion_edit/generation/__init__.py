"""Motion generation backends.

The public generation entry is ContactEditPlan -> ``lte_fullbody``.
``motion_edit.contact.generation`` is kept as a compatibility wrapper.
"""

from motion_edit.generation.lte_fullbody import LteGenerationResult, apply_contact_edit_plan_to_motion, resolve_body_index

__all__ = [
    "LteGenerationResult",
    "apply_contact_edit_plan_to_motion",
    "resolve_body_index",
]
