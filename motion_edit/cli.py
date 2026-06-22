from __future__ import annotations

import argparse
from dataclasses import replace
import shutil
from pathlib import Path

from .adapters.omniretarget import detect_omniretarget_paths
from .adapters.lte import import_lte_catalog
from .curation import filter_segments, load_layer_segments, write_status_layer
from .editing import clip_motion, splice_motions
from .export import (
    export_contact_overlay,
    export_cutter_segments,
    export_motion_manifest,
    export_motion_version_manifest,
    export_split_npz,
    export_surface_binding_overlay,
    export_surface_binding_report,
)
from .force_proto import contact_graph_from_masked_motion, segments_from_masked_motion
from .io import read_jsonl, segment_from_dict, write_jsonl
from .layers import iter_layer_files, read_layer, write_layer
from .paths import BACKUPS_ROOT, EXPORTS_ROOT, LAYERS_ROOT, SURFACES_ROOT, WORKBENCH_ROOT, ensure_data_dirs, layer_dir
from .contact import (
    append_anchor_edit_to_plan,
    bind_anchors_to_surfaces,
    bind_segment_to_contact_graph,
    filter_short_raw_missing_anchors,
    merge_nearby_contact_anchors,
    move_anchor_in_contact_layer,
    read_contact_edit_plan,
    read_contact_surfaces,
    refine_contact_graph_anchor_positions_from_raw_contacts,
    validate_contact_edit_plan,
    write_contact_edit_plan,
    write_contact_layer,
    write_contact_surfaces,
)
from .contact.graph import ContactGraph
from .contact.generation import apply_contact_edit_plan_to_motion
from .contact.layers import read_contact_graph
from .contact.patches import patches_from_anchors
from .contact.surface_catalog import box_surfaces, parse_box_descriptor, surfaces_from_urdf_meshes
from .storage.canonical import build_canonical_segments, mark_canonical_segment_statuses, write_motion_version_with_canonical_segments
from .storage.io import (
    read_canonical_segments,
    read_motion_version,
    read_token_catalog,
    replace_canonical_segments,
    write_canonical_segments,
    write_motion_asset,
    write_motion_version,
    write_token_catalog,
)
from .storage.schema import MotionAssetRecord, MotionVersionRecord
from .storage.tokens import build_tokens_from_segments
from .viewer import launch_viewer
from .workbench import (
    WorkbenchSession,
    curate_segment,
    export_cutter_session_file,
    load_workbench_segments,
    make_workbench_server,
    move_surface_editor_anchor,
    prepare_surface_editor_session,
    read_surface_editor_session,
    replace_segment,
    save_surface_editor_session,
    select_segment,
    split_segment,
    sync_cutter_session_file,
    sync_surface_editor_requests,
    trim_segment,
    upsert_workbench_segments,
    write_workbench_segments,
)


def _cmd_init(_args: argparse.Namespace) -> None:
    ensure_data_dirs()
    print(f"initialized {LAYERS_ROOT.parents[0]}")


