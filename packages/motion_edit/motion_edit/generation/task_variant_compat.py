from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from motion_edit.contact.plans import ContactEditPlan
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord, ContactSurfaceRecord
from motion_edit.contact.surface_frame import map_points_between_surface_frames
from motion_edit.generation.lte_fullbody import (
    LTE_FULLBODY_KEYPOINT_LINKS,
    _motion_strings,
    _recompute_linear_velocity,
    _semantic_body_weights,
)


@dataclass(frozen=True)
class ExpandedTaskVariant:
    edits: tuple[ContactAnchorEditRecord, ...]
    surfaces: tuple[ContactSurfaceRecord, ...]
    metadata: dict[str, Any]
    warnings: tuple[str, ...] = ()


def pose_edits_for_semantic_proxy(
    edits: Iterable[ContactAnchorEditRecord],
    pose_edits: Iterable[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Return pose edits that are not already represented by contact edits.

    Approach-position variants persist the same translation twice: once on the
    overlapping ground-contact anchors and once as a ``translate_pose`` edit.
    The edited contact points are the authority; the contact Laplacian should
    propagate their displacement through the body and determine the resulting
    root motion.  Applying the paired pose translation afterwards would move
    the whole body a second time.  Suppress only that redundant pose edit.
    """

    approach_contacts: list[tuple[tuple[int, int], np.ndarray]] = []
    for edit in edits:
        metadata = dict(edit.metadata or {})
        if metadata.get("task_variant") != "approach_position":
            continue
        pose_interval = metadata.get("pose_interval")
        delta = np.asarray(edit.delta_world, dtype=np.float64) if edit.delta_world is not None else None
        if (
            isinstance(pose_interval, (list, tuple))
            and len(pose_interval) == 2
            and delta is not None
            and delta.shape == (3,)
        ):
            approach_contacts.append(
                (
                    (int(pose_interval[0]), int(pose_interval[1])),
                    delta,
                )
            )

    retained: list[dict[str, Any]] = []
    for raw in pose_edits:
        frames = raw.get("affected_frames")
        translation = raw.get("translation_world")
        paired = (
            str(raw.get("edit_type") or "") == "translate_pose"
            and isinstance(frames, (list, tuple))
            and len(frames) == 2
            and translation is not None
            and any(
                (int(frames[0]), int(frames[1])) == interval
                and np.allclose(
                    np.asarray(translation, dtype=np.float64),
                    delta,
                    atol=1.0e-9,
                    rtol=0.0,
                )
                for interval, delta in approach_contacts
            )
        )
        if not paired:
            retained.append(raw)
    return tuple(retained)


def expand_task_variant_plan(
    plan: ContactEditPlan,
    *,
    anchors: Sequence[ContactAnchorRecord],
    surfaces: Sequence[ContactSurfaceRecord],
) -> ExpandedTaskVariant:
    """Expand surface-follow task variants into ordinary anchor edits.

    The persisted plan remains unchanged. Physical anchor/body identities are kept;
    only a generated ContactAnchorEditRecord is produced for the semantic solver.
    Source and target surface UV coordinates are preserved.
    """

    explicit = [ContactAnchorEditRecord(**raw) for raw in plan.edits]
    explicit_anchor_ids = {edit.anchor_id for edit in explicit}
    explicit_by_anchor = {edit.anchor_id: edit for edit in explicit}
    consumed_explicit_edit_ids: set[str] = set()
    surface_by_id = {surface.surface_id: surface for surface in surfaces}
    expanded: list[ContactAnchorEditRecord] = []
    warnings: list[str] = []
    transform_summaries: list[dict[str, Any]] = []

    for raw in plan.surface_transforms:
        transform_id = str(raw["transform_id"])
        source = _surface_from_dict(raw["source_surface"], motion_id=plan.source_motion_id, source="task_variant_source")
        target = _surface_from_dict(raw["target_surface"], motion_id=plan.source_motion_id, source="task_variant_target")
        surface_by_id[source.surface_id] = source
        surface_by_id[target.surface_id] = target
        translation_world = np.asarray(
            raw.get("translation_world")
            if raw.get("translation_world") is not None
            else np.asarray(target.origin, dtype=np.float64)
            - np.asarray(source.origin, dtype=np.float64),
            dtype=np.float64,
        )
        if translation_world.shape != (3,) or not np.all(
            np.isfinite(translation_world)
        ):
            raise ValueError(
                f"{transform_id}: translation_world must be one finite 3-vector"
            )
        tangent_delta = np.asarray(
            [
                float(
                    np.dot(
                        translation_world,
                        np.asarray(target.tangent_u, dtype=np.float64),
                    )
                ),
                float(
                    np.dot(
                        translation_world,
                        np.asarray(target.tangent_v, dtype=np.float64),
                    )
                ),
            ],
            dtype=np.float64,
        )
        failed_candidates = [
            anchor.anchor_id
            for anchor in anchors
            if not _anchor_matches_source_surface(anchor, source)
            and _anchor_failed_source_surface_binding(anchor, source)
        ]
        if failed_candidates:
            raise ValueError(
                f"{transform_id}: source contact layer contains anchors that "
                f"failed binding to transformed surface {source.surface_id!r}; "
                "rebuild it with raw-contact surface refinement instead of "
                "keeping fixed world targets: "
                + ", ".join(failed_candidates)
            )

        matched = 0
        generated = 0
        for anchor in anchors:
            if not _anchor_matches_source_surface(anchor, source):
                continue
            matched += 1
            if anchor.anchor_id in explicit_anchor_ids:
                explicit_edit = explicit_by_anchor[anchor.anchor_id]
                explicit_metadata = dict(explicit_edit.metadata or {})
                if explicit_metadata.get("compose_with_surface_transform"):
                    uv_delta = np.asarray(
                        explicit_metadata.get("surface_uv_delta"),
                        dtype=np.float64,
                    )
                    if uv_delta.shape != (2,) or not np.all(np.isfinite(uv_delta)):
                        raise ValueError(
                            f"{explicit_edit.edit_id}: composed surface edit requires "
                            "one finite metadata.surface_uv_delta"
                        )
                    uv_before = _anchor_uv(anchor, source)
                    uv_after = uv_before + uv_delta
                    if target.bounds is not None and not (
                        float(target.bounds["u"][0])
                        <= float(uv_after[0])
                        <= float(target.bounds["u"][1])
                        and float(target.bounds["v"][0])
                        <= float(uv_after[1])
                        <= float(target.bounds["v"][1])
                    ):
                        raise ValueError(
                            f"{explicit_edit.edit_id}: composed target UV "
                            f"{uv_after.tolist()} leaves {target.surface_id!r}"
                        )
                    old_world = _anchor_world(anchor, source, uv_before)
                    new_world = (
                        np.asarray(target.origin, dtype=np.float64)
                        + float(uv_after[0])
                        * np.asarray(target.tangent_u, dtype=np.float64)
                        + float(uv_after[1])
                        * np.asarray(target.tangent_v, dtype=np.float64)
                    )
                    delta_world = new_world - old_world
                    expanded.append(
                        replace(
                            explicit_edit,
                            old_world_position=old_world.tolist(),
                            new_world_position=new_world.tolist(),
                            requested_delta_world=delta_world.tolist(),
                            delta_world=delta_world.tolist(),
                            tangent_delta=uv_delta.tolist(),
                            surface_id=target.surface_id,
                            surface_normal=list(target.normal),
                            surface_coordinates_before={
                                "u": float(uv_before[0]),
                                "v": float(uv_before[1]),
                            },
                            surface_coordinates_after={
                                "u": float(uv_after[0]),
                                "v": float(uv_after[1]),
                            },
                            constraint_mode="reject",
                            metadata={
                                **explicit_metadata,
                                "composed_surface_transform_id": transform_id,
                                "source_surface": raw["source_surface"],
                                "target_surface": raw["target_surface"],
                                "surface_transform_then_uv": True,
                            },
                        )
                    )
                    consumed_explicit_edit_ids.add(explicit_edit.edit_id)
                    generated += 1
                    continue
                warnings.append(f"{transform_id}: explicit edit overrides surface-follow for {anchor.anchor_id}")
                continue
            uv = _anchor_uv(anchor, source)
            old_world = _anchor_world(anchor, source, uv)
            source_payload = raw["source_surface"]
            target_payload = raw["target_surface"]
            new_world = map_points_between_surface_frames(
                old_world,
                source_payload,
                target_payload,
            )
            anchor_delta = new_world - old_world
            expanded.append(
                ContactAnchorEditRecord(
                    edit_id=f"{transform_id}:{anchor.anchor_id}",
                    motion_id=plan.source_motion_id,
                    anchor_id=anchor.anchor_id,
                    body=anchor.body,
                    edit_type="move_contact_anchor",
                    old_world_position=old_world.tolist(),
                    new_world_position=new_world.tolist(),
                    requested_delta_world=anchor_delta.tolist(),
                    delta_world=anchor_delta.tolist(),
                    tangent_delta=[0.0, 0.0],
                    affected_frames=[int(anchor.start_frame), int(anchor.end_frame)],
                    surface_id=target.surface_id,
                    surface_normal=list(target.normal),
                    surface_coordinates_before={"u": float(uv[0]), "v": float(uv[1])},
                    surface_coordinates_after={"u": float(uv[0]), "v": float(uv[1])},
                    constraint_mode="surface_follow",
                    source="task_variant_surface_follow",
                    metadata={
                        "surface_transform_id": transform_id,
                        "surface_follow_source_surface_id": source.surface_id,
                        "surface_follow_target_surface_id": target.surface_id,
                        "surface_follow_preserve_uv": True,
                        "uniform_surface_translation": bool(
                            np.allclose(anchor_delta, translation_world, atol=1.0e-9)
                        ),
                        "source_surface": source_payload,
                        "target_surface": target_payload,
                        "height_scale": raw.get("height_scale"),
                    },
                )
            )
            generated += 1

        if matched == 0:
            raise ValueError(
                f"{transform_id}: no contact anchors matched source surface {source.surface_id!r} "
                f"or object {source.object_id!r}"
            )
        transform_summaries.append(
            {
                "transform_id": transform_id,
                "source_surface_id": source.surface_id,
                "target_surface_id": target.surface_id,
                "matched_anchor_count": matched,
                "generated_edit_count": generated,
                "height_scale": raw.get("height_scale"),
                "translation_world": translation_world.tolist(),
            }
        )

    return ExpandedTaskVariant(
        edits=tuple(
            [
                *(
                    edit
                    for edit in explicit
                    if edit.edit_id not in consumed_explicit_edit_ids
                ),
                *expanded,
            ]
        ),
        surfaces=tuple(surface_by_id.values()),
        metadata={
            "pose_edit_count": len(plan.pose_edits),
            "surface_transform_count": len(plan.surface_transforms),
            "expanded_surface_follow_edit_count": len(expanded),
            "composed_surface_uv_edit_count": len(consumed_explicit_edit_ids),
            "surface_transforms": transform_summaries,
        },
        warnings=tuple(warnings),
    )


def _anchor_failed_source_surface_binding(
    anchor: ContactAnchorRecord,
    source: ContactSurfaceRecord,
) -> bool:
    metadata = dict(anchor.metadata or {})
    refinement = metadata.get("raw_contact_position_refinement")
    if isinstance(refinement, Mapping):
        selected = str(refinement.get("selected_surface_id") or "")
        if selected == source.surface_id:
            return True
    if not metadata.get("surface_binding_failed"):
        return False
    reason = str(metadata.get("surface_binding_failure_reason") or "")
    return source.surface_id in reason or (
        bool(source.object_id) and str(source.object_id) in reason
    )


def apply_pose_edits_to_proxy(
    proxy: dict[str, Any],
    pose_edits: Iterable[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply legacy translate-pose edits to generated semantic curves.

    This updates both ``keypoint_*`` targets and the dense ``body_pos_w`` proxy.
    The final trajectory IK still operates on the semantic keypoints.
    """

    edits = list(pose_edits)
    if not edits:
        return proxy, {"applied_pose_edit_count": 0}

    output = dict(proxy)
    keypoint_names = tuple(name for name in LTE_FULLBODY_KEYPOINT_LINKS if f"keypoint_{name}" in output)
    if not keypoint_names:
        raise ValueError("pose edits require semantic keypoint arrays")
    frame_count = int(np.asarray(output[f"keypoint_{keypoint_names[0]}"]).shape[0])
    incremental = {name: np.zeros((frame_count, 3), dtype=np.float64) for name in keypoint_names}
    summaries: list[dict[str, Any]] = []

    aliases = {"root": "pelvis"}
    for raw in edits:
        edit_id = str(raw.get("edit_id") or "pose_edit")
        start, end = [int(value) for value in raw["affected_frames"]]
        start = max(0, min(frame_count, start))
        end = max(start, min(frame_count, end))
        if end <= start:
            raise ValueError(f"{edit_id}: pose edit interval is outside the motion")
        translation = np.asarray(raw["translation_world"], dtype=np.float64)
        resolved: list[str] = []
        for requested in raw["semantic_names"]:
            semantic = aliases.get(str(requested), str(requested))
            if semantic not in incremental:
                raise ValueError(f"{edit_id}: unsupported semantic target {requested!r}")
            incremental[semantic][start:end] += translation[None, :]
            resolved.append(semantic)
        summaries.append(
            {
                "edit_id": edit_id,
                "affected_frames": [start, end],
                "translation_world": translation.tolist(),
                "semantic_names": resolved,
                "weight_scale": float(raw.get("weight_scale", 1.0)),
            }
        )

    for name, delta in incremental.items():
        key = f"keypoint_{name}"
        output[key] = np.asarray(output[key], dtype=np.float64) + delta
        if f"offset_{name}" in output:
            output[f"offset_{name}"] = np.asarray(output[f"offset_{name}"], dtype=np.float64) + delta

    if "body_pos_w" in output and "body_names" in output:
        body_names = _motion_strings(output, ("body_names", "body_name", "body_pos_w_names", "body_pos_names"))
        weights = _semantic_body_weights(body_names, list(keypoint_names))
        stacked = np.stack([incremental[name] for name in keypoint_names], axis=1)
        dense_delta = np.einsum("tsc,bs->tbc", stacked, weights)
        body_pos = np.asarray(output["body_pos_w"], dtype=np.float64) + dense_delta
        output["body_pos_w"] = body_pos
        fps = float(np.asarray(output.get("fps", [50.0])).reshape(-1)[0])
        output["body_lin_vel_w"] = _recompute_linear_velocity(body_pos, fps, np.dtype(np.float64))

    return output, {"applied_pose_edit_count": len(edits), "pose_edits": summaries}


def _surface_from_dict(raw: dict[str, Any], *, motion_id: str, source: str) -> ContactSurfaceRecord:
    record = ContactSurfaceRecord(
        motion_id=str(raw.get("motion_id") or motion_id),
        surface_id=str(raw["surface_id"]),
        object_id=None if raw.get("object_id") is None else str(raw.get("object_id")),
        surface_type=str(raw.get("surface_type") or "plane"),
        origin=[float(value) for value in raw["origin"]],
        normal=[float(value) for value in raw["normal"]],
        tangent_u=[float(value) for value in raw["tangent_u"]],
        tangent_v=[float(value) for value in raw["tangent_v"]],
        bounds=None if raw.get("bounds") is None else dict(raw["bounds"]),
        source=str(raw.get("source") or source),
        metadata=dict(raw.get("metadata") or {}),
    )
    record.validate()
    return record


def _require_parallel_surface_basis(
    transform_id: str,
    source: ContactSurfaceRecord,
    target: ContactSurfaceRecord,
) -> None:
    for name in ("normal", "tangent_u", "tangent_v"):
        if not np.allclose(
            np.asarray(getattr(source, name), dtype=np.float64),
            np.asarray(getattr(target, name), dtype=np.float64),
            atol=1.0e-6,
            rtol=0.0,
        ):
            raise ValueError(
                f"{transform_id}: rotated surface-follow bases are not supported yet; "
                f"source/target {name} differ"
            )


def _anchor_matches_source_surface(anchor: ContactAnchorRecord, surface: ContactSurfaceRecord) -> bool:
    if anchor.surface_id and anchor.surface_id == surface.surface_id:
        return True
    return bool(
        surface.object_id
        and anchor.object_id
        and anchor.object_id == surface.object_id
        and (not anchor.surface_id or not surface.surface_id)
    )


def _anchor_uv(anchor: ContactAnchorRecord, surface: ContactSurfaceRecord) -> np.ndarray:
    coordinates = anchor.surface_coordinates or {}
    if "u" in coordinates and "v" in coordinates:
        return np.asarray([float(coordinates["u"]), float(coordinates["v"])], dtype=np.float64)
    if anchor.world_position is None:
        raise ValueError(f"{anchor.anchor_id}: surface-follow requires UV coordinates or world_position")
    return _project_uv(np.asarray(anchor.world_position, dtype=np.float64), surface)


def _anchor_world(
    anchor: ContactAnchorRecord,
    surface: ContactSurfaceRecord,
    uv: np.ndarray,
) -> np.ndarray:
    if anchor.world_position is not None:
        return np.asarray(anchor.world_position, dtype=np.float64)
    return _surface_point(surface, uv)


def _project_uv(point_w: np.ndarray, surface: ContactSurfaceRecord) -> np.ndarray:
    relative = np.asarray(point_w, dtype=np.float64) - np.asarray(surface.origin, dtype=np.float64)
    return np.asarray(
        [
            float(np.dot(relative, np.asarray(surface.tangent_u, dtype=np.float64))),
            float(np.dot(relative, np.asarray(surface.tangent_v, dtype=np.float64))),
        ],
        dtype=np.float64,
    )


def _surface_point(surface: ContactSurfaceRecord, uv: np.ndarray) -> np.ndarray:
    return (
        np.asarray(surface.origin, dtype=np.float64)
        + float(uv[0]) * np.asarray(surface.tangent_u, dtype=np.float64)
        + float(uv[1]) * np.asarray(surface.tangent_v, dtype=np.float64)
    )
