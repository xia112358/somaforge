from dataclasses import replace

from holosoma.config_types.algo import LayerConfig
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

_CONTACT_FORCE_ROLLOUT_MANIFEST = "configs/motion_matched/climb29_z1_rollout_ref_contact_force_manifest.json"
_CLIMB00_TEACHER_CHECKPOINT = (
    "logs/WholeBodyTracking/20260607_163425-g1_29dof_wbt_failure_window_climb00_4096_20k_fixed_p50-locomotion/"
    "model_16000.pt"
)

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

_wbt_distill_algo_config = replace(
    algo.distill_ppo.config,
    module_dict=replace(
        g1_29dof_wbt.algo.config.module_dict,
        actor=replace(g1_29dof_wbt.algo.config.module_dict.actor, min_noise_std=0.05),
    ),
    num_learning_iterations=g1_29dof_wbt.algo.config.num_learning_iterations,
    num_learning_epochs=g1_29dof_wbt.algo.config.num_learning_epochs,
    num_mini_batches=g1_29dof_wbt.algo.config.num_mini_batches,
    clip_param=g1_29dof_wbt.algo.config.clip_param,
    gamma=g1_29dof_wbt.algo.config.gamma,
    lam=g1_29dof_wbt.algo.config.lam,
    value_loss_coef=g1_29dof_wbt.algo.config.value_loss_coef,
    entropy_coef=g1_29dof_wbt.algo.config.entropy_coef,
    actor_learning_rate=g1_29dof_wbt.algo.config.actor_learning_rate,
    actor_optimizer=g1_29dof_wbt.algo.config.actor_optimizer,
    critic_learning_rate=g1_29dof_wbt.algo.config.critic_learning_rate,
    critic_optimizer=g1_29dof_wbt.algo.config.critic_optimizer,
    max_grad_norm=g1_29dof_wbt.algo.config.max_grad_norm,
    schedule=g1_29dof_wbt.algo.config.schedule,
    desired_kl=g1_29dof_wbt.algo.config.desired_kl,
    use_symmetry=False,
    num_steps_per_env=g1_29dof_wbt.algo.config.num_steps_per_env,
    save_interval=g1_29dof_wbt.algo.config.save_interval,
    load_optimizer=g1_29dof_wbt.algo.config.load_optimizer,
    init_noise_std=g1_29dof_wbt.algo.config.init_noise_std,
    init_at_random_ep_len=g1_29dof_wbt.algo.config.init_at_random_ep_len,
    empirical_normalization=g1_29dof_wbt.algo.config.empirical_normalization,
    eval_callbacks=g1_29dof_wbt.algo.config.eval_callbacks,
    distill=replace(
        algo.distill_ppo.config.distill,
        enable_kl=True,
        teacher_checkpoint_path=None,
        teacher_obs_keys=("teacher_actor_obs",),
        teacher_prior_coef=0.1,
        lambda_kl_init=1.0,
        lambda_kl_final=0.1,
        lambda_kl_anneal_iters=10000,
        lambda_kl_anneal_schedule="php_parkour",
        lambda_ppo_init=None,
        lambda_ppo_final=None,
        use_mean_mse_fallback=False,
        kl_std_min=1e-4,
    ),
)

_climb00_original_terrain = replace(
    terrain.terrain_motion_matched,
    terrain_term=replace(
        terrain.terrain_motion_matched.terrain_term,
        motion_matched_manifest=command.CLIMB00_ORIGINAL_MANIFEST,
    ),
)

g1_29dof_wbt_climb00_proto_distill = replace(
    g1_29dof_wbt,
    training=replace(
        g1_29dof_wbt.training,
        name="g1_29dof_wbt_climb00_proto_distill",
    ),
    algo=replace(
        algo.distill_ppo,
        config=_wbt_distill_algo_config,
    ),
    terrain=_climb00_original_terrain,
    observation=observation.g1_29dof_wbt_php_distill_observation,
    reward=reward.g1_29dof_wbt_reward,
    termination=termination.g1_29dof_wbt_php_student_termination,
    randomization=randomization.g1_29dof_wbt_php_student_randomization,
    command=command.g1_29dof_wbt_climb00_original_command,
    simulator=replace(
        g1_29dof_wbt.simulator,
        config=replace(g1_29dof_wbt.simulator.config, scene=replace(g1_29dof_wbt.simulator.config.scene, env_spacing=0.0)),
    ),
)

_wbt_distill_kl01_origref_algo_config = replace(
    _wbt_distill_algo_config,
    distill=replace(
        _wbt_distill_algo_config.distill,
        distill_type="kl",
        teacher_prior_coef=1.0,
        lambda_kl_init=0.1,
        lambda_kl_final=0.1,
        lambda_kl_anneal_iters=0,
        lambda_kl_anneal_schedule="linear",
        lambda_ppo_init=None,
        lambda_ppo_final=None,
        use_mean_mse_fallback=False,
        dagger_valid_use_bad_tracking=True,
        dagger_bad_ref_pos_threshold=0.5,
        dagger_bad_ref_ori_threshold=0.8,
        dagger_bad_motion_body_pos_threshold=0.25,
        dagger_bad_motion_body_pos_body_names=(
            "left_ankle_roll_link",
            "right_ankle_roll_link",
            "left_wrist_yaw_link",
            "right_wrist_yaw_link",
        ),
    ),
)

