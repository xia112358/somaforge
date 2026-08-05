from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch
from gmvq.current_frame_future import (
    CausalSegmentFutureModel,
    CurrentFrameFutureModel,
    canonical_boundary_state,
)
from gmvq.data import build_dataset
from gmvq.decode_motion_edit_ref import _restore_world_positions
from gmvq.hyar_wrapper import FrozenGMVQCodec
from gmvq.losses import compute_loss
from gmvq.models import GMVQAutoEncoder
from gmvq.prepare_motion_edit_segments import prepare_motion_manifest_segments, write_npz
from gmvq.train_gmvq import _kmeans_labels, _trajectory_embeddings
from somaforge_core.robot_assets import canonical_g1_source_metadata, encode_robot_asset_json

from scripts.gmvq_ref.decode_selector_ref import (
    _chain_pose_segment,
    _feature_schema,
    _normalize_quaternions,
    _strip_stale_contact_arrays,
    _write_decoded_segments,
)
from scripts.gmvq_ref.extract_selector_height_dataset import _forward_multiscale_grid
from scripts.gmvq_ref.start_conditioned_decoder import StartConditionedDecoder
from scripts.gmvq_ref.torch_g1_fk import _quat_wxyz_matrix
from scripts.gmvq_ref.train_start_conditioned_decoder import (
    WBT_TRACKED_LINK_NAMES,
    _taskspace_connection_mse,
)
from scripts.gmvq_ref.train_current_frame_future import (
    WBT_TRACKED_LINK_NAMES,
    _contact_body_weights,
    _observation_statistics,
    _previous_codes,
    _smooth_recovery_segment,
    _taskspace_sample_frames,
)
from scripts.gmvq_ref.finetune_current_frame_future_unrolled import (
    _cross_atom_velocity_loss,
    _endpoint_velocity,
    _integrate_pose_velocity,
    _pose_velocity_consistency,
    _relative_motion_loss,
    _taskspace_velocity_consistency,
    _taskspace_velocity_peak_consistency,
)
from gmvq.g1_fk import CanonicalG1TorchFK
from somaforge_core import G1_29DOF_JOINT_ORDER


def _write_motion(path: Path, x_offset: float) -> None:
    frames = 10
    joint_pos = np.zeros((frames, 7), dtype=np.float32)
    joint_pos[:, 0] = x_offset + np.arange(frames, dtype=np.float32)
    body_pos_w = np.zeros((frames, 2, 3), dtype=np.float32)
    body_pos_w[:, :, 0] = joint_pos[:, 0, None] + np.asarray([0.0, 1.0], dtype=np.float32)
    np.savez(
        path,
        joint_pos=joint_pos,
        body_pos_w=body_pos_w,
        robot_asset_json=np.asarray(encode_robot_asset_json()),
    )


