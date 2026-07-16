from __future__ import annotations

import numpy as np
from scipy.spatial import Delaunay

from motion_edit.contact_laplacian.omniretarget_mesh import build_omniretarget_interaction_mesh


def _omniretarget_reference(vertices: np.ndarray) -> np.ndarray:
    tetrahedra = Delaunay(vertices).simplices
    adjacency = [set() for _ in range(len(vertices))]
    for tetrahedron in tetrahedra:
        for left in range(4):
            for right in range(left + 1, 4):
                a, b = int(tetrahedron[left]), int(tetrahedron[right])
                adjacency[a].add(b)
                adjacency[b].add(a)
    laplacian = np.zeros((len(vertices), len(vertices)), dtype=np.float64)
    for index, neighbors in enumerate(adjacency):
        if neighbors:
            laplacian[index, index] = 1.0
            for neighbor in neighbors:
                laplacian[index, neighbor] = -1.0 / len(neighbors)
    return laplacian


def test_per_frame_delaunay_laplacian_matches_omniretarget_reference() -> None:
    robot = np.asarray(
        [
            [[0.2, 0.2, 0.8], [0.8, 0.3, 0.5]],
            [[0.3, 0.2, 0.7], [0.7, 0.4, 0.6]],
        ],
        dtype=np.float64,
    )
    terrain = np.asarray(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.1]],
        dtype=np.float64,
    )

    result = build_omniretarget_interaction_mesh(robot, terrain)

    for frame in range(robot.shape[0]):
        vertices = np.vstack([robot[frame], terrain])
        expected = _omniretarget_reference(vertices)
        np.testing.assert_allclose(result.laplacian_matrices[frame], expected)
        np.testing.assert_allclose(result.target_laplacian[frame], expected @ vertices)
    assert result.target_laplacian.shape == (2, 6, 3)


def test_interaction_mesh_requires_real_environment_points() -> None:
    robot = np.zeros((2, 4, 3), dtype=np.float64)
    try:
        build_omniretarget_interaction_mesh(robot, np.zeros((0, 3), dtype=np.float64))
    except ValueError as exc:
        assert "terrain/object" in str(exc)
    else:
        raise AssertionError("Missing environment points must not silently fall back to the origin")
