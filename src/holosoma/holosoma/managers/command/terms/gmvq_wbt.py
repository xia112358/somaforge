"""Online GMVQ reference command for an existing whole-body tracking policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from gmvq.g1_fk import CanonicalG1TorchFK
from gmvq.policy_reference import (
    GMVQOnlineReference,
    GMVQPolicyReferenceRuntime,
    query_local_height_scan,
)
from loguru import logger

from holosoma.managers.command.terms.wbt import FAKE_BODY_NAME_ALIASES, MotionCommand
from holosoma.utils.rotations import quat_apply, quat_inverse, quat_mul, yaw_quat


def _wxyz_to_xyzw(value: torch.Tensor) -> torch.Tensor:
    return torch.cat((value[..., 1:], value[..., :1]), dim=-1)


def _xyzw_to_wxyz(value: torch.Tensor) -> torch.Tensor:
    return torch.cat((value[..., 3:], value[..., :3]), dim=-1)


def _tracking_gate_error(
    current_reference_pos: torch.Tensor,
    robot_body_pos: torch.Tensor,
    gate_body_indices: torch.Tensor,
) -> torch.Tensor:
    """Return the worst current-frame hand/foot tracking error per environment."""
    return torch.norm(
        current_reference_pos.index_select(1, gate_body_indices)
        - robot_body_pos.index_select(1, gate_body_indices),
        dim=-1,
    ).amax(dim=1)


def _tracking_gate_handshake(
    *,
    next_ready: torch.Tensor,
    current_ready: torch.Tensor,
    pending_next: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Expose an unreachable next frame before committing its logical cursor."""
    advance_ready = next_ready
    start_pending = ~next_ready & current_ready
    updated_pending = pending_next | start_pending
    updated_pending = torch.where(advance_ready, torch.zeros_like(updated_pending), updated_pending)
    return advance_ready, updated_pending


