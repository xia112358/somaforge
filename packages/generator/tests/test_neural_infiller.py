from __future__ import annotations

import torch
from somaforge_core.motion_contracts import BODY_NAMES, CONTACT_PARTS
from generator.neural_infiller import (
    CanonicalG1CollisionPoints,
    G1ActionMedoidQDeformer,
    G1ConstrainedKeypointInfiller,
    G1ContactAwareQInfiller,
    InfillerOutput,
    _matrix_from_rotation6d,
    _quaternion_matrix_wxyz,
    constrained_infiller_loss,
    constrained_infiller_seam_loss,
    contact_aware_q_infiller_loss,
    full_geometry_box_collision_penalty,
    full_geometry_contact_surface_penalty,
)


def test_single_forward_has_exact_public_boundaries_and_bounded_private_qpos() -> None:
    torch.manual_seed(4)
    model = G1ConstrainedKeypointInfiller(11, width=32, layers=1, heads=4, ffn_width=64)
    batch, frames = 2, 6
    phase = torch.linspace(0.0, 1.0, frames)[None].expand(batch, -1)
    start_position = torch.randn(batch, len(BODY_NAMES), 3)
    end_position = torch.randn(batch, len(BODY_NAMES), 3)
    start_rotation = torch.randn(batch, len(BODY_NAMES), 6)
    end_rotation = torch.randn(batch, len(BODY_NAMES), 6)
    start_contact = torch.zeros(batch, len(CONTACT_PARTS))
    end_contact = torch.ones(batch, len(CONTACT_PARTS))
    output = model(
        torch.randn(batch, 11),
        phase,
        start_position,
        start_rotation,
        end_position,
        end_rotation,
        start_contact,
        end_contact,
    )
    torch.testing.assert_close(output.keypoint_position[:, 0], start_position)
    torch.testing.assert_close(output.keypoint_position[:, -1], end_position)
    torch.testing.assert_close(
        _matrix_from_rotation6d(output.keypoint_rotation6d[:, 0]),
        _matrix_from_rotation6d(start_rotation),
    )
    torch.testing.assert_close(
        _matrix_from_rotation6d(output.keypoint_rotation6d[:, -1]),
        _matrix_from_rotation6d(end_rotation),
    )
    rotation = _matrix_from_rotation6d(output.keypoint_rotation6d)
    identity = torch.eye(3).expand_as(rotation)
    torch.testing.assert_close(rotation.transpose(-1, -2) @ rotation, identity, atol=1.0e-5, rtol=1.0e-5)
    assert output.auxiliary_qpos.shape == (batch, frames, 36)
    assert torch.all(output.auxiliary_qpos[..., 7:] <= model.fk.joint_upper + 1.0e-6)
    assert torch.all(output.auxiliary_qpos[..., 7:] >= model.fk.joint_lower - 1.0e-6)

    torch.testing.assert_close(
        torch.linalg.vector_norm(output.auxiliary_qpos[..., 3:7], dim=-1),
        torch.ones(batch, frames),
    )


def test_constraint_loss_backpropagates_through_both_heads() -> None:
    torch.manual_seed(5)
    model = G1ConstrainedKeypointInfiller(7, width=32, layers=1, heads=4, ffn_width=64)
    batch, frames = 2, 5
    phase = torch.linspace(0.0, 1.0, frames)[None].expand(batch, -1)
    target_position = torch.randn(batch, frames, len(BODY_NAMES), 3)
    target_rotation = torch.randn(batch, frames, len(BODY_NAMES), 6)
    target_contact = torch.zeros(batch, frames, len(CONTACT_PARTS))
    target_qpos = torch.randn(batch, frames, 36)
    target_qpos[..., 3:7] = torch.nn.functional.normalize(target_qpos[..., 3:7], dim=-1)
    output = model(
        torch.randn(batch, 7),
        phase,
        target_position[:, 0],
        target_rotation[:, 0],
        target_position[:, -1],
        target_rotation[:, -1],
        target_contact[:, 0],
        target_contact[:, -1],
    )
    loss = constrained_infiller_loss(
        model,
        output,
        target_position=target_position,
        target_rotation6d=target_rotation,
        target_contact=target_contact,
        target_qpos=target_qpos,
        collision_penalty=output.auxiliary_qpos.square().mean() * 0.01,
    )
    loss.total.backward()
    assert model.keypoint_head[-1].weight.grad is not None
    assert model.q_residual_head[-1].weight.grad is not None
    assert model.boundary_q_head[-1].weight.grad is not None
    assert torch.isfinite(loss.total)


