from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from motion_edit.contact import (
    bind_anchors_to_surfaces,
    filter_short_raw_missing_anchors,
    merge_nearby_contact_anchors,
    read_contact_surfaces,
    refine_contact_graph_anchor_positions_from_raw_contacts,
    split_foot_contact_anchors,
    write_contact_layer,
    write_contact_surfaces,
)
from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.layers import read_contact_graph
from motion_edit.contact.patches import patches_from_anchors
from motion_edit.contact.surface_catalog import surfaces_from_obj_mesh_faces, surfaces_from_urdf_meshes
from motion_edit.io import write_jsonl
from motion_edit.paths import LAYERS_ROOT, SURFACES_ROOT, WORKBENCH_ROOT
from motion_edit.contact.segmentation.editor_cuts import stable_proto_transitions_for_editor
from motion_edit.workbench.surface_editor_session import SurfaceEditorSession, prepare_surface_editor_session


@dataclass(frozen=True)
class ContactEditorConfig:
    motion: str
    motion_id: str
    source_contact_layer: str
    session_name: str
    surface_catalog: str | None = None
    terrain_urdf: str | None = None
    terrain_mesh: str | None = None
    output_prefix: str | None = None
    edit_plan: str | None = None
    output_contact_layer: str | None = None
    repo_root: str | None = None
    with_terrain: bool = False
    ground_z: float = 0.0
    ground_half_extent: float = 10.0
    merge_max_gap: int = 3
    merge_max_distance: float = 0.06
    max_surface_distance: float = 0.08
    bind_mode: str = "reject"
    fps: int = 50
    prebound_contact_layer: bool = False
    contact_force_motion: str | None = None


@dataclass(frozen=True)
class PreparedContactEditor:
    session: SurfaceEditorSession
    ready_layer: str
    surface_catalog: str
    source_anchor_count: int
    merged_anchor_count: int
    visible_anchor_count: int
    ready_anchor_count: int
    filtered_count: int
    bound_count: int


def surface_binding_counts(graph: ContactGraph) -> dict[str, int]:
    statuses = []
    for anchor in graph.anchors:
        bindings = anchor.metadata.get("surface_bindings")
        latest = bindings[-1] if isinstance(bindings, list) and bindings else None
        if anchor.metadata.get("surface_binding_failed"):
            statuses.append("failed")
        elif not anchor.surface_id:
            statuses.append("unbound")
        elif isinstance(latest, dict) and latest.get("clamped"):
            statuses.append("clamped")
        elif anchor.surface_id and latest is None:
            statuses.append("suspicious")
        else:
            statuses.append("bound")
    return {
        "anchor_count": len(graph.anchors),
        "bound_count": statuses.count("bound") + statuses.count("clamped") + statuses.count("suspicious"),
        "unbound_count": statuses.count("unbound"),
        "failed_count": statuses.count("failed"),
        "clamped_count": statuses.count("clamped"),
        "suspicious_count": statuses.count("suspicious"),
    }


def default_terrain_surface_catalog(motion_id: str) -> Path:
    return SURFACES_ROOT / f"{motion_id}_terrain_surfaces.jsonl"


def write_urdf_surface_catalog(
    *,
    motion_id: str,
    terrain_urdf: str | Path,
    output: str | Path | None,
    include_side_surfaces: bool = False,
    include_ground: bool = True,
    ground_z: float = 0.0,
    ground_half_extent: float = 10.0,
) -> Path:
    out = Path(output).expanduser() if output is not None else default_terrain_surface_catalog(motion_id)
    surfaces = surfaces_from_urdf_meshes(
        motion_id=motion_id,
        urdf_path=terrain_urdf,
        include_sides=include_side_surfaces,
        include_ground=include_ground,
        ground_z=ground_z,
        ground_half_extent=ground_half_extent,
    )
    write_contact_surfaces(out, surfaces)
    return out


