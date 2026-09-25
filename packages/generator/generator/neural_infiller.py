"""Single-pass keypoint infiller with a private canonical-G1 state branch.

The private qpos branch is an auxiliary representation used to impose robot
kinematics and collision constraints.  It is decoded in the same network
forward as the public keypoints; it is never an IK post-processing stage.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from somaforge_core import CONTACT_BODY_NAMES_BY_PART, G1_29DOF_JOINT_ORDER
from somaforge_core.robot_assets import canonical_g1_urdf_path
from torch import Tensor, nn

from somaforge_core.motion_contracts import BODY_NAMES, CONTACT_PARTS


from somaforge_core.g1_kinematics import _rpy_matrix


from somaforge_core.g1_kinematics import _quaternion_matrix_wxyz


from somaforge_core.g1_kinematics import _axis_angle_matrix


from somaforge_core.g1_kinematics import _rotation6d


from somaforge_core.g1_kinematics import _matrix_from_rotation6d


from somaforge_core.g1_kinematics import _rotation_vector_matrix


from somaforge_core.g1_kinematics import _rotation_chordal_error


from somaforge_core.g1_kinematics import _rotation_angle_degrees


from somaforge_core.g1_kinematics import _rotation_log_vector


from somaforge_core.g1_kinematics import _quaternion_multiply_wxyz


from somaforge_core.g1_kinematics import _canonical_boundary


from somaforge_core.g1_kinematics import CanonicalG1ForwardKinematics


from contact_solver.collision_geometry import _mesh_vertices


from contact_solver.collision_geometry import _sphere_points


from contact_solver.collision_geometry import _cylinder_points


from contact_solver.collision_geometry import CanonicalG1CollisionPoints


from contact_solver.collision_geometry import full_geometry_box_ground_penetration


from contact_solver.collision_geometry import full_geometry_box_penetration


from contact_solver.collision_geometry import full_geometry_contact_surface_penalty


from contact_solver.collision_geometry import full_geometry_box_collision_penalty


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
        gamma_attention, beta_attention, gamma_ffn, beta_ffn = self.modulation(condition).chunk(4, dim=-1)
        normalized = (1.0 + gamma_attention[:, None]) * self.norm1(value) + beta_attention[:, None]
        value = value + self.attention(normalized, normalized, normalized, need_weights=False)[0]
        normalized = (1.0 + gamma_ffn[:, None]) * self.norm2(value) + beta_ffn[:, None]
        return value + self.ffn(normalized)


from somaforge_core.prediction_contracts import InfillerOutput


class G1ConstrainedKeypointInfiller(nn.Module):
    """Decode keypoints and canonical G1 qpos together, without an IK pass."""

    def __init__(
        self,
        condition_dim: int,
        *,
        width: int = 192,
        layers: int = 4,
        heads: int = 6,
        ffn_width: int = 768,
    ) -> None:
        super().__init__()
        self.fk = CanonicalG1ForwardKinematics()
        self.condition = nn.Sequential(nn.Linear(condition_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.phase = nn.Sequential(nn.Linear(9, width), nn.SiLU(), nn.Linear(width, width))
        self.blocks = nn.ModuleList(AdaLNBlock(width, heads, ffn_width) for _ in range(layers))
        self.norm = nn.LayerNorm(width)
        # 21 translation residuals plus one 3D tangent-space rotation residual
        # for every public rigid-body keypoint.  Rotation matrices are formed
        # inside forward(), so the public trajectory can never contain an
        # invalid or sheared "rotation6d" value.
        self.keypoint_head = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 42))
        self.q_residual_head = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 36))
        self.boundary_q_head = nn.Sequential(
            nn.Linear(63 + len(CONTACT_PARTS), width),
            nn.SiLU(),
            nn.Linear(width, width),
            nn.SiLU(),
            nn.Linear(width, 36),
        )
        self.contact_head = nn.Linear(width, len(CONTACT_PARTS))

    @staticmethod
    def phase_features(phase: Tensor) -> Tensor:
        values = [phase]
        for frequency in (1.0, 2.0, 4.0, 8.0):
            values.extend((torch.sin(math.pi * frequency * phase), torch.cos(math.pi * frequency * phase)))
        return torch.stack(values, dim=-1)

    def forward(
        self,
        condition_input: Tensor,
        phase: Tensor,
        start_position: Tensor,
        start_rotation6d: Tensor,
        end_position: Tensor,
        end_rotation6d: Tensor,
        start_contact: Tensor,
        end_contact: Tensor,
    ) -> InfillerOutput:
        condition = self.condition(condition_input)
        hidden = self.phase(self.phase_features(phase)) + condition[:, None]
        for block in self.blocks:
            hidden = block(hidden, condition)
        hidden = self.norm(hidden)

        raw_keypoint = self.keypoint_head(hidden)
        u = phase[..., None, None]
        envelope = 4.0 * u * (1.0 - u)
        position_base = (1.0 - u) * start_position[:, None] + u * end_position[:, None]
        position = position_base + envelope * raw_keypoint[..., :21].reshape_as(position_base)
        start_rotation = _matrix_from_rotation6d(start_rotation6d)
        end_rotation = _matrix_from_rotation6d(end_rotation6d)
        # The normalized chord supplies a valid endpoint-preserving base pose;
        # the learned residual is applied on SO(3), rather than added to a 6D
        # matrix representation as if orientation were an ordinary curve.
        rotation_base6d = (1.0 - u) * _rotation6d(start_rotation)[:, None] + u * _rotation6d(end_rotation)[:, None]
        rotation_base = _matrix_from_rotation6d(rotation_base6d)
        rotation_residual = raw_keypoint[..., 21:].reshape(len(raw_keypoint), raw_keypoint.shape[1], len(BODY_NAMES), 3)
        rotation_matrix = rotation_base @ _rotation_vector_matrix(envelope * rotation_residual)
        rotation = _rotation6d(rotation_matrix)

        start_canonical_position, start_canonical_rotation, start_torso_position, start_yaw = _canonical_boundary(
            start_position, start_rotation6d
        )
        end_canonical_position, end_canonical_rotation, end_torso_position, end_yaw = _canonical_boundary(
            end_position, end_rotation6d
        )
        start_boundary = torch.cat(
            (
                start_canonical_position.reshape(len(start_position), -1),
                start_canonical_rotation.reshape(len(start_rotation6d), -1),
                start_contact,
            ),
            dim=-1,
        )
        end_boundary = torch.cat(
            (
                end_canonical_position.reshape(len(end_position), -1),
                end_canonical_rotation.reshape(len(end_rotation6d), -1),
                end_contact,
            ),
            dim=-1,
        )
        start_q_raw = self.boundary_q_head(start_boundary)
        end_q_raw = self.boundary_q_head(end_boundary)
        q_residual = self.q_residual_head(hidden)
        q_u = phase[..., None]
        q_envelope = 4.0 * q_u * (1.0 - q_u)
        start_cosine, start_sine = torch.cos(start_yaw), torch.sin(start_yaw)
        end_cosine, end_sine = torch.cos(end_yaw), torch.sin(end_yaw)
        zero = torch.zeros_like(start_yaw)
        one = torch.ones_like(start_yaw)
        start_yaw_rotation = torch.stack(
            (start_cosine, -start_sine, zero, start_sine, start_cosine, zero, zero, zero, one),
            dim=-1,
        ).reshape(-1, 3, 3)
        end_yaw_rotation = torch.stack(
            (end_cosine, -end_sine, zero, end_sine, end_cosine, zero, zero, zero, one),
            dim=-1,
        ).reshape(-1, 3, 3)
        start_root_position = start_torso_position + torch.einsum("bij,bj->bi", start_yaw_rotation, start_q_raw[:, :3])
        end_root_position = end_torso_position + torch.einsum("bij,bj->bi", end_yaw_rotation, end_q_raw[:, :3])
        root_position = (
            (1.0 - q_u) * start_root_position[:, None]
            + q_u * end_root_position[:, None]
            + q_envelope * q_residual[..., :3]
        )
        identity_quaternion = q_residual.new_tensor((1.0, 0.0, 0.0, 0.0))
        start_local_quaternion = F.normalize(start_q_raw[:, 3:7] + identity_quaternion, dim=-1)
        end_local_quaternion = F.normalize(end_q_raw[:, 3:7] + identity_quaternion, dim=-1)
        start_yaw_quaternion = torch.stack((torch.cos(0.5 * start_yaw), zero, zero, torch.sin(0.5 * start_yaw)), dim=-1)
        end_yaw_quaternion = torch.stack((torch.cos(0.5 * end_yaw), zero, zero, torch.sin(0.5 * end_yaw)), dim=-1)
        start_quaternion = F.normalize(_quaternion_multiply_wxyz(start_yaw_quaternion, start_local_quaternion), dim=-1)
        end_quaternion = F.normalize(_quaternion_multiply_wxyz(end_yaw_quaternion, end_local_quaternion), dim=-1)
        end_quaternion = torch.where(
            (start_quaternion * end_quaternion).sum(dim=-1, keepdim=True) < 0.0,
            -end_quaternion,
            end_quaternion,
        )
        root_quaternion = F.normalize(
            (1.0 - q_u) * start_quaternion[:, None] + q_u * end_quaternion[:, None] + q_envelope * q_residual[..., 3:7],
            dim=-1,
        )
        joint_raw = (
            (1.0 - q_u) * start_q_raw[:, None, 7:] + q_u * end_q_raw[:, None, 7:] + q_envelope * q_residual[..., 7:]
        )
        joint_position = self.fk.bound_joints(joint_raw)
        qpos = torch.cat((root_position, root_quaternion, joint_position), dim=-1)

        contact_logits = self.contact_head(hidden)
        start_logits = 12.0 * (2.0 * start_contact - 1.0)
        end_logits = 12.0 * (2.0 * end_contact - 1.0)
        contact_logits = torch.where((phase <= 0.0)[..., None], start_logits[:, None], contact_logits)
        contact_logits = torch.where((phase >= 1.0)[..., None], end_logits[:, None], contact_logits)
        return InfillerOutput(position, rotation, contact_logits, qpos)


class G1ContactAwareQInfiller(nn.Module):
    """Generate one canonical G1 q trajectory; public keypoints come only from FK."""

    def __init__(
        self,
        condition_dim: int,
        *,
        width: int = 192,
        layers: int = 4,
        heads: int = 6,
        ffn_width: int = 768,
    ) -> None:
        super().__init__()
        self.fk = CanonicalG1ForwardKinematics()
        boundary_dim = condition_dim + 2 * 36 + 2 * len(CONTACT_PARTS)
        self.condition = nn.Sequential(
            nn.Linear(boundary_dim, width),
            nn.SiLU(),
            nn.Linear(width, width),
        )
        self.phase = nn.Sequential(nn.Linear(9, width), nn.SiLU(), nn.Linear(width, width))
        self.blocks = nn.ModuleList(AdaLNBlock(width, heads, ffn_width) for _ in range(layers))
        self.norm = nn.LayerNorm(width)
        self.q_residual_head = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 36))
        self.contact_head = nn.Linear(width, len(CONTACT_PARTS))

    @staticmethod
    def phase_features(phase: Tensor) -> Tensor:
        return G1ConstrainedKeypointInfiller.phase_features(phase)

    def forward(
        self,
        condition_input: Tensor,
        phase: Tensor,
        start_qpos: Tensor,
        end_qpos: Tensor,
        start_contact: Tensor,
        end_contact: Tensor,
    ) -> InfillerOutput:
        end_qpos = end_qpos.clone()
        end_qpos[:, 3:7] = torch.where(
            (start_qpos[:, 3:7] * end_qpos[:, 3:7]).sum(dim=-1, keepdim=True) < 0.0,
            -end_qpos[:, 3:7],
            end_qpos[:, 3:7],
        )
        condition = self.condition(
            torch.cat((condition_input, start_qpos, end_qpos, start_contact, end_contact), dim=-1)
        )
        hidden = self.phase(self.phase_features(phase)) + condition[:, None]
        for block in self.blocks:
            hidden = block(hidden, condition)
        hidden = self.norm(hidden)
        residual = self.q_residual_head(hidden)
        u = phase[..., None]
        envelope = 4.0 * u * (1.0 - u)
        root_position = (1.0 - u) * start_qpos[:, None, :3] + u * end_qpos[:, None, :3] + envelope * residual[..., :3]
        root_quaternion = F.normalize(
            (1.0 - u) * start_qpos[:, None, 3:7] + u * end_qpos[:, None, 3:7] + envelope * residual[..., 3:7],
            dim=-1,
        )
        joint_position = (
            (1.0 - u) * start_qpos[:, None, 7:]
            + u * end_qpos[:, None, 7:]
            + 0.5 * envelope * torch.tanh(residual[..., 7:])
        )
        joint_position = torch.maximum(torch.minimum(joint_position, self.fk.joint_upper), self.fk.joint_lower)
        qpos = torch.cat((root_position, root_quaternion, joint_position), dim=-1)
        keypoint_position, keypoint_rotation6d = self.fk(qpos)
        contact_logits = self.contact_head(hidden)
        start_logits = 12.0 * (2.0 * start_contact - 1.0)
        end_logits = 12.0 * (2.0 * end_contact - 1.0)
        contact_logits = torch.where((phase <= 0.0)[..., None], start_logits[:, None], contact_logits)
        contact_logits = torch.where((phase >= 1.0)[..., None], end_logits[:, None], contact_logits)
        return InfillerOutput(keypoint_position, keypoint_rotation6d, contact_logits, qpos)


class G1ActionMedoidQDeformer(nn.Module):
    """Deform a real action q-template while exposing only canonical-G1 FK poses.

    The selected action medoid supplies the temporal motion.  The network may
    deform that q trajectory to match the realized start boundary and the
    selector's next complete sparse-body boundary; it never freely recreates a
    motion by interpolating two q endpoints.
    """

    def __init__(
        self,
        condition_dim: int,
        *,
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
        self.maximum_root_translation_m = float(maximum_root_translation_m)
        self.maximum_root_quaternion_delta = float(maximum_root_quaternion_delta)
        self.maximum_joint_delta_rad = float(maximum_joint_delta_rad)
        boundary_dim = condition_dim + 36 + 2 * len(BODY_NAMES) * 9 + 2 * len(CONTACT_PARTS)
        self.condition = nn.Sequential(nn.Linear(boundary_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.base = nn.Sequential(nn.Linear(36, width), nn.SiLU(), nn.Linear(width, width))
        self.phase = nn.Sequential(nn.Linear(9, width), nn.SiLU(), nn.Linear(width, width))
        self.blocks = nn.ModuleList(AdaLNBlock(width, heads, ffn_width) for _ in range(layers))
        self.norm = nn.LayerNorm(width)
        self.endpoint_q_head = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 36))
        self.q_residual_head = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 36))

    @staticmethod
    def phase_features(phase: Tensor) -> Tensor:
        return G1ConstrainedKeypointInfiller.phase_features(phase)

    def align_base(self, base_qpos: Tensor, start_qpos: Tensor, phase: Tensor) -> Tensor:
        """Align the medoid to the exact realized start without erasing its shape."""

        u = phase[..., None]
        root_position = base_qpos[..., :3] + (start_qpos[:, None, :3] - base_qpos[:, :1, :3])
        base_quaternion = F.normalize(base_qpos[..., 3:7], dim=-1)
        base_start = base_quaternion[:, 0]
        inverse_base_start = torch.cat((base_start[:, :1], -base_start[:, 1:]), dim=-1)
        correction = _quaternion_multiply_wxyz(F.normalize(start_qpos[:, 3:7], dim=-1), inverse_base_start)
        root_quaternion = F.normalize(
            _quaternion_multiply_wxyz(correction[:, None].expand_as(base_quaternion), base_quaternion), dim=-1
        )
        joint_position = base_qpos[..., 7:] + (1.0 - u) * (start_qpos[:, None, 7:] - base_qpos[:, :1, 7:])
        return torch.cat((root_position, root_quaternion, joint_position), dim=-1)

    def forward(
        self,
        condition_input: Tensor,
        phase: Tensor,
        base_qpos: Tensor,
        start_qpos: Tensor,
        start_position: Tensor,
        start_rotation6d: Tensor,
        end_position: Tensor,
        end_rotation6d: Tensor,
        start_contact: Tensor,
        end_contact: Tensor,
        end_qpos: Tensor | None = None,
    ) -> InfillerOutput:
        if base_qpos.shape[:2] != phase.shape or base_qpos.shape[-1] != 36:
            raise ValueError("base_qpos must be [B,T,36] and match phase")
        condition = self.condition(
            torch.cat(
                (
                    condition_input,
                    start_qpos,
                    start_position.flatten(1),
                    start_rotation6d.flatten(1),
                    end_position.flatten(1),
                    end_rotation6d.flatten(1),
                    start_contact,
                    end_contact,
                ),
                dim=-1,
            )
        )
        aligned = self.align_base(base_qpos, start_qpos, phase)
        hidden = self.base(aligned) + self.phase(self.phase_features(phase)) + condition[:, None]
        for block in self.blocks:
            hidden = block(hidden, condition)
        residual = self.q_residual_head(self.norm(hidden))
        u = phase[..., None]
        if end_qpos is None:
            endpoint_residual = self.endpoint_q_head(condition + self.base(aligned[:, -1]))
            endpoint_root_position = aligned[:, -1, :3] + self.maximum_root_translation_m * torch.tanh(
                endpoint_residual[:, :3]
            )
            endpoint_root_quaternion = F.normalize(
                aligned[:, -1, 3:7] + self.maximum_root_quaternion_delta * torch.tanh(endpoint_residual[:, 3:7]),
                dim=-1,
            )
            endpoint_joint_position = aligned[:, -1, 7:] + self.maximum_joint_delta_rad * torch.tanh(
                endpoint_residual[:, 7:]
            )
            endpoint_joint_position = torch.maximum(
                torch.minimum(endpoint_joint_position, self.fk.joint_upper), self.fk.joint_lower
            )
        else:
            if end_qpos.shape != start_qpos.shape:
                raise ValueError("end_qpos must have the same [B,36] shape as start_qpos")
            endpoint_root_position = end_qpos[:, :3]
            endpoint_root_quaternion = F.normalize(end_qpos[:, 3:7], dim=-1)
            endpoint_joint_position = torch.maximum(
                torch.minimum(end_qpos[:, 7:], self.fk.joint_upper), self.fk.joint_lower
            )
        endpoint_quaternion = torch.where(
            (aligned[:, -1, 3:7] * endpoint_root_quaternion).sum(dim=-1, keepdim=True) < 0.0,
            -endpoint_root_quaternion,
            endpoint_root_quaternion,
        )
        envelope = 4.0 * u * (1.0 - u)
        root_position = (
            aligned[..., :3]
            + u * (endpoint_root_position[:, None] - aligned[:, -1:, :3])
            + envelope * self.maximum_root_translation_m * torch.tanh(residual[..., :3])
        )
        root_quaternion = F.normalize(
            aligned[..., 3:7]
            + u * (endpoint_quaternion[:, None] - aligned[:, -1:, 3:7])
            + envelope * self.maximum_root_quaternion_delta * torch.tanh(residual[..., 3:7]),
            dim=-1,
        )
        joint_position = (
            aligned[..., 7:]
            + u * (endpoint_joint_position[:, None] - aligned[:, -1:, 7:])
            + envelope * self.maximum_joint_delta_rad * torch.tanh(residual[..., 7:])
        )
        joint_position = torch.maximum(torch.minimum(joint_position, self.fk.joint_upper), self.fk.joint_lower)
        qpos = torch.cat((root_position, root_quaternion, joint_position), dim=-1)
        qpos = torch.where((phase <= 0.0)[..., None], start_qpos[:, None], qpos)
        if end_qpos is not None:
            terminal_qpos = torch.cat(
                (
                    end_qpos[:, :3],
                    F.normalize(end_qpos[:, 3:7], dim=-1),
                    torch.maximum(torch.minimum(end_qpos[:, 7:], self.fk.joint_upper), self.fk.joint_lower),
                ),
                dim=-1,
            )
            qpos = torch.where((phase >= 1.0)[..., None], terminal_qpos[:, None], qpos)
        position, rotation6d = self.fk(qpos)
        contact_logits = qpos.new_zeros(qpos.shape[:-1] + (len(CONTACT_PARTS),))
        return InfillerOutput(position, rotation6d, contact_logits, qpos)


@dataclass(frozen=True)
class ContactAwareQInfillerLoss:
    total: Tensor
    q_reconstruction: Tensor
    endpoint: Tensor
    keypoint_position: Tensor
    keypoint_rotation: Tensor
    contact: Tensor
    contact_position_velocity: Tensor
    contact_rotation_velocity: Tensor
    contact_surface: Tensor
    smoothness: Tensor
    collision: Tensor


def contact_aware_q_infiller_loss(
    model: G1ContactAwareQInfiller,
    output: InfillerOutput,
    *,
    target_qpos: Tensor,
    target_contact: Tensor,
    collision_penalty: Tensor,
    contact_surface_penalty: Tensor,
) -> ContactAwareQInfillerLoss:
    """Learn natural support kinematics from canonical q instead of post-processing."""

    if collision_penalty.ndim != 0:
        raise ValueError("collision_penalty must be a scalar tensor")
    if contact_surface_penalty.ndim != 0:
        raise ValueError("contact_surface_penalty must be a scalar tensor")
    target_position, target_rotation6d = model.fk(target_qpos)
    output_rotation = _matrix_from_rotation6d(output.keypoint_rotation6d)
    target_rotation = _matrix_from_rotation6d(target_rotation6d)
    q_reconstruction = (
        ((output.auxiliary_qpos[..., :3] - target_qpos[..., :3]) / 0.02).square().mean()
        + (1.0 - (output.auxiliary_qpos[..., 3:7] * target_qpos[..., 3:7]).sum(dim=-1).abs()).mean()
        + ((output.auxiliary_qpos[..., 7:] - target_qpos[..., 7:]) / 0.1).square().mean()
    )
    endpoint_q = output.auxiliary_qpos[:, (0, -1)]
    target_endpoint_q = target_qpos[:, (0, -1)]
    endpoint = (
        ((endpoint_q[..., :3] - target_endpoint_q[..., :3]) / 0.005).square().mean()
        + (1.0 - (endpoint_q[..., 3:7] * target_endpoint_q[..., 3:7]).sum(dim=-1).abs()).mean()
        + ((endpoint_q[..., 7:] - target_endpoint_q[..., 7:]) / 0.02).square().mean()
    )
    keypoint_position = ((output.keypoint_position - target_position) / 0.02).square().mean()
    keypoint_rotation = _rotation_chordal_error(output_rotation, target_rotation).mean()
    contact = F.binary_cross_entropy_with_logits(output.contact_logits, target_contact)

    persistent = (target_contact[:, 1:] > 0.5) & (target_contact[:, :-1] > 0.5)
    persistent_count = persistent.sum().clamp_min(1)
    output_position_delta = output.keypoint_position[:, 1:, 1:] - output.keypoint_position[:, :-1, 1:]
    target_position_delta = target_position[:, 1:, 1:] - target_position[:, :-1, 1:]
    position_velocity_error = ((output_position_delta - target_position_delta) / 0.005).square().mean(dim=-1)
    contact_position_velocity = (position_velocity_error * persistent).sum() / persistent_count

    output_rotation_delta = output_rotation[:, 1:, 1:] @ output_rotation[:, :-1, 1:].transpose(-1, -2)
    target_rotation_delta = target_rotation[:, 1:, 1:] @ target_rotation[:, :-1, 1:].transpose(-1, -2)
    rotation_velocity_error = _rotation_chordal_error(output_rotation_delta, target_rotation_delta)
    contact_rotation_velocity = (rotation_velocity_error * persistent).sum() / persistent_count

    output_joint_velocity = output.auxiliary_qpos[:, 1:, 7:] - output.auxiliary_qpos[:, :-1, 7:]
    target_joint_velocity = target_qpos[:, 1:, 7:] - target_qpos[:, :-1, 7:]
    output_root_velocity = output.auxiliary_qpos[:, 1:, :3] - output.auxiliary_qpos[:, :-1, :3]
    target_root_velocity = target_qpos[:, 1:, :3] - target_qpos[:, :-1, :3]
    smoothness = (
        (output_joint_velocity[:, 1:] - output_joint_velocity[:, :-1])
        - (target_joint_velocity[:, 1:] - target_joint_velocity[:, :-1])
    ).square().mean() + (
        (
            (output_root_velocity[:, 1:] - output_root_velocity[:, :-1])
            - (target_root_velocity[:, 1:] - target_root_velocity[:, :-1])
        )
        / 0.01
    ).square().mean()
    total = q_reconstruction + 2.0 * endpoint + 2.0 * keypoint_position + keypoint_rotation
    total = total + 0.2 * contact + 5.0 * contact_position_velocity + 2.0 * contact_rotation_velocity
    total = total + 5.0 * contact_surface_penalty
    total = total + 0.5 * smoothness + 10.0 * collision_penalty
    return ContactAwareQInfillerLoss(
        total,
        q_reconstruction,
        endpoint,
        keypoint_position,
        keypoint_rotation,
        contact,
        contact_position_velocity,
        contact_rotation_velocity,
        contact_surface_penalty,
        smoothness,
        collision_penalty,
    )


@dataclass(frozen=True)
class InfillerLoss:
    total: Tensor
    endpoint: Tensor
    contact: Tensor
    pose_position: Tensor
    pose_rotation: Tensor
    contact_pose: Tensor
    fk_consistency: Tensor
    boundary_fk_pose: Tensor
    q_supervision: Tensor
    boundary_q_supervision: Tensor
    smoothness: Tensor
    collision: Tensor


@dataclass(frozen=True)
class InfillerSeamLoss:
    total: Tensor
    keypoint_position_velocity: Tensor
    keypoint_rotation_velocity: Tensor
    q_root_position_velocity: Tensor
    q_root_rotation_velocity: Tensor
    q_joint_velocity: Tensor


def constrained_infiller_seam_loss(
    left: InfillerOutput,
    right: InfillerOutput,
    *,
    left_duration: Tensor,
    right_duration: Tensor,
    q_valid: Tensor,
) -> InfillerSeamLoss:
    """Match the outgoing and incoming physical twists at a shared boundary."""

    phase_steps = left.keypoint_position.shape[1] - 1
    left_dt = (left_duration / phase_steps).clamp_min(1.0e-4)
    right_dt = (right_duration / phase_steps).clamp_min(1.0e-4)
    left_rotation = _matrix_from_rotation6d(left.keypoint_rotation6d)
    right_rotation = _matrix_from_rotation6d(right.keypoint_rotation6d)
    # Every event is expressed in its own starting torso-yaw frame.  Align the
    # right event to the left frame through their shared full torso boundary
    # before comparing physical twists.
    alignment_rotation = left_rotation[:, -1, 0] @ right_rotation[:, 0, 0].transpose(-1, -2)
    alignment_translation = left.keypoint_position[:, -1, 0] - torch.einsum(
        "bij,bj->bi", alignment_rotation, right.keypoint_position[:, 0, 0]
    )
    aligned_right_position = alignment_translation[:, None, None] + torch.einsum(
        "bij,btqj->btqi", alignment_rotation, right.keypoint_position
    )
    aligned_right_rotation = torch.einsum("bij,btqjk->btqik", alignment_rotation, right_rotation)
    left_position_velocity = (left.keypoint_position[:, -1] - left.keypoint_position[:, -2]) / left_dt[:, None, None]
    right_position_velocity = (aligned_right_position[:, 1] - aligned_right_position[:, 0]) / right_dt[:, None, None]
    keypoint_position_velocity = ((left_position_velocity - right_position_velocity) / 0.5).square().mean()

    left_delta = left_rotation[:, -1] @ left_rotation[:, -2].transpose(-1, -2)
    right_delta = aligned_right_rotation[:, 1] @ aligned_right_rotation[:, 0].transpose(-1, -2)
    left_rotation_velocity = _rotation_log_vector(left_delta) / left_dt[:, None, None]
    right_rotation_velocity = _rotation_log_vector(right_delta) / right_dt[:, None, None]
    keypoint_rotation_velocity = ((left_rotation_velocity - right_rotation_velocity) / 2.0).square().mean()

    left_q = left.auxiliary_qpos
    right_q = right.auxiliary_qpos
    aligned_right_root_position = alignment_translation[:, None] + torch.einsum(
        "bij,btj->bti", alignment_rotation, right_q[:, :, :3]
    )
    left_root_velocity = (left_q[:, -1, :3] - left_q[:, -2, :3]) / left_dt[:, None]
    right_root_velocity = (aligned_right_root_position[:, 1] - aligned_right_root_position[:, 0]) / right_dt[:, None]
    q_root_position_per_sample = ((left_root_velocity - right_root_velocity) / 0.5).square().mean(dim=-1)

    left_root_rotation = _quaternion_matrix_wxyz(left_q[:, :, 3:7])
    right_root_rotation = _quaternion_matrix_wxyz(right_q[:, :, 3:7])
    right_root_rotation = torch.einsum("bij,btjk->btik", alignment_rotation, right_root_rotation)
    left_root_delta = left_root_rotation[:, -1] @ left_root_rotation[:, -2].transpose(-1, -2)
    right_root_delta = right_root_rotation[:, 1] @ right_root_rotation[:, 0].transpose(-1, -2)
    left_root_angular_velocity = _rotation_log_vector(left_root_delta) / left_dt[:, None]
    right_root_angular_velocity = _rotation_log_vector(right_root_delta) / right_dt[:, None]
    q_root_rotation_per_sample = (
        ((left_root_angular_velocity - right_root_angular_velocity) / 2.0).square().mean(dim=-1)
    )

    left_joint_velocity = (left_q[:, -1, 7:] - left_q[:, -2, 7:]) / left_dt[:, None]
    right_joint_velocity = (right_q[:, 1, 7:] - right_q[:, 0, 7:]) / right_dt[:, None]
    q_joint_per_sample = ((left_joint_velocity - right_joint_velocity) / 5.0).square().mean(dim=-1)
    valid = q_valid.to(left_q).reshape(-1)
    valid_count = valid.sum().clamp_min(1.0)
    q_root_position_velocity = (q_root_position_per_sample * valid).sum() / valid_count
    q_root_rotation_velocity = (q_root_rotation_per_sample * valid).sum() / valid_count
    q_joint_velocity = (q_joint_per_sample * valid).sum() / valid_count
    total = keypoint_position_velocity + keypoint_rotation_velocity
    total = total + q_root_position_velocity + q_root_rotation_velocity + q_joint_velocity
    return InfillerSeamLoss(
        total,
        keypoint_position_velocity,
        keypoint_rotation_velocity,
        q_root_position_velocity,
        q_root_rotation_velocity,
        q_joint_velocity,
    )


def constrained_infiller_loss(
    model: G1ConstrainedKeypointInfiller,
    output: InfillerOutput,
    *,
    target_position: Tensor,
    target_rotation6d: Tensor,
    target_contact: Tensor,
    target_qpos: Tensor,
    q_valid: Tensor | None = None,
    collision_penalty: Tensor,
    pose_position_weight: float = 0.5,
    pose_rotation_weight: float = 1.0,
    contact_pose_weight: float = 2.0,
    q_supervision_weight: float = 0.25,
    boundary_q_supervision_weight: float = 1.0,
    boundary_fk_pose_weight: float = 2.0,
    collision_weight: float = 10.0,
) -> InfillerLoss:
    """Constraint-first loss; ``collision_penalty`` is mandatory by design.

    The collision term must be produced from the auxiliary qpos against the
    canonical G1 geometry and current terrain.  Requiring it explicitly keeps
    a training caller from silently reverting to sparse keypoint collision.
    """

    if collision_penalty.ndim != 0:
        raise ValueError("collision_penalty must be a scalar tensor")
    fk_position, fk_rotation6d = model.fk(output.auxiliary_qpos)
    output_rotation = _matrix_from_rotation6d(output.keypoint_rotation6d)
    target_rotation = _matrix_from_rotation6d(target_rotation6d)
    fk_rotation = _matrix_from_rotation6d(fk_rotation6d)
    endpoint = ((output.keypoint_position[:, (0, -1)] - target_position[:, (0, -1)]) / 0.01).square().mean() + (
        _rotation_chordal_error(output_rotation[:, (0, -1)], target_rotation[:, (0, -1)]).mean()
    )
    contact = F.binary_cross_entropy_with_logits(output.contact_logits, target_contact)
    pose_position = ((output.keypoint_position - target_position) / 0.03).square().mean()
    pose_rotation = _rotation_chordal_error(output_rotation, target_rotation).mean()

    # CONTACT_PARTS and BODY_NAMES deliberately share the LF/RF/LH/RH/LK/RK
    # ordering after the torso.  A contact is a complete rigid-body pose, not
    # merely a point or a binary flag.
    active_contact = target_contact > 0.5
    active_count = active_contact.sum().clamp_min(1)
    contact_position_error = (
        ((output.keypoint_position[..., 1:, :] - target_position[..., 1:, :]) / 0.01).square().mean(dim=-1)
    )
    contact_rotation_error = _rotation_chordal_error(output_rotation[..., 1:, :, :], target_rotation[..., 1:, :, :])
    contact_pose = ((contact_position_error + contact_rotation_error) * active_contact).sum() / active_count

    # The public pose is directly supervised above.  Mechanical FK must align
    # to that teacher pose; using the other learned head as its target lets both
    # heads drift together.  A worst-body term prevents one foot or knee from
    # being sacrificed by the seven-body mean.
    fk_position_error = ((fk_position - target_position) / 0.02).square().mean(dim=-1)
    fk_rotation_error = _rotation_chordal_error(fk_rotation, target_rotation)
    fk_consistency = (
        fk_position_error.mean()
        + fk_position_error.mean(dim=(0, 1)).max()
        + fk_rotation_error.mean()
        + fk_rotation_error.mean(dim=(0, 1)).max()
    )
    boundary_fk_position_error = ((fk_position[:, (0, -1)] - target_position[:, (0, -1)]) / 0.01).square().mean(dim=-1)
    boundary_fk_rotation_error = _rotation_chordal_error(fk_rotation[:, (0, -1)], target_rotation[:, (0, -1)])
    boundary_fk_pose = (
        boundary_fk_position_error.mean()
        + boundary_fk_position_error.mean(dim=(0, 1)).max()
        + boundary_fk_rotation_error.mean()
        + boundary_fk_rotation_error.mean(dim=(0, 1)).max()
    )
    if q_valid is None:
        q_valid = torch.ones(len(target_qpos), dtype=target_qpos.dtype, device=target_qpos.device)
    valid = q_valid.to(target_qpos).reshape(-1)
    valid_count = valid.sum().clamp_min(1.0)
    q_supervision_per_sample = (
        ((output.auxiliary_qpos[..., :3] - target_qpos[..., :3]) / 0.02).square().mean(dim=(-1, -2))
        + (1.0 - (output.auxiliary_qpos[..., 3:7] * target_qpos[..., 3:7]).sum(dim=-1).abs()).mean(dim=-1)
        + ((output.auxiliary_qpos[..., 7:] - target_qpos[..., 7:]) / 0.2).square().mean(dim=(-1, -2))
    )
    q_supervision = (q_supervision_per_sample * valid).sum() / valid_count
    output_boundary_q = output.auxiliary_qpos[:, (0, -1)]
    target_boundary_q = target_qpos[:, (0, -1)]
    boundary_q_per_sample = (
        ((output_boundary_q[..., :3] - target_boundary_q[..., :3]) / 0.01).square().mean(dim=(-1, -2))
        + (1.0 - (output_boundary_q[..., 3:7] * target_boundary_q[..., 3:7]).sum(dim=-1).abs()).mean(dim=-1)
        + ((output_boundary_q[..., 7:] - target_boundary_q[..., 7:]) / 0.1).square().mean(dim=(-1, -2))
    )
    boundary_q_supervision = (boundary_q_per_sample * valid).sum() / valid_count
    q_velocity = output.auxiliary_qpos[:, 1:, 7:] - output.auxiliary_qpos[:, :-1, 7:]
    q_acceleration = q_velocity[:, 1:] - q_velocity[:, :-1]
    keypoint_velocity = output.keypoint_position[:, 1:] - output.keypoint_position[:, :-1]
    keypoint_acceleration = keypoint_velocity[:, 1:] - keypoint_velocity[:, :-1]
    rotation_velocity = output_rotation[:, 1:] @ output_rotation[:, :-1].transpose(-1, -2)
    rotation_acceleration = rotation_velocity[:, 1:] - rotation_velocity[:, :-1]
    smoothness = (
        q_acceleration.square().mean()
        + (keypoint_acceleration / 0.02).square().mean()
        + rotation_acceleration.square().mean()
    )
    total = endpoint + 0.2 * contact + 2.0 * fk_consistency + 0.1 * smoothness
    total = total + float(pose_position_weight) * pose_position
    total = total + float(pose_rotation_weight) * pose_rotation
    total = total + float(contact_pose_weight) * contact_pose
    total = total + float(boundary_fk_pose_weight) * boundary_fk_pose
    total = total + float(q_supervision_weight) * q_supervision
    total = total + float(boundary_q_supervision_weight) * boundary_q_supervision
    total = total + float(collision_weight) * collision_penalty
    return InfillerLoss(
        total,
        endpoint,
        contact,
        pose_position,
        pose_rotation,
        contact_pose,
        fk_consistency,
        boundary_fk_pose,
        q_supervision,
        boundary_q_supervision,
        smoothness,
        collision_penalty,
    )