def test_full_geometry_collision_points_and_box_penalty_are_differentiable() -> None:
    model = G1ConstrainedKeypointInfiller(3, width=32, layers=1, heads=4, ffn_width=64)
    geometry = CanonicalG1CollisionPoints(maximum_mesh_points=4)
    qpos = torch.zeros(1, 2, 36, requires_grad=True)
    with torch.no_grad():
        qpos[..., 3] = 1.0
    points, part = geometry(model.fk, qpos)
    assert points.shape[:2] == (1, 2)
    assert points.shape[2] > 47
    penalty = full_geometry_box_collision_penalty(
        points,
        part,
        torch.zeros(1, 2, len(CONTACT_PARTS)),
        box_center=torch.tensor([[0.0, 0.0, 0.5]]),
        box_rotation=torch.eye(3)[None],
        box_half_extents=torch.tensor([[0.5, 0.5, 0.5]]),
        ground_height=torch.tensor([0.0]),
    )
    penalty.backward()
    assert qpos.grad is not None
    assert torch.isfinite(qpos.grad).all()
    assert penalty > 0.0
    assert qpos.grad.abs().sum() > 0.0


def test_contact_surface_penalty_is_symmetric_for_hover_and_penetration() -> None:
    target = torch.tensor([[[[0.0, 0.0, 1.0]]]])
    part = torch.tensor([0])
    contact = torch.ones(1, 1, len(CONTACT_PARTS))
    geometry = {
        "box_center": torch.tensor([[4.0, 0.0, 0.5]]),
        "box_rotation": torch.eye(3)[None],
        "box_half_extents": torch.tensor([[0.5, 0.5, 0.5]]),
        "ground_height": torch.tensor([1.0]),
    }
    hover = full_geometry_contact_surface_penalty(
        target + torch.tensor((0.0, 0.0, 0.03)), target, part, contact, **geometry
    )
    penetration = full_geometry_contact_surface_penalty(
        target - torch.tensor((0.0, 0.0, 0.03)), target, part, contact, **geometry
    )
    torch.testing.assert_close(hover, penetration)
    torch.testing.assert_close(hover, torch.tensor(9.0), atol=1.0e-5, rtol=1.0e-5)


