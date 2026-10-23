"""Independent ACP stage-1/2 entrypoint; AppLauncher arguments are parsed first."""
from __future__ import annotations

from dataclasses import dataclass, replace

import tyro


@dataclass(frozen=True)
class Options:
    manifest: str
    stage: int = 1
    num_envs: int = 64
    iterations: int = 1000
    checkpoint: str | None = None
    output: str = "runtime/current/models/acp"
    name: str = "climb00"
    save_interval: int = 100
    input_start: int = 2000
    reward_start: int = 4000
    anneal_steps: int = 2000
    planner_batch: int = 4096
    minimum_replay: int = 1000
    replay_capacity: int = 100_000
    record_envs: int = 64
    observation_noise: bool = True


def build_config(options):
    from holosoma.config_types.algo import LayerConfig
    from holosoma.config_types.command import CommandTermCfg
    from holosoma.config_types.observation import ObservationManagerCfg, ObsGroupCfg, ObsTermCfg
    from holosoma.config_types.reward import RewardManagerCfg, RewardTermCfg
    from holosoma.config_types.termination import TerminationManagerCfg, TerminationTermCfg
    from holosoma.config_values.wbt.g1.command import make_wbt_command
    from holosoma.config_values.wbt.g1.experiment import g1_29dof_wbt_baseline_29 as base

    if options.stage not in (1, 2):
        raise ValueError("This entrypoint implements contact tracking and joint contact planning (stages 1/2)")
    if options.stage == 2 and options.checkpoint is None:
        raise ValueError("Stage 2 must start from an ACP stage-1/2 controller checkpoint")
    if options.num_envs < 1 or options.iterations < 1 or options.reward_start <= options.input_start:
        raise ValueError("Invalid ACP environment count, iteration count or annealing order")
    if min(options.anneal_steps, options.planner_batch, options.minimum_replay,
           options.replay_capacity, options.record_envs, options.save_interval) < 1:
        raise ValueError("ACP schedule, replay, batch and checkpoint sizes must be positive")
    command = make_wbt_command(options.manifest, reset_sampler="uniform", use_start_probe_envs=False)
    settings = {key: getattr(options, key) for key in ("stage", "input_start", "reward_start", "anneal_steps",
        "planner_batch", "minimum_replay", "replay_capacity", "record_envs", "observation_noise")}
    source = command.setup_terms["motion_command"]
    command = replace(command,
        setup_terms={"motion_command": replace(source, func="holosoma.acp.command:ACPCommand",
                                               params={**source.params, "acp": settings})},
        reset_terms={"motion_command": CommandTermCfg(func="holosoma.acp.command:ACPCommand")},
        step_terms={"motion_command": CommandTermCfg(func="holosoma.acp.command:ACPCommand")})
    actor = {
        "00_history": ObsTermCfg(func="holosoma.acp.observations:history_observation"),
        "01_goal": ObsTermCfg(func="holosoma.acp.observations:goal"),
        "02_scan": ObsTermCfg(func="holosoma.acp.observations:tracker_scan"),
        "03_contacts": ObsTermCfg(func="holosoma.acp.observations:actor_contacts")}
    observations = ObservationManagerCfg(groups={
        "actor_obs": ObsGroupCfg(terms=actor, concatenate=True, enable_noise=False),
        "critic_obs": ObsGroupCfg(terms={
            "privileged": ObsTermCfg(func="holosoma.acp.observations:critic_observation")},
            concatenate=True, enable_noise=False)})
    rewards = RewardManagerCfg(terms={
        "acp_task": RewardTermCfg(func="holosoma.acp.rewards:task", weight=1),
        "action_rate": RewardTermCfg(func="holosoma.managers.reward.terms.wbt:penalty_action_rate", weight=-0.1),
        "action_jerk": RewardTermCfg(func="holosoma.acp.rewards:action_jerk", weight=-0.05),
        "torque": RewardTermCfg(func="holosoma.managers.reward.terms.wbt:penalty_torque", weight=-1e-5),
        "limits": RewardTermCfg(func="holosoma.managers.reward.terms.wbt:limits_dof_pos",
                                params={"soft_dof_pos_limit": 0.9}, weight=-10)})
    termination = TerminationManagerCfg(terms={
        "timeout": base.termination.terms["timeout"],
        "bad_tracking": replace(base.termination.terms["bad_tracking"], params={
            **base.termination.terms["bad_tracking"].params, "bad_ref_pos_threshold": 0.5,
            "bad_ref_ori_threshold": 0.8, "bad_motion_body_pos_threshold": 0.3}),
        "motion_ends": TerminationTermCfg(func="holosoma.acp.env:reference_complete", is_timeout=True)})
    algo = replace(base.algo, _target_="holosoma.acp.ppo.ACPPPO", config=replace(base.algo.config,
        num_learning_iterations=options.iterations, num_mini_batches=8, num_learning_epochs=5,
        num_steps_per_env=24, save_interval=options.save_interval,
        actor_learning_rate=1e-4, critic_learning_rate=1e-4,
        desired_kl=0.02 if options.stage == 1 else 0.01,
        entropy_coef=0.006 if options.stage == 1 else 0.005,
        init_at_random_ep_len=False, empirical_normalization=True, use_symmetry=False,
        actor_optimizer=replace(base.algo.config.actor_optimizer, _target_="torch.optim.Adam", weight_decay=0),
        critic_optimizer=replace(base.algo.config.critic_optimizer, _target_="torch.optim.Adam", weight_decay=0),
        module_dict=replace(base.algo.config.module_dict,
            actor=replace(base.algo.config.module_dict.actor, input_dim=["actor_obs"],
                          layer_config=LayerConfig(hidden_dims=[512, 256, 128], activation="ELU")),
            critic=replace(base.algo.config.module_dict.critic, input_dim=["critic_obs"]))))
    return replace(base, env_class="holosoma.acp.env.ACPEnvironment", algo=algo,
        training=replace(base.training, project="ACP", name=f"{options.name}_stage{options.stage}",
                         num_envs=options.num_envs, checkpoint=options.checkpoint),
        logger=replace(base.logger, base_dir=options.output), command=command, observation=observations,
        reward=rewards, termination=termination,
        robot=replace(base.robot, control=replace(base.robot.control,
            action_scale=0.25, action_scales_by_effort_limit_over_p_gain=False)),
        simulator=replace(base.simulator, config=replace(base.simulator.config,
            sim=replace(base.simulator.config.sim, max_episode_length_s=25))),
        terrain=replace(base.terrain, terrain_term=replace(base.terrain.terrain_term,
            motion_matched_manifest=options.manifest)), nightly=None)


def main():
    from holosoma.utils.sim_utils import parse_isaaclab_launcher_args, sync_launcher_headless_config
    launcher = parse_isaaclab_launcher_args("Train ACP on canonical SomaForge assets")
    options = tyro.cli(Options)
    config = sync_launcher_headless_config(build_config(options), launcher)
    from holosoma.train_agent import train
    train(config, launcher_args=launcher)


if __name__ == "__main__":
    main()
