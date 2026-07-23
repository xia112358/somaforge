from __future__ import annotations

from dataclasses import replace
import sys
from typing import Any, Mapping, Sequence

import numpy as np

from . import newton_bindings as _legacy
from .schema import ContactAnchorRecord, ContactPatchRecord


_ORIGINAL_BIND_NEWTON_CONTACT_PATCHES = _legacy.bind_newton_contact_patches
_INSTALLED = False


def _anchor_raw_shape_ids(anchor: ContactAnchorRecord) -> tuple[int, ...]:
    metadata = anchor.metadata if isinstance(anchor.metadata, Mapping) else {}
    subcontact = metadata.get("foot_subcontact")
    if not isinstance(subcontact, Mapping):
        return ()
    raw = subcontact.get("raw_shape_ids")
    if raw is None:
        return ()
    values = np.asarray(raw, dtype=object).reshape(-1).tolist()
    resolved: set[int] = set()
    for value in values:
        try:
            resolved.add(int(value))
        except (TypeError, ValueError):
            continue
    return tuple(sorted(resolved))


def _filtered_motion_for_anchor(
    anchor: ContactAnchorRecord,
    motion: Mapping[str, Any],
) -> tuple[Mapping[str, Any], tuple[int, ...], int]:
    allowed_shape_ids = _anchor_raw_shape_ids(anchor)
    if not allowed_shape_ids:
        return motion, (), 0

    shape0 = np.asarray(motion["raw_contact_shape0"])
    shape1 = np.asarray(motion["raw_contact_shape1"])
    body0 = np.asarray(motion["raw_contact_body0"])
    body1 = np.asarray(motion["raw_contact_body1"])
    if shape0.shape != shape1.shape or body0.shape != shape0.shape or body1.shape != shape0.shape:
        raise ValueError("raw contact shape/body arrays must have identical shapes for strict shape filtering")

    allowed = np.asarray(allowed_shape_ids, dtype=np.int64)
    keep = np.isin(shape0, allowed) | np.isin(shape1, allowed)

    filtered = dict(motion)
    filtered_body0 = body0.copy()
    filtered_body1 = body1.copy()
    filtered_body0[~keep] = -1
    filtered_body1[~keep] = -1
    filtered["raw_contact_body0"] = filtered_body0
    filtered["raw_contact_body1"] = filtered_body1

    start = max(0, min(keep.shape[0], int(anchor.start_frame)))
    end = max(start, min(keep.shape[0], int(anchor.end_frame)))
    filtered_count = 0
    counts = np.asarray(motion["raw_contact_count"], dtype=np.int64)
    for frame in range(start, end):
        active = max(0, min(int(counts[frame]), keep.shape[1]))
        filtered_count += int(np.count_nonzero(~keep[frame, :active]))
    return filtered, allowed_shape_ids, filtered_count


def bind_newton_contact_patches(
    anchors: Sequence[ContactAnchorRecord],
    motion: Mapping[str, Any],
    *,
    source_recording_path: str | None = None,
    min_force_norm: float = 0.0,
) -> tuple[list[ContactPatchRecord], dict[str, Any]]:
    """Bind Newton patches with strict per-anchor raw shape identity.

    Split heel/toe anchors carry ``metadata.foot_subcontact.raw_shape_ids``.
    When present, contacts from every other shape are removed before invoking
    the established Newton body/point reconstruction. Anchors without this
    metadata retain the legacy compatibility behavior.
    """

    patches: list[ContactPatchRecord] = []
    warnings: list[str] = []
    bound_count = 0
    raw_sample_count = 0
    strict_anchor_count = 0
    filtered_sample_count = 0
    selected_env_id: int | None = None
    shape_filters: dict[str, list[int]] = {}

    for anchor in anchors:
        filtered_motion, allowed_shape_ids, removed = _filtered_motion_for_anchor(anchor, motion)
        anchor_patches, summary = _ORIGINAL_BIND_NEWTON_CONTACT_PATCHES(
            [anchor],
            filtered_motion,
            source_recording_path=source_recording_path,
            min_force_norm=min_force_norm,
        )
        patch = anchor_patches[0]
        if allowed_shape_ids:
            strict_anchor_count += 1
            filtered_sample_count += int(removed)
            shape_filters[anchor.anchor_id] = list(allowed_shape_ids)
            metadata = dict(patch.metadata)
            metadata["foot_subcontact_shape_filter"] = {
                "mode": "strict_raw_shape_ids",
                "raw_shape_ids": list(allowed_shape_ids),
                "filtered_raw_contact_count": int(removed),
            }
            patch = replace(patch, metadata=metadata)
            if patch.robot_binding_source != "newton_raw_contact":
                warnings.append(
                    f"{anchor.anchor_id}: strict raw_shape_ids={list(allowed_shape_ids)} produced no Newton patch"
                )

        patches.append(patch)
        warnings.extend(str(item) for item in summary.get("warnings", []))
        bound_count += int(summary.get("bound_patch_count", 0))
        raw_sample_count += int(summary.get("raw_sample_count", 0))
        if selected_env_id is None:
            selected_env_id = int(summary.get("selected_env_id", 0))

    result = {
        "backend": "newton_mjwarp",
        "point_body_pairing": "body0->point1,body1->point0",
        "selected_env_id": int(selected_env_id or 0),
        "anchor_count": len(anchors),
        "bound_patch_count": int(bound_count),
        "fallback_patch_count": int(len(anchors) - bound_count),
        "raw_sample_count": int(raw_sample_count),
        "strict_shape_filter_anchor_count": int(strict_anchor_count),
        "filtered_raw_contact_count": int(filtered_sample_count),
        "raw_shape_ids_by_anchor": shape_filters,
        "warnings": warnings,
    }
    return sorted(
        patches,
        key=lambda item: (item.start_frame, item.end_frame, item.body, item.patch_id),
    ), result


def install_strict_newton_shape_filter() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _legacy.bind_newton_contact_patches = bind_newton_contact_patches
    contact_package = sys.modules.get("motion_edit.contact")
    if contact_package is not None:
        setattr(contact_package, "bind_newton_contact_patches", bind_newton_contact_patches)
    _INSTALLED = True