g1_29dof_wbt_climb00_proto_distill_kl01_origref = replace(
    g1_29dof_wbt_climb00_proto_distill,
    training=replace(
        g1_29dof_wbt_climb00_proto_distill.training,
        name="g1_29dof_wbt_climb00_proto_distill_kl01_origref",
    ),
    algo=replace(
        algo.distill_ppo,
        config=_wbt_distill_kl01_origref_algo_config,
    ),
    terrain=_climb00_original_terrain,
    observation=observation.g1_29dof_wbt_php_distill_observation,
    reward=reward.g1_29dof_wbt_reward,
    termination=termination.g1_29dof_wbt_php_student_termination,
    randomization=randomization.g1_29dof_wbt_php_student_randomization,
    command=command.g1_29dof_wbt_climb00_original_command,
)

_wbt_php_distill_algo_config = replace(
    _wbt_distill_algo_config,
    num_learning_iterations=20000,
    num_learning_epochs=2,
    num_mini_batches=96,
    entropy_coef=0.001,
    actor_learning_rate=3e-4,
    critic_learning_rate=3e-4,
    max_actor_learning_rate=3e-4,
    max_critic_learning_rate=3e-4,
    desired_kl=0.01,
    adaptive_schedule_start_iter=1000,
    init_noise_std=g1_29dof_wbt.algo.config.init_noise_std,
    module_dict=replace(
        _wbt_distill_algo_config.module_dict,
        actor=replace(
            _wbt_distill_algo_config.module_dict.actor,
            layer_config=LayerConfig(hidden_dims=[512, 256, 128], activation="ELU"),
            min_noise_std=None,
            max_noise_std=None,
        ),
        critic=replace(
            _wbt_distill_algo_config.module_dict.critic,
            layer_config=LayerConfig(hidden_dims=[512, 256, 128], activation="ELU"),
        ),
    ),
    distill=replace(
        _wbt_distill_algo_config.distill,
        distill_type="php_dagger_ppo",
        teacher_checkpoint_path=_CLIMB00_TEACHER_CHECKPOINT,
        dagger_coef=10.0,
        lambda_dagger_init=1.0,
        lambda_dagger_final=0.1,
        lambda_ppo_init=None,
        lambda_ppo_final=None,
        teacher_prior_coef=1.0,
        lambda_kl_init=1.0,
        lambda_kl_final=0.1,
        lambda_kl_anneal_iters=10000,
        lambda_kl_anneal_schedule="php_parkour",
        use_mean_mse_fallback=True,
        teacher_hidden_dims=(512, 256, 128),
        dagger_valid_use_bad_tracking=True,
        dagger_bad_ref_pos_threshold=0.5,
        dagger_bad_ref_ori_threshold=0.8,
        dagger_bad_motion_body_pos_threshold=0.25,
        dagger_bad_motion_body_pos_body_names=(
            "left_ankle_roll_link",
            "right_ankle_roll_link",
            "left_wrist_yaw_link",
            "right_wrist_yaw_link",
        ),
    ),
)

g1_29dof_wbt_climb00_proto_php_distill = replace(
    g1_29dof_wbt_climb00_proto_distill,
    training=replace(
        g1_29dof_wbt_climb00_proto_distill.training,
        name="g1_29dof_wbt_climb00_proto_php_distill",
    ),
    algo=replace(
        algo.distill_ppo,
        config=_wbt_php_distill_algo_config,
    ),
    observation=observation.g1_29dof_wbt_php_distill_observation,
    reward=reward.g1_29dof_wbt_reward,
    termination=termination.g1_29dof_wbt_php_student_termination,
    randomization=randomization.g1_29dof_wbt_php_student_randomization,
    command=command.g1_29dof_wbt_climb00_original_command,
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
        name="g1_29dof_wbt_contact_force_6part_hotspot_multimotion",
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

_contact_force_touchdown_lift_motion_config = replace(
    _contact_force_motion_config,
    reset_sampler="hotspot_failure_window",
)

g1_29dof_wbt_contact_force_touchdown_lift = replace(
    g1_29dof_wbt_contact_force,
    training=replace(
        g1_29dof_wbt_contact_force.training,
        name="g1_29dof_wbt_contact_force_touchdown_lift_6part_hotspot_multimotion",
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
    "g1_29dof_wbt_climb00_proto_distill",
    "g1_29dof_wbt_climb00_proto_distill_kl01_origref",
    "g1_29dof_wbt_climb00_proto_php_distill",
    "g1_29dof_wbt_contact_force",
    "g1_29dof_wbt_contact_force_touchdown_lift",
    "g1_29dof_wbt_future_ref",
]

"""
Example:
python src/holosoma/holosoma/train_agent.py exp:g1-29dof-wbt
"""
