"""Exact trajectory derivatives sharing FK and using analytic temporal blocks.

This optional solver preserves the production residual, including phase-prefix
material budgets. A pose and its derivatives are evaluated once per frame, then
reused by frame tasks and both adjacent material intervals. Historical linear
terms and hinge derivatives never build full residual-by-state dense blocks.
"""
from __future__ import annotations

import time
import numpy as np
from scipy.sparse import coo_matrix

from .continuous_sparse_ik import SparseJointProblem


class FactoredJointProblem(SparseJointProblem):
    def __init__(self, joint, shape, *, dtype=np.float64):
        if not hasattr(joint.residual, 'continuous_temporal_weights'):
            raise ValueError('Factored IK requires the explicit production residual layout')
        if shape[1] != joint.root_dofs + joint.robot.joints.num_actuated_joints:
            raise ValueError('Factored IK supports pose variables without convex target variables')
        super().__init__(joint, shape)
        self.dtype = np.dtype(dtype)
        if self.dtype not in (np.dtype('float32'), np.dtype('float64')):
            raise ValueError('IK precision must be float32 or float64')
        jax, jnp = self.jax, self.jnp
        names, dimension, rd = joint.names, shape[1], joint.root_dofs
        self.weights = joint.residual.continuous_temporal_weights
        self.identity = jnp.eye(dimension, dtype=self.dtype)
        self.root = jnp.asarray(joint.root, dtype=self.dtype)
        self.rotations = jnp.asarray(joint.rotations, dtype=self.dtype)
        # A separate robot tree keeps precision experiments isolated.
        robot = jax.tree.map(lambda a: a.astype(self.dtype) if hasattr(a, 'dtype')
                             and np.issubdtype(a.dtype, np.floating) else a, joint.robot)

        def pose(state, rotation):
            fk = robot.forward_kinematics(state[rd:])
            if rd == 4:
                half = state[3]*.5
                yaw = jnp.concatenate((jnp.cos(half)[None], rotation[2]*jnp.sin(half)))
                q = fk[:, :4]
                w = yaw[:1]*q[:, :1]-jnp.sum(yaw[1:]*q[:, 1:], -1, keepdims=True)
                xyz = yaw[:1]*q[:, 1:]+q[:, :1]*yaw[1:]+jnp.cross(yaw[1:], q[:, 1:])
                fk = jnp.concatenate((w, xyz, joint.apply(yaw, fk[:, 4:7])), -1)
            return fk

        def pose_aux(state, rotation):
            value = pose(state, rotation)
            return value, value

        pose_derivative = jax.vmap(jax.jacfwd(pose_aux, argnums=0, has_aux=True))
        self.pose_derivatives = jax.jit(pose_derivative)

        def frame(state, fk, fk_jac, *arguments):
            args = dict(zip(names, arguments))
            if 'loaded_scale' in args:
                args['loaded_scale'] = jnp.zeros_like(args['loaded_scale'])
            ordered = tuple(args[name] for name in names)
            _, linear = jax.linearize(
                lambda s, p: joint.residual(s, *ordered, fk_override=p), state, fk)
            # The FK derivative is shared rather than propagated through FK again.
            return jax.vmap(linear)(self.identity, jnp.moveaxis(fk_jac, -1, 0)).T

        def material(state, previous, fk, before, links, local, normals, weights,
                     root, rotation, previous_root, previous_rotation):
            from somaforge_core.loaded_material_motion import tangent_material_rms
            now, old = fk[links], before[links]
            current = now[..., 4:7]+joint.apply(now[..., :4], local)+state[:3]
            prior = old[..., 4:7]+joint.apply(old[..., :4], local)+previous[:3]
            prior_world = previous_root[:3]+jnp.einsum('ij,pnj->pni', previous_rotation, prior)
            prior_base = jnp.einsum('ji,pnj->pni', rotation, prior_world-root[:3])
            return tangent_material_rms(current-prior_base, normals, weights, xp=jnp)

        def material_derivative(state, previous, fk, before, fk_jac, before_jac, *args):
            rms, linear = jax.linearize(lambda s, p, f, b: material(s, p, f, b, *args),
                                        state, previous, fk, before)
            zero_state, zero_pose = jnp.zeros_like(state), jnp.zeros_like(fk)
            current = jax.vmap(lambda ds, df: linear(ds, zero_state, df, zero_pose))(
                self.identity, jnp.moveaxis(fk_jac, -1, 0)).T
            previous_jac = jax.vmap(lambda ds, df: linear(zero_state, ds, zero_pose, df))(
                self.identity, jnp.moveaxis(before_jac, -1, 0)).T
            return rms, current, previous_jac

        def geometry(states, *arguments):
            fk_jac, fk = pose_derivative(states, self.rotations)
            dynamic = joint.dynamic_arguments(states, *arguments, poses_override=fk)
            ordered = tuple(dynamic[name] for name in names)
            blocks = jax.vmap(frame)(states, fk, fk_jac, *ordered)
            if joint.loaded is None:
                return blocks, (), ()
            a = dynamic
            material_data = jax.vmap(material_derivative)(
                states[1:], states[:-1], fk[1:], fk[:-1], fk_jac[1:], fk_jac[:-1],
                a['loaded_links'][1:], a['loaded_local'][1:], a['loaded_normals'][1:],
                a['loaded_weights'][1:], self.root[1:], self.rotations[1:],
                self.root[:-1], self.rotations[:-1])
            return blocks, material_data, (a['loaded_remaining'], a['loaded_scale'])

        self.geometry = jax.jit(geometry)

    def set_arguments(self, arguments, progress=None, refresh=None):
        converted = tuple(np.asarray(a, dtype=self.dtype) if np.issubdtype(np.asarray(a).dtype, np.floating)
                          else a for a in arguments)
        super().set_arguments(converted, progress, refresh)

    def jac(self, x):
        started = time.perf_counter()
        if self.refresh_arguments is not None and (
                not self.cached or not np.array_equal(x, self.cached['state'])):
            self.fun(x)
        n, dimension = self.shape
        rd, nq = self.joint.root_dofs, dimension-self.joint.root_dofs
        blocks, material, budget = self.geometry(
            self.jnp.asarray(x, dtype=self.dtype).reshape(self.shape), *self.arguments)
        blocks = np.asarray(blocks)
        material = tuple(np.asarray(a) for a in material)
        budget = tuple(np.asarray(a) for a in budget)
        geometry_finished = time.perf_counter()
        count = blocks.shape[1]
        # Geometry can have changed during a rejected trial. Use the arguments
        # refreshed for this exact state, including their current activity masks.
        args = {name: np.asarray(value) for name, value in
                zip(self.joint.names, self.arguments)}
        safety_size = (args['collision_deeper_weight'].shape[1]
                       + args['self_collision_sqrt_weight'].shape[1]
                       + args['release_weights'].shape[1])
        loaded_size = 12 if self.joint.loaded is not None else args['loaded_scale'].shape[1]*args['loaded_scale'].shape[2]
        temporal_start = count-safety_size-loaded_size-2*dimension
        if temporal_start < 0:
            raise ValueError('Production temporal residual layout changed')
        loaded_start = count-safety_size-loaded_size
        t, row, col = np.nonzero(blocks)
        values, rows, columns = [blocks[t, row, col]], [t*count+row], [t*dimension+col]

        def append(v, r, c):
            values.append(np.asarray(v).reshape(-1))
            rows.append(np.asarray(r, dtype=np.int64).reshape(-1))
            columns.append(np.asarray(c, dtype=np.int64).reshape(-1))

        # Exact linear history derivatives; frame zero/one masks remain intact.
        history = np.asarray(args['history_mask'])
        for offset, variable_offset, width, weight, mask, lag, factor in (
            (0, rd, nq, self.weights[0], 0, 1, -1.),
            (nq, rd, nq, self.weights[1], 1, 1, -2.),
            (nq, rd, nq, self.weights[1], 1, 2, 1.),
            (2*nq, 0, rd, 10., 0, 1, -1.),
            (2*nq+rd, 0, rd, 20., 1, 1, -2.),
            (2*nq+rd, 0, rd, 20., 1, 2, 1.)):
            times = np.flatnonzero(history[:, mask]*weight != 0)
            pose = np.maximum(times-lag, 0)
            component = np.arange(width)
            append(np.broadcast_to((factor*weight*history[times, mask])[:, None], (len(times), width)),
                   times[:, None]*count+temporal_start+offset+component,
                   pose[:, None]*dimension+variable_offset+component)

        if self.joint.loaded is not None:
            rms, current, previous = material
            remaining, scale = budget
            source = np.asarray(args['loaded_source_step'])[1:]
            difference = rms-source
            maximum_derivative = lambda v: np.where(v > 0, 1., np.where(v < 0, 0., .5))
            extra_factor = maximum_derivative(difference)
            delta = np.maximum(difference, 0)
            hinge = np.stack((delta-remaining[1:, 0], rms-remaining[1:, 1]), axis=1)
            hinge_factor = maximum_derivative(hinge)*scale[1:]
            # Current interval contributions touch precisely its two endpoint poses.
            for kind in range(2):
                coefficient = hinge_factor[:, kind]*(extra_factor if kind == 0 else 1.)
                for lag, block in ((0, current), (1, previous)):
                    step, part, column = np.nonzero(block*coefficient[..., None])
                    append((block*coefficient[..., None])[step, part, column],
                           (step+1)*count+loaded_start+kind*6+part,
                           (step+1-lag)*dimension+column)
            # Exact phase prefix derivatives. Build each phase's cumulative matrix
            # once, then gather active rows, instead of repeatedly scanning prefixes.
            for phase in self.joint.loaded.reference['phases']:
                a, b, p = (int(phase[k]) for k in ('start', 'end', 'part'))
                length = b-a
                for kind in range(2):
                    factors = extra_factor[a:b, p] if kind == 0 else np.ones(length)
                    increments = np.zeros((length, length+1, dimension), dtype=self.dtype)
                    steps = np.arange(length)
                    increments[steps, steps] = previous[a:b, p]*factors[:, None]
                    increments[steps, steps+1] = current[a:b, p]*factors[:, None]
                    prefix = np.cumsum(increments, axis=0)
                    # residual at step s uses all prior intervals, excluding s.
                    active = np.flatnonzero(hinge_factor[a:b, kind, p])
                    active = active[active > 0]
                    if len(active):
                        block = prefix[active-1]*hinge_factor[a+active, kind, p, None, None]
                        row_index, pose, column = np.nonzero(block)
                        append(block[row_index, pose, column],
                               (a+active[row_index]+1)*count+loaded_start+kind*6+p,
                               (a+pose)*dimension+column)

        matrix = coo_matrix((np.concatenate(values), (np.concatenate(rows), np.concatenate(columns))),
                            shape=(n*count, n*dimension)).tocsr()
        matrix.eliminate_zeros()
        finished = time.perf_counter()
        for key, seconds in (('shared_geometry_seconds', geometry_finished-started),
                             ('sparse_assembly_seconds', finished-geometry_finished)):
            self.timings[key] = self.timings.get(key, 0.)+seconds
        self.timings['jacobian_seconds'] += finished-started
        self.timings['jacobian_evaluations'] += 1
        self.timings['jacobian_nonzeros'] = matrix.nnz
        self.timings['precision'] = self.dtype.name
        return matrix
