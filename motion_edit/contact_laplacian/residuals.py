from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from .kinematics import KinematicsProvider
from .schema import ContactHandleSpec, InteractionMeshSpec


@dataclass
class LeastSquaresSystem:
    rows: list[dict[int, float]] = field(default_factory=list)
    rhs: list[float] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    def add_row(self, values: dict[int, float], rhs: float, label: str, weight: float = 1.0) -> None:
        scale = float(weight) ** 0.5
        if scale <= 0.0:
            return
        self.rows.append({int(col): float(value) * scale for col, value in values.items() if float(value) != 0.0})
        self.rhs.append(float(rhs) * scale)
        self.labels.append(str(label))

    @property
    def shape(self) -> tuple[int, int]:
        max_col = -1
        for row in self.rows:
            if row:
                max_col = max(max_col, max(row))
        return len(self.rows), max_col + 1


def variable_index(frame: int, dof: int, nq: int) -> int:
    return int(frame) * int(nq) + int(dof)


def add_contact_handle_residuals(
    system: LeastSquaresSystem,
    *,
    q: np.ndarray,
    kinematics: KinematicsProvider,
    handles: Sequence[ContactHandleSpec],
    n_frames: int,
    nq: int,
) -> None:
    for handle in handles:
        handle.validate()
        frames = np.asarray(handle.frames, dtype=np.int64)
        target = np.asarray(handle.target_xyz, dtype=np.float64)
        for local_index, frame in enumerate(frames):
            if frame < 0 or frame >= n_frames:
                raise ValueError(f"{handle.anchor_id}: frame {frame} outside trajectory length {n_frames}")
            point = kinematics.fk_points(q[frame], [handle.semantic_name])[0]
            jac = kinematics.jacobian_points(q[frame], [handle.semantic_name])[0]
            residual = target[local_index] - point
            for axis in range(3):
                values = {variable_index(frame, dof, nq): jac[axis, dof] for dof in range(nq)}
                system.add_row(values, residual[axis], f"{handle.kind}:{handle.anchor_id}", float(handle.weight))


def add_q_prior_residuals(
    system: LeastSquaresSystem,
    *,
    q: np.ndarray,
    q_prior: np.ndarray,
    weight: float,
) -> None:
    if weight <= 0.0:
        return
    n_frames, nq = q.shape
    for frame in range(n_frames):
        for dof in range(nq):
            system.add_row({variable_index(frame, dof, nq): 1.0}, float(q_prior[frame, dof] - q[frame, dof]), "q_prior", weight)


def add_q_smooth_residuals(
    system: LeastSquaresSystem,
    *,
    q: np.ndarray,
    q_prior: np.ndarray,
    weight: float,
) -> None:
    if weight <= 0.0 or q.shape[0] <= 1:
        return
    n_frames, nq = q.shape
    for frame in range(1, n_frames):
        current = q[frame] - q[frame - 1]
        prior = q_prior[frame] - q_prior[frame - 1]
        rhs = prior - current
        for dof in range(nq):
            system.add_row(
                {
                    variable_index(frame, dof, nq): 1.0,
                    variable_index(frame - 1, dof, nq): -1.0,
                },
                float(rhs[dof]),
                "q_smooth",
                weight,
            )


def add_temporal_laplacian_residuals(
    system: LeastSquaresSystem,
    *,
    q: np.ndarray,
    q_prior: np.ndarray,
    weight: float,
) -> None:
    if weight <= 0.0 or q.shape[0] <= 2:
        return
    n_frames, nq = q.shape
    for frame in range(1, n_frames - 1):
        current = q[frame - 1] - 2.0 * q[frame] + q[frame + 1]
        prior = q_prior[frame - 1] - 2.0 * q_prior[frame] + q_prior[frame + 1]
        rhs = prior - current
        for dof in range(nq):
            system.add_row(
                {
                    variable_index(frame - 1, dof, nq): 1.0,
                    variable_index(frame, dof, nq): -2.0,
                    variable_index(frame + 1, dof, nq): 1.0,
                },
                float(rhs[dof]),
                "temporal_laplacian",
                weight,
            )


