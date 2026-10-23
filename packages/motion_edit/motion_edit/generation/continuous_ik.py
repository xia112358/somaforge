"""Joint trajectory least squares using the existing per-frame IK residuals.

History poses are variables, not frozen previous answers. Native collision
linearizations are supplied by the caller and refreshed between joint solves.
The objective, original material sites, weights and bounds remain authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


SOLVER_SCHEMA = 'joint_trajectory_constrained_shared_fk_live_geometry_v3'


@dataclass
class ContinuousResult:
    states: np.ndarray
    residuals: np.ndarray
    solves: list[dict]








def solve_joint_trajectory(joint, rows, initial, lower, upper, *, max_nfev=25,
                           refinements=4, refresh=None, progress=None, problem_class=None):
    """Solve all poses together, re-querying nonlinear collision geometry."""
    from .continuous_sparse_ik import SparseJointProblem

    if refresh is not None:
        from .continuous_constrained_ik import solve_constrained_trajectory
        from .torch_newton_ik import TorchFactoredJointProblem
        return solve_constrained_trajectory(joint, rows, initial, lower, upper, refresh,
            max_nfev=max_nfev*(refinements+1), progress=progress,
            problem_class=problem_class or TorchFactoredJointProblem)

    states = np.asarray(initial).copy()
    solves = []
    problem = (problem_class or SparseJointProblem)(joint, states.shape)
    def refresh_arguments(value):
        return joint.stack(refresh(value, rows))
    for iteration in range(refinements+1):
        if refresh is not None:
            rows = refresh(states, rows)
        arguments = joint.stack(rows)
        problem.set_arguments(arguments, progress=(None if progress is None else
            lambda row, state: progress(dict(iteration=iteration, kind='evaluation', **row), state)),
            refresh=refresh_arguments if refresh is not None else None)
        result = problem.solve(states, lower, upper, max_nfev=max_nfev)
        states = result.x.reshape(states.shape)
        row = dict(iteration=iteration, cost=float(result.cost),
            optimality=float(result.optimality), nfev=int(result.nfev),
            success=bool(result.success), status=int(result.status),
            linearization='exact_sparse_blocks_and_material_phase_prefix',
            solver_profile=result.solver_profile)
        solves.append(row)
        if progress is not None:
            progress(dict(kind='solve_finished', **row), states)
        if result.success:
            break
    return ContinuousResult(states, result.fun, solves)


class NativeCollisionRows:
    """Refresh the original Newton geometry residuals for every trajectory pose."""

    witness_arguments = (
        'collision_link_indices', 'collision_points_local', 'collision_normals_base',
        'collision_terrain_points_base', 'collision_similarity_weight', 'collision_deeper_weight',
        'self_collision_link_a', 'self_collision_point_a_local', 'self_collision_link_b',
        'self_collision_point_b_local', 'self_collision_normals_base', 'self_collision_sqrt_weight')

    def __init__(self, joint, scene, link_names, source_signed, active_weights,
                 *, depth_weight, self_weight, sphere_geometry=None,
                 constraint_multipliers=None, collect_linearizations=False,
                 convex_geometry=None):
        self.joint, self.scene = joint, scene
        self.links = {name: i for i, name in enumerate(link_names)}
        self.source_signed, self.active_weights = source_signed, active_weights
        self.depth_weight, self.self_weight = depth_weight, self_weight
        self.sphere_geometry = sphere_geometry
        self.convex_geometry = convex_geometry
        self.constraint_multipliers = constraint_multipliers
        self.constraint_values = {}
        self.collect_linearizations = collect_linearizations
        self.constraint_linearizations = ()
        self.audits = []

    def stacked_arguments(self, states, rows, arguments):
        """Refresh every pose, replacing only the live witness argument buffers.

        Authored targets and source material sites are fixed throughout this
        solve. Preserve their existing device arrays instead of stacking and
        uploading them again at each trial. No pose, pair or witness is cached.
        """
        updated = self(states, rows)
        return tuple(np.stack([row[index] for row in updated])
            if name in self.witness_arguments else arguments[index]
            for index, name in enumerate(self.joint.names))

    def __call__(self, states, rows):
        from scipy.spatial.transform import Rotation
        from .trajectory_problem import (
            _terrain_surface_key, _surface_class, _contact_part_for_body_name,
            _is_contact_reference_body, _environment_deeper_weight_for_body)

        root = np.asarray(self.joint.root).copy()
        rotations = np.asarray(self.joint.rotations)
        root[:, :3] += np.einsum('tij,tj->ti', rotations, states[:, :3])
        if self.joint.root_dofs == 4:
            yaw = Rotation.from_rotvec(np.column_stack((np.zeros((len(states), 2)), states[:, 3])))
            root[:, 3:7] = (yaw*Rotation.from_matrix(rotations)).as_quat()[:, [3, 0, 1, 2]]
        fk = np.asarray(self.joint.poses(self.joint.jnp.asarray(states)))
        positions = np.asarray(self.joint.root)[:, None, :3]+np.einsum(
            'tij,tnj->tni', rotations, fk[..., 4:7]+states[:, None, :3])
        body_rotations = rotations[:, None] @ Rotation.from_quat(
            fk[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(*fk.shape[:2], 3, 3)
        spheres = (None if self.sphere_geometry is None else
                   self.sphere_geometry.query(positions, body_rotations))
        result = []
        constraints = {}
        linearizations = []
        audit = dict(terrain_max_m=0., terrain_excess_max_m=0., self_max_m=0.,
                     terrain_frames=0, self_frames=0, terrain_peak=None,
                     terrain_excess_peak=None, self_pairs=[], geometry_distance_known=True)

        def require_defined_normal(normal, frame, bodies, shape_pair):
            if np.all(np.isfinite(normal)) and np.linalg.norm(normal) > 0.:
                return
            audit['geometry_distance_known'] = False
            audit['undefined_geometry_witness'] = dict(frame=frame, bodies=bodies,
                shape_pair=list(map(int, shape_pair)))
            self.audits.append(audit)
            raise RuntimeError(f'Undefined optimizer geometry normal at frame {frame}, '
                               f'bodies {bodies}, shapes {tuple(shape_pair)}; '
                               'zero witness projection is not a known signed distance')
        for frame, original in enumerate(rows):
            # Targets and source material sites are immutable across queries.
            # Only native witness buffers need replacement for this pose.
            args = dict(zip(self.joint.names, original))
            for name in self.witness_arguments:
                args[name] = np.zeros_like(args[name])
            contacts = self.scene.query_qpos(np.r_[root[frame], states[frame, self.joint.root_dofs:]])
            if self.convex_geometry is not None:
                contacts = self.convex_geometry.refine(contacts, positions[frame], body_rotations[frame])
                audit['optimizer_distance_backend'] = self.convex_geometry.backend
            terrain = {}
            for local, index in enumerate(contacts.robot_body_indices):
                if self.sphere_geometry is not None and (
                        int(contacts.shape0[index]) in self.sphere_geometry.sphere_shape_ids or
                        int(contacts.shape1[index]) in self.sphere_geometry.sphere_shape_ids):
                    continue
                body = str(contacts.robot_body_names[local])
                require_defined_normal(contacts.normal_a_to_b_w[index], frame, [body],
                    (contacts.shape0[index], contacts.shape1[index]))
                face = _terrain_surface_key(contacts, local_index=local, contact_index=int(index))
                signed = float(contacts.geometry_distance_m[index])
                key = body, face
                if key not in terrain or signed < terrain[key][2]:
                    terrain[key] = (body, face, signed, contacts.robot_points_w[local],
                                    contacts.terrain_points_w[local], contacts.outward_normals_w[local])
            if spheres is not None:
                for record in spheres[frame]:
                    key = record[:2]
                    if key not in terrain or record[2] < terrain[key][2]:
                        terrain[key] = record
            terrain_depth = max((max(0., -item[2]) for item in terrain.values()), default=0.)
            audit['terrain_max_m'] = max(audit['terrain_max_m'], terrain_depth)
            audit['terrain_frames'] += int(terrain_depth > 0)
            slot = 0
            for (body, face), (_, _, signed, robot_point, terrain_point, outward) in terrain.items():
                if body not in self.links:
                    continue
                part, face_class = _contact_part_for_body_name(body), _surface_class(face)
                reference = self.source_signed[frame].get((body, face))
                active = ((part, face_class) in self.active_weights[frame]
                    and reference is not None and part is not None
                    and _is_contact_reference_body(body, part))
                # Positive demonstration clearance is a pose reference, not a
                # penetration allowance. Do not prohibit approaching a face.
                floor = min(float(reference), 0.) if active else 0.
                key = ('terrain', frame, body, face.rsplit(':', 1)[0])
                penalty = _environment_deeper_weight_for_body(
                    body, self.depth_weight, is_active_contact=active)
                multiplier = (0. if self.constraint_multipliers is None else
                              self.constraint_multipliers.get(key, 0.))
                shift = multiplier / penalty
                if key not in constraints or signed-floor < constraints[key][0]:
                    constraints[key] = (signed-floor, penalty)
                depth = max(0., -signed)
                excess = max(0., floor-signed)
                peak = dict(frame=frame, body=body, surface=face, signed_distance_m=signed,
                            source_signed_distance_m=reference, source_relative=active,
                            excess_penetration_m=excess)
                if audit['terrain_peak'] is None or depth > -audit['terrain_peak']['signed_distance_m']:
                    audit['terrain_peak'] = peak
                if excess > audit['terrain_excess_max_m']:
                    audit['terrain_excess_max_m'] = excess
                    audit['terrain_excess_peak'] = peak
                link = self.links[body]
                point = body_rotations[frame, link].T @ (robot_point-positions[frame, link])
                normal = rotations[frame].T @ outward
                if self.collect_linearizations:
                    # The signed constraint exists on both sides of the
                    # boundary. A zero hinge cost must not erase its Jacobian.
                    linearizations.append((key, frame, link, point, -1,
                        np.zeros(3), normal, signed-floor))
                if not active and signed >= shift:
                    continue
                if slot >= len(args['collision_link_indices']):
                    raise ValueError('Native collision rows exceed explicit capacity')
                target = rotations[frame].T @ (terrain_point-np.asarray(self.joint.root)[frame, :3])
                # The multiplier changes the augmented-Lagrangian residual;
                # geometry witnesses and the physical penetration audit stay
                # unchanged. Zero multipliers reproduce the original penalty.
                target += (floor+shift)*normal
                args['collision_link_indices'][slot] = link
                args['collision_points_local'][slot] = point
                args['collision_normals_base'][slot] = normal
                args['collision_terrain_points_base'][slot] = target
                args['collision_deeper_weight'][slot] = np.sqrt(penalty)
                slot += 1
            pairs = {}
            for index in np.flatnonzero((contacts.body0 >= 0) & (contacts.body1 >= 0)
                                        & (contacts.body0 != contacts.body1)):
                # Bodies are indexed by the native scene, never by contact slot.
                a = self.scene.body_names[int(contacts.body0[index])]
                b = self.scene.body_names[int(contacts.body1[index])]
                a, b = str(a), str(b)
                if a not in self.links or b not in self.links:
                    continue
                require_defined_normal(contacts.normal_a_to_b_w[index], frame, [a, b],
                    (contacts.shape0[index], contacts.shape1[index]))
                signed = float(contacts.geometry_distance_m[index])
                key = tuple(sorted((a, b)))
                if key not in pairs or signed < pairs[key][3]:
                    pairs[key] = (int(index), a, b, signed)
            for pair, item in pairs.items():
                constraints[('self', frame, *pair)] = (item[3], self.self_weight)
                if self.collect_linearizations:
                    index, a, b, signed = item
                    link_a, link_b = self.links[a], self.links[b]
                    point_a = body_rotations[frame, link_a].T @ (contacts.point0_w[index]-positions[frame, link_a])
                    point_b = body_rotations[frame, link_b].T @ (contacts.point1_w[index]-positions[frame, link_b])
                    normal = -rotations[frame].T @ contacts.normal_a_to_b_w[index]
                    linearizations.append((('self', frame, *pair), frame,
                        link_a, point_a, link_b, point_b, normal, signed))
            penetrating = {key for key, item in pairs.items() if item[3] < 0.}
            pairs = {key: item for key, item in pairs.items()
                     if item[3] < 0. or (self.constraint_multipliers is not None
                     and self.constraint_multipliers.get(('self', frame, *key), 0.) > 0.)}
            self_depth = max((max(0., -item[3]) for item in pairs.values()), default=0.)
            audit['self_pairs'] = sorted(set(map(tuple, audit['self_pairs'])) | penetrating)
            audit['self_max_m'] = max(audit['self_max_m'], self_depth)
            audit['self_frames'] += int(self_depth > 0)
            for slot, (index, a, b, signed) in enumerate(sorted(pairs.values(), key=lambda item: item[3])):
                if slot >= len(args['self_collision_link_a']):
                    raise ValueError('Native self-collision rows exceed explicit capacity')
                link_a, link_b = self.links[a], self.links[b]
                args['self_collision_link_a'][slot] = link_a
                args['self_collision_link_b'][slot] = link_b
                args['self_collision_point_a_local'][slot] = body_rotations[frame, link_a].T @ (contacts.point0_w[index]-positions[frame, link_a])
                args['self_collision_point_b_local'][slot] = body_rotations[frame, link_b].T @ (contacts.point1_w[index]-positions[frame, link_b])
                multiplier = (0. if self.constraint_multipliers is None else
                    self.constraint_multipliers.get(('self', frame, *tuple(sorted((a, b)))), 0.))
                # A displacement parallel to n introduces no extra first-order
                # rotational derivative: n dot (omega cross n) is zero.
                if multiplier:
                    args['self_collision_point_b_local'][slot] -= (
                        multiplier/self.self_weight *
                        (body_rotations[frame, link_b].T @ contacts.normal_a_to_b_w[index]))
                args['self_collision_normals_base'][slot] = rotations[frame].T @ contacts.normal_a_to_b_w[index]
                args['self_collision_sqrt_weight'][slot] = np.sqrt(self.self_weight)
            result.append(tuple(args[name] for name in self.joint.names))
        self.constraint_values = constraints
        self.constraint_linearizations = tuple(linearizations)
        self.audits.append(audit)
        return result
