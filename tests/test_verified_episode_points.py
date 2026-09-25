from types import SimpleNamespace

import numpy as np
import pytest

from motion_edit.generation.contact_episodes import _verified_episode_points


def patch(anchor, frames, points):
    return SimpleNamespace(
        anchor_id=anchor, source_target_frames=frames,
        source_target_points_w=points,
        metadata={'source_target_contract': 'newton_robot_geometry_point_trajectory'},
    )


def test_observed_mask_not_force_or_interpolated_gap():
    p = patch('a', [0, 2], [[[0, 0, 0]], [[2, 0, 0]]])
    xyz, active = _verified_episode_points([p], ['a'], 0, 3)
    np.testing.assert_array_equal(active, [True, False, True])
    np.testing.assert_allclose(xyz[:, 0], [0, 1, 2])


def test_other_surface_and_shape_do_not_leak_into_episode():
    a = patch('a', [0], [[[1, 2, 3]]])
    b = patch('b', [0], [[[99, 99, 99]]])
    xyz, active = _verified_episode_points([a, b], ['a'], 0, 1)
    np.testing.assert_allclose(xyz, [[1, 2, 3]])
    assert active.all()


def test_missing_binding_fails_without_distance_or_force_fallback():
    with pytest.raises(ValueError, match='missing verified'):
        _verified_episode_points([], ['a'], 0, 1)
