"""Whole-trajectory dual-Laplacian contact deformation solver.

The core objective is intentionally narrow:

* edited and fixed contact handles provide spatial boundary conditions;
* the temporal Laplacian propagates the deformation through time;
* semantic body-relative and interaction-mesh Laplacians propagate it through
  the robot/object spatial graph.

The q prior is only a weak gauge term that removes the global null space. The
legacy first-difference q smoothness term remains available for compatibility,
but is disabled by the default dual-Laplacian profile.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from .kinematics import KinematicsProvider
from .residuals import (
    LeastSquaresSystem,
    add_body_relative_residuals,
    add_contact_handle_residuals,
    add_interaction_mesh_laplacian_residuals,
    add_q_prior_residuals,
    add_q_smooth_residuals,
    add_temporal_laplacian_residuals,
    label_norms,
    system_to_sparse_or_dense,
)
from .schema import BatchContactLaplacianConfig, ContactHandleSpec, ContactLaplacianSolveResult, InteractionMeshSpec


_SEMANTIC_BODY_EDGE_CANDIDATES = (
    ("root", "torso"),
    ("pelvis", "torso"),
    ("root", "left_foot"),
    ("root", "right_foot"),
    ("root", "left_knee"),
    ("root", "right_knee"),
    ("pelvis", "left_foot"),
    ("pelvis", "right_foot"),
    ("pelvis", "left_knee"),
    ("pelvis", "right_knee"),
    ("left_knee", "left_foot"),
    ("right_knee", "right_foot"),
    ("torso", "left_hand"),
    ("torso", "right_hand"),
)


def solve_batch_contact_laplacian(
    q_init: np.ndarray,
    kinematics: KinematicsProvider,
    handles: list[ContactHandleSpec],
    semantic_points: list[str],
    config: BatchContactLaplacianConfig | None = None,
    *,
    q_prior: np.ndarray | None = None,
    body_edges: Sequence[tuple[str, str]] | None = None,
    interaction_mesh: InteractionMeshSpec | None = None,
) -> ContactLaplacianSolveResult:
    """Solve one global trajectory problem over ``q[0:T]``.

    For the body-position proxy provider, ``q - q_prior`` is exactly the
    semantic deformation field. The temporal residual therefore minimizes its
    second derivative, while body and mesh residuals minimize its spatial
    Laplacian. Contact handles are the only high-weight target terms.
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

    resolved_body_edges = (
        tuple((str(parent), str(child)) for parent, child in body_edges)
        if body_edges is not None
        else _default_semantic_body_edges(semantic_points)
    )

    edited_count = sum(1 for handle in handles if handle.kind == "edited_contact")
    fixed_count = sum(1 for handle in handles if handle.kind == "fixed_contact")
    force_load_count = sum(1 for handle in handles if handle.load_profile is not None)
    contact_handle_active = bool(edited_count or fixed_count)

    warnings: list[str] = []
    temporal_active = float(cfg.temporal_laplacian_weight) > 0.0
    body_spatial_active = float(cfg.body_relative_weight) > 0.0 and bool(resolved_body_edges)
    mesh_spatial_active = float(cfg.mesh_laplacian_weight) > 0.0 and interaction_mesh is not None
    if not temporal_active and contact_handle_active:
        warnings.append("temporal_laplacian_weight is zero; contact deformation can change abruptly in time")
    if float(cfg.mesh_laplacian_weight) > 0.0 and interaction_mesh is None:
        warnings.append("mesh_laplacian_weight > 0 but no interaction_mesh spec was provided; mesh residual skipped")
    if float(cfg.body_relative_weight) > 0.0 and not resolved_body_edges:
        warnings.append("body_relative_weight > 0 but no compatible semantic body edges were available; body-relative residual skipped")
    if contact_handle_active and not body_spatial_active and not mesh_spatial_active:
        warnings.append("no spatial Laplacian is active; deformation will not propagate through body/object structure")

    iteration_meta: list[dict[str, object]] = []
    mesh_meta: dict[str, object] = {"active": False, "rows": 0}
    var_count = n_frames * nq

    for iteration in range(max(0, int(cfg.num_iters))):
        system, current_mesh_meta = _build_system(
            q=q,
            prior=prior,
            kinematics=kinematics,
            handles=handles,
            body_edges=resolved_body_edges,
            interaction_mesh=interaction_mesh,
            config=cfg,
        )
        _append_mesh_warning(warnings, current_mesh_meta)
        if not system.rows:
            iteration_meta.append(
                {
                    "iteration": iteration,
                    "rows": 0,
                    "step_norm": 0.0,
                    "residual_norm": 0.0,
                    "accepted": False,
                }
            )
            break

        rhs = np.asarray(system.rhs, dtype=np.float64)
        current_cost = float(np.dot(rhs, rhs))
        matrix, rhs, is_sparse = system_to_sparse_or_dense(system, var_count)
        lhs, full_rhs = _add_damping(matrix, rhs, var_count, float(cfg.damping), is_sparse)
        solution = _solve_least_squares(lhs, full_rhs, is_sparse)
        raw_step = np.asarray(solution, dtype=np.float64).reshape(n_frames, nq)
        trust_step = _clip_trust_region(raw_step, float(cfg.trust_region))

        predicted_residual = _matrix_vector_product(matrix, trust_step.reshape(-1), is_sparse) - rhs
        accepted = False
        accepted_scale = 0.0
        accepted_step = np.zeros_like(trust_step)
        accepted_q = q
        accepted_system = system
        accepted_mesh_meta = current_mesh_meta
        accepted_cost = current_cost
        trials = 0
        max_line_search_steps = max(0, int(cfg.line_search_max_steps))
        cost_slack = max(1.0e-14, current_cost * 1.0e-12)

        for line_search_index in range(max_line_search_steps + 1):
            trials = line_search_index + 1
            scale = 0.5**line_search_index
            candidate_step = trust_step * scale
            candidate_q = q + candidate_step
            candidate_system, candidate_mesh_meta = _build_system(
                q=candidate_q,
                prior=prior,
                kinematics=kinematics,
                handles=handles,
                body_edges=resolved_body_edges,
                interaction_mesh=interaction_mesh,
                config=cfg,
            )
            candidate_rhs = np.asarray(candidate_system.rhs, dtype=np.float64)
            candidate_cost = float(np.dot(candidate_rhs, candidate_rhs))
            if candidate_cost <= current_cost + cost_slack:
                accepted = True
                accepted_scale = scale
                accepted_step = candidate_step
                accepted_q = candidate_q
                accepted_system = candidate_system
                accepted_mesh_meta = candidate_mesh_meta
                accepted_cost = candidate_cost
                break

        if not accepted:
            warnings.append(f"iteration {iteration}: line search rejected the trust-region step")

        q = accepted_q
        mesh_meta = accepted_mesh_meta
        _append_mesh_warning(warnings, mesh_meta)
        accepted_rhs = np.asarray(accepted_system.rhs, dtype=np.float64)
        step_norm = float(np.linalg.norm(accepted_step))
        relative_improvement = (current_cost - accepted_cost) / max(current_cost, 1.0e-24)
        iteration_meta.append(
            {
                "iteration": iteration,
                "rows": len(system.rows),
                "variables": int(var_count),
                "sparse": bool(is_sparse),
                "accepted": bool(accepted),
                "line_search_trials": int(trials),
                "accepted_step_scale": float(accepted_scale),
                "raw_step_norm": float(np.linalg.norm(raw_step)),
                "trust_step_norm": float(np.linalg.norm(trust_step)),
                "step_norm": step_norm,
                "max_frame_step": float(np.max(np.linalg.norm(accepted_step, axis=1))) if len(accepted_step) else 0.0,
                "objective_before": current_cost,
                "objective_after": accepted_cost,
                "relative_improvement": float(relative_improvement),
                "predicted_residual_norm": float(np.linalg.norm(predicted_residual)),
                "residual_norm": float(np.linalg.norm(accepted_rhs)),
                "residual_norms_by_label": label_norms(accepted_system.labels, accepted_rhs),
            }
        )
        if not accepted:
            break
        if step_norm < float(cfg.step_tolerance):
            break
        if relative_improvement <= float(cfg.relative_cost_tolerance):
            break

    deformation = q - prior
    frame_deformation_norm = np.linalg.norm(deformation, axis=1) if len(deformation) else np.zeros(0, dtype=np.float64)
    metadata = {
        "solver": "batch_contact_laplacian",
        "objective_profile": "dual_laplacian_contact_deformation",
        "core_residual_families": [
            "edited_contact",
            "fixed_contact",
            "temporal_laplacian",
            "body_relative",
            "mesh_laplacian",
        ],
        "trajectory_shape": [int(n_frames), int(nq)],
        "semantic_points": list(semantic_points),
        "body_edges": [list(edge) for edge in resolved_body_edges],
        "edited_handle_count": int(edited_count),
        "fixed_handle_count": int(fixed_count),
        "handle_count": int(len(handles)),
        "force_load_active": bool(force_load_count),
        "force_load_handle_count": int(force_load_count),
        "force_load_weight_mode": "contact_local_phase_profile" if force_load_count else "none",
        "force_load_interval_mapping": "same_frame_interval" if force_load_count else "none",
        "interaction_mesh": mesh_meta,
        "spatial_laplacian_active": bool(body_spatial_active or mesh_spatial_active),
        "temporal_laplacian_active": bool(temporal_active),
        "deformation_norm": float(np.linalg.norm(deformation)),
        "deformation_max_frame_norm": float(np.max(frame_deformation_norm)) if len(frame_deformation_norm) else 0.0,
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
        "line_search_max_steps": int(cfg.line_search_max_steps),
        "relative_cost_tolerance": float(cfg.relative_cost_tolerance),
        "step_tolerance": float(cfg.step_tolerance),
        "iterations": iteration_meta,
    }
    return ContactLaplacianSolveResult(q=q, metadata=metadata, warnings=warnings)


