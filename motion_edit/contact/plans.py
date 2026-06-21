from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Literal

from motion_edit.contact.schema import ContactAnchorEditRecord

ContactEditPlanStatus = Literal["draft", "validated", "locked", "generated"]


@dataclass(frozen=True)
class ContactEditPlan:
    plan_id: str
    source_motion_path: str
    source_motion_id: str
    source_contact_layer: str
    source_segment_layer: str | None = None
    edits: list[dict[str, Any]] = field(default_factory=list)
    status: ContactEditPlanStatus = "draft"
    output_motion_path: str | None = None
    output_contact_layer: str | None = None
    output_segment_layer: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self, *, allow_free: bool = False) -> None:
        validate_contact_edit_plan(self, allow_free=allow_free)

    def to_dict(self) -> dict[str, Any]:
        validate_contact_edit_plan(self, allow_free=True)
        return asdict(self)


def _edit_dict(edit: ContactAnchorEditRecord | dict[str, Any]) -> dict[str, Any]:
    if isinstance(edit, ContactAnchorEditRecord):
        return edit.to_dict()
    return dict(edit)


def write_contact_edit_plan(path: str | Path, plan: ContactEditPlan) -> Path:
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return out


def read_contact_edit_plan(path: str | Path) -> ContactEditPlan:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return ContactEditPlan(**data)


def append_anchor_edit_to_plan(
    path: str | Path,
    edit: ContactAnchorEditRecord | dict[str, Any],
    *,
    plan_id: str,
    source_motion_path: str,
    source_motion_id: str,
    source_contact_layer: str,
    source_segment_layer: str | None = None,
) -> ContactEditPlan:
    plan_path = Path(path).expanduser()
    if plan_path.exists():
        plan = read_contact_edit_plan(plan_path)
    else:
        plan = ContactEditPlan(
            plan_id=plan_id,
            source_motion_path=source_motion_path,
            source_motion_id=source_motion_id,
            source_contact_layer=source_contact_layer,
            source_segment_layer=source_segment_layer,
        )
    edits = list(plan.edits)
    edits.append(_edit_dict(edit))
    updated = ContactEditPlan(
        plan_id=plan.plan_id,
        source_motion_path=plan.source_motion_path,
        source_motion_id=plan.source_motion_id,
        source_contact_layer=plan.source_contact_layer,
        source_segment_layer=plan.source_segment_layer or source_segment_layer,
        edits=edits,
        status="draft" if plan.status == "validated" else plan.status,
        output_motion_path=plan.output_motion_path,
        output_contact_layer=plan.output_contact_layer,
        output_segment_layer=plan.output_segment_layer,
        metadata=dict(plan.metadata),
    )
    write_contact_edit_plan(plan_path, updated)
    return updated


def validate_contact_edit_plan(plan: ContactEditPlan, *, allow_free: bool = False) -> list[str]:
    if plan.status not in {"draft", "validated", "locked", "generated"}:
        raise ValueError(f"{plan.plan_id}: unsupported status {plan.status}")
    if not plan.source_motion_id:
        raise ValueError(f"{plan.plan_id}: source_motion_id is required")
    if not plan.source_contact_layer:
        raise ValueError(f"{plan.plan_id}: source_contact_layer is required")
    warnings: list[str] = []
    for index, raw_edit in enumerate(plan.edits):
        edit = ContactAnchorEditRecord(**raw_edit)
        edit.validate()
        if edit.affected_frames is not None:
            if len(edit.affected_frames) != 2:
                raise ValueError(f"{edit.edit_id}: affected_frames must be [start, end]")
            if edit.affected_frames[0] < 0 or edit.affected_frames[1] <= edit.affected_frames[0]:
                raise ValueError(f"{edit.edit_id}: affected_frames must be a valid positive interval")
        free_edit = edit.constraint_mode in {None, "free_3d"} or not edit.surface_id
        if free_edit and not allow_free:
            raise ValueError(f"{edit.edit_id}: edit {index} is not surface-constrained")
        if edit.surface_normal is not None and edit.delta_world is not None:
            normal_component = sum(float(edit.surface_normal[i]) * float(edit.delta_world[i]) for i in range(3))
            if abs(normal_component) > 1e-6:
                raise ValueError(f"{edit.edit_id}: effective delta has surface-normal displacement")
        if edit.constraint_mode == "reject" and edit.clamped:
            raise ValueError(f"{edit.edit_id}: reject-mode edit cannot be clamped")
        if edit.clamped:
            warnings.append(f"{edit.edit_id}: clamped to surface bounds")
    return warnings
