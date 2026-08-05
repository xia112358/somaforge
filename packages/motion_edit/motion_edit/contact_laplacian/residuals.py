from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from motion_edit.contact.dynamics import contact_local_phase

from .kinematics import KinematicsProvider
from .omniretarget_mesh import build_omniretarget_interaction_mesh
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
        strengths = _compiled_contact_strengths(handle, len(frames))
        for local_index, frame in enumerate(frames):
            if frame < 0 or frame >= n_frames:
                raise ValueError(f"{handle.anchor_id}: frame {frame} outside trajectory length {n_frames}")
            effective_weight = float(handle.weight) * float(strengths[local_index])
            point = kinematics.fk_points(q[frame], [handle.semantic_name])[0]
            jac = kinematics.jacobian_points(q[frame], [handle.semantic_name])[0]
            residual = target[local_index] - point
            for axis in range(3):
                values = {variable_index(frame, dof, nq): jac[axis, dof] for dof in range(nq)}
                system.add_row(values, residual[axis], f"{handle.kind}:{handle.anchor_id}", effective_weight)


def _compiled_contact_strengths(handle: ContactHandleSpec, frame_count: int) -> np.ndarray:
    if handle.load_profile is None:
        return np.ones(int(frame_count), dtype=np.float64)
    phase = contact_local_phase(int(frame_count))
    strength = np.asarray(handle.load_profile.evaluate(phase), dtype=np.float64)
    if strength.shape != (int(frame_count),):
        raise ValueError(f"{handle.anchor_id}: compiled load strength shape mismatch")
    if not np.all(np.isfinite(strength)) or np.any(strength < 0.0):
        raise ValueError(f"{handle.anchor_id}: compiled load strength must be finite and nonnegative")
    return strength


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
    """Penalize the temporal Laplacian of the deformation ``q - q_prior``."""

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
    """Preserve the spatial Laplacian over the semantic body graph.

    The family weight is distributed across edges so adding another semantic
    edge changes graph resolution, not the total spatial stiffness.
    """

    if weight <= 0.0 or not edges:
        return
    n_frames, nq = q.shape
    edge_weight = float(weight) / float(len(edges))
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
                system.add_row(values, float(residual[axis]), "body_relative", edge_weight)


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
        neighbor_weight = -1.0 / float(len(nbrs))
        for neighbor in nbrs:
            laplacian[index, neighbor] = neighbor_weight
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
    prepared_mesh: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add whole-trajectory interaction-mesh Laplacian residuals.

    Robot vertices are linearized through FK Jacobians. Object vertices are
    fixed points and therefore contribute to the residual value but not to the
    Jacobian columns. The family weight is averaged over active Laplacian
    vertices, so different surface polygon resolutions remain comparable.
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

    prepared = prepared_mesh or prepare_interaction_mesh_laplacian(
        mesh=mesh,
        q_reference=q_ref,
        kinematics=kinematics,
    )
    warning = prepared.get("warning")
    if warning:
        return {"active": False, "rows": 0, "warning": str(warning)}
    ref_robot_all = np.asarray(prepared["reference_robot_points"], dtype=np.float64)
    laplacians = np.asarray(prepared["laplacian_matrices"], dtype=np.float64)
    edge_counts = np.asarray(prepared["edge_counts"], dtype=np.int32)

    row_count = 0
    active_counts: list[int] = []
    per_vertex_weights: list[float] = []
    for frame in range(n_frames):
        laplacian = laplacians[frame]
        active_lap_rows = tuple(
            row for row in range(vertex_count) if np.any(laplacian[row, :robot_count])
        )
        if not active_lap_rows:
            continue
        laplacian_row_weight = float(weight) / float(len(active_lap_rows))
        active_counts.append(len(active_lap_rows))
        per_vertex_weights.append(laplacian_row_weight)
        robot_current = kinematics.fk_points(q_arr[frame], robot_points)
        robot_jac = kinematics.jacobian_points(q_arr[frame], robot_points)
        vertices_current = np.vstack([robot_current, object_points])
        vertices_ref = np.vstack([ref_robot_all[frame], ref_object_points])
        current_lap = laplacian @ vertices_current
        target_lap = laplacian @ vertices_ref
        residual = target_lap - current_lap

        for lap_row in active_lap_rows:
            robot_coeffs = laplacian[lap_row, :robot_count]
            for axis in range(3):
                values: dict[int, float] = {}
                for robot_index, coeff in enumerate(robot_coeffs):
                    if coeff == 0.0:
                        continue
                    jac_axis = robot_jac[robot_index, axis]
                    for dof in range(nq):
                        contribution = float(coeff) * float(jac_axis[dof])
                        if contribution == 0.0:
                            continue
                        col = variable_index(frame, dof, nq)
                        values[col] = values.get(col, 0.0) + contribution
                if values:
                    system.add_row(values, float(residual[lap_row, axis]), "mesh_laplacian", laplacian_row_weight)
                    row_count += 1

    if not active_counts:
        return {"active": False, "rows": 0, "warning": "interaction mesh has no robot-coupled Laplacian rows"}
    return {
        "active": True,
        "rows": int(row_count),
        "vertex_count": int(vertex_count),
        "robot_vertex_count": int(robot_count),
        "object_vertex_count": int(object_count),
        "topology": mesh.topology,
        "edge_count": int(np.max(edge_counts)),
        "edge_count_min": int(np.min(edge_counts)),
        "edge_count_max": int(np.max(edge_counts)),
        "active_laplacian_vertex_count": int(np.max(active_counts)),
        "active_laplacian_vertex_count_min": int(np.min(active_counts)),
        "active_laplacian_vertex_count_max": int(np.max(active_counts)),
        "family_weight": float(weight),
        "per_vertex_weight": float(np.min(per_vertex_weights)),
        "per_vertex_weight_min": float(np.min(per_vertex_weights)),
        "per_vertex_weight_max": float(np.max(per_vertex_weights)),
        "normalization": "mean_over_robot_coupled_laplacian_vertices",
        "topology_precomputed": prepared_mesh is not None,
        "topology_cache_hit": bool(prepared.get("cache_hit", False)),
        "topology_cache_path": prepared.get("cache_path"),
    }