class GMVQMotionCommand(MotionCommand):
    """Decode one reference atom per environment boundary and track it online.

    ``motion_config`` remains the authoritative reset pose and schema contract.
    Once reset has written that state to the simulator, all subsequent reference
    frames come from the GMVQ bundle using current terrain and robot state.
    """

    def __init__(self, cfg: Any, env: Any) -> None:
        super().__init__(cfg, env)
        self.bundle_path = str(cfg.params["gmvq_bundle"])
        self.tracking_gate_m = float(cfg.params.get("gmvq_tracking_gate_m", 0.15))
        record_path = cfg.params.get("gmvq_boundary_record_path")
        self.boundary_record_path = None if not record_path else Path(str(record_path)).expanduser()
        self._boundary_records: dict[str, list[np.ndarray]] = {
            key: []
            for key in (
                "height_scan",
                "joint_pos",
                "joint_vel",
                "previous_code",
                "code",
                "theta",
                "length",
            )
        }
        self._gmvq_ready = False

    def setup(self) -> None:
        self._gmvq_ready = False
        super().setup()
        self.gmvq_runtime = GMVQPolicyReferenceRuntime(self.bundle_path, device=self.device)
        self.online_reference = GMVQOnlineReference(
            self.gmvq_runtime,
            num_envs=self.num_envs,
            fps=1.0 / float(self._env.dt),
        )

        tracked_names = [FAKE_BODY_NAME_ALIASES.get(name, name) for name in self.motion_cfg.body_names_to_track]
        ref_name = FAKE_BODY_NAME_ALIASES.get(self.motion_cfg.body_name_ref[0], self.motion_cfg.body_name_ref[0])
        fk_names = list(dict.fromkeys([*tracked_names, ref_name]))
        self._gmvq_fk = CanonicalG1TorchFK(
            joint_names=list(self._env.simulator.dof_names),  # type: ignore[attr-defined]
            link_names=fk_names,
        ).to(self.device)
        self._gmvq_tracked_fk_indices = torch.as_tensor(
            [fk_names.index(name) for name in tracked_names], dtype=torch.long, device=self.device
        )
        self._gmvq_ref_fk_index = fk_names.index(ref_name)
        gate_names = (
            "left_ankle_roll_link",
            "right_ankle_roll_link",
            "left_wrist_yaw_link",
            "right_wrist_yaw_link",
        )
        self._gmvq_gate_body_indices = torch.as_tensor(
            [tracked_names.index(name) for name in gate_names], dtype=torch.long, device=self.device
        )
        self._gmvq_body_pos = torch.zeros(self.num_envs, len(tracked_names), 3, device=self.device)
        self._gmvq_body_quat = torch.zeros(self.num_envs, len(tracked_names), 4, device=self.device)
        self._gmvq_body_quat[..., 3] = 1.0
        self._gmvq_body_lin_vel = torch.zeros_like(self._gmvq_body_pos)
        self._gmvq_body_ang_vel = torch.zeros_like(self._gmvq_body_pos)
        self._gmvq_pending_next = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self._gmvq_ref_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self._gmvq_ref_quat = torch.zeros(self.num_envs, 4, device=self.device)
        self._gmvq_ref_quat[..., 3] = 1.0
        self._gmvq_ready = True
        logger.info(
            "GMVQ online WBT reference ready: bundle={}, envs={}, scan_points={}, tracking_gate_m={}",
            self.bundle_path,
            self.num_envs,
            int(self.gmvq_runtime.local_grid.shape[0]),
            self.tracking_gate_m,
        )

    def _robot_state_q_qd(self) -> tuple[torch.Tensor, torch.Tensor]:
        root = self._env.simulator.robot_root_states  # type: ignore[attr-defined]
        q = torch.cat((_xyzw_to_wxyz(root[:, 3:7]), self._env.simulator.dof_pos), dim=1)
        q = torch.cat((root[:, :3], q), dim=1)
        qd = torch.cat((root[:, 7:13], self._env.simulator.dof_vel), dim=1)
        return q, qd

    def _command_q_qd(self) -> tuple[torch.Tensor, torch.Tensor]:
        current_q, current_qd = self.online_reference.current()
        if not torch.any(self._gmvq_pending_next):
            return current_q, current_qd
        next_q, next_qd = self.online_reference.future((1,))
        pending = self._gmvq_pending_next[:, None]
        return (
            torch.where(pending, next_q[:, 0], current_q),
            torch.where(pending, next_qd[:, 0], current_qd),
        )

    def _height_scan(self, q: torch.Tensor) -> torch.Tensor:
        terrain_state = self._env.terrain_manager.get_state("locomotion_terrain")
        query = getattr(terrain_state, "query_terrain_heights", None)
        if not callable(query):
            raise RuntimeError("GMVQ online reference requires terrain height queries")
        return query_local_height_scan(
            local_grid=self.gmvq_runtime.local_grid,
            root_pos_w=q[:, :3],
            root_quat_wxyz=q[:, 3:7],
            query_terrain_heights=query,
        )

    def _record_boundaries(
        self,
        env_ids: torch.Tensor,
        *,
        height_scan: torch.Tensor,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
        previous_code: torch.Tensor,
    ) -> None:
        if self.boundary_record_path is None or env_ids.numel() == 0:
            return
        ids = env_ids.to(self.device, dtype=torch.long)
        values = {
            "height_scan": height_scan[ids],
            "joint_pos": joint_pos[ids],
            "joint_vel": joint_vel[ids],
            "previous_code": previous_code[ids, None],
            "code": self.online_reference.codes[ids, None],
            "theta": self.online_reference.theta[ids],
            "length": self.online_reference.lengths[ids, None],
        }
        for key, value in values.items():
            self._boundary_records[key].append(value.detach().cpu().numpy())
        self.boundary_record_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            self.boundary_record_path,
            schema=np.asarray("gmvq_online_boundary_dataset_v1"),
            **{key: np.concatenate(chunks, axis=0) for key, chunks in self._boundary_records.items()},
        )

    @torch.no_grad()
    def _refresh_fk_cache(self, *, zero_velocity: bool = False) -> None:
        previous_pos = self._gmvq_body_pos.clone()
        previous_quat = self._gmvq_body_quat.clone()
        q, _ = self._command_q_qd()
        pos, quat_wxyz = self._gmvq_fk.forward_pose(q)
        quat_xyzw = _wxyz_to_xyzw(quat_wxyz)
        self._gmvq_body_pos = pos.index_select(1, self._gmvq_tracked_fk_indices)
        self._gmvq_body_quat = quat_xyzw.index_select(1, self._gmvq_tracked_fk_indices)
        self._gmvq_ref_pos = pos[:, self._gmvq_ref_fk_index]
        self._gmvq_ref_quat = quat_xyzw[:, self._gmvq_ref_fk_index]
        if zero_velocity:
            self._gmvq_body_lin_vel.zero_()
            self._gmvq_body_ang_vel.zero_()
            return
        dt = float(self._env.dt)
        self._gmvq_body_lin_vel = (self._gmvq_body_pos - previous_pos) / dt
        delta = quat_mul(self._gmvq_body_quat, quat_inverse(previous_quat, w_last=True), w_last=True)
        sign = torch.where(delta[..., 3:4] < 0.0, -1.0, 1.0)
        delta = delta * sign
        vector = delta[..., :3]
        norm = vector.norm(dim=-1, keepdim=True)
        angle = 2.0 * torch.atan2(norm, delta[..., 3:4].clamp_min(1.0e-8))
        self._gmvq_body_ang_vel = vector / norm.clamp_min(1.0e-8) * angle / dt

    def reset(self, env_ids: torch.Tensor | None) -> None:
        ids = self._ensure_index_tensor(env_ids)
        term_manager = getattr(self._env, "termination_manager", None)
        term_dones = getattr(term_manager, "term_dones", {})
        reasons = {
            name: ids[mask[ids].to(torch.bool)].detach().cpu().tolist()
            for name, mask in term_dones.items()
            if ids.numel() > 0 and torch.any(mask[ids])
        }
        if reasons:
            details: dict[str, list[float]] = {}
            bad_tracking = getattr(term_manager, "_term_instances", {}).get("bad_tracking")
            if bad_tracking is not None:
                for name in (
                    "_last_ref_pos_error",
                    "_last_ref_ori_error",
                    "_last_motion_body_pos_error",
                    "_last_motion_body_pos_body_index",
                ):
                    value = getattr(bad_tracking, name, None)
                    if value is not None:
                        details[name] = value[ids].detach().cpu().tolist()
            if self._gmvq_ready:
                tracked_error = torch.norm(self.body_pos_relative_w[ids] - self.robot_body_pos_w[ids], dim=-1)
                details["cursor"] = self.online_reference.cursors[ids].detach().cpu().tolist()
                details["tracked_body_error_m"] = tracked_error.detach().cpu().tolist()
            logger.info("GMVQ episode reset reasons: {}, details={}", reasons, details)
        self._gmvq_ready = False
        try:
            super().reset(ids)
        finally:
            self._gmvq_ready = True
        if ids.numel() == 0:
            return
        self._gmvq_pending_next[ids] = False
        q, qd = self._robot_state_q_qd()
        height_scan = self._height_scan(q)
        self.online_reference.reset(
            ids,
            height_scan=height_scan,
            joint_pos=q,
            joint_vel=qd,
        )
        initial_previous = torch.full((self.num_envs,), -1, dtype=torch.long, device=self.device)
        self._record_boundaries(
            ids,
            height_scan=height_scan,
            joint_pos=q,
            joint_vel=qd,
            previous_code=initial_previous,
        )
        logger.info(
            "GMVQ reset: env_ids={}, codes={}, lengths={}",
            ids.detach().cpu().tolist(),
            self.online_reference.codes[ids].detach().cpu().tolist(),
            self.online_reference.lengths[ids].detach().cpu().tolist(),
        )
        self.time_steps[ids] = self.online_reference.cursors[ids]
        self.motion_ids[ids] = 0
        self._refresh_fk_cache(zero_velocity=True)

    def step(self) -> None:
        q, qd = self._robot_state_q_qd()
        height_scan = self._height_scan(q)
        previous_code = self.online_reference.codes.clone()
        next_q, _ = self.online_reference.future((1,))
        next_q = next_q[:, 0]
        next_pos, next_quat_wxyz = self._gmvq_fk.forward_pose(next_q)
        next_relative_pos, _ = self._adapt_body_targets(
            body_pos_w=next_pos.index_select(1, self._gmvq_tracked_fk_indices),
            body_quat_w=_wxyz_to_xyzw(next_quat_wxyz.index_select(1, self._gmvq_tracked_fk_indices)),
            ref_pos_w=next_pos[:, self._gmvq_ref_fk_index],
            ref_quat_w=_wxyz_to_xyzw(next_quat_wxyz[:, self._gmvq_ref_fk_index]),
            root_pos_w=next_q[:, :3],
            root_quat_w=_wxyz_to_xyzw(next_q[:, 3:7]),
        )
        next_gate_error = _tracking_gate_error(
            next_relative_pos,
            self.robot_body_pos_w,
            self._gmvq_gate_body_indices,
        )
        current_gate_error = _tracking_gate_error(
            self.body_pos_relative_w,
            self.robot_body_pos_w,
            self._gmvq_gate_body_indices,
        )
        advance_ready, self._gmvq_pending_next = _tracking_gate_handshake(
            next_ready=next_gate_error <= self.tracking_gate_m,
            current_ready=current_gate_error <= self.tracking_gate_m,
            pending_next=self._gmvq_pending_next,
        )
        advance_ready |= self._env.episode_length_buf <= 1
        self._gmvq_pending_next &= ~advance_ready
        refreshed = self.online_reference.advance(
            height_scan=height_scan,
            joint_pos=q,
            joint_vel=qd,
            advance_ready=advance_ready,
        )
        if refreshed.numel() > 0:
            self._record_boundaries(
                refreshed,
                height_scan=height_scan,
                joint_pos=q,
                joint_vel=qd,
                previous_code=previous_code,
            )
            logger.info(
                "GMVQ atom boundary: env_ids={}, codes={}, lengths={}",
                refreshed.detach().cpu().tolist(),
                self.online_reference.codes[refreshed].detach().cpu().tolist(),
                self.online_reference.lengths[refreshed].detach().cpu().tolist(),
            )
        self.time_steps.copy_(self.online_reference.cursors)
        self._refresh_fk_cache()
        self._update_relative_targets()

    def _update_relative_targets(self) -> None:
        self.body_pos_relative_w, self.body_quat_relative_w = self._adapt_body_targets(
            body_pos_w=self.body_pos_w,
            body_quat_w=self.body_quat_w,
            ref_pos_w=self.ref_pos_w,
            ref_quat_w=self.ref_quat_w,
            root_pos_w=self.root_pos_w,
            root_quat_w=self.root_quat_w,
        )

    def _adapt_body_targets(
        self,
        *,
        body_pos_w: torch.Tensor,
        body_quat_w: torch.Tensor,
        ref_pos_w: torch.Tensor,
        ref_quat_w: torch.Tensor,
        root_pos_w: torch.Tensor,
        root_quat_w: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        use_root = (self._env.episode_length_buf == 0).unsqueeze(1).float()
        ref_pos_w = root_pos_w * use_root + ref_pos_w * (1 - use_root)
        ref_quat_w = root_quat_w * use_root + ref_quat_w * (1 - use_root)
        robot_ref_pos_w = self.robot_root_pos_w * use_root + self.robot_ref_pos_w * (1 - use_root)
        robot_ref_quat_w = self.robot_root_quat_w * use_root + self.robot_ref_quat_w * (1 - use_root)
        count = len(self.motion_cfg.body_names_to_track)
        ref_pos = ref_pos_w[:, None, :].repeat(1, count, 1)
        ref_quat = ref_quat_w[:, None, :].repeat(1, count, 1)
        robot_ref_pos = robot_ref_pos_w[:, None, :].repeat(1, count, 1)
        robot_ref_quat = robot_ref_quat_w[:, None, :].repeat(1, count, 1)
        delta_quat = quat_mul(robot_ref_quat, quat_inverse(ref_quat, w_last=True), w_last=True)
        if self.motion_cfg.relative_reference_rotation != "full":
            delta_quat = yaw_quat(delta_quat, w_last=True)
        relative_quat = quat_mul(delta_quat, body_quat_w, w_last=True)
        delta_height = ref_pos - robot_ref_pos
        delta_height[..., :2] = 0.0
        relative_pos = robot_ref_pos + delta_height + quat_apply(delta_quat, body_pos_w - ref_pos, w_last=True)
        return relative_pos, relative_quat

    @property
    def joint_pos(self) -> torch.Tensor:
        if not self._gmvq_ready:
            return super().joint_pos
        return self._command_q_qd()[0][:, 7:]

    @property
    def joint_vel(self) -> torch.Tensor:
        if not self._gmvq_ready:
            return super().joint_vel
        return self._command_q_qd()[1][:, 6:]

    @property
    def body_pos_w(self) -> torch.Tensor:
        return super().body_pos_w if not self._gmvq_ready else self._gmvq_body_pos

    @property
    def body_quat_w(self) -> torch.Tensor:
        return super().body_quat_w if not self._gmvq_ready else self._gmvq_body_quat

    @property
    def body_lin_vel_w(self) -> torch.Tensor:
        return super().body_lin_vel_w if not self._gmvq_ready else self._gmvq_body_lin_vel

    @property
    def body_ang_vel_w(self) -> torch.Tensor:
        return super().body_ang_vel_w if not self._gmvq_ready else self._gmvq_body_ang_vel

    @property
    def ref_pos_w(self) -> torch.Tensor:
        return super().ref_pos_w if not self._gmvq_ready else self._gmvq_ref_pos

    @property
    def ref_quat_w(self) -> torch.Tensor:
        return super().ref_quat_w if not self._gmvq_ready else self._gmvq_ref_quat

    @property
    def ref_lin_vel_w(self) -> torch.Tensor:
        if not self._gmvq_ready:
            return super().ref_lin_vel_w
        return self._gmvq_body_lin_vel[:, self.motion_cfg.body_names_to_track.index(self.motion_cfg.body_name_ref[0])]

    @property
    def ref_ang_vel_w(self) -> torch.Tensor:
        if not self._gmvq_ready:
            return super().ref_ang_vel_w
        return self._gmvq_body_ang_vel[:, self.motion_cfg.body_names_to_track.index(self.motion_cfg.body_name_ref[0])]

    @property
    def root_pos_w(self) -> torch.Tensor:
        if not self._gmvq_ready:
            return super().root_pos_w
        return self.online_reference.current()[0][:, :3]

    @property
    def root_quat_w(self) -> torch.Tensor:
        if not self._gmvq_ready:
            return super().root_quat_w
        return _wxyz_to_xyzw(self.online_reference.current()[0][:, 3:7])

    @property
    def root_lin_vel_w(self) -> torch.Tensor:
        if not self._gmvq_ready:
            return super().root_lin_vel_w
        return self.online_reference.current()[1][:, :3]

    @property
    def root_ang_vel_w(self) -> torch.Tensor:
        if not self._gmvq_ready:
            return super().root_ang_vel_w
        return self.online_reference.current()[1][:, 3:6]

    def future_joint_pos_vel(self, offsets: tuple[int, ...]) -> tuple[torch.Tensor, torch.Tensor]:
        q, qd = self.online_reference.future(offsets)
        return q[..., 7:], qd[..., 6:]

    def future_body_pos_quat_offsets(self, offsets: tuple[int, ...]) -> tuple[torch.Tensor, torch.Tensor]:
        q, _ = self.online_reference.future(offsets)
        pos, quat = self._gmvq_fk.forward_pose(q)
        return (
            pos.index_select(2, self._gmvq_tracked_fk_indices),
            _wxyz_to_xyzw(quat.index_select(2, self._gmvq_tracked_fk_indices)),
        )


__all__ = ["GMVQMotionCommand"]
