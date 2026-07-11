from __future__ import annotations

import argparse
import dataclasses
import os
from pathlib import Path

import tyro
from loguru import logger

from holosoma.agents.base_algo.base_algo import BaseAlgo
from holosoma.config_types.eval_callback import EvalCallbacksConfig
from holosoma.config_types.experiment import ExperimentConfig
from holosoma.utils.config_utils import CONFIG_NAME
from holosoma.utils.eval_utils import (
    CheckpointConfig,
    init_eval_logging,
    load_checkpoint,
    load_saved_experiment_config,
)
from holosoma.utils.experiment_paths import get_experiment_dir, get_timestamp
from holosoma.utils.helpers import get_class
from holosoma.utils.motion_matched_config import normalize_motion_matched_config
from holosoma.utils.sim_utils import (
    close_simulation_app,
    parse_isaaclab_launcher_args,
    setup_simulation_environment,
    sync_launcher_headless_config,
)
from holosoma.utils.tyro_utils import TYRO_CONIFG
from holosoma.utils.viewport_camera import prime_overview_viewport


def _acceptance_repeat_count(eval_cbs_cfg: EvalCallbacksConfig | None) -> int:
    if eval_cbs_cfg is None:
        return 1
    acceptance_cfg = eval_cbs_cfg.acceptance.config
    return max(1, int(getattr(acceptance_cfg, "repeats", 1)))


def _with_repeat_suffix(path_str: str, rep_index: int) -> str:
    if not path_str:
        return path_str
    path = Path(path_str)
    stem = path.stem
    suffix = path.suffix
    replacements = (
        ("_acceptance_summary", f"_rep{rep_index}_acceptance_summary"),
        ("_acceptance", f"_rep{rep_index}_acceptance"),
        ("_fail", f"_rep{rep_index}_fail"),
    )
    for old, new in replacements:
        if stem.endswith(old):
            return str(path.with_name(f"{stem[: -len(old)]}{new}{suffix}"))
    return str(path.with_name(f"{stem}_rep{rep_index}{suffix}"))


def _eval_callbacks_for_repeat(
    eval_cbs_cfg: EvalCallbacksConfig | None,
    rep_index: int,
    repeat_count: int,
) -> dict:
    if eval_cbs_cfg is None:
        return {}
    if repeat_count <= 1:
        return eval_cbs_cfg.collect_active_callbacks()

    acceptance_cb_cfg = eval_cbs_cfg.acceptance
    acceptance_cfg = acceptance_cb_cfg.config
    rep_acceptance_cfg = dataclasses.replace(
        acceptance_cfg,
        output_path=_with_repeat_suffix(acceptance_cfg.output_path, rep_index),
        summary_path=_with_repeat_suffix(acceptance_cfg.summary_path, rep_index),
        fail_output_path=_with_repeat_suffix(acceptance_cfg.fail_output_path, rep_index),
    )
    rep_acceptance_cb_cfg = dataclasses.replace(acceptance_cb_cfg, config=rep_acceptance_cfg)
    rep_eval_cbs_cfg = dataclasses.replace(eval_cbs_cfg, acceptance=rep_acceptance_cb_cfg)
    return rep_eval_cbs_cfg.collect_active_callbacks()


def run_eval_with_tyro(
    tyro_config: ExperimentConfig,
    checkpoint_cfg: CheckpointConfig,
    saved_config: ExperimentConfig,
    saved_wandb_path: str | None,
    eval_cbs_cfg: EvalCallbacksConfig | None = None,
    launcher_args: argparse.Namespace | None = None,
):
    tyro_config = normalize_motion_matched_config(tyro_config)

    # Use shared simulation environment setup
    env, device, simulation_app = setup_simulation_environment(tyro_config, launcher_args=launcher_args)
    prime_overview_viewport(env, label="Eval")

    eval_log_dir = get_experiment_dir(tyro_config.logger, tyro_config.training, get_timestamp(), task_name="eval")
    eval_log_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving eval logs to {eval_log_dir}")
    tyro_config.save_config(str(eval_log_dir / CONFIG_NAME))

    assert checkpoint_cfg.checkpoint is not None
    checkpoint = load_checkpoint(checkpoint_cfg.checkpoint, str(eval_log_dir))
    checkpoint_path = str(checkpoint)

    algo_class = get_class(tyro_config.algo._target_)
    algo: BaseAlgo = algo_class(
        device=device,
        env=env,
        config=tyro_config.algo.config,
        log_dir=str(eval_log_dir),
        multi_gpu_cfg=None,
    )
    algo.setup()
    algo.attach_checkpoint_metadata(saved_config, saved_wandb_path)
    algo.load(checkpoint_path)

    checkpoint_dir = os.path.dirname(checkpoint_path)

    exported_policy_dir_path = os.path.join(checkpoint_dir, "exported")
    os.makedirs(exported_policy_dir_path, exist_ok=True)
    exported_policy_name = checkpoint_path.split("/")[-1]  # example: model_5000.pt
    exported_onnx_name = exported_policy_name.replace(".pt", ".onnx")  # example: model_5000.onnx

    if tyro_config.training.export_onnx:
        exported_onnx_path = os.path.join(exported_policy_dir_path, exported_onnx_name)
        if not hasattr(algo, "export"):
            raise AttributeError(
                f"{algo_class.__name__} is missing an `export` method required for ONNX export during evaluation."
            )

        algo.export(onnx_file_path=exported_onnx_path)  # type: ignore[attr-defined]
        logger.info(f"Exported policy as onnx to: {exported_onnx_path}")

    repeat_count = _acceptance_repeat_count(eval_cbs_cfg)
    for rep_index in range(1, repeat_count + 1):
        cb_configs = _eval_callbacks_for_repeat(eval_cbs_cfg, rep_index, repeat_count)
        object.__setattr__(algo.config, "eval_callbacks", cb_configs or None)
        if hasattr(algo, "eval_callbacks"):
            algo.eval_callbacks.clear()
        logger.info(f"Starting eval repeat {rep_index}/{repeat_count}")
        prime_overview_viewport(env, label="Eval")
        algo.evaluate_policy(
            max_eval_steps=tyro_config.training.max_eval_steps,
        )

    # Cleanup simulation app
    if simulation_app:
        close_simulation_app(simulation_app)


def main() -> None:
    init_eval_logging()
    launcher_args = parse_isaaclab_launcher_args("Evaluate a Holosoma agent.")
    checkpoint_cfg, remaining_args = tyro.cli(CheckpointConfig, return_unknown_args=True, add_help=False)
    eval_cbs_cfg, remaining_args = tyro.cli(
        EvalCallbacksConfig, return_unknown_args=True, add_help=False, args=remaining_args
    )
    saved_cfg, saved_wandb_path = load_saved_experiment_config(checkpoint_cfg)
    eval_cfg = saved_cfg.get_eval_config()
    overwritten_tyro_config = tyro.cli(
        ExperimentConfig,
        default=eval_cfg,
        args=remaining_args,
        description="Overriding config on top of what's loaded.",
        config=TYRO_CONIFG,
    )
    overwritten_tyro_config = sync_launcher_headless_config(overwritten_tyro_config, launcher_args)
    from somaforge_core.robot_assets import validate_g1_robot_config

    validate_g1_robot_config(overwritten_tyro_config.robot)

    run_eval_with_tyro(
        overwritten_tyro_config,
        checkpoint_cfg,
        saved_cfg,
        saved_wandb_path,
        eval_cbs_cfg=eval_cbs_cfg,
        launcher_args=launcher_args,
    )


if __name__ == "__main__":
    main()
