"""Motion generation backends.

The public generation entry is ContactEditPlan -> ``lte_fullbody``.
``motion_edit.contact.generation`` is kept as a compatibility wrapper.

Interactive Contact Editor generation supplies ``source_plan_path`` and does
not expose a solver selector. Those calls now use the unified
``batch_contact_laplacian`` backend by default. Programmatic and CLI callers can
still request either backend explicitly; only the legacy ``ik_subprocess`` path
uses the external LTE/IK subprocess.
"""

from __future__ import annotations

from typing import Any

from motion_edit.generation.lte_fullbody import (
    LteGenerationResult,
    apply_contact_edit_plan_to_motion as _apply_contact_edit_plan_to_motion,
    resolve_body_index,
)


def apply_contact_edit_plan_to_motion(*args: Any, **kwargs: Any) -> LteGenerationResult:
    if (
        kwargs.get("mode", "lte_fullbody") == "lte_fullbody"
        and "fullbody_solver" not in kwargs
        and kwargs.get("source_plan_path") is not None
    ):
        kwargs["fullbody_solver"] = "batch_contact_laplacian"
    return _apply_contact_edit_plan_to_motion(*args, **kwargs)


__all__ = [
    "LteGenerationResult",
    "apply_contact_edit_plan_to_motion",
    "resolve_body_index",
]
