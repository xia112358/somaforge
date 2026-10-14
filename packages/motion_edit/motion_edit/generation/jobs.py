"""The shared editor/CLI candidate generation contract and provenance receipt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

from motion_edit.contact.plans import read_contact_edit_plan
from motion_edit.generation.contract import validate_generation_metadata
from motion_edit.generation.contact_aware_preview import ContactAwarePreviewResult


def generate_candidate(
    plan_path: str | Path,
    *,
    output_motion_path: str | Path,
    generation_fn: Callable[..., ContactAwarePreviewResult] | None = None,
    source_prefix_config: str | Path | None = None,
    **options,
) -> ContactAwarePreviewResult:
    from motion_edit.generation import generate_contact_aware_pyroki_preview

    path = Path(plan_path).expanduser().resolve()
    plan_bytes = path.read_bytes()
    plan = read_contact_edit_plan(path)
    validate_generation_metadata(plan.metadata)
    from .source_prefix_reference import (
        configure_plan_prefix, load_prefix_configuration, prefix_implementation_fingerprints,
        verify_prefix_diagnostics,
    )
    prefix_provenance = None
    if source_prefix_config is not None:
        config, prefix_provenance = load_prefix_configuration(source_prefix_config)
        plan = configure_plan_prefix(plan, config, prefix_provenance)
        plan_bytes = json.dumps(plan.to_dict(), sort_keys=True, allow_nan=False).encode()
    else:
        plan = configure_plan_prefix(plan)
    expected_prefix = plan.metadata.get("source_prefix_reference")
    if expected_prefix is not None:
        plan_bytes = json.dumps(plan.to_dict(), sort_keys=True, allow_nan=False).encode()
    result = (generation_fn or generate_contact_aware_pyroki_preview)(
        plan if expected_prefix is not None else path, output_motion_path=output_motion_path, **options,
    )
    if result.diagnostics.get("augmentation_objective") != plan.metadata["augmentation_objective"]:
        raise ValueError("Generated IK objective does not match its plan")
    if result.diagnostics.get("free_surface_contacts") is not True:
        raise ValueError("Generated IK surface tasks do not match its plan")
    verify_prefix_diagnostics(result.diagnostics, expected_prefix, plan.metadata.get("root_yaw_condition"))
    snapshot = result.output_motion_path.with_suffix(".generation.plan.json")
    snapshot.write_bytes(plan_bytes)
    receipt = {
        "plan": str(snapshot.resolve()),
        "authored_plan": str(path),
        "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "motion": str(result.output_motion_path.resolve()),
        "taskspace": str(result.taskspace_spec_path.resolve()),
        "ik_artifact": str(result.ik_output_path.resolve()),
        "diagnostics": result.diagnostics,
        "training_ready": False,
        "status": "requires_native_validation",
        "backend": "contact_aware_rollout_authority",
        "source_prefix_reference": expected_prefix,
        "root_yaw_condition": plan.metadata.get("root_yaw_condition"),
        "source_prefix_configuration": prefix_provenance or plan.metadata.get("source_prefix_configuration"),
        "source_prefix_implementation": prefix_implementation_fingerprints() if expected_prefix else None,
    }
    result.output_motion_path.with_suffix(".generation.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8",
    )
    return result
