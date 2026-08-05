from __future__ import annotations

import argparse
import shutil
from dataclasses import replace
from pathlib import Path

from .augmentation import AugmentationRunConfig, run_augmentation_queue
from .adapters.omniretarget import detect_omniretarget_paths
from .adapters.asset_manifest import load_asset_manifest
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
    split_foot_contact_anchors,
    validate_contact_edit_plan,
    write_contact_edit_plan,
    write_contact_layer,
    write_contact_surfaces,
)
from .contact.graph import ContactGraph
from .contact.jitter import DEFAULT_JITTER_BODIES, generate_contact_jitter_plans
from .generation import apply_contact_aware_edit_plan_to_motion, apply_contact_edit_plan_to_motion
from .contact.layers import read_contact_graph
from .contact.patches import patches_from_anchors
from .contact.surface_catalog import box_surfaces, parse_box_descriptor, surfaces_from_obj_mesh_faces, surfaces_from_urdf_meshes
from .storage.canonical import (
    build_canonical_segments,
    mark_canonical_segment_statuses,
    write_motion_version_with_canonical_segments,
)
from .storage.io import (
    list_motion_assets,
    read_canonical_segments,
    read_motion_asset,
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
from .workbench.contact_editor_setup import (
    ContactEditorConfig,
    prepare_contact_editor_session as prepare_contact_editor_workbench_session,
)


def _cmd_init(_args: argparse.Namespace) -> None:
    ensure_data_dirs()
    print(f"initialized {LAYERS_ROOT.parents[0]}")


def _cmd_import_force_proto(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    motion_dir = Path(args.motion_dir).expanduser().resolve()
    out_dir = layer_dir("candidate", args.layer_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    registered_by_path = {}
    if getattr(args, "use_registered_motion_ids", False) or getattr(args, "update_motions", False):
        registered_by_path = {
            str(Path(record.motion_path).expanduser().resolve()): record
            for record in list_motion_assets()
        }
    motion_paths = sorted(motion_dir.glob(args.pattern))
    explicit_motion_id = getattr(args, "motion_id", None)
    if explicit_motion_id and len(motion_paths) != 1:
        raise ValueError("--motion-id requires --pattern to match exactly one motion")
    total = 0
    for motion_path in motion_paths:
        registered = registered_by_path.get(str(motion_path.resolve()))
        motion_id = explicit_motion_id or (
            registered.motion_id
            if registered is not None and registered.motion_id
            else None
        )
        segments = segments_from_masked_motion(motion_path, source=args.source, status="candidate", motion_id=motion_id)
        write_layer(out_dir / f"{motion_path.stem}.jsonl", segments)
        graph = contact_graph_from_masked_motion(motion_path, source=args.source, motion_id=motion_id)
        surfaces = None
        surface_catalog = getattr(args, "surface_catalog", None)
        max_surface_distance = float(
            getattr(args, "max_surface_distance", 0.08)
        )
        if surface_catalog:
            surfaces = read_contact_surfaces(Path(surface_catalog).expanduser())
            graph = refine_contact_graph_anchor_positions_from_raw_contacts(
                graph,
                motion_path,
                surfaces=surfaces,
                max_surface_distance=max_surface_distance,
            )
            graph = split_foot_contact_anchors(graph)
            graph, _filter_events = filter_short_raw_missing_anchors(
                graph,
                drop_classes={
                    "raw_missing",
                    "edge_candidate",
                    "outside_known_surfaces",
                },
                source="import_force_proto_surface_filter",
            )
            bound_anchors = bind_anchors_to_surfaces(
                graph.anchors,
                surfaces,
                max_distance=max_surface_distance,
                mode="reject",
            )
            graph = ContactGraph(
                motion_id=graph.motion_id,
                events=graph.events,
                anchors=bound_anchors,
                patches=patches_from_anchors(bound_anchors),
                transitions=graph.transitions,
            )
            counts = _surface_binding_counts(graph)
            if counts["unbound_count"] or counts["failed_count"]:
                raise ValueError(
                    "surface-aware force proto import requires every retained "
                    "contact anchor to be bound: "
                    f"anchors={counts['anchor_count']} "
                    f"bound={counts['bound_count']} "
                    f"unbound={counts['unbound_count']} "
                    f"failed={counts['failed_count']}"
                )
        write_contact_layer(LAYERS_ROOT / "contact" / args.layer_name, graph)
        if surfaces is not None:
            write_contact_surfaces(
                LAYERS_ROOT
                / "contact"
                / args.layer_name
                / "surfaces"
                / f"{graph.motion_id}.jsonl",
                surfaces,
            )
        if registered is not None and getattr(args, "update_motions", False):
            derived = dict(registered.derived or {})
            derived["contact_layer"] = f"contact/{args.layer_name}"
            write_motion_asset(replace(registered, contact_layer=f"contact/{args.layer_name}", derived=derived))
        total += len(segments)
    print(f"wrote {total} candidate segments to {out_dir}; contact layer={LAYERS_ROOT / 'contact' / args.layer_name}")


def _cmd_import_asset_manifest(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    selected = set(args.motion_id or [])
    assets = load_asset_manifest(args.manifest, verify_hashes=args.verify_hashes)
    if selected:
        assets = [asset for asset in assets if asset.motion_id in selected or str(asset.motion_index) in selected]
    candidate_root = layer_dir("candidate", args.layer_name)
    candidate_root.mkdir(parents=True, exist_ok=True)
    contact_layer = f"contact/{args.layer_name}"
    segment_count = 0
    for asset in assets:
        surfaces = surfaces_from_obj_mesh_faces(
            motion_id=asset.motion_id,
            obj_path=asset.terrain_mesh_path,
            include_sides=False,
            include_ground=True,
        )
        surface_path = SURFACES_ROOT / f"{asset.motion_id}_terrain_surfaces.jsonl"
        write_contact_surfaces(surface_path, surfaces)
        segments = segments_from_masked_motion(
            asset.force_motion_path,
            source=args.layer_name,
            status="candidate",
            motion_id=asset.motion_id,
        )
        write_layer(candidate_root / f"{asset.motion_id}.jsonl", segments)
        graph = contact_graph_from_masked_motion(
            asset.force_motion_path,
            source=args.layer_name,
            motion_id=asset.motion_id,
        )
        write_contact_layer(LAYERS_ROOT / contact_layer, graph)
        record = MotionAssetRecord(
            motion_asset_id=asset.motion_asset_id,
            motion_path=str(asset.reference_motion_path),
            source="newton_asset_manifest",
            fps=args.fps,
            motion_id=asset.motion_id,
            terrain_id=str(asset.motion_index),
            terrain_mesh=str(asset.terrain_mesh_path),
            surface_catalog_path=str(surface_path),
            source_motion_path=str(asset.source_motion_path),
            contact_force_npz=str(asset.force_motion_path),
            source_manifest=str(asset.manifest_path),
            asset_hashes={
                "reference_motion_sha256": asset.reference_motion_sha256,
                "motion_sha256": asset.motion_sha256,
                "source_sha256": asset.source_sha256,
                "terrain_sha256": asset.terrain_sha256,
                "contact_solver_sha256": asset.contact_solver_sha256,
            },
            contact_layer=contact_layer,
            raw_contact={"available": True, "source": "newton_8part"},
            metadata={
                "manifest_motion_index": asset.motion_index,
                "kinematic_reference": "clean_reference_motion_file",
                "contact_force_source": "newton_rollout_motion_file",
                "contact_force_provenance": asset.provenance,
            },
        )
        write_motion_asset(record)
        segment_count += len(segments)
    print(
        f"imported {len(assets)} manifest assets, {segment_count} candidate segments; "
        f"contact layer={LAYERS_ROOT / contact_layer}"
    )


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
        terrain_mesh=getattr(args, "terrain_mesh", None),
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
    graph = read_contact_graph(LAYERS_ROOT / source_layer, args.motion_id)
    try:
        graph = refine_contact_graph_anchor_positions_from_raw_contacts(
            graph,
            args.motion,
            surfaces=surfaces,
            max_surface_distance=args.max_surface_distance,
        )
    except Exception as exc:
        message = str(exc)
        if "missing raw contact fields" not in message and "Failed to interpret file" not in message:
            raise
    graph = split_foot_contact_anchors(graph)
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


def _apply_motion_asset_defaults_to_contact_editor_args(args: argparse.Namespace) -> bool:
    motion_key = getattr(args, "motion_asset_id", None) or getattr(args, "motion_id", None)
    if not motion_key:
        return False
    try:
        record = read_motion_asset(motion_key)
    except FileNotFoundError:
        return False
    args.motion = args.motion or record.motion_path
    args.motion_id = args.motion_id or record.motion_id or record.motion_asset_id
    args.terrain_urdf = args.terrain_urdf or record.terrain_urdf
    args.terrain_mesh = getattr(args, "terrain_mesh", None) or record.terrain_mesh
    args.surface_catalog = args.surface_catalog or record.surface_catalog_path
    derived = record.derived or {}
    args.source_contact_layer = args.source_contact_layer or derived.get("bound_contact_layer") or derived.get("contact_layer")
    args.edit_plan = args.edit_plan or derived.get("edit_plan_path")
    args.output_contact_layer = args.output_contact_layer or derived.get("output_contact_layer")
    if not args.output_prefix:
        args.output_prefix = f"contact/{args.session_name}"
    if (record.terrain_urdf or record.terrain_mesh or record.surface_catalog_path) and not args.with_terrain:
        args.with_terrain = True
    if record.fps and args.fps == 50:
        args.fps = int(record.fps)
    return True


def _cmd_contact_editor(args: argparse.Namespace) -> None:
    from .web import run_contact_editor

    ensure_data_dirs()
    motion_id = args.motion_id or args.motion_asset_id
    if args.motion and not motion_id:
        raise ValueError("direct motion paths are no longer accepted by contact-editor; register the Motion first")
    run_contact_editor(
        motion_id=motion_id,
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
    )


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
    if output is not None:
        out = Path(output).expanduser()
    elif include_side_surfaces:
        out = SURFACES_ROOT / f"{motion_id}_terrain_surfaces_with_sides.jsonl"
    else:
        out = _default_terrain_surface_catalog(motion_id)
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


def _write_obj_surface_catalog(
    *,
    motion_id: str,
    terrain_mesh: str | Path,
    output: str | Path | None,
    include_side_surfaces: bool = False,
    include_ground: bool = True,
    ground_z: float = 0.0,
    ground_half_extent: float = 10.0,
) -> Path:
    if output is not None:
        out = Path(output).expanduser()
    elif include_side_surfaces:
        out = SURFACES_ROOT / f"{motion_id}_terrain_surfaces_with_sides.jsonl"
    else:
        out = _default_terrain_surface_catalog(motion_id)
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


def _resolve_surface_catalog(
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
    if terrain_mesh:
        out = _write_obj_surface_catalog(
            motion_id=motion_id,
            terrain_mesh=terrain_mesh,
            output=None,
            include_side_surfaces=include_side_surfaces,
            include_ground=include_ground,
            ground_z=ground_z,
            ground_half_extent=ground_half_extent,
        )
        print(f"generated terrain surface catalog from OBJ: {out}")
        return out
    raise ValueError("surface catalog is required; pass --surface-catalog, --terrain-urdf, or --terrain-mesh")


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
    print(
        f"validated contact edit plan {args.plan} edits={len(plan.edits)} "
        f"surface_transforms={len(plan.surface_transforms)} pose_edits={len(plan.pose_edits)} "
        f"status={plan.status}"
    )
    for warning in warnings:
        print(f"warning: {warning}")


def _cmd_generate_lte_augmentation(args: argparse.Namespace) -> None:
    plan = read_contact_edit_plan(args.plan)
    if plan.status not in {"validated", "locked"} and not args.allow_draft:
        raise ValueError("contact edit plan must be validated or locked; pass --allow-draft to override")
    result = apply_contact_edit_plan_to_motion(
        plan,
        output_motion_path=args.output_motion,
        mode=args.mode,
        source_plan_path=args.plan,
        source_contact_layer=args.source_contact_layer,
        output_contact_layer=args.output_contact_layer,
        output_segment_layer=args.output_segment_layer,
        output_motion_version_id=args.output_motion_version_id,
        falloff_before=args.falloff_before,
        falloff_after=args.falloff_after,
        global_weight=args.global_weight,
        edited_body_weight=args.edited_body_weight,
        fps=args.fps,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        register_motion_version=args.register_motion_version,
        build_canonical=args.build_canonical,
        allow_draft=args.allow_draft,
        allow_free=args.allow_free,
        fullbody_solver=args.fullbody_solver,
        contact_laplacian_iters=args.contact_laplacian_iters,
        contact_laplacian_damping=args.contact_laplacian_damping,
        contact_laplacian_trust=args.contact_laplacian_trust,
        edit_contact_weight=args.edit_contact_weight,
        fixed_contact_weight=args.fixed_contact_weight,
        temporal_laplacian_weight=args.temporal_laplacian_weight,
        body_relative_weight=args.body_relative_weight,
        q_prior_weight=args.q_prior_weight,
        q_smooth_weight=args.q_smooth_weight,
        mesh_laplacian_weight=args.mesh_laplacian_weight,
        contact_laplacian_proxy_only=args.contact_laplacian_proxy_only,
        lte_repo_root=args.lte_repo_root,
        ik_script=args.ik_script,
        ik_conda_env=args.ik_conda_env,
        ik_max_nfev=args.ik_max_nfev,
        ik_q_prior_weight=args.ik_q_prior_weight,
        ik_q_smooth_weight=args.ik_q_smooth_weight,
        intermediate_dir=args.intermediate_dir,
    )
    action = "dry-run diagnostic geometry" if args.dry_run else "generated diagnostic geometry"
    print(f"{action} {result.output_motion_path}")
    if result.output_contact_layer:
        print(f"output contact layer: {result.output_contact_layer}")
    if result.output_segment_layer:
        print(f"output segment layer: {result.output_segment_layer}")
    if result.output_motion_version_id:
        print(f"output motion version: {result.output_motion_version_id}")
    for warning in result.warnings or []:
        print(f"warning: {warning}")


def _cmd_generate_ref(args: argparse.Namespace) -> None:
    plan_path = Path(args.plan).expanduser()
    plan = read_contact_edit_plan(plan_path)
    output_contact_layer = args.output_contact_layer or plan.output_contact_layer
    output_segment_layer = args.output_segment_layer or plan.output_segment_layer
    if not output_contact_layer and not args.dry_run:
        raise ValueError("generate-ref requires --output-contact-layer or output_contact_layer in the plan")
    result = apply_contact_aware_edit_plan_to_motion(
        plan,
        output_motion_path=args.output_motion,
        bake_force=False,
        overwrite=args.overwrite,
        source_plan_path=plan_path,
        source_contact_layer=args.source_contact_layer,
        output_contact_layer=output_contact_layer,
        output_segment_layer=output_segment_layer,
        output_motion_version_id=args.output_motion_version_id,
        fps=args.fps,
        dry_run=args.dry_run,
        register_motion_version=args.register_motion_version,
        build_canonical=args.build_canonical,
        allow_draft=args.allow_draft,
        allow_free=args.allow_free,
        fullbody_solver="batch_contact_laplacian",
        contact_laplacian_iters=args.contact_laplacian_iters,
        contact_laplacian_damping=args.contact_laplacian_damping,
        contact_laplacian_trust=args.contact_laplacian_trust,
        edit_contact_weight=args.edit_contact_weight,
        fixed_contact_weight=args.fixed_contact_weight,
        temporal_laplacian_weight=args.temporal_laplacian_weight,
        body_relative_weight=args.body_relative_weight,
        q_prior_weight=args.q_prior_weight,
        q_smooth_weight=args.q_smooth_weight,
        mesh_laplacian_weight=args.mesh_laplacian_weight,
        contact_laplacian_proxy_only=False,
        lte_repo_root=args.lte_repo_root,
        ik_script=args.ik_script,
        ik_conda_env=args.ik_conda_env,
        ik_max_nfev=args.ik_max_nfev,
        ik_q_prior_weight=args.ik_q_prior_weight,
        ik_q_smooth_weight=args.ik_q_smooth_weight,
        intermediate_dir=args.intermediate_dir,
    )
    action = "dry-run WBT ref generation" if args.dry_run else "generated WBT ref"
    print(f"{action} {result.output_motion_path}")
    if result.generation.output_contact_layer:
        print(f"output contact layer: {result.generation.output_contact_layer}")
    if result.generation.output_segment_layer:
        print(f"output segment layer: {result.generation.output_segment_layer}")
    if result.generation.output_motion_version_id:
        print(f"output motion version: {result.generation.output_motion_version_id}")
    if not args.dry_run:
        print("next stage: run the edited reference in Newton and collect the canonical 8-part contact rollout")
    for warning in result.warnings:
        print(f"warning: {warning}")


def _cmd_force_retarget(args: argparse.Namespace) -> None:
    from .generation.pyroki_trajectory_optimizer import WholeTrajectoryConfig
    from .physics_retarget import (
        ForceGuidedRetargetConfig,
        NewtonSubprocessRunner,
        WholeTrajectoryPhysicsProjector,
        load_newton_force_target,
        run_force_guided_retarget,
    )

    target = load_newton_force_target(args.target_force_motion)
    projector = WholeTrajectoryPhysicsProjector(
        lte_path=args.lte,
        config=WholeTrajectoryConfig(max_iterations=args.pyroki_iterations),
    )
    runner = NewtonSubprocessRunner(
        base_manifest_path=args.manifest,
        target_force_motion_path=args.target_force_motion,
        motion_id=args.motion_id,
        checkpoint_path=args.checkpoint,
        python_executable=args.newton_python,
        repo_root=Path(__file__).resolve().parents[3],
        parallel_envs=args.num_envs,
        device=args.device,
        output_fps=args.fps,
    )
    result = run_force_guided_retarget(
        initial_motion_path=args.initial_motion,
        target_force_w=target.force_w,
        target_mask=target.mask,
        target_joint_pos=target.joint_pos,
        projector=projector,
        physics_runner=runner,
        output_motion_path=args.output_motion,
        work_dir=args.work_dir,
        config=ForceGuidedRetargetConfig(
            max_iterations=args.physics_iterations,
            force_weight=args.force_weight,
            tangential_force_weight=args.tangential_force_weight,
            unexpected_contact_weight=args.unexpected_contact_weight,
            contact_state_weight=args.contact_state_weight,
            tracking_weight=args.tracking_weight,
        ),
    )
    print(f"wrote Newton force-retargeted motion {result.output_motion_path}")
    print(f"best objective={result.best_objective:.6f} iterations={len(result.iterations) - 1}")


def _cmd_generate_contact_jitter_plans(args: argparse.Namespace) -> None:
    results, stats = generate_contact_jitter_plans(
        args.cut_summary,
        args.output_dir,
        augmentations_per_motion=args.augmentations_per_motion,
        offset_radius=args.offset_radius,
        edit_probability=args.edit_probability,
        max_edits=args.max_edits,
        max_attempts=args.max_attempts,
        seed=args.seed,
        bodies=args.body or DEFAULT_JITTER_BODIES,
        mode=args.mode,
        sampler=args.sampler,
        min_radius_fraction=args.min_radius_fraction,
        knee_radius_scale=args.knee_radius_scale,
        limit_motions=args.limit_motions,
    )
    print(
        "generated contact jitter plans "
        f"plans={stats['plan_count']} motions={stats['source_motion_count']} "
        f"skipped_no_edits={stats['skipped_no_edits']} output_dir={args.output_dir}"
    )
    if results:
        print(f"manifest: {Path(args.output_dir).expanduser() / 'manifest.json'}")


def _cmd_generate_augmentations(args: argparse.Namespace) -> None:
    run_augmentation_queue(
        AugmentationRunConfig(
            plan_manifest=args.plan_manifest,
            start_index=args.start_index,
            limit=args.limit,
            output_motion_dir=args.output_motion_dir,
            motion_version_prefix=args.motion_version_prefix,
            source_contact_layer=args.source_contact_layer,
            state_path=args.state_path,
            accepted_manifest=args.accepted_manifest,
            max_attempts=args.max_attempts,
            max_proxy_contact_error_m=args.max_proxy_contact_error_m,
            max_environment_anchor_error_m=args.max_environment_anchor_error_m,
            allow_draft=args.allow_draft,
            allow_free=args.allow_free,
            fullbody_solver=args.fullbody_solver,
            contact_laplacian_iters=args.contact_laplacian_iters,
            contact_laplacian_damping=args.contact_laplacian_damping,
            contact_laplacian_trust=args.contact_laplacian_trust,
            edit_contact_weight=args.edit_contact_weight,
            fixed_contact_weight=args.fixed_contact_weight,
            temporal_laplacian_weight=args.temporal_laplacian_weight,
            body_relative_weight=args.body_relative_weight,
            q_prior_weight=args.q_prior_weight,
            q_smooth_weight=args.q_smooth_weight,
            mesh_laplacian_weight=args.mesh_laplacian_weight,
            overwrite=args.overwrite,
            register_motion_version=args.register_motion_version,
            build_canonical=args.build_canonical,
            dry_run=args.dry_run,
            continue_on_error=args.continue_on_error,
            lte_repo_root=args.lte_repo_root,
            ik_script=args.ik_script,
            ik_conda_env=args.ik_conda_env,
            ik_max_nfev=args.ik_max_nfev,
            ik_q_prior_weight=args.ik_q_prior_weight,
            ik_q_smooth_weight=args.ik_q_smooth_weight,
            intermediate_dir=args.intermediate_dir,
        )
    )


def _cmd_batch_generate_lte_augmentations(args: argparse.Namespace) -> None:
    """Compatibility alias for the dataset-level augmentation queue."""

    _cmd_generate_augmentations(args)


def _cmd_register_motion_asset(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    record = MotionAssetRecord(
        motion_asset_id=args.motion_asset_id,
        motion_path=str(Path(args.motion).expanduser()),
        source=args.source,
        fps=args.fps,
        motion_id=getattr(args, "motion_id", None),
        terrain_id=getattr(args, "terrain_id", None),
        terrain_urdf=str(Path(args.terrain_urdf).expanduser()) if getattr(args, "terrain_urdf", None) else None,
        terrain_mesh=str(Path(args.terrain_mesh).expanduser()) if getattr(args, "terrain_mesh", None) else None,
        surface_catalog_path=str(Path(args.surface_catalog).expanduser()) if getattr(args, "surface_catalog", None) else None,
        raw_contact={
            "available": bool(getattr(args, "raw_contact", False)),
            "source": getattr(args, "raw_contact_source", None),
        },
        derived={
            key: value
            for key, value in {
                "contact_layer": getattr(args, "contact_layer", None),
                "bound_contact_layer": getattr(args, "bound_contact_layer", None),
                "edit_plan_path": getattr(args, "edit_plan", None),
                "output_contact_layer": getattr(args, "output_contact_layer", None),
            }.items()
            if value
        },
    )
    out = write_motion_asset(record)
    print(f"registered motion {record.motion_asset_id} path={out}")


def _add_register_motion_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--motion-asset-id", "--motion-id", dest="motion_asset_id", required=True)
    parser.add_argument("--motion", required=True)
    parser.add_argument("--rollout-motion-id", dest="motion_id", default=None)
    parser.add_argument("--terrain-id", default=None)
    parser.add_argument("--terrain-urdf", default=None)
    parser.add_argument("--terrain-mesh", default=None)
    parser.add_argument("--surface-catalog", default=None)
    parser.add_argument("--contact-layer", default=None)
    parser.add_argument("--bound-contact-layer", default=None)
    parser.add_argument("--edit-plan", default=None)
    parser.add_argument("--output-contact-layer", default=None)
    parser.add_argument("--raw-contact", action="store_true")
    parser.add_argument("--raw-contact-source", default=None)
    parser.add_argument("--fps", type=float, default=None)
    parser.add_argument("--source", default="local")


def _cmd_list_motions(_args: argparse.Namespace) -> None:
    ensure_data_dirs()
    for record in list_motion_assets():
        print(
            f"{record.motion_asset_id}\tmotion_id={record.motion_id or record.motion_asset_id}"
            f"\tmotion={record.motion_path}\tterrain={record.terrain_urdf or '-'}"
        )


def _cmd_show_motion(args: argparse.Namespace) -> None:
    ensure_data_dirs()
    record = read_motion_asset(args.motion_id)
    print(record.to_dict())


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
    parser = argparse.ArgumentParser(
        prog="motion-edit",
        description="Contact-centric motion curation: register motion, bind contacts, edit in contact-editor, then generate lte_fullbody motion.",
    )
    public_commands = (
        "init,register-motion,register-motion-asset,list-motions,show-motion,"
        "import-asset-manifest,import-force-proto,bind-contact-surfaces,summarize-surface-bindings,"
        "export-surface-binding-report,export-surface-binding-overlay,"
        "contact-editor,validate-contact-edit-plan,generate-ref,"
        "force-retarget,"
        "generate-contact-jitter-plans,generate-augmentations,"
        "register-motion-version,build-canonical-segmentation,build-token-catalog,"
        "export-manifest,export-split-npz"
    )
    sub = parser.add_subparsers(dest="cmd", required=True, metavar="{" + public_commands + "}")

    def add_hidden_parser(name: str) -> argparse.ArgumentParser:
        hidden = sub.add_parser(name, help=argparse.SUPPRESS)
        sub._choices_actions = [action for action in sub._choices_actions if action.dest != name]  # type: ignore[attr-defined]
        return hidden

    p = sub.add_parser("init")
    p.set_defaults(func=_cmd_init)

    p = sub.add_parser("import-force-proto")
    p.add_argument("--motion-dir", required=True)
    p.add_argument("--pattern", default="*.npz")
    p.add_argument("--layer-name", default="force_contact")
    p.add_argument("--source", default="force_contact")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--max-surface-distance", type=float, default=0.08)
    p.add_argument("--use-registered-motion-ids", action="store_true")
    p.add_argument("--update-motions", action="store_true")
    p.set_defaults(func=_cmd_import_force_proto)

    p = sub.add_parser("import-asset-manifest")
    p.add_argument("--manifest", required=True)
    p.add_argument("--layer-name", default="newton_8part")
    p.add_argument("--motion-id", action="append", default=None, help="Import one climb_XX or numeric motion id; repeatable")
    p.add_argument("--fps", type=float, default=50.0)
    p.add_argument("--verify-hashes", action=argparse.BooleanOptionalAction, default=True)
    p.set_defaults(func=_cmd_import_asset_manifest)

    p = add_hidden_parser("import-manual-cuts")
    p.add_argument("--segments-dir", required=True)
    p.add_argument("--layer-name", default="default")
    p.set_defaults(func=_cmd_import_manual_cuts)

    p = add_hidden_parser("export-cutter-segments")
    p.add_argument("--source", required=True, help="Layer path relative to data/layers, e.g. candidates/force_contact")
    p.add_argument("--output-dir", default=None)
    p.add_argument("--install-to", default=None)
    p.set_defaults(func=_cmd_export_cutter_segments)

    p = add_hidden_parser("export-contact-overlay")
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
    p.add_argument("--terrain-mesh", default=None)
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

    p = sub.add_parser("refine-contact-anchor-positions", help="[internal] refine anchor positions from raw contact points")
    p.add_argument("--contact-layer", required=True, help="Contact layer path relative to data/layers")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--motion", required=True, help="Motion npz containing raw_contact_* arrays")
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--output-contact-layer", required=True)
    p.add_argument("--max-part-distance", type=float, default=0.25)
    p.add_argument("--max-surface-distance", type=float, default=0.05)
    p.set_defaults(func=_cmd_refine_contact_anchor_positions)

    p = sub.add_parser("merge-contact-anchors", help="[internal] merge fragmented contact anchors")
    p.add_argument("--contact-layer", required=True, help="Contact layer path relative to data/layers")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--output-contact-layer", required=True)
    p.add_argument("--max-gap", type=int, default=3)
    p.add_argument("--max-distance", type=float, default=0.06)
    p.add_argument("--merge-class", action="append", choices=("top", "ground", "edge_candidate", "outside_known_surfaces", "raw_missing"))
    p.add_argument("--allow-cross-class", action="store_true")
    p.add_argument("--source", default="merge_contact_anchors")
    p.set_defaults(func=_cmd_merge_contact_anchors)

    p = sub.add_parser("filter-contact-anchors", help="[internal] filter contact anchors for editor preparation")
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

    p = sub.add_parser("create-box-surface-catalog", help="[diagnostic] create a simple box surface catalog")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--box", action="append", required=True, help="object_id:cx,cy,cz:sx,sy,sz")
    p.add_argument("--top-only", action="store_true")
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_create_box_surface_catalog)

    p = sub.add_parser("create-urdf-surface-catalog", help="[internal] create surface catalog from terrain URDF")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--terrain-urdf", required=True)
    p.add_argument("--include-side-surfaces", action="store_true")
    p.add_argument("--no-ground", action="store_true")
    p.add_argument("--ground-z", type=float, default=0.0)
    p.add_argument("--ground-half-extent", type=float, default=10.0)
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_create_urdf_surface_catalog)

    p = add_hidden_parser("move-contact-anchor")
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

    p = sub.add_parser("generate-ref")
    p.add_argument("--plan", required=True)
    p.add_argument("--output-motion", required=True)
    p.add_argument("--output-motion-version-id", default=None)
    p.add_argument("--output-contact-layer", default=None)
    p.add_argument("--output-segment-layer", default=None)
    p.add_argument("--source-contact-layer", default=None)
    p.add_argument("--allow-draft", action="store_true")
    p.add_argument("--allow-free", action="store_true")
    p.add_argument("--contact-laplacian-iters", type=int, default=8)
    p.add_argument("--contact-laplacian-damping", type=float, default=1.0e-4)
    p.add_argument("--contact-laplacian-trust", type=float, default=0.05)
    p.add_argument("--edit-contact-weight", type=float, default=1000.0)
    p.add_argument("--fixed-contact-weight", type=float, default=1000.0)
    p.add_argument("--temporal-laplacian-weight", type=float, default=40.0)
    p.add_argument("--body-relative-weight", type=float, default=10.0)
    p.add_argument("--q-prior-weight", type=float, default=0.02)
    p.add_argument("--q-smooth-weight", type=float, default=0.0)
    p.add_argument("--mesh-laplacian-weight", type=float, default=1.0)
    p.add_argument("--fps", type=float, default=50.0)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--register-motion-version", action="store_true")
    p.add_argument("--build-canonical", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--lte-repo-root", default=None, help=argparse.SUPPRESS)
    p.add_argument("--ik-script", default=None, help=argparse.SUPPRESS)
    p.add_argument("--ik-conda-env", default="env_somaforge", help=argparse.SUPPRESS)
    p.add_argument("--ik-max-nfev", type=int, default=None, help=argparse.SUPPRESS)
    p.add_argument("--ik-q-prior-weight", type=float, default=12.0, help=argparse.SUPPRESS)
    p.add_argument("--ik-q-smooth-weight", type=float, default=60.0, help=argparse.SUPPRESS)
    p.add_argument("--intermediate-dir", default=None)
    p.set_defaults(func=_cmd_generate_ref)

    p = sub.add_parser("force-retarget", help="match an edited trajectory to a real Newton 8-part force rollout")
    p.add_argument("--initial-motion", required=True, help="Edited PyRoki/Holosoma motion used as the first candidate")
    p.add_argument("--lte", required=True, help="Contact-Laplacian keypoint NPZ produced by generate-ref")
    p.add_argument("--target-force-motion", required=True, help="Canonical Newton rollout containing target 8-part force")
    p.add_argument("--manifest", required=True, help="Canonical base motion/terrain manifest")
    p.add_argument("--motion-id", required=True)
    p.add_argument("--checkpoint", required=True, help="WBT checkpoint used to roll out every candidate")
    p.add_argument("--newton-python", required=True, help="Python executable in the Isaac Lab 3/Newton conda environment")
    p.add_argument("--output-motion", required=True)
    p.add_argument("--work-dir", required=True)
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--num-envs", type=int, default=16)
    p.add_argument("--fps", type=float, default=50.0)
    p.add_argument("--physics-iterations", type=int, default=4)
    p.add_argument("--pyroki-iterations", type=int, default=25)
    p.add_argument("--force-weight", type=float, default=1.0)
    p.add_argument("--tangential-force-weight", type=float, default=0.25)
    p.add_argument("--unexpected-contact-weight", type=float, default=0.5)
    p.add_argument("--contact-state-weight", type=float, default=0.25)
    p.add_argument("--tracking-weight", type=float, default=0.1)
    p.set_defaults(func=_cmd_force_retarget)

    p = add_hidden_parser("generate-lte-augmentation")
    p.add_argument("--plan", required=True)
    p.add_argument("--output-motion", required=True)
    p.add_argument("--output-motion-version-id", default=None)
    p.add_argument("--output-contact-layer", default=None)
    p.add_argument("--output-segment-layer", default=None)
    p.add_argument("--source-contact-layer", default=None)
    p.add_argument("--allow-draft", action="store_true")
    p.add_argument("--allow-free", action="store_true")
    p.add_argument("--mode", choices=("lte_fullbody",), default="lte_fullbody")
    p.add_argument("--fullbody-solver", choices=("ik_subprocess", "batch_contact_laplacian"), default="batch_contact_laplacian")
    p.add_argument("--contact-laplacian-iters", type=int, default=8)
    p.add_argument("--contact-laplacian-damping", type=float, default=1.0e-4)
    p.add_argument("--contact-laplacian-trust", type=float, default=0.05)
    p.add_argument("--edit-contact-weight", type=float, default=1000.0)
    p.add_argument("--fixed-contact-weight", type=float, default=1000.0)
    p.add_argument("--temporal-laplacian-weight", type=float, default=40.0)
    p.add_argument("--body-relative-weight", type=float, default=10.0)
    p.add_argument("--q-prior-weight", type=float, default=0.02)
    p.add_argument("--q-smooth-weight", type=float, default=0.0)
    p.add_argument("--mesh-laplacian-weight", type=float, default=1.0)
    p.add_argument("--contact-laplacian-proxy-only", action="store_true", help="[debug] write only the body-space contact-Laplacian proxy output; do not run IK")
    p.add_argument("--falloff-before", type=int, default=20)
    p.add_argument("--falloff-after", type=int, default=20)
    p.add_argument("--global-weight", type=float, default=0.35)
    p.add_argument("--edited-body-weight", type=float, default=1.0)
    p.add_argument("--fps", type=float, default=50.0)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--register-motion-version", action="store_true")
    p.add_argument("--build-canonical", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--lte-repo-root", default=None, help="[legacy ik_subprocess] external LTE repo root")
    p.add_argument("--ik-script", default=None, help="[legacy ik_subprocess] fullbody IK script")
    p.add_argument("--ik-conda-env", default="env_somaforge", help="[legacy ik_subprocess] conda env for external IK")
    p.add_argument("--ik-max-nfev", type=int, default=None, help="[legacy ik_subprocess] maximum IK evaluations")
    p.add_argument("--ik-q-prior-weight", type=float, default=12.0)
    p.add_argument("--ik-q-smooth-weight", type=float, default=60.0)
    p.add_argument("--intermediate-dir", default=None)
    p.set_defaults(func=_cmd_generate_lte_augmentation)

    p = sub.add_parser("generate-contact-jitter-plans")
    p.add_argument("--cut-summary", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--augmentations-per-motion", type=int, default=8)
    p.add_argument("--offset-radius", type=float, default=0.05)
    p.add_argument("--edit-probability", type=float, default=0.35)
    p.add_argument("--max-edits", type=int, default=12)
    p.add_argument("--max-attempts", type=int, default=32)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument(
        "--body",
        action="append",
        choices=("left_heel", "left_toe", "right_heel", "right_toe", "left_hand", "right_hand", "left_knee", "right_knee"),
    )
    p.add_argument("--mode", choices=("reject", "clamp"), default="reject")
    p.add_argument("--sampler", choices=("local_disk", "local_annulus", "surface_uniform", "mixed"), default="local_disk")
    p.add_argument("--min-radius-fraction", type=float, default=0.5)
    p.add_argument("--knee-radius-scale", type=float, default=0.5)
    p.add_argument("--limit-motions", type=int, default=None)
    p.set_defaults(func=_cmd_generate_contact_jitter_plans)

    def add_augmentation_queue_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--plan-manifest", required=True)
        parser.add_argument("--start-index", type=int, default=0)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--output-motion-dir", default=None)
        parser.add_argument("--motion-version-prefix", default="")
        parser.add_argument("--source-contact-layer", default=None)
        parser.add_argument("--state-path", default=None)
        parser.add_argument("--accepted-manifest", default=None)
        parser.add_argument("--max-attempts", type=int, default=2)
        parser.add_argument("--max-proxy-contact-error-m", type=float, default=5.0e-3)
        parser.add_argument("--max-environment-anchor-error-m", type=float, default=5.0e-4)
        parser.add_argument("--allow-draft", action="store_true")
        parser.add_argument("--allow-free", action="store_true")
        parser.add_argument(
            "--fullbody-solver",
            choices=("batch_contact_laplacian",),
            default="batch_contact_laplacian",
            help="compatibility name for one motion's whole-trajectory Contact Laplacian + full-body IK solve",
        )
        parser.add_argument("--contact-laplacian-iters", type=int, default=8)
        parser.add_argument("--contact-laplacian-damping", type=float, default=1.0e-4)
        parser.add_argument("--contact-laplacian-trust", type=float, default=0.05)
        parser.add_argument("--edit-contact-weight", type=float, default=1000.0)
        parser.add_argument("--fixed-contact-weight", type=float, default=1000.0)
        parser.add_argument("--temporal-laplacian-weight", type=float, default=40.0)
        parser.add_argument("--body-relative-weight", type=float, default=10.0)
        parser.add_argument("--q-prior-weight", type=float, default=0.02)
        parser.add_argument("--q-smooth-weight", type=float, default=0.0)
        parser.add_argument("--mesh-laplacian-weight", type=float, default=1.0)
        parser.add_argument("--overwrite", action="store_true")
        parser.add_argument("--register-motion-version", action="store_true")
        parser.add_argument("--build-canonical", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")
        parser.add_argument("--lte-repo-root", default=None)
        parser.add_argument("--ik-script", default=None)
        parser.add_argument("--ik-conda-env", default="env_somaforge")
        parser.add_argument("--ik-max-nfev", type=int, default=None)
        parser.add_argument("--ik-q-prior-weight", type=float, default=12.0)
        parser.add_argument("--ik-q-smooth-weight", type=float, default=60.0)
        parser.add_argument("--intermediate-dir", default=None)

    p = sub.add_parser(
        "generate-augmentations",
        help="run a durable queue of independent ContactEditPlan data augmentations",
    )
    add_augmentation_queue_arguments(p)
    p.set_defaults(func=_cmd_generate_augmentations)

    p = add_hidden_parser("batch-generate-lte-augmentations")
    add_augmentation_queue_arguments(p)
    p.set_defaults(func=_cmd_batch_generate_lte_augmentations)

    p = sub.add_parser("register-motion-asset")
    p.add_argument("--motion-asset-id", required=True)
    p.add_argument("--motion", required=True)
    p.add_argument("--motion-id", default=None)
    p.add_argument("--terrain-id", default=None)
    p.add_argument("--terrain-urdf", default=None)
    p.add_argument("--terrain-mesh", default=None)
    p.add_argument("--surface-catalog", default=None)
    p.add_argument("--contact-layer", default=None)
    p.add_argument("--bound-contact-layer", default=None)
    p.add_argument("--edit-plan", default=None)
    p.add_argument("--output-contact-layer", default=None)
    p.add_argument("--raw-contact", action="store_true")
    p.add_argument("--raw-contact-source", default=None)
    p.add_argument("--fps", type=float, default=None)
    p.add_argument("--source", default="local")
    p.set_defaults(func=_cmd_register_motion_asset)

    p = sub.add_parser("register-motion")
    _add_register_motion_args(p)
    p.set_defaults(func=_cmd_register_motion_asset)

    p = sub.add_parser("list-motions")
    p.set_defaults(func=_cmd_list_motions)

    p = sub.add_parser("show-motion")
    p.add_argument("--motion-id", required=True)
    p.set_defaults(func=_cmd_show_motion)

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

    p = add_hidden_parser("migrate-layer-to-canonical")
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

    p = sub.add_parser("mark-segment-status", help="[advanced] update canonical segment status")
    p.add_argument("--motion-version-id", required=True)
    p.add_argument("--segment-id", action="append", default=None)
    p.add_argument("--status", choices=("candidate", "accepted", "rejected", "manual"), default=None)
    p.add_argument("--reason", default=None)
    p.add_argument("--source", default="mark_segment_status")
    p.add_argument("--status-by-file", default=None)
    p.set_defaults(func=_cmd_mark_segment_status)

    p = add_hidden_parser("canonical-action")
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

    p = add_hidden_parser("import-lte-catalog")
    p.add_argument("--catalog", required=True)
    p.add_argument("--layer-name", default="lte")
    p.set_defaults(func=_cmd_import_lte_catalog)

    p = add_hidden_parser("accept")
    p.add_argument("--source", required=True)
    p.add_argument("--layer-name", default="default")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--segment-id", action="append", default=None)
    p.add_argument("--index", action="append", type=int, default=None)
    p.set_defaults(func=lambda args: setattr(args, "status", "accepted") or _cmd_curate(args))

    p = add_hidden_parser("reject")
    p.add_argument("--source", required=True)
    p.add_argument("--layer-name", default="default")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--segment-id", action="append", default=None)
    p.add_argument("--index", action="append", type=int, default=None)
    p.set_defaults(func=lambda args: setattr(args, "status", "rejected") or _cmd_curate(args))

    p = add_hidden_parser("list-layer")
    p.add_argument("--source", required=True)
    p.add_argument("--motion-id", default=None)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=_cmd_list_layer)

    p = sub.add_parser("list-contact-layer")
    p.add_argument("--source", required=True, help="Contact layer path relative to data/layers, e.g. contact/force_contact")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=_cmd_list_contact_layer)

    p = add_hidden_parser("workbench-action")
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

    p = sub.add_parser("contact-editor", help="launch the main interactive contact-anchor editor")
    p.add_argument("motion", nargs="?", default=None, help=argparse.SUPPRESS)
    p.add_argument("--motion-id", default=None)
    p.add_argument("--motion-asset-id", default=None, help=argparse.SUPPRESS)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8094)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(func=_cmd_contact_editor)

    p = add_hidden_parser("workbench")
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

    p = sub.add_parser("detect-motion", help="[diagnostic] inspect inferred terrain/contact paths for a motion")
    p.add_argument("motion")
    p.add_argument("--repo-root", default=None)
    p.add_argument("--dataset-root", default=None)
    p.set_defaults(func=_cmd_detect_motion)

    p = add_hidden_parser("edit-clip")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--end", type=int, required=True)
    p.set_defaults(func=_cmd_edit_clip)

    p = add_hidden_parser("edit-splice")
    p.add_argument("--output", required=True)
    p.add_argument("inputs", nargs="+")
    p.set_defaults(func=_cmd_edit_splice)

    p = add_hidden_parser("summarize")
    p.set_defaults(func=_cmd_summarize)
    public_help = {
        "init": "initialize local motion_edit data directories",
        "register-motion": "register an archived source rollout bundle",
        "register-motion-asset": "register a motion asset path",
        "list-motions": "list registered motions",
        "show-motion": "show one registered motion",
        "import-asset-manifest": "register canonical Newton force, source motion, and terrain assets from a manifest",
        "import-force-proto": "extract contact-first proto layers from rollout motions",
        "bind-contact-surfaces": "bind contact anchors to known terrain/object surfaces",
        "summarize-surface-bindings": "summarize surface binding quality",
        "export-surface-binding-report": "write a surface binding inspection report",
        "export-surface-binding-overlay": "write a viewer overlay for surface bindings",
        "contact-editor": "launch the main Contact Editor UI",
        "validate-contact-edit-plan": "validate staged contact-anchor edits",
        "generate-ref": "generate an edited kinematic candidate for Newton force retargeting",
        "force-retarget": "match an edited trajectory to target force using repeated Newton rollouts",
        "generate-contact-jitter-plans": "generate surface-constrained contact jitter plans",
        "generate-augmentations": "run and validate a resumable ContactEditPlan augmentation queue",
        "register-motion-version": "register an archived source or generated force-ref motion version",
        "build-canonical-segmentation": "initialize the canonical segmentation for a motion version",
        "build-token-catalog": "build tokens from canonical segments",
        "export-manifest": "export a manifest from legacy layers or a motion version",
        "export-split-npz": "materialize split npz export cache",
    }
    sub._choices_actions = [  # type: ignore[attr-defined]
        argparse._SubParsersAction._ChoicesPseudoAction(name, [], help_text)
        for name, help_text in public_help.items()
        if name in sub.choices
    ]
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
