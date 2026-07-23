#!/usr/bin/env python3
"""Generate the first contact-aware edited trajectory without starting Isaac.

The output is a PyRoki-FK-consistent preview. Run the direct Newton/MJWarp
canonicalizer before using it as a WBT training reference.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from motion_edit.generation import generate_contact_aware_pyroki_preview


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path, help="Validated ContactEditPlan JSON.")
    parser.add_argument("--output", required=True, type=Path, help="Output PyRoki preview motion NPZ.")
    parser.add_argument("--source-contact-layer", default=None)
    parser.add_argument("--intermediate-dir", type=Path, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--allow-free", action="store_true")
    parser.add_argument("--contact-laplacian-iters", type=int, default=5)
    parser.add_argument("--contact-laplacian-damping", type=float, default=1.0e-4)
    parser.add_argument("--contact-laplacian-trust", type=float, default=0.05)
    parser.add_argument("--edit-contact-weight", type=float, default=1000.0)
    parser.add_argument("--fixed-contact-weight", type=float, default=1000.0)
    parser.add_argument("--temporal-laplacian-weight", type=float, default=10.0)
    parser.add_argument("--body-relative-weight", type=float, default=10.0)
    parser.add_argument("--q-prior-weight", type=float, default=0.05)
    parser.add_argument("--q-smooth-weight", type=float, default=1.0)
    parser.add_argument("--mesh-laplacian-weight", type=float, default=0.0)
    parser.add_argument("--source-reference-weight", type=float, default=0.01)
    parser.add_argument("--boundary-ramp-frames", type=int, default=10)
    parser.add_argument("--min-raw-contact-force-norm", type=float, default=0.0)
    parser.add_argument("--ik-conda-env", default="env_pyroki_climb_projection")
    parser.add_argument("--ik-script", type=Path, default=None)
    parser.add_argument("--ik-max-nfev", type=int, default=None)
    args = parser.parse_args()

    result = generate_contact_aware_pyroki_preview(
        args.plan,
        output_motion_path=args.output,
        source_contact_layer=args.source_contact_layer,
        intermediate_dir=args.intermediate_dir,
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
    print(
        json.dumps(
            {
                "output_motion": str(result.output_motion_path),
                "semantic_task_proxy": str(result.semantic_task_proxy_path),
                "taskspace_spec": str(result.taskspace_spec_path),
                "ik_output": str(result.ik_output_path),
                "binding_summary": result.binding_summary,
                "diagnostics": result.diagnostics,
                "warnings": list(result.warnings),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
