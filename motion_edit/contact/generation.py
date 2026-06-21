from __future__ import annotations

from pathlib import Path

from motion_edit.contact.plans import ContactEditPlan


def apply_contact_edit_plan_to_motion(
    plan: ContactEditPlan,
    *,
    output_motion_path: str | Path,
    mode: str = "stub",
) -> Path:
    raise NotImplementedError(
        f"contact edit plan generation is not implemented yet "
        f"(plan_id={plan.plan_id}, mode={mode}, output={Path(output_motion_path).expanduser()})"
    )
