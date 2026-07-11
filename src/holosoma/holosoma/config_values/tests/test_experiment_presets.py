from holosoma.config_values.experiment import DEFAULTS
from holosoma.config_values.wbt.g1.command import (
    BASELINE_29_MANIFEST,
    BASELINE_SINGLE_MANIFEST,
    CONTACT_FORCE_MANIFEST,
)

EXPECTED_MANIFESTS = {
    "g1_29dof_wbt_baseline_single": BASELINE_SINGLE_MANIFEST,
    "g1_29dof_wbt_baseline_29": BASELINE_29_MANIFEST,
    "g1_29dof_wbt_contact_force": CONTACT_FORCE_MANIFEST,
}


def _motion_config(experiment):
    return experiment.command.setup_terms["motion_command"].params["motion_config"]


def test_only_canonical_pipeline_experiments_are_registered() -> None:
    assert set(DEFAULTS) == set(EXPECTED_MANIFESTS)
    assert len({experiment.training.name for experiment in DEFAULTS.values()}) == len(DEFAULTS)


def test_experiments_bind_one_manifest_to_motion_and_terrain() -> None:
    for name, experiment in DEFAULTS.items():
        expected_manifest = EXPECTED_MANIFESTS[name]
        assert _motion_config(experiment).motion_manifest == expected_manifest
        assert experiment.terrain.terrain_term.motion_matched_manifest == expected_manifest


def test_experiments_use_canonical_robot_newton_and_compact_outputs() -> None:
    for experiment in DEFAULTS.values():
        assert experiment.robot.asset.urdf_file == "g1/g1_29dof_spherehand.urdf"
        assert experiment.simulator.config.name == "isaaclab3_newton"
        assert experiment.training.num_envs == 4096
        assert experiment.training.export_onnx is False
        assert experiment.algo.config.export_onnx is False
        assert experiment.algo.config.num_learning_iterations == 20000
        assert experiment.algo.config.num_learning_epochs == 5
        assert experiment.algo.config.actor_learning_rate == 1e-3
        assert experiment.algo.config.critic_learning_rate == 1e-3
        assert experiment.algo.config.min_actor_learning_rate is None
        assert experiment.algo.config.min_critic_learning_rate is None
        assert experiment.algo.config.max_actor_learning_rate is None
        assert experiment.algo.config.max_critic_learning_rate is None
        assert experiment.algo.config.save_interval == 1000


def test_experiment_sampler_roles_are_explicit() -> None:
    for experiment in DEFAULTS.values():
        motion = _motion_config(experiment)
        assert motion.reset_sampler == "hotspot_failure_window"
        assert motion.start_at_timestep_zero_prob == 0.0
    single_motion = _motion_config(DEFAULTS["g1_29dof_wbt_baseline_single"])
    assert single_motion.use_start_probe_envs is True
    assert single_motion.probe_env_per_motion == 10


def test_experiment_episode_horizons_match_training_stage() -> None:
    assert DEFAULTS["g1_29dof_wbt_baseline_single"].simulator.config.sim.max_episode_length_s == 22.0
    assert DEFAULTS["g1_29dof_wbt_baseline_29"].simulator.config.sim.max_episode_length_s == 10.0
    assert DEFAULTS["g1_29dof_wbt_contact_force"].simulator.config.sim.max_episode_length_s == 20.0