def write_obj_surface_catalog(
    *,
    motion_id: str,
    terrain_mesh: str | Path,
    output: str | Path | None,
    include_side_surfaces: bool = False,
    include_ground: bool = True,
    ground_z: float = 0.0,
    ground_half_extent: float = 10.0,
) -> Path:
    out = Path(output).expanduser() if output is not None else default_terrain_surface_catalog(motion_id)
    surfaces = surfaces_from_obj_mesh_faces(
        motion_id=motion_id,
        obj_path=terrain_mesh,
        include_sides=include_side_surfaces,
        include_ground=include_ground,
        ground_z=ground_z,
        ground_half_extent=ground_half_extent,
    )
    write_contact_surfaces(out, surfaces)
    return out


def resolve_surface_catalog(
    *,
    motion_id: str,
    surface_catalog: str | None,
    terrain_urdf: str | Path | None,
    terrain_mesh: str | Path | None = None,
    include_side_surfaces: bool = False,
    include_ground: bool = True,
    ground_z: float = 0.0,
    ground_half_extent: float = 10.0,
) -> Path:
    if surface_catalog:
        path = Path(surface_catalog).expanduser()
        if not path.exists():
            raise FileNotFoundError(path)
        return path
    if terrain_mesh:
        return write_obj_surface_catalog(
            motion_id=motion_id,
            terrain_mesh=terrain_mesh,
            output=None,
            include_side_surfaces=include_side_surfaces,
            include_ground=include_ground,
            ground_z=ground_z,
            ground_half_extent=ground_half_extent,
        )
    if terrain_urdf:
        return write_urdf_surface_catalog(
            motion_id=motion_id,
            terrain_urdf=terrain_urdf,
            output=None,
            include_side_surfaces=include_side_surfaces,
            include_ground=include_ground,
            ground_z=ground_z,
            ground_half_extent=ground_half_extent,
        )
    raise ValueError("surface catalog is required; pass surface_catalog, terrain_mesh, or terrain_urdf")


def filter_surfaces_for_binding(surfaces, *, include_side_surfaces: bool):
    if include_side_surfaces:
        return list(surfaces)
    return [
        surface
        for surface in surfaces
        if surface.surface_id == "terrain_ground_z0" or float(surface.normal[2]) > 0.5
    ]


def infer_terrain_urdf(config: ContactEditorConfig) -> str | None:
    return config.terrain_urdf


