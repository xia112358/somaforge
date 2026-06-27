from __future__ import annotations

import argparse
from pathlib import Path

from motion_edit.segmentation.session import (
    SegmentationEditSession,
    create_segmentation_edit_session,
    read_segmentation_edit_session,
    save_segmentation_edit_session,
)
from motion_edit.viewer.app import launch_viewer


def _load_or_create_session(args: argparse.Namespace) -> SegmentationEditSession:
    if args.session:
        session = read_segmentation_edit_session(args.session)
        if args.motion_version_id and session.motion_version_id != args.motion_version_id:
            raise ValueError(
                f"session motion_version_id={session.motion_version_id} does not match "
                f"--motion-version-id={args.motion_version_id}"
            )
        if session.state != "open":
            raise ValueError(f"segmentation edit session {session.session_id} is {session.state}, not open")
        return session
    if not args.motion_version_id:
        raise ValueError("pass --motion-version-id to create a session, or --session to reuse one")
    return create_segmentation_edit_session(
        args.motion_version_id,
        session_id=args.session_id,
        overwrite=args.overwrite,
    )


def _cmd_cutter(args: argparse.Namespace) -> None:
    session = _load_or_create_session(args)
    motion_path = args.motion or session.motion_path
    print(f"segmentation session: {session.session_id}")
    print(f"motion_version_id: {session.motion_version_id}")
    print(f"draft segment path: {session.draft_segment_path}")
    print("opening existing segment timeline with draft segments as --segment-export-path")
    process = launch_viewer(
        motion_path,
        repo_root=args.repo_root,
        layer=None,
        segment_path=session.draft_segment_path,
        conda_env=args.conda_env,
        timeline_port=args.timeline_port,
        fps=args.fps,
        with_terrain=args.with_terrain,
    )
    print(f"viewer pid={process.pid}")
    print(f"Open Motion Cutter: http://localhost:{args.timeline_port}")
    process.wait()
    print("viewer closed")
    if args.save_on_exit:
        out = save_segmentation_edit_session(
            session,
            reason=args.reason or f"save segmentation cutter session {session.session_id}",
            allow_overlap=args.allow_overlap,
        )
        print(f"saved draft segmentation to canonical: {out}")
    else:
        print("canonical segmentation was not modified")
        print(f"review draft: motion-edit-seg list --session {session.session_id}")
        print(f"save later:  motion-edit-seg save --session {session.session_id}")
        print(f"discard:     motion-edit-seg discard --session {session.session_id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m motion_edit.segmentation.cutter",
        description=(
            "Open the existing motion cutter / segment timeline on a segmentation edit draft. "
            "This does not create a new timeline layer: the viewer receives draft_segments.jsonl "
            "as its normal --segment-export-path."
        ),
    )
    parser.add_argument("--motion-version-id", default=None, help="canonical motion version to copy into a draft session")
    parser.add_argument("--session", default=None, help="existing open segmentation edit session id, dir, or session.json")
    parser.add_argument("--session-id", default=None, help="new session id when creating a draft")
    parser.add_argument("--overwrite", action="store_true", help="overwrite an existing session with --session-id")
    parser.add_argument("--motion", default=None, help="override motion npz path; defaults to the motion version path")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--conda-env", default="hsretargeting")
    parser.add_argument("--timeline-port", type=int, default=8094)
    parser.add_argument("--fps", type=int, default=50)
    parser.add_argument("--with-terrain", action="store_true")
    parser.add_argument("--save-on-exit", action="store_true", help="replace canonical segmentation when the viewer exits")
    parser.add_argument("--allow-overlap", action="store_true", help="allow overlap validation warnings when saving")
    parser.add_argument("--reason", default=None)
    parser.set_defaults(func=_cmd_cutter)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
