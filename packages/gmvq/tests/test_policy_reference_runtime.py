from __future__ import annotations

from types import SimpleNamespace

import torch
from gmvq.current_frame_future import CausalSegmentFutureModel
from gmvq.g1_fk import CanonicalG1TorchFK
from gmvq.policy_reference import (
    GMVQOnlineReference,
    GMVQPolicyReferenceRuntime,
    SharedNextAtomSelector,
    query_local_height_scan,
)


def test_query_local_height_scan_rotates_training_grid_by_root_yaw() -> None:
    grid = torch.tensor([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0]])
    root_pos = torch.tensor([[10.0, 20.0, 3.0]])
    half = 2.0**-0.5
    root_quat = torch.tensor([[half, 0.0, 0.0, half]])
    queried: list[torch.Tensor] = []

    def query(xy: torch.Tensor) -> torch.Tensor:
        queried.append(xy.clone())
        return xy[:, 0] + 2.0 * xy[:, 1]

    scan = query_local_height_scan(
        local_grid=grid,
        root_pos_w=root_pos,
        root_quat_wxyz=root_quat,
        query_terrain_heights=query,
    )
    torch.testing.assert_close(queried[0], torch.tensor([[10.0, 21.0], [8.0, 20.0]]))
    torch.testing.assert_close(scan, torch.tensor([[49.0, 45.0]]))


class _FakeRuntime:
    device_ref = torch.device("cpu")
    max_frames = 4
    codec = SimpleNamespace(theta_dim=2)

    def decode_next(self, *, height_scan, joint_pos, joint_vel, previous_code):
        del height_scan
        batch = joint_pos.shape[0]
        steps = torch.arange(self.max_frames, dtype=torch.float32)[None, :, None]
        q = joint_pos[:, None, :].expand(-1, self.max_frames, -1).clone()
        q[..., :1] += steps
        qd = joint_vel[:, None, :].expand(-1, self.max_frames, -1).clone()
        codes = previous_code + 1
        return {
            "joint_pos": q,
            "joint_vel": qd,
            "codes": codes,
            "theta": torch.zeros(batch, 2),
            "lengths": torch.full((batch,), 3, dtype=torch.long),
            "stopped": torch.zeros(batch, dtype=torch.bool),
        }


def test_online_reference_refreshes_environments_independently_at_boundaries() -> None:
    provider = GMVQOnlineReference(_FakeRuntime(), num_envs=2)
    ids = torch.arange(2)
    scan = torch.zeros(2, 1)
    q = torch.zeros(2, 36)
    qd = torch.zeros(2, 35)
    provider.reset(ids, height_scan=scan, joint_pos=q, joint_vel=qd)
    provider.cursors[:] = torch.tensor([2, 1])

    refreshed = provider.advance(height_scan=scan, joint_pos=q, joint_vel=qd)

    assert refreshed.tolist() == [0]
    assert provider.cursors.tolist() == [0, 2]
    assert provider.codes.tolist() == [1, 0]


def test_online_reference_pauses_only_environments_that_are_not_tracking_ready() -> None:
    provider = GMVQOnlineReference(_FakeRuntime(), num_envs=2)
    ids = torch.arange(2)
    scan = torch.zeros(2, 1)
    q = torch.zeros(2, 36)
    qd = torch.zeros(2, 35)
    provider.reset(ids, height_scan=scan, joint_pos=q, joint_vel=qd)

    provider.advance(
        height_scan=scan,
        joint_pos=q,
        joint_vel=qd,
        advance_ready=torch.tensor([False, True]),
    )

    assert provider.cursors.tolist() == [0, 1]


def test_canonical_g1_fk_preserves_floating_pelvis_pose() -> None:
    joint_names = [
        "left_hip_pitch_joint",
        "left_hip_roll_joint",
        "left_hip_yaw_joint",
        "left_knee_joint",
        "left_ankle_pitch_joint",
        "left_ankle_roll_joint",
        "right_hip_pitch_joint",
        "right_hip_roll_joint",
        "right_hip_yaw_joint",
        "right_knee_joint",
        "right_ankle_pitch_joint",
        "right_ankle_roll_joint",
        "waist_yaw_joint",
        "waist_roll_joint",
        "waist_pitch_joint",
        "left_shoulder_pitch_joint",
        "left_shoulder_roll_joint",
        "left_shoulder_yaw_joint",
        "left_elbow_joint",
        "left_wrist_roll_joint",
        "left_wrist_pitch_joint",
        "left_wrist_yaw_joint",
        "right_shoulder_pitch_joint",
        "right_shoulder_roll_joint",
        "right_shoulder_yaw_joint",
        "right_elbow_joint",
        "right_wrist_roll_joint",
        "right_wrist_pitch_joint",
        "right_wrist_yaw_joint",
    ]
    fk = CanonicalG1TorchFK(joint_names=joint_names, link_names=["pelvis", "torso_link"])
    q = torch.zeros(2, 36)
    q[:, :3] = torch.tensor([1.0, 2.0, 3.0])
    q[:, 3] = 1.0
    pos, quat = fk.forward_pose(q)
    torch.testing.assert_close(pos[:, 0], q[:, :3])
    torch.testing.assert_close(quat[:, 0], q[:, 3:7])
    assert pos.shape == (2, 2, 3)
    assert quat.shape == (2, 2, 4)