def add_body_relative_residuals(
    system: LeastSquaresSystem,
    *,
    q: np.ndarray,
    q_prior: np.ndarray,
    kinematics: KinematicsProvider,
    edges: Sequence[tuple[str, str]],
    weight: float,
) -> None:
    if weight <= 0.0 or not edges:
        return
    n_frames, nq = q.shape
    for frame in range(n_frames):
        for parent, child in edges:
            points = kinematics.fk_points(q[frame], [parent, child])
            prior_points = kinematics.fk_points(q_prior[frame], [parent, child])
            jac = kinematics.jacobian_points(q[frame], [parent, child])
            current_rel = points[0] - points[1]
            prior_rel = prior_points[0] - prior_points[1]
            residual = prior_rel - current_rel
            rel_jac = jac[0] - jac[1]
            for axis in range(3):
                values = {variable_index(frame, dof, nq): rel_jac[axis, dof] for dof in range(nq)}
                system.add_row(values, float(residual[axis]), "body_relative", weight)


def build_uniform_laplacian_matrix(num_vertices: int, edges: Sequence[tuple[int, int]]) -> np.ndarray:
    """Build the uniform interaction-mesh Laplacian used by Holosoma.

    Each row encodes ``v_i - mean(neighbors_i)``. This is the lightweight
    extraction of the original interaction mesh retargeter Laplacian term; it
    avoids Delaunay/tetrahedral dependencies and accepts explicit or KNN edges.
    """

    n = int(num_vertices)
    if n <= 0:
        raise ValueError("num_vertices must be positive")
    neighbors: list[set[int]] = [set() for _ in range(n)]
    for a_raw, b_raw in edges:
        a, b = int(a_raw), int(b_raw)
        if a == b:
            continue
        if a < 0 or b < 0 or a >= n or b >= n:
            raise ValueError(f"edge {(a, b)!r} outside vertex range 0..{n - 1}")
        neighbors[a].add(b)
        neighbors[b].add(a)

    laplacian = np.zeros((n, n), dtype=np.float64)
    for index, nbrs in enumerate(neighbors):
        if not nbrs:
            continue
        laplacian[index, index] = 1.0
        weight = -1.0 / float(len(nbrs))
        for neighbor in nbrs:
            laplacian[index, neighbor] = weight
    return laplacian


def build_knn_edges(vertices: np.ndarray, k: int) -> tuple[tuple[int, int], ...]:
    """Build undirected KNN edges for a small interaction mesh."""

    points = np.asarray(vertices, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"vertices must have shape [N, 3], got {points.shape}")
    n = points.shape[0]
    if n <= 1 or int(k) <= 0:
        return ()
    k_eff = min(int(k), n - 1)
    edges: set[tuple[int, int]] = set()
    for index in range(n):
        dist = np.linalg.norm(points - points[index], axis=1)
        order = np.argsort(dist)
        for neighbor in order[1 : k_eff + 1]:
            a, b = sorted((int(index), int(neighbor)))
            edges.add((a, b))
    return tuple(sorted(edges))