def _cmd_import_force_proto(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    motion_dir = Path(args.motion_dir).expanduser().resolve()
    out_dir = layer_dir("candidate", args.layer_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for motion_path in sorted(motion_dir.glob(args.pattern)):
        segments = segments_from_masked_motion(motion_path, source=args.source, status="candidate")
        write_layer(out_dir / f"{motion_path.stem}.jsonl", segments)
        graph = contact_graph_from_masked_motion(motion_path, source=args.source)
        write_contact_layer(LAYERS_ROOT / "contact" / args.layer_name, graph)
        total += len(segments)
    print(f"wrote {total} candidate segments to {out_dir}; contact layer={LAYERS_ROOT / 'contact' / args.layer_name}")


def _warn_legacy_layer_workflow(preferred: str) -> None:
    print(f"legacy layer workflow: for canonical storage, use {preferred} instead.")


def _cmd_import_manual_cuts(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    _warn_legacy_layer_workflow("cutter --update-canonical or build-canonical-segmentation")
    segments_dir = Path(args.segments_dir).expanduser().resolve()
    out_dir = LAYERS_ROOT / "manual" / args.layer_name
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for source_path in sorted(segments_dir.glob("*.segments.jsonl")):
        records = read_jsonl(source_path)
        segments = [segment_from_dict(item, default_source="manual", default_status="manual") for item in records]
        out_path = out_dir / f"{source_path.name.removesuffix('.segments.jsonl')}.jsonl"
        write_layer(out_path, segments)
        total += len(segments)
    print(f"wrote {total} manual segments to {out_dir}")


def _load_source_segments(source: str) -> list:
    return load_layer_segments(source)


def _cmd_export_cutter_segments(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    _warn_legacy_layer_workflow("cutter --motion-version-id ... --update-canonical")
    segments = _load_source_segments(args.source)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else EXPORTS_ROOT / "cutter_segments" / args.source.replace("/", "_")
    written = export_cutter_segments(output_dir, segments)
    if args.install_to:
        install_dir = Path(args.install_to).expanduser().resolve()
        backup_dir = BACKUPS_ROOT / f"cutter_segments_{args.source.replace('/', '_')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for path in written:
            target = install_dir / path.name
            if target.exists():
                shutil.copy2(target, backup_dir / target.name)
            shutil.copy2(path, target)
        print(f"installed {len(written)} cutter segment files to {install_dir}; backups in {backup_dir}")
    else:
        print(f"exported {len(written)} cutter segment files to {output_dir}")


def _cmd_export_contact_overlay(args: argparse.Namespace) -> None:
    graph = read_contact_graph(LAYERS_ROOT / args.source, args.motion_id)
    output = export_contact_overlay(args.output, graph)
    print(f"wrote contact overlay {output}")


def _read_surfaces_for_contact_layer(contact_layer: str, motion_id: str, surface_catalog: str | None):
    if surface_catalog:
        return read_contact_surfaces(Path(surface_catalog).expanduser())
    sidecar = LAYERS_ROOT / contact_layer / "surfaces" / f"{motion_id}.jsonl"
    if sidecar.exists():
        return read_contact_surfaces(sidecar)
    return []


def _surface_binding_counts(graph) -> dict[str, int]:
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


def _cmd_export_surface_binding_report(args: argparse.Namespace) -> None:
    graph = read_contact_graph(LAYERS_ROOT / args.contact_layer, args.motion_id)
    surfaces = _read_surfaces_for_contact_layer(args.contact_layer, args.motion_id, args.surface_catalog)
    out = export_surface_binding_report(args.output, graph=graph, surfaces=surfaces)
    counts = _surface_binding_counts(graph)
    print(
        f"wrote surface binding report {out} anchors={counts['anchor_count']} "
        f"bound={counts['bound_count']} unbound={counts['unbound_count']} failed={counts['failed_count']} "
        f"clamped={counts['clamped_count']} surfaces={len(surfaces)}"
    )


def _cmd_export_surface_binding_overlay(args: argparse.Namespace) -> None:
    graph = read_contact_graph(LAYERS_ROOT / args.contact_layer, args.motion_id)
    surfaces = _read_surfaces_for_contact_layer(args.contact_layer, args.motion_id, args.surface_catalog)
    out = export_surface_binding_overlay(args.output, graph=graph, surfaces=surfaces)
    counts = _surface_binding_counts(graph)
    print(
        f"wrote surface binding overlay {out} anchors={counts['anchor_count']} "
        f"bound={counts['bound_count']} unbound={counts['unbound_count']} failed={counts['failed_count']} "
        f"clamped={counts['clamped_count']} surfaces={len(surfaces)}"
    )


def _cmd_summarize_surface_bindings(args: argparse.Namespace) -> None:
    graph = read_contact_graph(LAYERS_ROOT / args.contact_layer, args.motion_id)
    surfaces = _read_surfaces_for_contact_layer(args.contact_layer, args.motion_id, args.surface_catalog)
    counts = _surface_binding_counts(graph)
    used_surfaces = sorted({anchor.surface_id for anchor in graph.anchors if anchor.surface_id})
    suspicious = []
    for anchor in graph.anchors:
        bindings = anchor.metadata.get("surface_bindings")
        if anchor.metadata.get("surface_binding_failed") or (anchor.surface_id and not bindings):
            suspicious.append(anchor)
    print(f"motion_id={args.motion_id}")
    print(
        f"anchors={counts['anchor_count']} bound={counts['bound_count']} unbound={counts['unbound_count']} "
        f"failed={counts['failed_count']} clamped={counts['clamped_count']} suspicious={counts['suspicious_count']}"
    )
    print(f"surfaces={len(surfaces)} used={','.join(used_surfaces) if used_surfaces else '<none>'}")
    for anchor in suspicious[: args.limit]:
        reason = anchor.metadata.get("surface_binding_failure_reason") or "binding metadata missing"
        print(f"suspicious {anchor.anchor_id} body={anchor.body} surface={anchor.surface_id} reason={reason}")


def _cmd_bind_contact_surfaces(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    contact_layer = args.contact_layer
    version = None
    if args.motion_version_id:
        version = read_motion_version(args.motion_version_id)
        if contact_layer is None:
            contact_layer = version.contact_layer
    if contact_layer is None:
        raise ValueError("bind-contact-surfaces requires --contact-layer or --motion-version-id with contact_layer")
    if args.update_motion_version and not args.motion_version_id:
        raise ValueError("--update-motion-version requires --motion-version-id")
    graph = read_contact_graph(LAYERS_ROOT / contact_layer, args.motion_id)
    surface_catalog = _resolve_surface_catalog(
        motion_id=args.motion_id,
        surface_catalog=args.surface_catalog,
        terrain_urdf=getattr(args, "terrain_urdf", None),
        include_side_surfaces=getattr(args, "include_side_surfaces", False),
        include_ground=not getattr(args, "no_ground", False),
        ground_z=getattr(args, "ground_z", 0.0),
        ground_half_extent=getattr(args, "ground_half_extent", 10.0),
    )
    surfaces = _filter_surfaces_for_binding(
        read_contact_surfaces(surface_catalog),
        include_side_surfaces=getattr(args, "include_side_surfaces", False),
    )
    bound_anchors = bind_anchors_to_surfaces(
        graph.anchors,
        surfaces,
        max_distance=args.max_distance,
        mode=args.mode,
    )
    bound_graph = ContactGraph(
        motion_id=graph.motion_id,
        events=graph.events,
        anchors=bound_anchors,
        patches=patches_from_anchors(bound_anchors),
        transitions=graph.transitions,
    )
    out_layer = write_contact_layer(LAYERS_ROOT / args.output_contact_layer, bound_graph)
    write_contact_surfaces(out_layer / "surfaces" / f"{args.motion_id}.jsonl", surfaces)
    bound_count = sum(1 for anchor in bound_anchors if anchor.surface_id)
    failed_count = sum(1 for anchor in bound_anchors if anchor.metadata.get("surface_binding_failed"))
    clamped_count = sum(
        1
        for anchor in bound_anchors
        for binding in anchor.metadata.get("surface_bindings", [])
        if binding.get("clamped")
    )
    if args.update_motion_version and version is not None:
        write_motion_version(replace(version, contact_layer=args.output_contact_layer))
    if args.rebind_canonical_segments:
        if not args.motion_version_id:
            raise ValueError("--rebind-canonical-segments requires --motion-version-id")
        segments = [
            bind_segment_to_contact_graph(segment, bound_graph)
            for segment in read_canonical_segments(args.motion_version_id)
        ]
        replace_canonical_segments(
            args.motion_version_id,
            segments,
            reason=f"surface binding from {args.output_contact_layer}",
            source="surface_binding",
            kind="surface_binding_rebind",
        )
    print(
        f"bound contact surfaces motion={args.motion_id} total={len(bound_anchors)} "
        f"bound={bound_count} unbound={len(bound_anchors) - bound_count} clamped={clamped_count} failed={failed_count}"
    )
    print(f"wrote contact layer {out_layer}")


def _cmd_refine_contact_anchor_positions(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    graph = read_contact_graph(LAYERS_ROOT / args.contact_layer, args.motion_id)
    surfaces = read_contact_surfaces(args.surface_catalog) if args.surface_catalog else None
    refined_graph = refine_contact_graph_anchor_positions_from_raw_contacts(
        graph,
        args.motion,
        surfaces=surfaces,
        max_part_distance=args.max_part_distance,
        max_surface_distance=args.max_surface_distance,
    )
    out_layer = write_contact_layer(LAYERS_ROOT / args.output_contact_layer, refined_graph)
    if surfaces is not None:
        write_contact_surfaces(out_layer / "surfaces" / f"{args.motion_id}.jsonl", surfaces)
    refined_count = sum(
        1
        for anchor in refined_graph.anchors
        if not anchor.metadata.get("raw_contact_position_refinement_failed")
    )
    failed_count = len(refined_graph.anchors) - refined_count
    print(
        f"refined contact anchor positions motion={args.motion_id} total={len(refined_graph.anchors)} "
        f"refined={refined_count} failed={failed_count}"
    )
    print(f"wrote contact layer {out_layer}")


def _cmd_merge_contact_anchors(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    graph = read_contact_graph(LAYERS_ROOT / args.contact_layer, args.motion_id)
    merge_classes = set(args.merge_class) if args.merge_class else None
    merged_graph, events = merge_nearby_contact_anchors(
        graph,
        max_gap=args.max_gap,
        max_distance=args.max_distance,
        merge_classes=merge_classes,
        same_class_only=not args.allow_cross_class,
        source=args.source,
    )
    out_layer = write_contact_layer(LAYERS_ROOT / args.output_contact_layer, merged_graph)
    if events:
        write_jsonl(out_layer / "edits" / f"{args.motion_id}.merge_events.jsonl", events)
    print(
        f"merged contact anchors motion={args.motion_id} before={len(graph.anchors)} "
        f"after={len(merged_graph.anchors)} merges={len(events)}"
    )
    print(f"wrote contact layer {out_layer}")


def _cmd_filter_contact_anchors(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    graph = read_contact_graph(LAYERS_ROOT / args.contact_layer, args.motion_id)
    neighbor_classes = set(args.neighbor_class) if args.neighbor_class else None
    filtered_graph, events = filter_short_raw_missing_anchors(
        graph,
        max_duration=args.max_duration,
        max_gap=args.max_gap,
        max_distance=args.max_distance,
        neighbor_classes=neighbor_classes,
        drop_classes=set(args.drop_class or []),
        source=args.source,
    )
    out_layer = write_contact_layer(LAYERS_ROOT / args.output_contact_layer, filtered_graph)
    if events:
        write_jsonl(out_layer / "edits" / f"{args.motion_id}.filter_events.jsonl", events)
    print(
        f"filtered contact anchors motion={args.motion_id} before={len(graph.anchors)} "
        f"after={len(filtered_graph.anchors)} removed={len(events)}"
    )
    print(f"wrote contact layer {out_layer}")


def _prepare_contact_editor_layer(args: argparse.Namespace) -> tuple[str, str]:
    source_layer = args.source_contact_layer
    prefix = args.output_prefix or f"contact/{args.session_name}"
    merged_layer = f"{prefix}_merged"
    visible_layer = f"{prefix}_editor_visible"
    ready_layer = f"{prefix}_editor_ready"

    graph = read_contact_graph(LAYERS_ROOT / source_layer, args.motion_id)
    merged_graph, merge_events = merge_nearby_contact_anchors(
        graph,
        max_gap=args.merge_max_gap,
        max_distance=args.merge_max_distance,
        merge_classes={"top", "ground"},
        same_class_only=True,
        source="contact_editor_merge",
    )
    merged_root = write_contact_layer(LAYERS_ROOT / merged_layer, merged_graph)
    if merge_events:
        write_jsonl(merged_root / "edits" / f"{args.motion_id}.merge_events.jsonl", merge_events)

    visible_graph, filter_events = filter_short_raw_missing_anchors(
        merged_graph,
        drop_classes={"raw_missing", "edge_candidate", "outside_known_surfaces"},
        source="contact_editor_filter",
    )
    visible_root = write_contact_layer(LAYERS_ROOT / visible_layer, visible_graph)
    if filter_events:
        write_jsonl(visible_root / "edits" / f"{args.motion_id}.filter_events.jsonl", filter_events)

    surface_catalog = _resolve_surface_catalog(
        motion_id=args.motion_id,
        surface_catalog=args.surface_catalog,
        terrain_urdf=args.terrain_urdf,
        include_side_surfaces=False,
        include_ground=True,
        ground_z=args.ground_z,
        ground_half_extent=args.ground_half_extent,
    )
    surfaces = _filter_surfaces_for_binding(read_contact_surfaces(surface_catalog), include_side_surfaces=False)
    bound_anchors = bind_anchors_to_surfaces(
        visible_graph.anchors,
        surfaces,
        max_distance=args.max_surface_distance,
        mode=args.bind_mode,
    )
    ready_graph = ContactGraph(
        motion_id=visible_graph.motion_id,
        events=visible_graph.events,
        anchors=bound_anchors,
        patches=patches_from_anchors(bound_anchors),
        transitions=visible_graph.transitions,
    )
    counts = _surface_binding_counts(ready_graph)
    if counts["unbound_count"] or counts["failed_count"]:
        raise ValueError(
            "contact-editor refused to open because editor-ready contact layer is not fully bound: "
            f"anchors={counts['anchor_count']} bound={counts['bound_count']} "
            f"unbound={counts['unbound_count']} failed={counts['failed_count']}"
        )
    ready_root = write_contact_layer(LAYERS_ROOT / ready_layer, ready_graph)
    write_contact_surfaces(ready_root / "surfaces" / f"{args.motion_id}.jsonl", surfaces)
    print(
        "prepared contact editor layer "
        f"source={source_layer} merged={merged_layer} visible={visible_layer} ready={ready_layer}"
    )
    print(
        f"contact-editor anchors source={len(graph.anchors)} merged={len(merged_graph.anchors)} "
        f"visible={len(visible_graph.anchors)} ready={len(ready_graph.anchors)} "
        f"filtered={len(filter_events)} bound={counts['bound_count']}"
    )
    return ready_layer, str(surface_catalog)


def _launch_surface_editor_for_args(args: argparse.Namespace, *, contact_layer: str, surface_catalog: str | None) -> None:
    session = prepare_surface_editor_session(
        motion_path=args.motion,
        motion_id=args.motion_id,
        contact_layer=contact_layer,
        surface_catalog=surface_catalog,
        session_name=args.session_name,
        edit_plan_path=args.edit_plan,
        output_contact_layer=args.output_contact_layer,
        layers_root=LAYERS_ROOT,
        workbench_root=WORKBENCH_ROOT,
    )
    print(f"surface editor session: {session.session_dir}")
    print(f"surface binding report: {session.report_path}")
    print(f"surface binding overlay: {session.overlay_path}")
    print(f"contact overlay: {session.contact_overlay_path}")
    print(f"pending edits: {session.pending_edits_path}")
    print(f"surface edit requests: {session.request_path}")
    print(f"viewer overlay support: local motion_edit Viser adapter edit_mode={args.edit_mode}")
    if args.edit_mode == "request":
        print(f"sync pending viewer requests: motion-edit surface-editor-sync --session {session.session_dir / 'session.json'}")
        print(f"save after sync: motion-edit surface-editor-sync --session {session.session_dir / 'session.json'} --save")
    else:
        print("direct edit mode: use Viser 'Move anchor' and 'Save edits'; no terminal sync is required")
        print(f"request fallback remains available: motion-edit surface-editor-sync --session {session.session_dir / 'session.json'}")
    process = launch_viewer(
        args.motion,
        repo_root=args.repo_root,
        layer=None,
        conda_env=args.conda_env,
        timeline_port=args.timeline_port,
        fps=args.fps,
        with_terrain=args.with_terrain,
        surface_binding_overlay=session.overlay_path,
        surface_editor_session=session.session_dir / "session.json",
        surface_editor_requests=session.request_path,
        surface_editor_edit_mode=args.edit_mode,
        surface_editor_step_size=args.step_size,
        surface_editor_default_mode=args.default_mode,
        surface_editor_show_only=args.show_only,
        surface_editor_select_anchor=args.select_anchor,
        prefer_local_surface_editor=not args.external_viewer,
    )
    print(f"viewer pid={process.pid}")
    print(f"Open Motion Cutter: http://localhost:{args.timeline_port}")
    process.wait()
    if args.save_on_exit:
        out = save_surface_editor_session(session, layers_root=LAYERS_ROOT)
        print(f"saved surface editor session output_contact_layer={out}")
    else:
        print("surface editor session prepared; no ContactLayer was saved because --save-on-exit was not set")


def _cmd_contact_editor(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    if args.include_side_surfaces:
        raise ValueError("contact-editor does not allow side surfaces; use surface-editor only for debug")
    if args.no_ground:
        raise ValueError("contact-editor requires ground surface support")
    if args.surface_catalog is None and args.terrain_urdf is None and args.with_terrain:
        paths = detect_omniretarget_paths(args.motion, repo_root=args.repo_root)
        if paths.terrain_urdf is None:
            raise ValueError("--with-terrain could not resolve a terrain URDF; pass --surface-catalog or --terrain-urdf")
        args.terrain_urdf = str(paths.terrain_urdf)
    ready_layer, surface_catalog = _prepare_contact_editor_layer(args)
    if args.output_contact_layer is None:
        args.output_contact_layer = f"{ready_layer}_edited"
    _launch_surface_editor_for_args(args, contact_layer=ready_layer, surface_catalog=surface_catalog)


def _cmd_create_box_surface_catalog(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    surfaces = []
    for descriptor in args.box:
        object_id, center, size = parse_box_descriptor(descriptor)
        surfaces.extend(
            box_surfaces(
                motion_id=args.motion_id,
                object_id=object_id,
                center=center,
                size=size,
                include_sides=not args.top_only,
            )
        )
    write_contact_surfaces(args.output, surfaces)
    print(f"wrote {len(surfaces)} contact surfaces to {Path(args.output).expanduser()}")


def _default_terrain_surface_catalog(motion_id: str) -> Path:
    return SURFACES_ROOT / f"{motion_id}_terrain_surfaces.jsonl"


def _write_urdf_surface_catalog(
    *,
    motion_id: str,
    terrain_urdf: str | Path,
    output: str | Path | None,
    include_side_surfaces: bool = False,
    include_ground: bool = True,
    ground_z: float = 0.0,
    ground_half_extent: float = 10.0,
) -> Path:
    out = Path(output).expanduser() if output is not None else _default_terrain_surface_catalog(motion_id)
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


def _resolve_surface_catalog(
    *,
    motion_id: str,
    surface_catalog: str | None,
    terrain_urdf: str | Path | None,
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
    if terrain_urdf:
        out = _write_urdf_surface_catalog(
            motion_id=motion_id,
            terrain_urdf=terrain_urdf,
            output=None,
            include_side_surfaces=include_side_surfaces,
            include_ground=include_ground,
            ground_z=ground_z,
            ground_half_extent=ground_half_extent,
        )
        print(f"generated terrain surface catalog from URDF: {out}")
        return out
    raise ValueError("surface catalog is required; pass --surface-catalog or --terrain-urdf")


def _filter_surfaces_for_binding(surfaces, *, include_side_surfaces: bool):
    if include_side_surfaces:
        return list(surfaces)
    return [
        surface
        for surface in surfaces
        if surface.surface_id == "terrain_ground_z0" or float(surface.normal[2]) > 0.5
    ]


def _cmd_create_urdf_surface_catalog(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    out = _write_urdf_surface_catalog(
        motion_id=args.motion_id,
        terrain_urdf=args.terrain_urdf,
        output=args.output,
        include_side_surfaces=args.include_side_surfaces,
        include_ground=not args.no_ground,
        ground_z=args.ground_z,
        ground_half_extent=args.ground_half_extent,
    )
    surfaces = read_contact_surfaces(out)
    print(f"wrote {len(surfaces)} URDF contact surfaces to {out}")


def _cmd_move_contact_anchor(args: argparse.Namespace) -> None:
    destination = args.output_source or f"{args.source}_edited"
    new_world = args.new_world_position
    delta_world = args.delta_world
    moved_graph, edit = move_anchor_in_contact_layer(
        LAYERS_ROOT / args.source,
        LAYERS_ROOT / destination,
        motion_id=args.motion_id,
        anchor_id=args.anchor_id,
        delta_world=delta_world,
        tangent_delta=args.tangent_delta,
        new_world_position=new_world,
        mode=args.mode,
        allow_free_3d=args.allow_free_3d,
        source=args.edit_source,
    )
    moved_anchor = next(anchor for anchor in moved_graph.anchors if anchor.anchor_id == args.anchor_id)
    print(
        f"moved anchor {args.anchor_id} motion={args.motion_id} "
        f"world_position={moved_anchor.world_position} edit={edit.edit_id} output={LAYERS_ROOT / destination}"
    )
    if args.edit_plan:
        if not args.source_motion:
            raise ValueError("--edit-plan requires --source-motion")
        edit_plan_path = Path(args.edit_plan).expanduser()
        if edit_plan_path.exists() and not args.append_to_plan:
            raise ValueError("--edit-plan exists; pass --append-to-plan to append")
        plan = append_anchor_edit_to_plan(
            edit_plan_path,
            edit,
            plan_id=args.plan_id or Path(args.edit_plan).expanduser().stem,
            source_motion_path=args.source_motion,
            source_motion_id=args.motion_id,
            source_contact_layer=args.source,
            source_segment_layer=args.source_segments,
        )
        action = "appended" if args.append_to_plan else "wrote"
        print(f"{action} edit plan {args.edit_plan} edits={len(plan.edits)} status={plan.status}")


def _cmd_validate_contact_edit_plan(args: argparse.Namespace) -> None:
    plan = read_contact_edit_plan(args.plan)
    warnings = validate_contact_edit_plan(plan, allow_free=args.allow_free)
    if not args.no_write:
        plan = replace(plan, status="validated")
        write_contact_edit_plan(args.plan, plan)
    print(f"validated contact edit plan {args.plan} edits={len(plan.edits)} status={plan.status}")
    for warning in warnings:
        print(f"warning: {warning}")


def _cmd_generate_lte_augmentation(args: argparse.Namespace) -> None:
    plan = read_contact_edit_plan(args.plan)
    if plan.status not in {"validated", "locked"} and not args.allow_draft:
        raise ValueError("contact edit plan must be validated or locked; pass --allow-draft to override")
    output = apply_contact_edit_plan_to_motion(plan, output_motion_path=args.output_motion, mode=args.mode)
    print(f"generated LTE augmentation {output}")


def _cmd_register_motion_asset(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    record = MotionAssetRecord(
        motion_asset_id=args.motion_asset_id,
        motion_path=str(Path(args.motion).expanduser()),
        source=args.source,
        fps=args.fps,
    )
    out = write_motion_asset(record)
    print(f"registered motion asset {record.motion_asset_id} path={out}")


def _cmd_register_motion_version(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    record = MotionVersionRecord(
        motion_version_id=args.motion_version_id,
        motion_path=str(Path(args.motion).expanduser()),
        kind=args.kind,
        base_motion_id=args.base_motion_id,
        motion_asset_id=args.motion_asset_id,
        parent_motion_version_id=args.parent_motion_version_id,
        contact_layer=args.contact_layer,
        edit_plan_id=args.edit_plan_id,
    )
    out = write_motion_version(record)
    print(f"registered motion version {record.motion_version_id} path={out}")


def _source_segments_for_motion(source: str | None, motion_id: str) -> list:
    if not source:
        return []
    path = LAYERS_ROOT / source / f"{motion_id}.jsonl"
    if not path.exists():
        return []
    default_status = "candidate" if source.startswith("candidates/") else "manual"
    return read_layer(path, default_source=source.split("/", 1)[-1], default_status=default_status)


def _cmd_build_canonical_segmentation(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    motion_path = str(Path(args.motion).expanduser())
    motion_id = args.motion_id or Path(motion_path).stem
    graph = read_contact_graph(LAYERS_ROOT / args.contact_layer, motion_id)
    source_segments = _source_segments_for_motion(args.source, motion_id)
    segments = build_canonical_segments(
        motion_version_id=args.motion_version_id,
        motion_path=motion_path,
        graph=graph,
        source_segments=source_segments,
        cut_source=args.cut_source,
    )
    record, segment_path = write_motion_version_with_canonical_segments(
        motion_version_id=args.motion_version_id,
        motion_path=motion_path,
        contact_layer=args.contact_layer,
        segments=segments,
        base_motion_id=motion_id,
        reset_canonical=args.reset_canonical or args.overwrite,
        reason=args.reason,
        source=args.cut_source,
    )
    print(
        f"wrote canonical segmentation motion_version={record.motion_version_id} "
        f"segments={len(segments)} path={segment_path}"
    )


def _cmd_mark_segment_status(args: argparse.Namespace) -> None:
    updates = []
    if args.status_by_file:
        updates.extend(read_jsonl(Path(args.status_by_file).expanduser()))
    if args.segment_id:
        if not args.status:
            raise ValueError("--segment-id requires --status")
        updates.extend(
            {
                "segment_id": segment_id,
                "status": args.status,
                "reason": args.reason,
                "source": args.source,
            }
            for segment_id in args.segment_id
        )
    if not updates:
        raise ValueError("mark-segment-status requires --segment-id or --status-by-file")
    segments = mark_canonical_segment_statuses(motion_version_id=args.motion_version_id, updates=updates)
    print(f"updated canonical segment status motion_version={args.motion_version_id} updates={len(updates)}")
    print(f"canonical segments={len(segments)}")


def _cmd_canonical_action(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    segments = read_canonical_segments(args.motion_version_id)
    selected = select_segment(
        segments,
        motion_id=args.motion_id,
        segment_id=args.segment_id,
        index=args.index,
    )
    if args.action == "trim":
        if args.start_frame is None or args.end_frame is None:
            raise ValueError("trim requires --start-frame and --end-frame")
        replacements = [trim_segment(selected, start_frame=args.start_frame, end_frame=args.end_frame)]
    elif args.action == "split":
        if args.frame is None:
            raise ValueError("split requires --frame")
        replacements = list(split_segment(selected, frame=args.frame))
    elif args.action == "delete":
        replacements = []
    else:
        raise ValueError(f"unsupported canonical action: {args.action}")
    updated = replace_segment(segments, selected.segment_id, replacements)
    out = replace_canonical_segments(
        args.motion_version_id,
        updated,
        reason=args.reason or f"{args.action} {selected.segment_id}",
        source=args.source,
        kind=args.action,
    )
    print(
        f"{args.action}: motion_version={args.motion_version_id} "
        f"selected={selected.segment_id} replacements={','.join(segment.segment_id for segment in replacements) or '<deleted>'}"
    )
    print(f"updated canonical segmentation {out}")


def _cmd_build_token_catalog(args: argparse.Namespace) -> None:
    segments = read_canonical_segments(args.motion_version_id)
    tokens = build_tokens_from_segments(args.motion_version_id, segments)
    out = write_token_catalog(args.motion_version_id, tokens, args.output)
    try:
        version = read_motion_version(args.motion_version_id)
        metadata = dict(version.metadata)
        metadata["token_catalog_status"] = "current"
        metadata.pop("token_catalog_stale_reason", None)
        updated = replace(version, token_catalog_path=str(out), metadata=metadata)
        write_motion_version(updated)
    except FileNotFoundError:
        print(f"warning: motion version not found for {args.motion_version_id}; token catalog path was not linked")
    print(f"wrote token catalog motion_version={args.motion_version_id} tokens={len(tokens)} path={out}")


def _cmd_summarize(_args: argparse.Namespace) -> None:
    ensure_data_dirs()
    for root in [LAYERS_ROOT / "manual", LAYERS_ROOT / "candidates", LAYERS_ROOT / "accepted", LAYERS_ROOT / "rejected"]:
        files = sorted(root.rglob("*.jsonl"))
        count = 0
        for path in files:
            count += sum(1 for _ in path.open("r", encoding="utf-8"))
        print(f"{root.relative_to(LAYERS_ROOT)}: files={len(files)} segments={count}")


def _cmd_detect_motion(args: argparse.Namespace) -> None:
    paths = detect_omniretarget_paths(args.motion, repo_root=args.repo_root, dataset_root=args.dataset_root)
    print(f"motion_path: {paths.motion_path}")
    print(f"dataset_root: {paths.dataset_root}")
    print(f"terrain_urdf: {paths.terrain_urdf}")
    print(f"terrain_obj: {paths.terrain_obj}")
    print(f"contact_force_npz: {paths.contact_force_npz}")
    print(f"holosoma_motion_path: {paths.holosoma_motion_path}")


def _cmd_view(args: argparse.Namespace) -> None:
    process = launch_viewer(
        args.motion,
        repo_root=args.repo_root,
        layer=args.layer,
        conda_env=args.conda_env,
        timeline_port=args.timeline_port,
        fps=args.fps,
        with_terrain=args.with_terrain,
    )
    print(f"viewer pid={process.pid}")
    print(f"Open Motion Cutter: http://localhost:{args.timeline_port}")
    process.wait()


def _cmd_edit_clip(args: argparse.Namespace) -> None:
    output = clip_motion(args.input, args.output, args.start, args.end)
    print(f"wrote clip {output}")


def _cmd_edit_splice(args: argparse.Namespace) -> None:
    output = splice_motions(args.inputs, args.output)
    print(f"wrote splice {output}")


def _cmd_export_manifest(args: argparse.Namespace) -> None:
    if args.source and args.motion_version_id:
        raise ValueError("export-manifest accepts either --source or --motion-version-id, not both")
    if args.motion_version_id:
        version = read_motion_version(args.motion_version_id)
        segments = read_canonical_segments(args.motion_version_id)
        output = export_motion_version_manifest(args.output, version=version, segments=segments)
    else:
        if not args.source:
            raise ValueError("export-manifest requires --source or --motion-version-id")
        segments = _load_source_segments(args.source)
        output = export_motion_manifest(args.output, segments)
    print(f"wrote manifest {output}")


def _cmd_export_split_npz(args: argparse.Namespace) -> None:
    if args.motion_version_id:
        version = read_motion_version(args.motion_version_id)
        segments = read_canonical_segments(args.motion_version_id)
        if args.status:
            segments = [segment for segment in segments if segment.status == args.status]
        token_by_segment = {}
        if version.token_catalog_path:
            try:
                token_by_segment = {token.segment_id: token.token_id for token in read_token_catalog(args.motion_version_id, version.token_catalog_path)}
            except FileNotFoundError:
                print(f"warning: token catalog not found: {version.token_catalog_path}")
        hardened_segments = []
        for segment in segments:
            metadata = dict(segment.metadata)
            metadata["motion_version_id"] = args.motion_version_id
            token_id = token_by_segment.get(segment.segment_id)
            if token_id:
                metadata["token_id"] = token_id
            hardened_segments.append(
                replace(
                    segment,
                    motion_path=segment.motion_path or segment.clip_npz or version.motion_path,
                    clip_npz=segment.clip_npz or segment.motion_path or version.motion_path,
                    metadata=metadata,
                )
            )
        segments = hardened_segments
        default_output_name = args.motion_version_id if args.status is None else f"{args.motion_version_id}_{args.status}"
    else:
        if not args.source:
            raise ValueError("export-split-npz requires --source or --motion-version-id")
        segments = _load_source_segments(args.source)
        default_output_name = args.source.replace("/", "_")
    if args.motion_id or args.segment_id or args.index is not None:
        segments = filter_segments(
            segments,
            motion_id=args.motion_id,
            segment_ids=set(args.segment_id or []) if args.segment_id else None,
            indices=set(args.index or []) if args.index is not None else None,
        )
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else EXPORTS_ROOT / "split_npz" / default_output_name
    written = export_split_npz(output_dir, segments)
    print(f"wrote {len(written)} split npz files to {output_dir}")


def _cmd_import_lte_catalog(args: argparse.Namespace) -> None:
    motions, segments = import_lte_catalog(args.catalog, layer_name=args.layer_name)
    print(f"imported LTE catalog motions={motions} full_motion_segments={segments} layer=candidates/{args.layer_name}")


def _cmd_curate(args: argparse.Namespace) -> None:
    _warn_legacy_layer_workflow("mark-segment-status")
    segments = _load_source_segments(args.source)
    selected = filter_segments(
        segments,
        motion_id=args.motion_id,
        segment_ids=set(args.segment_id or []) if args.segment_id else None,
        indices=set(args.index or []) if args.index is not None else None,
    )
    out = write_status_layer(args.status, args.layer_name, selected)
    print(f"wrote {len(selected)} {args.status} segments to {out}")


def _cmd_list_layer(args: argparse.Namespace) -> None:
    segments = _load_source_segments(args.source)
    if args.motion_id:
        segments = [segment for segment in segments if segment.motion_id == args.motion_id]
    by_motion = {}
    for segment in segments:
        by_motion.setdefault(segment.motion_id, []).append(segment)
    total = 0
    for motion_id, items in sorted(by_motion.items()):
        print(f"{motion_id}: {len(items)}")
        for index, segment in enumerate(sorted(items, key=lambda s: (s.start_frame, s.end_frame))[: args.limit]):
            print(
                f"  {index:03d} {segment.start_frame:5d}->{segment.end_frame:<5d} "
                f"{segment.segment_id} source={segment.source} status={segment.status}"
            )
        total += len(items)
    print(f"total={total}")


def _cmd_list_contact_layer(args: argparse.Namespace) -> None:
    root = LAYERS_ROOT / args.source
    if not root.exists():
        raise FileNotFoundError(f"contact layer not found: {root}")
    event_files = sorted((root / "events").glob("*.jsonl"))
    if args.motion_id:
        event_files = [path for path in event_files if path.stem == args.motion_id]
    total_events = 0
    total_anchors = 0
    total_patches = 0
    total_transitions = 0
    for event_path in event_files:
        motion_id = event_path.stem
        graph = read_contact_graph(root, motion_id)
        total_events += len(graph.events)
        total_anchors += len(graph.anchors)
        total_patches += len(graph.patches)
        total_transitions += len(graph.transitions)
        print(
            f"{motion_id}: events={len(graph.events)} anchors={len(graph.anchors)} "
            f"patches={len(graph.patches)} transitions={len(graph.transitions)}"
        )
        for anchor in graph.anchors[: args.limit]:
            print(
                f"  anchor {anchor.start_frame:5d}->{anchor.end_frame:<5d} "
                f"{anchor.anchor_id} body={anchor.body} role={anchor.role}"
            )
        for patch in graph.patches[: args.limit]:
            print(
                f"  patch  {patch.start_frame:5d}->{patch.end_frame:<5d} "
                f"{patch.patch_id} body={patch.body} anchor={patch.anchor_id}"
            )
        for transition in graph.transitions[: args.limit]:
            print(
                f"  transition {transition.start_frame:5d}->{transition.end_frame:<5d} "
                f"{transition.transition_id} active={transition.active_body} "
                f"support={','.join(transition.support_bodies)}"
            )
    print(
        f"total_events={total_events} total_anchors={total_anchors} "
        f"total_patches={total_patches} total_transitions={total_transitions}"
    )


def _cmd_workbench_action(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    segments = load_workbench_segments(args.source)
    selected = select_segment(
        segments,
        motion_id=args.motion_id,
        segment_id=args.segment_id,
        index=args.index,
    )

    if args.action == "trim":
        if args.start_frame is None or args.end_frame is None:
            raise ValueError("trim requires --start-frame and --end-frame")
        replacements = [trim_segment(selected, start_frame=args.start_frame, end_frame=args.end_frame)]
        destination = args.output_source or "manual/workbench_tmp"
        output_segments = replace_segment(segments, selected.segment_id, replacements)
    elif args.action == "split":
        if args.frame is None:
            raise ValueError("split requires --frame")
        replacements = list(split_segment(selected, frame=args.frame))
        destination = args.output_source or "manual/workbench_tmp"
        output_segments = replace_segment(segments, selected.segment_id, replacements)
    elif args.action in {"accept", "reject"}:
        _warn_legacy_layer_workflow("mark-segment-status")
        status = "accepted" if args.action == "accept" else "rejected"
        replacements = [curate_segment(selected, status=status)]  # type: ignore[arg-type]
        destination = args.output_source or f"{status}/{args.layer_name}"
        output_segments = replacements
    else:
        raise ValueError(f"unsupported workbench action: {args.action}")

    print(
        f"{args.action}: selected={selected.segment_id} "
        f"replacements={','.join(segment.segment_id for segment in replacements)} "
        f"destination={destination}"
    )
    if args.dry_run:
        print("dry-run: no files written")
        return
    if args.action in {"accept", "reject"}:
        out = upsert_workbench_segments(destination, output_segments)
    else:
        out = write_workbench_segments(destination, output_segments)
    print(f"wrote {len(output_segments)} workbench segments to {out}")


def _cmd_cutter(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    motion_id = args.motion_id or Path(args.motion).expanduser().stem
    if args.update_canonical:
        if not args.motion_version_id:
            raise ValueError("--update-canonical requires --motion-version-id")
        if args.destination:
            raise ValueError("--destination is a legacy layer output and cannot be used with --update-canonical")
        version = read_motion_version(args.motion_version_id)
        contact_graph = None
        if version.contact_layer:
            try:
                contact_graph = read_contact_graph(LAYERS_ROOT / version.contact_layer, motion_id)
            except FileNotFoundError:
                print(f"warning: contact graph not found for {version.contact_layer}; canonical cutter edits will not be rebound")
        segments = read_canonical_segments(args.motion_version_id)
        session_dir = WORKBENCH_ROOT / "sessions" / args.session_name
        segment_path = session_dir / f"{motion_id}.segments.jsonl"
        write_jsonl(segment_path, (segment.to_cutter_json() for segment in segments if segment.motion_id == motion_id))
        print(f"cutter session file: {segment_path}")
        process = launch_viewer(
            args.motion,
            repo_root=args.repo_root,
            layer=None,
            segment_path=segment_path,
            conda_env=args.conda_env,
            timeline_port=args.timeline_port,
            fps=args.fps,
            with_terrain=args.with_terrain,
        )
        print(f"viewer pid={process.pid}")
        print(f"Open Motion Cutter: http://localhost:{args.timeline_port}")
        process.wait()
        edited_segments = []
        for item in read_jsonl(segment_path):
            parsed = segment_from_dict(item, default_source="viser_cutter", default_status="manual")
            metadata = dict(parsed.metadata)
            metadata["motion_version_id"] = args.motion_version_id
            metadata["cut_source"] = "cutter_refined"
            edits = list(metadata.get("motion_edit_edits") or [])
            edits.append({"kind": "import_from_cutter", "source": "viser_cutter", "params": {"motion_version_id": args.motion_version_id}})
            metadata["motion_edit_edits"] = edits
            updated = replace(
                parsed,
                source="viser_cutter",
                status="manual",
                motion_path=parsed.motion_path or version.motion_path or args.motion,
                clip_npz=parsed.clip_npz or version.motion_path or args.motion,
                metadata=metadata,
            )
            if contact_graph is not None:
                updated = bind_segment_to_contact_graph(updated, contact_graph)
                rebound_meta = dict(updated.metadata)
                rebound_meta["motion_version_id"] = args.motion_version_id
                rebound_meta["cut_source"] = "cutter_refined"
                rebound_meta["motion_edit_edits"] = edits
                transition = rebound_meta.get("contact_transition")
                if isinstance(transition, dict) and transition.get("transition_id"):
                    rebound_meta["parent_transition_id"] = transition["transition_id"]
                updated = replace(updated, metadata=rebound_meta)
            edited_segments.append(updated)
        out = replace_canonical_segments(
            args.motion_version_id,
            edited_segments,
            reason=f"cutter session {args.session_name}",
            source="viser_cutter",
            kind="cutter_refine",
        )
        print(f"updated canonical segmentation from cutter {out}")
        return
    if not args.source:
        raise ValueError("cutter requires --source unless --update-canonical is used")
    session = export_cutter_session_file(
        motion_id=motion_id,
        source_layer=args.source,
        session_name=args.session_name,
        destination_layer=args.destination,
        motion_path=args.motion,
        viewer_port=args.timeline_port,
    )
    print(f"cutter session file: {session.segment_path}")
    process = launch_viewer(
        args.motion,
        repo_root=args.repo_root,
        layer=None,
        segment_path=session.segment_path,
        conda_env=args.conda_env,
        timeline_port=args.timeline_port,
        fps=args.fps,
        with_terrain=args.with_terrain,
    )
    print(f"viewer pid={process.pid}")
    print(f"Open Motion Cutter: http://localhost:{args.timeline_port}")
    process.wait()
    out = sync_cutter_session_file(
        session.segment_path,
        source_layer=args.source,
        session_name=args.session_name,
        destination_layer=args.destination,
    )
    print(f"synced cutter session to {out}")


def _cmd_surface_editor(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    print("warning: surface-editor is a debug/internal entry; use contact-editor for the main curation workflow")
    surface_catalog = args.surface_catalog
    terrain_urdf_arg = getattr(args, "terrain_urdf", None)
    if surface_catalog is None and (args.with_terrain or terrain_urdf_arg):
        terrain_urdf = Path(terrain_urdf_arg).expanduser() if terrain_urdf_arg else None
        if terrain_urdf is None:
            paths = detect_omniretarget_paths(args.motion, repo_root=args.repo_root)
            terrain_urdf = paths.terrain_urdf
        if terrain_urdf is None:
            raise ValueError("--with-terrain could not resolve a terrain URDF; pass --surface-catalog or --terrain-urdf")
        surface_catalog = str(
            _write_urdf_surface_catalog(
                motion_id=args.motion_id,
                terrain_urdf=terrain_urdf,
                output=None,
                include_side_surfaces=getattr(args, "include_side_surfaces", False),
                include_ground=not getattr(args, "no_ground", False),
                ground_z=getattr(args, "ground_z", 0.0),
                ground_half_extent=getattr(args, "ground_half_extent", 10.0),
            )
        )
        print(f"generated terrain surface catalog from URDF: {surface_catalog}")
    _launch_surface_editor_for_args(args, contact_layer=args.contact_layer, surface_catalog=surface_catalog)


def _cmd_surface_editor_move_anchor(args: argparse.Namespace) -> None:
    session = read_surface_editor_session(args.session)
    moved_graph, edit = move_surface_editor_anchor(
        session,
        anchor_id=args.anchor_id,
        tangent_delta=args.tangent_delta,
        requested_world_position=args.requested_world_position,
        mode=args.mode,
    )
    print(
        f"moved surface anchor {args.anchor_id} motion={session.motion_id} "
        f"delta_world={edit.delta_world} tangent_delta={edit.tangent_delta}"
    )
    print(f"updated overlay {session.overlay_path}")
    if args.save:
        out = save_surface_editor_session(session, layers_root=LAYERS_ROOT)
        print(f"saved surface editor session output_contact_layer={out}")


def _cmd_surface_editor_sync(args: argparse.Namespace) -> None:
    session = read_surface_editor_session(args.session)
    count, out = sync_surface_editor_requests(session, save=args.save, layers_root=LAYERS_ROOT)
    print(f"synced surface editor requests session={args.session} applied={count}")
    print(f"updated overlay {session.overlay_path}")
    print(f"pending edits {session.pending_edits_path}")
    if args.save:
        print(f"saved surface editor session output_contact_layer={out}")


def _cmd_workbench(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    session = WorkbenchSession(
        source=args.source,
        motion_path=args.motion,
        motion_id=args.motion_id,
        selected_segment_id=args.segment_id,
        selected_index=args.index,
        current_frame=args.current_frame,
        output_source=args.output_source,
        layer_name=args.layer_name,
        dry_run=args.dry_run,
    )
    print(f"source={args.source} motion_id={session.selected().motion_id} selected={session.selected().segment_id}")
    if args.once:
        print(session.state())
        return
    server = make_workbench_server(session, host=args.host, port=args.port)
    print(f"workbench api: http://{args.host}:{args.port}/api/state")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="motion-edit")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.set_defaults(func=_cmd_init)

    p = sub.add_parser("import-force-proto")
    p.add_argument("--motion-dir", required=True)
    p.add_argument("--pattern", default="*.npz")
    p.add_argument("--layer-name", default="force_contact")
    p.add_argument("--source", default="force_contact")
    p.set_defaults(func=_cmd_import_force_proto)

    p = sub.add_parser("import-manual-cuts")
    p.add_argument("--segments-dir", required=True)
    p.add_argument("--layer-name", default="default")
    p.set_defaults(func=_cmd_import_manual_cuts)

    p = sub.add_parser("export-cutter-segments")
    p.add_argument("--source", required=True, help="Layer path relative to data/layers, e.g. candidates/force_contact")
    p.add_argument("--output-dir", default=None)
    p.add_argument("--install-to", default=None)
    p.set_defaults(func=_cmd_export_cutter_segments)

    p = sub.add_parser("export-contact-overlay")
    p.add_argument("--source", required=True, help="Contact layer path relative to data/layers, e.g. contact/force_contact")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_export_contact_overlay)

    p = sub.add_parser("export-surface-binding-report")
    p.add_argument("--contact-layer", required=True, help="Contact layer path relative to data/layers")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_export_surface_binding_report)

    p = sub.add_parser("export-surface-binding-overlay")
    p.add_argument("--contact-layer", required=True, help="Contact layer path relative to data/layers")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_export_surface_binding_overlay)

    p = sub.add_parser("summarize-surface-bindings")
    p.add_argument("--contact-layer", required=True, help="Contact layer path relative to data/layers")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=_cmd_summarize_surface_bindings)

    p = sub.add_parser("bind-contact-surfaces")
    p.add_argument("--contact-layer", default=None, help="Contact layer path relative to data/layers, e.g. contact/force_contact")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--terrain-urdf", default=None)
    p.add_argument("--include-side-surfaces", action="store_true")
    p.add_argument("--no-ground", action="store_true")
    p.add_argument("--ground-z", type=float, default=0.0)
    p.add_argument("--ground-half-extent", type=float, default=10.0)
    p.add_argument("--output-contact-layer", required=True)
    p.add_argument("--max-distance", type=float, default=0.05)
    p.add_argument("--mode", choices=("reject", "clamp"), default="reject")
    p.add_argument("--motion-version-id", default=None)
    p.add_argument("--update-motion-version", action="store_true")
    p.add_argument("--rebind-canonical-segments", action="store_true")
    p.set_defaults(func=_cmd_bind_contact_surfaces)

    p = sub.add_parser("refine-contact-anchor-positions")
    p.add_argument("--contact-layer", required=True, help="Contact layer path relative to data/layers")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--motion", required=True, help="Motion npz containing raw_contact_* arrays")
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--output-contact-layer", required=True)
    p.add_argument("--max-part-distance", type=float, default=0.25)
    p.add_argument("--max-surface-distance", type=float, default=0.05)
    p.set_defaults(func=_cmd_refine_contact_anchor_positions)

    p = sub.add_parser("merge-contact-anchors")
    p.add_argument("--contact-layer", required=True, help="Contact layer path relative to data/layers")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--output-contact-layer", required=True)
    p.add_argument("--max-gap", type=int, default=3)
    p.add_argument("--max-distance", type=float, default=0.06)
    p.add_argument("--merge-class", action="append", choices=("top", "ground", "edge_candidate", "outside_known_surfaces", "raw_missing"))
    p.add_argument("--allow-cross-class", action="store_true")
    p.add_argument("--source", default="merge_contact_anchors")
    p.set_defaults(func=_cmd_merge_contact_anchors)

    p = sub.add_parser("filter-contact-anchors")
    p.add_argument("--contact-layer", required=True, help="Contact layer path relative to data/layers")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--output-contact-layer", required=True)
    p.add_argument("--strategy", choices=("short_raw_missing",), default="short_raw_missing")
    p.add_argument("--max-duration", type=int, default=5)
    p.add_argument("--max-gap", type=int, default=2)
    p.add_argument("--max-distance", type=float, default=0.08)
    p.add_argument("--neighbor-class", action="append", choices=("top", "ground"))
    p.add_argument("--drop-class", action="append", choices=("raw_missing", "edge_candidate", "outside_known_surfaces"))
    p.add_argument("--source", default="filter_short_raw_missing")
    p.set_defaults(func=_cmd_filter_contact_anchors)

    p = sub.add_parser("create-box-surface-catalog")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--box", action="append", required=True, help="object_id:cx,cy,cz:sx,sy,sz")
    p.add_argument("--top-only", action="store_true")
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_create_box_surface_catalog)

    p = sub.add_parser("create-urdf-surface-catalog")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--terrain-urdf", required=True)
    p.add_argument("--include-side-surfaces", action="store_true")
    p.add_argument("--no-ground", action="store_true")
    p.add_argument("--ground-z", type=float, default=0.0)
    p.add_argument("--ground-half-extent", type=float, default=10.0)
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_create_urdf_surface_catalog)

    p = sub.add_parser("move-contact-anchor")
    p.add_argument("--source", required=True, help="Contact layer path relative to data/layers, e.g. contact/force_contact")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--anchor-id", required=True)
    p.add_argument("--delta-world", nargs=3, type=float, default=None)
    p.add_argument("--tangent-delta", nargs=2, type=float, default=None)
    p.add_argument("--new-world-position", nargs=3, type=float, default=None)
    p.add_argument("--mode", choices=("reject", "clamp"), default="reject")
    p.add_argument("--allow-free-3d", action="store_true")
    p.add_argument("--output-source", default=None, help="Destination contact layer path, default <source>_edited")
    p.add_argument("--edit-source", default="manual")
    p.add_argument("--edit-plan", default=None)
    p.add_argument("--append-to-plan", action="store_true")
    p.add_argument("--plan-id", default=None)
    p.add_argument("--source-motion", default=None)
    p.add_argument("--source-segments", default=None)
    p.set_defaults(func=_cmd_move_contact_anchor)

    p = sub.add_parser("validate-contact-edit-plan")
    p.add_argument("--plan", required=True)
    p.add_argument("--allow-free", action="store_true")
    p.add_argument("--no-write", action="store_true")
    p.set_defaults(func=_cmd_validate_contact_edit_plan)

    p = sub.add_parser("generate-lte-augmentation")
    p.add_argument("--plan", required=True)
    p.add_argument("--output-motion", required=True)
    p.add_argument("--allow-draft", action="store_true")
    p.add_argument("--mode", default="stub")
    p.set_defaults(func=_cmd_generate_lte_augmentation)

    p = sub.add_parser("register-motion-asset")
    p.add_argument("--motion-asset-id", required=True)
    p.add_argument("--motion", required=True)
    p.add_argument("--fps", type=float, default=None)
    p.add_argument("--source", default="local")
    p.set_defaults(func=_cmd_register_motion_asset)

    p = sub.add_parser("register-motion-version")
    p.add_argument("--motion-version-id", required=True)
    p.add_argument("--motion", required=True)
    p.add_argument("--kind", choices=("raw", "augmented"), default="raw")
    p.add_argument("--base-motion-id", default=None)
    p.add_argument("--motion-asset-id", default=None)
    p.add_argument("--parent-motion-version-id", default=None)
    p.add_argument("--edit-plan-id", default=None)
    p.add_argument("--contact-layer", default=None)
    p.set_defaults(func=_cmd_register_motion_version)

    p = sub.add_parser("build-canonical-segmentation")
    p.add_argument("--motion-version-id", required=True)
    p.add_argument("--motion", required=True)
    p.add_argument("--motion-id", default=None)
    p.add_argument("--contact-layer", required=True)
    p.add_argument("--source", default=None)
    p.add_argument("--cut-source", default="contact_auto")
    p.add_argument("--reset-canonical", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--reason", default=None)
    p.set_defaults(func=_cmd_build_canonical_segmentation)

    p = sub.add_parser("migrate-layer-to-canonical")
    p.add_argument("--motion-version-id", required=True)
    p.add_argument("--motion", required=True)
    p.add_argument("--motion-id", default=None)
    p.add_argument("--contact-layer", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--cut-source", default="migrated")
    p.add_argument("--reset-canonical", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--reason", default=None)
    p.set_defaults(func=_cmd_build_canonical_segmentation)

    p = sub.add_parser("mark-segment-status")
    p.add_argument("--motion-version-id", required=True)
    p.add_argument("--segment-id", action="append", default=None)
    p.add_argument("--status", choices=("candidate", "accepted", "rejected", "manual"), default=None)
    p.add_argument("--reason", default=None)
    p.add_argument("--source", default="mark_segment_status")
    p.add_argument("--status-by-file", default=None)
    p.set_defaults(func=_cmd_mark_segment_status)

    p = sub.add_parser("canonical-action")
    p.add_argument("--motion-version-id", required=True)
    p.add_argument("--segment-id", default=None)
    p.add_argument("--motion-id", default=None)
    p.add_argument("--index", type=int, default=None)
    p.add_argument("--action", required=True, choices=("trim", "split", "delete"))
    p.add_argument("--start-frame", type=int, default=None)
    p.add_argument("--end-frame", type=int, default=None)
    p.add_argument("--frame", type=int, default=None)
    p.add_argument("--reason", default=None)
    p.add_argument("--source", default="canonical_action")
    p.set_defaults(func=_cmd_canonical_action)

    p = sub.add_parser("build-token-catalog")
    p.add_argument("--motion-version-id", required=True)
    p.add_argument("--output", default=None)
    p.set_defaults(func=_cmd_build_token_catalog)

    p = sub.add_parser("export-manifest")
    p.add_argument("--source", default=None, help="Layer path relative to data/layers")
    p.add_argument("--motion-version-id", default=None)
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_export_manifest)

    p = sub.add_parser("export-split-npz")
    p.add_argument("--source", default=None, help="Layer path relative to data/layers")
    p.add_argument("--motion-version-id", default=None)
    p.add_argument("--status", choices=("candidate", "accepted", "rejected", "manual"), default=None)
    p.add_argument("--output-dir", default=None)
    p.add_argument("--motion-id", default=None)
    p.add_argument("--segment-id", action="append", default=None)
    p.add_argument("--index", action="append", type=int, default=None)
    p.set_defaults(func=_cmd_export_split_npz)

    p = sub.add_parser("import-lte-catalog")
    p.add_argument("--catalog", required=True)
    p.add_argument("--layer-name", default="lte")
    p.set_defaults(func=_cmd_import_lte_catalog)

    p = sub.add_parser("accept")
    p.add_argument("--source", required=True)
    p.add_argument("--layer-name", default="default")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--segment-id", action="append", default=None)
    p.add_argument("--index", action="append", type=int, default=None)
    p.set_defaults(func=lambda args: setattr(args, "status", "accepted") or _cmd_curate(args))

    p = sub.add_parser("reject")
    p.add_argument("--source", required=True)
    p.add_argument("--layer-name", default="default")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--segment-id", action="append", default=None)
    p.add_argument("--index", action="append", type=int, default=None)
    p.set_defaults(func=lambda args: setattr(args, "status", "rejected") or _cmd_curate(args))

    p = sub.add_parser("list-layer")
    p.add_argument("--source", required=True)
    p.add_argument("--motion-id", default=None)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_cmd_list_layer)

    p = sub.add_parser("list-contact-layer")
    p.add_argument("--source", required=True, help="Contact layer path relative to data/layers, e.g. contact/force_contact")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=_cmd_list_contact_layer)

    p = sub.add_parser("workbench-action")
    p.add_argument("--source", required=True, help="Layer path relative to data/layers")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--segment-id", default=None)
    p.add_argument("--index", type=int, default=None)
    p.add_argument("--action", required=True, choices=["trim", "split", "accept", "reject"])
    p.add_argument("--start-frame", type=int, default=None)
    p.add_argument("--end-frame", type=int, default=None)
    p.add_argument("--frame", type=int, default=None)
    p.add_argument("--output-source", default=None, help="Destination layer path relative to data/layers")
    p.add_argument("--layer-name", default="workbench_tmp", help="Layer name for accept/reject defaults")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=_cmd_workbench_action)

    p = sub.add_parser("cutter")
    p.add_argument("motion")
    p.add_argument("--source", default=None, help="Source layer path relative to data/layers")
    p.add_argument("--session-name", required=True)
    p.add_argument("--destination", default=None, help="Destination layer path, default manual/<session-name>")
    p.add_argument("--motion-version-id", default=None)
    p.add_argument("--update-canonical", action="store_true")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--repo-root", default=None)
    p.add_argument("--conda-env", default="hsretargeting")
    p.add_argument("--timeline-port", type=int, default=8094)
    p.add_argument("--fps", type=int, default=50)
    p.add_argument("--with-terrain", action="store_true")
    p.set_defaults(func=_cmd_cutter)

    p = sub.add_parser("contact-editor")
    p.add_argument("motion")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--source-contact-layer", required=True)
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--terrain-urdf", default=None)
    p.add_argument("--include-side-surfaces", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--no-ground", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--ground-z", type=float, default=0.0)
    p.add_argument("--ground-half-extent", type=float, default=10.0)
    p.add_argument("--output-prefix", default=None, help="Contact layer prefix for generated *_merged, *_editor_visible, *_editor_ready layers")
    p.add_argument("--session-name", required=True)
    p.add_argument("--edit-plan", default=None)
    p.add_argument("--output-contact-layer", default=None)
    p.add_argument("--repo-root", default=None)
    p.add_argument("--conda-env", default="hsretargeting")
    p.add_argument("--timeline-port", type=int, default=8094)
    p.add_argument("--fps", type=int, default=50)
    p.add_argument("--with-terrain", action="store_true")
    p.add_argument("--save-on-exit", action="store_true")
    p.add_argument("--edit-mode", choices=("direct", "request"), default="direct")
    p.add_argument("--step-size", type=float, default=0.02)
    p.add_argument("--default-mode", choices=("reject", "clamp"), default="reject")
    p.add_argument("--show-only", choices=("all", "bound", "edited", "clamped", "suspicious", "failed", "unbound"), default="all")
    p.add_argument("--select-anchor", default=None)
    p.add_argument("--external-viewer", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--merge-max-gap", type=int, default=3)
    p.add_argument("--merge-max-distance", type=float, default=0.06)
    p.add_argument("--max-surface-distance", type=float, default=0.08)
    p.add_argument("--bind-mode", choices=("reject", "clamp"), default="reject")
    p.set_defaults(func=_cmd_contact_editor)

    p = sub.add_parser("surface-editor")
    p.add_argument("motion")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--contact-layer", required=True)
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--terrain-urdf", default=None)
    p.add_argument("--include-side-surfaces", action="store_true")
    p.add_argument("--no-ground", action="store_true")
    p.add_argument("--ground-z", type=float, default=0.0)
    p.add_argument("--ground-half-extent", type=float, default=10.0)
    p.add_argument("--session-name", required=True)
    p.add_argument("--edit-plan", default=None)
    p.add_argument("--output-contact-layer", default=None)
    p.add_argument("--repo-root", default=None)
    p.add_argument("--conda-env", default="hsretargeting")
    p.add_argument("--timeline-port", type=int, default=8094)
    p.add_argument("--fps", type=int, default=50)
    p.add_argument("--with-terrain", action="store_true")
    p.add_argument("--save-on-exit", action="store_true")
    p.add_argument("--edit-mode", choices=("direct", "request"), default="direct")
    p.add_argument("--step-size", type=float, default=0.02)
    p.add_argument("--default-mode", choices=("reject", "clamp"), default="reject")
    p.add_argument("--show-only", choices=("all", "bound", "edited", "clamped", "suspicious", "failed", "unbound"), default="all")
    p.add_argument("--select-anchor", default=None)
    p.add_argument("--external-viewer", action="store_true", help="Use the legacy external Holosoma viewer instead of the local surface overlay adapter")
    p.set_defaults(func=_cmd_surface_editor)

    p = sub.add_parser("surface-editor-sync")
    p.add_argument("--session", required=True, help="Path to surface editor session.json")
    p.add_argument("--save", action="store_true")
    p.set_defaults(func=_cmd_surface_editor_sync)

    p = sub.add_parser("surface-editor-move-anchor")
    p.add_argument("--session", required=True, help="Path to surface editor session.json")
    p.add_argument("--anchor-id", required=True)
    p.add_argument("--tangent-delta", nargs=2, type=float, default=None)
    p.add_argument("--requested-world-position", nargs=3, type=float, default=None)
    p.add_argument("--mode", choices=("reject", "clamp"), default="reject")
    p.add_argument("--save", action="store_true")
    p.set_defaults(func=_cmd_surface_editor_move_anchor)

    p = sub.add_parser("workbench")
    p.add_argument("motion", nargs="?", default=None, help="Optional .npz motion path for state metadata")
    p.add_argument("--source", required=True, help="Layer path relative to data/layers")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--segment-id", default=None)
    p.add_argument("--index", type=int, default=0)
    p.add_argument("--current-frame", type=int, default=-1)
    p.add_argument("--output-source", default="manual/workbench_tmp")
    p.add_argument("--layer-name", default="workbench_tmp")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8095)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--once", action="store_true", help="Build session, print state, and exit without serving")
    p.set_defaults(func=_cmd_workbench)

    p = sub.add_parser("detect-motion")
    p.add_argument("motion")
    p.add_argument("--repo-root", default=None)
    p.add_argument("--dataset-root", default=None)
    p.set_defaults(func=_cmd_detect_motion)

    p = sub.add_parser("view")
    p.add_argument("motion")
    p.add_argument("--repo-root", default=None)
    p.add_argument("--layer", default=None, help="Layer path relative to data/layers, e.g. candidates/force_contact")
    p.add_argument("--conda-env", default="hsretargeting")
    p.add_argument("--timeline-port", type=int, default=8094)
    p.add_argument("--fps", type=int, default=50)
    p.add_argument("--with-terrain", action="store_true")
    p.set_defaults(func=_cmd_view)

    p = sub.add_parser("edit-clip")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--end", type=int, required=True)
    p.set_defaults(func=_cmd_edit_clip)

    p = sub.add_parser("edit-splice")
    p.add_argument("--output", required=True)
    p.add_argument("inputs", nargs="+")
    p.set_defaults(func=_cmd_edit_splice)

    p = sub.add_parser("summarize")
    p.set_defaults(func=_cmd_summarize)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
