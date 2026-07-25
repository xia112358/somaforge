from __future__ import annotations

from functools import lru_cache

import numpy as np

from motion_edit.generation import omni_contact_graph as omni


@lru_cache(maxsize=8192)
def _cached_delaunay_edges_bytes(
    shape: tuple[int, int],
    payload: bytes,
) -> tuple[tuple[tuple[int, int], ...], bool]:
    from scipy.spatial import Delaunay, QhullError

    points = np.frombuffer(payload, dtype=np.float64).reshape(shape)
    try:
        tetrahedra = Delaunay(points).simplices
    except QhullError:
        try:
            tetrahedra = Delaunay(points, qhull_options="QJ").simplices
        except QhullError:
            return (), False
    return tuple(sorted(omni._simplex_edges(tetrahedra))), True


def _cached_delaunay_edges(
    vertices: np.ndarray,
) -> tuple[set[tuple[int, int]], bool]:
    points = np.ascontiguousarray(vertices, dtype=np.float64)
    edges, succeeded = _cached_delaunay_edges_bytes(
        (int(points.shape[0]), int(points.shape[1])),
        points.tobytes(),
    )
    return set(edges), bool(succeeded)


def install_delaunay_topology_cache() -> None:
    """Cache the fixed reference Delaunay graph across solver iterations."""

    omni._delaunay_edges = _cached_delaunay_edges
