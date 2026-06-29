"""Whole Body Tracking observation presets for the G1 robot."""

from holosoma.config_types.observation import ObservationManagerCfg, ObsGroupCfg, ObsTermCfg

actor_obs_shared = ObsGroupCfg(
    concatenate=True,
    enable_noise=True,
    history_length=1,
    terms={
        "motion_command": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:motion_command",
            scale=1.0,
            noise=0.0,
        ),
        "motion_ref_joint_pos": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:motion_ref_joint_pos",
            scale=1.0,
            noise=0.01,
        ),
        "motion_ref_joint_vel": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:motion_ref_joint_vel",
            scale=1.0,
            noise=0.5,
        ),
        "motion_ref_pos_b": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:motion_ref_pos_b",
            scale=1.0,
            noise=0.25,
        ),
        "pelvis_global_pos": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:pelvis_global_pos",
            scale=1.0,
            noise=0.0,
        ),
        "pelvis_global_lin_vel": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:pelvis_global_lin_vel",
            scale=1.0,
            noise=0.0,
        ),
        "motion_ref_ori_b": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:motion_ref_ori_b",
            scale=1.0,
            noise=0.05,
        ),
        "robot_body_pos_b": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:robot_body_pos_b",
            scale=1.0,
            noise=0.0,
        ),
        "robot_body_ori_b": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:robot_body_ori_b",
            scale=1.0,
            noise=0.0,
        ),
        "base_lin_vel": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:base_lin_vel",
            scale=1.0,
            noise=0.0,
        ),
        "base_ang_vel": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:base_ang_vel",
            scale=1.0,
            noise=0.2,
        ),
        "terrain_height_scan": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:terrain_height_scan",
            scale=1.0,
            noise=0.0,
            clip=(-1.0, 1.0),
        ),
        "dof_pos": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:dof_pos",
            scale=1.0,
            noise=0.01,
        ),
        "dof_vel": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:dof_vel",
            scale=1.0,
            noise=0.5,
        ),
        "actions": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:actions",
            scale=1.0,
            noise=0.0,
        ),
    },
)

critic_obs_shared_terms = {
    "motion_command": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:motion_command",
        scale=1.0,
        noise=0.0,
    ),
    "motion_ref_joint_pos": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:motion_ref_joint_pos",
        scale=1.0,
        noise=0.01,
    ),
    "motion_ref_joint_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:motion_ref_joint_vel",
        scale=1.0,
        noise=0.5,
    ),
    "motion_ref_pos_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:motion_ref_pos_b",
        scale=1.0,
        noise=0.25,
    ),
    "pelvis_global_pos": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:pelvis_global_pos",
        scale=1.0,
        noise=0.0,
    ),
    "pelvis_global_lin_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:pelvis_global_lin_vel",
        scale=1.0,
        noise=0.0,
    ),
    "motion_ref_ori_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:motion_ref_ori_b",
        scale=1.0,
        noise=0.05,
    ),
    "robot_body_pos_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:robot_body_pos_b",
        scale=1.0,
        noise=0.0,
    ),
    "robot_body_ori_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:robot_body_ori_b",
        scale=1.0,
        noise=0.0,
    ),
    "base_lin_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:base_lin_vel",
        scale=1.0,
        noise=0.0,
    ),
    "base_ang_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:base_ang_vel",
        scale=1.0,
        noise=0.2,
    ),
    "terrain_height_scan": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:terrain_height_scan",
        scale=1.0,
        noise=0.05,
        clip=(-1.0, 1.0),
    ),
    "dof_pos": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:dof_pos",
        scale=1.0,
        noise=0.01,
    ),
    "dof_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:dof_vel",
        scale=1.0,
        noise=0.5,
    ),
    "actions": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:actions",
        scale=1.0,
        noise=0.0,
    ),
}

