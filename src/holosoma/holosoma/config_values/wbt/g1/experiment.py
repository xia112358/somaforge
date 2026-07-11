from dataclasses import replace

from holosoma.config_types.command import CommandTermCfg
from holosoma.config_types.experiment import ExperimentConfig, NightlyConfig, TrainingConfig
from holosoma.config_values import (
    action,
    algo,
    command,
    curriculum,
    observation,
    randomization,
    reward,
    robot,
    simulator,
    termination,
    terrain,
)

_motion_matched_terrain = replace(
    terrain.terrain_motion_matched,
    terrain_term=replace(
        terrain.terrain_motion_matched.terrain_term,
        motion_matched_manifest=command.DEFAULT_MOTION_MATCHED_MANIFEST,
    ),
)

_CONTACT_FORCE_ROLLOUT_MANIFEST = "runtime/current/manifests/newton_contact_force_8part.json"

g1_29dof_wbt = ExperimentConfig(
    training=TrainingConfig(
        project="WholeBodyTracking",
        name="g1_29dof_wbt_manager",
        num_envs=4096,
    ),
    env_class="holosoma.envs.wbt.wbt_manager.WholeBodyTrackingManager",
    algo=replace(
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
            init_at_random_ep_len=True,
            empirical_normalization=True,
            use_symmetry=False,
            actor_optimizer=replace(algo.ppo.config.actor_optimizer, weight_decay=0.000),
            critic_optimizer=replace(algo.ppo.config.critic_optimizer, weight_decay=0.000),
        ),
    ),
    simulator=replace(
        simulator.isaaclab3_newton,
        config=replace(
            simulator.isaaclab3_newton.config,
            sim=replace(
                simulator.isaaclab3_newton.config.sim,
                max_episode_length_s=10.0,
            ),
        ),
    ),
    robot=replace(
        robot.g1_29dof,
        control=replace(
            robot.g1_29dof.control,
            action_scale=0.25,
            action_scales_by_effort_limit_over_p_gain=True,
        ),
        asset=replace(robot.g1_29dof.asset, enable_self_collisions=True),
        init_state=replace(robot.g1_29dof.init_state, pos=[0.0, 0.0, 0.76]),
    ),
    terrain=_motion_matched_terrain,
    observation=observation.g1_29dof_wbt_observation,
    action=action.g1_29dof_joint_pos,
    termination=termination.g1_29dof_wbt_termination,
    randomization=randomization.g1_29dof_wbt_randomization,
    command=command.g1_29dof_wbt_command,
    curriculum=curriculum.g1_29dof_wbt_curriculum,
    reward=reward.g1_29dof_wbt_reward,
    nightly=NightlyConfig(
        iterations=8000,
        metrics={
            "Episode/rew_motion_global_ref_position_error_exp": [0.3, "inf"],
            "Episode/rew_motion_global_ref_orientation_error_exp": [0.4, "inf"],
            "Episode/rew_motion_relative_body_position_error_exp": [0.85, "inf"],
            "Episode/rew_motion_relative_body_orientation_error_exp": [0.7, "inf"],
            "Episode/rew_motion_global_body_lin_vel": [0.60, "inf"],
            "Episode/rew_motion_global_body_ang_vel": [0.45, "inf"],
        },
    ),
)

g1_29dof_wbt_a2a = replace(
    g1_29dof_wbt,
    training=replace(
        g1_29dof_wbt.training,
        name="g1_29dof_wbt_a2a_manager",
    ),
    terrain=_motion_matched_terrain,
    observation=observation.g1_29dof_wbt_a2a_observation,
    reward=reward.g1_29dof_wbt_a2a_reward,
    simulator=replace(
        g1_29dof_wbt.simulator,
        config=replace(g1_29dof_wbt.simulator.config, scene=replace(g1_29dof_wbt.simulator.config.scene, env_spacing=0.0)),
    ),
)

g1_29dof_wbt_future_ref = replace(
    g1_29dof_wbt,
    training=replace(
        g1_29dof_wbt.training,
        name="g1_29dof_wbt_future_ref_manager",
    ),
    terrain=_motion_matched_terrain,
    observation=observation.g1_29dof_wbt_future_ref_observation,
    simulator=replace(
        g1_29dof_wbt.simulator,
        config=replace(g1_29dof_wbt.simulator.config, scene=replace(g1_29dof_wbt.simulator.config.scene, env_spacing=0.0)),
    ),
)