def test_motion_manifest_packs_multiple_force_free_refs_relative_to_segment_root(tmp_path: Path) -> None:
    motion_a = tmp_path / "motion_a.npz"
    motion_b = tmp_path / "motion_b.npz"
    _write_motion(motion_a, 10.0)
    _write_motion(motion_b, 20.0)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "motion_files": [
                    {"motion_id": 0, "motion_name": "a", "motion_file": str(motion_a)},
                    {"motion_id": 1, "motion_name": "b", "motion_file": str(motion_b)},
                ]
            }
        ),
        encoding="utf-8",
    )
    template = tmp_path / "segments.jsonl"
    template.write_text(
        json.dumps(
            {
                "track": "proto",
                "segment_id": "contact_phase",
                "start_frame": 0,
                "end_frame": 6,
                "metadata": {"active_body": "left_hand"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    prepared, stats = prepare_motion_manifest_segments(
        manifest,
        segment_template=template,
        feature_keys=["joint_pos", "body_pos_w"],
        target_len=6,
        min_len=1,
        max_len=6,
        include_tail=True,
        relative_root=True,
    )

    assert stats["kept"] == 4
    assert [item.length for item in prepared] == [6, 4, 6, 4]
    assert [item.segment_id.rsplit("_", 1)[-1] for item in prepared] == [
        "phase",
        "tail",
        "phase",
        "tail",
    ]
    assert all("_w" not in item.segment_id for item in prepared)
    assert len({item.source_path for item in prepared}) == 2
    assert np.allclose(prepared[0].segment[0, :3], 0.0)
    assert np.allclose(prepared[0].segment[0, 7:10], 0.0)
    assert prepared[0].contact_force_provenance_json is None

    output = tmp_path / "pack.npz"
    write_npz(output, prepared, feature_keys=["joint_pos", "body_pos_w"], stats=stats)
    with np.load(output, allow_pickle=False) as data:
        assert data["segments"].shape == (4, 6, 13)
        assert bool(data["relative_root"]) is True
        assert data["anchor_root_pos"].shape == (4, 3)
        assert "contact_force_provenance_json" not in data.files
    schema = _feature_schema(
        output,
        {
            "joint_pos": np.zeros((10, 7), dtype=np.float32),
            "body_pos_w": np.zeros((10, 2, 3), dtype=np.float32),
        },
    )
    assert schema == [
        {"key": "joint_pos", "start": 0, "end": 7, "shape": [7]},
        {"key": "body_pos_w", "start": 7, "end": 13, "shape": [2, 3]},
    ]


def test_relative_decode_restores_root_and_body_world_positions() -> None:
    split = {
        "joint_pos": np.asarray([0.5, 0.0, 0.0, 1.0], dtype=np.float32),
        "body_pos_w": np.asarray([[0.25, 0.0, 0.0], [1.25, 0.0, 0.0]], dtype=np.float32),
    }
    _restore_world_positions(split, np.asarray([10.0, 2.0, 3.0], dtype=np.float32))
    assert np.allclose(split["joint_pos"][:3], [10.5, 2.0, 3.0])
    assert np.allclose(split["body_pos_w"][0], [10.25, 2.0, 3.0])


def test_selector_decode_normalizes_quaternions() -> None:
    normalized, correction = _normalize_quaternions(
        np.asarray([[2.0, 0.0, 0.0, 0.0], [0.0, 0.0, 3.0, 4.0]], dtype=np.float32),
        context="test",
    )
    assert np.allclose(np.linalg.norm(normalized, axis=-1), 1.0)
    assert correction == 4.0


def test_selector_decode_chains_actual_segment_endpoints() -> None:
    source_joint = np.zeros((4, 8), dtype=np.float32)
    source_joint[:, 0] = 10.0
    source_joint[:, 3] = 1.0
    source = {
        "joint_pos": source_joint,
        "joint_vel": np.zeros((4, 7), dtype=np.float32),
        "fps": np.asarray(50.0, dtype=np.float32),
    }
    decoded = np.zeros((2, 2, 8), dtype=np.float32)
    decoded[:, :, 3] = 1.0
    decoded[0, :, 0] = [0.0, 0.5]
    decoded[0, :, 7] = [0.0, 0.2]
    decoded[1, :, 0] = [0.1, 0.4]
    decoded[1, :, 7] = [1.0, 1.4]
    schema = [{"key": "joint_pos", "start": 0, "end": 8, "shape": [8]}]

    result, report = _write_decoded_segments(
        source_ref=source,
        decoded_segments=decoded,
        schema_keys=schema,
        start_frames=np.asarray([0, 2], dtype=np.int64),
        end_frames=np.asarray([2, 4], dtype=np.int64),
        lengths=np.asarray([2, 2], dtype=np.int64),
        anchor_root_pos=np.asarray([[10.0, 0.0, 0.0], [99.0, 0.0, 0.0]], dtype=np.float32),
        blend_overlaps=True,
        chain_relative_segments=True,
    )

    np.testing.assert_allclose(result["joint_pos"][:, 0], [10.0, 10.5, 10.5, 10.8], atol=1.0e-6)
    np.testing.assert_allclose(result["joint_pos"][:, 7], [0.0, 0.2, 0.2, 0.6], atol=1.0e-6)
    assert report["chain_relative_segments"] is True
    assert result["joint_vel"].shape == (4, 7)


def test_selector_decode_strips_stale_contact_observations() -> None:
    source = {
        "joint_pos": np.zeros((2, 36), dtype=np.float32),
        "contact_force_part_w": np.ones((2, 8, 3), dtype=np.float32),
        "contact_force_provenance_json": np.asarray("{}"),
        "raw_contact_point_w": np.ones((2, 4, 3), dtype=np.float32),
        "terrain_id": np.asarray(0),
    }

    stripped, removed = _strip_stale_contact_arrays(source)

    assert removed == [
        "contact_force_part_w",
        "contact_force_provenance_json",
        "raw_contact_point_w",
    ]
    assert set(stripped) == {"joint_pos", "terrain_id"}


def test_selector_decode_carries_source_motion_through_gaps_and_tail() -> None:
    source_joint = np.zeros((7, 8), dtype=np.float32)
    source_joint[:, 0] = np.arange(7, dtype=np.float32)
    source_joint[:, 3] = 1.0
    source_joint[:, 7] = np.arange(7, dtype=np.float32) * 0.1
    source = {
        "joint_pos": source_joint,
        "joint_vel": np.zeros((7, 7), dtype=np.float32),
        "fps": np.asarray(1.0, dtype=np.float32),
    }
    decoded = np.zeros((2, 2, 8), dtype=np.float32)
    decoded[:, :, 3] = 1.0
    decoded[0, :, 0] = [0.0, 0.5]
    decoded[1, :, 0] = [0.0, 0.25]
    schema = [{"key": "joint_pos", "start": 0, "end": 8, "shape": [8]}]

    result, report = _write_decoded_segments(
        source_ref=source,
        decoded_segments=decoded,
        schema_keys=schema,
        start_frames=np.asarray([0, 4], dtype=np.int64),
        end_frames=np.asarray([2, 6], dtype=np.int64),
        lengths=np.asarray([2, 2], dtype=np.int64),
        anchor_root_pos=np.zeros((2, 3), dtype=np.float32),
        blend_overlaps=False,
        chain_relative_segments=True,
    )

    np.testing.assert_allclose(
        result["joint_pos"][:, 0],
        [0.0, 0.5, 1.5, 2.5, 2.5, 2.75, 3.75],
        atol=1.0e-6,
    )
    assert report["written_frame_count"] == 7


def test_world_axis_root_delta_is_not_rotated_during_chaining() -> None:
    decoded = np.zeros((2, 8), dtype=np.float32)
    decoded[:, 3] = 1.0
    decoded[1, 0] = 1.0
    base = np.zeros(8, dtype=np.float32)
    # 90 degree rotation around Y would rotate +X into -Z if incorrectly
    # applied to a world-axis translation.
    base[3:7] = np.asarray([np.sqrt(0.5), 0.0, np.sqrt(0.5), 0.0], dtype=np.float32)
    split = {"joint_pos": decoded}

    _chain_pose_segment(
        split,
        base_joint_pose=base,
        base_body_pos=None,
        base_body_quat=None,
        rotate_root_translation=False,
    )

    np.testing.assert_allclose(split["joint_pos"][1, :3], [1.0, 0.0, 0.0], atol=1.0e-6)


def test_chaining_can_preserve_absolute_articulated_pose() -> None:
    decoded = np.zeros((2, 9), dtype=np.float32)
    decoded[:, 3] = 1.0
    decoded[:, 7:] = [[0.1, 0.2], [0.3, 0.4]]
    base = np.zeros(9, dtype=np.float32)
    base[3] = 1.0
    base[7:] = [0.8, -0.7]
    split = {"joint_pos": decoded}

    _chain_pose_segment(
        split,
        base_joint_pose=base,
        base_body_pos=None,
        base_body_quat=None,
        rebase_articulated_joints=False,
    )

    np.testing.assert_allclose(split["joint_pos"][:, 7:], decoded[:, 7:], atol=1.0e-6)


def test_torch_fk_quaternion_matrix_is_differentiable() -> None:
    quaternion = torch.tensor([[1.0, 0.0, 0.0, 0.0]], requires_grad=True)
    matrix = _quat_wxyz_matrix(quaternion)
    torch.testing.assert_close(matrix, torch.eye(3).unsqueeze(0))
    matrix.sum().backward()
    assert quaternion.grad is not None


def test_start_conditioned_decoder_starts_as_absolute_identity_correction() -> None:
    model = StartConditionedDecoder(feature_dim=7, num_codes=3, theta_dim=2, hidden_dim=16, depth=2)
    base = torch.randn(2, 5, 7)
    result = model(
        base,
        start_state=torch.randn(2, 7),
        codes=torch.tensor([0, 2]),
        theta=torch.randn(2, 2),
        lengths=torch.tensor([5, 4]),
    )
    torch.testing.assert_close(result, base)


def test_start_condition_correction_decays_to_absolute_endpoint() -> None:
    model = StartConditionedDecoder(
        feature_dim=7,
        num_codes=3,
        theta_dim=2,
        hidden_dim=16,
        depth=2,
        condition_decay_power=4.0,
    )
    with torch.no_grad():
        model.net[-1].bias.fill_(1.0)
    base = torch.zeros(1, 5, 7)
    result = model(
        base,
        start_state=torch.ones(1, 7),
        codes=torch.tensor([1]),
        theta=torch.zeros(1, 2),
        lengths=torch.tensor([5]),
    )
    torch.testing.assert_close(result[:, -1], base[:, -1])
    assert torch.all(result[:, 0] > base[:, 0])


def test_start_conditioned_decoder_generates_absolute_future_from_exact_state() -> None:
    model = StartConditionedDecoder(
        feature_dim=71,
        num_codes=3,
        theta_dim=2,
        hidden_dim=16,
        depth=0,
        anchor_start=True,
    )
    with torch.no_grad():
        model.net[-1].weight[7, 71 + 7] = 0.5
    base = torch.zeros(2, 8, 71)
    base[..., 3] = 1.0
    start = torch.zeros(2, 71)
    start[:, :3] = torch.tensor([[1.0, 2.0, 3.0], [-1.0, 0.5, 0.8]])
    start[:, 3] = 1.0
    start[:, 7:36] = 0.25
    start[1, 7] = -0.25
    start[:, 36:] = 0.5

    result = model(
        base,
        start_state=start,
        codes=torch.tensor([0, 2]),
        theta=torch.zeros(2, 2),
        lengths=torch.tensor([8, 6]),
    )

    assert result.shape == (2, 8, 71)
    torch.testing.assert_close(result[:, 0], start, rtol=0.0, atol=0.0)
    assert torch.isfinite(result).all()
    assert not torch.equal(result[0, 1:, 7], result[1, 1:, 7])


def test_taskspace_connection_loss_tracks_metric_wbt_body_motion() -> None:
    fk = CanonicalG1TorchFK(
        joint_names=list(G1_29DOF_JOINT_ORDER),
        link_names=list(WBT_TRACKED_LINK_NAMES),
    )
    start = torch.zeros(1, 71)
    start[:, 3] = 1.0
    prediction = start[:, None].repeat(1, 3, 1).requires_grad_(True)
    valid = torch.ones(1, 3, dtype=torch.bool)
    mean = torch.zeros(71)
    std = torch.ones(71)

    zero = _taskspace_connection_mse(
        prediction,
        start_state=start,
        valid=valid,
        mean=mean,
        std=std,
        frames=2,
        fps=50.0,
        decay_power=1.0,
        fk=fk,
    )
    torch.testing.assert_close(zero, torch.zeros_like(zero))

    perturbed = prediction.clone()
    perturbed[:, 1, 22] = 0.2
    loss = _taskspace_connection_mse(
        perturbed,
        start_state=start,
        valid=valid,
        mean=mean,
        std=std,
        frames=2,
        fps=50.0,
        decay_power=1.0,
        fk=fk,
    )
    assert loss > 0.0
    loss.backward()
    assert prediction.grad is not None
    assert torch.isfinite(prediction.grad).all()
    assert prediction.grad.abs().sum() > 0.0


def test_current_frame_future_jointly_generates_code_theta_and_trajectory() -> None:
    model = CurrentFrameFutureModel(
        height_dim=5,
        state_dim=9,
        feature_dim=7,
        num_codes=4,
        theta_dim=3,
        max_frames=11,
        branch_dim=8,
        context_dim=12,
        code_embed_dim=4,
        decoder_dim=10,
        decoder_layers=1,
        time_harmonics=2,
    )
    observation = torch.randn(2, 14)
    start = torch.randn(2, 7)
    output = model(observation, start_state=start)

    assert output["code_logits"].shape == (2, 4)
    assert output["codes"].shape == (2,)
    assert output["theta"].shape == (2, 3)
    assert output["trajectory"].shape == (2, 11, 7)
    torch.testing.assert_close(output["trajectory"][:, 0], start, rtol=0.0, atol=0.0)

    output["trajectory"][:, 1:].square().mean().backward()
    assert model.code_head.weight.grad is not None
    assert model.code_head.weight.grad.abs().sum() > 0.0


def test_unrolled_future_uses_runtime_pose_finite_difference_velocity() -> None:
    q = torch.zeros(1, 2, 36)
    q[..., 3] = 1.0
    q[:, 1, 0] = 0.02
    q[:, 1, 7] = 0.1
    velocity = _endpoint_velocity(q, 50.0)
    torch.testing.assert_close(velocity[:, :3], torch.tensor([[1.0, 0.0, 0.0]]))
    torch.testing.assert_close(velocity[:, 3:6], torch.zeros(1, 3))
    torch.testing.assert_close(velocity[:, 6], torch.tensor([5.0]))


def test_full_trajectory_losses_cover_pose_velocity_and_cross_atom_smoothness() -> None:
    q = torch.zeros(1, 4, 36)
    q[..., 3] = 1.0
    q[0, :, 0] = torch.tensor([0.0, 0.02, 0.04, 0.06])
    q[0, :, 7] = torch.tensor([0.0, 0.01, 0.02, 0.03])
    qd = torch.zeros(1, 4, 35)
    qd[..., 0] = 1.0
    qd[..., 6] = 0.5
    valid = torch.ones(1, 4, dtype=torch.bool)
    torch.testing.assert_close(_pose_velocity_consistency(q, qd, valid, 50.0), torch.zeros(()))

    previous_tail = q[:, :2]
    continuous_head = q[:, 1:3]
    torch.testing.assert_close(
        _cross_atom_velocity_loss(previous_tail, continuous_head), torch.zeros(())
    )
    discontinuous_head = continuous_head.clone()
    discontinuous_head[:, 1, 0] += 0.1
    assert _cross_atom_velocity_loss(previous_tail, discontinuous_head) > 0.0

    integrated = _integrate_pose_velocity(q[:, 0], qd[:, 0], 50.0)
    torch.testing.assert_close(integrated[:, :3], q[:, 1, :3])
    torch.testing.assert_close(integrated[:, 7:], q[:, 1, 7:])

    fk = CanonicalG1TorchFK(
        joint_names=list(G1_29DOF_JOINT_ORDER), link_names=list(WBT_TRACKED_LINK_NAMES)
    )
    torch.testing.assert_close(
        _taskspace_velocity_peak_consistency(q, qd, valid, 50.0, fk),
        torch.zeros(()),
        atol=1.0e-12,
        rtol=0.0,
    )
    jumped = q.clone()
    jumped[:, 2, 0] += 0.1
    tail_loss = _taskspace_velocity_peak_consistency(jumped, qd, valid, 50.0, fk)
    assert tail_loss > 0.0
    assert tail_loss > _taskspace_velocity_consistency(jumped, qd, valid, 50.0, fk)

    with pytest.raises(ValueError, match="tail_fraction"):
        _taskspace_velocity_peak_consistency(jumped, qd, valid, 50.0, fk, 0.0)
    with pytest.raises(ValueError, match="link_tail_fraction"):
        _taskspace_velocity_peak_consistency(
            jumped, qd, valid, 50.0, fk, link_tail_fraction=0.0
        )


def test_causal_guide_conditions_shape_without_replacing_recursive_state() -> None:
    model = CausalSegmentFutureModel(
        height_dim=2,
        state_dim=3,
        feature_dim=7,
        num_codes=2,
        theta_dim=2,
        max_frames=4,
        branch_dim=4,
        context_dim=6,
        code_embed_dim=3,
        dynamics_dim=5,
        dynamics_layers=1,
        time_harmonics=1,
        use_guide=True,
        guide_residual_output=False,
    )
    start = torch.zeros(1, 7)
    start[:, 3] = 1.0
    guide = torch.randn(1, 4, 7)
    output = model(torch.zeros(1, 5), start_state=start, guide_trajectory=guide)
    torch.testing.assert_close(
        output["trajectory"], start[:, None].expand_as(output["trajectory"])
    )


def test_relative_motion_loss_ignores_start_offset_but_not_shape_change() -> None:
    target_mean = torch.zeros(71)
    target_std = torch.ones(71)
    guide = torch.zeros(1, 4, 71)
    guide[..., 3] = 1.0
    guide[0, :, 7] = torch.tensor([0.0, 0.1, 0.2, 0.3])
    prediction = guide.clone()
    prediction[..., 7] += 0.4
    valid = torch.ones(1, 4, dtype=torch.bool)
    torch.testing.assert_close(
        _relative_motion_loss(prediction, guide, valid, target_mean, target_std),
        torch.zeros(()),
    )
    prediction[0, 2, 7] += 0.2
    assert _relative_motion_loss(prediction, guide, valid, target_mean, target_std) > 0.0


def test_causal_segment_future_generates_every_frame_from_previous_state() -> None:
    model = CausalSegmentFutureModel(
        height_dim=2,
        state_dim=3,
        feature_dim=7,
        num_codes=2,
        theta_dim=2,
        max_frames=4,
        branch_dim=4,
        context_dim=6,
        code_embed_dim=3,
        dynamics_dim=5,
        dynamics_layers=1,
        time_harmonics=1,
    )
    with torch.no_grad():
        model.delta_head.bias[0] = 0.1
    start = torch.zeros(1, 7)
    start[:, 3] = 1.0
    output = model(torch.zeros(1, 5), start_state=start)
    assert model.config()["dynamics_dim"] == 5
    torch.testing.assert_close(output["trajectory"][:, 0], start, rtol=0.0, atol=0.0)
    torch.testing.assert_close(
        output["trajectory"][0, :, 0],
        torch.tensor([0.0, 0.1, 0.2, 0.3]),
        rtol=0.0,
        atol=1.0e-6,
    )


def test_guided_causal_segment_requires_a_full_shape_hint() -> None:
    model = CausalSegmentFutureModel(
        height_dim=2,
        state_dim=3,
        feature_dim=7,
        num_codes=2,
        theta_dim=2,
        max_frames=4,
        branch_dim=4,
        context_dim=6,
        code_embed_dim=3,
        dynamics_dim=5,
        dynamics_layers=1,
        time_harmonics=1,
        use_guide=True,
    )
    start = torch.zeros(1, 7)
    start[:, 3] = 1.0
    observation = torch.zeros(1, 5)
    with pytest.raises(ValueError, match="guide_trajectory"):
        model(observation, start_state=start)
    output = model(
        observation,
        start_state=start,
        guide_trajectory=start[:, None].repeat(1, 4, 1),
    )
    torch.testing.assert_close(output["trajectory"][:, 0], start, rtol=0.0, atol=0.0)


def test_guide_residual_output_carries_start_condition_smoothly_into_shape() -> None:
    model = CausalSegmentFutureModel(
        height_dim=2,
        state_dim=3,
        feature_dim=7,
        num_codes=2,
        theta_dim=2,
        max_frames=4,
        branch_dim=4,
        context_dim=6,
        code_embed_dim=3,
        dynamics_dim=5,
        dynamics_layers=1,
        time_harmonics=1,
        use_guide=True,
        guide_residual_output=True,
    )
    start = torch.zeros(1, 7)
    start[:, 0] = 3.0
    start[:, 3] = 1.0
    guide = torch.zeros(1, 4, 7)
    guide[..., 3] = 1.0
    guide[0, :, 0] = torch.tensor([0.0, 0.1, 0.2, 0.3])
    output = model(torch.zeros(1, 5), start_state=start, guide_trajectory=guide)

    assert model.config()["guide_residual_output"] is True
    torch.testing.assert_close(output["trajectory"][:, 0], start, rtol=0.0, atol=0.0)
    expected_x = torch.tensor([3.0, 1.4333334, 0.5333334, 0.3])
    torch.testing.assert_close(output["trajectory"][0, :, 0], expected_x, rtol=0.0, atol=1.0e-6)


def test_guide_residual_output_cannot_run_without_a_guide() -> None:
    with pytest.raises(ValueError, match="requires use_guide"):
        CausalSegmentFutureModel(
            height_dim=2,
            state_dim=3,
            feature_dim=7,
            num_codes=2,
            theta_dim=2,
            max_frames=4,
            guide_residual_output=True,
        )


def test_joint_trajectory_output_predicts_frames_without_pose_integration() -> None:
    model = CausalSegmentFutureModel(
        height_dim=2,
        state_dim=3,
        feature_dim=7,
        num_codes=2,
        theta_dim=2,
        max_frames=4,
        branch_dim=4,
        context_dim=6,
        code_embed_dim=3,
        dynamics_dim=5,
        dynamics_layers=1,
        time_harmonics=1,
        use_guide=True,
        joint_trajectory_output=True,
    )
    start = torch.zeros(1, 7)
    start[:, 0] = 3.0
    start[:, 3] = 1.0
    guide = torch.zeros(1, 4, 7)
    guide[..., 3] = 1.0
    guide[0, :, 0] = torch.tensor([0.0, 0.1, 0.3, 0.6])

    with torch.no_grad():
        model.delta_head.bias[0] = 0.1
    output = model(torch.zeros(1, 5), start_state=start, guide_trajectory=guide)

    assert model.config()["joint_trajectory_output"] is True
    torch.testing.assert_close(output["trajectory"][:, 0], start, rtol=0.0, atol=0.0)
    # Every future frame gets one independently decoded residual. It is not
    # cumulatively added to the preceding generated pose.
    torch.testing.assert_close(
        output["trajectory"][0, 1:, 0],
        torch.tensor([0.2, 0.4, 0.7]),
        rtol=0.0,
        atol=1.0e-6,
    )


def test_joint_trajectory_output_rejects_integrating_modes() -> None:
    common = dict(
        height_dim=2,
        state_dim=3,
        feature_dim=7,
        num_codes=2,
        theta_dim=2,
        max_frames=4,
    )
    with pytest.raises(ValueError, match="requires use_guide"):
        CausalSegmentFutureModel(**common, joint_trajectory_output=True)
    with pytest.raises(ValueError, match="mutually exclusive"):
        CausalSegmentFutureModel(
            **common,
            use_guide=True,
            guide_residual_output=True,
            joint_trajectory_output=True,
        )
    with pytest.raises(ValueError, match="requires joint_trajectory_output"):
        CausalSegmentFutureModel(
            **common,
            use_guide=True,
            start_residual_conditioning=True,
        )


def test_forward_multiscale_grid_extends_ahead_and_keeps_near_field() -> None:
    grid = _forward_multiscale_grid(
        near_size=0.6,
        near_points_per_axis=7,
        forward_length=1.6,
        forward_half_width=0.9,
        forward_rows=10,
        forward_cols=11,
    )

    assert grid.shape == (159, 3)
    assert np.isclose(grid[:, 0].min(), -0.3)
    assert np.isclose(grid[:, 0].max(), 1.6)
    assert np.isclose(np.abs(grid[:, 1]).max(), 0.9)
    assert grid[:49].reshape(7, 7, 3).shape == (7, 7, 3)
    assert grid[49:].reshape(10, 11, 3).shape == (10, 11, 3)


def test_causal_future_uses_spatial_scan_convolutions() -> None:
    model = CausalSegmentFutureModel(
        height_dim=10,
        state_dim=4,
        feature_dim=7,
        num_codes=3,
        theta_dim=2,
        max_frames=4,
        branch_dim=8,
        context_dim=12,
        code_embed_dim=4,
        dynamics_dim=10,
        dynamics_layers=1,
        time_harmonics=1,
        scan_grid_shapes=((2, 3), (2, 2)),
    )
    observation = torch.randn(2, 14, requires_grad=True)
    start = torch.randn(2, 7)
    output = model(observation, start_state=start, previous_code=torch.tensor([-1, 0]))

    assert output["trajectory"].shape == (2, 4, 7)
    assert sum(isinstance(layer, torch.nn.Conv2d) for layer in model.modules()) == 4
    output["code_logits"].sum().backward()
    assert observation.grad is not None
    assert observation.grad[:, :10].abs().sum() > 0.0


def test_branch_scan_normalization_shares_statistics_within_each_grid() -> None:
    observation = np.asarray(
        [
            [0.0, 1.0, 2.0, 3.0, 10.0, 12.0, 20.0],
            [4.0, 5.0, 6.0, 7.0, 14.0, 16.0, 24.0],
        ],
        dtype=np.float32,
    )
    mean, std = _observation_statistics(
        observation,
        np.asarray([True, True]),
        height_dim=6,
        scan_grid_shapes=((2, 2), (1, 2)),
        scan_normalization="branch",
    )

    np.testing.assert_allclose(mean[:4], np.full(4, observation[:, :4].mean()))
    np.testing.assert_allclose(std[:4], np.full(4, observation[:, :4].std()))
    np.testing.assert_allclose(mean[4:6], np.full(2, observation[:, 4:6].mean()))
    np.testing.assert_allclose(std[4:6], np.full(2, observation[:, 4:6].std()))
    assert mean[6] == observation[:, 6].mean()
    assert std[6] == observation[:, 6].std()


def test_spatial_scan_antialias_spreads_an_edge_before_learned_convolutions() -> None:
    plain = CausalSegmentFutureModel(
        height_dim=9,
        state_dim=1,
        feature_dim=2,
        num_codes=2,
        theta_dim=1,
        max_frames=2,
        branch_dim=4,
        context_dim=4,
        code_embed_dim=2,
        dynamics_dim=4,
        dynamics_layers=1,
        time_harmonics=1,
        scan_grid_shapes=((3, 3),),
        scan_antialias=False,
    )
    filtered = CausalSegmentFutureModel(**(plain.config() | {"scan_antialias": True}))
    captured: list[torch.Tensor] = []
    filtered.height_encoder.branches[0][0].register_forward_pre_hook(
        lambda _module, values: captured.append(values[0].detach().clone())
    )
    scan = torch.zeros(1, 9)
    scan[0, 4] = 1.0
    filtered.height_encoder(scan)

    assert filtered.config()["scan_antialias"] is True
    torch.testing.assert_close(
        captured[0].reshape(3, 3),
        torch.tensor([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=torch.float32) / 16.0,
    )


def test_previous_code_is_a_soft_logit_residual_not_a_transition_mask() -> None:
    model = CausalSegmentFutureModel(
        height_dim=4,
        state_dim=3,
        feature_dim=7,
        num_codes=3,
        theta_dim=2,
        max_frames=3,
        branch_dim=6,
        context_dim=8,
        code_embed_dim=3,
        dynamics_dim=8,
        dynamics_layers=1,
        time_harmonics=1,
        scan_grid_shapes=((2, 2),),
        previous_code_embed_dim=2,
        previous_code_logit_scale=1.0,
        previous_code_dropout=0.0,
    ).eval()
    with torch.no_grad():
        model.code_head.weight.zero_()
        model.code_head.bias.zero_()
        model.previous_code_embedding.weight.zero_()
        model.previous_code_embedding.weight[0] = torch.tensor([1.0, 0.0])
        model.previous_code_embedding.weight[1] = torch.tensor([0.0, 1.0])
        model.previous_code_head.weight.zero_()
        model.previous_code_head.weight[1, 0] = 4.0
        model.previous_code_head.weight[2, 1] = 4.0

    observation = torch.zeros(2, 7)
    start = torch.zeros(2, 7)
    output = model(observation, start_state=start, previous_code=torch.tensor([0, 1]))
    assert output["codes"].tolist() == [1, 2]


def test_previous_codes_follow_each_sequence_independently() -> None:
    motion_ids = np.asarray(["m", "m", "m", "m"])
    sequence_ids = np.asarray(["m#0", "m#0", "m#1", "m#1"])
    start_frames = np.asarray([0, 10, 0, 10])
    codes = np.asarray([0, 1, 0, 2])

    previous = _previous_codes(sequence_ids, start_frames, codes)

    assert motion_ids.tolist() == ["m"] * 4
    assert previous.tolist() == [-1, 0, -1, 0]


def test_contact_body_weights_include_current_and_immediately_following_atom() -> None:
    weights = _contact_body_weights(
        np.asarray(
            [
                '["left_foot", "right_foot"]',
                '["left_hand", "left_knee"]',
                '["right_hand"]',
            ]
        ),
        np.asarray(["sequence", "sequence", "sequence"]),
        np.asarray([0, 20, 40]),
        body_names=WBT_TRACKED_LINK_NAMES,
        contact_weight=4.0,
    )
    index = {name: i for i, name in enumerate(WBT_TRACKED_LINK_NAMES)}

    assert weights[0, index["left_ankle_roll_link"]] == 4.0
    assert weights[0, index["right_ankle_roll_link"]] == 4.0
    assert weights[0, index["left_wrist_yaw_link"]] == 4.0
    assert weights[0, index["left_knee_link"]] == 4.0
    assert weights[0, index["right_wrist_yaw_link"]] == 1.0
    assert weights[1, index["right_wrist_yaw_link"]] == 4.0


def test_taskspace_sample_frames_cover_complete_atom_and_endpoint() -> None:
    frames = _taskspace_sample_frames(torch.tensor([2, 9, 17]), samples=5)

    assert frames[:, 0].tolist() == [0, 0, 0]
    assert frames[:, -1].tolist() == [1, 8, 16]
    assert frames[1].tolist() == [0, 2, 4, 6, 8]


def test_smooth_recovery_segment_starts_measured_and_returns_to_source_shape() -> None:
    segment = np.zeros((9, 71), dtype=np.float32)
    segment[:, 3] = 1.0
    measured_q = segment[0, :36].copy()
    measured_q[7] = 0.02
    angle = np.deg2rad(4.0)
    measured_q[3:7] = [np.cos(0.5 * angle), 0.0, np.sin(0.5 * angle), 0.0]
    measured_qd = np.linspace(-0.1, 0.1, 35, dtype=np.float32)

    recovered = _smooth_recovery_segment(
        segment,
        length=9,
        start_joint_pos=measured_q,
        start_joint_vel=measured_qd,
        recovery_fraction=0.5,
        fps=50.0,
    )

    np.testing.assert_allclose(recovered[0, :36], measured_q, atol=1.0e-6)
    np.testing.assert_allclose(recovered[0, 36:], measured_qd, atol=1.0e-6)
    np.testing.assert_allclose(recovered[4:, :36], segment[4:, :36], atol=1.0e-6)
    assert abs(float(recovered[1, 7] - recovered[0, 7])) < 0.02
    np.testing.assert_allclose(np.linalg.norm(recovered[:9, 3:7], axis=1), 1.0, atol=1.0e-6)
    assert np.isfinite(recovered).all()


def test_canonical_boundary_state_is_invariant_to_world_xy_and_yaw() -> None:
    joint_pos = torch.zeros(1, 36)
    joint_pos[:, :3] = torch.tensor([[0.7, -0.2, 0.8]])
    joint_pos[:, 3:7] = torch.tensor([[0.9938, 0.0997, -0.0499, 0.0050]])
    joint_pos[:, 7:] = torch.linspace(-0.3, 0.4, 29)
    joint_vel = torch.zeros(1, 35)
    joint_vel[:, :3] = torch.tensor([[0.4, -0.2, 0.1]])
    joint_vel[:, 3:6] = torch.tensor([[0.2, 0.3, -0.1]])
    joint_vel[:, 6:] = torch.linspace(-0.5, 0.5, 29)

    yaw = torch.tensor(0.7)
    half = 0.5 * yaw
    delta = torch.tensor([[torch.cos(half), 0.0, 0.0, torch.sin(half)]])
    w, x, y, z = delta.unbind(dim=-1)
    qw, qx, qy, qz = joint_pos[:, 3:7].unbind(dim=-1)
    transformed_pos = joint_pos.clone()
    transformed_pos[:, :2] += torch.tensor([[1.2, -0.8]])
    transformed_pos[:, 3:7] = torch.stack(
        (
            w * qw - x * qx - y * qy - z * qz,
            w * qx + x * qw + y * qz - z * qy,
            w * qy - x * qz + y * qw + z * qx,
            w * qz + x * qy - y * qx + z * qw,
        ),
        dim=-1,
    )
    transformed_vel = joint_vel.clone()
    cosine, sine = torch.cos(yaw), torch.sin(yaw)
    for start in (0, 3):
        vx, vy = joint_vel[:, start], joint_vel[:, start + 1]
        transformed_vel[:, start] = cosine * vx - sine * vy
        transformed_vel[:, start + 1] = sine * vx + cosine * vy

    torch.testing.assert_close(
        canonical_boundary_state(transformed_pos, transformed_vel),
        canonical_boundary_state(joint_pos, joint_vel),
        atol=1.0e-5,
        rtol=1.0e-5,
    )


def test_terrain_scalar_conditions_theta_without_changing_code_logits() -> None:
    model = CausalSegmentFutureModel(
        height_dim=4,
        terrain_scalar_dim=1,
        state_dim=3,
        feature_dim=7,
        num_codes=3,
        theta_dim=2,
        max_frames=3,
        branch_dim=6,
        context_dim=8,
        code_embed_dim=3,
        dynamics_dim=8,
        dynamics_layers=1,
        time_harmonics=1,
        scan_grid_shapes=((2, 2),),
        previous_code_dropout=0.0,
    ).eval()
    observation = torch.zeros(2, 8)
    observation[1, 4] = 2.0
    output = model(observation, start_state=torch.zeros(2, 7), previous_code=torch.tensor([0, 0]))

    torch.testing.assert_close(output["code_logits"][0], output["code_logits"][1])
    assert not torch.allclose(output["theta"][0], output["theta"][1])


def test_masked_reconstruction_weights_actual_segments_equally() -> None:
    model = GMVQAutoEncoder(t=4, d=1, latent_dim=2, num_codes=2)
    x = torch.zeros((2, 4, 1))
    recon = torch.zeros_like(x)
    recon[0, 0, 0] = 2.0
    recon[1, :, 0] = 1.0
    output = model(x)
    output["x_recon"] = recon
    valid_mask = torch.tensor([[True, False, False, False], [True, True, True, True]])
    cfg = type(
        "LossConfig",
        (),
        {
            "beta_theta": 0.0,
            "beta_rate": 0.0,
            "beta_commit": 0.0,
            "beta_usage": 0.0,
            "beta_sigma": 0.0,
            "beta_vel": 0.0,
            "beta_mix": 0.0,
            "beta_balance": 0.0,
            "beta_sep": 0.0,
            "beta_theta_moments": 0.0,
            "beta_length": 0.0,
        },
    )()

    _, metrics = compute_loss(x, output, model, cfg, valid_mask=valid_mask)

    assert torch.isclose(metrics["recon_loss"], torch.tensor(2.5))


def test_frozen_codec_accepts_force_free_kinematic_ref_checkpoint(tmp_path: Path) -> None:
    model = GMVQAutoEncoder(t=4, d=3, latent_dim=2, num_codes=2, decoder_type="time")
    checkpoint = tmp_path / "force_free_gmvq.pt"
    torch.save(
        {
            "model_state": model.state_dict(),
            "model_config": model.config(),
            "robot_asset": canonical_g1_source_metadata(),
            "contact_force_provenance": None,
            "norm_stats": None,
        },
        checkpoint,
    )

    codec = FrozenGMVQCodec(checkpoint)

    assert codec.contact_force_provenance is None
    assert codec.reference_kind == "kinematic_ref"
    code = torch.tensor([0])
    theta = torch.zeros((1, 2))
    lengths = torch.tensor([2])
    decoded = codec.decode_hybrid(code, theta, lengths=lengths)
    assert decoded["x_hat"].shape == (1, 4, 3)
    with torch.no_grad():
        q = codec.model.quantizer
        z_q = q.code_mu[code] + q.sigma()[code] * q._theta_for_decode(theta)
        expected = codec.model.decoder(z_q, lengths=lengths)
    assert torch.allclose(decoded["x_hat"], expected)
    full_length = codec.decode_hybrid(code, theta, lengths=torch.tensor([4]))["x_hat"]
    assert not torch.allclose(decoded["x_hat"], full_length)


def test_code_only_stage_decodes_from_discrete_prototype() -> None:
    model = GMVQAutoEncoder(
        t=4,
        d=3,
        latent_dim=4,
        theta_dim=2,
        num_codes=3,
        decoder_type="time",
        theta_enabled=False,
    )
    output = model(torch.randn(5, 4, 3), lengths=torch.full((5,), 4))

    expected = model.quantizer.code_mu[output["codes"]]
    assert output["theta"].shape == (5, 2)
    assert torch.allclose(output["z_q"], expected)
    assert model.config()["theta_enabled"] is False
    assert model.config()["theta_dim"] == 2


def test_dual_view_keeps_code_assignment_independent_of_absolute_target() -> None:
    torch.manual_seed(7)
    model = GMVQAutoEncoder(
        t=4,
        d=3,
        latent_dim=4,
        theta_dim=2,
        num_codes=3,
        encoder_type="bigru_masked",
        decoder_type="time",
        theta_enabled=True,
        dual_view=True,
    )
    code_x = torch.randn(1, 4, 3).repeat(2, 1, 1)
    target = torch.randn(1, 4, 3).repeat(2, 1, 1)
    target[1] += 5.0
    output = model(
        target,
        code_x=code_x,
        valid_mask=torch.ones((2, 4), dtype=torch.bool),
        lengths=torch.full((2,), 4),
    )

    assert output["codes"][0] == output["codes"][1]
    assert torch.allclose(output["z_e"][0], output["z_e"][1])
    assert not torch.allclose(output["z_theta_source"][0], output["z_theta_source"][1])
    assert not torch.allclose(output["theta"][0], output["theta"][1])
    assert model.config()["dual_view"] is True


def test_dual_view_dataset_normalizes_code_and_target_views_separately(tmp_path: Path) -> None:
    target = np.arange(24, dtype=np.float32).reshape(2, 4, 3)
    code = target * 0.1 - target.mean(axis=1, keepdims=True)
    data_path = tmp_path / "dual_view.npz"
    np.savez(
        data_path,
        segments=target,
        code_segments=code,
        valid_mask=np.ones((2, 4), dtype=np.bool_),
        lengths=np.full((2,), 4, dtype=np.int64),
        robot_asset_json=np.asarray(encode_robot_asset_json()),
    )

    dataset, target_stats = build_dataset(str(data_path), synthetic=False)

    assert target_stats is not None
    assert dataset.code_norm_stats is not None
    item = dataset[0]
    assert isinstance(item, dict)
    assert item["x"].shape == item["code_x"].shape == (4, 3)
    assert not torch.allclose(target_stats.mean, dataset.code_norm_stats.mean)


def test_reduced_theta_roundtrip_is_supported_by_frozen_codec(tmp_path: Path) -> None:
    model = GMVQAutoEncoder(
        t=4,
        d=3,
        latent_dim=4,
        theta_dim=2,
        num_codes=3,
        decoder_type="time",
        theta_enabled=True,
    )
    checkpoint = tmp_path / "reduced_theta_gmvq.pt"
    torch.save(
        {
            "model_state": model.state_dict(),
            "model_config": model.config(),
            "robot_asset": canonical_g1_source_metadata(),
            "contact_force_provenance": None,
            "norm_stats": None,
        },
        checkpoint,
    )

    codec = FrozenGMVQCodec(checkpoint)
    assert codec.theta_dim == 2
    decoded = codec.decode_hybrid(
        torch.tensor([0, 1]),
        torch.zeros((2, 2)),
        lengths=torch.tensor([2, 4]),
    )
    assert decoded["x_hat"].shape == (2, 4, 3)
    assert decoded["z_q"].shape == (2, 4)


def test_local_output_theta_is_a_code_specific_linear_residual() -> None:
    model = GMVQAutoEncoder(
        t=4,
        d=3,
        latent_dim=4,
        theta_dim=2,
        num_codes=3,
        decoder_type="time",
        theta_enabled=True,
        local_output_theta=True,
    )
    with torch.no_grad():
        model.local_theta_basis.zero_()
        model.local_theta_basis[1, 0, :, 2] = 0.25

    codes = torch.tensor([0, 1, 1])
    theta = torch.tensor([[1.0, 0.0], [1.0, 0.0], [-1.0, 0.0]])
    decoded = model.decode_hybrid(codes, theta, lengths=torch.full((3,), 4))["x_hat"]

    assert torch.allclose(decoded[1, :, :2], decoded[2, :, :2])
    assert torch.allclose(decoded[1, :, 2] - decoded[2, :, 2], torch.full((4,), 0.5))
    assert model.config()["local_output_theta"] is True


def test_trajectory_bootstrap_clusters_motion_without_segment_metadata() -> None:
    base = torch.linspace(0.0, 1.0, 8)
    segments = torch.zeros((6, 8, 3))
    segments[0:2, :, 0] = base
    segments[2:4, :, 1] = -base
    segments[4:6, :, 2] = torch.sin(base * torch.pi)
    segments[1] += 0.01
    segments[3] -= 0.01
    segments[5] += 0.005
    valid_mask = torch.ones((6, 8), dtype=torch.bool)

    embedding = _trajectory_embeddings(
        segments,
        valid_mask,
        phase_steps=8,
        pca_dim=3,
    )
    labels = _kmeans_labels(embedding, num_codes=3, restarts=8)

    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[4] == labels[5]
    assert len(set(labels.tolist())) == 3


def test_three_view_gmvq_accepts_distinct_code_theta_and_target_dimensions() -> None:
    model = GMVQAutoEncoder(
        t=5,
        d=7,
        code_d=3,
        theta_d=9,
        latent_dim=4,
        theta_dim=2,
        num_codes=3,
        encoder_type="bigru_masked",
        decoder_type="time",
        dual_view=True,
        local_output_theta=True,
    )
    output = model(
        torch.randn(2, 5, 7),
        code_x=torch.randn(2, 5, 3),
        theta_x=torch.randn(2, 5, 9),
        valid_mask=torch.ones((2, 5), dtype=torch.bool),
        lengths=torch.full((2,), 5),
    )

    assert output["x_recon"].shape == (2, 5, 7)
    assert model.config()["code_d"] == 3
    assert model.config()["theta_d"] == 9
