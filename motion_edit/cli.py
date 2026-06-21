from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .adapters.omniretarget import detect_omniretarget_paths
from .adapters.lte import import_lte_catalog
from .curation import filter_segments, load_layer_segments, write_status_layer
from .editing import clip_motion, splice_motions
from .export import export_cutter_segments, export_motion_manifest, export_split_npz
from .force_proto import segments_from_masked_motion
from .io import read_jsonl, segment_from_dict
from .layers import iter_layer_files, read_layer, write_layer
from .paths import BACKUPS_ROOT, EXPORTS_ROOT, LAYERS_ROOT, ensure_data_dirs, layer_dir
from .viewer import launch_viewer


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
        total += len(segments)
    print(f"wrote {total} candidate segments to {out_dir}")


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