_contact_force_motion_config = replace(
    command.g1_29dof_wbt_command.setup_terms["motion_command"].params["motion_config"],
    motion_manifest=_CONTACT_FORCE_ROLLOUT_MANIFEST,
    reset_sampler="hotspot_failure_window",
)

_contact_force_terrain = replace(
    terrain.terrain_motion_matched,
    terrain_term=replace(
        terrain.terrain_motion_matched.terrain_term,
        motion_matched_manifest=_CONTACT_FORCE_ROLLOUT_MANIFEST,
    ),
)

g1_29dof_wbt_contact_force = replace(
    g1_29dof_wbt,
    training=replace(
        g1_29dof_wbt.training,
        name="g1_29dof_wbt_contact_force_8part_hotspot_multimotion",
    ),
    terrain=_contact_force_terrain,
    observation=observation.g1_29dof_wbt_contact_force_observation,
    reward=reward.g1_29dof_wbt_contact_force_reward,
    command=replace(
        command.g1_29dof_wbt_command,
        setup_terms={
            "motion_command": CommandTermCfg(
                func="holosoma.managers.command.terms.wbt:MotionCommand",
                params={"motion_config": _contact_force_motion_config},
            ),
        },
    ),
    simulator=replace(
        g1_29dof_wbt.simulator,
        config=replace(
            g1_29dof_wbt.simulator.config,
            sim=replace(g1_29dof_wbt.simulator.config.sim, max_episode_length_s=20.0),
            scene=replace(g1_29dof_wbt.simulator.config.scene, env_spacing=0.0),
        ),
    ),
)

_contact_force_zero_start_motion_config = replace(
    _contact_force_motion_config,
    reset_sampler="uniform",
    start_at_timestep_zero_prob=1.0,
    freeze_at_timestep_zero_prob=0.0,
    use_start_probe_envs=False,
    probe_env_per_motion=0,
)

g1_29dof_wbt_contact_force_zero_start = replace(
    g1_29dof_wbt_contact_force,
    training=replace(
        g1_29dof_wbt_contact_force.training,
        name="g1_29dof_wbt_contact_force_8part_zero_start_multimotion",
        export_onnx=False,
    ),
    algo=replace(
        g1_29dof_wbt_contact_force.algo,
        config=replace(
            g1_29dof_wbt_contact_force.algo.config,
            actor_learning_rate=1e-4,
            critic_learning_rate=1e-4,
            num_learning_iterations=2000,
            load_optimizer=False,
            init_at_random_ep_len=False,
            export_onnx=False,
        ),
    ),
    command=replace(
        command.g1_29dof_wbt_command,
        setup_terms={
            "motion_command": CommandTermCfg(
                func="holosoma.managers.command.terms.wbt:MotionCommand",
                params={"motion_config": _contact_force_zero_start_motion_config},
            ),
        },
    ),
)

_contact_force_touchdown_lift_motion_config = replace(
    _contact_force_motion_config,
    reset_sampler="hotspot_failure_window",
)

g1_29dof_wbt_contact_force_touchdown_lift = replace(
    g1_29dof_wbt_contact_force,
    training=replace(
        g1_29dof_wbt_contact_force.training,
        name="g1_29dof_wbt_contact_force_touchdown_lift_8part_hotspot_multimotion",
    ),
    command=replace(
        command.g1_29dof_wbt_command,
        setup_terms={
            "motion_command": CommandTermCfg(
                func="holosoma.managers.command.terms.wbt:MotionCommand",
                params={"motion_config": _contact_force_touchdown_lift_motion_config},
            ),
        },
    ),
)

g1_29dof_wbt_a2a_pure = replace(
    g1_29dof_wbt_a2a,
    training=replace(
        g1_29dof_wbt_a2a.training,
        name="g1_29dof_wbt_a2a_pure_manager",
    ),
    observation=observation.g1_29dof_wbt_a2a_pure_observation,
    termination=termination.g1_29dof_wbt_a2a_pure_termination,
)

__all__ = [
    "g1_29dof_wbt",
    "g1_29dof_wbt_a2a",
    "g1_29dof_wbt_a2a_pure",
    "g1_29dof_wbt_contact_force",
    "g1_29dof_wbt_contact_force_zero_start",
    "g1_29dof_wbt_contact_force_touchdown_lift",
    "g1_29dof_wbt_future_ref",
]

"""
Example:
python src/holosoma/holosoma/train_agent.py exp:g1-29dof-wbt
"""