def _default_semantic_body_edges(semantic_points: Sequence[str]) -> tuple[tuple[str, str], ...]:
    available = {str(name) for name in semantic_points}
    edges: list[tuple[str, str]] = []
    for parent, child in _SEMANTIC_BODY_EDGE_CANDIDATES:
        if parent in available and child in available:
            edges.append((parent, child))
    # The Omni graph uses explicit hip/knee/ankle and
    # shoulder/elbow nodes. Legacy semantic providers expose only endpoints;
    # keep those endpoints connected without adding shortcuts to a complete
    # Omni skeleton.
    fallback_edges = (
        ("root", "left_foot"),
        ("root", "right_foot"),
        ("pelvis", "left_foot"),
        ("pelvis", "right_foot"),
        ("torso", "left_hand"),
        ("torso", "right_hand"),
    )

    def connected(start: str, goal: str) -> bool:
        adjacency: dict[str, set[str]] = {}
        for first, second in edges:
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)
        pending = [start]
        visited: set[str] = set()
        while pending:
            node = pending.pop()
            if node == goal:
                return True
            if node in visited:
                continue
            visited.add(node)
            pending.extend(adjacency.get(node, ()))
        return False

    for parent, child in fallback_edges:
        if (
            parent in available
            and child in available
            and not connected(parent, child)
        ):
            edges.append((parent, child))
    return tuple(edges)


