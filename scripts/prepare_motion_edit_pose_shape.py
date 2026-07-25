#!/usr/bin/env python3
"""Prepare a low-jitter rollout pose seed and derived ContactEditPlan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from motion_edit.generation.pose_shape_cleanup import (
    filtered_pose_seed_arrays,
    write_pose_shape_plan,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollout", required=True, type=Path)
    parser.add_argument("--output-seed", required=True, type=Path)
    parser.add_argument("--plan-template", required=True, type=Path)
    parser.add_argument("--output-plan", required=True, type=Path)
    parser.add_argument("--canonical-motion", required=True, type=Path)
    parser.add_argument("--cutoff-hz", type=float, default=6.0)
    args = parser.parse_args()

    rollout = args.rollout.expanduser().resolve()
    output_seed = args.output_seed.expanduser().resolve()
    if not rollout.is_file():
        raise FileNotFoundError(rollout)
    with np.load(rollout, allow_pickle=True) as data:
        source = {key: data[key] for key in data.files}
    seed = filtered_pose_seed_arrays(
        source,
        source_path=rollout,
        cutoff_hz=args.cutoff_hz,
    )
    output_seed.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_seed, **seed)
    output_plan = write_pose_shape_plan(
        args.plan_template,
        args.output_plan,
        rollout_path=rollout,
        canonical_motion_path=args.canonical_motion,
        cutoff_hz=args.cutoff_hz,
    )
    print(
        json.dumps(
            {
                "rollout": str(rollout),
                "pose_seed": str(output_seed),
                "canonical_motion": str(
                    args.canonical_motion.expanduser().resolve()
                ),
                "derived_plan": str(output_plan),
                "frames": int(seed["joint_pos"].shape[0]),
                "cutoff_hz": float(args.cutoff_hz),
                "contact_force_source": str(
                    json.loads(output_plan.read_text(encoding="utf-8"))[
                        "metadata"
                    ]["contact_force_source_path"]
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