def prepare_interaction_mesh_laplacian(
    *,
    mesh: InteractionMeshSpec,
    q_reference: np.ndarray,
    kinematics: KinematicsProvider,
) -> dict[str, Any]:
    """Build the reference topology once for all nonlinear/line-search evaluations."""

    mesh.validate()
    q_ref = np.asarray(q_reference, dtype=np.float64)
    if q_ref.ndim != 2:
        raise ValueError(f"q_reference must be [T,nq], got {q_ref.shape}")
    robot_points = tuple(str(point) for point in mesh.robot_points)
    object_points = np.asarray(mesh.object_points, dtype=np.float64)
    ref_object_points = (
        np.asarray(mesh.reference_object_points, dtype=np.float64)
        if mesh.reference_object_points is not None
        else object_points
    )
    ref_robot_all = _reference_robot_points(mesh, q_ref, kinematics, robot_points)
    n_frames = q_ref.shape[0]
    vertex_count = len(robot_points) + object_points.shape[0]
    cache_path = _interaction_topology_cache_path()
    cache_key = _interaction_topology_cache_key(
        mesh=mesh,
        q_reference=q_ref,
        robot_points=robot_points,
        object_points=object_points,
        reference_robot_points=ref_robot_all,
        reference_object_points=ref_object_points,
    )
    cached = _load_interaction_topology_cache(
        cache_path,
        expected_key=cache_key,
        expected_frames=n_frames,
        expected_vertices=vertex_count,
    )
    if cached is not None:
        return cached
    if mesh.topology == "omniretarget_delaunay":
        aligned_mesh = build_omniretarget_interaction_mesh(ref_robot_all, ref_object_points)
        laplacians = aligned_mesh.laplacian_matrices
        edge_counts = aligned_mesh.edge_counts
    else:
        ref_vertices_first = np.vstack([ref_robot_all[0], ref_object_points])
        edges = tuple(mesh.edges) if mesh.edges else build_knn_edges(ref_vertices_first, int(mesh.knn_k))
        if not edges:
            return {"warning": "interaction mesh has no edges"}
        laplacian = build_uniform_laplacian_matrix(vertex_count, edges)
        laplacians = np.broadcast_to(laplacian[None], (n_frames, vertex_count, vertex_count))
        edge_counts = np.full((n_frames,), len(edges), dtype=np.int32)
    result = {
        "reference_robot_points": ref_robot_all,
        "laplacian_matrices": laplacians,
        "edge_counts": edge_counts,
        "cache_hit": False,
        "cache_path": str(cache_path) if cache_path is not None else None,
    }
    _write_interaction_topology_cache(cache_path, cache_key=cache_key, prepared=result)
    return result


