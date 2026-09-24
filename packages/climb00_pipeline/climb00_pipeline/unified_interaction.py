"""Joint next-interaction prediction and interaction-conditioned q infilling.

Unlike the legacy contact-first selector, this module has no action vocabulary
and no pose-realization stage.  One shared decoder predicts the endpoint q,
active contacts, surfaces, and duration together.  Contact geometry is derived
from that same q through canonical-G1 FK, so pose and contact cannot disagree.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F
from torch import Tensor, nn

from .contact_q_generator import ContactPlanQInfiller, ContactTransitionPlan, ResidualBlock, TerrainScanEncoder
from .contracts import CONTACT_BODY_INDEX, CONTACT_PARTS
from .neural_infiller import InfillerOutput, _matrix_from_rotation6d, _quaternion_multiply_wxyz


@dataclass(frozen=True)
class UnifiedInteractionPrediction:
    qpos: Tensor
    q_velocity: Tensor
    stationary_contact: Tensor
    keypoint_position: Tensor
    keypoint_rotation6d: Tensor
    contact_logits: Tensor
    active_contact: Tensor
    touchdown_logits: Tensor
    touchdown: Tensor
    persistent_logits: Tensor
    persistent_support: Tensor
    surface_logits: Tensor
    contact_surface: Tensor
    contact_local_offset: Tensor
    contact_position: Tensor
    contact_velocity: Tensor
    duration: Tensor

    def persistent_from(self, current_contact: Tensor) -> Tensor:
        return self.persistent_support & (current_contact > 0.5)

    def touchdown_from(self, current_contact: Tensor) -> Tensor:
        del current_contact
        return self.touchdown

    def liftoff_from(self, current_contact: Tensor) -> Tensor:
        return (current_contact > 0.5) & ~self.persistent_support

    def swing_from(self, current_contact: Tensor) -> Tensor:
        return (current_contact <= 0.5) & ~self.active_contact


@dataclass(frozen=True)
class UnifiedInteractionLoss:
    total: Tensor
    q_pose: Tensor
    contact_state: Tensor
    touchdown: Tensor
    persistent: Tensor
    surface: Tensor
    active_geometry: Tensor
    persistent_anchor: Tensor
    duration: Tensor
    topology_choice: Tensor
    surface_feasibility: Tensor
    inactive_clearance: Tensor
    contact_orientation: Tensor
    q_velocity: Tensor
    contact_velocity: Tensor


@dataclass(frozen=True)
class InteractionInfillerLoss:
    total: Tensor
    q_reconstruction: Tensor
    endpoint: Tensor
    contact_state: Tensor
    persistent_anchor: Tensor
    touchdown_anchor: Tensor
    liftoff_anchor: Tensor
    smoothness: Tensor
    collision: Tensor
    inactive_clearance: Tensor
    contact_orientation: Tensor
    contact_angular_velocity: Tensor


@dataclass(frozen=True)
class InteractionProjectionResult:
    """A q-space constrained trajectory and its before/after audit."""

    output: InfillerOutput
    diagnostics: dict[str, float]


def _endpoint_root_shift_penalty(qpos: Tensor, initial_q: Tensor, maximum_shift_m: float) -> Tensor:
    endpoint_shift = torch.linalg.vector_norm(qpos[:, -1, :3] - initial_q[:, -1, :3], dim=-1)
    return (torch.nn.functional.relu(endpoint_shift - maximum_shift_m) / 0.05).square().mean()


def _limit_endpoint_root_shift(q_tail: Tensor, initial_endpoint: Tensor, maximum_shift_m: float) -> Tensor:
    root = q_tail[..., :3]
    delta = root[:, -1] - initial_endpoint
    scale = (maximum_shift_m / torch.linalg.vector_norm(delta, dim=-1).clamp_min(1.0e-8)).clamp_max(1.0)
    limited_endpoint = initial_endpoint + scale[:, None] * delta
    limited_root = torch.cat((root[:, :-1], limited_endpoint[:, None]), dim=1)
    return torch.cat((limited_root, q_tail[..., 3:]), dim=-1)


def _collision_depth_cost(excess: Tensor, mode: str) -> Tensor:
    if mode == "quadratic":
        return excess.square()
    if mode != "exponential":
        raise ValueError(f"unknown collision cost mode: {mode}")
    # Float32 exponential up to 10 cm excess; a C1 linear continuation beyond
    # that keeps extreme bootstrap states finite without zeroing their gradient.
    excess = excess.float()
    capped = excess.clamp_max(10.0)
    return torch.expm1(capped) + torch.exp(capped) * (excess - capped)


def rollout_dense_collision_loss(
    penetration: Tensor, tolerance_m: float = 0.002, *, mode: str = "quadratic"
) -> Tensor:
    """Penalize collision depth, duration, and the worst dense-trajectory frame."""

    excess = torch.nn.functional.relu(penetration - tolerance_m) / 0.01
    frame_max = excess.amax(dim=-1)
    soft_occupied = 1.0 - torch.exp(-frame_max)
    cost = _collision_depth_cost(excess, mode)
    frame_cost = cost.amax(dim=-1)
    return (
        cost.mean()
        + 0.25 * frame_cost.mean()
        + 0.25 * frame_cost.max()
        + 0.25 * soft_occupied.mean()
    )


def rollout_ground_collision_loss(
    penetration: Tensor, tolerance_m: float = 0.002, *, mode: str = "quadratic"
) -> Tensor:
    """Penalize ground penetration without diluting it over geometry samples."""

    excess = torch.nn.functional.relu(penetration - tolerance_m) / 0.01
    frame_max = excess.amax(dim=-1)
    soft_occupied = 1.0 - torch.exp(-frame_max)
    frame_cost = _collision_depth_cost(frame_max, mode)
    return frame_cost.mean() + frame_cost.max() + 0.25 * soft_occupied.mean()


def contact_rotation_losses(
    predicted_rotation6d: Tensor,
    target_rotation6d: Tensor,
    contact_mask: Tensor,
    *,
    orientation_scale: float = 0.2,
    angular_step_scale: float = 0.05,
    balance_contact_parts: bool = False,
) -> tuple[Tensor, Tensor]:
    """Return contact-link orientation and angular-step losses from FK rotations."""

    if predicted_rotation6d.shape != target_rotation6d.shape:
        raise ValueError("predicted and target contact rotations must have the same shape")
    if predicted_rotation6d.shape[-2:] != (len(CONTACT_BODY_INDEX), 6):
        raise ValueError("contact rotations must end in [contact_part, rotation6d]")
    expected_mask = predicted_rotation6d.shape[:-1]
    if contact_mask.shape != expected_mask:
        raise ValueError(f"contact mask must have shape {expected_mask}, got {tuple(contact_mask.shape)}")
    predicted = _matrix_from_rotation6d(predicted_rotation6d)
    target = _matrix_from_rotation6d(target_rotation6d)
    mask = contact_mask.to(predicted.dtype)
    chordal = ((predicted - target) / orientation_scale).square().mean(dim=(-2, -1))

    def masked_mean(value: Tensor, value_mask: Tensor) -> Tensor:
        if not balance_contact_parts:
            return (value * value_mask).sum() / value_mask.sum().clamp_min(1.0)
        reduce_dims = tuple(range(value_mask.ndim - 1))
        part_count = value_mask.sum(dim=reduce_dims)
        part_mean = (value * value_mask).sum(dim=reduce_dims) / part_count.clamp_min(1.0)
        valid_part = part_count > 0.0
        return (part_mean * valid_part).sum() / valid_part.sum().clamp_min(1)

    orientation = masked_mean(chordal, mask)
    if predicted.ndim < 5 or predicted.shape[1] < 2:
        return orientation, predicted.sum() * 0.0
    predicted_step = predicted[:, :-1].transpose(-1, -2) @ predicted[:, 1:]
    target_step = target[:, :-1].transpose(-1, -2) @ target[:, 1:]
    pair_mask = mask[:, :-1] * mask[:, 1:]
    angular_step = ((predicted_step - target_step) / angular_step_scale).square().mean(dim=(-2, -1))
    angular_velocity = masked_mean(angular_step, pair_mask)
    return orientation, angular_velocity


class UnifiedInteractionPredictor(nn.Module):
    """Predict the next pose-contact interaction as one coupled random variable."""

    def __init__(
        self,
        endpoint_offsets: Tensor,
        q_mean: Tensor,
        q_std: Tensor,
        scan_mean: Tensor,
        scan_std: Tensor,
        duration_log_mean: Tensor,
        duration_log_std: Tensor,
        *,
        surface_count: int = 2,
        width: int = 256,
        blocks: int = 4,
        maximum_root_translation_m: float = 0.5,
        maximum_root_quaternion_delta: float = 0.7,
        maximum_joint_delta_rad: float = 1.0,
        maximum_contact_offset_delta_m: float = 0.08,
        minimum_duration_s: float = 0.12,
        maximum_duration_s: float = 8.66,
        topology_transitions: Tensor | None = None,
        phase_topologies: Tensor | None = None,
        phase_q_prototypes: Tensor | None = None,
        phase_q_velocity_prototypes: Tensor | None = None,
        predict_boundary_velocity: bool = True,
        use_phase_condition: bool = True,
        fixed_material_contacts: bool = False,
        remember_material_contacts: bool = False,
        persistent_constraint_iterations: int = 0,
        persistent_constraint_damping: float = 1.0e-3,
        persistent_constraint_maximum_step: float = 0.25,
    ) -> None:
        super().__init__()
        if endpoint_offsets.shape != (len(CONTACT_PARTS), surface_count, 3):
            raise ValueError("endpoint_offsets must have shape [6, surface_count, 3]")
        from .neural_infiller import CanonicalG1ForwardKinematics

        self.fk = CanonicalG1ForwardKinematics()
        self.surface_count = int(surface_count)
        self.maximum_root_translation_m = float(maximum_root_translation_m)
        self.maximum_root_quaternion_delta = float(maximum_root_quaternion_delta)
        self.maximum_joint_delta_rad = float(maximum_joint_delta_rad)
        self.maximum_contact_offset_delta_m = float(maximum_contact_offset_delta_m)
        self.predict_boundary_velocity = bool(predict_boundary_velocity)
        self.use_phase_condition = bool(use_phase_condition)
        self.fixed_material_contacts = bool(fixed_material_contacts)
        self.remember_material_contacts = bool(remember_material_contacts)
        if self.fixed_material_contacts and self.remember_material_contacts:
            raise ValueError('Choose canonical fixed points or initialized material-point memory, not both')
        if not self.use_phase_condition:
            phase_topologies = None
            phase_q_prototypes = None
            phase_q_velocity_prototypes = None
        self.persistent_constraint_iterations = int(persistent_constraint_iterations)
        self.persistent_constraint_damping = float(persistent_constraint_damping)
        self.persistent_constraint_maximum_step = float(persistent_constraint_maximum_step)
        if self.persistent_constraint_iterations < 0:
            raise ValueError("persistent constraint iterations must be non-negative")
        if self.persistent_constraint_damping <= 0.0:
            raise ValueError("persistent constraint damping must be positive")
        if self.persistent_constraint_maximum_step <= 0.0:
            raise ValueError("persistent constraint maximum step must be positive")
        self.minimum_duration_s = float(minimum_duration_s)
        self.maximum_duration_s = float(maximum_duration_s)
        if not 0.0 < self.minimum_duration_s <= self.maximum_duration_s:
            raise ValueError("duration limits must be positive and ordered")
        if topology_transitions is None:
            topology_transitions = torch.empty((0, 4, len(CONTACT_PARTS)), dtype=torch.bool)
        topology_transitions = topology_transitions.to(torch.bool)
        if topology_transitions.ndim != 3 or topology_transitions.shape[1:] != (4, len(CONTACT_PARTS)):
            raise ValueError("topology_transitions must have shape [K,4,6]")
        if len(topology_transitions):
            start, persistent, touchdown, finish = topology_transitions.unbind(dim=1)
            if bool((persistent & ~start).any() or (persistent & ~finish).any()):
                raise ValueError("persistent contacts must be active at both boundaries")
            if bool((touchdown & ~finish).any() or (persistent & touchdown).any()):
                raise ValueError("touchdown must be an exclusive subset of end contacts")
        self.register_buffer("topology_transitions", topology_transitions, persistent=False)
        if phase_topologies is None:
            phase_topologies = torch.empty((0, 4, len(CONTACT_PARTS)), dtype=torch.bool)
        phase_topologies = phase_topologies.to(torch.bool)
        if phase_topologies.ndim != 3 or phase_topologies.shape[1:] != (4, len(CONTACT_PARTS)):
            raise ValueError("phase_topologies must have shape [E,4,6]")
        self.register_buffer("phase_topologies", phase_topologies, persistent=False)
        if phase_q_prototypes is None:
            phase_q_prototypes = torch.empty((0, 36), dtype=torch.float32)
        phase_q_prototypes = phase_q_prototypes.float()
        if phase_q_prototypes.ndim != 2 or phase_q_prototypes.shape[1] != 36:
            raise ValueError("phase_q_prototypes must have shape [E,36]")
        if len(phase_q_prototypes) and len(phase_q_prototypes) != len(phase_topologies):
            raise ValueError("phase q prototypes and topology schedule must have equal length")
        self.register_buffer("phase_q_prototypes", phase_q_prototypes, persistent=False)
        if phase_q_velocity_prototypes is None:
            phase_q_velocity_prototypes = torch.zeros((len(phase_topologies), 36), dtype=torch.float32)
        phase_q_velocity_prototypes = phase_q_velocity_prototypes.float()
        if phase_q_velocity_prototypes.shape != (len(phase_topologies), 36):
            raise ValueError("phase q velocity prototypes must have shape [E,36]")
        self.register_buffer(
            "phase_q_velocity_prototypes", phase_q_velocity_prototypes, persistent=False
        )
        self.phase_q_residual_adapter = nn.Parameter(torch.zeros((len(phase_topologies), 36), dtype=torch.float32))
        self.phase_q_feature_adapter = nn.Parameter(
            torch.zeros((len(phase_topologies), 36, width), dtype=torch.float32)
        )
        self.register_buffer("endpoint_offsets", endpoint_offsets.float())
        self.register_buffer("q_mean", q_mean.float())
        self.register_buffer("q_std", q_std.float())
        self.register_buffer("scan_mean", scan_mean.float())
        self.register_buffer("scan_std", scan_std.float())
        self.register_buffer("duration_log_mean", duration_log_mean.float().reshape(()))
        self.register_buffer("duration_log_std", duration_log_std.float().reshape(()))

        state_dim = 36 + len(CONTACT_PARTS) * (1 + 3 + 3 + surface_count) + 2 * len(CONTACT_PARTS) + int(self.use_phase_condition)
        if self.predict_boundary_velocity:
            state_dim += 36
        self.state_encoder = nn.Sequential(nn.Linear(state_dim, width), nn.SiLU(), ResidualBlock(width))
        self.scan_encoder = TerrainScanEncoder(width)
        self.trunk = nn.Sequential(
            nn.Linear(2 * width, width),
            nn.SiLU(),
            *(ResidualBlock(width) for _ in range(blocks)),
            nn.LayerNorm(width),
        )
        self.topology_encoder = nn.Linear(3 * len(CONTACT_PARTS), width)
        nn.init.zeros_(self.topology_encoder.weight)
        nn.init.zeros_(self.topology_encoder.bias)
        # A single head is intentional: none of these quantities is upstream
        # of another.  Geometry is then made exact by deriving it from FK.
        # Velocity is appended so every older head row retains its exact
        # meaning when a checkpoint is expanded into the interaction-state
        # model.  New velocity rows start at zero (a stationary boundary).
        output_dim = 36 + 3 * len(CONTACT_PARTS) + len(CONTACT_PARTS) * (surface_count + 3) + 1
        if self.predict_boundary_velocity:
            output_dim += 36
        self.interaction_head = nn.Linear(width, output_dim)
        nn.init.zeros_(self.interaction_head.weight)
        nn.init.zeros_(self.interaction_head.bias)

    def load_compatible_state_dict(
        self, state_dict: dict[str, Tensor], *, reset_q_head_for_prototypes: bool = False
    ) -> None:
        """Load pre-history checkpoints while preserving their exact initial behavior."""

        state_dict = dict(state_dict)
        key = "state_encoder.0.weight"
        incoming = state_dict[key]
        expected = self.state_dict()[key]
        if incoming.shape != expected.shape:
            if incoming.shape[0] != expected.shape[0] or incoming.shape[1] >= expected.shape[1]:
                raise ValueError(f"incompatible {key}: {tuple(incoming.shape)} versus {tuple(expected.shape)}")
            expanded = expected.new_zeros(expected.shape)
            expanded[:, : incoming.shape[1]] = incoming
            state_dict[key] = expanded
        for key in ("interaction_head.weight", "interaction_head.bias"):
            incoming = state_dict[key]
            expected = self.state_dict()[key]
            if incoming.shape != expected.shape:
                if incoming.shape[0] >= expected.shape[0] or incoming.shape[1:] != expected.shape[1:]:
                    raise ValueError(f"incompatible {key}: {tuple(incoming.shape)} versus {tuple(expected.shape)}")
                expanded = expected.new_zeros(expected.shape)
                expanded[: incoming.shape[0]] = incoming
                state_dict[key] = expanded
        for missing_key in (
            "topology_encoder.weight",
            "topology_encoder.bias",
            "phase_q_residual_adapter",
            "phase_q_feature_adapter",
        ):
            if missing_key not in state_dict:
                state_dict[missing_key] = self.state_dict()[missing_key]
        self.load_state_dict(state_dict)
        if reset_q_head_for_prototypes and len(self.phase_q_prototypes):
            with torch.no_grad():
                self.interaction_head.weight[:36].zero_()
                self.interaction_head.bias[:36].zero_()

    def phase_topology_condition(self, current_contact: Tensor, interaction_phase: Tensor) -> Tensor:
        if not len(self.phase_topologies):
            return current_contact.new_zeros((len(current_contact), 3 * len(CONTACT_PARTS)))
        phase_index = torch.round(
            interaction_phase.clamp(0.0, 1.0) * (len(self.phase_topologies) - 1)
        ).to(torch.long)
        scheduled = self.phase_topologies.to(current_contact.device)[phase_index]
        compatible = (scheduled[:, 0] == (current_contact > 0.5)).all(dim=-1)
        condition = torch.cat((scheduled[:, 1], scheduled[:, 2], scheduled[:, 3]), dim=-1).to(current_contact.dtype)
        return condition * compatible[:, None]

    def _apply_q_delta(
        self,
        current_qpos: Tensor,
        residual: Tensor,
        interaction_phase: Tensor | None = None,
        current_contact: Tensor | None = None,
    ) -> Tensor:
        base_qpos = current_qpos
        phase_index = None
        if len(self.phase_q_residual_adapter) and interaction_phase is not None:
            phase_index = torch.round(
                interaction_phase.clamp(0.0, 1.0) * (len(self.phase_q_residual_adapter) - 1)
            ).to(torch.long)
            residual = residual + self.phase_q_residual_adapter[phase_index]
        if len(self.phase_q_prototypes) and interaction_phase is not None:
            if phase_index is None:
                phase_index = torch.round(
                    interaction_phase.clamp(0.0, 1.0) * (len(self.phase_q_prototypes) - 1)
                ).to(torch.long)
            prototype = self.phase_q_prototypes.to(current_qpos.device)[phase_index]
            if len(self.phase_topologies) and current_contact is not None:
                scheduled = self.phase_topologies.to(current_qpos.device)[phase_index]
                compatible = (scheduled[:, 0] == (current_contact > 0.5)).all(dim=-1)
                base_qpos = torch.where(compatible[:, None], prototype, current_qpos)
            else:
                base_qpos = prototype
        root_position = base_qpos[:, :3] + self.maximum_root_translation_m * torch.tanh(residual[:, :3])
        root_quaternion = F.normalize(
            base_qpos[:, 3:7] + self.maximum_root_quaternion_delta * torch.tanh(residual[:, 3:7]), dim=-1
        )
        joints = base_qpos[:, 7:] + self.maximum_joint_delta_rad * torch.tanh(residual[:, 7:])
        joints = torch.maximum(torch.minimum(joints, self.fk.joint_upper), self.fk.joint_lower)
        return torch.cat((root_position, root_quaternion, joints), dim=-1)

    def contact_points(
        self,
        qpos: Tensor,
        contact_surface: Tensor,
        contact_local_offset: Tensor | None = None,
    ) -> Tensor:
        position, rotation6d = self.fk(qpos)
        rotation = _matrix_from_rotation6d(rotation6d)
        points = []
        for part, body in enumerate(CONTACT_BODY_INDEX):
            surface = contact_surface[:, part].clamp(0, self.surface_count - 1)
            offset = (
                self.endpoint_offsets[part, surface]
                if contact_local_offset is None
                else contact_local_offset[:, part]
            )
            points.append(position[:, body] - torch.einsum("bij,bj->bi", rotation[:, body], offset))
        return torch.stack(points, dim=1)

    @staticmethod
    def tangent_q_velocity(qpos: Tensor, q_velocity: Tensor) -> Tensor:
        """Keep quaternion coordinate velocity in the unit-sphere tangent."""

        quaternion_velocity = q_velocity[:, 3:7] - qpos[:, 3:7] * (
            qpos[:, 3:7] * q_velocity[:, 3:7]
        ).sum(dim=-1, keepdim=True)
        return torch.cat((q_velocity[:, :3], quaternion_velocity, q_velocity[:, 7:]), dim=-1)

    def contact_point_velocity(
        self,
        qpos: Tensor,
        q_velocity: Tensor,
        contact_surface: Tensor,
        contact_local_offset: Tensor,
        *,
        epsilon_s: float = 1.0e-3,
    ) -> Tensor:
        """Differentiate the same FK material points used by the keyframe."""

        q_velocity = self.tangent_q_velocity(qpos, q_velocity)
        before = qpos - epsilon_s * q_velocity
        after = qpos + epsilon_s * q_velocity
        before = torch.cat((before[:, :3], F.normalize(before[:, 3:7], dim=-1), before[:, 7:]), dim=-1)
        after = torch.cat((after[:, :3], F.normalize(after[:, 3:7], dim=-1), after[:, 7:]), dim=-1)
        return (
            self.contact_points(after, contact_surface, contact_local_offset)
            - self.contact_points(before, contact_surface, contact_local_offset)
        ) / (2.0 * epsilon_s)

    @staticmethod
    def _coordinate_to_generalized_velocity(qpos: Tensor, q_velocity: Tensor) -> Tensor:
        conjugate = torch.cat((qpos[:, 3:4], -qpos[:, 4:7]), dim=-1)
        angular_quaternion = 2.0 * _quaternion_multiply_wxyz(q_velocity[:, 3:7], conjugate)
        return torch.cat((q_velocity[:, :3], angular_quaternion[:, 1:4], q_velocity[:, 7:]), dim=-1)

    @staticmethod
    def _generalized_to_coordinate_velocity(qpos: Tensor, velocity: Tensor) -> Tensor:
        zero = velocity[:, :1] * 0.0
        angular_quaternion = torch.cat((zero, velocity[:, 3:6]), dim=-1)
        quaternion_velocity = 0.5 * _quaternion_multiply_wxyz(
            angular_quaternion, qpos[:, 3:7]
        )
        return torch.cat((velocity[:, :3], quaternion_velocity, velocity[:, 6:]), dim=-1)

    def decode_contact_consistent_velocity(
        self,
        qpos: Tensor,
        q_velocity: Tensor,
        contact_surface: Tensor,
        contact_local_offset: Tensor,
        stationary_contact: Tensor,
    ) -> Tensor:
        """Construct qdot in the feasible velocity space of material contacts."""

        q_velocity = self.tangent_q_velocity(qpos, q_velocity)
        generalized = self._coordinate_to_generalized_velocity(qpos, q_velocity)
        points = self.contact_points(qpos, contact_surface, contact_local_offset)
        jacobian = self.fk.point_geometric_jacobian(qpos, points, CONTACT_BODY_INDEX)
        row_mask = stationary_contact[..., None].expand(-1, -1, 3).reshape(len(qpos), -1).to(qpos)
        jacobian = jacobian.reshape(len(qpos), 3 * len(CONTACT_PARTS), 35) * row_mask[..., None]
        # The velocity coordinates are decoded in this instantaneous feasible
        # basis. Detaching the basis avoids unnecessary second-order FK terms;
        # the returned velocity remains differentiable with respect to the
        # predicted free coordinates.
        jacobian = jacobian.detach()
        identity = torch.eye(3 * len(CONTACT_PARTS), dtype=qpos.dtype, device=qpos.device)
        system = jacobian @ jacobian.transpose(-1, -2) + 1.0e-8 * identity[None]
        violation = jacobian @ generalized[..., None]
        correction = jacobian.transpose(-1, -2) @ torch.linalg.solve(system, violation)
        feasible = generalized - correction[..., 0]
        return self._generalized_to_coordinate_velocity(qpos, feasible)

    def boundary_stationary_contacts(
        self, persistent_support: Tensor, interaction_phase: Tensor
    ) -> Tensor:
        stationary = persistent_support
        if len(self.phase_topologies):
            phase_index = torch.round(
                interaction_phase.clamp(0.0, 1.0) * (len(self.phase_topologies) - 1)
            ).to(torch.long)
            next_index = (phase_index + 1).clamp_max(len(self.phase_topologies) - 1)
            next_persistent = self.phase_topologies.to(persistent_support.device)[next_index, 1]
            has_next = phase_index < len(self.phase_topologies) - 1
            stationary = stationary | (next_persistent & has_next[:, None])
        return stationary

    def _apply_tangent_delta(self, qpos: Tensor, delta: Tensor) -> Tensor:
        root_position = qpos[:, :3] + delta[:, :3]
        rotation_vector = delta[:, 3:6]
        angle = torch.linalg.vector_norm(rotation_vector, dim=-1, keepdim=True)
        vector_scale = 0.5 * torch.sinc(angle / (2.0 * torch.pi))
        delta_quaternion = torch.cat((torch.cos(0.5 * angle), vector_scale * rotation_vector), dim=-1)
        root_quaternion = F.normalize(
            _quaternion_multiply_wxyz(delta_quaternion, qpos[:, 3:7]), dim=-1
        )
        joints = qpos[:, 7:] + delta[:, 6:]
        joints = torch.maximum(torch.minimum(joints, self.fk.joint_upper), self.fk.joint_lower)
        return torch.cat((root_position, root_quaternion, joints), dim=-1)

    def constrain_persistent_contacts(
        self,
        qpos: Tensor,
        contact_surface: Tensor,
        contact_local_offset: Tensor,
        persistent: Tensor,
        anchor: Tensor,
        *,
        iterations: int | None = None,
    ) -> Tensor:
        """Impose persistent material-point constraints with differentiable DLS IK."""

        constraint_iterations = self.persistent_constraint_iterations if iterations is None else int(iterations)
        if constraint_iterations < 0:
            raise ValueError("iterations must be non-negative")
        if constraint_iterations == 0:
            return qpos
        row_mask = persistent[..., None].expand(-1, -1, 3).reshape(len(qpos), -1).to(qpos)
        identity = torch.eye(3 * len(CONTACT_PARTS), dtype=qpos.dtype, device=qpos.device)
        identity = identity.expand(len(qpos), -1, -1)
        constrained = qpos
        for _ in range(constraint_iterations):
            points = self.contact_points(constrained, contact_surface, contact_local_offset)
            jacobian = self.fk.point_geometric_jacobian(constrained, points, CONTACT_BODY_INDEX)
            jacobian = jacobian.reshape(len(qpos), 3 * len(CONTACT_PARTS), 35) * row_mask[..., None]
            residual = (anchor - points).reshape(len(qpos), -1) * row_mask
            system = jacobian @ jacobian.transpose(-1, -2)
            system = system + self.persistent_constraint_damping**2 * identity
            delta = jacobian.transpose(-1, -2) @ torch.linalg.solve(system, residual[..., None])
            delta = delta[..., 0]
            root_step = torch.linalg.vector_norm(delta[:, :3], dim=-1)
            angular_step = torch.linalg.vector_norm(delta[:, 3:], dim=-1)
            scale = torch.minimum(
                (self.persistent_constraint_maximum_step / root_step.clamp_min(1.0e-8)).clamp_max(1.0),
                (self.persistent_constraint_maximum_step / angular_step.clamp_min(1.0e-8)).clamp_max(1.0),
            )
            constrained = self._apply_tangent_delta(constrained, scale[:, None] * delta)
        return constrained

    def synchronize_contact_targets(
        self,
        prediction: UnifiedInteractionPrediction,
        contact_target: Tensor,
    ) -> UnifiedInteractionPrediction:
        """Decode one q/contact keyframe against a shared set of contact targets.

        ``contact_target`` may be discretely selected from the terrain scan, but
        it never replaces FK geometry on its own.  The constrained q is the
        authoritative keyframe and all body/contact geometry is recomputed from
        that same q, keeping pose and contact inseparable.
        """

        if contact_target.shape != prediction.contact_position.shape:
            raise ValueError("contact_target must have shape [B,6,3]")
        constrained_contact = prediction.persistent_support | prediction.touchdown
        qpos = self.constrain_persistent_contacts(
            prediction.qpos,
            prediction.contact_surface,
            prediction.contact_local_offset,
            constrained_contact,
            contact_target,
        )
        position, rotation6d = self.fk(qpos)
        contact_position = self.contact_points(
            qpos, prediction.contact_surface, prediction.contact_local_offset
        )
        q_velocity = self.decode_contact_consistent_velocity(
            qpos,
            prediction.q_velocity,
            prediction.contact_surface,
            prediction.contact_local_offset,
            prediction.stationary_contact,
        )
        return UnifiedInteractionPrediction(
            qpos=qpos,
            q_velocity=q_velocity,
            stationary_contact=prediction.stationary_contact,
            keypoint_position=position,
            keypoint_rotation6d=rotation6d,
            contact_logits=prediction.contact_logits,
            active_contact=prediction.active_contact,
            touchdown_logits=prediction.touchdown_logits,
            touchdown=prediction.touchdown,
            persistent_logits=prediction.persistent_logits,
            persistent_support=prediction.persistent_support,
            surface_logits=prediction.surface_logits,
            contact_surface=prediction.contact_surface,
            contact_local_offset=prediction.contact_local_offset,
            contact_position=contact_position,
            contact_velocity=self.contact_point_velocity(
                qpos,
                q_velocity,
                prediction.contact_surface,
                prediction.contact_local_offset,
            ),
            duration=prediction.duration,
        )

    def decode_topology(
        self,
        current_contact: Tensor,
        contact_logits: Tensor,
        persistent_logits: Tensor,
        touchdown_logits: Tensor,
        interaction_phase: Tensor | None = None,
    ) -> tuple[Tensor, Tensor, Tensor]:
        """Jointly select the most likely transition supported by training data."""

        if not len(self.topology_transitions):
            active = contact_logits >= 0.0
            persistent = (persistent_logits >= 0.0) & (current_contact > 0.5) & active
            return active, persistent, active & ~persistent
        transition = self.topology_transitions.to(contact_logits.device)
        score = self.topology_scores(current_contact, contact_logits, persistent_logits, touchdown_logits)
        selected = transition[score.argmax(dim=-1)]
        if len(self.phase_topologies) and interaction_phase is not None:
            phase_index = torch.round(
                interaction_phase.clamp(0.0, 1.0) * (len(self.phase_topologies) - 1)
            ).to(torch.long)
            scheduled = self.phase_topologies.to(contact_logits.device)[phase_index]
            compatible = (scheduled[:, 0] == (current_contact > 0.5)).all(dim=-1)
            selected = torch.where(compatible[:, None, None], scheduled, selected)
        return selected[:, 3], selected[:, 1], selected[:, 2]

    def topology_scores(
        self,
        current_contact: Tensor,
        contact_logits: Tensor,
        persistent_logits: Tensor,
        touchdown_logits: Tensor,
    ) -> Tensor:
        if not len(self.topology_transitions):
            raise ValueError("topology scores require a non-empty transition table")
        transition = self.topology_transitions.to(contact_logits.device)
        candidate = torch.stack((transition[:, 3], transition[:, 1], transition[:, 2]), dim=1)
        logits = torch.stack((contact_logits, persistent_logits, touchdown_logits), dim=1)
        log_likelihood = (
            candidate[None] * F.logsigmoid(logits[:, None])
            + ~candidate[None] * F.logsigmoid(-logits[:, None])
        ).sum(dim=(2, 3))
        current = current_contact > 0.5
        start_mismatch = (transition[None, :, 0] != current[:, None]).sum(dim=-1)
        return log_likelihood - 100.0 * start_mismatch

    def forward(
        self,
        current_qpos: Tensor,
        current_contact: Tensor,
        current_contact_position: Tensor,
        current_contact_surface: Tensor,
        scan: Tensor,
        previous_persistent: Tensor | None = None,
        previous_touchdown: Tensor | None = None,
        interaction_phase: Tensor | None = None,
        current_q_velocity: Tensor | None = None,
        *,
        apply_persistent_constraint: bool = True,
        current_contact_local_offset: Tensor | None = None,
    ) -> UnifiedInteractionPrediction:
        if current_contact_position.shape[-2:] != (len(CONTACT_PARTS), 3):
            raise ValueError("current_contact_position must have shape [B,6,3]")
        if previous_persistent is None:
            previous_persistent = torch.zeros_like(current_contact)
        if previous_touchdown is None:
            previous_touchdown = torch.zeros_like(current_contact)
        if interaction_phase is None:
            interaction_phase = current_qpos.new_zeros((len(current_qpos),))
        if current_q_velocity is None:
            current_q_velocity = torch.zeros_like(current_qpos)
        if current_q_velocity.shape != current_qpos.shape:
            raise ValueError("current_q_velocity and current_qpos must share [B,36]")
        if self.predict_boundary_velocity:
            current_q_velocity = self.tangent_q_velocity(current_qpos, current_q_velocity)
        if previous_persistent.shape != current_contact.shape or previous_touchdown.shape != current_contact.shape:
            raise ValueError("previous interaction masks must match current_contact")
        if interaction_phase.shape != (len(current_qpos),):
            raise ValueError("interaction_phase must have shape [B]")
        q_feature = ((current_qpos - self.q_mean) / self.q_std).clamp(-10.0, 10.0)
        anchors = current_contact_position * current_contact[..., None]
        if (((current_contact_surface < 0) | (current_contact_surface >= self.surface_count)) &
                current_contact.bool()).any():
            raise ValueError('Observed Newton surface is outside predictor vocabulary; cannot clamp it into ground/top')
        current_surface = F.one_hot(
            current_contact_surface.clamp(0, self.surface_count - 1), self.surface_count
        ).to(current_qpos.dtype) * current_contact[..., None]
        current_position, current_rotation6d = self.fk(current_qpos)
        current_rotation = _matrix_from_rotation6d(current_rotation6d)
        current_local_offsets = []
        for part, body in enumerate(CONTACT_BODY_INDEX):
            surface = current_contact_surface[:, part].clamp(0, self.surface_count - 1)
            measured = torch.einsum(
                "bij,bj->bi",
                current_rotation[:, body].transpose(-1, -2),
                current_position[:, body] - current_contact_position[:, part],
            )
            canonical = self.endpoint_offsets[part, surface]
            inferred = torch.where(current_contact[:, part : part + 1] > 0.5, measured, canonical)
            if self.remember_material_contacts and current_contact_local_offset is not None:
                if current_contact_local_offset.shape != current_contact_position.shape:
                    raise ValueError('Material point memory must have shape [B,6,3]')
                inferred = current_contact_local_offset[:, part]
            current_local_offsets.append(canonical if self.fixed_material_contacts else inferred)
        current_local_offset = torch.stack(current_local_offsets, dim=1)
        state_values = (
            q_feature,
            current_contact,
            anchors.flatten(1),
            current_local_offset.flatten(1),
            current_surface.flatten(1),
            previous_persistent,
            previous_touchdown,
        )
        if self.use_phase_condition:
            state_values += (interaction_phase[:, None],)
        if self.predict_boundary_velocity:
            state_values += (current_q_velocity.clamp(-10.0, 10.0),)
        state = self.state_encoder(torch.cat(state_values, dim=-1))
        scan_feature = self.scan_encoder((scan - self.scan_mean) / self.scan_std)
        hidden = self.trunk(torch.cat((state, scan_feature), dim=-1))
        if self.use_phase_condition:
            hidden = hidden + self.topology_encoder(self.phase_topology_condition(current_contact, interaction_phase))
        raw = self.interaction_head(hidden)
        cursor = 0
        q_residual = raw[:, cursor : cursor + 36]
        cursor += 36
        if len(self.phase_q_feature_adapter):
            phase_index = torch.round(
                interaction_phase.clamp(0.0, 1.0) * (len(self.phase_q_feature_adapter) - 1)
            ).to(torch.long)
            q_residual = q_residual + torch.einsum(
                "bi,boi->bo", hidden, self.phase_q_feature_adapter[phase_index]
            )
        contact_logits = raw[:, cursor : cursor + len(CONTACT_PARTS)] + 2.0 * (2.0 * current_contact - 1.0)
        cursor += len(CONTACT_PARTS)
        touchdown_logits = raw[:, cursor : cursor + len(CONTACT_PARTS)] - 2.0
        cursor += len(CONTACT_PARTS)
        persistent_logits = raw[:, cursor : cursor + len(CONTACT_PARTS)] + 2.0 * (2.0 * current_contact - 1.0)
        cursor += len(CONTACT_PARTS)
        surface_logits = raw[:, cursor : cursor + len(CONTACT_PARTS) * self.surface_count].reshape(
            -1, len(CONTACT_PARTS), self.surface_count
        ) + 2.0 * current_surface
        cursor += len(CONTACT_PARTS) * self.surface_count
        contact_offset_residual = raw[:, cursor : cursor + len(CONTACT_PARTS) * 3].reshape(
            -1, len(CONTACT_PARTS), 3
        )
        cursor += len(CONTACT_PARTS) * 3
        duration = torch.exp(raw[:, cursor] * self.duration_log_std + self.duration_log_mean).clamp(
            self.minimum_duration_s, self.maximum_duration_s
        )
        cursor += 1
        q_velocity = torch.zeros_like(current_qpos)
        if self.predict_boundary_velocity:
            q_velocity_scale = current_qpos.new_tensor(
                (0.5, 0.5, 0.5, 1.0, 1.0, 1.0, 1.0) + (3.0,) * 29
            )
            q_velocity = q_velocity_scale * torch.tanh(raw[:, cursor : cursor + 36])
        if self.predict_boundary_velocity and len(self.phase_q_velocity_prototypes):
            velocity_phase_index = torch.round(
                interaction_phase.clamp(0.0, 1.0) * (len(self.phase_q_velocity_prototypes) - 1)
            ).to(torch.long)
            q_velocity = q_velocity + self.phase_q_velocity_prototypes.to(q_velocity.device)[
                velocity_phase_index
            ]
        active_contact, persistent_support, touchdown = self.decode_topology(
            current_contact, contact_logits, persistent_logits, touchdown_logits, interaction_phase
        )
        persistent = persistent_support & (current_contact > 0.5)
        qpos = self._apply_q_delta(current_qpos, q_residual, interaction_phase, current_contact)
        contact_surface = surface_logits.argmax(dim=-1)
        contact_surface = torch.where(persistent, current_contact_surface, contact_surface)
        predicted_canonical_offset = self.endpoint_offsets[
            torch.arange(len(CONTACT_PARTS), device=qpos.device)[None], contact_surface
        ]
        offset_base = torch.where(
            current_contact[..., None] > 0.5, current_local_offset, predicted_canonical_offset
        )
        if self.remember_material_contacts:
            # A new touchdown starts a new material-point choice. Adding to the
            # previous point on every touchdown makes an unbounded random walk.
            # Persistent contacts still preserve memory exactly below.
            offset_base = predicted_canonical_offset
        contact_local_offset = offset_base + self.maximum_contact_offset_delta_m * torch.tanh(contact_offset_residual)
        contact_local_offset = torch.where(persistent[..., None], current_local_offset, contact_local_offset)
        if self.fixed_material_contacts:
            contact_local_offset = predicted_canonical_offset
        if apply_persistent_constraint:
            qpos = self.constrain_persistent_contacts(
                qpos, contact_surface, contact_local_offset, persistent, current_contact_position
            )
        position, rotation6d = self.fk(qpos)
        contact_position = self.contact_points(qpos, contact_surface, contact_local_offset)
        stationary_contact = self.boundary_stationary_contacts(
            persistent_support, interaction_phase
        )
        contact_velocity = torch.zeros_like(contact_position)
        if self.predict_boundary_velocity:
            q_velocity = self.tangent_q_velocity(qpos, q_velocity)
            q_velocity = self.decode_contact_consistent_velocity(
                qpos, q_velocity, contact_surface, contact_local_offset, stationary_contact
            )
            contact_velocity = self.contact_point_velocity(
                qpos, q_velocity, contact_surface, contact_local_offset
            )
        return UnifiedInteractionPrediction(
            qpos=qpos,
            q_velocity=q_velocity,
            stationary_contact=stationary_contact,
            keypoint_position=position,
            keypoint_rotation6d=rotation6d,
            contact_logits=contact_logits,
            active_contact=active_contact,
            touchdown_logits=touchdown_logits,
            touchdown=touchdown,
            persistent_logits=persistent_logits,
            persistent_support=persistent_support,
            surface_logits=surface_logits,
            contact_surface=contact_surface,
            contact_local_offset=contact_local_offset,
            contact_position=contact_position,
            contact_velocity=contact_velocity,
            duration=duration,
        )


def unified_interaction_loss(
    prediction: UnifiedInteractionPrediction,
    *,
    target_qpos: Tensor,
    target_contact: Tensor,
    target_touchdown: Tensor,
    target_persistent: Tensor,
    target_surface: Tensor,
    target_contact_position: Tensor,
    target_duration: Tensor,
    current_contact: Tensor,
    current_contact_position: Tensor,
    target_contact_rotation6d: Tensor | None = None,
    contact_orientation_weight: float = 0.0,
    balance_contact_parts: bool = False,
    active_geometry_weight: float = 2.0,
    persistent_anchor_weight: float = 5.0,
    topology_choice_penalty: Tensor | None = None,
    surface_feasibility_penalty: Tensor | None = None,
    inactive_clearance_penalty: Tensor | None = None,
    target_q_velocity: Tensor | None = None,
    q_velocity_weight: float = 1.0,
    contact_velocity_weight: float = 5.0,
    target_stationary_contact: Tensor | None = None,
) -> UnifiedInteractionLoss:
    """Supervise pose and contact together, including support-anchor invariance."""

    q_pose = (
        ((prediction.qpos[:, :3] - target_qpos[:, :3]) / 0.02).square().mean()
        + (1.0 - (prediction.qpos[:, 3:7] * target_qpos[:, 3:7]).sum(dim=-1).abs()).mean()
        + ((prediction.qpos[:, 7:] - target_qpos[:, 7:]) / 0.1).square().mean()
    )
    contact_state = F.binary_cross_entropy_with_logits(prediction.contact_logits, target_contact)
    touchdown = F.binary_cross_entropy_with_logits(prediction.touchdown_logits, target_touchdown)
    persistent_state = F.binary_cross_entropy_with_logits(prediction.persistent_logits, target_persistent)
    active = target_contact > 0.5
    valid_geometry = active & (target_surface >= 0)
    def contact_part_mean(value: Tensor, mask: Tensor) -> Tensor:
        if not balance_contact_parts:
            return value[mask].mean()
        numeric_mask = mask.to(value.dtype)
        count = numeric_mask.sum(dim=0)
        mean = (value * numeric_mask).sum(dim=0) / count.clamp_min(1.0)
        valid_part = count > 0.0
        return (mean * valid_part).sum() / valid_part.sum().clamp_min(1)

    if bool(valid_geometry.any()):
        surface = F.cross_entropy(prediction.surface_logits[valid_geometry], target_surface[valid_geometry])
        geometry_error = (
            (prediction.contact_position - target_contact_position) / 0.01
        ).square().mean(dim=-1)
        active_geometry = contact_part_mean(geometry_error, valid_geometry)
    else:
        surface = prediction.surface_logits.sum() * 0.0
        active_geometry = prediction.contact_position.sum() * 0.0
    persistent = valid_geometry & (target_persistent > 0.5)
    if bool(persistent.any()):
        persistent_error = (
            (prediction.contact_position - current_contact_position) / 0.005
        ).square().mean(dim=-1)
        persistent_anchor = contact_part_mean(persistent_error, persistent)
    else:
        persistent_anchor = prediction.contact_position.sum() * 0.0
    duration = ((torch.log(prediction.duration) - torch.log(target_duration)) / 0.1).square().mean()
    topology_choice = prediction.qpos.sum() * 0.0 if topology_choice_penalty is None else topology_choice_penalty
    surface_feasibility = (
        prediction.qpos.sum() * 0.0 if surface_feasibility_penalty is None else surface_feasibility_penalty
    )
    inactive_clearance = (
        prediction.qpos.sum() * 0.0 if inactive_clearance_penalty is None else inactive_clearance_penalty
    )
    if topology_choice.ndim != 0 or surface_feasibility.ndim != 0 or inactive_clearance.ndim != 0:
        raise ValueError("geometry penalties must be scalar")
    if min(contact_orientation_weight, active_geometry_weight, persistent_anchor_weight) < 0.0:
        raise ValueError("contact loss weights must be non-negative")
    if target_contact_rotation6d is None:
        contact_orientation = prediction.qpos.sum() * 0.0
    else:
        contact_orientation, _ = contact_rotation_losses(
            prediction.keypoint_rotation6d[:, CONTACT_BODY_INDEX],
            target_contact_rotation6d,
            valid_geometry,
            balance_contact_parts=balance_contact_parts,
        )
    if target_q_velocity is None:
        q_velocity = prediction.q_velocity.sum() * 0.0
    else:
        velocity_scale = prediction.q_velocity.new_tensor(
            (0.2, 0.2, 0.2, 0.5, 0.5, 0.5, 0.5) + (1.0,) * 29
        )
        q_velocity = ((prediction.q_velocity - target_q_velocity) / velocity_scale).square().mean()
    stationary = target_persistent > 0.5 if target_stationary_contact is None else target_stationary_contact > 0.5
    if bool(stationary.any()):
        contact_speed = prediction.contact_velocity.square().sum(dim=-1)
        contact_velocity = contact_part_mean(contact_speed / 0.05**2, stationary)
    else:
        contact_velocity = prediction.contact_velocity.sum() * 0.0
    if min(q_velocity_weight, contact_velocity_weight) < 0.0:
        raise ValueError("velocity loss weights must be non-negative")
    total = q_pose + contact_state + touchdown + persistent_state + surface
    total = total + active_geometry_weight * active_geometry
    total = total + persistent_anchor_weight * persistent_anchor
    total = total + contact_orientation_weight * contact_orientation
    total = total + q_velocity_weight * q_velocity + contact_velocity_weight * contact_velocity
    total = total + duration + 2.0 * topology_choice + 5.0 * surface_feasibility + 10.0 * inactive_clearance
    return UnifiedInteractionLoss(
        total,
        q_pose,
        contact_state,
        touchdown,
        persistent_state,
        surface,
        active_geometry,
        persistent_anchor,
        duration,
        topology_choice,
        surface_feasibility,
        inactive_clearance,
        contact_orientation,
        q_velocity,
        contact_velocity,
    )


class InteractionQInfiller(ContactPlanQInfiller):
    """Connect complete interaction boundaries while keeping exact endpoint q."""

    def __init__(
        self,
        *args,
        contact_constraint_iterations: int = 0,
        contact_constraint_damping: float = 1.0e-3,
        contact_constraint_maximum_step: float = 0.25,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.contact_constraint_iterations = int(contact_constraint_iterations)
        self.contact_constraint_damping = float(contact_constraint_damping)
        self.contact_constraint_maximum_step = float(contact_constraint_maximum_step)
        if self.contact_constraint_iterations < 0:
            raise ValueError("contact constraint iterations must be non-negative")
        if self.contact_constraint_damping <= 0.0:
            raise ValueError("contact constraint damping must be positive")
        if self.contact_constraint_maximum_step <= 0.0:
            raise ValueError("contact constraint maximum step must be positive")

    def _trajectory_points(self, qpos: Tensor, local_offset: Tensor) -> Tensor:
        position, rotation6d = self.fk(qpos)
        rotation = _matrix_from_rotation6d(rotation6d)
        points = []
        for part, body in enumerate(CONTACT_BODY_INDEX):
            points.append(
                position[..., body, :]
                - torch.einsum("...ij,...j->...i", rotation[..., body, :, :], local_offset[..., part, :])
            )
        return torch.stack(points, dim=-2)

    def _apply_flat_tangent_delta(self, qpos: Tensor, delta: Tensor) -> Tensor:
        root_position = qpos[:, :3] + delta[:, :3]
        rotation_vector = delta[:, 3:6]
        angle = torch.linalg.vector_norm(rotation_vector, dim=-1, keepdim=True)
        delta_quaternion = torch.cat(
            (torch.cos(0.5 * angle), 0.5 * torch.sinc(angle / (2.0 * torch.pi)) * rotation_vector), dim=-1
        )
        root_quaternion = F.normalize(
            _quaternion_multiply_wxyz(delta_quaternion, qpos[:, 3:7]), dim=-1
        )
        joints = qpos[:, 7:] + delta[:, 6:]
        joints = torch.maximum(torch.minimum(joints, self.fk.joint_upper), self.fk.joint_lower)
        return torch.cat((root_position, root_quaternion, joints), dim=-1)

    def constrain_contact_trajectory(
        self,
        qpos: Tensor,
        local_offset: Tensor,
        active_constraint: Tensor,
        anchor: Tensor,
        constraint_strength: Tensor | None = None,
        *,
        iterations: int | None = None,
    ) -> Tensor:
        """Constrain every active material contact point inside the trajectory."""

        constraint_iterations = self.contact_constraint_iterations if iterations is None else int(iterations)
        if constraint_iterations < 0:
            raise ValueError("iterations must be non-negative")
        if constraint_iterations == 0:
            return qpos
        batch, frames = qpos.shape[:2]
        flat_q = qpos.reshape(batch * frames, 36)
        flat_offset = local_offset.reshape(batch * frames, len(CONTACT_PARTS), 3)
        flat_anchor = anchor.reshape(batch * frames, len(CONTACT_PARTS), 3)
        row_mask = active_constraint[..., None].expand(-1, -1, -1, 3).reshape(batch * frames, -1).to(qpos)
        if constraint_strength is None:
            constraint_strength = active_constraint.to(qpos.dtype)
        row_strength = (
            constraint_strength[..., None]
            .expand(-1, -1, -1, 3)
            .reshape(batch * frames, -1)
            .to(qpos)
        )
        identity = torch.eye(3 * len(CONTACT_PARTS), dtype=qpos.dtype, device=qpos.device)
        identity = identity.expand(batch * frames, -1, -1)
        constrained = flat_q
        for _ in range(constraint_iterations):
            points = self._trajectory_points(constrained, flat_offset)
            jacobian = self.fk.point_geometric_jacobian(constrained, points, CONTACT_BODY_INDEX)
            jacobian = jacobian.reshape(batch * frames, 3 * len(CONTACT_PARTS), 35) * row_mask[..., None]
            residual = (flat_anchor - points).reshape(batch * frames, -1) * row_strength
            system = jacobian @ jacobian.transpose(-1, -2)
            system = system + self.contact_constraint_damping**2 * identity
            delta = jacobian.transpose(-1, -2) @ torch.linalg.solve(system, residual[..., None])
            delta = delta[..., 0]
            root_step = torch.linalg.vector_norm(delta[:, :3], dim=-1)
            angular_step = torch.linalg.vector_norm(delta[:, 3:], dim=-1)
            scale = torch.minimum(
                (self.contact_constraint_maximum_step / root_step.clamp_min(1.0e-8)).clamp_max(1.0),
                (self.contact_constraint_maximum_step / angular_step.clamp_min(1.0e-8)).clamp_max(1.0),
            )
            constrained = self._apply_flat_tangent_delta(constrained, scale[:, None] * delta)
        return constrained.reshape(batch, frames, 36)

    def forward(
        self,
        scan: Tensor,
        phase: Tensor,
        start_qpos: Tensor,
        end: UnifiedInteractionPrediction,
        start_contact: Tensor,
        base_qpos: Tensor | None = None,
        start_contact_position: Tensor | None = None,
        start_q_velocity: Tensor | None = None,
        *,
        apply_contact_constraint: bool = True,
        contact_constraint_iterations: int | None = None,
    ) -> InfillerOutput:
        if base_qpos is None:
            u = phase[..., None]
            flip_end_quaternion = (
                (start_qpos[:, 3:7] * end.qpos[:, 3:7]).sum(dim=-1, keepdim=True) < 0.0
            )
            end_quaternion = torch.where(
                flip_end_quaternion,
                -end.qpos[:, 3:7],
                end.qpos[:, 3:7],
            )
            aligned_end_qpos = torch.cat((end.qpos[:, :3], end_quaternion, end.qpos[:, 7:]), dim=-1)
            if start_q_velocity is None:
                base_qpos = (1.0 - u) * start_qpos[:, None] + u * aligned_end_qpos[:, None]
            else:
                if start_q_velocity.shape != start_qpos.shape:
                    raise ValueError("start_q_velocity and start_qpos must share [B,36]")
                start_velocity = UnifiedInteractionPredictor.tangent_q_velocity(
                    start_qpos, start_q_velocity
                )
                end_velocity = UnifiedInteractionPredictor.tangent_q_velocity(end.qpos, end.q_velocity)
                end_velocity = torch.cat(
                    (
                        end_velocity[:, :3],
                        torch.where(flip_end_quaternion, -end_velocity[:, 3:7], end_velocity[:, 3:7]),
                        end_velocity[:, 7:],
                    ),
                    dim=-1,
                )
                start_tangent = start_velocity * end.duration[:, None]
                end_tangent = end_velocity * end.duration[:, None]
                u2, u3 = u.square(), u.pow(3)
                h00 = 2.0 * u3 - 3.0 * u2 + 1.0
                h10 = u3 - 2.0 * u2 + u
                h01 = -2.0 * u3 + 3.0 * u2
                h11 = u3 - u2
                base_qpos = (
                    h00 * start_qpos[:, None]
                    + h10 * start_tangent[:, None]
                    + h01 * aligned_end_qpos[:, None]
                    + h11 * end_tangent[:, None]
                )
            base_qpos = torch.cat(
                (base_qpos[..., :3], F.normalize(base_qpos[..., 3:7], dim=-1), base_qpos[..., 7:]),
                dim=-1,
            )
        touchdown = end.touchdown.to(scan.dtype)
        plan = ContactTransitionPlan(
            action_logits=scan.new_empty((len(scan), 0)),
            action_index=torch.zeros(len(scan), dtype=torch.long, device=scan.device),
            touchdown=touchdown,
            end_contact=end.active_contact.to(scan.dtype),
            target_position=end.contact_position,
            target_rotation6d=end.keypoint_rotation6d[:, CONTACT_BODY_INDEX],
            surface_logits=end.surface_logits,
            target_surface=end.contact_surface,
            duration=end.duration,
        )
        output = super().forward(scan, phase, base_qpos, start_qpos, end.qpos, plan, start_contact)
        constraint_iterations = (
            self.contact_constraint_iterations
            if contact_constraint_iterations is None
            else int(contact_constraint_iterations)
        )
        if constraint_iterations < 0:
            raise ValueError("contact_constraint_iterations must be non-negative")
        if apply_contact_constraint and constraint_iterations > 0:
            if start_contact_position is None:
                raise ValueError("start_contact_position is required for constrained infilling")
            start_position, start_rotation6d = self.fk(start_qpos)
            start_rotation = _matrix_from_rotation6d(start_rotation6d)
            start_offsets = []
            for part, body in enumerate(CONTACT_BODY_INDEX):
                start_offsets.append(
                    torch.einsum(
                        "bij,bj->bi",
                        start_rotation[:, body].transpose(-1, -2),
                        start_position[:, body] - start_contact_position[:, part],
                    )
                )
            start_offset = torch.stack(start_offsets, dim=1)
            start_active = start_contact > 0.5
            persistent = end.persistent_support & start_active & end.active_contact
            liftoff = start_active & ~persistent
            touchdown_mask = end.active_contact & ~persistent
            # Keep the same Jacobian rows throughout the segment and smoothly
            # vary only their target residual.  This is the exact v51 contact
            # transition rule and also avoids switching the IK system mid-segment.
            release = (1.0 - phase[..., None] / 0.2).clamp(0.0, 1.0)
            acquire = ((phase[..., None] - 0.8) / 0.2).clamp(0.0, 1.0)
            release = release.square() * (3.0 - 2.0 * release)
            acquire = acquire.square() * (3.0 - 2.0 * acquire)
            active_part = persistent | liftoff | touchdown_mask
            active_constraint = active_part[:, None].expand(-1, phase.shape[1], -1)
            constraint_strength = (
                persistent[:, None].to(phase.dtype)
                + liftoff[:, None].to(phase.dtype) * release
                + touchdown_mask[:, None].to(phase.dtype) * acquire
            )
            use_end = touchdown_mask[:, None]
            local_offset = torch.where(
                use_end[..., None], end.contact_local_offset[:, None], start_offset[:, None]
            ).expand(-1, phase.shape[1], -1, -1)
            anchor = torch.where(
                use_end[..., None], end.contact_position[:, None], start_contact_position[:, None]
            ).expand(-1, phase.shape[1], -1, -1)
            unconstrained_q = output.auxiliary_qpos
            constraint_kwargs = (
                {}
                if contact_constraint_iterations is None
                else {"iterations": constraint_iterations}
            )
            constrained_q = self.constrain_contact_trajectory(
                unconstrained_q,
                local_offset,
                active_constraint,
                anchor,
                constraint_strength,
                **constraint_kwargs,
            )
            if start_q_velocity is not None:
                # The independently solved IK correction is generally
                # first-order near an event boundary and would overwrite the
                # Hermite boundary tangent.  Fade it only for the C1/Hermite
                # path.  The legacy v51 path has no prescribed boundary
                # velocity and applies its material-contact constraint
                # directly over the complete segment.
                fade_in = (phase / 0.1).clamp(0.0, 1.0)
                fade_out = ((1.0 - phase) / 0.1).clamp(0.0, 1.0)
                fade_in = fade_in.square() * (3.0 - 2.0 * fade_in)
                fade_out = fade_out.square() * (3.0 - 2.0 * fade_out)
                correction_weight = (fade_in * fade_out)[..., None]
                constrained_q = unconstrained_q + correction_weight * (constrained_q - unconstrained_q)
            constrained_q = torch.cat(
                (
                    constrained_q[..., :3],
                    F.normalize(constrained_q[..., 3:7], dim=-1),
                    constrained_q[..., 7:],
                ),
                dim=-1,
            )
            position, rotation6d = self.fk(constrained_q)
            output = InfillerOutput(position, rotation6d, output.contact_logits, constrained_q)
        start = start_contact[:, None]
        finish = end.active_contact.to(scan.dtype)[:, None]
        transition = torch.sigmoid((phase[..., None] - 0.5) * 16.0)
        probability = (1.0 - transition) * start + transition * finish
        logits = torch.logit(probability.clamp(1.0e-5, 1.0 - 1.0e-5))
        logits = torch.where((phase <= 0.0)[..., None], 12.0 * (2.0 * start - 1.0), logits)
        logits = torch.where((phase >= 1.0)[..., None], 12.0 * (2.0 * finish - 1.0), logits)
        return InfillerOutput(output.keypoint_position, output.keypoint_rotation6d, logits, output.auxiliary_qpos)


def _trajectory_contact_points(
    output: InfillerOutput,
    start_local_offset: Tensor,
    end_local_offset: Tensor,
    phase: Tensor,
) -> Tensor:
    rotation = _matrix_from_rotation6d(output.keypoint_rotation6d)
    u = phase[..., None, None]
    local_offset = (1.0 - u) * start_local_offset[:, None] + u * end_local_offset[:, None]
    points = []
    for part, body in enumerate(CONTACT_BODY_INDEX):
        rotated = torch.einsum("btij,btj->bti", rotation[:, :, body], local_offset[:, :, part])
        points.append(output.keypoint_position[:, :, body] - rotated)
    return torch.stack(points, dim=2)


def project_interaction_q_trajectory(
    output: InfillerOutput,
    *,
    fk: nn.Module,
    collision_geometry: nn.Module,
    phase: Tensor,
    start_contact: Tensor,
    start_contact_position: Tensor,
    end: UnifiedInteractionPrediction,
    box_center: Tensor,
    box_rotation: Tensor,
    box_half_extents: Tensor,
    ground_height: Tensor,
    steps: int = 120,
    learning_rate: float = 0.01,
    maximum_endpoint_root_shift_m: float = 0.15,
    endpoint_root_shift_weight: float = 5.0,
    collect_diagnostics: bool = True,
) -> InteractionProjectionResult:
    """Project a generated interaction in q-space onto support and collision constraints.

    The current boundary (frame zero) is immutable.  The predicted next q is
    allowed to move because otherwise an inaccurate persistent endpoint makes
    the constraints inconsistent.  Touchdown points remain fixed targets and
    persistent points remain fixed at their current world anchors.
    """

    from .neural_infiller import full_geometry_box_penetration

    if steps < 0:
        raise ValueError("steps must be non-negative")
    if maximum_endpoint_root_shift_m < 0.0:
        raise ValueError("maximum endpoint root shift must be non-negative")
    if endpoint_root_shift_weight < 0.0:
        raise ValueError("endpoint root shift weight must be non-negative")
    initial_q = output.auxiliary_qpos.detach()
    batch, frames, _ = initial_q.shape
    if phase.shape != (batch, frames):
        raise ValueError("phase must match the q trajectory batch and frame dimensions")

    start_position, start_rotation6d = fk(initial_q[:, 0])
    start_rotation = _matrix_from_rotation6d(start_rotation6d)
    start_offsets = []
    for part, body in enumerate(CONTACT_BODY_INDEX):
        start_offsets.append(
            torch.einsum(
                "bij,bj->bi",
                start_rotation[:, body].transpose(-1, -2),
                start_position[:, body] - start_contact_position[:, part],
            )
        )
    start_offsets = torch.stack(start_offsets, dim=1).detach()

    start_active = start_contact > 0.5
    persistent = end.persistent_support & start_active & end.active_contact
    touchdown = end.active_contact & ~persistent
    liftoff = start_active & ~persistent
    phase3 = phase[..., None]
    anchor_mask = persistent[:, None].expand(-1, frames, -1).clone()
    anchor_mask |= liftoff[:, None] & (phase3 <= 0.2)
    anchor_mask |= touchdown[:, None] & (phase3 >= 0.8)
    end_point = end.contact_position.detach()
    box_local = torch.einsum(
        "bij,bpj->bpi", box_rotation.transpose(-1, -2), end_point - box_center[:, None]
    )
    box_local_xy = torch.maximum(
        torch.minimum(box_local[..., :2], box_half_extents[:, None, :2]),
        -box_half_extents[:, None, :2],
    )
    box_local_top = torch.cat(
        (box_local_xy, box_half_extents[:, None, 2:3].expand(-1, len(CONTACT_PARTS), -1)), dim=-1
    )
    box_surface_point = box_center[:, None] + torch.einsum("bij,bpj->bpi", box_rotation, box_local_top)
    ground_surface_point = end_point.clone()
    ground_surface_point[..., 2] = ground_height[:, None]
    end_surface_point = torch.where(
        (end.contact_surface == 1)[..., None], box_surface_point, ground_surface_point
    ).detach()
    touchdown_window = touchdown[:, None] & (phase3 >= 0.8)
    anchor_target = torch.where(
        touchdown_window[..., None],
        end_surface_point[:, None],
        start_contact_position[:, None],
    ).detach()
    contact_schedule = anchor_mask.to(initial_q.dtype)

    def evaluate(qpos: Tensor) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        position, rotation6d = fk(qpos)
        candidate = InfillerOutput(position, rotation6d, output.contact_logits, qpos)
        points = _trajectory_contact_points(candidate, start_offsets, end.contact_local_offset.detach(), phase)
        anchor_error = torch.linalg.vector_norm(points - anchor_target, dim=-1)
        collision_points, point_part = collision_geometry(fk, qpos)
        penetration = full_geometry_box_penetration(
            collision_points,
            point_part,
            contact_schedule,
            box_center=box_center,
            box_rotation=box_rotation,
            box_half_extents=box_half_extents,
            ground_height=ground_height,
        )
        return position, rotation6d, anchor_error, penetration

    def audit(qpos: Tensor, prefix: str) -> dict[str, float]:
        with torch.no_grad():
            _, _, anchor_error, penetration = evaluate(qpos)
            selected = anchor_error[anchor_mask]
            return {
                f"{prefix}_anchor_mean_cm": float(selected.mean().item() * 100.0) if selected.numel() else 0.0,
                f"{prefix}_anchor_max_cm": float(selected.max().item() * 100.0) if selected.numel() else 0.0,
                f"{prefix}_penetration_max_cm": float(penetration.max().item() * 100.0),
                f"{prefix}_collision_free_fraction": float((penetration.amax(dim=-1) <= 0.002).float().mean().item()),
            }

    diagnostics = audit(initial_q, "before") if collect_diagnostics else {}
    if collect_diagnostics:
        touchdown_snap = torch.linalg.vector_norm(end_surface_point - end_point, dim=-1)[touchdown]
        diagnostics["touchdown_surface_snap_mean_cm"] = (
            float(touchdown_snap.mean().item() * 100.0) if touchdown_snap.numel() else 0.0
        )
        diagnostics["touchdown_surface_snap_max_cm"] = (
            float(touchdown_snap.max().item() * 100.0) if touchdown_snap.numel() else 0.0
        )
    if steps == 0:
        if collect_diagnostics:
            diagnostics.update(audit(initial_q, "after"))
        return InteractionProjectionResult(output, diagnostics)

    variable = initial_q[:, 1:].clone().requires_grad_(True)
    optimizer = torch.optim.Adam((variable,), lr=learning_rate)
    initial_velocity = initial_q[:, 1:] - initial_q[:, :-1]
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        q_tail = _limit_endpoint_root_shift(variable, initial_q[:, -1, :3], maximum_endpoint_root_shift_m)
        quaternion = F.normalize(q_tail[..., 3:7], dim=-1)
        joints = torch.maximum(torch.minimum(q_tail[..., 7:], fk.joint_upper), fk.joint_lower)
        qpos = torch.cat((initial_q[:, :1], torch.cat((q_tail[..., :3], quaternion, joints), dim=-1)), dim=1)
        _, _, anchor_error, penetration = evaluate(qpos)
        selected = anchor_error[anchor_mask]
        anchor_loss = qpos.sum() * 0.0
        if selected.numel():
            normalized = selected / 0.005
            anchor_loss = normalized.square().mean() + 0.25 * normalized.square().max()
        frame_penetration = penetration.amax(dim=-1) / 0.005
        collision_loss = frame_penetration.square().mean() + 0.25 * frame_penetration.square().max()
        root_deviation = ((qpos[..., :3] - initial_q[..., :3]) / 0.05).square().mean()
        quaternion_deviation = 1.0 - (qpos[..., 3:7] * initial_q[..., 3:7]).sum(dim=-1).abs()
        joint_deviation = ((qpos[..., 7:] - initial_q[..., 7:]) / 0.2).square().mean()
        velocity = qpos[:, 1:] - qpos[:, :-1]
        velocity_deviation = ((velocity - initial_velocity) / 0.1).square().mean()
        excessive_endpoint_shift = _endpoint_root_shift_penalty(
            qpos, initial_q, maximum_endpoint_root_shift_m
        )
        loss = 10.0 * anchor_loss + 10.0 * collision_loss
        loss = loss + 0.05 * root_deviation + 0.05 * quaternion_deviation.mean()
        loss = loss + 0.02 * joint_deviation + 0.002 * velocity_deviation
        loss = loss + endpoint_root_shift_weight * excessive_endpoint_shift
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        q_tail = _limit_endpoint_root_shift(variable, initial_q[:, -1, :3], maximum_endpoint_root_shift_m)
        final_q = torch.cat(
            (
                initial_q[:, :1],
                torch.cat(
                    (
                        q_tail[..., :3],
                        F.normalize(q_tail[..., 3:7], dim=-1),
                        torch.maximum(torch.minimum(q_tail[..., 7:], fk.joint_upper), fk.joint_lower),
                    ),
                    dim=-1,
                ),
            ),
            dim=1,
        )
        position, rotation6d = fk(final_q)
        projected = InfillerOutput(position, rotation6d, output.contact_logits, final_q)
        if collect_diagnostics:
            diagnostics.update(audit(final_q, "after"))
            diagnostics["endpoint_root_shift_cm"] = float(
                torch.linalg.vector_norm(final_q[:, -1, :3] - initial_q[:, -1, :3], dim=-1).mean().item() * 100.0
            )
            diagnostics["q_rms_joint_shift_deg"] = float(
                torch.rad2deg(torch.sqrt(torch.mean((final_q[..., 7:] - initial_q[..., 7:]).square()))).item()
            )
    return InteractionProjectionResult(projected, diagnostics)


def interaction_infiller_loss(
    output: InfillerOutput,
    *,
    phase: Tensor,
    target_qpos: Tensor,
    start_qpos: Tensor,
    end: UnifiedInteractionPrediction,
    start_contact: Tensor,
    start_contact_position: Tensor,
    collision_penalty: Tensor,
    inactive_clearance_penalty: Tensor,
    target_contact_rotation6d: Tensor | None = None,
    persistent_anchor_weight: float = 5.0,
    touchdown_anchor_weight: float = 2.0,
    liftoff_anchor_weight: float = 2.0,
    collision_weight: float = 10.0,
    contact_orientation_weight: float = 0.0,
    contact_angular_velocity_weight: float = 0.0,
) -> InteractionInfillerLoss:
    """Enforce support timing and no-penetration while filling interactions.

    Collision and inactive-clearance values are supplied by the terrain
    geometry implementation, keeping this loss independent of one scan type.
    """

    if collision_penalty.ndim != 0 or inactive_clearance_penalty.ndim != 0:
        raise ValueError("collision and inactive-clearance penalties must be scalar")
    q_reconstruction = (
        ((output.auxiliary_qpos[..., :3] - target_qpos[..., :3]) / 0.02).square().mean()
        + (1.0 - (output.auxiliary_qpos[..., 3:7] * target_qpos[..., 3:7]).sum(dim=-1).abs()).mean()
        + ((output.auxiliary_qpos[..., 7:] - target_qpos[..., 7:]) / 0.1).square().mean()
    )
    endpoint = (
        (output.auxiliary_qpos[:, 0] - start_qpos).square().mean()
        + (output.auxiliary_qpos[:, -1] - end.qpos).square().mean()
    )
    start_active = start_contact > 0.5
    end_active = end.active_contact
    persistent = end.persistent_support & start_active & end_active
    touchdown = end_active & ~persistent
    liftoff = start_active & ~persistent
    phase3 = phase[..., None]
    desired_contact = persistent[:, None].expand(-1, phase.shape[1], -1).clone()
    desired_contact |= liftoff[:, None] & (phase3 <= 0.2)
    desired_contact |= touchdown[:, None] & (phase3 >= 0.8)
    contact_state = F.binary_cross_entropy_with_logits(output.contact_logits, desired_contact.to(output.contact_logits.dtype))

    start_rotation = _matrix_from_rotation6d(output.keypoint_rotation6d[:, 0])
    start_local_offsets = []
    for part, body in enumerate(CONTACT_BODY_INDEX):
        start_local_offsets.append(
            torch.einsum(
                "bij,bj->bi",
                start_rotation[:, body].transpose(-1, -2),
                output.keypoint_position[:, 0, body] - start_contact_position[:, part],
            )
        )
    points = _trajectory_contact_points(
        output, torch.stack(start_local_offsets, dim=1), end.contact_local_offset, phase
    )

    def masked_anchor(error: Tensor, mask: Tensor) -> Tensor:
        count = mask.sum().clamp_min(1)
        return (error.square().sum(dim=-1) * mask).sum() / count / (0.005**2)

    persistent_mask = persistent[:, None].expand_as(desired_contact)
    persistent_error = points - start_contact_position[:, None]
    persistent_anchor = masked_anchor(persistent_error, persistent_mask)
    touchdown_mask = touchdown[:, None] & (phase3 >= 0.8)
    touchdown_error = points - end.contact_position[:, None]
    touchdown_anchor = masked_anchor(touchdown_error, touchdown_mask)
    liftoff_mask = liftoff[:, None] & (phase3 <= 0.2)
    liftoff_error = points - start_contact_position[:, None]
    liftoff_anchor = masked_anchor(liftoff_error, liftoff_mask)
    velocity = output.auxiliary_qpos[:, 1:] - output.auxiliary_qpos[:, :-1]
    smoothness = (velocity[:, 1:] - velocity[:, :-1]).square().mean()
    if target_contact_rotation6d is None:
        contact_orientation = output.auxiliary_qpos.sum() * 0.0
        contact_angular_velocity = output.auxiliary_qpos.sum() * 0.0
    else:
        contact_orientation, contact_angular_velocity = contact_rotation_losses(
            output.keypoint_rotation6d[:, :, CONTACT_BODY_INDEX],
            target_contact_rotation6d,
            desired_contact,
        )
    if min(
        persistent_anchor_weight,
        touchdown_anchor_weight,
        liftoff_anchor_weight,
        collision_weight,
        contact_orientation_weight,
        contact_angular_velocity_weight,
    ) < 0.0:
        raise ValueError("infiller loss weights must be non-negative")
    total = q_reconstruction + endpoint + 0.2 * contact_state
    total = total + persistent_anchor_weight * persistent_anchor
    total = total + touchdown_anchor_weight * touchdown_anchor
    total = total + liftoff_anchor_weight * liftoff_anchor + 0.5 * smoothness
    total = total + contact_orientation_weight * contact_orientation
    total = total + contact_angular_velocity_weight * contact_angular_velocity
    total = total + collision_weight * collision_penalty + 10.0 * inactive_clearance_penalty
    return InteractionInfillerLoss(
        total,
        q_reconstruction,
        endpoint,
        contact_state,
        persistent_anchor,
        touchdown_anchor,
        liftoff_anchor,
        smoothness,
        collision_penalty,
        inactive_clearance_penalty,
        contact_orientation,
        contact_angular_velocity,
    )
