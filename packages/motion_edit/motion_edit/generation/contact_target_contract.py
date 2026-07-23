from __future__ import annotations

from dataclasses import replace
import importlib
from typing import Any, Mapping

import numpy as np


_INSTALLED = False
_ORIGINAL_BUILD: Any | None = None


def _edit_world_delta(edit: Any) -> np.ndarray | None:
    value = getattr(edit, "delta_world", None)
    if value is not None:
        delta = np.asarray(value, dtype=np.float64)
    else:
        before = getattr(edit, "old_world_position", None)
        after = getattr(edit, "new_world_position", None)
        if before is None or after is None:
            return None
        delta = np.asarray(after, dtype=np.float64) - np.asarray(
            before,
            dtype=np.float64,
        )
    if delta.shape != (3,) or not np.all(np.isfinite(delta)):
        return None
    return delta


def _effective_surface_id(edit: Any, anchors_by_id: Mapping[str, Any]) -> str | None:
    value = getattr(edit, "surface_id", None)
    if value:
        return str(value)
    anchor = anchors_by_id.get(str(getattr(edit, "anchor_id", "")))
    if anchor is None:
        return None
    value = getattr(anchor, "surface_id", None)
    return str(value) if value else None


def build_contact_aware_taskspace_motion(*args: Any, **kwargs: Any):
    """Compile patch targets with the same world displacement as semantic handles.

    Surface metadata remains available for diagnostics, but an edit that exposes
    a finite world delta is represented as

    ``target_patch_w = source_patch_w + edit_delta_world``.

    This preserves the source semantic-to-patch rigid offset and gives the
    Laplacian handle and downstream rigid patch IK the same translation contract.
    """

    if _ORIGINAL_BUILD is None:
        raise RuntimeError("authoritative contact-target wrapper is not installed")

    anchors = tuple(kwargs.get("anchors", ()) or ())
    edits = tuple(kwargs.get("edits", ()) or ())
    surfaces = tuple(kwargs.get("surfaces", ()) or ())
    anchors_by_id = {str(anchor.anchor_id): anchor for anchor in anchors}

    edits_by_surface: dict[str, list[Any]] = {}
    for edit in edits:
        surface_id = _effective_surface_id(edit, anchors_by_id)
        if surface_id is not None:
            edits_by_surface.setdefault(surface_id, []).append(edit)

    # Removing a surface from the original builder's lookup selects its explicit
    # world-delta branch. Only do this when every edit using that surface exposes
    # a valid world displacement.
    translated_surface_ids = {
        surface_id
        for surface_id, grouped_edits in edits_by_surface.items()
        if grouped_edits
        and all(_edit_world_delta(edit) is not None for edit in grouped_edits)
    }
    filtered_surfaces = tuple(
        surface
        for surface in surfaces
        if str(getattr(surface, "surface_id", "")) not in translated_surface_ids
    )

    call_kwargs = dict(kwargs)
    call_kwargs["surfaces"] = filtered_surfaces
    spec = _ORIGINAL_BUILD(*args, **call_kwargs)

    edits_by_anchor = {
        str(getattr(edit, "anchor_id", "")): edit
        for edit in edits
    }
    updated_contacts = []
    translated_anchor_ids: list[str] = []
    for contact in spec.contacts:
        edit = edits_by_anchor.get(str(contact.anchor_id))
        delta = _edit_world_delta(edit) if edit is not None else None
        effective_surface = (
            _effective_surface_id(edit, anchors_by_id)
            if edit is not None
            else None
        )
        use_translation_contract = (
            contact.kind == "edited_contact"
            and delta is not None
            and effective_surface in translated_surface_ids
        )
        if not use_translation_contract:
            updated_contacts.append(contact)
            continue

        if contact.target_points_w is None or contact.target_uv is not None:
            raise ValueError(
                f"{contact.anchor_id}: edited contact did not compile to an "
                "explicit world-translation target"
            )
        metadata = dict(contact.metadata)
        metadata.update(
            {
                "target_contract": "source_patch_world_plus_edit_delta_world",
                "authoritative_delta_world": delta.astype(float).tolist(),
                "semantic_patch_displacement_contract": "same_world_delta",
                "source_surface_id": effective_surface,
            }
        )
        updated_contacts.append(replace(contact, metadata=metadata))
        translated_anchor_ids.append(str(contact.anchor_id))

    metadata = dict(spec.metadata)
    metadata.update(
        {
            "contact_target_contract": (
                "edited_patch_target_equals_source_patch_plus_semantic_edit_delta"
            ),
            "translated_surface_ids": sorted(translated_surface_ids),
            "translated_contact_anchor_ids": sorted(translated_anchor_ids),
            "semantic_patch_displacement_contract": "same_world_delta",
        }
    )
    resolved = replace(
        spec,
        contacts=tuple(updated_contacts),
        metadata=metadata,
    )
    resolved.validate()
    return resolved


def install_authoritative_contact_target_contract() -> None:
    global _INSTALLED, _ORIGINAL_BUILD
    if _INSTALLED:
        return
    builder = importlib.import_module("motion_edit.generation.taskspace_builder")
    _ORIGINAL_BUILD = builder.build_contact_aware_taskspace_motion
    builder.build_contact_aware_taskspace_motion = (
        build_contact_aware_taskspace_motion
    )
    _INSTALLED = True
