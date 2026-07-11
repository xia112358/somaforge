from __future__ import annotations

import argparse
import json
from pathlib import Path

from motion_edit.generation.contact_force_bake import (
    bake_retargeted_contact_forces_for_motion,
    validate_wbt_contact_force_policy_ref,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="motion-edit-bake-force",
        description="Retarget an existing Isaac Lab/Newton contact-force reference.",
    )
    parser.add_argument("--motion", required=True, help="Input fullbody motion npz containing joint_pos")
    parser.add_argument("--output-motion", default=None, help="Output npz. Omit only with --in-place")
    parser.add_argument("--in-place", action="store_true", help="Write force fields back into --motion")
    parser.add_argument("--source-force-ref", required=True, help="Source Isaac Lab/Newton force-reference npz")
    parser.add_argument("--target-contact-layer", default=None, help="Contact layer root used for target surface normals in retarget mode")
    parser.add_argument("--target-motion-id", default=None, help="Motion id inside --target-contact-layer")
    parser.add_argument("--force-unit-scale", type=float, default=1.0)
    parser.add_argument("--retarget-max-force-norm", type=float, default=5000.0)
    parser.add_argument("--retarget-smoothing-window", type=int, default=3)
    parser.add_argument("--policy-ref-compat", choices=("wbt_contact_force_8part", "none"), default="wbt_contact_force_8part")
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
    result = bake_retargeted_contact_forces_for_motion(
        motion,
        output_motion_path=output_motion,
        source_force_ref_path=args.source_force_ref,
        target_contact_layer_path=args.target_contact_layer,
        target_motion_id=args.target_motion_id,
        force_unit_scale=args.force_unit_scale,
        max_force_norm=args.retarget_max_force_norm,
        smoothing_window=args.retarget_smoothing_window,
        policy_ref_compat=args.policy_ref_compat,
        overwrite=args.overwrite,
    )
    print(f"baked contact forces: {result.output_motion_path}")
    print(
        "force stats: "
        f"source_phases={result.metadata.get('source_phase_count', 0)} "
        f"retarget_phases={result.metadata.get('retarget_phase_count', 0)} "
        f"unmatched={result.metadata.get('unmatched_target_phase_count', 0)} "
        f"force_norm_max={result.metadata.get('force_norm_max', 0.0)}"
    )
    for warning in result.warnings:
        print(f"warning: {warning}")
    if args.check_policy_ref:
        report = validate_wbt_contact_force_policy_ref(
            result.output_motion_path, require_newton_source=False
        )
        print("diagnostic shape check: " + json.dumps(report, sort_keys=True))
if __name__ == "__main__":
    main()
