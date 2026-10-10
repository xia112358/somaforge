"""Geometry used by the IK objective, separate from native contact activation.

Closed obstacles are queried as solids with their exact native vertices. Sphere
distances use their exact native centres/radii, independent of narrow-phase
contact normals. This private scene must never supply simulation contact labels.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np

from .native_sphere_distance import NativeSphereDistance, SPHERE_DISTANCE_SCHEMA

OPTIMIZATION_GEOMETRY_SCHEMA = 'native_model_defined_convex_and_exact_sphere_distance_v2'


@lru_cache(maxsize=32)
def _scene(resolved, mtime_ns, size, device):
    import newton
    import trimesh
    from .newton_collision import DirectNewtonCollisionScene

    scene = DirectNewtonCollisionScene(resolved, device=device)
    kinds, bodies = scene.model.shape_type.numpy(), scene.model.shape_body.numpy()
    for shape in np.flatnonzero((bodies < 0) & (kinds == int(newton.GeoType.MESH))):
        geometry = scene.model.shape_source[int(shape)]
        mesh = trimesh.Trimesh(vertices=geometry.vertices,
                              faces=np.asarray(geometry.indices).reshape(-1, 3), process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent or not mesh.is_convex:
            raise ValueError('Closed-solid IK distance requires verified closed convex terrain')
        kinds[shape] = int(newton.GeoType.CONVEX_MESH)
    scene.model.shape_type.assign(kinds)
    scene.pipeline = newton.CollisionPipeline(scene.model, max_triangle_pairs=2_500_000)
    scene.contacts = scene.pipeline.contacts()
    # Replay identical Newton kernels. The broad phase still runs at every
    # changed pose; neither candidate pairs nor contact truth are cached.
    scene.prepare_collision_graph(include_fk=True)
    scene.optimization_geometry_schema = OPTIMIZATION_GEOMETRY_SCHEMA
    return scene


def optimizer_scene(terrain_mesh, *, device='cpu'):
    """Return a private geometry scene; never mutate a cached policy scene."""
    if terrain_mesh is None:
        return _scene(None, None, None, str(device))
    path = Path(terrain_mesh).expanduser().resolve()
    stamp = path.stat()
    return _scene(str(path), stamp.st_mtime_ns, stamp.st_size, str(device))


def source_geometry_distances(scene, link_names, qpos, robot, robot_joint_names):
    """Measure source shapes from the same defined field as the edited poses.

    Keep the established source-reference scope: penetrating spheres or pairs
    already observed by the native proximity query. Distant positive gaps must
    not become new source constraints. Source poses and contact labels are read
    only; this does not change the native reference execution.
    """
    import jax
    import jax.numpy as jnp
    from scipy.spatial.transform import Rotation
    from .newton_collision import G1_29DOF_JOINT_ORDER
    from .convex_geometry_distance import ConvexGeometryDistance
    from .pyroki_taskspace import world_body_poses_from_pyroki_fk
    from .pyroki_fullbody_ik import _robot_min_geometry_distance_by_body_surface

    geometry = NativeSphereDistance(scene, link_names)
    convex = ConvexGeometryDistance(scene, link_names)
    indices = [tuple(G1_29DOF_JOINT_ORDER).index(name) for name in robot_joint_names]
    cfg = np.asarray(qpos, dtype=float)[:, 7:][:, indices]
    fk = np.asarray(jax.jit(jax.vmap(robot.forward_kinematics))(jnp.asarray(cfg)))
    positions, quaternions = world_body_poses_from_pyroki_fk(np.asarray(qpos)[:, :7], fk)
    rotations = Rotation.from_quat(np.asarray(quaternions)[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(
        len(qpos), len(link_names), 3, 3)
    frames = []
    for i, pose in enumerate(qpos):
        contacts = convex.refine(scene.query_qpos(pose), positions[i], rotations[i])
        frames.append(_robot_min_geometry_distance_by_body_surface(contacts))
    records = geometry.query(positions, rotations)
    sphere_names = set(geometry.names)
    for frame, extra in zip(frames, records):
        observed = set(frame)
        for key in list(frame):
            if key[0] in sphere_names:
                del frame[key]
        for body, face, gap, *_ in extra:
            if gap <= 0. or (body, face) in observed:
                frame[(body, face)] = min(frame.get((body, face), np.inf), gap)
    return frames
