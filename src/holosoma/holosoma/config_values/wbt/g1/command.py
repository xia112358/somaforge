"""Whole Body Tracking command presets for the G1 robot."""

import dataclasses

from holosoma.config_types.command import CommandManagerCfg, CommandTermCfg, MotionConfig, NoiseToInitialPoseConfig

DEFAULT_MOTION_MATCHED_MANIFEST = "runtime/current/manifests/motion_edit_ref_v1.json"
CLIMB00_ORIGINAL_MANIFEST = "runtime/current/manifests/climb00_motion_edit_ref.json"
CLIMB00_PROTO_SPLIT_MANIFEST = "runtime/current/manifests/climb00_proto_split_ref.json"

init_pose_config = NoiseToInitialPoseConfig(
    overall_noise_scale=1.0,
    dof_pos=0.1,
    root_pos=[0.05, 0.05, 0.01],
    root_rot=[0.1, 0.1, 0.2],
    root_lin_vel=[0.5, 0.5, 0.2],
    root_ang_vel=[0.52, 0.52, 0.78],
    object_pos=[0.05, 0.05, 0.0],
)

motion_config = MotionConfig(
    motion_file="",
    motion_manifest=DEFAULT_MOTION_MATCHED_MANIFEST,
    body_names_to_track=[
        "pelvis",
        "left_hip_roll_link",
        "left_knee_link",
        "left_ankle_roll_link",
        "right_hip_roll_link",
        "right_knee_link",
        "right_ankle_roll_link",
        "torso_link",
        "left_shoulder_roll_link",
        "left_elbow_link",
        "left_wrist_yaw_link",
        "right_shoulder_roll_link",
        "right_elbow_link",
        "right_wrist_yaw_link",
    ],
    body_name_ref=["torso_link"],
    reset_sampler="adaptive",
    noise_to_initial_pose=init_pose_config,
)

g1_29dof_wbt_command = CommandManagerCfg(
    params={},
    setup_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
            params={
                "motion_config": motion_config,
            },
        ),
    },
    reset_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
        )
    },
    step_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
        )
    },
)

climb00_proto_motion_config = dataclasses.replace(
    motion_config,
    motion_manifest=CLIMB00_PROTO_SPLIT_MANIFEST,
    reset_sampler="proto_adaptive",
    use_start_probe_envs=False,
    chain_motion_segments=True,
    require_chain_boundary_success=True,
    chain_gate_before_transition=True,
    chain_boundary_tracking_threshold=0.0,
    chain_boundary_contact_threshold=10.0,
)

climb00_original_motion_config = dataclasses.replace(
    motion_config,
    motion_manifest=CLIMB00_ORIGINAL_MANIFEST,
    reset_sampler="uniform",
    use_start_probe_envs=False,
    chain_motion_segments=False,
    require_chain_boundary_success=False,
    chain_gate_before_transition=False,
)

g1_29dof_wbt_climb00_proto_command = CommandManagerCfg(
    params={},
    setup_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
            params={
                "motion_config": climb00_proto_motion_config,
            },
        ),
    },
    reset_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
        )
    },
    step_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
        )
    },
)

g1_29dof_wbt_climb00_original_command = CommandManagerCfg(
    params={},
    setup_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
            params={
                "motion_config": climb00_original_motion_config,
            },
        ),
    },
    reset_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
        )
    },
    step_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
        )
    },
)

__all__ = [
    "CLIMB00_ORIGINAL_MANIFEST",
    "CLIMB00_PROTO_SPLIT_MANIFEST",
    "DEFAULT_MOTION_MATCHED_MANIFEST",
    "g1_29dof_wbt_climb00_original_command",
    "g1_29dof_wbt_climb00_proto_command",
    "g1_29dof_wbt_command",
]
