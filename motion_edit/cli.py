from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .adapters.omniretarget import detect_omniretarget_paths
from .adapters.lte import import_lte_catalog
from .curation import filter_segments, load_layer_segments, write_status_layer
from .editing import clip_motion, splice_motions
from .export import export_contact_overlay, export_cutter_segments, export_motion_manifest, export_split_npz
from .force_proto import contact_graph_from_masked_motion, segments_from_masked_motion
from .io import read_jsonl, segment_from_dict
from .layers import iter_layer_files, read_layer, write_layer
from .paths import BACKUPS_ROOT, EXPORTS_ROOT, LAYERS_ROOT, ensure_data_dirs, layer_dir
from .contact import write_contact_layer
from .contact.layers import read_contact_graph
from .contact.io import read_contact_anchors, read_contact_events, read_contact_transitions
from .contact.io import read_contact_patches
from .viewer import launch_viewer
from .workbench import (
    WorkbenchSession,
    curate_segment,
    export_cutter_session_file,
    load_workbench_segments,
    make_workbench_server,
    replace_segment,
    select_segment,
    split_segment,
    sync_cutter_session_file,
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


def _cmd_import_manual_cuts(args: argparse.Namespace) -> None:
    ensure_data_dirs()
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
    segments = _load_source_segments(args.source)
    output = export_motion_manifest(args.output, segments)
    print(f"wrote manifest {output}")


def _cmd_export_split_npz(args: argparse.Namespace) -> None:
    segments = _load_source_segments(args.source)
    if args.motion_id or args.segment_id or args.index is not None:
        segments = filter_segments(
            segments,
            motion_id=args.motion_id,
            segment_ids=set(args.segment_id or []) if args.segment_id else None,
            indices=set(args.index or []) if args.index is not None else None,
        )
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else EXPORTS_ROOT / "split_npz" / args.source.replace("/", "_")
    written = export_split_npz(output_dir, segments)
    print(f"wrote {len(written)} split npz files to {output_dir}")


def _cmd_import_lte_catalog(args: argparse.Namespace) -> None:
    motions, segments = import_lte_catalog(args.catalog, layer_name=args.layer_name)
    print(f"imported LTE catalog motions={motions} full_motion_segments={segments} layer=candidates/{args.layer_name}")


def _cmd_curate(args: argparse.Namespace) -> None:
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
        events = read_contact_events(event_path)
        anchors = read_contact_anchors(root / "anchors" / f"{motion_id}.jsonl")
        patch_path = root / "patches" / f"{motion_id}.jsonl"
        patches = read_contact_patches(patch_path) if patch_path.exists() else []
        transitions = read_contact_transitions(root / "transitions" / f"{motion_id}.jsonl")
        total_events += len(events)
        total_anchors += len(anchors)
        total_patches += len(patches)
        total_transitions += len(transitions)
        print(f"{motion_id}: events={len(events)} anchors={len(anchors)} patches={len(patches)} transitions={len(transitions)}")
        for anchor in anchors[: args.limit]:
            print(
                f"  anchor {anchor.start_frame:5d}->{anchor.end_frame:<5d} "
                f"{anchor.anchor_id} body={anchor.body} role={anchor.role}"
            )
        for patch in patches[: args.limit]:
            print(
                f"  patch  {patch.start_frame:5d}->{patch.end_frame:<5d} "
                f"{patch.patch_id} body={patch.body} anchor={patch.anchor_id}"
            )
        for transition in transitions[: args.limit]:
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

    p = sub.add_parser("export-manifest")
    p.add_argument("--source", required=True, help="Layer path relative to data/layers")
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_export_manifest)

    p = sub.add_parser("export-split-npz")
    p.add_argument("--source", required=True, help="Layer path relative to data/layers")
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
    p.add_argument("--source", required=True, help="Source layer path relative to data/layers")
    p.add_argument("--session-name", required=True)
    p.add_argument("--destination", default=None, help="Destination layer path, default manual/<session-name>")
    p.add_argument("--motion-id", default=None)
    p.add_argument("--repo-root", default=None)
    p.add_argument("--conda-env", default="hsretargeting")
    p.add_argument("--timeline-port", type=int, default=8094)
    p.add_argument("--fps", type=int, default=50)
    p.add_argument("--with-terrain", action="store_true")
    p.set_defaults(func=_cmd_cutter)

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
