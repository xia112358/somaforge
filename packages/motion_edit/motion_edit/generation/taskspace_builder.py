from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from motion_edit.contact.newton_bindings import body_local_point_to_world
from motion_edit.contact.schema import (
    ContactAnchorEditRecord,
    ContactAnchorRecord,
    ContactPatchRecord,
    ContactSurfaceRecord,
)
from motion_edit.generation.taskspace_spec import (
    ContactAwareTaskspaceMotion,
    ContactPatchTarget,
    make_boundary_weights,
)


def build_contact_aware_taskspace_motion(
    *,
    motion_id: str,
    source_motion: Mapping[str, Any],
    contact_pose_motion: Mapping[str, Any] | None = None,
    semantic_names: Sequence[str],
    semantic_targets_w: np.ndarray,
    patches: Sequence[ContactPatchRecord],
    anchors: Sequence[ContactAnchorRecord],
    surfaces: Sequence[ContactSurfaceRecord],
    edits: Sequence[ContactAnchorEditRecord],
    semantic_weights: np.ndarray | None = None,
    frame_start: int = 0,
    frame_end: int | None = None,
    source_reference_weight: float = 0.01,
    boundary_ramp_frames: int = 10,
) -> ContactAwareTaskspaceMotion:
    """Compile regenerated semantic curves and rigid contact patches into one spec.

    Large spatial edits are assumed to have already been handled by the semantic
    curve generator. This builder only converts the result into a precise task
    contract for trajectory IK:

    * semantic link centers are soft targets;
    * robot-local patch points remain rigid;
    * edited contacts translate along the bound surface in UV;
    * unedited contacts retain their original Newton-recorded world trajectory;
    * the source joint motion is an initializer and weak tie-breaker.
    """

    source_qpos = np.asarray(source_motion["joint_pos"], dtype=np.float64)
    source_qvel = np.asarray(source_motion["joint_vel"], dtype=np.float64)
    contact_motion = source_motion if contact_pose_motion is None else contact_pose_motion
    body_pos_w = np.asarray(contact_motion["body_pos_w"], dtype=np.float64)
    body_quat_w = np.asarray(contact_motion["body_quat_w"], dtype=np.float64)
    body_names = _string_list(contact_motion.get("body_names"))
    if not body_names:
        raise ValueError("contact-aware taskspace generation requires body_names")

    full_frame_count = source_qpos.shape[0]
    stop = full_frame_count if frame_end is None else min(full_frame_count, int(frame_end))
    start = max(0, min(stop, int(frame_start)))
    if stop <= start:
        raise ValueError(f"invalid taskspace frame interval [{start}, {stop})")
    frame_count = stop - start

    semantic = _window_array(
        np.asarray(semantic_targets_w, dtype=np.float64),
        start=start,
        stop=stop,
        expected_tail=(len(tuple(semantic_names)), 3),
        name="semantic_targets_w",
    )
    weights = (
        np.ones((frame_count, len(tuple(semantic_names))), dtype=np.float64)
        if semantic_weights is None
        else _window_array(
            np.asarray(semantic_weights, dtype=np.float64),
            start=start,
            stop=stop,
            expected_tail=(len(tuple(semantic_names)),),
            name="semantic_weights",
        )
    )

    anchors_by_id = {anchor.anchor_id: anchor for anchor in anchors}
    edits_by_anchor = {edit.anchor_id: edit for edit in edits}
    surfaces_by_id = {surface.surface_id: surface for surface in surfaces}
    contacts: list[ContactPatchTarget] = []
    skipped: list[dict[str, str]] = []

    for patch in patches:
        anchor_id = patch.anchor_id or patch.patch_id.removesuffix("_patch")
        anchor = anchors_by_id.get(anchor_id)
        if anchor is None:
            skipped.append({"patch_id": patch.patch_id, "reason": "anchor missing"})
            continue
        if not patch.robot_points_local:
            skipped.append({"patch_id": patch.patch_id, "reason": "Newton robot-local patch missing"})
            continue

        contact_start = max(start, int(anchor.start_frame))
        contact_end = min(stop, int(anchor.end_frame))
        edit = edits_by_anchor.get(anchor.anchor_id)
        if edit is not None and edit.affected_frames is not None:
            contact_start = max(contact_start, int(edit.affected_frames[0]))
            contact_end = min(contact_end, int(edit.affected_frames[1]))
        if contact_end <= contact_start:
            skipped.append({"patch_id": patch.patch_id, "reason": "contact interval outside solve window"})
            continue

        body_index = _resolve_body_index(body_names, patch)
        if body_index is None:
            skipped.append({"patch_id": patch.patch_id, "reason": "body pose index unresolved"})
            continue

        frames = np.arange(contact_start, contact_end, dtype=np.int64)
        points_local = np.asarray(patch.robot_points_local, dtype=np.float64)
        source_points_w = np.asarray(
            [
                [
                    body_local_point_to_world(
                        point_local,
                        body_pos_w[frame, body_index],
                        body_quat_w[frame, body_index],
                    )
                    for point_local in points_local
                ]
                for frame in frames
            ],
            dtype=np.float64,
        )

        surface_id = (edit.surface_id if edit is not None else None) or anchor.surface_id
        surface = surfaces_by_id.get(surface_id or "")
        kwargs: dict[str, Any] = {}
        if edit is not None and surface is not None:
            delta_uv = _edit_delta_uv(edit, surface)
            source_uv = _surface_uv(source_points_w, surface)
            kwargs = {
                "surface_id": surface.surface_id,
                "surface_origin_w": np.asarray(surface.origin, dtype=np.float64),
                "surface_normal_w": np.asarray(surface.normal, dtype=np.float64),
                "surface_tangent_u_w": np.asarray(surface.tangent_u, dtype=np.float64),
                "surface_tangent_v_w": np.asarray(surface.tangent_v, dtype=np.float64),
                "target_uv": source_uv + delta_uv[None, None, :],
            }
        elif edit is not None:
            delta_world = _edit_delta_world(edit)
            kwargs = {"target_points_w": source_points_w + delta_world[None, None, :]}
        else:
            kwargs = {"target_points_w": source_points_w}

        contact = ContactPatchTarget(
            anchor_id=anchor.anchor_id,
            kind="edited_contact" if edit is not None else "fixed_contact",
            body_label=patch.newton_body_label or (patch.link_names or [patch.body])[0],
            shape_labels=tuple(patch.newton_shape_labels or patch.sphere_ids or ()),
            points_local=points_local,
            frames=frames,
            normals_local=(
                np.asarray(patch.robot_normals_local, dtype=np.float64)
                if patch.robot_normals_local is not None
                else None
            ),
            metadata={
                "patch_id": patch.patch_id,
                "robot_binding_backend": patch.robot_binding_backend,
                "robot_binding_source": patch.robot_binding_source,
                "source_surface_coordinates": anchor.surface_coordinates,
                "edit_id": edit.edit_id if edit is not None else None,
            },
            **kwargs,
        )
        contact.validate()
        contacts.append(contact)

    qpos = source_qpos[start:stop].copy()
    qvel = source_qvel[start:stop].copy()
    source_weights = np.full(qpos.shape, float(source_reference_weight), dtype=np.float64)
    boundary_weights = make_boundary_weights(frame_count, boundary_ramp_frames)

    spec = ContactAwareTaskspaceMotion(
        motion_id=motion_id,
        fps=_fps(source_motion),
        frame_start=start,
        frame_end=stop,
        semantic_names=tuple(str(name) for name in semantic_names),
        semantic_targets_w=semantic,
        semantic_weights=weights,
        contacts=tuple(contacts),
        source_qpos=qpos,
        source_qvel=qvel,
        source_reference_weights=source_weights,
        boundary_weights=boundary_weights,
        metadata={
            "schema": "contact_aware_taskspace_motion_v1",
            "old_motion_role": "initializer_and_weak_tie_breaker",
            "contact_patch_role": "rigid_hard_constraint_target",
            "semantic_curve_role": "primary_soft_motion_target",
            "source_reference_weight": float(source_reference_weight),
            "skipped_patches": skipped,
        },
    )
    spec.validate()
    return spec


