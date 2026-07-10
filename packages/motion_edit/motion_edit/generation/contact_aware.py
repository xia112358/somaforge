from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from motion_edit.contact.plans import ContactEditPlan
from motion_edit.generation.contact_force_bake import ContactForceBakeResult, bake_prescribed_contact_forces_for_motion
from motion_edit.generation.lte_fullbody import LteGenerationResult, apply_contact_edit_plan_to_motion


@dataclass(frozen=True)
class ContactAwareGenerationResult:
    """Combined result for generated kinematics followed by force-ref writing."""

    generation: LteGenerationResult
    force_bake: ContactForceBakeResult | None = None

    @property
    def output_motion_path(self) -> Path:
        return self.force_bake.output_motion_path if self.force_bake is not None else self.generation.output_motion_path

    @property
    def warnings(self) -> list[str]:
        return [*(self.generation.warnings or []), *((self.force_bake.warnings if self.force_bake is not None else []))]


def apply_contact_aware_edit_plan_to_motion(
    plan: ContactEditPlan,
    *,
    output_motion_path: str | Path,
    bake_force: bool = True,
    force_output_motion_path: str | Path | None = None,
    force_backend: Any | None = None,
    force_mujoco_model_path: str | Path | None = None,
    force_source_ref_path: str | Path | None = None,
    force_target_contact_layer_path: str | Path | None = None,
    force_target_motion_id: str | None = None,
    force_geom_part_map: dict[str, str] | None = None,
    force_body_part_map: dict[str, str] | None = None,
    force_solve_mode: str = "forward",
    force_assignment_max_distance: float = 0.35,
    force_unit_scale: float = 1.0,
    force_retarget_max_force_norm: float | None = 5000.0,
    force_retarget_smoothing_window: int = 3,
    force_policy_ref_compat: str = "wbt_contact_force_6part",
    overwrite: bool = False,
    _generation_fn: Callable[..., LteGenerationResult] | None = None,
    _force_bake_fn: Callable[..., ContactForceBakeResult] | None = None,
    **generation_kwargs: Any,
) -> ContactAwareGenerationResult:
    """Run contact-aware force-ref generation: kinematics first, force reference second.

    Geometry retargeting remains delegated to the existing fullbody generation
    path. The force stage can be a prescribed-contact diagnostic solve or
    contact-phase force retargeting; neither mode runs a rollout or feeds forces
    back into the body state. The formal CLI uses retarget mode through
    ``motion-edit generate-ref``.
    """

    generator = _generation_fn or apply_contact_edit_plan_to_motion
    force_baker = _force_bake_fn or bake_prescribed_contact_forces_for_motion
    resolved_force_source_ref_path = force_source_ref_path
    if str(force_solve_mode) == "retarget" and resolved_force_source_ref_path is None:
        resolved_force_source_ref_path = plan.source_motion_path
    generation_kwargs.setdefault("mode", "lte_fullbody")
    generation_kwargs.setdefault("fullbody_solver", "batch_contact_laplacian")
    generation = generator(
        plan,
        output_motion_path=output_motion_path,
        overwrite=overwrite,
        **generation_kwargs,
    )
    if not bake_force or bool(generation_kwargs.get("dry_run", False)):
        return ContactAwareGenerationResult(generation=generation, force_bake=None)
    force_out = Path(force_output_motion_path).expanduser() if force_output_motion_path is not None else generation.output_motion_path
    force_bake_result = force_baker(
        generation.output_motion_path,
        output_motion_path=force_out,
        backend=force_backend,
        mujoco_model_path=force_mujoco_model_path,
        source_force_ref_path=resolved_force_source_ref_path,
        target_contact_layer_path=force_target_contact_layer_path,
        target_motion_id=force_target_motion_id,
        geom_part_map=force_geom_part_map,
        body_part_map=force_body_part_map,
        solve_mode=force_solve_mode,
        assignment_max_distance=force_assignment_max_distance,
        force_unit_scale=force_unit_scale,
        retarget_max_force_norm=force_retarget_max_force_norm,
        retarget_smoothing_window=force_retarget_smoothing_window,
        policy_ref_compat=force_policy_ref_compat,
        overwrite=overwrite or force_out == generation.output_motion_path,
    )
    return ContactAwareGenerationResult(generation=generation, force_bake=force_bake_result)
