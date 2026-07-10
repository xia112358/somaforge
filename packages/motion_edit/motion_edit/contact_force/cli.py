from __future__ import annotations

import argparse
import json
from pathlib import Path

from motion_edit.generation.contact_force_bake import (
    bake_prescribed_contact_forces_for_motion,
    validate_wbt_contact_force_policy_ref,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="motion-edit-bake-force",
        description="Bake or retarget contact forces into a generated policy-ref npz without running a rollout.",
    )
    parser.add_argument("--motion", required=True, help="Input fullbody motion npz containing joint_pos")
    parser.add_argument("--output-motion", default=None, help="Output npz. Omit only with --in-place")
    parser.add_argument("--in-place", action="store_true", help="Write force fields back into --motion")
    parser.add_argument("--mujoco-model", default=None, help="MuJoCo XML model used for prescribed-state contact solve")
    parser.add_argument("--source-force-ref", default=None, help="Source force-reference npz used when --solve-mode retarget")
    parser.add_argument("--target-contact-layer", default=None, help="Contact layer root used for target surface normals in retarget mode")
    parser.add_argument("--target-motion-id", default=None, help="Motion id inside --target-contact-layer")
    parser.add_argument("--solve-mode", choices=("forward", "inverse", "retarget"), default="forward")
    parser.add_argument("--fps", type=float, default=None, help="Override fps if the motion npz has no fps/dt")
    parser.add_argument("--assignment-max-distance", type=float, default=0.35)
    parser.add_argument("--force-unit-scale", type=float, default=1.0)
    parser.add_argument("--retarget-max-force-norm", type=float, default=5000.0)
    parser.add_argument("--retarget-smoothing-window", type=int, default=3)
    parser.add_argument("--policy-ref-compat", choices=("wbt_contact_force_6part", "none"), default="wbt_contact_force_6part")
    parser.add_argument("--geom-part-map", default=None, help="JSON file mapping MuJoCo geom names to canonical contact parts")
    parser.add_argument("--body-part-map", default=None, help="JSON file mapping MuJoCo body names to canonical contact parts")
    parser.add_argument("--check-policy-ref", action="store_true", help="Validate the output against the WBT contact-force policy ref contract")
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
    if args.solve_mode == "retarget":
        if args.source_force_ref is None:
            raise ValueError("--source-force-ref is required with --solve-mode retarget")
    elif args.mujoco_model is None:
        raise ValueError("--mujoco-model is required unless --solve-mode retarget")
    result = bake_prescribed_contact_forces_for_motion(
        motion,
        output_motion_path=output_motion,
        mujoco_model_path=args.mujoco_model,
        source_force_ref_path=args.source_force_ref,
        target_contact_layer_path=args.target_contact_layer,
        target_motion_id=args.target_motion_id,
        solve_mode=args.solve_mode,
        fps=args.fps,
        assignment_max_distance=args.assignment_max_distance,
        force_unit_scale=args.force_unit_scale,
        retarget_max_force_norm=args.retarget_max_force_norm,
        retarget_smoothing_window=args.retarget_smoothing_window,
        policy_ref_compat=args.policy_ref_compat,
        geom_part_map=_load_name_part_map(args.geom_part_map, label="geom-part-map"),
        body_part_map=_load_name_part_map(args.body_part_map, label="body-part-map"),
        overwrite=args.overwrite,
    )
    print(f"baked contact forces: {result.output_motion_path}")
    if args.solve_mode == "retarget":
        print(
            "force stats: "
            f"source_phases={result.metadata.get('source_phase_count', 0)} "
            f"retarget_phases={result.metadata.get('retarget_phase_count', 0)} "
            f"unmatched={result.metadata.get('unmatched_target_phase_count', 0)} "
            f"force_norm_max={result.metadata.get('force_norm_max', 0.0)}"
        )
    else:
        print(
            "force stats: "
            f"used_samples={result.metadata.get('used_sample_count', 0)} "
            f"unknown_samples={result.metadata.get('unknown_sample_count', 0)} "
            f"missing_intended={result.metadata.get('missing_intended_contact_frames', 0)} "
            f"force_norm_max={result.metadata.get('force_norm_max', 0.0)}"
        )
    for warning in result.warnings:
        print(f"warning: {warning}")
    if args.check_policy_ref:
        report = validate_wbt_contact_force_policy_ref(result.output_motion_path)
        print("policy-ref check: " + json.dumps(report, sort_keys=True))


def _load_name_part_map(path: str | None, *, label: str) -> dict[str, str]:
    if path is None:
        return {}
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object mapping names to contact parts")
    out: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError(f"{label} entries must be string-to-string mappings")
        out[key] = value
    return out


if __name__ == "__main__":
    main()
