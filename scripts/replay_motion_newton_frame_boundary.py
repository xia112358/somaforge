#!/usr/bin/env python3
"""Calculate contact force while playing an edited trajectory in Newton.

Each 20 ms control-frame boundary is written from the command motion. Newton
then advances four continuous 5 ms substeps under torques recorded from the
source rollout. The fourth substep supplies the training-force sample.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import tyro
from holosoma.config_types.env import get_tyro_env_config
from holosoma.config_values.experiment import AnnotatedExperimentConfig
from holosoma.utils.eval_utils import init_sim_imports
from holosoma.utils.helpers import get_class
from holosoma.utils.motion_matched_config import normalize_motion_matched_config
from holosoma.utils.sim_utils import (
    close_simulation_app,
    parse_isaaclab_launcher_args,
    sync_launcher_headless_config,
)
from holosoma.utils.tyro_utils import TYRO_CONIFG
from motion_edit.contact_force.frame_boundary_replay import (
    reduce_sensor_force_parts,
    stable_contact_masks,
)
from somaforge_core.contact_schema import CONTACT_FORCE_PART_ORDER


OUTPUT_ENV = "SOMAFORGE_FRAME_BOUNDARY_REPLAY_OUTPUT"
RECORDING_ENV = "SOMAFORGE_FORCE_ROLLOUT_RECORDING"
RECORDING_ENV_ID_ENV = "SOMAFORGE_FORCE_ROLLOUT_ENV_ID"
MAX_FRAMES_ENV = "SOMAFORGE_FRAME_BOUNDARY_MAX_FRAMES"


def _root_quaternion_xyzw(qpos: np.ndarray, order: str) -> np.ndarray:
    quat = np.asarray(qpos, dtype=np.float32)[3:7]
    if order == "xyzw":
        return quat
    if order == "wxyz":
        return quat[[1, 2, 3, 0]]
    raise ValueError(f"unsupported root quaternion order: {order!r}")


def _motion_targets_from_command(env) -> dict[str, np.ndarray]:
    """Materialize the configured command motion in simulator joint order."""

    motion_command = env.command_manager.get_state("motion_command")
    motion_start = int(
        motion_command.motion.motion_start_idx[motion_command.motion_ids[0]].item()
    )
    motion_end = int(
        motion_command.motion.motion_end_idx[motion_command.motion_ids[0]].item()
    )
    frame_count = motion_end - motion_start
    qpos = np.zeros((frame_count, env.num_dof + 7), dtype=np.float32)
    qvel = np.zeros((frame_count, env.num_dof + 6), dtype=np.float32)
    for frame in range(frame_count):
        motion_command.time_steps[0] = motion_start + frame
        qpos[frame, :3] = motion_command.root_pos_w[0].detach().cpu().numpy()
        qpos[frame, 3:7] = motion_command.root_quat_w[0].detach().cpu().numpy()
        qpos[frame, 7:] = motion_command.joint_pos[0].detach().cpu().numpy()
        qvel[frame, :3] = (
            motion_command.body_lin_vel_w[0, 0].detach().cpu().numpy()
        )
        qvel[frame, 3:6] = (
            motion_command.body_ang_vel_w[0, 0].detach().cpu().numpy()
        )
        qvel[frame, 6:] = motion_command.joint_vel[0].detach().cpu().numpy()
    return {
        "joint_pos": qpos,
        "joint_vel": qvel,
        "joint_names": np.asarray(env.simulator._robot.joint_names),
    }


def _load_recording(
    path: Path,
    *,
    env_id: int,
    frame_count: int,
    robot_joint_names: list[str],
) -> tuple[dict[str, np.ndarray], dict[str, object], list[str]]:
    with np.load(path, allow_pickle=False) as recording:
        metadata = json.loads(str(recording["_metadata_json"].item()))
        recording_joint_names = [str(name) for name in metadata["dof_names"]]
        recording_sensor_names = [
            str(name) for name in metadata["contact_sensor_body_names"]
        ]
        missing = [
            name for name in robot_joint_names if name not in recording_joint_names
        ]
        if missing:
            raise ValueError(f"force rollout recording is missing joints: {missing}")
        order = np.asarray(
            [recording_joint_names.index(name) for name in robot_joint_names],
            dtype=np.int64,
        )
        if int(metadata["control_decimation"]) != 4:
            raise ValueError("production force replay requires four physics substeps")
        if int(metadata["sim_dt"] * 1000) != 5:
            raise ValueError("production force replay requires 5 ms physics steps")
        if recording["dof_pos"].shape[0] < frame_count:
            raise ValueError("force rollout recording is shorter than the command motion")
        source = {
            key: np.asarray(recording[key])[:frame_count, env_id].copy()
            for key in (
                "dof_pos",
                "dof_vel",
                "torques_substep",
                "dof_pos_substep",
                "dof_vel_substep",
                "root_pos",
                "root_quat_xyzw",
                "root_lin_vel",
                "root_ang_vel",
                "contact_sensor_forces",
            )
        }
    for key in (
        "dof_pos",
        "dof_vel",
    ):
        source[key] = source[key][:, order]
    for key in (
        "torques_substep",
        "dof_pos_substep",
        "dof_vel_substep",
    ):
        source[key] = source[key][:, :, order]
    return source, metadata, recording_sensor_names


def record_frame_boundary_replay(
    *,
    env,
    motion: dict[str, np.ndarray],
    recording_path: str | Path,
    output_path: str | Path,
    recording_env_id: int = 0,
    root_quat_order: str = "xyzw",
) -> Path:
    """Run the production frame-boundary Newton replay contract."""

    import torch

    output = Path(output_path).expanduser().resolve()
    recording = Path(recording_path).expanduser().resolve()
    if not recording.is_file():
        raise FileNotFoundError(recording)
    sim = env.simulator
    robot_joint_names = [str(name) for name in sim._robot.joint_names]
    motion_qpos = np.asarray(motion["joint_pos"], dtype=np.float32)
    motion_qvel = np.asarray(motion["joint_vel"], dtype=np.float32)
    motion_joint_names = [
        str(name) for name in np.asarray(motion["joint_names"]).reshape(-1)
    ]
    missing = [name for name in robot_joint_names if name not in motion_joint_names]
    if missing:
        raise ValueError(f"command motion is missing robot joints: {missing}")
    motion_order = np.asarray(
        [motion_joint_names.index(name) for name in robot_joint_names],
        dtype=np.int64,
    )
    if motion_qpos.ndim != 2 or motion_qpos.shape[1] != len(robot_joint_names) + 7:
        raise ValueError(f"invalid command joint_pos shape: {motion_qpos.shape}")
    if motion_qvel.shape != (
        motion_qpos.shape[0],
        len(robot_joint_names) + 6,
    ):
        raise ValueError(f"invalid command joint_vel shape: {motion_qvel.shape}")
    frame_count = motion_qpos.shape[0]
    max_frames = int(os.environ.get(MAX_FRAMES_ENV, str(frame_count)))
    frame_count = min(frame_count, max_frames)
    source, recording_metadata, recording_sensor_names = _load_recording(
        recording,
        env_id=int(recording_env_id),
        frame_count=frame_count,
        robot_joint_names=robot_joint_names,
    )
    boundary_joint_pos = motion_qpos[:frame_count, 7:][:, motion_order]
    boundary_joint_vel = motion_qvel[:frame_count, 6:][:, motion_order]
    boundary_root = np.zeros((frame_count, 13), dtype=np.float32)
    boundary_root[:, :3] = motion_qpos[:frame_count, :3]
    for frame in range(frame_count):
        boundary_root[frame, 3:7] = _root_quaternion_xyzw(
            motion_qpos[frame],
            root_quat_order,
        )
    boundary_root[:, 7:10] = motion_qvel[:frame_count, :3]
    boundary_root[:, 10:13] = motion_qvel[:frame_count, 3:6]

    env_ids = torch.zeros(1, dtype=torch.long, device=env.device)
    sensor = sim.contact_sensor
    sensor_names_value = getattr(sensor, "sensor_names", None)
    if sensor_names_value is None:
        sensor_names_value = sensor.body_names
    sensor_body_names = [str(name) for name in sensor_names_value]
    if sensor_body_names != recording_sensor_names:
        raise ValueError("recording and replay contact-sensor body orders differ")

    def write_boundary_state(frame: int) -> None:
        sim.dof_pos[env_ids] = torch.as_tensor(
            boundary_joint_pos[frame],
            dtype=sim.dof_pos.dtype,
            device=env.device,
        ).unsqueeze(0)
        sim.dof_vel[env_ids] = torch.as_tensor(
            boundary_joint_vel[frame],
            dtype=sim.dof_vel.dtype,
            device=env.device,
        ).unsqueeze(0)
        sim.robot_root_states[env_ids, :13] = torch.as_tensor(
            boundary_root[frame],
            dtype=sim.robot_root_states.dtype,
            device=env.device,
        ).unsqueeze(0)
        sim.set_actor_root_state_tensor_robots(env_ids, sim.robot_root_states)
        sim.set_dof_state_tensor_robots(env_ids, sim.dof_state)
        sim.scene.write_data_to_sim()
        sim.sim.forward()
        sim.refresh_sim_tensors()

    decimation = 4
    sim.enable_raw_rigid_contact_history(decimation)
    force = np.zeros(
        (frame_count, len(CONTACT_FORCE_PART_ORDER), 3),
        dtype=np.float32,
    )
    substep_force = np.zeros(
        (frame_count, decimation, len(CONTACT_FORCE_PART_ORDER), 3),
        dtype=np.float32,
    )
    reference_force = reduce_sensor_force_parts(
        source["contact_sensor_forces"],
        recording_sensor_names,
    ).astype(np.float32)
    replay_joint_pos = np.zeros(
        (frame_count, len(robot_joint_names)),
        dtype=np.float32,
    )
    replay_joint_vel = np.zeros_like(replay_joint_pos)
    replay_root = np.zeros((frame_count, 13), dtype=np.float32)
    frame_error = np.zeros((frame_count, 4), dtype=np.float32)
    pre_substep_error = np.zeros((frame_count, decimation, 2), dtype=np.float32)
    applied_torque = np.asarray(
        source["torques_substep"],
        dtype=np.float32,
    ).copy()
    frame_valid = np.ones(frame_count, dtype=bool)
    frame_valid[0] = False

    write_boundary_state(0)
    replay_joint_pos[0] = boundary_joint_pos[0]
    replay_joint_vel[0] = boundary_joint_vel[0]
    replay_root[0] = boundary_root[0]
    for frame in range(1, frame_count):
        write_boundary_state(frame - 1)
        for substep in range(decimation):
            recorded_q = torch.as_tensor(
                source["dof_pos_substep"][frame, substep],
                device=env.device,
            )
            recorded_qd = torch.as_tensor(
                source["dof_vel_substep"][frame, substep],
                device=env.device,
            )
            pre_substep_error[frame, substep, 0] = torch.linalg.vector_norm(
                sim.dof_pos[0] - recorded_q
            ).item()
            pre_substep_error[frame, substep, 1] = torch.linalg.vector_norm(
                sim.dof_vel[0] - recorded_qd
            ).item()
            torque = torch.as_tensor(
                applied_torque[frame, substep],
                dtype=sim.dof_pos.dtype,
                device=env.device,
            ).unsqueeze(0)
            sim.apply_torques_at_dof(torque)
            sim.simulate_at_each_physics_step()
            sim.refresh_sim_tensors()
            sensor_value = sensor.data.net_forces_w[0].detach().cpu().numpy()
            substep_force[frame, substep] = reduce_sensor_force_parts(
                sensor_value,
                sensor_body_names,
            )

        force[frame] = substep_force[frame, -1]
        replay_joint_pos[frame] = sim.dof_pos[0].detach().cpu().numpy()
        replay_joint_vel[frame] = sim.dof_vel[0].detach().cpu().numpy()
        replay_root[frame] = sim.robot_root_states[0].detach().cpu().numpy()
        frame_error[frame, 0] = np.linalg.norm(
            replay_joint_pos[frame] - boundary_joint_pos[frame]
        )
        frame_error[frame, 1] = np.linalg.norm(
            replay_joint_vel[frame] - boundary_joint_vel[frame]
        )
        frame_error[frame, 2] = np.linalg.norm(
            replay_root[frame, :3] - boundary_root[frame, :3]
        )
        quat_dot = abs(
            float(np.dot(replay_root[frame, 3:7], boundary_root[frame, 3:7]))
        )
        frame_error[frame, 3] = 1.0 - min(1.0, quat_dot)
        if frame % 25 == 0 or frame + 1 == frame_count:
            print(
                json.dumps(
                    {
                        "frame": frame,
                        "frames_total": frame_count,
                        "joint_position_error_norm": float(frame_error[frame, 0]),
                        "root_position_error_m": float(frame_error[frame, 2]),
                        "force_max_n": float(
                            np.linalg.norm(force[frame], axis=-1).max(initial=0.0)
                        ),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    raw_mask, stable_mask = stable_contact_masks(
        force,
        on_threshold=10.0,
        off_threshold=5.0,
        close_gap_frames=2,
    )
    payload = {
        "contact_force_part_order": np.asarray(CONTACT_FORCE_PART_ORDER),
        "contact_force_part_w": force,
        "contact_force_part_substep_w": substep_force,
        "contact_force_part_mask": stable_mask,
        "contact_force_part_mask_raw": raw_mask,
        "contact_force_frame_valid": frame_valid,
        "reference_contact_force_part_w": reference_force,
        "joint_names": np.asarray(robot_joint_names),
        "dof_pos": replay_joint_pos,
        "dof_vel": replay_joint_vel,
        "root_state_xyzw": replay_root,
        "frame_tracking_error": frame_error,
        "pre_substep_joint_tracking_error": pre_substep_error,
        "applied_torque_substep": applied_torque,
        "boundary_joint_pos": boundary_joint_pos,
        "boundary_joint_vel": boundary_joint_vel,
        "boundary_root_state_xyzw": boundary_root,
        "metadata_json": np.asarray(
            json.dumps(
                {
                    "runner": "newton_frame_boundary_force_replay",
                    "recording": str(recording),
                    "recording_env_id": int(recording_env_id),
                    "boundary_state_source": "command_motion",
                    "state_policy": "frame_boundary_playback",
                    "state_overwrite_frequency": (
                        "once_per_20ms_control_frame_before_four_5ms_substeps"
                    ),
                    "control_mode": "recorded_torques",
                    "torque_source": "recording.torques_substep",
                    "force_sampling": "latest_physics_step",
                    "frame_zero_force_valid": False,
                    "self_collisions_enabled": False,
                    "newton_solver_config": recording_metadata[
                        "newton_solver_config"
                    ],
                },
                sort_keys=True,
            )
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **payload)
    print(f"Wrote {output}", flush=True)
    return output


def main() -> None:
    output = Path(os.environ[OUTPUT_ENV]).expanduser().resolve()
    recording = Path(os.environ[RECORDING_ENV]).expanduser().resolve()
    recording_env_id = int(os.environ.get(RECORDING_ENV_ID_ENV, "0"))
    launcher_args = parse_isaaclab_launcher_args(
        "Calculate edited-motion contact force with Newton frame-boundary replay."
    )
    config = tyro.cli(AnnotatedExperimentConfig, config=TYRO_CONIFG)
    config = normalize_motion_matched_config(config)
    config = sync_launcher_headless_config(config, launcher_args)
    simulation_app = init_sim_imports(config, launcher_args=launcher_args)
    failure: BaseException | None = None
    try:
        device = str(getattr(launcher_args, "device", None) or "cuda:0")
        env = get_class(config.env_class)(get_tyro_env_config(config), device=device)
        record_frame_boundary_replay(
            env=env,
            motion=_motion_targets_from_command(env),
            recording_path=recording,
            recording_env_id=recording_env_id,
            output_path=output,
            root_quat_order="xyzw",
        )
        del env
    except BaseException as exc:
        failure = exc
    finally:
        close_simulation_app(simulation_app)
    if failure is not None:
        raise failure


if __name__ == "__main__":
    main()