future_ref_terms = {
    "future_motion_ref_joint_pos": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:future_motion_ref_joint_pos",
        params={"offsets": (1, 2, 4, 8)},
        scale=1.0,
        noise=0.01,
    ),
    "future_motion_ref_pos_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:future_motion_ref_pos_b",
        params={"offsets": (1, 2, 4, 8)},
        scale=1.0,
        noise=0.25,
    ),
    "future_motion_ref_ori_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:future_motion_ref_ori_b",
        params={"offsets": (1, 2, 4, 8)},
        scale=1.0,
        noise=0.05,
    ),
}

actor_obs_future_ref_terms = {
    **actor_obs_shared.terms,
    **future_ref_terms,
}

critic_obs_future_ref_terms = {
    **critic_obs_shared_terms,
    **future_ref_terms,
}

a2a_limb_state_term = {
    "limb_state": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:limb_state",
        scale=1.0,
        noise=0.0,
    ),
}

contact_force_ref_term = {
    "contact_force_ref_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:contact_force_ref_b",
        params={"force_scale": 300.0},
        scale=1.0,
        noise=0.0,
    ),
}

actor_obs_a2a_terms = {
    **actor_obs_shared.terms,
    **a2a_limb_state_term,
}

critic_obs_a2a_terms = {
    **critic_obs_shared_terms,
    **a2a_limb_state_term,
}

actor_obs_contact_force_terms = {
    **actor_obs_shared.terms,
    **contact_force_ref_term,
}

critic_obs_contact_force_terms = {
    **critic_obs_shared_terms,
    **contact_force_ref_term,
}

pure_a2a_actor_obs_terms = {
    "a2a_root_ref": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:a2a_root_ref",
        scale=1.0,
        noise=0.0,
    ),
    "a2a_active_limb_ref": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:a2a_active_limb_ref",
        scale=1.0,
        noise=0.0,
    ),
    **a2a_limb_state_term,
    "motion_ref_ori_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:motion_ref_ori_b",
        scale=1.0,
        noise=0.05,
    ),
    "base_ang_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:base_ang_vel",
        scale=1.0,
        noise=0.2,
    ),
    "dof_pos": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:dof_pos",
        scale=1.0,
        noise=0.01,
    ),
    "dof_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:dof_vel",
        scale=1.0,
        noise=0.5,
    ),
    "actions": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:actions",
        scale=1.0,
        noise=0.0,
    ),
}

pure_a2a_critic_obs_terms = pure_a2a_actor_obs_terms

g1_29dof_wbt_observation = ObservationManagerCfg(
    groups={
        "actor_obs": actor_obs_shared,
        "critic_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=False,
            history_length=1,
            terms=critic_obs_shared_terms,
        ),
    },
)

g1_29dof_wbt_a2a_observation = ObservationManagerCfg(
    groups={
        "actor_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=True,
            history_length=1,
            terms=actor_obs_a2a_terms,
        ),
        "critic_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=False,
            history_length=1,
            terms=critic_obs_a2a_terms,
        ),
    },
)

g1_29dof_wbt_future_ref_observation = ObservationManagerCfg(
    groups={
        "actor_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=True,
            history_length=1,
            terms=actor_obs_future_ref_terms,
        ),
        "critic_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=False,
            history_length=1,
            terms=critic_obs_future_ref_terms,
        ),
    },
)

g1_29dof_wbt_contact_force_observation = ObservationManagerCfg(
    groups={
        "actor_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=True,
            history_length=1,
            terms=actor_obs_contact_force_terms,
        ),
        "critic_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=False,
            history_length=1,
            terms=critic_obs_contact_force_terms,
        ),
    },
)

g1_29dof_wbt_a2a_pure_observation = ObservationManagerCfg(
    groups={
        "actor_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=True,
            history_length=1,
            terms=pure_a2a_actor_obs_terms,
        ),
        "critic_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=False,
            history_length=1,
            terms=pure_a2a_critic_obs_terms,
        ),
    },
)

__all__ = [
    "g1_29dof_wbt_a2a_observation",
    "g1_29dof_wbt_a2a_pure_observation",
    "g1_29dof_wbt_contact_force_observation",
    "g1_29dof_wbt_future_ref_observation",
    "g1_29dof_wbt_observation",
]
