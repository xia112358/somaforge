from __future__ import annotations

import argparse
import json
from pathlib import Path

from motion_edit.contact.plans import read_contact_edit_plan
from motion_edit.generation.contact_aware import apply_contact_aware_edit_plan_to_motion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="motion-edit-contact-aware-augment",
        description="Generate contact-aware motion augmentation and optionally bake prescribed contact forces.",
    )
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output-motion", required=True)
    parser.add_argument("--force-output-motion", default=None)
    parser.add_argument("--source-contact-layer", default=None)
    parser.add_argument("--output-contact-layer", default=None)
    parser.add_argument("--output-segment-layer", default=None)
    parser.add_argument("--output-motion-version-id", default=None)
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--allow-free", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fullbody-solver", choices=("ik_subprocess", "batch_contact_laplacian"), default="batch_contact_laplacian")
    parser.add_argument("--contact-laplacian-iters", type=int, default=5)
    parser.add_argument("--contact-laplacian-damping", type=float, default=1.0e-4)
    parser.add_argument("--contact-laplacian-trust", type=float, default=0.05)
    parser.add_argument("--edit-contact-weight", type=float, default=1000.0)
    parser.add_argument("--fixed-contact-weight", type=float, default=1000.0)
    parser.add_argument("--temporal-laplacian-weight", type=float, default=10.0)
    parser.add_argument("--body-relative-weight", type=float, default=10.0)
    parser.add_argument("--q-prior-weight", type=float, default=1.0)
    parser.add_argument("--q-smooth-weight", type=float, default=1.0)
    parser.add_argument("--mesh-laplacian-weight", type=float, default=0.0)
    parser.add_argument("--contact-laplacian-proxy-only", action="store_true")
    parser.add_argument("--lte-repo-root", default=None)
    parser.add_argument("--ik-script", default=None)
    parser.add_argument("--ik-conda-env", default="env_pyroki_climb_projection")
    parser.add_argument("--ik-max-nfev", type=int, default=None)
    parser.add_argument("--intermediate-dir", default=None)
    parser.add_argument("--no-force-bake", action="store_true")
    parser.add_argument("--force-mujoco-model", default=None)
    parser.add_argument(
        "--force-source-ref",
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--force-solve-mode", choices=("forward", "inverse", "retarget"), default="forward")
    parser.add_argument("--force-assignment-max-distance", type=float, default=0.35)
    parser.add_argument("--force-unit-scale", type=float, default=1.0)
    parser.add_argument("--force-retarget-max-force-norm", type=float, default=5000.0)
    parser.add_argument("--force-retarget-smoothing-window", type=int, default=3)
    parser.add_argument("--force-policy-ref-compat", choices=("wbt_contact_force_6part", "none"), default="wbt_contact_force_6part")
    parser.add_argument("--force-geom-part-map", default=None, help="JSON file mapping MuJoCo geom names to canonical contact parts")
    parser.add_argument("--force-body-part-map", default=None, help="JSON file mapping MuJoCo body names to canonical contact parts")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    bake_force = not bool(args.no_force_bake)
    if bake_force and not args.dry_run:
        if args.force_solve_mode != "retarget" and args.force_mujoco_model is None:
            raise ValueError("force baking requires --force-mujoco-model, or pass --no-force-bake")
    plan_path = Path(args.plan).expanduser()
    plan = read_contact_edit_plan(plan_path)
    result = apply_contact_aware_edit_plan_to_motion(
        plan,
        output_motion_path=args.output_motion,
        bake_force=bake_force,
        force_output_motion_path=args.force_output_motion,
        force_mujoco_model_path=args.force_mujoco_model,
        force_source_ref_path=args.force_source_ref,
        force_target_contact_layer_path=(Path("data/layers") / args.output_contact_layer) if args.output_contact_layer else None,
        force_target_motion_id=plan.source_motion_id if args.output_contact_layer else None,
        force_geom_part_map=_load_name_part_map(args.force_geom_part_map, label="force-geom-part-map"),
        force_body_part_map=_load_name_part_map(args.force_body_part_map, label="force-body-part-map"),
        force_solve_mode=args.force_solve_mode,
        force_assignment_max_distance=args.force_assignment_max_distance,
        force_unit_scale=args.force_unit_scale,
        force_retarget_max_force_norm=args.force_retarget_max_force_norm,
        force_retarget_smoothing_window=args.force_retarget_smoothing_window,
        force_policy_ref_compat=args.force_policy_ref_compat,
        overwrite=args.overwrite,
        source_plan_path=plan_path,
        source_contact_layer=args.source_contact_layer,
        output_contact_layer=args.output_contact_layer,
        output_segment_layer=args.output_segment_layer,
        output_motion_version_id=args.output_motion_version_id,
        dry_run=args.dry_run,
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
        intermediate_dir=args.intermediate_dir,
    )
    action = "dry-run contact-aware augmentation" if args.dry_run else "generated contact-aware augmentation"
    print(f"{action} {result.output_motion_path}")
    if result.force_bake is not None:
        meta = result.force_bake.metadata
        if args.force_solve_mode == "retarget":
            print(
                "force bake: "
                f"source_phases={meta.get('source_phase_count', 0)} "
                f"retarget_phases={meta.get('retarget_phase_count', 0)} "
                f"unmatched={meta.get('unmatched_target_phase_count', 0)} "
                f"force_norm_max={meta.get('force_norm_max', 0.0)}"
            )
        else:
            print(
                "force bake: "
                f"used_samples={meta.get('used_sample_count', 0)} "
                f"unknown_samples={meta.get('unknown_sample_count', 0)} "
                f"missing_intended={meta.get('missing_intended_contact_frames', 0)} "
                f"force_norm_max={meta.get('force_norm_max', 0.0)}"
            )
    for warning in result.warnings:
        print(f"warning: {warning}")


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
