from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse

from motion_edit.contact_laplacian import (
    BodyPositionTrajectoryKinematicsProvider,
    InteractionMeshSpec,
)
from motion_edit.contact_laplacian.residuals import (
    prepare_interaction_mesh_laplacian,
)
from motion_edit.contact_laplacian.solver import _solve_least_squares


def test_sparse_factorized_solve_matches_dense_least_squares() -> None:
    matrix = sparse.csr_matrix(
        np.asarray(
            [
                [2.0, 0.0],
                [0.0, 3.0],
                [1.0, -1.0],
                [0.1, 0.0],
                [0.0, 0.1],
            ],
            dtype=np.float64,
        )
    )
    rhs = np.asarray([1.0, -2.0, 0.5, 0.0, 0.0], dtype=np.float64)

    actual = _solve_least_squares(matrix, rhs, True)
    expected = np.linalg.lstsq(matrix.toarray(), rhs, rcond=None)[0]

    np.testing.assert_allclose(actual, expected, atol=1.0e-11, rtol=0.0)


def test_interaction_topology_cache_is_exact_and_fail_closed(
    tmp_path,
    monkeypatch,
) -> None:
    cache = tmp_path / "topology.npz"
    monkeypatch.setenv("SOMAFORGE_LAPLACIAN_TOPOLOGY_CACHE", str(cache))
    provider = BodyPositionTrajectoryKinematicsProvider(("left_foot",))
    q_reference = np.zeros((3, 3), dtype=np.float64)
    mesh = InteractionMeshSpec(
        robot_points=("left_foot",),
        object_points=np.asarray([[1.0, 0.0, 0.0]], dtype=np.float64),
        edges=((0, 1),),
        reference_object_points=np.asarray([[1.0, 0.0, 0.0]], dtype=np.float64),
    )

    first = prepare_interaction_mesh_laplacian(
        mesh=mesh,
        q_reference=q_reference,
        kinematics=provider,
    )
    second = prepare_interaction_mesh_laplacian(
        mesh=mesh,
        q_reference=q_reference,
        kinematics=provider,
    )

    assert cache.is_file()
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    np.testing.assert_array_equal(
        first["laplacian_matrices"],
        second["laplacian_matrices"],
    )
    changed_target = InteractionMeshSpec(
        robot_points=("left_foot",),
        object_points=np.asarray([[1.0, 0.0, 0.1]], dtype=np.float64),
        edges=((0, 1),),
        reference_object_points=np.asarray([[1.0, 0.0, 0.0]], dtype=np.float64),
    )
    target_variant = prepare_interaction_mesh_laplacian(
        mesh=changed_target,
        q_reference=q_reference,
        kinematics=provider,
    )
    assert target_variant["cache_hit"] is True

    changed_reference = q_reference.copy()
    changed_reference[1, 0] = 0.01
    with pytest.raises(ValueError, match="different source reference"):
        prepare_interaction_mesh_laplacian(
            mesh=mesh,
            q_reference=changed_reference,
            kinematics=provider,
        )
