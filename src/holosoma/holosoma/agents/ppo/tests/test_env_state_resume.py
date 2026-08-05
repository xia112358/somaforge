from types import SimpleNamespace

from holosoma.agents.base_algo.base_algo import BaseAlgo
from holosoma.agents.ppo.ppo import PPO


def test_pending_env_state_is_restored_once_after_reset() -> None:
    ppo = PPO.__new__(PPO)
    state = {"motion_sampler": {"schema": "test"}}
    restored = []
    ppo._pending_env_state = state
    ppo._pending_env_state_restore = True
    ppo._restore_env_state = restored.append

    ppo._restore_pending_env_state_after_reset()
    ppo._restore_pending_env_state_after_reset()

    assert restored == [state]
    assert ppo._pending_env_state is None
    assert ppo._pending_env_state_restore is False


def test_missing_env_state_reaches_environment_restore_hook() -> None:
    restored = []
    algo = BaseAlgo.__new__(BaseAlgo)
    algo.env = SimpleNamespace(load_checkpoint_state=restored.append)

    algo._restore_env_state(None)

    assert restored == [None]
