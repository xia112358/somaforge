"""OmniRetarget-compatible interaction-mesh Laplacian construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class OmniRetargetInteractionMesh:
    """Per-frame Delaunay interaction meshes and uniform Laplacians."""

    laplacian_matrices: np.ndarray
    target_laplacian: np.ndarray
    object_points_w: np.ndarray
    edge_counts: np.ndarray
    robot_vertex_count: int

    @property
    def frame_count(self) -> int:
        return int(self.laplacian_matrices.shape[0])

    @property
    def vertex_count(self) -> int:
        return int(self.laplacian_matrices.shape[1])


def build_omniretarget_interaction_mesh(
    target_robot_points_w: np.ndarray,
    object_points_w: np.ndarray,
) -> OmniRetargetInteractionMesh:
    """Match OmniRetarget's per-frame 3D Delaunay/uniform-Laplacian construction.

    Robot vertices retain the input order and are followed by the environment
    vertices. The environment sample set is fixed over the trajectory, while
    Delaunay adjacency is rebuilt from each frame's source target positions.
    """

    try:
        from scipy.spatial import Delaunay
        from scipy.spatial import QhullError
    except ImportError as exc:
        raise RuntimeError("OmniRetarget interaction meshes require scipy") from exc

    robot = np.asarray(target_robot_points_w, dtype=np.float64)
    objects = np.asarray(object_points_w, dtype=np.float64)
    if robot.ndim != 3 or robot.shape[2] != 3:
        raise ValueError(f"target_robot_points_w must be [T,R,3], got {robot.shape}")
    if objects.ndim != 2 or objects.shape[1] != 3:
        raise ValueError(f"object_points_w must be [O,3], got {objects.shape}")
    if robot.shape[1] == 0:
        raise ValueError("interaction mesh requires at least one robot vertex")
    if objects.shape[0] == 0:
        raise ValueError("OmniRetarget interaction mesh requires terrain/object sample points")
    if not np.all(np.isfinite(robot)) or not np.all(np.isfinite(objects)):
        raise ValueError("interaction mesh vertices contain NaN or Inf")

    frames, robot_count, _ = robot.shape
    vertex_count = robot_count + objects.shape[0]
    if vertex_count < 4:
        raise ValueError("3D Delaunay interaction mesh requires at least four total vertices")

    matrices = np.empty((frames, vertex_count, vertex_count), dtype=np.float64)
    coordinates = np.empty((frames, vertex_count, 3), dtype=np.float64)
    edge_counts = np.empty((frames,), dtype=np.int32)
    for frame in range(frames):
        vertices = np.vstack([robot[frame], objects])
        try:
            tetrahedra = np.asarray(Delaunay(vertices).simplices, dtype=np.int32)
        except QhullError as exc:
            raise ValueError(
                f"frame {frame}: target and terrain points do not form a valid 3D Delaunay interaction mesh"
            ) from exc
        edges = _tetrahedron_edges(tetrahedra)
        laplacian = _uniform_laplacian_matrix(vertex_count, edges)
        matrices[frame] = laplacian
        coordinates[frame] = laplacian @ vertices
        edge_counts[frame] = len(edges)

    return OmniRetargetInteractionMesh(
        laplacian_matrices=matrices,
        target_laplacian=coordinates,
        object_points_w=objects.copy(),
        edge_counts=edge_counts,
        robot_vertex_count=robot_count,
    )


def sample_terrain_mesh_points(
    mesh_path: str | Path,
    *,
    count: int = 100,
    seed: int = 0,
) -> np.ndarray:
    """Deterministically sample the terrain surface used by OmniRetarget."""

    try:
        import trimesh
    except ImportError as exc:
        raise RuntimeError("terrain interaction sampling requires trimesh") from exc

    path = Path(mesh_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if int(count) < 1:
        raise ValueError("terrain sample count must be positive")
    loaded = trimesh.load(str(path), force="scene")
    if isinstance(loaded, trimesh.Scene):
        geometries = [geometry for geometry in loaded.geometry.values() if isinstance(geometry, trimesh.Trimesh)]
        if not geometries:
            raise ValueError(f"terrain scene contains no triangle mesh: {path}")
        mesh = trimesh.util.concatenate(geometries)
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise ValueError(f"terrain asset is not a triangle mesh: {path}")
    triangles = np.asarray(mesh.triangles, dtype=np.float64)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or triangles.shape[0] == 0:
        raise ValueError(f"terrain mesh has no triangles: {path}")
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    valid = np.isfinite(areas) & (areas > 0.0)
    if not np.any(valid):
        raise ValueError(f"terrain mesh has no nondegenerate triangles: {path}")
    triangles = triangles[valid]
    probabilities = areas[valid] / np.sum(areas[valid])
    rng = np.random.default_rng(int(seed))
    triangle_index = rng.choice(triangles.shape[0], size=int(count), p=probabilities)
    selected = triangles[triangle_index]
    uv = rng.random((int(count), 2))
    root_u = np.sqrt(uv[:, 0])
    barycentric = np.stack([1.0 - root_u, root_u * (1.0 - uv[:, 1]), root_u * uv[:, 1]], axis=1)
    return np.einsum("ni,nic->nc", barycentric, selected)


def _tetrahedron_edges(tetrahedra: np.ndarray) -> tuple[tuple[int, int], ...]:
    simplices = np.asarray(tetrahedra, dtype=np.int64)
    if simplices.ndim != 2 or simplices.shape[1] != 4:
        raise ValueError(f"Delaunay tetrahedra must be [K,4], got {simplices.shape}")
    edges: set[tuple[int, int]] = set()
    for tetrahedron in simplices:
        for left in range(4):
            for right in range(left + 1, 4):
                a, b = sorted((int(tetrahedron[left]), int(tetrahedron[right])))
                edges.add((a, b))
    return tuple(sorted(edges))


def _uniform_laplacian_matrix(
    vertex_count: int,
    edges: tuple[tuple[int, int], ...],
) -> np.ndarray:
    neighbors: list[set[int]] = [set() for _ in range(int(vertex_count))]
    for left, right in edges:
        neighbors[int(left)].add(int(right))
        neighbors[int(right)].add(int(left))
    laplacian = np.zeros((int(vertex_count), int(vertex_count)), dtype=np.float64)
    for index, adjacent in enumerate(neighbors):
        if not adjacent:
            continue
        laplacian[index, index] = 1.0
        weight = -1.0 / float(len(adjacent))
        for neighbor in adjacent:
            laplacian[index, neighbor] = weight
    return laplacian