def _interaction_topology_cache_path() -> Path | None:
    raw = os.environ.get("SOMAFORGE_LAPLACIAN_TOPOLOGY_CACHE")
    return Path(raw).expanduser().resolve() if raw else None


def _interaction_topology_cache_key(
    *,
    mesh: InteractionMeshSpec,
    q_reference: np.ndarray,
    robot_points: Sequence[str],
    object_points: np.ndarray,
    reference_robot_points: np.ndarray,
    reference_object_points: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"somaforge_laplacian_topology_v2\0")
    digest.update(str(mesh.topology).encode("utf-8"))
    for name in robot_points:
        digest.update(b"\0")
        digest.update(str(name).encode("utf-8"))
    for value in (
        q_reference,
        reference_robot_points,
        reference_object_points,
    ):
        array = np.ascontiguousarray(value)
        digest.update(str(array.shape).encode("ascii"))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(memoryview(array).cast("B"))
    return digest.hexdigest()


def _load_interaction_topology_cache(
    path: Path | None,
    *,
    expected_key: str,
    expected_frames: int,
    expected_vertices: int,
) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as data:
        cached_key = str(np.asarray(data["cache_key"]).item())
        if cached_key != expected_key:
            raise ValueError(
                "Laplacian topology cache belongs to a different source reference: "
                f"{path}"
            )
        reference_robot_points = np.asarray(data["reference_robot_points"], dtype=np.float64)
        laplacian_matrices = np.asarray(data["laplacian_matrices"], dtype=np.float64)
        edge_counts = np.asarray(data["edge_counts"], dtype=np.int32)
        failed_frames = (
            np.asarray(data["delaunay_failed_frames"], dtype=np.int32).tolist()
            if "delaunay_failed_frames" in data.files
            else []
        )
    if laplacian_matrices.shape != (
        int(expected_frames),
        int(expected_vertices),
        int(expected_vertices),
    ):
        raise ValueError(
            "Laplacian topology cache has an invalid matrix shape: "
            f"{laplacian_matrices.shape}"
        )
    return {
        "reference_robot_points": reference_robot_points,
        "laplacian_matrices": laplacian_matrices,
        "edge_counts": edge_counts,
        "cache_hit": True,
        "cache_path": str(path),
        "delaunay_failed_frames": failed_frames,
    }


def _write_interaction_topology_cache(
    path: Path | None,
    *,
    cache_key: str,
    prepared: dict[str, Any],
) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp.npz")
    payload = {
        "cache_key": np.asarray(cache_key),
        "reference_robot_points": np.asarray(
            prepared["reference_robot_points"], dtype=np.float64
        ),
        "laplacian_matrices": np.asarray(
            prepared["laplacian_matrices"], dtype=np.float64
        ),
        "edge_counts": np.asarray(prepared["edge_counts"], dtype=np.int32),
    }
    if "delaunay_failed_frames" in prepared:
        payload["delaunay_failed_frames"] = np.asarray(
            prepared["delaunay_failed_frames"], dtype=np.int32
        )
    np.savez(temporary, **payload)
    temporary.replace(path)


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
