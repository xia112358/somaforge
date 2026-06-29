"""Eval callback that records per-step trajectory data to an NPZ file.

Records joint positions, velocities, torques, body poses, and root state
for later visualization with viser_eval_viewer.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from holosoma.agents.callbacks.base_callback import RLEvalCallback
from holosoma.config_types.eval_callback import RecordingConfig
from holosoma.utils.safe_torch_import import torch


class EvalRecordingCallback(RLEvalCallback):
    """Records per-step data during evaluation and saves to .npz on completion."""

    def __init__(
        self,
        config: RecordingConfig,
        training_loop: Any = None,
    ):
        super().__init__(config, training_loop)
        self.env_id = config.env_id

        output_path = config.output_path
        if not output_path.endswith(".npz"):
            output_path += ".npz"
        if training_loop is not None and hasattr(training_loop, "log_dir"):
            output_path = str(Path(training_loop.log_dir) / output_path)
        self.output_path = output_path

        self._buffers: dict[str, list[np.ndarray]] = {}
        self._metadata: dict[str, Any] = {}
        self._step_count = 0
        self._initial_state_recorded = False
        self._bootstrap_state_recorded = False
        self._stopped_after_done = False

    def _get_env(self):
        """Get the unwrapped BaseTask environment."""
        return self.training_loop._unwrap_env()

    def _save(self) -> None:
        """Save recorded data to NPZ."""
        if self._step_count == 0:
            return

        arrays: dict[str, np.ndarray] = {}
        for name, values in self._buffers.items():
            if values:
                arrays[name] = np.stack(values, axis=0)

        arrays["_metadata_json"] = np.array(json.dumps(self._metadata))

        path = Path(self.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(str(path), **arrays)

        channel_summary = ", ".join(
            f"{name}{list(arr.shape)}" for name, arr in arrays.items() if name != "_metadata_json"
        )
        logger.info(f"EvalRecordingCallback: saved {self._step_count} steps to {path}\n  Channels: {channel_summary}")

    def on_pre_evaluate_policy(self) -> None:
        env = self._get_env()
        sim = env.simulator

        self._metadata["dt"] = float(env.dt)
        self._metadata["fps"] = round(1.0 / float(env.dt))
        self._metadata["sim_dt"] = float(env.sim_dt)
        self._metadata["sim_fps"] = round(1.0 / float(env.sim_dt))
        self._metadata["control_decimation"] = env.simulator.simulator_config.sim.control_decimation
        self._metadata["env_id"] = self.env_id
        self._metadata["num_envs"] = int(env.num_envs)
        if self.env_id < 0:
            self._metadata["env_done_steps"] = [None for _ in range(env.num_envs)]
            self._metadata["env_done_is_timeout"] = [False for _ in range(env.num_envs)]
            self._metadata["env_done_terms"] = [[] for _ in range(env.num_envs)]
        if hasattr(sim, "dof_names"):
            self._metadata["dof_names"] = list(sim.dof_names)
        if hasattr(sim, "body_names"):
            self._metadata["body_names"] = list(sim.body_names)
        try:
            from isaaclab_newton.physics.newton_manager import NewtonManager

            model = getattr(NewtonManager, "_model", None)
            if model is not None:
                self._metadata["newton_body_labels"] = [str(x) for x in getattr(model, "body_label", [])]
                self._metadata["newton_shape_labels"] = [str(x) for x in getattr(model, "shape_label", [])]
                shape_body = getattr(model, "shape_body", None)
                if shape_body is not None:
                    self._metadata["newton_shape_body"] = np.asarray(shape_body.numpy(), dtype=np.int32).tolist()
        except Exception as exc:
            logger.debug(f"EvalRecordingCallback: Newton contact metadata unavailable: {exc}")

        # Static robot properties
        robot_cfg = env.robot_config
        self._metadata["effort_limits"] = list(robot_cfg.dof_effort_limit_list)
        self._metadata["dof_pos_lower_limits"] = list(robot_cfg.dof_pos_lower_limit_list)
        self._metadata["dof_pos_upper_limits"] = list(robot_cfg.dof_pos_upper_limit_list)
        self._metadata["velocity_limits"] = list(robot_cfg.dof_vel_limit_list)
        asset_cfg = robot_cfg.asset
        self._metadata["urdf_path"] = str(Path(asset_cfg.asset_root) / asset_cfg.urdf_file)

        channel_names = [
            "dof_pos_target",
            "dof_pos",
            "dof_vel",
            "torques",
            "torques_substep",
            "dof_pos_substep",
            "dof_vel_substep",
            "actions",
            "root_pos",
            "root_quat_xyzw",
            "root_lin_vel",
            "root_ang_vel",
            "body_pos_w",
            "body_quat_xyzw",
            "body_lin_vel_w",
            "body_ang_vel_w",
            "contact_forces",
            "contact_forces_history",
            "raw_contact_count",
            "raw_contact_shape0",
            "raw_contact_shape1",
            "raw_contact_body0",
            "raw_contact_body1",
            "raw_contact_point0_w",
            "raw_contact_point1_w",
            "raw_contact_normal_w",
            "raw_contact_force_w",
            "motion_id",
            "motion_time_step",
            "terminated",
            "timeout",
            "commanded_velocity",
        ]
        for name in channel_names:
            self._buffers[name] = []

        logger.info(f"EvalRecordingCallback: recording env_id={self.env_id}, output={self.output_path}")

    def on_pre_eval_env_step(self, actor_state: dict) -> dict:
        return actor_state

    def on_pre_eval_reset_bootstrap(self, actor_state: dict) -> dict:
        if self.env_id >= 0 and self._stopped_after_done:
            return actor_state
        if self.config.record_initial_state and not self._initial_state_recorded:
            self._record_step(actor_state)
            self._initial_state_recorded = True
        return actor_state

    def on_post_eval_reset(self, actor_state: dict) -> dict:
        if self.env_id >= 0 and self._stopped_after_done:
            return actor_state
        if not self.config.record_initial_state:
            return actor_state
        if not self._initial_state_recorded:
            self._record_step(actor_state)
            self._initial_state_recorded = True
            return actor_state
        if not self._bootstrap_state_recorded:
            self._record_step(actor_state)
            self._bootstrap_state_recorded = True
        return actor_state

    def on_post_eval_env_step(self, actor_state: dict) -> dict:
        self._current_actor_state = actor_state
        if self.env_id < 0:
            self._update_all_env_done_metadata(actor_state)
            if self._all_envs_done():
                self._stopped_after_done = True
                return actor_state
            self._record_step(actor_state)
            return actor_state
        if self._stopped_after_done:
            return actor_state
        if self._actor_state_done(actor_state):
            self._metadata["episode_done"] = True
            self._metadata["done_step"] = int(self._step_count)
            self._metadata["done_is_timeout"] = self._actor_state_timeout(actor_state)
            self._metadata["done_terms"] = self._active_done_terms()
            self._stopped_after_done = True
            return actor_state
        self._record_step(actor_state)
        return actor_state

    def _update_all_env_done_metadata(self, actor_state: dict) -> None:
        dones = actor_state.get("dones")
        if dones is None:
            return
        try:
            done_values = dones.detach().cpu().numpy().astype(bool).reshape(-1)
        except AttributeError:
            done_values = np.asarray(dones, dtype=bool).reshape(-1)
        done_steps = self._metadata.setdefault("env_done_steps", [None for _ in range(done_values.size)])
        done_timeouts = self._metadata.setdefault("env_done_is_timeout", [False for _ in range(done_values.size)])
        done_terms = self._metadata.setdefault("env_done_terms", [[] for _ in range(done_values.size)])
        for env_id, is_done in enumerate(done_values.tolist()):
            if not is_done or done_steps[env_id] is not None:
                continue
            done_steps[env_id] = int(self._step_count)
            done_timeouts[env_id] = self._actor_state_timeout_for_env(actor_state, env_id)
            done_terms[env_id] = self._active_done_terms_for_env(env_id)

    def _all_envs_done(self) -> bool:
        done_steps = self._metadata.get("env_done_steps")
        return isinstance(done_steps, list) and bool(done_steps) and all(step is not None for step in done_steps)

    def _actor_state_done(self, actor_state: dict) -> bool:
        dones = actor_state.get("dones")
        if dones is None:
            return False
        try:
            return bool(dones[self.env_id].detach().cpu().item())
        except (AttributeError, IndexError, TypeError):
            return bool(dones[self.env_id])

    def _actor_state_timeout(self, actor_state: dict) -> bool:
        return self._actor_state_timeout_for_env(actor_state, self.env_id)

    def _actor_state_timeout_for_env(self, actor_state: dict, env_id: int) -> bool:
        extras = actor_state.get("extras")
        if not isinstance(extras, dict):
            return False
        time_outs = extras.get("time_outs")
        if time_outs is None:
            return False
        try:
            return bool(time_outs[env_id].detach().cpu().item())
        except (AttributeError, IndexError, TypeError):
            return bool(time_outs[env_id])

    def _active_done_terms(self) -> list[str]:
        return self._active_done_terms_for_env(self.env_id)

    def _active_done_terms_for_env(self, env_id: int) -> list[str]:
        actor_state = getattr(self, "_current_actor_state", None)
        if isinstance(actor_state, dict):
            extras = actor_state.get("extras")
            if isinstance(extras, dict):
                active_terms = self._active_done_terms_from_mapping(extras.get("term_dones"), env_id)
                if active_terms:
                    return active_terms

        env = self._get_env()
        termination_manager = getattr(env, "termination_manager", None)
        term_dones = getattr(termination_manager, "term_dones", None)
        return self._active_done_terms_from_mapping(term_dones, env_id)

    def _active_done_terms_from_mapping(self, term_dones: Any, env_id: int) -> list[str]:
        if not isinstance(term_dones, dict):
            return []
        active_terms: list[str] = []
        for name, values in term_dones.items():
            try:
                is_active = bool(values[env_id].detach().cpu().item())
            except (AttributeError, IndexError, TypeError):
                is_active = bool(values[env_id])
            if is_active:
                active_terms.append(str(name))
        return active_terms

    def _record_step(self, actor_state: dict) -> None:
        env = self._get_env()
        sim = env.simulator
        eid = slice(None) if self.env_id < 0 else self.env_id

        def _to_np(t: torch.Tensor) -> np.ndarray:
            return t.detach().cpu().numpy().copy()

        self._buffers["dof_pos"].append(_to_np(sim.dof_pos[eid]))  # post_eval_env_step, so after 4 decimation
        self._buffers["dof_vel"].append(_to_np(sim.dof_vel[eid]))
        self._buffers["torques"].append(
            _to_np(self._extract_torques(env, eid))
        )  # pre_eval_env_step, so the torques is the last decimation

        # robot_root_states: [num_envs, 13] = pos(3), quat_xyzw(4), lin_vel(3), ang_vel(3)
        root = sim.robot_root_states[eid]
        if self.env_id < 0:
            self._buffers["root_pos"].append(_to_np(root[:, :3]))
            self._buffers["root_quat_xyzw"].append(_to_np(root[:, 3:7]))
            self._buffers["root_lin_vel"].append(_to_np(root[:, 7:10]))
            self._buffers["root_ang_vel"].append(_to_np(root[:, 10:13]))
        else:
            self._buffers["root_pos"].append(_to_np(root[:3]))
            self._buffers["root_quat_xyzw"].append(_to_np(root[3:7]))
            self._buffers["root_lin_vel"].append(_to_np(root[7:10]))
            self._buffers["root_ang_vel"].append(_to_np(root[10:13]))

        self._buffers["body_pos_w"].append(_to_np(sim._rigid_body_pos[eid]))
        self._buffers["body_quat_xyzw"].append(_to_np(sim._rigid_body_rot[eid]))
        self._buffers["body_lin_vel_w"].append(_to_np(sim._rigid_body_vel[eid]))
        self._buffers["body_ang_vel_w"].append(_to_np(sim._rigid_body_ang_vel[eid]))
        if hasattr(sim, "contact_forces"):
            self._buffers["contact_forces"].append(_to_np(sim.contact_forces[eid]))
        if hasattr(sim, "contact_forces_history"):
            self._buffers["contact_forces_history"].append(_to_np(sim.contact_forces_history[eid]))
        if hasattr(sim, "get_raw_rigid_contacts"):
            try:
                raw_contacts = sim.get_raw_rigid_contacts()
            except Exception as exc:
                logger.debug(f"EvalRecordingCallback: failed to read raw rigid contacts: {exc}")
                raw_contacts = None
            if raw_contacts is not None:
                self._buffers["raw_contact_count"].append(np.asarray(raw_contacts["count"], dtype=np.int32))
                self._buffers["raw_contact_shape0"].append(np.asarray(raw_contacts["shape0"], dtype=np.int32))
                self._buffers["raw_contact_shape1"].append(np.asarray(raw_contacts["shape1"], dtype=np.int32))
                self._buffers["raw_contact_body0"].append(np.asarray(raw_contacts["body0"], dtype=np.int32))
                self._buffers["raw_contact_body1"].append(np.asarray(raw_contacts["body1"], dtype=np.int32))
                self._buffers["raw_contact_point0_w"].append(np.asarray(raw_contacts["point0_w"], dtype=np.float32))
                self._buffers["raw_contact_point1_w"].append(np.asarray(raw_contacts["point1_w"], dtype=np.float32))
                self._buffers["raw_contact_normal_w"].append(np.asarray(raw_contacts["normal_w"], dtype=np.float32))
                self._buffers["raw_contact_force_w"].append(np.asarray(raw_contacts["force_w"], dtype=np.float32))

        if hasattr(env, "command_manager") and env.command_manager is not None:
            try:
                motion_command = env.command_manager.get_state("motion_command")
                self._buffers["motion_id"].append(_to_np(motion_command.motion_ids[eid]))
                self._buffers["motion_time_step"].append(_to_np(motion_command.time_steps[eid]))
            except (AttributeError, KeyError, IndexError):
                pass
        if hasattr(env, "termination_manager") and env.termination_manager is not None:
            try:
                self._buffers["terminated"].append(_to_np(env.termination_manager.terminated[eid]))
                self._buffers["timeout"].append(_to_np(env.termination_manager.time_outs[eid]))
            except (AttributeError, IndexError):
                pass

        # substep tensors: [decimation, num_dof] — one row per physics sub-step
        torques_substep, dof_pos_substep, dof_vel_substep = self._extract_substep_data(env, eid)
        self._buffers["torques_substep"].append(_to_np(torques_substep))
        self._buffers["dof_pos_substep"].append(_to_np(dof_pos_substep))
        self._buffers["dof_vel_substep"].append(_to_np(dof_vel_substep))

        if "actions" in actor_state and actor_state["actions"] is not None:
            self._buffers["actions"].append(_to_np(actor_state["actions"][eid]))

        # Record desired target joint positions (PD setpoint)
        self._buffers["dof_pos_target"].append(_to_np(self._extract_dof_pos_target(env, eid)))

        # Record commanded velocity [lin_vel_x, lin_vel_y, ang_vel_yaw]
        if hasattr(env, "command_manager") and env.command_manager is not None:
            try:
                self._buffers["commanded_velocity"].append(_to_np(env.command_manager.commands[eid]))
            except (AttributeError, IndexError):
                pass

        self._step_count += 1

    def _extract_dof_pos_target(self, env: Any, env_id: int | slice) -> torch.Tensor:
        """Extract desired target joint positions from the action manager's joint control term.

        The PD target is: actions_after_delay * action_scales + default_dof_pos.
        Returns shape [num_dof].
        """
        for _term_name, term in env.action_manager.iter_terms():
            if hasattr(term, "_actions_after_delay") and hasattr(term, "action_scales"):
                return term._actions_after_delay[env_id] * term.action_scales + env.default_dof_pos[env_id]
        raise RuntimeError("No action term with _actions_after_delay found")

    def _extract_torques(self, env: Any, env_id: int | slice) -> torch.Tensor:
        """Extract torques from the action manager's joint control term.

        Returns torques, shape [num_dof].
        """
        for _term_name, term in env.action_manager.iter_terms():
            if hasattr(term, "torques"):
                return term.torques[env_id]
        raise RuntimeError("No action term with torques found")

    def _extract_substep_data(self, env: Any, env_id: int | slice) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Extract sub-step torques, dof_pos, and dof_vel from the action manager's joint control term.

        Returns (torques_substep, dof_pos_substep, dof_vel_substep), each shape [decimation, num_dof].
        """
        for _term_name, term in env.action_manager.iter_terms():
            if hasattr(term, "torques_substep"):
                return term.torques_substep[env_id], term.dof_pos_substep[env_id], term.dof_vel_substep[env_id]
        raise RuntimeError("No action term with torques_substep found")

    def on_post_evaluate_policy(self) -> None:
        self._save()