def prepare_contact_editor_session(
    config: ContactEditorConfig,
    *,
    layers_root: Path = LAYERS_ROOT,
    workbench_root: Path = WORKBENCH_ROOT,
) -> PreparedContactEditor:
    terrain_urdf = infer_terrain_urdf(config)
    surface_catalog = resolve_surface_catalog(
        motion_id=config.motion_id,
        surface_catalog=config.surface_catalog,
        terrain_urdf=terrain_urdf,
        terrain_mesh=config.terrain_mesh,
        include_side_surfaces=False,
        include_ground=True,
        ground_z=config.ground_z,
        ground_half_extent=config.ground_half_extent,
    )
    source_layer = config.source_contact_layer
    prefix = config.output_prefix or f"contact/{config.session_name}"
    merged_layer = f"{prefix}_merged"
    visible_layer = f"{prefix}_editor_visible"
    ready_layer = f"{prefix}_editor_ready"

    surfaces = filter_surfaces_for_binding(read_contact_surfaces(surface_catalog), include_side_surfaces=False)
    graph = read_contact_graph(layers_root / source_layer, config.motion_id)
    contact_motion = config.contact_force_motion or config.motion
    if config.prebound_contact_layer:
        counts = surface_binding_counts(graph)
        if counts["unbound_count"] or counts["failed_count"]:
            raise ValueError(
                "contact-editor refused to open because prebound contact layer is not fully bound: "
                f"anchors={counts['anchor_count']} bound={counts['bound_count']} "
                f"unbound={counts['unbound_count']} failed={counts['failed_count']}"
            )
        session = prepare_surface_editor_session(
            motion_path=config.motion,
            contact_force_path=contact_motion,
            motion_id=config.motion_id,
            contact_layer=source_layer,
            surface_catalog=str(surface_catalog),
            session_name=config.session_name,
            edit_plan_path=config.edit_plan,
            output_contact_layer=config.output_contact_layer or f"{source_layer}_edited",
            layers_root=layers_root,
            workbench_root=workbench_root,
        )
        return PreparedContactEditor(
            session=session,
            ready_layer=source_layer,
            surface_catalog=str(surface_catalog),
            source_anchor_count=len(graph.anchors),
            merged_anchor_count=len(graph.anchors),
            visible_anchor_count=len(graph.anchors),
            ready_anchor_count=len(graph.anchors),
            filtered_count=0,
            bound_count=counts["bound_count"],
        )
    try:
        graph = refine_contact_graph_anchor_positions_from_raw_contacts(
            graph,
            contact_motion,
            surfaces=surfaces,
            max_surface_distance=config.max_surface_distance,
        )
    except Exception as exc:
        message = str(exc)
        if "missing raw contact fields" not in message and "Failed to interpret file" not in message:
            raise
    graph = split_foot_contact_anchors(graph)
    merged_graph, merge_events = merge_nearby_contact_anchors(
        graph,
        max_gap=config.merge_max_gap,
        max_distance=config.merge_max_distance,
        merge_classes={"top", "ground"},
        same_class_only=True,
        source="contact_editor_merge",
    )
    merged_root = write_contact_layer(layers_root / merged_layer, merged_graph)
    if merge_events:
        write_jsonl(merged_root / "edits" / f"{config.motion_id}.merge_events.jsonl", merge_events)

    visible_graph, filter_events = filter_short_raw_missing_anchors(
        merged_graph,
        drop_classes={"raw_missing", "edge_candidate", "outside_known_surfaces"},
        source="contact_editor_filter",
    )
    visible_root = write_contact_layer(layers_root / visible_layer, visible_graph)
    if filter_events:
        write_jsonl(visible_root / "edits" / f"{config.motion_id}.filter_events.jsonl", filter_events)

    bound_anchors = bind_anchors_to_surfaces(
        visible_graph.anchors,
        surfaces,
        max_distance=config.max_surface_distance,
        mode=config.bind_mode,
    )
    bound_graph = ContactGraph(
        motion_id=visible_graph.motion_id,
        events=visible_graph.events,
        anchors=bound_anchors,
        patches=patches_from_anchors(bound_anchors),
        transitions=visible_graph.transitions,
    )
    ready_transitions = stable_proto_transitions_for_editor(
        graph=bound_graph,
        motion=contact_motion,
        fps=config.fps,
        fallback=visible_graph.transitions,
    )
    ready_graph = ContactGraph(
        motion_id=bound_graph.motion_id,
        events=bound_graph.events,
        anchors=bound_graph.anchors,
        patches=bound_graph.patches,
        transitions=ready_transitions,
    )
    counts = surface_binding_counts(ready_graph)
    if counts["unbound_count"] or counts["failed_count"]:
        raise ValueError(
            "contact-editor refused to open because editor-ready contact layer is not fully bound: "
            f"anchors={counts['anchor_count']} bound={counts['bound_count']} "
            f"unbound={counts['unbound_count']} failed={counts['failed_count']}"
        )
    ready_root = write_contact_layer(layers_root / ready_layer, ready_graph)
    write_contact_surfaces(ready_root / "surfaces" / f"{config.motion_id}.jsonl", surfaces)
    session = prepare_surface_editor_session(
        motion_path=config.motion,
        contact_force_path=contact_motion,
        motion_id=config.motion_id,
        contact_layer=ready_layer,
        surface_catalog=str(surface_catalog),
        session_name=config.session_name,
        edit_plan_path=config.edit_plan,
        output_contact_layer=config.output_contact_layer or f"{ready_layer}_edited",
        layers_root=layers_root,
        workbench_root=workbench_root,
    )
    return PreparedContactEditor(
        session=session,
        ready_layer=ready_layer,
        surface_catalog=str(surface_catalog),
        source_anchor_count=len(graph.anchors),
        merged_anchor_count=len(merged_graph.anchors),
        visible_anchor_count=len(visible_graph.anchors),
        ready_anchor_count=len(ready_graph.anchors),
        filtered_count=len(filter_events),
        bound_count=counts["bound_count"],
    )