def test_shared_next_atom_selector_does_not_force_observed_transition() -> None:
    model = SharedNextAtomSelector(height_dim=2, state_dim=3, num_codes=4, theta_dim=2, branch_dim=8, context_dim=12)
    with torch.no_grad():
        model.code_head.weight.zero_()
        model.code_head.bias.copy_(torch.tensor([0.0, 4.0, 2.0, 3.0]))
    observation = torch.zeros(2, 5)
    previous = torch.tensor([0, 1])
    transition = torch.zeros(4, 4, dtype=torch.bool)
    transition[0, 2] = True
    transition[1, 3] = True
    logits, codes, theta = model(observation, previous, transition)
    assert logits.shape == (2, 4)
    assert codes.tolist() == [1, 1]
    assert theta.shape == (2, 2)


def test_legacy_runtime_does_not_force_observed_transition() -> None:
    runtime = GMVQPolicyReferenceRuntime.__new__(GMVQPolicyReferenceRuntime)
    torch.nn.Module.__init__(runtime)
    runtime.device_ref = torch.device("cpu")
    runtime.next_atom_model = None
    runtime.code_model = torch.nn.Linear(86, 2)
    with torch.no_grad():
        runtime.code_model.weight.zero_()
        runtime.code_model.bias.copy_(torch.tensor([0.0, 4.0]))
    runtime.theta_model = None
    runtime.codec = SimpleNamespace(t=4, theta_dim=2)
    runtime.stop_code = 1
    runtime.register_buffer("local_grid", torch.zeros(2, 3))
    runtime.register_buffer("length_prior", torch.ones(1, dtype=torch.long))
    runtime.register_buffer("transition_mask", torch.tensor([[True, False], [False, False]]))
    runtime.register_buffer("code_mean", torch.zeros(86))
    runtime.register_buffer("code_std", torch.ones(86))

    result = runtime.decode_next(
        height_scan=torch.zeros(1, 2),
        joint_pos=torch.zeros(1, 36),
        joint_vel=torch.zeros(1, 35),
        previous_code=torch.tensor([0]),
    )

    assert result["codes"].tolist() == [1]
    assert result["stopped"].tolist() == [True]


def test_runtime_prefers_causal_current_frame_future_without_transition_state() -> None:
    model = CausalSegmentFutureModel(
        height_dim=2,
        state_dim=84,
        feature_dim=71,
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
    with torch.no_grad():
        model.code_head.weight.zero_()
        model.code_head.bias.copy_(torch.tensor([2.0, 0.0]))
        model.previous_code_head.weight.zero_()
        model.length_prior.copy_(torch.tensor([4, 1]))

    class _GuideCodec:
        t = 4
        theta_dim = 2

        def decode_hybrid(self, codes, theta, *, lengths):
            del codes, theta, lengths
            guide = torch.zeros(1, 4, 71)
            guide[..., 3] = 1.0
            guide[0, :, 0] = torch.tensor([0.0, 0.1, 0.2, 0.3])
            return {"x_hat": guide}

    runtime = GMVQPolicyReferenceRuntime.__new__(GMVQPolicyReferenceRuntime)
    torch.nn.Module.__init__(runtime)
    runtime.device_ref = torch.device("cpu")
    runtime.current_frame_future = model
    runtime.codec = _GuideCodec()
    runtime.stop_code = 1
    runtime.register_buffer("local_grid", torch.zeros(2, 3))
    for name, value in (
        ("future_observation_mean", torch.zeros(86)),
        ("future_observation_std", torch.ones(86)),
        ("future_target_mean", torch.zeros(71)),
        ("future_target_std", torch.ones(71)),
        ("future_theta_mean", torch.zeros(2)),
        ("future_theta_std", torch.ones(2)),
    ):
        runtime.register_buffer(name, value)
    q = torch.zeros(1, 36)
    q[:, 0] = 5.0
    q[:, 3] = 1.0
    result = runtime.decode_next(
        height_scan=torch.zeros(1, 2),
        joint_pos=q,
        joint_vel=torch.zeros(1, 35),
        previous_code=torch.tensor([99]),
    )

    assert result["codes"].tolist() == [0]
    assert result["lengths"].tolist() == [4]
    torch.testing.assert_close(result["joint_pos"][0, :, 0], torch.tensor([5.0, 5.1, 5.2, 5.3]))
    torch.testing.assert_close(result["joint_pos"][:, 0], q, rtol=0.0, atol=0.0)
