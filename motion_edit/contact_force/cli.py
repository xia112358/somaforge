from __future__ import annotations

import argparse
from pathlib import Path

from motion_edit.generation.contact_force_bake import bake_prescribed_contact_forces_for_motion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="motion-edit-bake-force",
        description="Bake prescribed-playback contact forces into a generated motion npz without running a rollout.",
    )
    parser.add_argument("--motion", required=True, help="Input fullbody motion npz containing joint_pos")
    parser.add_argument("--output-motion", default=None, help="Output npz. Omit only with --in-place")
    parser.add_argument("--in-place", action="store_true", help="Write force fields back into --motion")
    parser.add_argument("--mujoco-model", required=True, help="MuJoCo XML model used for prescribed-state contact solve")
    parser.add_argument("--solve-mode", choices=("forward", "inverse"), default="forward")
    parser.add_argument("--fps", type=float, default=None, help="Override fps if the motion npz has no fps/dt")
    parser.add_argument("--assignment-max-distance", type=float, default=0.35)
    parser.add_argument("--force-unit-scale", type=float, default=1.0)
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing --output-motion when it already exists")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    motion = Path(args.motion).expanduser()
    output_motion = Path(args.output_motion).expanduser() if args.output_motion else None
    if output_motion is None and not args.in_place:
        raise ValueError("pass --output-motion or --in-place")
    if output_motion is not None and args.in_place:
        raise ValueError("--output-motion and --in-place are mutually exclusive")
    result = bake_prescribed_contact_forces_for_motion(
        motion,
        output_motion_path=output_motion,
        mujoco_model_path=args.mujoco_model,
        solve_mode=args.solve_mode,
        fps=args.fps,
        assignment_max_distance=args.assignment_max_distance,
        force_unit_scale=args.force_unit_scale,
        overwrite=args.overwrite,
    )
    print(f"baked prescribed contact forces: {result.output_motion_path}")
    print(
        "force stats: "
        f"used_samples={result.metadata.get('used_sample_count', 0)} "
        f"unknown_samples={result.metadata.get('unknown_sample_count', 0)} "
        f"missing_intended={result.metadata.get('missing_intended_contact_frames', 0)} "
        f"force_norm_max={result.metadata.get('force_norm_max', 0.0)}"
    )
    for warning in result.warnings:
        print(f"warning: {warning}")


if __name__ == "__main__":
    main()
