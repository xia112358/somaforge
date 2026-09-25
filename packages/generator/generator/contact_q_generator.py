"""Contact-first keyframe generation and q-space trajectory infilling."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import torch
import torch.nn.functional as F
from torch import Tensor, nn

from somaforge_core.motion_contracts import CONTACT_PARTS
from somaforge_core.g1_kinematics import CanonicalG1ForwardKinematics, _matrix_from_rotation6d, _quaternion_multiply_wxyz, _rotation6d
from somaforge_core.prediction_contracts import InfillerOutput

PART_BODY_INDEX = (1, 2, 3, 4, 5, 6)


class ResidualBlock(nn.Module):
    def __init__(self, width: int) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.LayerNorm(width),
            nn.Linear(width, 2 * width),
            nn.SiLU(),
            nn.Linear(2 * width, width),
        )

    def forward(self, value: Tensor) -> Tensor:
        return value + self.network(value)


class TerrainScanEncoder(nn.Module):
    def __init__(self, width: int, rows: int = 20, columns: int = 17) -> None:
        super().__init__()
        self.rows = int(rows)
        self.columns = int(columns)
        self.network = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.SiLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.SiLU(),
            nn.Conv2d(64, 64, 3, stride=2, padding=1),
            nn.SiLU(),
            nn.AdaptiveAvgPool2d((2, 2)),
            nn.Flatten(),
            nn.Linear(256, width),
            nn.SiLU(),
            ResidualBlock(width),
        )

    def forward(self, scan: Tensor) -> Tensor:
        if scan.shape[-1] != self.rows * self.columns:
            raise ValueError(f"expected scan dimension {self.rows * self.columns}, got {scan.shape[-1]}")
        return self.network(scan.reshape(-1, 1, self.rows, self.columns))


@dataclass(frozen=True)
class ContactTransitionPlan:
    action_logits: Tensor
    action_index: Tensor
    touchdown: Tensor
    end_contact: Tensor
    target_position: Tensor
    target_rotation6d: Tensor
    surface_logits: Tensor
    target_surface: Tensor
    duration: Tensor

    def with_geometry(
        self,
        *,
        target_position: Tensor | None = None,
        target_rotation6d: Tensor | None = None,
        target_surface: Tensor | None = None,
        duration: Tensor | None = None,
    ) -> ContactTransitionPlan:
        return replace(
            self,
            target_position=self.target_position if target_position is None else target_position,
            target_rotation6d=self.target_rotation6d if target_rotation6d is None else target_rotation6d,
            target_surface=self.target_surface if target_surface is None else target_surface,
            duration=self.duration if duration is None else duration,
        )


@dataclass(frozen=True)
class ContactQPrediction:
    plan: ContactTransitionPlan
    qpos: Tensor
    keypoint_position: Tensor
    keypoint_rotation6d: Tensor


class SequentialContactQPredictor(nn.Module):
    """Plan the next contact transition, then realize that plan as one full q state."""

    def __init__(
        self,
        action_touchdown_masks: Tensor,
        action_end_contact_masks: Tensor,
        action_base_start_qpos: Tensor,
        action_base_end_qpos: Tensor,
        endpoint_offsets: Tensor,
        q_mean: Tensor,
        q_std: Tensor,
        scan_mean: Tensor,
        scan_std: Tensor,
        contact_position_mean: Tensor,
        contact_position_std: Tensor,
        duration_log_mean: Tensor,
        duration_log_std: Tensor,
        *,
        surface_count: int = 2,
        width: int = 256,
        blocks: int = 4,
        action_embedding_dim: int = 64,
        refinement_steps: int = 0,
        action_joint_state: bool = True,
        contact_conditioned_selector: bool = False,
        maximum_root_translation_m: float = 0.5,
        maximum_root_quaternion_delta: float = 0.7,
        maximum_joint_delta_rad: float = 1.0,
    ) -> None:
        super().__init__()
        action_count = len(action_touchdown_masks)
        self.fk = CanonicalG1ForwardKinematics()
        self.surface_count = int(surface_count)
        self.refinement_steps = int(refinement_steps)
        self.action_joint_state = bool(action_joint_state)
        self.contact_conditioned_selector = bool(contact_conditioned_selector)
        self.maximum_root_translation_m = float(maximum_root_translation_m)
        self.maximum_root_quaternion_delta = float(maximum_root_quaternion_delta)
        self.maximum_joint_delta_rad = float(maximum_joint_delta_rad)
        self.register_buffer("action_touchdown_masks", action_touchdown_masks.bool())
        self.register_buffer("action_end_contact_masks", action_end_contact_masks.bool())
        self.register_buffer("action_base_start_qpos", action_base_start_qpos.float())
        self.register_buffer("action_base_end_qpos", action_base_end_qpos.float())
        self.register_buffer("endpoint_offsets", endpoint_offsets.float())
        self.register_buffer("q_mean", q_mean.float())
        self.register_buffer("q_std", q_std.float())
        self.register_buffer("scan_mean", scan_mean.float())
        self.register_buffer("scan_std", scan_std.float())
        self.register_buffer("contact_position_mean", contact_position_mean.float())
        self.register_buffer("contact_position_std", contact_position_std.float())
        self.register_buffer("duration_log_mean", duration_log_mean.float().reshape(()))
        self.register_buffer("duration_log_std", duration_log_std.float().reshape(()))

        selector_state_dimension = (
            7 + len(CONTACT_PARTS) * (1 + 3 + 6)
            if self.contact_conditioned_selector
            else (36 if self.action_joint_state else 7) + len(CONTACT_PARTS)
        )
        self.q_encoder = nn.Sequential(
            nn.Linear(selector_state_dimension, width),
            nn.SiLU(),
            ResidualBlock(width),
        )
        self.pose_state_encoder = (
            None
            if self.action_joint_state or self.contact_conditioned_selector
            else nn.Sequential(nn.Linear(36, width), nn.SiLU(), ResidualBlock(width))
        )
        self.scan_encoder = TerrainScanEncoder(width)
        self.trunk = nn.Sequential(
            nn.Linear(2 * width, width),
            nn.SiLU(),
            *(ResidualBlock(width) for _ in range(blocks)),
            nn.LayerNorm(width),
        )
        self.action_head = nn.Linear(width, action_count)
        self.action_embedding = nn.Embedding(action_count, action_embedding_dim)
        self.plan_trunk = nn.Sequential(
            nn.Linear(
                width
                + action_embedding_dim
                + (0 if self.action_joint_state or self.contact_conditioned_selector else width),
                width,
            ),
            nn.SiLU(),
            ResidualBlock(width),
            nn.LayerNorm(width),
        )
        self.contact_position_head = nn.Linear(width, len(CONTACT_PARTS) * 3)
        self.contact_rotation_head = nn.Linear(width, len(CONTACT_PARTS) * 6)
        self.surface_head = nn.Linear(width, len(CONTACT_PARTS) * self.surface_count)
        self.duration_head = nn.Linear(width, 1)

        plan_dimension = (
            width
            + action_embedding_dim
            + 2 * len(CONTACT_PARTS)
            + len(CONTACT_PARTS) * (3 + 6 + self.surface_count)
            + 1
            + (36 if self.contact_conditioned_selector else 0)
        )
        self.pose_realizer = nn.Sequential(
            nn.Linear(plan_dimension, 2 * width),
            nn.SiLU(),
            ResidualBlock(2 * width),
            ResidualBlock(2 * width),
            nn.Linear(2 * width, 36),
        )
        refinement_dimension = plan_dimension + 36 + len(CONTACT_PARTS) * (3 + 6 + 1)
        self.pose_refiners = nn.ModuleList(
            nn.Sequential(
                nn.Linear(refinement_dimension, 2 * width),
                nn.SiLU(),
                ResidualBlock(2 * width),
                nn.Linear(2 * width, 36),
            )
            for _ in range(self.refinement_steps)
        )

    def encode(
        self,
        current_qpos: Tensor,
        current_contact: Tensor,
        scan: Tensor,
        current_contact_position: Tensor | None = None,
        current_contact_rotation6d: Tensor | None = None,
    ) -> Tensor:
        q_feature = (current_qpos - self.q_mean) / self.q_std
        scan_feature = (scan - self.scan_mean) / self.scan_std
        if self.contact_conditioned_selector:
            if current_contact_position is None or current_contact_rotation6d is None:
                raise ValueError("contact-conditioned selector requires current contact positions and rotations")
            mask = current_contact[..., None]
            action_state = torch.cat(
                (
                    q_feature[:, :7],
                    current_contact,
                    (current_contact_position * mask).flatten(1),
                    (current_contact_rotation6d * mask).flatten(1),
                ),
                dim=-1,
            )
        else:
            q_state = q_feature if self.action_joint_state else q_feature[:, :7]
            action_state = torch.cat((q_state, current_contact), dim=-1)
        state = self.q_encoder(action_state)
        return self.trunk(torch.cat((state, self.scan_encoder(scan_feature)), dim=-1))

    def plan(
        self,
        current_qpos: Tensor,
        current_contact: Tensor,
        scan: Tensor,
        action_index: Tensor | None = None,
        current_contact_position: Tensor | None = None,
        current_contact_rotation6d: Tensor | None = None,
    ) -> tuple[Tensor, ContactTransitionPlan]:
        hidden = self.encode(
            current_qpos,
            current_contact,
            scan,
            current_contact_position,
            current_contact_rotation6d,
        )
        action_logits = self.action_head(hidden)
        if action_index is None:
            action_index = action_logits.argmax(dim=-1)
        plan_inputs = [hidden, self.action_embedding(action_index)]
        if self.pose_state_encoder is not None:
            q_feature = ((current_qpos - self.q_mean) / self.q_std).clamp(-10.0, 10.0)
            plan_inputs.append(self.pose_state_encoder(q_feature))
        value = self.plan_trunk(torch.cat(plan_inputs, dim=-1))
        raw_rotation = self.contact_rotation_head(value).reshape(-1, len(CONTACT_PARTS), 6)
        contact_rotation = _rotation6d(_matrix_from_rotation6d(raw_rotation))
        surface_logits = self.surface_head(value).reshape(-1, len(CONTACT_PARTS), self.surface_count)
        plan = ContactTransitionPlan(
            action_logits=action_logits,
            action_index=action_index,
            touchdown=self.action_touchdown_masks[action_index].to(hidden.dtype),
            end_contact=self.action_end_contact_masks[action_index].to(hidden.dtype),
            target_position=(
                self.contact_position_head(value).reshape(-1, len(CONTACT_PARTS), 3) * self.contact_position_std
                + self.contact_position_mean
            ),
            target_rotation6d=contact_rotation,
            surface_logits=surface_logits,
            target_surface=surface_logits.argmax(dim=-1),
            duration=torch.exp(self.duration_head(value).squeeze(-1) * self.duration_log_std + self.duration_log_mean),
        )
        return hidden, plan

    def aligned_action_endpoint(self, action_index: Tensor, current_qpos: Tensor) -> Tensor:
        base_start = self.action_base_start_qpos[action_index]
        base_end = self.action_base_end_qpos[action_index]
        root_position = base_end[:, :3] + current_qpos[:, :3] - base_start[:, :3]
        start_quaternion = F.normalize(base_start[:, 3:7], dim=-1)
        inverse_start = torch.cat((start_quaternion[:, :1], -start_quaternion[:, 1:]), dim=-1)
        correction = _quaternion_multiply_wxyz(F.normalize(current_qpos[:, 3:7], dim=-1), inverse_start)
        root_quaternion = F.normalize(
            _quaternion_multiply_wxyz(correction, F.normalize(base_end[:, 3:7], dim=-1)), dim=-1
        )
        # Current joint error is state, not an intra-action parameter.  Carrying
        # it into the next endpoint makes recursive error accumulate without
        # bound.  Only the root coordinate frame is aligned; the planned
        # transition keeps its learned terminal joint manifold.
        joints = base_end[:, 7:]
        joints = torch.maximum(torch.minimum(joints, self.fk.joint_upper), self.fk.joint_lower)
        return torch.cat((root_position, root_quaternion, joints), dim=-1)

    def realize_pose(self, hidden: Tensor, current_qpos: Tensor, plan: ContactTransitionPlan) -> ContactQPrediction:
        surface = F.one_hot(plan.target_surface.clamp(0, self.surface_count - 1), self.surface_count).to(hidden.dtype)
        value = torch.cat(
            (
                hidden,
                self.action_embedding(plan.action_index),
                plan.touchdown,
                plan.end_contact,
                plan.target_position.flatten(1),
                plan.target_rotation6d.flatten(1),
                surface.flatten(1),
                plan.duration[:, None],
                *(
                    (((current_qpos - self.q_mean) / self.q_std).clamp(-10.0, 10.0),)
                    if self.contact_conditioned_selector
                    else ()
                ),
            ),
            dim=-1,
        )
        base = self.aligned_action_endpoint(plan.action_index, current_qpos)
        qpos = self._apply_q_delta(base, self.pose_realizer(value), scale=1.0)
        active = plan.end_contact[..., None]
        for refiner in self.pose_refiners:
            position, rotation6d = self.fk(qpos)
            contact_position_error = (plan.target_position - position[:, PART_BODY_INDEX]) * active
            contact_rotation_error = (plan.target_rotation6d - rotation6d[:, PART_BODY_INDEX]) * active
            normalized_q = ((qpos - self.q_mean) / self.q_std).clamp(-10.0, 10.0)
            refinement = torch.cat(
                (
                    value,
                    normalized_q,
                    (contact_position_error / 0.05).flatten(1),
                    contact_rotation_error.flatten(1),
                    plan.end_contact,
                ),
                dim=-1,
            )
            qpos = self._apply_q_delta(qpos, refiner(refinement), scale=0.35)
        position, rotation6d = self.fk(qpos)
        realized_plan = plan.with_geometry(
            target_position=position[:, PART_BODY_INDEX],
            target_rotation6d=rotation6d[:, PART_BODY_INDEX],
        )
        return ContactQPrediction(realized_plan, qpos, position, rotation6d)

    def _apply_q_delta(self, base: Tensor, residual: Tensor, *, scale: float) -> Tensor:
        root_position = base[:, :3] + scale * self.maximum_root_translation_m * torch.tanh(residual[:, :3])
        root_quaternion = F.normalize(
            base[:, 3:7] + scale * self.maximum_root_quaternion_delta * torch.tanh(residual[:, 3:7]),
            dim=-1,
        )
        joints = base[:, 7:] + scale * self.maximum_joint_delta_rad * torch.tanh(residual[:, 7:])
        joints = torch.maximum(torch.minimum(joints, self.fk.joint_upper), self.fk.joint_lower)
        return torch.cat((root_position, root_quaternion, joints), dim=-1)

    def forward(
        self,
        current_qpos: Tensor,
        current_contact: Tensor,
        scan: Tensor,
        action_index: Tensor | None = None,
        plan_override: ContactTransitionPlan | None = None,
        current_contact_position: Tensor | None = None,
        current_contact_rotation6d: Tensor | None = None,
    ) -> ContactQPrediction:
        hidden, predicted_plan = self.plan(
            current_qpos,
            current_contact,
            scan,
            action_index,
            current_contact_position,
            current_contact_rotation6d,
        )
        plan = predicted_plan if plan_override is None else plan_override
        return self.realize_pose(hidden, current_qpos, plan)

    def contact_points(self, prediction: ContactQPrediction) -> Tensor:
        rotation = _matrix_from_rotation6d(prediction.keypoint_rotation6d)
        points = []
        for part, body in enumerate(PART_BODY_INDEX):
            surface = prediction.plan.target_surface[:, part].clamp(0, self.surface_count - 1)
            offset = self.endpoint_offsets[part, surface]
            points.append(prediction.keypoint_position[:, body] - torch.einsum("bij,bj->bi", rotation[:, body], offset))
        return torch.stack(points, dim=1)


class AdaLNBlock(nn.Module):
    def __init__(self, width: int, heads: int, ffn_width: int) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(width, elementwise_affine=False)
        self.norm2 = nn.LayerNorm(width, elementwise_affine=False)
        self.modulation = nn.Sequential(nn.SiLU(), nn.Linear(width, 4 * width))
        nn.init.zeros_(self.modulation[-1].weight)
        nn.init.zeros_(self.modulation[-1].bias)
        self.attention = nn.MultiheadAttention(width, heads, batch_first=True)
        self.ffn = nn.Sequential(nn.Linear(width, ffn_width), nn.GELU(), nn.Linear(ffn_width, width))

    def forward(self, value: Tensor, condition: Tensor) -> Tensor:
        gamma_a, beta_a, gamma_f, beta_f = self.modulation(condition).chunk(4, dim=-1)
        normalized = (1.0 + gamma_a[:, None]) * self.norm1(value) + beta_a[:, None]
        value = value + self.attention(normalized, normalized, normalized, need_weights=False)[0]
        normalized = (1.0 + gamma_f[:, None]) * self.norm2(value) + beta_f[:, None]
        return value + self.ffn(normalized)


class ContactPlanQInfiller(nn.Module):
    """Fill only the q trajectory between two immutable q boundaries."""

    def __init__(
        self,
        scan_mean: Tensor,
        scan_std: Tensor,
        *,
        surface_count: int = 2,
        width: int = 192,
        layers: int = 4,
        heads: int = 6,
        ffn_width: int = 768,
        maximum_root_translation_m: float = 0.35,
        maximum_root_quaternion_delta: float = 0.5,
        maximum_joint_delta_rad: float = 0.75,
    ) -> None:
        super().__init__()
        self.fk = CanonicalG1ForwardKinematics()
        self.surface_count = int(surface_count)
        self.maximum_root_translation_m = float(maximum_root_translation_m)
        self.maximum_root_quaternion_delta = float(maximum_root_quaternion_delta)
        self.maximum_joint_delta_rad = float(maximum_joint_delta_rad)
        self.register_buffer("scan_mean", scan_mean.float())
        self.register_buffer("scan_std", scan_std.float())
        self.scan_encoder = TerrainScanEncoder(width)
        plan_dimension = 2 * 36 + 3 * len(CONTACT_PARTS) + len(CONTACT_PARTS) * (3 + 6 + surface_count) + 1
        self.condition = nn.Sequential(
            nn.Linear(plan_dimension + width, width), nn.SiLU(), ResidualBlock(width), nn.LayerNorm(width)
        )
        self.base = nn.Sequential(nn.Linear(36, width), nn.SiLU(), nn.Linear(width, width))
        self.phase = nn.Sequential(nn.Linear(9, width), nn.SiLU(), nn.Linear(width, width))
        self.blocks = nn.ModuleList(AdaLNBlock(width, heads, ffn_width) for _ in range(layers))
        self.norm = nn.LayerNorm(width)
        self.residual_head = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 36))

    @staticmethod
    def phase_features(phase: Tensor) -> Tensor:
        values = [phase]
        for frequency in (1.0, 2.0, 4.0, 8.0):
            values.extend((torch.sin(math.pi * frequency * phase), torch.cos(math.pi * frequency * phase)))
        return torch.stack(values, dim=-1)

    def align_base(self, base_qpos: Tensor, start_qpos: Tensor, phase: Tensor) -> Tensor:
        u = phase[..., None]
        root_position = base_qpos[..., :3] + start_qpos[:, None, :3] - base_qpos[:, :1, :3]
        base_quaternion = F.normalize(base_qpos[..., 3:7], dim=-1)
        inverse_start = torch.cat((base_quaternion[:, :1, :1], -base_quaternion[:, :1, 1:]), dim=-1)
        correction = _quaternion_multiply_wxyz(F.normalize(start_qpos[:, None, 3:7], dim=-1), inverse_start)
        root_quaternion = F.normalize(
            _quaternion_multiply_wxyz(correction.expand_as(base_quaternion), base_quaternion), dim=-1
        )
        joints = base_qpos[..., 7:] + (1.0 - u) * (start_qpos[:, None, 7:] - base_qpos[:, :1, 7:])
        return torch.cat((root_position, root_quaternion, joints), dim=-1)

    def forward(
        self,
        scan: Tensor,
        phase: Tensor,
        base_qpos: Tensor,
        start_qpos: Tensor,
        end_qpos: Tensor,
        plan: ContactTransitionPlan,
        start_contact: Tensor,
    ) -> InfillerOutput:
        if base_qpos.shape[:2] != phase.shape:
            raise ValueError("base_qpos and phase must share [B,T]")
        surface = F.one_hot(plan.target_surface.clamp(0, self.surface_count - 1), self.surface_count).to(scan.dtype)
        plan_value = torch.cat(
            (
                start_qpos,
                end_qpos,
                start_contact,
                plan.touchdown,
                plan.end_contact,
                plan.target_position.flatten(1),
                plan.target_rotation6d.flatten(1),
                surface.flatten(1),
                plan.duration[:, None],
            ),
            dim=-1,
        )
        scan_feature = self.scan_encoder((scan - self.scan_mean) / self.scan_std)
        condition = self.condition(torch.cat((plan_value, scan_feature), dim=-1))
        aligned = self.align_base(base_qpos, start_qpos, phase)
        hidden = self.base(aligned) + self.phase(self.phase_features(phase)) + condition[:, None]
        for block in self.blocks:
            hidden = block(hidden, condition)
        residual = self.residual_head(self.norm(hidden))
        u = phase[..., None]
        # Boundary velocity is supplied explicitly by InteractionQInfiller.
        # Keep the learned residual value and slope zero at both endpoints so it
        # cannot undo that hard C1 boundary condition.
        envelope = 16.0 * u.square() * (1.0 - u).square()
        end_quaternion = F.normalize(end_qpos[:, 3:7], dim=-1)
        end_quaternion = torch.where(
            (aligned[:, -1, 3:7] * end_quaternion).sum(dim=-1, keepdim=True) < 0.0,
            -end_quaternion,
            end_quaternion,
        )
        root_position = (
            aligned[..., :3]
            + u * (end_qpos[:, None, :3] - aligned[:, -1:, :3])
            + envelope * self.maximum_root_translation_m * torch.tanh(residual[..., :3])
        )
        root_quaternion = F.normalize(
            aligned[..., 3:7]
            + u * (end_quaternion[:, None] - aligned[:, -1:, 3:7])
            + envelope * self.maximum_root_quaternion_delta * torch.tanh(residual[..., 3:7]),
            dim=-1,
        )
        joints = (
            aligned[..., 7:]
            + u * (end_qpos[:, None, 7:] - aligned[:, -1:, 7:])
            + envelope * self.maximum_joint_delta_rad * torch.tanh(residual[..., 7:])
        )
        joints = torch.maximum(torch.minimum(joints, self.fk.joint_upper), self.fk.joint_lower)
        qpos = torch.cat((root_position, root_quaternion, joints), dim=-1)
        qpos = torch.where((phase <= 0.0)[..., None], start_qpos[:, None], qpos)
        terminal = torch.cat(
            (
                end_qpos[:, :3],
                F.normalize(end_qpos[:, 3:7], dim=-1),
                torch.maximum(torch.minimum(end_qpos[:, 7:], self.fk.joint_upper), self.fk.joint_lower),
            ),
            dim=-1,
        )
        qpos = torch.where((phase >= 1.0)[..., None], terminal[:, None], qpos)
        position, rotation6d = self.fk(qpos)
        contact_logits = qpos.new_zeros(qpos.shape[:-1] + (len(CONTACT_PARTS),))
        return InfillerOutput(position, rotation6d, contact_logits, qpos)
