#!/usr/bin/env python3
"""Generate one contact-aware edited motion end to end.

Pipeline:
  ContactEditPlan
    -> batch contact-Laplacian semantic curve
    -> rigid Newton-recorded contact patch task-space spec
    -> PyRoki trajectory IK preview
    -> direct Newton eval_fk canonical motion

No Isaac Lab, Kit, or SimulationContext is started.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from motion_edit.generation.contact_aware_preview import generate_contact_aware_pyroki_preview
from motion_edit.generation.newton_direct_fk import canonicalize_motion_with_direct_newton_fk
from motion_edit.generation.omni_generation_defaults import OMNI_GENERATION_DEFAULTS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="Final direct-Newton-canonical motion NPZ.")
    parser.add_argument("--source-contact-layer", default=None)
    parser.add_argument("--intermediate-dir", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--allow-free", action="store_true")
    parser.add_argument(
        "--contact-laplacian-iters",
        type=int,
        default=int(OMNI_GENERATION_DEFAULTS["contact_laplacian_iters"]),
    )
    parser.add_argument("--contact-laplacian-damping", type=float, default=1.0e-4)
    parser.add_argument("--contact-laplacian-trust", type=float, default=0.05)
    parser.add_argument("--edit-contact-weight", type=float, default=1000.0)
    parser.add_argument("--fixed-contact-weight", type=float, default=1000.0)
    parser.add_argument(
        "--temporal-laplacian-weight",
        type=float,
        default=float(OMNI_GENERATION_DEFAULTS["temporal_laplacian_weight"]),
    )
    parser.add_argument(
        "--body-relative-weight",
        type=float,
        default=float(OMNI_GENERATION_DEFAULTS["body_relative_weight"]),
    )
    parser.add_argument(
        "--q-prior-weight",
        type=float,
        default=float(OMNI_GENERATION_DEFAULTS["q_prior_weight"]),
    )
    parser.add_argument(
        "--q-smooth-weight",
        type=float,
        default=float(OMNI_GENERATION_DEFAULTS["q_smooth_weight"]),
    )
    parser.add_argument(
        "--mesh-laplacian-weight",
        type=float,
        default=float(OMNI_GENERATION_DEFAULTS["mesh_laplacian_weight"]),
    )
    parser.add_argument("--source-reference-weight", type=float, default=0.01)
    parser.add_argument("--boundary-ramp-frames", type=int, default=10)
    parser.add_argument("--min-raw-contact-force-norm", type=float, default=0.0)
    parser.add_argument("--ik-conda-env", default="env_pyroki_climb_projection")
    parser.add_argument("--ik-script", type=Path, default=None)
    parser.add_argument("--ik-max-nfev", type=int, default=None)
    parser.add_argument("--newton-device", default="cpu")
    parser.add_argument("--robot-urdf", type=Path, default=None)
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    work_dir = (
        args.intermediate_dir.expanduser().resolve()
        if args.intermediate_dir is not None
        else output.parent / f"{output.stem}_work"
    )
    work_dir.mkdir(parents=True, exist_ok=True)
    preview_path = work_dir / f"{output.stem}.pyroki_fk_preview.npz"

    preview = generate_contact_aware_pyroki_preview(
        args.plan,
        output_motion_path=preview_path,
        source_contact_layer=args.source_contact_layer,
        intermediate_dir=work_dir,
        overwrite=args.overwrite,
        allow_draft=args.allow_draft,
        allow_free=args.allow_free,
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
        source_reference_weight=args.source_reference_weight,
        boundary_ramp_frames=args.boundary_ramp_frames,
        min_raw_contact_force_norm=args.min_raw_contact_force_norm,
        ik_conda_env=args.ik_conda_env,
        ik_script=args.ik_script,
        ik_max_nfev=args.ik_max_nfev,
    )
    canonical = canonicalize_motion_with_direct_newton_fk(
        preview.output_motion_path,
        output,
        robot_urdf=args.robot_urdf,
        device=args.newton_device,
        overwrite=args.overwrite,
    )
    print(
        json.dumps(
            {
                "output": str(canonical.output_path),
                "semantic_task_proxy": str(preview.semantic_task_proxy_path),
                "preview": str(preview.output_motion_path),
                "taskspace_spec": str(preview.taskspace_spec_path),
                "ik_output": str(preview.ik_output_path),
                "frames": canonical.frame_count,
                "body_count": len(canonical.body_names),
                "joint_count": len(canonical.joint_names),
                "binding_summary": preview.binding_summary,
                "ik_diagnostics": preview.diagnostics,
                "newton_backend": canonical.backend_metadata,
                "warnings": list(preview.warnings),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
