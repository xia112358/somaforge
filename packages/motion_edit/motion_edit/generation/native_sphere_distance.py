"""Sphere-to-native-terrain geometry for optimization, never contact labels.

The signed distance uses complete closed convex terrain triangles and actual
sphere centres/radii. It does not depend on a solver contact candidate or its
normal, which can be zero in the generic convex narrow phase. Witnesses and
pose gradients describe this same geometric value; physics activation, margins,
forces and effective contact selection remain the native solver's responsibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

SPHERE_DISTANCE_SCHEMA = 'native_convex_sphere_geometry_v1'


@dataclass(frozen=True)
class ConvexTerrain:
    triangles: np.ndarray
    normals: np.ndarray

    @classmethod
    def from_mesh(cls, vertices, indices):
        import trimesh
        mesh = trimesh.Trimesh(vertices=np.asarray(vertices, dtype=np.float64),
                               faces=np.asarray(indices).reshape(-1, 3), process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent or not mesh.is_convex:
            raise ValueError('Optimizer sphere distance requires closed convex terrain geometry')
        triangles = np.asarray(mesh.triangles, dtype=np.float64)
        normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
        length = np.linalg.norm(normals, axis=-1)
        if np.any(length == 0.):
            raise ValueError('Degenerate terrain triangle')
        normals /= length[:, None]
        if mesh.volume <= 0.:
            raise ValueError('Terrain triangle winding must point outward')
        return cls(triangles, normals)

    def query(self, centers):
        """Return signed point distance, its unit gradient and surface witness."""
        points = np.asarray(centers, dtype=np.float64)
        shape = points.shape[:-1]
        p = points.reshape(-1, 3)[:, None]
        a, b, c = (self.triangles[None, :, i] for i in range(3))
        normals = self.normals[None]
        plane_distance = np.sum((p-a)*normals, axis=-1)
        projection = p-plane_distance[..., None]*normals
        ab, ac = b-a, c-a
        dot00, dot01, dot11 = np.sum(ab*ab, -1), np.sum(ab*ac, -1), np.sum(ac*ac, -1)
        dot02, dot12 = np.sum((projection-a)*ab, -1), np.sum((projection-a)*ac, -1)
        determinant = dot00*dot11-dot01**2
        u, v = ((dot11*dot02-dot01*dot12)/determinant,
                (dot00*dot12-dot01*dot02)/determinant)
        inside_triangle = (u >= 0.) & (v >= 0.) & (u+v <= 1.)
        starts = self.triangles[None]
        edges = np.roll(starts, -1, axis=2)-starts
        offset = p[:, :, None]-starts
        fraction = np.clip(np.sum(offset*edges, -1)/np.sum(edges*edges, -1), 0., 1.)
        on_edges = starts+fraction[..., None]*edges
        edge_distance = np.sum((p[:, :, None]-on_edges)**2, -1)
        edge = edge_distance.argmin(axis=-1)
        closest = np.take_along_axis(on_edges, edge[..., None, None], axis=2)[..., 0, :]
        closest = np.where(inside_triangle[..., None], projection, closest)
        squared = np.sum((p-closest)**2, axis=-1)
        triangle = squared.argmin(axis=-1)
        rows = np.arange(len(p))
        outside_witness = closest[rows, triangle]
        outside_distance = np.sqrt(squared[rows, triangle])
        face = plane_distance.argmax(axis=-1)
        inside_distance = plane_distance[rows, face]
        inside = inside_distance <= 0.
        signed = np.where(inside, inside_distance, outside_distance)
        inward_face_gradient = self.normals[face]
        outside_gradient = np.divide(points.reshape(-1, 3)-outside_witness,
            outside_distance[:, None], out=np.zeros_like(outside_witness),
            where=outside_distance[:, None] > 0.)
        gradient = np.where(inside[:, None], inward_face_gradient, outside_gradient)
        witness = np.where(inside[:, None], points.reshape(-1, 3)-inside_distance[:, None]*gradient,
                           outside_witness)
        return signed.reshape(shape), gradient.reshape(*shape, 3), witness.reshape(*shape, 3)


class NativeSphereDistance:
    """Compile physical native spheres, terrain and collision filters once."""

    def __init__(self, scene, link_names):
        import newton
        from scipy.spatial.transform import Rotation
        from newton._src.geometry.broad_phase_common import test_world_and_group_pair
        model = scene.model
        kinds, bodies, flags = (getattr(model, name).numpy() for name in
                                ('shape_type', 'shape_body', 'shape_flags'))
        scales, transforms = model.shape_scale.numpy(), model.shape_transform.numpy()
        worlds, groups = model.shape_world.numpy(), model.shape_collision_group.numpy()
        colliding = (flags & int(newton.ShapeFlags.COLLIDE_SHAPES)) != 0
        sphere = np.flatnonzero(colliding & (bodies >= 0) & (kinds == int(newton.GeoType.SPHERE)))
        self.shape_ids = sphere
        self.sphere_shape_ids = set(map(int, sphere))
        self.names = tuple(scene.body_names[int(bodies[s])] for s in sphere)
        self.link_indices = np.asarray([tuple(link_names).index(name) for name in self.names])
        self.centers_local = transforms[sphere, :3].astype(np.float64)
        self.radii = scales[sphere, 0].astype(np.float64)
        if np.any(self.radii <= 0.):
            raise ValueError('Physical sphere radius must be positive')
        excluded = {tuple(sorted(map(int, pair))) for pair in model.shape_collision_filter_pairs}
        self.terrain = []
        for s in np.flatnonzero(colliding & (bodies < 0)):
            label = scene.shape_labels[int(s)]
            rotation = Rotation.from_quat(transforms[s, 3:])
            if kinds[s] in (int(newton.GeoType.MESH), int(newton.GeoType.CONVEX_MESH)):
                source = model.shape_source[int(s)]
                vertices = rotation.apply(np.asarray(source.vertices, dtype=np.float64)*scales[s])+transforms[s, :3]
                geometry = ConvexTerrain.from_mesh(vertices, source.indices)
            elif kinds[s] == int(newton.GeoType.PLANE):
                if np.any(scales[s, :2] != 0.):
                    raise ValueError('Finite terrain planes need their full surface geometry')
                geometry = (transforms[s, :3].astype(np.float64), rotation.apply([0., 0., 1.]))
            else:
                raise ValueError(f'Unsupported native static geometry type {kinds[s]} at shape {s}')
            allowed = np.asarray([bool(test_world_and_group_pair(int(worlds[robot]), int(worlds[s]),
                int(groups[robot]), int(groups[s]))) and tuple(sorted((int(robot), int(s)))) not in excluded
                for robot in sphere])
            self.terrain.append((int(s), label, geometry, allowed))

    def query(self, positions, rotations):
        positions, rotations = np.asarray(positions), np.asarray(rotations)
        centers = positions[:, self.link_indices]+np.einsum('tsij,sj->tsi',
            rotations[:, self.link_indices], self.centers_local)
        results = [[] for _ in range(len(positions))]
        for shape, label, geometry, allowed in self.terrain:
            if isinstance(geometry, ConvexTerrain):
                point_gap, normal, target = geometry.query(centers)
            else:
                origin, outward = geometry
                point_gap = np.sum((centers-origin)*outward, axis=-1)
                normal = np.broadcast_to(outward, centers.shape)
                target = centers-point_gap[..., None]*normal
            gap = point_gap-self.radii
            robot_point = centers-self.radii[None, :, None]*normal
            for frame in range(len(positions)):
                records = []
                for sphere in np.flatnonzero(allowed):
                    outward = normal[frame, sphere]
                    face = ('ground' if 'ground' in label.lower() else
                            ('top' if outward[2] > np.sqrt(.5) else
                             ('bottom' if outward[2] < -np.sqrt(.5) else 'side')))
                    records.append((self.names[sphere], f'{label}:{face}', float(gap[frame, sphere]),
                                    robot_point[frame, sphere], target[frame, sphere], outward))
                results[frame].extend(records)
        return results
