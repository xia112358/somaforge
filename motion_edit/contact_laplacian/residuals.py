from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from .kinematics import KinematicsProvider
from .schema import ContactHandleSpec


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