def test_shared_boundary_has_identical_private_qpos_across_segments() -> None:
    torch.manual_seed(6)
    model = G1ConstrainedKeypointInfiller(5, width=32, layers=1, heads=4, ffn_width=64)
    phase = torch.linspace(0.0, 1.0, 7)[None]
    first = torch.randn(1, len(BODY_NAMES), 3)
    middle = torch.randn(1, len(BODY_NAMES), 3)
    last = torch.randn(1, len(BODY_NAMES), 3)
    first_rotation = torch.randn(1, len(BODY_NAMES), 6)
    middle_rotation = torch.randn(1, len(BODY_NAMES), 6)
    last_rotation = torch.randn(1, len(BODY_NAMES), 6)
    first_contact = torch.zeros(1, len(CONTACT_PARTS))
    middle_contact = torch.tensor([[1, 0, 1, 0, 0, 0]], dtype=torch.float32)
    last_contact = torch.ones(1, len(CONTACT_PARTS))
    left = model(
        torch.randn(1, 5),
        phase,
        first,
        first_rotation,
        middle,
        middle_rotation,
        first_contact,
        middle_contact,
    )
    angle = torch.tensor(0.6)
    cosine, sine = torch.cos(angle), torch.sin(angle)
    yaw = torch.tensor(((cosine, -sine, 0.0), (sine, cosine, 0.0), (0.0, 0.0, 1.0)))
    translation = torch.tensor((0.7, -0.4, 0.2))
    transformed_middle = torch.einsum("ij,bnj->bni", yaw, middle) + translation
    transformed_middle_rotation = torch.einsum(
        "ij,bnjk->bnik", yaw, middle_rotation.reshape(1, len(BODY_NAMES), 3, 2)
    ).reshape(1, len(BODY_NAMES), 6)
    transformed_last = torch.einsum("ij,bnj->bni", yaw, last) + translation
    transformed_last_rotation = torch.einsum(
        "ij,bnjk->bnik", yaw, last_rotation.reshape(1, len(BODY_NAMES), 3, 2)
    ).reshape(1, len(BODY_NAMES), 6)
    right = model(
        torch.randn(1, 5),
        phase,
        transformed_middle,
        transformed_middle_rotation,
        transformed_last,
        transformed_last_rotation,
        middle_contact,
        last_contact,
    )
    expected_root = torch.einsum("ij,bj->bi", yaw, left.auxiliary_qpos[:, -1, :3]) + translation
    torch.testing.assert_close(expected_root, right.auxiliary_qpos[:, 0, :3], atol=1.0e-5, rtol=1.0e-5)
    torch.testing.assert_close(left.auxiliary_qpos[:, -1, 7:], right.auxiliary_qpos[:, 0, 7:])
    expected_rotation = yaw @ _quaternion_matrix_wxyz(left.auxiliary_qpos[:, -1, 3:7])
    actual_rotation = _quaternion_matrix_wxyz(right.auxiliary_qpos[:, 0, 3:7])
    torch.testing.assert_close(expected_rotation, actual_rotation, atol=1.0e-5, rtol=1.0e-5)


def test_seam_loss_measures_c1_continuity_after_shared_boundary() -> None:
    frames = 5
    phase = torch.linspace(0.0, 1.0, frames)
    identity6d = torch.tensor((1.0, 0.0, 0.0, 1.0, 0.0, 0.0))

    def output(offset: float, velocity_scale: float = 1.0) -> InfillerOutput:
        position = torch.zeros(1, frames, len(BODY_NAMES), 3)
        position[..., 0] = offset + velocity_scale * phase[None, :, None]
        rotation = identity6d.expand(1, frames, len(BODY_NAMES), 6).clone()
        qpos = torch.zeros(1, frames, 36)
        qpos[..., 0] = offset + velocity_scale * phase
        qpos[..., 3] = 1.0
        qpos[..., 7:] = (offset + velocity_scale * phase)[None, :, None]
        return InfillerOutput(position, rotation, torch.zeros(1, frames, len(CONTACT_PARTS)), qpos)

    left = output(0.0)
    right = output(1.0)
    continuous = constrained_infiller_seam_loss(
        left,
        right,
        left_duration=torch.ones(1),
        right_duration=torch.ones(1),
        q_valid=torch.ones(1, dtype=torch.bool),
    )
    torch.testing.assert_close(continuous.total, torch.tensor(0.0), atol=1.0e-6, rtol=0.0)
    discontinuous = constrained_infiller_seam_loss(
        left,
        output(1.0, velocity_scale=3.0),
        left_duration=torch.ones(1),
        right_duration=torch.ones(1),
        q_valid=torch.ones(1, dtype=torch.bool),
    )
    assert discontinuous.keypoint_position_velocity > 0.0
    assert discontinuous.q_joint_velocity > 0.0


