"""Evaluate a WBT checkpoint with online GMVQ references."""

from __future__ import annotations

from dataclasses import dataclass, replace

import tyro

from holosoma.config_values.wbt.g1.command import make_gmvq_wbt_command
from holosoma.eval_agent import run_eval_with_tyro
from holosoma.utils.eval_utils import CheckpointConfig, init_eval_logging, load_saved_experiment_config
from holosoma.utils.sim_utils import parse_isaaclab_launcher_args, sync_launcher_headless_config
from holosoma.utils.tyro_utils import TYRO_CONIFG


@dataclass(frozen=True)
class GMVQReferenceEvalConfig:
    bundle: str
    """Self-contained GMVQ policy-reference bundle."""

    bootstrap_motion: str
    """Canonical motion used only for the initial simulator reset pose."""

    max_steps: int = 2000
    """Maximum policy steps for the smoke/evaluation run."""

    parallel_envs: int = 1
    """Number of independently advancing online reference environments."""

    tracking_gate_m: float = 0.15
    """Pause reference phase while tracked hand/foot error exceeds this distance."""

    boundary_record: str | None = None
    """Optional NPZ path for online atom-boundary observations and teacher outputs."""

    motion_manifest: str | None = None
    """Optional motion-matched manifest used to select the eval motion/terrain set."""


def main() -> None:
    init_eval_logging()
    launcher_args = parse_isaaclab_launcher_args("Evaluate online GMVQ references with a WBT policy.")
    checkpoint_cfg, remaining = tyro.cli(CheckpointConfig, return_unknown_args=True, add_help=False)
    saved_config, saved_wandb_path = load_saved_experiment_config(checkpoint_cfg)
    runtime_cfg = tyro.cli(GMVQReferenceEvalConfig, args=remaining, config=TYRO_CONIFG)
    if runtime_cfg.motion_manifest is not None:
        terrain_term = replace(
            saved_config.terrain.terrain_term,
            motion_matched_manifest=runtime_cfg.motion_manifest,
        )
        saved_config = replace(
            saved_config,
            terrain=replace(saved_config.terrain, terrain_term=terrain_term),
        )
    evaluation = replace(saved_config.evaluation, max_steps=int(runtime_cfg.max_steps))
    config = replace(
        saved_config,
        command=make_gmvq_wbt_command(
            bundle=runtime_cfg.bundle,
            bootstrap_motion=runtime_cfg.bootstrap_motion,
            tracking_gate_m=float(runtime_cfg.tracking_gate_m),
            boundary_record_path=runtime_cfg.boundary_record,
        ),
    ).get_eval_config(evaluation)
    config = replace(config, training=replace(config.training, num_envs=int(runtime_cfg.parallel_envs)))
    config = sync_launcher_headless_config(config, launcher_args)
    run_eval_with_tyro(
        config,
        checkpoint_cfg,
        saved_config,
        saved_wandb_path,
        evaluation=evaluation,
        launcher_args=launcher_args,
    )


if __name__ == "__main__":
    main()
