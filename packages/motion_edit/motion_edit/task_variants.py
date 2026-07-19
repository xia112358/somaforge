"""Task-conditioned Motion Edit variants for one motion and terrain pair."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from motion_edit.contact import (
    ContactEditPlan,
    PoseEditRecord,
    bind_anchors_to_surfaces,
    patches_from_anchors,
    read_contact_surfaces,
    write_contact_edit_plan,
    write_contact_layer,
    write_contact_surfaces,
)
from motion_edit.contact.actions import move_anchor_in_graph
from motion_edit.contact.layers import read_contact_graph
from motion_edit.contact.schema import ContactSurfaceRecord
from motion_edit.contact.surface_catalog import surfaces_from_obj_mesh_faces
from motion_edit.force_proto import contact_graph_from_masked_motion
from motion_edit.paths import LAYERS_ROOT
from motion_edit.robot_mirror import (
    ROBOT_MIRROR_SCHEMA,
    filter_mirrored_contacts_to_surfaces,
    mirror_contact_force_npz,
    mirror_motion_npz,
)
from motion_edit.workbench.edit_handles import build_contact_episode_handles

HEIGHT_VARIANT_SCHEMA = "motion_edit_height_task_variant_v1"
APPROACH_POSITION_SCHEMA = "motion_edit_approach_position_task_variant_v1"
ROBOT_MIRROR_VARIANT_SCHEMA = "motion_edit_robot_mirror_task_variant_v1"


@dataclass(frozen=True)
class HeightVariantArtifacts:
    plan_path: Path
    terrain_path: Path
    surface_catalog_path: Path
    manifest_path: Path
    source_contact_layer: str
    output_contact_layer: str
    output_motion_path: Path
    surface_transform_count: int
    contact_episode_count: int
    anchor_constraint_count: int


@dataclass(frozen=True)
class ApproachPositionVariantArtifacts:
    plan_path: Path
    terrain_path: Path
    surface_catalog_path: Path
    manifest_path: Path
    source_contact_layer: str
    output_contact_layer: str
    output_motion_path: Path
    pose_edit_count: int
    ground_anchor_edit_count: int
    contact_episode_count: int
    translation_world: tuple[float, float, float]


@dataclass(frozen=True)
class RobotMirrorVariantArtifacts:
    plan_path: Path
    terrain_path: Path
    surface_catalog_path: Path
    manifest_path: Path
    source_contact_layer: str
    output_contact_layer: str
    initial_motion_path: Path
    output_motion_path: Path
    output_contact_force_path: Path
    anchor_count: int
    event_count: int
    transition_count: int


def _write_height_scaled_obj(source: Path, output: Path, *, height_scale: float) -> None:
    if not np.isfinite(height_scale) or height_scale <= 0.0:
        raise ValueError("height_scale must be finite and positive")
    lines: list[str] = []
    vertex_count = 0
    for raw in source.read_text(encoding="utf-8").splitlines():
        if not raw.startswith("v "):
            lines.append(raw)
            continue
        fields = raw.split()
        if len(fields) != 4:
            raise ValueError(f"{source}: unsupported OBJ vertex line {raw!r}")
        x, y, z = (float(value) for value in fields[1:])
        lines.append(f"v {x:.8f} {y:.8f} {z * height_scale:.8f}")
        vertex_count += 1
    if vertex_count == 0:
        raise ValueError(f"{source}: OBJ has no vertices")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _obstacle_top_surfaces(surfaces: list[ContactSurfaceRecord]) -> list[ContactSurfaceRecord]:
    return [surface for surface in surfaces if surface.object_id != "terrain_ground" and float(surface.normal[2]) > 0.9]


def _surface_payload(surface: ContactSurfaceRecord) -> dict[str, Any]:
    return {
        "surface_id": surface.surface_id,
        "object_id": surface.object_id,
        "origin": list(surface.origin),
        "normal": list(surface.normal),
        "tangent_u": list(surface.tangent_u),
        "tangent_v": list(surface.tangent_v),
        "bounds": dict(surface.bounds) if surface.bounds is not None else None,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_height_task_variant(
    *,
    motion_id: str,
    source_motion_path: str | Path,
    contact_force_source_path: str | Path,
    source_contact_layer: str,
    source_surface_catalog: str | Path,
    source_terrain_mesh: str | Path,
    height_scale: float,
    output_dir: str | Path,
    plan_id: str | None = None,
    layers_root: Path = LAYERS_ROOT,
) -> HeightVariantArtifacts:
    """Create one height-conditioned plan whose anchors follow the moved surface.

    The obstacle footprint and every anchor's surface coordinates stay fixed.
    Only the terrain surface moves in world Z; contacts have zero displacement
    relative to the transformed surface.
    """

    if not 0.5 <= float(height_scale) <= 1.5:
        raise ValueError("height_scale must be within the supported [0.5, 1.5] range")
    source_motion = Path(source_motion_path).expanduser().resolve()
    force_source = Path(contact_force_source_path).expanduser().resolve()
    source_mesh = Path(source_terrain_mesh).expanduser().resolve()
    out_dir = Path(output_dir).expanduser().resolve()
    variant_id = plan_id or f"{motion_id}_height_{height_scale:.3f}".replace(".", "p")
    terrain_path = out_dir / "terrain" / f"multi_boxes_z_scale_{height_scale:.3f}.obj"
    surface_path = out_dir / "surfaces" / f"{variant_id}.jsonl"
    plan_path = out_dir / "plans" / f"{variant_id}.json"
    manifest_path = out_dir / "manifests" / f"{variant_id}.json"
    output_motion_path = out_dir / "motions" / f"{variant_id}.policy_ref_v1.npz"
    derived_source_layer = f"contact/task_variants/{variant_id}_source"
    output_contact_layer = f"contact/task_variants/{variant_id}"

    _write_height_scaled_obj(source_mesh, terrain_path, height_scale=float(height_scale))
    source_surfaces = read_contact_surfaces(Path(source_surface_catalog).expanduser())
    target_surfaces = surfaces_from_obj_mesh_faces(
        motion_id=motion_id,
        obj_path=terrain_path,
        include_sides=False,
        include_ground=True,
    )
    write_contact_surfaces(surface_path, target_surfaces)
    source_tops = _obstacle_top_surfaces(source_surfaces)
    target_tops = _obstacle_top_surfaces(target_surfaces)
    if len(source_tops) != 1 or len(target_tops) != 1:
        raise ValueError(
            f"height task variant currently requires one obstacle top surface; "
            f"got source={len(source_tops)} target={len(target_tops)}"
        )
    source_top = source_tops[0]
    target_top = target_tops[0]
    graph = read_contact_graph(layers_root / source_contact_layer, motion_id)
    affected_anchors = [anchor for anchor in graph.anchors if anchor.surface_id == source_top.surface_id]
    if not affected_anchors:
        raise ValueError(f"{motion_id}: no anchors are bound to obstacle top surface {source_top.surface_id}")
    translation = np.asarray(target_top.origin, dtype=np.float64) - np.asarray(source_top.origin, dtype=np.float64)
    surface_transform = {
        "transform_id": f"{variant_id}_surface_follow",
        "kind": "surface_follow",
        "translation_world": translation.tolist(),
        "source_surface": _surface_payload(source_top),
        "target_surface": _surface_payload(target_top),
        "height_scale": float(height_scale),
    }
    episodes = [
        handle
        for handle in build_contact_episode_handles(
            affected_anchors,
            max_gap_frames=10,
            min_duration_frames=20,
        )
        if handle.surface_id == source_top.surface_id
    ]

    plan = ContactEditPlan(
        plan_id=variant_id,
        source_motion_path=str(source_motion),
        source_motion_id=motion_id,
        source_contact_layer=derived_source_layer,
        edits=[],
        surface_transforms=[surface_transform],
        status="validated",
        output_motion_path=str(output_motion_path),
        output_contact_layer=output_contact_layer,
        output_segment_layer=f"candidates/task_variants/{variant_id}",
        metadata={
            "schema": HEIGHT_VARIANT_SCHEMA,
            "task_variant": "obstacle_height",
            "height_scale": float(height_scale),
            "source_terrain_mesh": str(source_mesh),
            "target_terrain_mesh": str(terrain_path),
            "target_surface_catalog": str(surface_path),
            "contact_force_source_path": str(force_source),
            "contact_semantics": "surface_coordinates_fixed_world_position_follows_surface",
            "contact_episode_count": len(episodes),
            "anchor_constraint_count": len(episodes),
            "source_anchor_fragment_count": len(affected_anchors),
            "contact_episode_policy": {"max_gap_frames": 10, "min_duration_frames": 20},
        },
    )
    plan.validate()
    write_contact_edit_plan(plan_path, plan)

    write_contact_layer(layers_root / derived_source_layer, graph)
    write_contact_surfaces(layers_root / derived_source_layer / "surfaces" / f"{motion_id}.jsonl", target_surfaces)
    write_contact_surfaces(layers_root / output_contact_layer / "surfaces" / f"{motion_id}.jsonl", target_surfaces)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema": HEIGHT_VARIANT_SCHEMA,
                "motion_id": motion_id,
                "plan_id": variant_id,
                "height_scale": float(height_scale),
                "source_motion_path": str(source_motion),
                "contact_force_source_path": str(force_source),
                "source_terrain_mesh": str(source_mesh),
                "target_terrain_mesh": str(terrain_path),
                "surface_catalog": str(surface_path),
                "source_contact_layer": derived_source_layer,
                "output_contact_layer": output_contact_layer,
                "output_motion_path": str(output_motion_path),
                "surface_transform_count": 1,
                "contact_episode_count": len(episodes),
                "anchor_constraint_count": len(episodes),
                "source_anchor_fragment_count": len(affected_anchors),
                "contact_episodes": [handle.to_dict() for handle in episodes],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return HeightVariantArtifacts(
        plan_path=plan_path,
        terrain_path=terrain_path,
        surface_catalog_path=surface_path,
        manifest_path=manifest_path,
        source_contact_layer=derived_source_layer,
        output_contact_layer=output_contact_layer,
        output_motion_path=output_motion_path,
        surface_transform_count=1,
        contact_episode_count=len(episodes),
        anchor_constraint_count=len(episodes),
    )


def create_approach_position_task_variant(
    *,
    motion_id: str,
    source_motion_path: str | Path,
    contact_force_source_path: str | Path,
    source_contact_layer: str,
    source_surface_catalog: str | Path,
    source_terrain_mesh: str | Path,
    last_step_start_frame: int,
    pose_start_frame: int,
    first_obstacle_contact_frame: int,
    farther_distance_m: float,
    output_dir: str | Path,
    lateral_left_m: float = 0.0,
    plan_id: str | None = None,
    layers_root: Path = LAYERS_ROOT,
) -> ApproachPositionVariantArtifacts:
    """Translate the final pre-contact step pose relative to a fixed obstacle."""

    farther = float(farther_distance_m)
    lateral_left = float(lateral_left_m)
    if not np.isfinite(farther) or abs(farther) > 0.2:
        raise ValueError("farther_distance_m must be finite and within [-0.2, 0.2]")
    if not np.isfinite(lateral_left) or abs(lateral_left) > 0.2:
        raise ValueError("lateral_left_m must be finite and within [-0.2, 0.2]")
    if not 0.0 < float(np.hypot(farther, lateral_left)) <= 0.2:
        raise ValueError("combined approach position offset must be within (0, 0.2]")
    if not 0 <= int(last_step_start_frame) < int(pose_start_frame) < int(first_obstacle_contact_frame):
        raise ValueError("last-step frames must satisfy start < pose_start < first obstacle contact")
    source_motion = Path(source_motion_path).expanduser().resolve()
    force_source = Path(contact_force_source_path).expanduser().resolve()
    source_mesh = Path(source_terrain_mesh).expanduser().resolve()
    out_dir = Path(output_dir).expanduser().resolve()
    variant_id = plan_id or (
        f"{motion_id}_approach_far_{farther:.3f}_left_{lateral_left:.3f}".replace(".", "p")
    )
    surface_path = out_dir / "surfaces" / f"{variant_id}.jsonl"
    plan_path = out_dir / "plans" / f"{variant_id}.json"
    manifest_path = out_dir / "manifests" / f"{variant_id}.json"
    output_motion_path = out_dir / "motions" / f"{variant_id}.policy_ref_v1.npz"
    derived_source_layer = f"contact/task_variants/{variant_id}_source"
    output_contact_layer = f"contact/task_variants/{variant_id}"

    with np.load(source_motion, allow_pickle=True) as motion:
        body_pos = np.asarray(motion["body_pos_w"], dtype=np.float64)
        body_names = [str(name) for name in np.asarray(motion["body_names"]).reshape(-1).tolist()]
    pelvis_index = body_names.index("pelvis")
    approach_delta = (
        body_pos[int(pose_start_frame), pelvis_index, :2]
        - body_pos[int(last_step_start_frame), pelvis_index, :2]
    )
    approach_norm = float(np.linalg.norm(approach_delta))
    if approach_norm <= 1.0e-6:
        raise ValueError("cannot infer approach direction from the final step")
    approach_xy = approach_delta / approach_norm
    away_xy = -approach_xy
    left_xy = np.asarray([-approach_xy[1], approach_xy[0]], dtype=np.float64)
    translation_xy = away_xy * farther + left_xy * lateral_left
    translation = np.asarray(
        [translation_xy[0], translation_xy[1], 0.0],
        dtype=np.float64,
    )

    surfaces = read_contact_surfaces(Path(source_surface_catalog).expanduser())
    write_contact_surfaces(surface_path, surfaces)
    ground_surfaces = [surface for surface in surfaces if surface.object_id == "terrain_ground"]
    if len(ground_surfaces) != 1:
        raise ValueError(f"approach position variant requires one ground surface, got {len(ground_surfaces)}")
    ground = ground_surfaces[0]
    graph = read_contact_graph(layers_root / source_contact_layer, motion_id)
    foot_bodies = {"left_foot", "left_heel", "left_toe", "left_sole", "right_foot", "right_heel", "right_toe", "right_sole"}
    ground_anchors = [
        anchor
        for anchor in graph.anchors
        if anchor.surface_id == ground.surface_id
        and anchor.body in foot_bodies
        and int(anchor.start_frame) < int(first_obstacle_contact_frame)
        and int(anchor.end_frame) > int(pose_start_frame)
    ]
    if not ground_anchors:
        raise ValueError("final pre-contact pose has no editable ground-foot anchors")
    moved_graph = graph
    anchor_edits = []
    for anchor in ground_anchors:
        moved_graph, edit = move_anchor_in_graph(
            moved_graph,
            anchor_id=anchor.anchor_id,
            delta_world=translation,
            mode="reject",
            source="task_approach_position",
        )
        affected = [
            max(int(pose_start_frame), int(anchor.start_frame)),
            min(int(first_obstacle_contact_frame), int(anchor.end_frame)),
        ]
        anchor_edits.append(
            replace(
                edit,
                edit_id=f"{variant_id}::{anchor.anchor_id}",
                affected_frames=affected,
                source="task_approach_position",
                metadata={
                    **edit.metadata,
                    "task_variant": "approach_position",
                    "pose_interval": [int(pose_start_frame), int(first_obstacle_contact_frame)],
                },
            )
        )
    pose_edit = PoseEditRecord(
        edit_id=f"{variant_id}_pose",
        motion_id=motion_id,
        affected_frames=[int(pose_start_frame), int(first_obstacle_contact_frame)],
        translation_world=translation.tolist(),
        semantic_names=[
            "root",
            "torso",
            "left_foot",
            "right_foot",
            "left_heel",
            "left_toe",
            "right_heel",
            "right_toe",
            "left_knee",
            "right_knee",
        ],
        source="task_approach_position",
        metadata={
            "last_step_start_frame": int(last_step_start_frame),
            "pose_start_frame": int(pose_start_frame),
            "first_obstacle_contact_frame": int(first_obstacle_contact_frame),
            "farther_distance_m": farther,
            "lateral_left_m": lateral_left,
        },
    )
    edited_anchor_ids = {edit.anchor_id for edit in anchor_edits}
    edited_episode_count = len(
        build_contact_episode_handles(
            [anchor for anchor in graph.anchors if anchor.anchor_id in edited_anchor_ids],
            max_gap_frames=10,
            min_duration_frames=1,
        )
    )
    plan = ContactEditPlan(
        plan_id=variant_id,
        source_motion_path=str(source_motion),
        source_motion_id=motion_id,
        source_contact_layer=derived_source_layer,
        edits=[edit.to_dict() for edit in anchor_edits],
        pose_edits=[pose_edit.to_dict()],
        status="validated",
        output_motion_path=str(output_motion_path),
        output_contact_layer=output_contact_layer,
        output_segment_layer=f"candidates/task_variants/{variant_id}",
        metadata={
            "schema": APPROACH_POSITION_SCHEMA,
            "task_variant": "approach_position",
            "last_step_start_frame": int(last_step_start_frame),
            "pose_start_frame": int(pose_start_frame),
            "first_obstacle_contact_frame": int(first_obstacle_contact_frame),
            "farther_distance_m": farther,
            "lateral_left_m": lateral_left,
            "translation_world": translation.tolist(),
            "source_terrain_mesh": str(source_mesh),
            "target_terrain_mesh": str(source_mesh),
            "target_surface_catalog": str(surface_path),
            "contact_force_source_path": str(force_source),
            "ground_anchor_edit_count": len(anchor_edits),
            "contact_episode_count": edited_episode_count,
            "contact_constraint_count": edited_episode_count,
            "source_anchor_fragment_count": len(anchor_edits),
        },
    )
    plan.validate()
    write_contact_edit_plan(plan_path, plan)
    write_contact_layer(layers_root / derived_source_layer, graph)
    write_contact_surfaces(layers_root / derived_source_layer / "surfaces" / f"{motion_id}.jsonl", surfaces)
    write_contact_surfaces(layers_root / output_contact_layer / "surfaces" / f"{motion_id}.jsonl", surfaces)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema": APPROACH_POSITION_SCHEMA,
                "motion_id": motion_id,
                "plan_id": variant_id,
                "source_motion_path": str(source_motion),
                "contact_force_source_path": str(force_source),
                "source_terrain_mesh": str(source_mesh),
                "target_terrain_mesh": str(source_mesh),
                "surface_catalog": str(surface_path),
                "source_contact_layer": derived_source_layer,
                "output_contact_layer": output_contact_layer,
                "output_motion_path": str(output_motion_path),
                "pose_edit_count": 1,
                "ground_anchor_edit_count": len(anchor_edits),
                "contact_episode_count": edited_episode_count,
                "contact_constraint_count": edited_episode_count,
                "source_anchor_fragment_count": len(anchor_edits),
                "farther_distance_m": farther,
                "lateral_left_m": lateral_left,
                "translation_world": translation.tolist(),
                "pose_edit": pose_edit.to_dict(),
                "ground_anchor_edits": [edit.to_dict() for edit in anchor_edits],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return ApproachPositionVariantArtifacts(
        plan_path=plan_path,
        terrain_path=source_mesh,
        surface_catalog_path=surface_path,
        manifest_path=manifest_path,
        source_contact_layer=derived_source_layer,
        output_contact_layer=output_contact_layer,
        output_motion_path=output_motion_path,
        pose_edit_count=1,
        ground_anchor_edit_count=len(anchor_edits),
        contact_episode_count=edited_episode_count,
        translation_world=tuple(float(value) for value in translation),
    )


def create_robot_mirror_task_variant(
    *,
    motion_id: str,
    source_motion_path: str | Path,
    contact_force_source_path: str | Path,
    source_contact_layer: str,
    source_surface_catalog: str | Path,
    source_terrain_mesh: str | Path,
    output_dir: str | Path,
    plan_id: str | None = None,
    mirror_surface_id: str | None = None,
    layers_root: Path = LAYERS_ROOT,
) -> RobotMirrorVariantArtifacts:
    """Swap the G1 leading side while leaving the obstacle asset unchanged."""

    source_motion = Path(source_motion_path).expanduser().resolve()
    force_source = Path(contact_force_source_path).expanduser().resolve()
    source_mesh = Path(source_terrain_mesh).expanduser().resolve()
    out_dir = Path(output_dir).expanduser().resolve()
    variant_id = plan_id or f"{motion_id}_robot_mirror_lr"
    surface_path = out_dir / "surfaces" / f"{variant_id}.jsonl"
    plan_path = out_dir / "plans" / f"{variant_id}.json"
    manifest_path = out_dir / "manifests" / f"{variant_id}.json"
    output_motion_path = out_dir / "motions" / f"{variant_id}.policy_ref_v1.npz"
    initial_motion_path = out_dir / "intermediate" / f"{variant_id}.mirror_init.npz"
    output_force_path = out_dir / "contact_force" / f"{variant_id}.contact_force_8part_v1.npz"
    derived_source_layer = f"contact/task_variants/{variant_id}_source"
    output_contact_layer = f"contact/task_variants/{variant_id}"

    surfaces = read_contact_surfaces(Path(source_surface_catalog).expanduser())
    write_contact_surfaces(surface_path, surfaces)
    top_surfaces = _obstacle_top_surfaces(surfaces)
    if mirror_surface_id is not None:
        top_surfaces = [surface for surface in top_surfaces if surface.surface_id == mirror_surface_id]
    if len(top_surfaces) != 1:
        raise ValueError(f"robot mirror variant requires one obstacle top surface, got {len(top_surfaces)}")
    top = top_surfaces[0]
    mirror_motion_npz(source_motion, initial_motion_path)
    mirror_motion_npz(source_motion, output_motion_path)
    mirror_contact_force_npz(force_source, output_force_path)
    contact_redetection = filter_mirrored_contacts_to_surfaces(output_force_path, surfaces)
    mirrored_graph = contact_graph_from_masked_motion(
        output_force_path,
        source="robot_local_mirror_redetected",
        motion_id=motion_id,
    )
    bound_anchors = bind_anchors_to_surfaces(
        mirrored_graph.anchors,
        surfaces,
        max_distance=0.08,
        mode="reject",
        project_world_position=False,
    )
    mirrored_graph = replace(
        mirrored_graph,
        anchors=bound_anchors,
        patches=patches_from_anchors(bound_anchors),
    )
    write_contact_layer(layers_root / derived_source_layer, mirrored_graph)
    write_contact_layer(layers_root / output_contact_layer, mirrored_graph)
    write_contact_surfaces(layers_root / derived_source_layer / "surfaces" / f"{motion_id}.jsonl", surfaces)
    write_contact_surfaces(layers_root / output_contact_layer / "surfaces" / f"{motion_id}.jsonl", surfaces)

    terrain_hash = _sha256(source_mesh)
    plan = ContactEditPlan(
        plan_id=variant_id,
        source_motion_path=str(source_motion),
        source_motion_id=motion_id,
        source_contact_layer=derived_source_layer,
        edits=[],
        status="generated",
        output_motion_path=str(output_motion_path),
        output_contact_layer=output_contact_layer,
        output_segment_layer=f"candidates/task_variants/{variant_id}",
        metadata={
            "schema": ROBOT_MIRROR_VARIANT_SCHEMA,
            "transform_schema": ROBOT_MIRROR_SCHEMA,
            "task_variant": "leading_foot_robot_only_mirror",
            "source_terrain_mesh": str(source_mesh),
            "target_terrain_mesh": str(source_mesh),
            "terrain_sha256_before": terrain_hash,
            "terrain_sha256_after": terrain_hash,
            "obstacle_transform": "identity",
            "target_surface_catalog": str(surface_path),
            "contact_force_source_path": str(force_source),
            "output_contact_force_path": str(output_force_path),
            "initial_mirror_motion_path": str(initial_motion_path),
            "generation_mode": "direct_robot_local_reflection",
            "root_transform": "identity",
            "robot_local_reflection_matrix": [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]],
            "mirror_reference_surface_id": top.surface_id,
            "left_right_semantics": "robot_joints_bodies_contacts_and_forces_swapped_per_frame",
            "contact_graph_generation": "rebuilt_from_mirrored_8part_frame_masks_and_points",
            "contact_redetection": contact_redetection,
            "world_contact_anchor_lock": False,
            "raw_contact_detail": "omitted_solver_specific_shape_and_body_ids",
        },
    )
    plan.validate()
    write_contact_edit_plan(plan_path, plan)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema": ROBOT_MIRROR_VARIANT_SCHEMA,
                "transform_schema": ROBOT_MIRROR_SCHEMA,
                "motion_id": motion_id,
                "plan_id": variant_id,
                "source_motion_path": str(source_motion),
                "output_motion_path": str(output_motion_path),
                "initial_mirror_motion_path": str(initial_motion_path),
                "generation_mode": "direct_robot_local_reflection",
                "contact_force_source_path": str(force_source),
                "output_contact_force_path": str(output_force_path),
                "source_terrain_mesh": str(source_mesh),
                "target_terrain_mesh": str(source_mesh),
                "terrain_sha256_before": terrain_hash,
                "terrain_sha256_after": terrain_hash,
                "obstacle_transform": "identity",
                "surface_catalog": str(surface_path),
                "source_contact_layer": derived_source_layer,
                "output_contact_layer": output_contact_layer,
                "root_transform": "identity",
                "robot_local_reflection_matrix": [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]],
                "mirror_reference_surface_id": top.surface_id,
                "anchor_count": len(mirrored_graph.anchors),
                "event_count": len(mirrored_graph.events),
                "transition_count": len(mirrored_graph.transitions),
                "contact_graph_generation": "rebuilt_from_mirrored_8part_frame_masks_and_points",
                "contact_redetection": contact_redetection,
                "world_contact_anchor_lock": False,
                "raw_contact_detail": "omitted_solver_specific_shape_and_body_ids",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return RobotMirrorVariantArtifacts(
        plan_path=plan_path,
        terrain_path=source_mesh,
        surface_catalog_path=surface_path,
        manifest_path=manifest_path,
        source_contact_layer=derived_source_layer,
        output_contact_layer=output_contact_layer,
        initial_motion_path=initial_motion_path,
        output_motion_path=output_motion_path,
        output_contact_force_path=output_force_path,
        anchor_count=len(mirrored_graph.anchors),
        event_count=len(mirrored_graph.events),
        transition_count=len(mirrored_graph.transitions),
    )


__all__ = [
    "APPROACH_POSITION_SCHEMA",
    "HEIGHT_VARIANT_SCHEMA",
    "ROBOT_MIRROR_VARIANT_SCHEMA",
    "ApproachPositionVariantArtifacts",
    "HeightVariantArtifacts",
    "RobotMirrorVariantArtifacts",
    "create_approach_position_task_variant",
    "create_height_task_variant",
    "create_robot_mirror_task_variant",
]