def _build_system(
    *,
    q: np.ndarray,
    prior: np.ndarray,
    kinematics: KinematicsProvider,
    handles: Sequence[ContactHandleSpec],
    body_edges: Sequence[tuple[str, str]],
    interaction_mesh: InteractionMeshSpec | None,
    config: BatchContactLaplacianConfig,
) -> tuple[LeastSquaresSystem, dict[str, object]]:
    n_frames, nq = q.shape
    system = LeastSquaresSystem()
    add_contact_handle_residuals(
        system,
        q=q,
        kinematics=kinematics,
        handles=handles,
        n_frames=n_frames,
        nq=nq,
    )
    add_temporal_laplacian_residuals(
        system,
        q=q,
        q_prior=prior,
        weight=float(config.temporal_laplacian_weight),
    )
    add_body_relative_residuals(
        system,
        q=q,
        q_prior=prior,
        kinematics=kinematics,
        edges=body_edges,
        weight=float(config.body_relative_weight),
    )
    mesh_meta: dict[str, object] = {"active": False, "rows": 0}
    if interaction_mesh is not None and float(config.mesh_laplacian_weight) > 0.0:
        mesh_meta = add_interaction_mesh_laplacian_residuals(
            system,
            q=q,
            q_reference=prior,
            kinematics=kinematics,
            mesh=interaction_mesh,
            weight=float(config.mesh_laplacian_weight),
        )
    # Gauge/compatibility regularizers are deliberately assembled after both
    # Laplacian families so they cannot be mistaken for the algorithmic core.
    add_q_prior_residuals(system, q=q, q_prior=prior, weight=float(config.q_prior_weight))
    add_q_smooth_residuals(system, q=q, q_prior=prior, weight=float(config.q_smooth_weight))
    return system, mesh_meta


def _append_mesh_warning(warnings: list[str], mesh_meta: dict[str, object]) -> None:
    warning = mesh_meta.get("warning")
    if warning and str(warning) not in warnings:
        warnings.append(str(warning))


def _matrix_vector_product(matrix, vector: np.ndarray, is_sparse: bool) -> np.ndarray:
    value = matrix @ vector if is_sparse else matrix.dot(vector)
    return np.asarray(value, dtype=np.float64).reshape(-1)


def _add_damping(matrix, rhs: np.ndarray, var_count: int, damping: float, is_sparse: bool):
    if damping <= 0.0:
        return matrix, rhs
    scale = damping**0.5
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
