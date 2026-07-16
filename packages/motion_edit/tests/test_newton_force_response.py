from __future__ import annotations

import numpy as np

from motion_edit.physics_retarget.force_response import (
    NewtonForceResponseConfig,
    estimate_force_displacement_secant,
    force_directions,
    force_matching_displacement,
    probe_normal_displacement,
)


def test_contact_direction_comes_from_target_force_without_geometry() -> None:
    force = np.asarray([[[3.0, 4.0, 0.0], [0.0, 0.0, 0.0]]])
    directions = force_directions(force, np.asarray([[True, False]]))

    np.testing.assert_allclose(directions[0, 0], [0.6, 0.8, 0.0])
    np.testing.assert_allclose(directions[0, 1], [0.0, 0.0, 1.0])


def test_zero_force_frames_in_closed_contact_gap_interpolate_force_direction() -> None:
    force = np.asarray(
        [
            [[1.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0]],
            [[0.0, 1.0, 0.0]],
        ]
    )
    directions = force_directions(force, np.ones((3, 1), dtype=bool))

    np.testing.assert_allclose(directions[1, 0], [2**-0.5, 2**-0.5, 0.0])


def test_active_part_without_any_force_sample_is_rejected() -> None:
    force = np.zeros((3, 1, 3), dtype=np.float64)

    with np.testing.assert_raises_regex(ValueError, "part 0 has no nonzero"):
        force_directions(force, np.ones((3, 1), dtype=bool))


def test_probe_moves_inward_when_newton_force_is_too_low() -> None:
    config = NewtonForceResponseConfig(probe_displacement_m=5.0e-4)
    target = np.asarray([[100.0, 0.0]])
    actual = np.asarray([[20.0, 0.0]])
    mask = np.asarray([[True, False]])

    displacement = probe_normal_displacement(
        target_force_n=target,
        actual_force_n=actual,
        contact_mask=mask,
        config=config,
    )

    assert displacement[0, 0] < 0.0
    assert abs(displacement[0, 0]) <= config.probe_displacement_m
    assert displacement[0, 1] == 0.0


def test_secant_uses_newton_force_response_without_fixed_stiffness() -> None:
    config = NewtonForceResponseConfig(temporal_median_radius=0)
    baseline = np.asarray([[20.0], [40.0]])
    response = np.asarray([[30.0], [60.0]])
    achieved = np.asarray([[-0.001], [-0.002]])
    mask = np.ones((2, 1), dtype=bool)

    slope, valid = estimate_force_displacement_secant(
        baseline_force_n=baseline,
        response_force_n=response,
        achieved_displacement_m=achieved,
        contact_mask=mask,
        config=config,
    )

    np.testing.assert_allclose(slope, -10_000.0)
    np.testing.assert_array_equal(valid, True)


def test_force_matching_uses_measured_secant_and_trust_limit() -> None:
    config = NewtonForceResponseConfig(max_displacement_m=0.003)
    displacement = force_matching_displacement(
        target_force_n=np.asarray([[100.0, 100.0]]),
        actual_force_n=np.asarray([[50.0, 0.0]]),
        response_n_per_m=np.asarray([[-10_000.0, np.nan]]),
        response_valid=np.asarray([[True, False]]),
        contact_mask=np.asarray([[True, True]]),
        config=config,
    )

    assert displacement[0, 0] == -0.003
    assert -config.probe_displacement_m <= displacement[0, 1] < 0.0