def add_interaction_mesh_laplacian_residuals(
    system: LeastSquaresSystem,
    *,
    q: np.ndarray,
    q_reference: np.ndarray,
    kinematics: KinematicsProvider,
    mesh: InteractionMeshSpec,
    weight: float,
) -> dict[str, Any]:
    """Add whole-trajectory interaction mesh Laplacian residuals.

    Robot vertices are linearized through FK Jacobians. Object vertices are
    fixed points and therefore contribute to the residual value but not to the
    Jacobian columns.
    """

    if weight <= 0.0:
        return {"active": False, "rows": 0}
    mesh.validate()
    q_arr = np.asarray(q, dtype=np.float64)
    q_ref = np.asarray(q_reference, dtype=np.float64)
    if q_arr.shape != q_ref.shape:
        raise ValueError(f"q_reference must have shape {q_arr.shape}, got {q_ref.shape}")
    n_frames, nq = q_arr.shape
    robot_points = tuple(str(point) for point in mesh.robot_points)
    object_points = np.asarray(mesh.object_points, dtype=np.float64)
    ref_object_points = (
        np.asarray(mesh.reference_object_points, dtype=np.float64)
        if mesh.reference_object_points is not None
        else object_points
    )
    robot_count = len(robot_points)
    object_count = object_points.shape[0]
    vertex_count = robot_count + object_count

    ref_robot_all = _reference_robot_points(mesh, q_ref, kinematics, robot_points)
    ref_vertices_first = np.vstack([ref_robot_all[0], ref_object_points])
    edges = tuple(mesh.edges) if mesh.edges else build_knn_edges(ref_vertices_first, int(mesh.knn_k))
    if not edges:
        return {"active": False, "rows": 0, "warning": "interaction mesh has no edges"}
    laplacian = build_uniform_laplacian_matrix(vertex_count, edges)

    row_count = 0
    for frame in range(n_frames):
        robot_current = kinematics.fk_points(q_arr[frame], robot_points)
        robot_jac = kinematics.jacobian_points(q_arr[frame], robot_points)
        vertices_current = np.vstack([robot_current, object_points])
        vertices_ref = np.vstack([ref_robot_all[frame], ref_object_points])
        current_lap = laplacian @ vertices_current
        target_lap = laplacian @ vertices_ref
        residual = target_lap - current_lap

        for lap_row in range(vertex_count):
            robot_coeffs = laplacian[lap_row, :robot_count]
            if not np.any(robot_coeffs):
                continue
            for axis in range(3):
                values: dict[int, float] = {}
                for robot_index, coeff in enumerate(robot_coeffs):
                    if coeff == 0.0:
                        continue
                    jac_axis = robot_jac[robot_index, axis]
                    for dof in range(nq):
                        col = variable_index(frame, dof, nq)
                        values[col] = values.get(col, 0.0) + float(coeff) * float(jac_axis[dof])
                if values:
                    system.add_row(values, float(residual[lap_row, axis]), "mesh_laplacian", weight)
                    row_count += 1

    return {
        "active": True,
        "rows": int(row_count),
        "vertex_count": int(vertex_count),
        "robot_vertex_count": int(robot_count),
        "object_vertex_count": int(object_count),
        "edge_count": int(len(edges)),
    }


def _reference_robot_points(
    mesh: InteractionMeshSpec,
    q_reference: np.ndarray,
    kinematics: KinematicsProvider,
    robot_points: Sequence[str],
) -> np.ndarray:
    if mesh.reference_robot_points is not None:
        ref = np.asarray(mesh.reference_robot_points, dtype=np.float64)
        if ref.ndim == 2:
            return np.repeat(ref[None, :, :], q_reference.shape[0], axis=0)
        return ref
    return np.asarray([kinematics.fk_points(q_reference[frame], robot_points) for frame in range(q_reference.shape[0])], dtype=np.float64)


def label_norms(labels: Sequence[str], residual: np.ndarray) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for label, value in zip(labels, np.asarray(residual, dtype=np.float64).reshape(-1)):
        grouped.setdefault(label.split(":", 1)[0], []).append(float(value))
    return {key: float(np.linalg.norm(values)) for key, values in grouped.items()}


def system_to_dense(system: LeastSquaresSystem, var_count: int) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.zeros((len(system.rows), int(var_count)), dtype=np.float64)
    for row_index, row in enumerate(system.rows):
        for col, value in row.items():
            matrix[row_index, col] = value
    return matrix, np.asarray(system.rhs, dtype=np.float64)


def system_to_sparse_or_dense(system: LeastSquaresSystem, var_count: int) -> tuple[Any, np.ndarray, bool]:
    rhs = np.asarray(system.rhs, dtype=np.float64)
    try:
        from scipy import sparse  # type: ignore

        row_indices: list[int] = []
        col_indices: list[int] = []
        values: list[float] = []
        for row_index, row in enumerate(system.rows):
            for col, value in row.items():
                row_indices.append(row_index)
                col_indices.append(col)
                values.append(value)
        matrix = sparse.coo_matrix((values, (row_indices, col_indices)), shape=(len(system.rows), int(var_count)), dtype=np.float64).tocsr()
        return matrix, rhs, True
    except Exception:
        matrix, rhs = system_to_dense(system, var_count)
        return matrix, rhs, False
