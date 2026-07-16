import copy
from types import SimpleNamespace

import torch
from holosoma.agents.modules.data_utils import RolloutStorage
from holosoma.agents.ppo.kl_early_stop_ppo import KLEarlyStopPPO
from holosoma.agents.ppo.ppo import PPO


def test_actor_rollback_restores_adamw_parameters_and_optimizer_state() -> None:
    actor = torch.nn.Linear(3, 2)
    optimizer = torch.optim.AdamW(actor.parameters(), lr=1e-3)

    optimizer.zero_grad()
    actor(torch.ones(4, 3)).sum().backward()
    optimizer.step()
    actor_state, optimizer_state = KLEarlyStopPPO._snapshot_actor_update(actor, optimizer)

    optimizer.zero_grad()
    actor(torch.full((4, 3), 2.0)).sum().backward()
    optimizer.step()
    KLEarlyStopPPO._restore_actor_update(actor, optimizer, actor_state, optimizer_state)

    restored_actor_state = actor.state_dict()
    for key, expected in actor_state.items():
        torch.testing.assert_close(restored_actor_state[key], expected)

    restored_optimizer_state = optimizer.state_dict()
    expected_optimizer_state = copy.deepcopy(optimizer_state)
    assert restored_optimizer_state["param_groups"] == expected_optimizer_state["param_groups"]
    for parameter_id, expected_state in expected_optimizer_state["state"].items():
        for key, expected in expected_state.items():
            actual = restored_optimizer_state["state"][parameter_id][key]
            if torch.is_tensor(expected):
                torch.testing.assert_close(actual, expected)
            else:
                assert actual == expected


def test_rollback_learning_rate_targets_early_stop_kl_and_respects_floor() -> None:
    backed_off = KLEarlyStopPPO._rollback_learning_rate(
        current_learning_rate=1e-2,
        minimum_learning_rate=1e-5,
        post_kl=15.0,
        target_kl=0.02,
    )
    assert 3e-4 < backed_off < 4e-4

    floored = KLEarlyStopPPO._rollback_learning_rate(
        current_learning_rate=1e-5,
        minimum_learning_rate=1e-5,
        post_kl=0.05,
        target_kl=0.02,
    )
    assert floored == 1e-5


def test_refresh_rollout_policy_statistics_preserves_means_above_ten() -> None:
    class FakeActor:
        std = torch.tensor([0.5])

        @staticmethod
        def act_raw_inference(policy_state_dict):
            return policy_state_dict["actor_obs"] * 2.0

    storage = RolloutStorage(num_envs=2, num_transitions_per_env=2)
    storage.register("actor_obs", shape=(1,))
    storage.register("action_mean", shape=(1,))
    storage.register("action_sigma", shape=(1,))
    storage["actor_obs"].copy_(torch.tensor([[[6.0], [7.0]], [[8.0], [9.0]]]))

    algo = object.__new__(KLEarlyStopPPO)
    algo.storage = storage
    algo.config = SimpleNamespace(num_mini_batches=2)
    algo.actor = FakeActor()
    algo._refresh_rollout_policy_statistics()

    torch.testing.assert_close(storage["action_mean"].flatten(), torch.tensor([12.0, 14.0, 16.0, 18.0]))
    torch.testing.assert_close(storage["action_sigma"], torch.full_like(storage["action_sigma"], 0.5))


def test_raw_gaussian_kl_is_zero_for_unchanged_means_above_action_bound() -> None:
    algo = object.__new__(PPO)
    algo.is_multi_gpu = False
    raw_mean = torch.tensor([[25.0, -18.0]])
    sigma = torch.tensor([[0.5, 0.8]])

    kl = algo._compute_kl_div(raw_mean, sigma, raw_mean.clone(), sigma.clone())

    torch.testing.assert_close(kl, torch.tensor(0.0))