def _surface_uv(points_w: np.ndarray, surface: ContactSurfaceRecord) -> np.ndarray:
    points = np.asarray(points_w, dtype=np.float64)
    relative = points - np.asarray(surface.origin, dtype=np.float64)[None, None, :]
    tangent_u = np.asarray(surface.tangent_u, dtype=np.float64)
    tangent_v = np.asarray(surface.tangent_v, dtype=np.float64)
    return np.stack([relative @ tangent_u, relative @ tangent_v], axis=-1)


def _edit_delta_uv(edit: ContactAnchorEditRecord, surface: ContactSurfaceRecord) -> np.ndarray:
    if edit.tangent_delta is not None:
        return np.asarray(edit.tangent_delta, dtype=np.float64)
    before = edit.surface_coordinates_before or {}
    after = edit.surface_coordinates_after or {}
    if all(key in before and key in after for key in ("u", "v")):
        return np.asarray(
            [float(after["u"]) - float(before["u"]), float(after["v"]) - float(before["v"])],
            dtype=np.float64,
        )
    delta_world = _edit_delta_world(edit)
    return np.asarray(
        [
            float(np.dot(delta_world, np.asarray(surface.tangent_u, dtype=np.float64))),
            float(np.dot(delta_world, np.asarray(surface.tangent_v, dtype=np.float64))),
        ],
        dtype=np.float64,
    )


