from __future__ import annotations

import dataclasses
import datetime
import json
from datetime import timezone

import holosoma.config_values.action
import holosoma.config_values.algo
import holosoma.config_values.command
import holosoma.config_values.curriculum
import holosoma.config_values.logger
import holosoma.config_values.observation
import holosoma.config_values.randomization
import holosoma.config_values.reward
import holosoma.config_values.robot
import holosoma.config_values.simulator
import holosoma.config_values.termination
import holosoma.config_values.terrain
import tyro
import yaml
from holosoma.config_types.action import ActionManagerCfg
from holosoma.config_types.algo import AlgoConfig
from holosoma.config_types.command import CommandManagerCfg
from holosoma.config_types.curriculum import CurriculumManagerCfg
from holosoma.config_types.eval_callback import EvaluationConfig
from holosoma.config_types.logger import LoggerConfig
from holosoma.config_types.observation import ObservationManagerCfg
from holosoma.config_types.randomization import RandomizationManagerCfg
from holosoma.config_types.reward import RewardManagerCfg
from holosoma.config_types.robot import RobotConfig
from holosoma.config_types.simulator import SimulatorConfig
from holosoma.config_types.termination import TerminationManagerCfg
from holosoma.config_types.terrain import TerrainManagerCfg
from pydantic.dataclasses import dataclass
from typing_extensions import Annotated


def now_timestamp() -> str:
    return datetime.datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


@dataclass(frozen=True)
class NightlyConfig:
    iterations: int
    metrics: dict[str, list[float | str]]


@dataclass(frozen=True)
class TrainingConfig:
    """Configuration for training execution and evaluation."""

    # Simulation settings
    headless: Annotated[bool, tyro.conf.Suppress] = True
    """Resolved Kit runtime mode. Select visualizers with AppLauncher ``--visualizer``."""

    torch_deterministic: bool = False
    """Enable PyTorch deterministic mode."""

    multigpu: bool = False
    """Enable multi-GPU training."""

    # Environment settings
    num_envs: int = 4096
    """Number of parallel environments."""

    seed: int = 42
    """Random seed for reproducibility."""

    # Checkpoint settings
    checkpoint: str | None = None
    """Path to checkpoint for resuming training."""

    # Logging settings
    project: str = "default_project"
    """Project name for logging. `logger.project` takes precedence if set."""

    name: str = "run"
    """Run name for logging. `logger.name` takes precedence if set."""


@dataclass(frozen=True)
class ExperimentConfig:
    """Top-level experiment configuration used by the Tyro CLI."""

    env_class: str = "holosoma.envs.wbt.wbt_manager.WholeBodyTrackingManager"

    training: TrainingConfig = TrainingConfig()
    algo: Annotated[
        AlgoConfig,
        tyro.conf.arg(constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.algo.DEFAULTS)),
    ] = holosoma.config_values.algo.ppo
    simulator: Annotated[
        SimulatorConfig,
        tyro.conf.arg(constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.simulator.DEFAULTS)),
    ] = holosoma.config_values.simulator.isaaclab3_newton
    terrain: Annotated[
        TerrainManagerCfg,
        tyro.conf.arg(constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.terrain.DEFAULTS)),
    ] = holosoma.config_values.terrain.terrain_motion_matched
    observation: Annotated[
        ObservationManagerCfg | None,
        tyro.conf.arg(
            constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.observation.DEFAULTS)
        ),
    ] = holosoma.config_values.observation.none
    action: Annotated[
        ActionManagerCfg | None,
        tyro.conf.arg(constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.action.DEFAULTS)),
    ] = holosoma.config_values.action.none
    reward: Annotated[
        RewardManagerCfg | None,
        tyro.conf.arg(constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.reward.DEFAULTS)),
    ] = holosoma.config_values.reward.none
    termination: Annotated[
        TerminationManagerCfg | None,
        tyro.conf.arg(
            constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.termination.DEFAULTS)
        ),
    ] = holosoma.config_values.termination.none
    randomization: Annotated[
        RandomizationManagerCfg | None,
        tyro.conf.arg(
            constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.randomization.DEFAULTS)
        ),
    ] = holosoma.config_values.randomization.none
    command: Annotated[
        CommandManagerCfg | None,
        tyro.conf.arg(constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.command.DEFAULTS)),
    ] = holosoma.config_values.command.none
    curriculum: Annotated[
        CurriculumManagerCfg | None,
        tyro.conf.arg(
            constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.curriculum.DEFAULTS)
        ),
    ] = holosoma.config_values.curriculum.none
    robot: Annotated[
        RobotConfig,
        tyro.conf.arg(constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.robot.DEFAULTS)),
    ] = holosoma.config_values.robot.g1_29dof
    logger: Annotated[
        LoggerConfig,
        tyro.conf.arg(constructor=tyro.extras.subcommand_type_from_defaults(holosoma.config_values.logger.DEFAULTS)),
    ] = holosoma.config_values.logger.disabled
    nightly: NightlyConfig | None = None

    evaluation: Annotated[EvaluationConfig, tyro.conf.Suppress] = EvaluationConfig()

    def get_nightly_config(self) -> ExperimentConfig:
        if self.nightly is None:
            raise ValueError("nightly config is missing.")

        return dataclasses.replace(
            self,
            algo=dataclasses.replace(
                self.algo,
                config=dataclasses.replace(  # type: ignore[arg-type]
                    self.algo.config,
                    num_learning_iterations=self.nightly.iterations,
                ),
            ),
        )

    def get_eval_config(self, evaluation: EvaluationConfig | None = None) -> ExperimentConfig:
        """Build the simulator/algo config for a resolved evaluation request."""

        evaluation = evaluation or self.evaluation
        eval_spawn_cfg = dataclasses.replace(
            self.terrain.terrain_term.spawn,
            randomize_tiles=evaluation.randomize_tiles,
            xy_offset_range=evaluation.xy_offset_range,
        )
        eval_logger = dataclasses.replace(
            holosoma.config_values.logger.disabled,
            base_dir=self.logger.base_dir,
            video=evaluation.video,
            headless_recording=False,
        )

        return dataclasses.replace(
            self,
            evaluation=evaluation,
            terrain=dataclasses.replace(
                self.terrain,
                terrain_term=dataclasses.replace(
                    self.terrain.terrain_term,
                    spawn=eval_spawn_cfg,
                ),
            ),
            simulator=dataclasses.replace(
                self.simulator,
                config=dataclasses.replace(
                    self.simulator.config,
                    sim=dataclasses.replace(
                        self.simulator.config.sim,
                        max_episode_length_s=evaluation.max_episode_length_s,
                    ),
                ),
            ),
            training=dataclasses.replace(
                self.training,
                num_envs=evaluation.num_envs,
            ),
            logger=eval_logger,
        )

    def save_config(self, path: str) -> None:
        with open(path, "w") as file:
            yaml.safe_dump(self.to_serializable_dict(), file)

    def to_serializable_dict(self) -> dict:
        """Return a JSON-friendly representation of the config."""
        # Directly using yaml.safe_dump does not handle string enums properly,
        # so round-trip through JSON to coerce typing objects into primitives.
        return json.loads(json.dumps(dataclasses.asdict(self)))
