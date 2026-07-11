"""Canonical G1 whole-body tracking experiment presets."""

from dataclasses import replace

from holosoma.config_types.experiment import ExperimentConfig, NightlyConfig, TrainingConfig
from holosoma.config_values import (
    action,
    algo,
    curriculum,
    observation,
    randomization,
    reward,
    robot,
    simulator,
    termination,
    terrain,
)
from holosoma.config_values.wbt.g1 import command


def _terrain_for(manifest: str):
    return replace(
        terrain.terrain_motion_matched,
        terrain_term=replace(
            terrain.terrain_motion_matched.terrain_term,
            motion_matched_manifest=manifest,
        ),
    )


_ppo = replace(
    algo.ppo,
    config=replace(
        algo.ppo.config,
        num_learning_iterations=20000,
        num_learning_epochs=5,
        save_interval=1000,
        entropy_coef=0.005,
        init_noise_std=0.2,
        actor_learning_rate=1e-3,
        critic_learning_rate=1e-3,
        min_actor_learning_rate=None,
        min_critic_learning_rate=None,
        max_actor_learning_rate=None,
        max_critic_learning_rate=None,
        init_at_random_ep_len=True,
        empirical_normalization=True,
        use_symmetry=False,
        export_onnx=False,
        actor_optimizer=replace(algo.ppo.config.actor_optimizer, weight_decay=0.0),
        critic_optimizer=replace(algo.ppo.config.critic_optimizer, weight_decay=0.0),
    ),
)

_robot = replace(
    robot.g1_29dof,
    control=replace(
        robot.g1_29dof.control,
        action_scale=0.25,
        action_scales_by_effort_limit_over_p_gain=True,
    ),
    asset=replace(robot.g1_29dof.asset, enable_self_collisions=True),
    init_state=replace(robot.g1_29dof.init_state, pos=[0.0, 0.0, 0.76]),
)

_nightly = NightlyConfig(
    iterations=8000,
    metrics={
        "Episode/rew_motion_global_ref_position_error_exp": [0.3, "inf"],
        "Episode/rew_motion_global_ref_orientation_error_exp": [0.4, "inf"],
        "Episode/rew_motion_relative_body_position_error_exp": [0.85, "inf"],
        "Episode/rew_motion_relative_body_orientation_error_exp": [0.7, "inf"],
        "Episode/rew_motion_global_body_lin_vel": [0.60, "inf"],
        "Episode/rew_motion_global_body_ang_vel": [0.45, "inf"],
    },
)

g1_29dof_wbt_baseline_29 = ExperimentConfig(
    training=TrainingConfig(
        project="WholeBodyTracking",
        name="g1_29dof_wbt_baseline_29_hotspot",
        num_envs=4096,
        export_onnx=False,
    ),
    env_class="holosoma.envs.wbt.wbt_manager.WholeBodyTrackingManager",
    algo=_ppo,
    simulator=replace(
        simulator.isaaclab3_newton,
        config=replace(
            simulator.isaaclab3_newton.config,
            sim=replace(simulator.isaaclab3_newton.config.sim, max_episode_length_s=10.0),
        ),
    ),
    robot=_robot,
    terrain=_terrain_for(command.BASELINE_29_MANIFEST),
    observation=observation.g1_29dof_wbt_observation,
    action=action.g1_29dof_joint_pos,
    termination=termination.g1_29dof_wbt_termination,
    randomization=randomization.g1_29dof_wbt_randomization,
    command=command.g1_29dof_wbt_baseline_29_command,
    curriculum=curriculum.g1_29dof_wbt_curriculum,
    reward=reward.g1_29dof_wbt_reward,
    nightly=_nightly,
)

g1_29dof_wbt_baseline_single = replace(
    g1_29dof_wbt_baseline_29,
    training=replace(
        g1_29dof_wbt_baseline_29.training,
        name="g1_29dof_wbt_baseline_single_hotspot",
    ),
    terrain=_terrain_for(command.BASELINE_SINGLE_MANIFEST),
    command=command.g1_29dof_wbt_baseline_single_command,
    simulator=replace(
        g1_29dof_wbt_baseline_29.simulator,
        config=replace(
            g1_29dof_wbt_baseline_29.simulator.config,
            sim=replace(g1_29dof_wbt_baseline_29.simulator.config.sim, max_episode_length_s=22.0),
        ),
    ),
)

g1_29dof_wbt_contact_force = replace(
    g1_29dof_wbt_baseline_29,
    training=replace(
        g1_29dof_wbt_baseline_29.training,
        name="g1_29dof_wbt_contact_force_8part_hotspot",
    ),
    terrain=_terrain_for(command.CONTACT_FORCE_MANIFEST),
    observation=observation.g1_29dof_wbt_contact_force_observation,
    reward=reward.g1_29dof_wbt_contact_force_reward,
    command=command.g1_29dof_wbt_contact_force_command,
    simulator=replace(
        g1_29dof_wbt_baseline_29.simulator,
        config=replace(
            g1_29dof_wbt_baseline_29.simulator.config,
            sim=replace(g1_29dof_wbt_baseline_29.simulator.config.sim, max_episode_length_s=20.0),
            scene=replace(g1_29dof_wbt_baseline_29.simulator.config.scene, env_spacing=0.0),
        ),
    ),
)

__all__ = [
    "g1_29dof_wbt_baseline_29",
    "g1_29dof_wbt_baseline_single",
    "g1_29dof_wbt_contact_force",
]
