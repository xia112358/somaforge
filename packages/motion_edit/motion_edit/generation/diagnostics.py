"""Internal generation diagnostics.

``lte_windowed`` is kept as a diagnostic/test path inside the lte_fullbody
implementation. It is intentionally not exposed as a public CLI mode.
"""

from motion_edit.generation.lte_fullbody import apply_contact_edit_plan_to_motion

__all__ = ["apply_contact_edit_plan_to_motion"]