def test_q_only_infiller_has_exact_q_boundaries_and_fk_only_keypoints() -> None:
    torch.manual_seed(9)
    model = G1ContactAwareQInfiller(14, width=32, layers=1, heads=4, ffn_width=64)
    batch, frames = 2, 7
    start = torch.zeros(batch, 36)
    end = torch.zeros(batch, 36)
    start[:, 3] = 1.0
    end[:, 3] = 1.0
    joint_midpoint = 0.5 * (model.fk.joint_lower + model.fk.joint_upper)
    start[:, 7:] = joint_midpoint
    end[:, 7:] = joint_midpoint
    phase = torch.linspace(0.0, 1.0, frames)[None].expand(batch, -1)
    contact = torch.zeros(batch, len(CONTACT_PARTS))
    output = model(torch.randn(batch, 14), phase, start, end, contact, contact)
    torch.testing.assert_close(output.auxiliary_qpos[:, 0], start, atol=1.0e-6, rtol=0.0)
    torch.testing.assert_close(output.auxiliary_qpos[:, -1], end, atol=1.0e-6, rtol=0.0)
    fk_position, fk_rotation = model.fk(output.auxiliary_qpos)
    torch.testing.assert_close(output.keypoint_position, fk_position)
    torch.testing.assert_close(output.keypoint_rotation6d, fk_rotation)


def test_action_medoid_q_deformer_preserves_exact_start_and_fk_contract() -> None:
    model = G1ActionMedoidQDeformer(5, width=32, layers=1, heads=4, ffn_width=64)
    batch, frames = 2, 7
    phase = torch.linspace(0.0, 1.0, frames)[None].expand(batch, -1)
    base = torch.zeros(batch, frames, 36)
    base[..., 3] = 1.0
    base[..., 7:] = 0.1 * torch.sin(phase[..., None] * torch.pi)
    start = base[:, 0].clone()
    start[:, :3] = torch.tensor(((0.2, -0.1, 0.8), (-0.3, 0.2, 0.7)))
    position, rotation = model.fk(start)
    contact = torch.zeros(batch, len(CONTACT_PARTS))
    output = model(
        torch.zeros(batch, 5),
        phase,
        base,
        start,
        position,
        rotation,
        position + 0.05,
        rotation,
        contact,
        contact,
    )
    expected_position, expected_rotation = model.fk(output.auxiliary_qpos)
    assert torch.equal(output.auxiliary_qpos[:, 0], start)
    torch.testing.assert_close(output.keypoint_position, expected_position)
    torch.testing.assert_close(output.keypoint_rotation6d, expected_rotation)
    assert torch.all(output.auxiliary_qpos[..., 7:] <= model.fk.joint_upper + 1.0e-6)
    assert torch.all(output.auxiliary_qpos[..., 7:] >= model.fk.joint_lower - 1.0e-6)

    end = start.clone()
    end[:, :3] += torch.tensor((0.35, 0.05, 0.12))
    end[:, 7:] += 0.03
    end_position, end_rotation = model.fk(end)
    constrained = model(
        torch.zeros(batch, 5),
        phase,
        base,
        start,
        position,
        rotation,
        end_position,
        end_rotation,
        contact,
        contact,
        end,
    )
    torch.testing.assert_close(constrained.auxiliary_qpos[:, -1], end)
    torch.testing.assert_close(constrained.keypoint_position[:, -1], end_position)
    torch.testing.assert_close(constrained.keypoint_rotation6d[:, -1], end_rotation)


def test_q_only_contact_loss_is_finite_and_backpropagates() -> None:
    torch.manual_seed(10)
    model = G1ContactAwareQInfiller(6, width=32, layers=1, heads=4, ffn_width=64)
    batch, frames = 2, 8
    target = torch.zeros(batch, frames, 36)
    target[..., 3] = 1.0
    target[..., 7:] = 0.05 * torch.randn(batch, frames, 29)
    phase = torch.linspace(0.0, 1.0, frames)[None].expand(batch, -1)
    contact = torch.ones(batch, frames, len(CONTACT_PARTS))
    output = model(
        torch.randn(batch, 6),
        phase,
        target[:, 0],
        target[:, -1],
        contact[:, 0],
        contact[:, -1],
    )
    loss = contact_aware_q_infiller_loss(
        model,
        output,
        target_qpos=target,
        target_contact=contact,
        collision_penalty=output.auxiliary_qpos.square().mean() * 0.001,
        contact_surface_penalty=output.auxiliary_qpos.square().mean() * 0.001,
    )
    loss.total.backward()
    assert torch.isfinite(loss.total)
    assert model.q_residual_head[-1].weight.grad is not None
