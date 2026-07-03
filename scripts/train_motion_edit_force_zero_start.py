#!/usr/bin/env python3
"""Launch motion-edit force-ref finetuning with zero-start episodes.

This wrapper keeps the motion-edit finetune path separate from the standard
contact-force hotspot/probe training presets. It only requires a base checkpoint
and a motion-matched manifest; all zero-start overrides are applied here.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXP_NAME = "exp:g1-29dof-wbt-contact-force-zero-start"
DEFAULT_RUN_NAME = "motion_edit_force_ref_zero_start_from_base"


def _build_command(args: argparse.Namespace, extra_args: list[str]) -> list[str]:
    train_script = REPO_ROOT / "src/holosoma/holosoma/train_agent.py"
    headless = not args.gui

    cmd = [
        sys.executable,
        str(train_script),
        EXP_NAME,
        "simulator:isaaclab3-newton",
        "--training.checkpoint",
        str(args.checkpoint.expanduser()),
        "--training.name",
        args.name,
        "--training.num-envs",
        str(args.num_envs),
        "--training.headless",
        str(headless),
        "--training.export-onnx",
        "False",
        "--algo.config.num-learning-iterations",
        str(args.iterations),
        "--algo.config.actor-learning-rate",
        str(args.learning_rate),
        "--algo.config.critic-learning-rate",
        str(args.learning_rate),
        "--algo.config.load-optimizer",
        "False",
        "--algo.config.init-at-random-ep-len",
        "False",
        "--algo.config.export-onnx",
        "False",
        "--command.setup-terms.motion-command.params.motion-config.motion-manifest",
        str(args.motion_manifest.expanduser()),
        "--command.setup-terms.motion-command.params.motion-config.canonicalize-motion-order-on-load",
        str(args.canonicalize_motion_order_on_load),
        "--command.setup-terms.motion-command.params.motion-config.start-at-timestep-zero-prob",
        "1.0",
        "--command.setup-terms.motion-command.params.motion-config.freeze-at-timestep-zero-prob",
        "0.0",
        "--command.setup-terms.motion-command.params.motion-config.use-start-probe-envs",
        "False",
        "--command.setup-terms.motion-command.params.motion-config.probe-env-per-motion",
        "0",
        "--terrain.terrain-term.motion-matched-manifest",
        str(args.motion_manifest.expanduser()),
        "--logger.video.enabled",
        "False",
    ]
    if args.save_interval is not None:
        cmd.extend(["--algo.config.save-interval", str(args.save_interval)])
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]
    cmd.extend(extra_args)
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path, help="Base policy checkpoint to finetune from.")
    parser.add_argument("--motion-manifest", required=True, type=Path, help="Motion-matched force-ref manifest.")
    parser.add_argument("--num-envs", type=int, default=4096)
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--learning-rate", type=float, default=1.0e-4)
    parser.add_argument("--save-interval", type=int, default=100)
    parser.add_argument(
        "--canonicalize-motion-order-on-load",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Preorder loaded motion tensors for this force-ref finetune experiment.",
    )
    parser.add_argument("--name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--gui", action="store_true", help="Run with Isaac Sim GUI enabled.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved command without executing it.")
    args, extra_args = parser.parse_known_args()

    cmd = _build_command(args, extra_args)
    print("Command:")
    print(" ".join(cmd), flush=True)
    if args.dry_run:
        return
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


if __name__ == "__main__":
    main()
