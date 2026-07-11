from types import SimpleNamespace

import torch
from holosoma.managers.command.terms.wbt import MotionCommand


def test_start_probe_tensorboard_metrics_are_summary_only() -> None:
    command = SimpleNamespace(
        _use_completion_learning_sampler=False,
        _use_group_probe_envs=False,
        _use_start_probe_envs=True,
        _probe_completion_ema=torch.tensor([0.2, 0.7, 0.5]),
        _probe_success_ema=torch.tensor([0.1, 0.8, 0.4]),
        _probe_fail_ema=torch.tensor([0.7, 0.1, 0.3]),
        _probe_timeout_ema=torch.tensor([0.2, 0.1, 0.3]),
        _probe_count=torch.tensor([4, 7, 5]),
        _normal_motion_sampling_weights=torch.tensor([0.6, 0.1, 0.3]),
    )

    metrics = MotionCommand.get_motion_learning_progress_metrics(command)

    assert set(metrics) == {
        "start_probe_episode_count",
        "completion_ema_mean",
        "completion_ema_min",
        "completion_ema_min_motion",
        "start_to_end_success_ema_mean",
        "start_to_end_success_ema_min",
        "start_to_end_success_ema_min_motion",
        "fail_ema_mean",
        "timeout_ema_mean",
        "normal_motion_weight_max",
        "normal_motion_weight_max_motion",
    }
    assert metrics["start_probe_episode_count"] == 16.0


def test_group_probe_tensorboard_metrics_are_summary_only() -> None:
    command = SimpleNamespace(
        _use_completion_learning_sampler=False,
        _use_group_probe_envs=True,
        _group_probe_completion_ema=torch.tensor([0.25, 0.75]),
        _group_probe_success_ema=torch.tensor([0.2, 0.8]),
        _group_probe_fail_ema=torch.tensor([0.6, 0.1]),
        _group_probe_timeout_ema=torch.tensor([0.2, 0.1]),
        _normal_group_sampling_weights=torch.tensor([0.7, 0.3]),
    )

    metrics = MotionCommand.get_motion_learning_progress_metrics(command)

    assert set(metrics) == {
        "group_probe_completion_ema_mean",
        "group_probe_completion_ema_min",
        "group_probe_completion_ema_min_group",
        "group_probe_start_to_end_success_ema_mean",
        "group_probe_start_to_end_success_ema_min",
        "group_probe_start_to_end_success_ema_min_group",
        "group_probe_fail_ema_mean",
        "group_probe_timeout_ema_mean",
        "group_probe_normal_group_weight_max",
        "group_probe_normal_group_weight_max_group",
    }


def test_completion_sampler_tensorboard_metrics_are_summary_only() -> None:
    command = SimpleNamespace(
        _use_completion_learning_sampler=True,
        _completion_learned_mask=torch.tensor([False, True, False]),
        _normal_motion_sampling_weights=torch.tensor([0.6, 0.1, 0.3]),
        _completion_progress_ema=torch.tensor([0.2, 0.9, 0.4]),
        _completion_success_ema=torch.tensor([0.1, 0.8, 0.3]),
        _completion_fail_ema=torch.tensor([0.7, 0.1, 0.5]),
    )

    metrics = MotionCommand.get_motion_learning_progress_metrics(command)

    assert set(metrics) == {
        "completion_learned_frac",
        "completion_progress_ema_mean",
        "completion_success_ema_mean",
        "completion_fail_ema_mean",
        "completion_success_ema_min",
        "completion_success_ema_min_motion",
        "completion_normal_motion_weight_max",
        "completion_normal_motion_weight_max_motion",
    }
