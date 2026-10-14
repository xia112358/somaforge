"""Defined signed-distance witnesses on the actual native convex shapes.

This is optimizer geometry only. It does not determine simulation contact
activation, force, allocation, labels or margins. The native scene supplies
the candidate pairs and physical shape parameters; double precision GJK/EPA
supplies a scalar and witnesses consistent with its pose derivative.
"""
from dataclasses import replace

import numpy as np
from scipy.spatial.transform import Rotation


CONVEX_DISTANCE_SCHEMA = 'native_model_f64_gjk_epa_witnesses_v1'


class ConvexGeometryDistance:
    def __init__(self, scene, link_names):
        import coal
        import newton

        self.coal, self.kinds_enum = coal, newton.GeoType
        self.scene, self.model = scene, scene.model
        self.links = {name: i for i, name in enumerate(link_names)}
        model = self.model
        self.kinds, self.bodies = model.shape_type.numpy(), model.shape_body.numpy()
        self.scales = np.asarray(model.shape_scale.numpy(), dtype=float)
        self.local = np.asarray(model.shape_transform.numpy(), dtype=float)
        self.local_rotations = Rotation.from_quat(self.local[:, 3:]).as_matrix()
        self.geometries = {}
        self.request = coal.DistanceRequest()
        self.request.enable_signed_distance = True
        self.request.gjk_tolerance = self.request.epa_tolerance = 1.e-12
        self.backend = f'coal_{coal.__version__}_geometry_only'

    def geometry(self, shape):
        if shape in self.geometries:
            return self.geometries[shape]
        coal, kinds = self.coal, self.kinds_enum
        kind, scale = self.kinds[shape], self.scales[shape]
        if kind in (int(kinds.MESH), int(kinds.CONVEX_MESH)):
            import trimesh

            source = self.model.shape_source[shape]
            vertices = np.asarray(source.vertices, dtype=float)*scale
            faces = np.asarray(source.indices).reshape(-1, 3)
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
            if not mesh.is_convex or not mesh.is_watertight or not mesh.is_winding_consistent:
                raise ValueError(f'Native optimizer shape {shape} is not a verified convex solid')
            points, triangles = coal.StdVec_Vec3s(), coal.StdVec_Triangle()
            for point in vertices:
                points.append(point)
            for face in faces:
                triangles.append(coal.Triangle(*map(int, face)))
            result = coal.Convex(points, triangles)
        elif kind == int(kinds.SPHERE):
            result = coal.Sphere(float(scale[0]))
        elif kind == int(kinds.CYLINDER):
            if scale[2] != 0.:
                raise ValueError('Native barrel cylinder needs its actual curved geometry')
            result = coal.Cylinder(float(scale[0]), 2.*float(scale[1]))
        elif kind == int(kinds.CAPSULE):
            result = coal.Capsule(float(scale[0]), 2.*float(scale[1]))
        elif kind == int(kinds.BOX):
            result = coal.Box(2.*scale)
        elif kind == int(kinds.ELLIPSOID):
            result = coal.Ellipsoid(scale)
        elif kind == int(kinds.PLANE):
            if np.any(scale[:2] != 0.):
                raise ValueError('Finite native plane needs its bounded geometry')
            result = coal.Halfspace(np.array([0., 0., 1.]), 0.)
        else:
            raise ValueError(f'Unsupported actual native shape type {kind} at shape {shape}')
        self.geometries[shape] = result
        return result

    def transform(self, shape, positions, rotations):
        rotation, position = self.local_rotations[shape], self.local[shape, :3]
        if self.bodies[shape] >= 0:
            body = self.links[self.scene.body_names[int(self.bodies[shape])]]
            position = positions[body]+rotations[body] @ position
            rotation = rotations[body] @ rotation
        return self.coal.Transform3s(rotation, position)

    def refine(self, contacts, positions, rotations):
        """Return geometry witnesses; retain original native candidate arrays.

        Inputs are the optimizer's exact FK poses, not a quantized physics
        state. Raw native contacts are immutable and remain available for audit.
        The result must never be used as simulation contact truth.
        """
        first, second, normals, distance = (np.array(value, copy=True) for value in
            (contacts.point0_w, contacts.point1_w, contacts.normal_a_to_b_w,
             contacts.geometry_distance_m))
        # A native manifold can contain several records for the same shapes.
        # The full-shape distance is identical for those records at this pose.
        # These caches are local: a changed pose must always be queried again.
        transforms, pairs = {}, {}
        for index in range(len(distance)):
            a, b = int(contacts.shape0[index]), int(contacts.shape1[index])
            if (a, b) not in pairs:
                for shape in (a, b):
                    if shape not in transforms:
                        transforms[shape] = self.transform(shape, positions, rotations)
                result = self.coal.DistanceResult()
                gap = self.coal.distance(self.geometry(a), transforms[a],
                    self.geometry(b), transforms[b], self.request, result)
                pairs[(a, b)] = (gap, result.getNearestPoint1(), result.getNearestPoint2(), result.normal)
            distance[index], first[index], second[index], normals[index] = pairs[(a, b)]
        # Validate the same witnesses together, avoiding thousands of scalar
        # NumPy calls over one trajectory. This does not alter any query result.
        valid = (np.isfinite(distance) & np.isfinite(normals).all(axis=1)
            & np.isfinite(first).all(axis=1) & np.isfinite(second).all(axis=1)
            & np.isclose(np.linalg.norm(normals, axis=1), 1., atol=1.e-10, rtol=1.e-10))
        if not valid.all():
            index = int(np.flatnonzero(~valid)[0])
            pair = int(contacts.shape0[index]), int(contacts.shape1[index])
            raise RuntimeError(f'Undefined convex geometry at native shape pair {pair}')
        indices = contacts.robot_body_indices
        first_robot = contacts.body0[indices] >= 0
        return replace(contacts, point0_w=first, point1_w=second,
            normal_a_to_b_w=normals, geometry_distance_m=distance,
            robot_points_w=np.where(first_robot[:, None], first[indices], second[indices]),
            terrain_points_w=np.where(first_robot[:, None], second[indices], first[indices]),
            outward_normals_w=normals[indices]*np.where(first_robot, -1., 1.)[:, None])
