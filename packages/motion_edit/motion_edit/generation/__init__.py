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

from motion_edit.generation.contact_semantic_aliases import install_lte_contact_semantic_aliases

install_lte_contact_semantic_aliases()

from motion_edit.generation.omni_contact_graph import install_omni_contact_graph

install_omni_contact_graph()

from motion_edit.generation.omni_contact_core import install_contact_core_nodes

install_contact_core_nodes()

from motion_edit.generation.omni_delaunay_cache import install_delaunay_topology_cache

install_delaunay_topology_cache()

from motion_edit.generation.omni_legacy_fallback import install_legacy_foot_fallbacks

install_legacy_foot_fallbacks()

from motion_edit.generation.omni_surface_mapping import install_surface_specific_object_mapping

install_surface_specific_object_mapping()

from motion_edit.contact.newton_shape_filter import install_strict_newton_shape_filter

install_strict_newton_shape_filter()

from motion_edit.generation.contact_target_contract import (
    install_authoritative_contact_target_contract,
)

install_authoritative_contact_target_contract()

from motion_edit.generation.contact_aware import ContactAwareGenerationResult, apply_contact_aware_edit_plan_to_motion
from motion_edit.generation.contact_aware_preview import (
    ContactAwarePreviewResult,
    generate_contact_aware_pyroki_preview,
)
from motion_edit.generation.omni_generation_defaults import install_generation_defaults

install_generation_defaults(generate_contact_aware_pyroki_preview)

from motion_edit.generation.contact_force_bake import (
    ContactForceBakeResult,
    bake_retargeted_contact_forces_for_motion,
)
from motion_edit.generation.lte_fullbody import (
    LteGenerationResult,
    apply_contact_edit_plan_to_motion as _apply_contact_edit_plan_to_motion,
    resolve_body_index,
)
from motion_edit.generation.taskspace_builder import build_contact_aware_taskspace_motion
from motion_edit.generation.taskspace_spec import (
    ContactAwareTaskspaceMotion,
    ContactPatchTarget,
    make_boundary_weights,
    read_contact_aware_taskspace_motion,
    write_contact_aware_taskspace_motion,
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
    "ContactAwareGenerationResult",
    "ContactAwarePreviewResult",
    "ContactAwareTaskspaceMotion",
    "ContactForceBakeResult",
    "ContactPatchTarget",
    "LteGenerationResult",
    "apply_contact_aware_edit_plan_to_motion",
    "apply_contact_edit_plan_to_motion",
    "bake_retargeted_contact_forces_for_motion",
    "build_contact_aware_taskspace_motion",
    "generate_contact_aware_pyroki_preview",
    "make_boundary_weights",
    "read_contact_aware_taskspace_motion",
    "resolve_body_index",
    "write_contact_aware_taskspace_motion",
]
