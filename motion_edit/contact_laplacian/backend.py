"""Handle-building helpers for the experimental batch contact-Laplacian path.

The functions here convert ContactGraph/ContactEditPlan data into solver handle
specs. They intentionally depend on an abstract kinematics provider; a real
robot provider is still required before this path can replace the production IK
subprocess generator.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from motion_edit.contact.dynamics import load_profile_from_motion_force
from motion_edit.contact.schema import ContactAnchorEditRecord

from .kinematics import KinematicsProvider
from .schema import BatchContactLaplacianConfig, ContactHandleSpec


DEFAULT_CONTACT_BODY_TO_SEMANTIC = {
    "left_foot": "left_foot",
    "right_foot": "right_foot",
    "left_hand": "left_hand",
    "right_hand": "right_hand",
    "left_knee": "left_knee",
    "right_knee": "right_knee",
    "lf": "left_foot",
    "rf": "right_foot",
    "lh": "left_hand",
    "rh": "right_hand",
    "lk": "left_knee",
    "rk": "right_knee",
}


def build_contact_handle_specs(
    *,
    graph: Any,
    edits: Sequence[ContactAnchorEditRecord],
    q_reference: np.ndarray,
    kinematics: KinematicsProvider,
    config: BatchContactLaplacianConfig | None = None,
    body_to_semantic: Mapping[str, str] | None = None,
    source_motion: Mapping[str, Any] | None = None,
    min_load_strength: float = 0.05,
    zero_delta_eps: float = 1.0e-9,
) -> tuple[list[ContactHandleSpec], dict[str, Any]]:
    cfg = config or BatchContactLaplacianConfig()
    q_ref = np.asarray(q_reference, dtype=np.float64)
    if q_ref.ndim != 2:
        raise ValueError(f"q_reference must have shape [T, nq], got {q_ref.shape}")
    n_frames = q_ref.shape[0]
    aliases = {**DEFAULT_CONTACT_BODY_TO_SEMANTIC, **dict(body_to_semantic or {})}
    anchors_by_id = {anchor.anchor_id: anchor for anchor in graph.anchors}
    edited_by_anchor: dict[str, ContactAnchorEditRecord] = {}
    zero_delta_anchor_ids: set[str] = set()
    skipped: list[dict[str, str]] = []
    load_profile_count = 0

    handles: list[ContactHandleSpec] = []
    for edit in edits:
        anchor = anchors_by_id.get(edit.anchor_id)
        if anchor is None:
            skipped.append({"anchor_id": edit.anchor_id, "reason": "edit anchor missing from graph"})
            continue
        delta = _edit_delta_or_zero(edit)
        if float(np.linalg.norm(delta)) <= zero_delta_eps:
            zero_delta_anchor_ids.add(edit.anchor_id)
            continue
        semantic = _resolve_semantic_name(edit.body or anchor.body, aliases)
        if semantic is None:
            skipped.append({"anchor_id": edit.anchor_id, "reason": f"unsupported edit body {edit.body or anchor.body!r}"})
            continue
        start, end = _edit_interval(edit, anchor, n_frames)
        frames = np.arange(start, end, dtype=np.int64)
        load_profile = _load_profile_for_anchor(
            source_motion=source_motion,
            body=edit.body or anchor.body,
            start=start,
            end=end,
            normal=edit.surface_normal or anchor.surface_normal or anchor.normal,
            min_load_strength=min_load_strength,
        )
        if load_profile is not None:
            load_profile_count += 1
        target = _fk_trajectory(q_ref, kinematics, semantic, frames) + delta[None, :]
        handles.append(
            ContactHandleSpec(
                anchor_id=edit.anchor_id,
                body=edit.body or anchor.body,
                semantic_name=semantic,
                frames=frames,
                target_xyz=target,
                kind="edited_contact",
                weight=float(edit.metadata.get("contact_laplacian_weight", cfg.edit_contact_weight)) if isinstance(edit.metadata, dict) else float(cfg.edit_contact_weight),
                surface_id=edit.surface_id or anchor.surface_id,
                object_id=anchor.object_id,
                load_profile=load_profile,
                metadata={"edit_id": edit.edit_id},
            )
        )
        edited_by_anchor[edit.anchor_id] = edit

    for anchor in graph.anchors:
        if anchor.anchor_id in edited_by_anchor:
            continue
        semantic = _resolve_semantic_name(anchor.body, aliases)
        if semantic is None:
            skipped.append({"anchor_id": anchor.anchor_id, "reason": f"unsupported fixed body {anchor.body!r}"})
            continue
        start = max(0, min(n_frames, int(anchor.start_frame)))
        end = max(start, min(n_frames, int(anchor.end_frame)))
        if end <= start:
            skipped.append({"anchor_id": anchor.anchor_id, "reason": "empty fixed contact interval"})
            continue
        frames = np.arange(start, end, dtype=np.int64)
        load_profile = _load_profile_for_anchor(
            source_motion=source_motion,
            body=anchor.body,
            start=start,
            end=end,
            normal=anchor.surface_normal or anchor.normal,
            min_load_strength=min_load_strength,
        )
        if load_profile is not None:
            load_profile_count += 1
        handles.append(
            ContactHandleSpec(
                anchor_id=anchor.anchor_id,
                body=anchor.body,
                semantic_name=semantic,
                frames=frames,
                target_xyz=_fk_trajectory(q_ref, kinematics, semantic, frames),
                kind="fixed_contact",
                weight=float(cfg.fixed_contact_weight),
                surface_id=anchor.surface_id,
                object_id=anchor.object_id,
                load_profile=load_profile,
                metadata={"zero_delta_edit": anchor.anchor_id in zero_delta_anchor_ids},
            )
        )

    metadata = {
        "edited_handle_count": sum(1 for handle in handles if handle.kind == "edited_contact"),
        "fixed_handle_count": sum(1 for handle in handles if handle.kind == "fixed_contact"),
        "zero_delta_edit_count": len(zero_delta_anchor_ids),
        "skipped_anchor_count": len(skipped),
        "skipped_anchors": skipped,
        "force_load_profile_count": int(load_profile_count),
        "force_load_profile_source": "source_motion_contact_force_part_w" if source_motion is not None else "none",
    }
    return handles, metadata


def _load_profile_for_anchor(
    *,
    source_motion: Mapping[str, Any] | None,
    body: str,
    start: int,
    end: int,
    normal: Sequence[float] | None,
    min_load_strength: float,
):
    if source_motion is None:
        return None
    return load_profile_from_motion_force(
        dict(source_motion),
        body=body,
        start_frame=start,
        end_frame=end,
        normal_w=normal,
        min_strength=min_load_strength,
    )


def _resolve_semantic_name(body: str, aliases: Mapping[str, str]) -> str | None:
    key = str(body)
    if key in aliases:
        return aliases[key]
    lower = key.lower()
    if lower in aliases:
        return aliases[lower]
    for token, semantic in aliases.items():
        if token and token in lower:
            return semantic
    return None


def _edit_delta_or_zero(edit: ContactAnchorEditRecord) -> np.ndarray:
    if edit.delta_world is not None:
        return np.asarray(edit.delta_world, dtype=np.float64)
    if edit.old_world_position is not None and edit.new_world_position is not None:
        return np.asarray(edit.new_world_position, dtype=np.float64) - np.asarray(edit.old_world_position, dtype=np.float64)
    return np.zeros(3, dtype=np.float64)


def _edit_interval(edit: ContactAnchorEditRecord, anchor: Any, n_frames: int) -> tuple[int, int]:
    if edit.affected_frames is not None:
        start, end = int(edit.affected_frames[0]), int(edit.affected_frames[1])
    else:
        start, end = int(anchor.start_frame), int(anchor.end_frame)
    start = max(0, min(n_frames, start))
    end = max(start, min(n_frames, end))
    if end <= start:
        raise ValueError(f"{edit.edit_id}: empty edit interval [{start}, {end}]")
    return start, end


def _fk_trajectory(q_reference: np.ndarray, kinematics: KinematicsProvider, semantic_name: str, frames: np.ndarray) -> np.ndarray:
    return np.asarray([kinematics.fk_points(q_reference[int(frame)], [semantic_name])[0] for frame in frames], dtype=np.float64)
