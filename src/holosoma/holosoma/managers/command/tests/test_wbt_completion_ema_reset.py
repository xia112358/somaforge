from types import SimpleNamespace

import torch

from holosoma.managers.command.terms.wbt import MotionCommand


def _command() -> MotionCommand:
    command = MotionCommand.__new__(MotionCommand)
    command.device = torch.device("cpu")
    command.motion_cfg = SimpleNamespace(
        hotspot_failure_uniform_mix=0.0,
        failure_window_pre_frames=0,
        failure_window_post_frames=0,
        failure_window_before_prob=1.0,
    )
    command.motion = SimpleNamespace(
        motion_start_idx=torch.tensor([0, 1000]),
        motion_end_idx=torch.tensor([101, 1201]),
    )
    command.motion_ids = torch.tensor([0, 1])
    command._failure_window_retry_active = torch.zeros(2, dtype=torch.bool)
    command._failure_window_retry_motion_ids = torch.full((2,), -1, dtype=torch.long)
    command._failure_window_retry_target_steps = torch.zeros(2, dtype=torch.long)
    command._use_start_probe_envs = True
    command._use_group_probe_envs = False
    command._probe_count = torch.tensor([4, 4])
    command._probe_completion_ema = torch.tensor([0.4, 0.6])
    return command


def test_completion_ema_branch_resets_at_completion_ema_mean() -> None:
    command = _command()

    sampled = command._sample_completion_ema_failure_window_time_steps(
        torch.tensor([0, 1])
    )

    assert sampled.tolist() == [50, 1100]
    assert command._failure_window_retry_active.tolist() == [True, True]
    assert command._failure_window_retry_motion_ids.tolist() == [0, 1]
    assert command._failure_window_retry_target_steps.tolist() == [50, 1100]


def test_completion_ema_branch_is_uniform_until_probe_has_reported() -> None:
    command = _command()
    command._probe_count.zero_()

    torch.manual_seed(7)
    sampled = command._sample_completion_ema_failure_window_time_steps(
        torch.tensor([0, 1])
    )

    assert 0 <= sampled[0].item() < 100
    assert 1000 <= sampled[1].item() < 1200
    assert command._failure_window_retry_active.tolist() == [False, False]