def _edit_delta_world(edit: ContactAnchorEditRecord) -> np.ndarray:
    if edit.delta_world is not None:
        return np.asarray(edit.delta_world, dtype=np.float64)
    if edit.old_world_position is not None and edit.new_world_position is not None:
        return np.asarray(edit.new_world_position, dtype=np.float64) - np.asarray(edit.old_world_position, dtype=np.float64)
    return np.zeros(3, dtype=np.float64)


def _resolve_body_index(body_names: Sequence[str], patch: ContactPatchRecord) -> int | None:
    lowered = [str(name).lower() for name in body_names]
    candidates = [
        *(patch.link_names or []),
        patch.newton_body_label.rstrip("/").split("/")[-1] if patch.newton_body_label else "",
        patch.body,
    ]
    for candidate in candidates:
        key = str(candidate).lower()
        if key in lowered:
            return lowered.index(key)
    for candidate in candidates:
        key = str(candidate).lower()
        if not key:
            continue
        for index, name in enumerate(lowered):
            if key in name or name in key:
                return index
    return None


def _window_array(
    array: np.ndarray,
    *,
    start: int,
    stop: int,
    expected_tail: tuple[int, ...],
    name: str,
) -> np.ndarray:
    if array.shape[1:] != expected_tail:
        raise ValueError(f"{name} must have trailing shape {expected_tail}, got {array.shape}")
    frame_count = stop - start
    if array.shape[0] == frame_count:
        return array.copy()
    if array.shape[0] >= stop:
        return array[start:stop].copy()
    raise ValueError(f"{name} has {array.shape[0]} frames and cannot cover [{start}, {stop})")


def _fps(motion: Mapping[str, Any]) -> float:
    if "fps" in motion:
        return float(np.asarray(motion["fps"]).reshape(-1)[0])
    if "dt" in motion:
        dt = float(np.asarray(motion["dt"]).reshape(-1)[0])
        if dt > 0.0:
            return 1.0 / dt
    return 50.0


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    return [str(item) for item in np.asarray(value, dtype=object).reshape(-1).tolist()]
