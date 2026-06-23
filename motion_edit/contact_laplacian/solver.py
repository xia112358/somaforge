from __future__ import annotations

from typing import Sequence

import numpy as np

from .kinematics import KinematicsProvider
from .residuals import (
    LeastSquaresSystem,
    add_body_relative_residuals,
    add_contact_handle_residuals,
    add_q_prior_residuals,
    add_q_smooth_residuals,
    add_temporal_laplacian_residuals,
    label_norms,
    system_to_sparse_or_dense,
)
from .schema import BatchContactLaplacianConfig, ContactHandleSpec, ContactLaplacianSolveResult


def solve_batch_contact_laplacian(
    q_init: np.ndarray,
    kinematics: KinematicsProvider,
    handles: list[ContactHandleSpec],
    semantic_points: list[str],
    config: BatchContactLaplacianConfig | None = None,
    *,
    q_prior: np.ndarray | None = None,
    body_edges: Sequence[tuple[str, str]] | None = None,
) -> ContactLaplacianSolveResult:
    """Solve a full-trajectory contact-Laplacian least-squares problem.

    The optimization variable is the entire trajectory ``dq [T, nq]``. Spatial
    contact terms are block-diagonal by frame, while q smoothness and temporal
    Laplacian terms couple adjacent frames in the same global system.
    """

    cfg = config or BatchContactLaplacianConfig()
    q = np.asarray(q_init, dtype=np.float64).copy()
    if q.ndim != 2:
        raise ValueError(f"q_init must have shape [T, nq], got {q.shape}")
    n_frames, nq = q.shape
    if nq != int(kinematics.nq):
        raise ValueError(f"q_init has nq={nq}, but kinematics provider has nq={kinematics.nq}")
    prior = np.asarray(q_prior if q_prior is not None else q_init, dtype=np.float64)
    if prior.shape != q.shape:
        raise ValueError(f"q_prior must have shape {q.shape}, got {prior.shape}")
    for handle in handles:
        handle.validate()

    warnings: list[str] = []
    if float(cfg.mesh_laplacian_weight) > 0.0:
        warnings.append("mesh_laplacian residual is not active yet; missing object/terrain mesh adapter")

    edited_count = sum(1 for handle in handles if handle.kind == "edited_contact")
    fixed_count = sum(1 for handle in handles if handle.kind == "fixed_contact")
    iteration_meta: list[dict[str, object]] = []
    var_count = n_frames * nq

    for iteration in range(max(0, int(cfg.num_iters))):
        system = LeastSquaresSystem()
        add_contact_handle_residuals(
            system,
            q=q,
            kinematics=kinematics,
            handles=handles,
            n_frames=n_frames,
            nq=nq,
        )
        add_q_prior_residuals(system, q=q, q_prior=prior, weight=float(cfg.q_prior_weight))
        add_q_smooth_residuals(system, q=q, q_prior=prior, weight=float(cfg.q_smooth_weight))
        add_temporal_laplacian_residuals(system, q=q, q_prior=prior, weight=float(cfg.temporal_laplacian_weight))
        add_body_relative_residuals(
            system,
            q=q,
            q_prior=prior,
            kinematics=kinematics,
            edges=body_edges or (),
            weight=float(cfg.body_relative_weight),
        )
        if not system.rows:
            iteration_meta.append({"iteration": iteration, "rows": 0, "step_norm": 0.0, "residual_norm": 0.0})
            break
        matrix, rhs, is_sparse = system_to_sparse_or_dense(system, var_count)
        lhs, full_rhs = _add_damping(matrix, rhs, var_count, float(cfg.damping), is_sparse)
        solution = _solve_least_squares(lhs, full_rhs, is_sparse)
        raw_step = np.asarray(solution, dtype=np.float64).reshape(n_frames, nq)
        step = _clip_trust_region(raw_step, float(cfg.trust_region))
        q += step
        predicted = matrix @ solution if is_sparse else matrix.dot(solution)
        residual = predicted - rhs
        iteration_meta.append(
            {
                "iteration": iteration,
                "rows": len(system.rows),
                "variables": int(var_count),
                "sparse": bool(is_sparse),
                "raw_step_norm": float(np.linalg.norm(raw_step)),
                "step_norm": float(np.linalg.norm(step)),
                "max_frame_step": float(np.max(np.linalg.norm(step, axis=1))) if len(step) else 0.0,
                "residual_norm": float(np.linalg.norm(residual)),
                "residual_norms_by_label": label_norms(system.labels, residual),
            }
        )
        if float(np.linalg.norm(step)) < 1.0e-10:
            break

    metadata = {
        "solver": "batch_contact_laplacian",
        "trajectory_shape": [int(n_frames), int(nq)],
        "semantic_points": list(semantic_points),
        "edited_handle_count": int(edited_count),
        "fixed_handle_count": int(fixed_count),
        "handle_count": int(len(handles)),
        "weights": {
            "edit_contact_weight": float(cfg.edit_contact_weight),
            "fixed_contact_weight": float(cfg.fixed_contact_weight),
            "temporal_laplacian_weight": float(cfg.temporal_laplacian_weight),
            "body_relative_weight": float(cfg.body_relative_weight),
            "q_prior_weight": float(cfg.q_prior_weight),
            "q_smooth_weight": float(cfg.q_smooth_weight),
            "mesh_laplacian_weight": float(cfg.mesh_laplacian_weight),
        },
        "damping": float(cfg.damping),
        "trust_region": float(cfg.trust_region),
        "iterations": iteration_meta,
    }
    return ContactLaplacianSolveResult(q=q, metadata=metadata, warnings=warnings)


def _add_damping(matrix, rhs: np.ndarray, var_count: int, damping: float, is_sparse: bool):
    if damping <= 0.0:
        return matrix, rhs
    scale = damping ** 0.5
    if is_sparse:
        from scipy import sparse  # type: ignore

        damp = sparse.eye(var_count, format="csr", dtype=np.float64) * scale
        return sparse.vstack([matrix, damp], format="csr"), np.concatenate([rhs, np.zeros(var_count, dtype=np.float64)])
    damp = np.eye(var_count, dtype=np.float64) * scale
    return np.vstack([matrix, damp]), np.concatenate([rhs, np.zeros(var_count, dtype=np.float64)])


def _solve_least_squares(matrix, rhs: np.ndarray, is_sparse: bool) -> np.ndarray:
    if is_sparse:
        try:
            from scipy.sparse import linalg as splinalg  # type: ignore

            return np.asarray(splinalg.lsqr(matrix, rhs, atol=1.0e-10, btol=1.0e-10)[0], dtype=np.float64)
        except Exception:
            matrix = matrix.toarray()
    return np.linalg.lstsq(np.asarray(matrix, dtype=np.float64), np.asarray(rhs, dtype=np.float64), rcond=None)[0]


def _clip_trust_region(step: np.ndarray, trust_region: float) -> np.ndarray:
    if trust_region <= 0.0:
        return step
    clipped = np.asarray(step, dtype=np.float64).copy()
    norms = np.linalg.norm(clipped, axis=1)
    for frame, norm in enumerate(norms):
        if norm > trust_region:
            clipped[frame] *= trust_region / (norm + 1.0e-12)
    return clipped
