from __future__ import annotations

import importlib
from typing import Any

import numpy as np

from motion_edit.contact_laplacian.schema import ContactHandleSpec


_INSTALLED = False


def _patch_role(anchor: Any | None) -> str | None:
    if anchor is None:
        return None
    metadata = anchor.metadata if isinstance(getattr(anchor, "metadata", None), dict) else {}
    role = metadata.get("patch_role")
    if role in {"heel", "toe", "sole"}:
        return str(role)
    subcontact = metadata.get("foot_subcontact")
    if isinstance(subcontact, dict):
        name = subcontact.get("name")
        if name in {"heel", "toe", "sole"}:
            return str(name)
        if isinstance(subcontact.get("heel"), dict) and isinstance(
            subcontact.get("toe"),
            dict,
        ):
            return "sole"
    return None


def _side(body: str) -> str | None:
    value = str(body).lower()
    if value.startswith(("left", "l")):
        return "left"
    if value.startswith(("right", "r")):
        return "right"
    return None


def _semantic_bindings(
    *,
    body: str,
    anchor: Any | None,
    keypoints: dict[str, np.ndarray],
) -> tuple[tuple[str, str, str | None], ...]:
    """Return ``(semantic_name, physical_force_body, patch_role)`` bindings."""

    role = _patch_role(anchor)
    side = _side(body)
    if side is not None and role == "heel":
        name = f"{side}_ankle"
        return ((name, f"{side}_heel", role),) if name in keypoints else ()
    if side is not None and role == "toe":
        name = f"{side}_foot"
        return ((name, f"{side}_toe", role),) if name in keypoints else ()
    if side is not None and role == "sole":
        candidates = (
            (f"{side}_ankle", f"{side}_heel", "heel"),
            (f"{side}_foot", f"{side}_toe", "toe"),
        )
        return tuple(item for item in candidates if item[0] in keypoints)

    lte = importlib.import_module("motion_edit.generation.lte_fullbody")
    name = lte._resolve_lte_handle_name(body, keypoints)
    if name not in keypoints:
        return ()
    return ((str(name), str(body), role),)


def _contact_laplacian_handles_from_edits(
    edits: list[Any],
    keypoints: dict[str, np.ndarray],
    *,
    graph: Any,
    config: Any,
    source_motion: dict[str, Any] | None = None,
) -> list[ContactHandleSpec]:
    lte = importlib.import_module("motion_edit.generation.lte_fullbody")
    handles: list[ContactHandleSpec] = []
    n_frames = len(next(iter(keypoints.values())))
    edited_anchor_ids: set[str] = set()
    zero_delta_anchor_ids: set[str] = set()
    anchors_by_id = {anchor.anchor_id: anchor for anchor in graph.anchors}

    for edit in edits:
        anchor = anchors_by_id.get(edit.anchor_id)
        bindings = _semantic_bindings(
            body=edit.body,
            anchor=anchor,
            keypoints=keypoints,
        )
        if not bindings:
            raise ValueError(
                f"{edit.edit_id}: contact body {edit.body!r} / "
                f"patch_role={_patch_role(anchor)!r} has no supported semantic"
            )

        start, end = lte._edit_interval(
            edit,
            type(
                "AnchorInterval",
                (),
                {"start_frame": 0, "end_frame": n_frames},
            )(),
        )
        start = max(0, min(n_frames, int(start)))
        end = max(start, min(n_frames, int(end)))
        if end <= start:
            raise ValueError(
                f"{edit.edit_id}: empty batch contact-Laplacian interval "
                f"[{start}, {end}]"
            )
        delta = np.asarray(lte._edit_delta(edit), dtype=np.float64)
        if float(np.linalg.norm(delta)) <= 1.0e-9:
            zero_delta_anchor_ids.add(edit.anchor_id)
            continue

        frames = np.arange(start, end, dtype=np.int64)
        for semantic_name, force_body, role in bindings:
            load_profile = lte._contact_load_profile_for_interval(
                source_motion=source_motion,
                body=force_body,
                start=start,
                end=end,
                normal=(
                    edit.surface_normal
                    or (
                        anchor.surface_normal
                        if anchor is not None
                        else None
                    )
                    or (anchor.normal if anchor is not None else None)
                ),
            )
            handles.append(
                ContactHandleSpec(
                    anchor_id=edit.anchor_id,
                    body=force_body,
                    semantic_name=semantic_name,
                    frames=frames,
                    target_xyz=keypoints[semantic_name][frames]
                    + delta[None, :],
                    kind="edited_contact",
                    weight=float(config.edit_contact_weight),
                    surface_id=edit.surface_id,
                    object_id=(
                        anchor.object_id if anchor is not None else None
                    ),
                    load_profile=load_profile,
                    metadata={
                        "edit_id": edit.edit_id,
                        "patch_role": _patch_role(anchor),
                        "semantic_contact_role": role,
                        "authoritative_delta_world": delta.astype(float).tolist(),
                        "semantic_patch_displacement_contract": "same_world_delta",
                        "source_frame_start": int(start),
                        "source_frame_end": int(end),
                        "target_frame_start": int(start),
                        "target_frame_end": int(end),
                        "source_target_interval_mapping": "same_frame_interval",
                    },
                )
            )
        edited_anchor_ids.add(edit.anchor_id)

    for anchor in graph.anchors:
        if anchor.anchor_id in edited_anchor_ids:
            continue
        bindings = _semantic_bindings(
            body=anchor.body,
            anchor=anchor,
            keypoints=keypoints,
        )
        if not bindings:
            continue
        start = max(0, min(n_frames, int(anchor.start_frame)))
        end = max(start, min(n_frames, int(anchor.end_frame)))
        if end <= start:
            continue
        frames = np.arange(start, end, dtype=np.int64)

        for semantic_name, force_body, role in bindings:
            load_profile = lte._contact_load_profile_for_interval(
                source_motion=source_motion,
                body=force_body,
                start=start,
                end=end,
                normal=anchor.surface_normal or anchor.normal,
            )
            handles.append(
                ContactHandleSpec(
                    anchor_id=anchor.anchor_id,
                    body=force_body,
                    semantic_name=semantic_name,
                    frames=frames,
                    target_xyz=keypoints[semantic_name][frames],
                    kind="fixed_contact",
                    weight=float(config.fixed_contact_weight),
                    surface_id=anchor.surface_id,
                    object_id=anchor.object_id,
                    load_profile=load_profile,
                    metadata={
                        "zero_delta_edit": (
                            anchor.anchor_id in zero_delta_anchor_ids
                        ),
                        "patch_role": _patch_role(anchor),
                        "semantic_contact_role": role,
                        "source_frame_start": int(start),
                        "source_frame_end": int(end),
                        "target_frame_start": int(start),
                        "target_frame_end": int(end),
                        "source_target_interval_mapping": "same_frame_interval",
                    },
                )
            )
    return handles


def install_foot_contact_handle_contract() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    lte = importlib.import_module("motion_edit.generation.lte_fullbody")
    lte._contact_laplacian_handles_from_edits = (
        _contact_laplacian_handles_from_edits
    )
    _INSTALLED = True
