"""Sparse derivatives of the unchanged coupled trajectory IK objective.

Frame tasks are block diagonal, temporal terms join adjacent poses, and loaded
material budgets have their exact phase-prefix derivatives. Computing those
blocks once avoids repeating full-trajectory autodiff inside each LSMR product.
"""
import numpy as np
import time
from scipy.optimize import least_squares
from scipy.sparse import coo_matrix


class SparseJointProblem:
    def __init__(self, joint, shape):
        import jax
        import jax.numpy as jnp

        self.joint, self.shape = joint, shape
        self.jax, self.jnp = jax, jnp
        self.arguments = None
        self.refresh_arguments = None
        self.progress = None
        self.cached = {}
        self.evaluations = 0
        self.timings = dict(value_seconds=0., jacobian_seconds=0., jacobian_evaluations=0)
        self.value = jax.jit(lambda x, *args: joint(x.reshape(shape), *args).reshape(-1))
        def dynamic(x, *arguments):
            args = joint.dynamic_arguments(x.reshape(shape), *arguments)
            return tuple(args[name] for name in joint.names)

        self.dynamic = jax.jit(dynamic)

        def frame(state, previous, previous_previous, *arguments):
            args = dict(zip(joint.names, arguments))
            args['q_previous'] = previous[joint.root_dofs:]
            args['q_previous_previous'] = previous_previous[joint.root_dofs:]
            args['root_delta_previous'] = previous[:joint.root_dofs]
            args['root_delta_previous_previous'] = previous_previous[:joint.root_dofs]
            if 'loaded_scale' in args:
                args['loaded_scale'] = jnp.zeros_like(args['loaded_scale'])
            return joint.residual(state, *(args[name] for name in joint.names))

        # Separate sweeps let JAX discard FK from the history derivatives.
        # A combined sweep propagates mostly-zero directions through FK.
        derivatives = tuple(jax.jacfwd(frame, argnums=i) for i in range(3))
        def local(state, previous, previous_previous, *arguments):
            return tuple(derivative(state, previous, previous_previous, *arguments)
                         for derivative in derivatives)
        self.local = jax.jit(jax.vmap(local))
        if joint.loaded is not None:
            index = joint.names.index('loaded_remaining')+1
            self.remaining = jax.jit(jax.vmap(jax.jacfwd(joint.residual, argnums=index)))

            def pose(state, rotation):
                fk = joint.robot.forward_kinematics(state[joint.root_dofs:])
                if joint.root_dofs == 4:
                    half = state[3]*.5
                    yaw = jnp.concatenate((jnp.cos(half)[None], rotation[2]*jnp.sin(half)))
                    q = fk[:, :4]
                    w = yaw[:1]*q[:, :1]-jnp.sum(yaw[1:]*q[:, 1:], -1, keepdims=True)
                    xyz = yaw[:1]*q[:, 1:]+q[:, :1]*yaw[1:]+jnp.cross(yaw[1:], q[:, 1:])
                    fk = jnp.concatenate((w, xyz, joint.apply(yaw, fk[:, 4:7])), -1)
                return fk

            def material(current, previous, links, local, normals, weights,
                         root, rotation, previous_root, previous_rotation):
                from somaforge_core.loaded_material_motion import tangent_material_rms
                now = pose(current, rotation)[links]
                before = pose(previous, previous_rotation)[links]
                now_point = now[..., 4:7]+joint.apply(now[..., :4], local)+current[:3]
                before_point = before[..., 4:7]+joint.apply(before[..., :4], local)+previous[:3]
                before_world = previous_root[:3]+jnp.einsum('ij,pnj->pni', previous_rotation, before_point)
                before_base = jnp.einsum('ji,pnj->pni', rotation, before_world-root[:3])
                return tangent_material_rms(now_point-before_base, normals, weights, xp=jnp)

            self.material = jax.jit(jax.vmap(material))
            self.material_jac = jax.jit(jax.vmap(jax.jacfwd(material, argnums=(0, 1))))

    def set_arguments(self, arguments, progress=None, refresh=None):
        self.arguments = tuple(self.jnp.asarray(a) for a in arguments)
        self.progress = progress
        self.refresh_arguments = refresh
        self.cached = {}
        self.evaluations = 0
        self.timings = dict(value_seconds=0., jacobian_seconds=0., jacobian_evaluations=0)

    def fun(self, x):
        if self.cached and np.array_equal(x, self.cached['state']):
            return self.cached['value']
        started = time.perf_counter()
        if self.refresh_arguments is not None:
            self.arguments = tuple(self.jnp.asarray(a) for a in self.refresh_arguments(x.reshape(self.shape)))
        refreshed = time.perf_counter()
        self.timings['native_refresh_seconds'] = self.timings.get('native_refresh_seconds', 0.)+refreshed-started
        value = np.asarray(self.value(self.jnp.asarray(x), *self.arguments))
        self.timings['value_seconds'] += time.perf_counter()-refreshed
        self.cached.update(state=np.array(x, copy=True), value=value)
        self.evaluations += 1
        if self.progress is not None and (self.evaluations == 1 or self.evaluations % 5 == 0):
            self.progress(dict(evaluation=self.evaluations, cost=float(.5*np.dot(value, value))),
                          x.reshape(self.shape))
        return value

    def jac(self, x):
        started = time.perf_counter()
        if self.refresh_arguments is not None and (
                not self.cached or not np.array_equal(x, self.cached['state'])):
            self.fun(x)
        states = self.jnp.asarray(x).reshape(self.shape)
        previous = self.jnp.concatenate((states[:1], states[:-1]), 0)
        previous_previous = self.jnp.concatenate((states[:1], previous[:-1]), 0)
        dynamic = self.dynamic(self.jnp.asarray(x), *self.arguments)
        self.jax.block_until_ready(dynamic)
        dynamic_finished = time.perf_counter()
        blocks = tuple(np.asarray(block) for block in self.local(states, previous, previous_previous, *dynamic))
        local_finished = time.perf_counter()
        n, dimension = self.shape
        residual_count = blocks[0].shape[1]
        values, row_indices, column_indices = [], [], []
        for lag, block in enumerate(blocks):
            t, row, column = np.nonzero(block)
            values.append(block[t, row, column])
            row_indices.append(t*residual_count+row)
            column_indices.append(np.maximum(t-lag, 0)*dimension+column)

        if self.joint.loaded is not None:
            args = dict(zip(self.joint.names, dynamic))
            rms_args = (states[1:], states[:-1], args['loaded_links'][1:],
                args['loaded_local'][1:], args['loaded_normals'][1:], args['loaded_weights'][1:],
                self.joint.root[1:], self.joint.rotations[1:], self.joint.root[:-1], self.joint.rotations[:-1])
            rms = np.asarray(self.material(*rms_args))
            current_jac, previous_jac = map(np.asarray, self.material_jac(*rms_args))
            remaining_jac = np.asarray(self.remaining(states, *dynamic))
            difference = rms-np.asarray(args['loaded_source_step'][1:])
            # Match JAX maximum's symmetric derivative at exact equality.
            extra_derivative = np.where(difference > 0., 1., np.where(difference < 0., 0., .5))
            for phase in self.joint.loaded.reference['phases']:
                a, b, part = (int(phase[k]) for k in ('start', 'end', 'part'))
                path_prefix = np.zeros((b-a+1, dimension))
                extra_prefix = np.zeros_like(path_prefix)
                for step in range(a, b):
                    local = step-a
                    path_prefix[local] += previous_jac[step, part]
                    path_prefix[local+1] += current_jac[step, part]
                    factor = extra_derivative[step, part]
                    extra_prefix[local] += factor*previous_jac[step, part]
                    extra_prefix[local+1] += factor*current_jac[step, part]
                    for kind, prefix in ((0, extra_prefix), (1, path_prefix)):
                        for row in np.flatnonzero(remaining_jac[step+1, :, kind, part]):
                            pose, column = np.nonzero(prefix)
                            weight = -remaining_jac[step+1, row, kind, part]
                            values.append(weight*prefix[pose, column])
                            row_indices.append(np.full(len(pose), (step+1)*residual_count+row, int))
                            column_indices.append((pose+a)*dimension+column)
        matrix = coo_matrix((np.concatenate(values),
            (np.concatenate(row_indices), np.concatenate(column_indices))),
            shape=(n*residual_count, n*dimension)).tocsr()
        matrix.eliminate_zeros()
        for key, seconds in (
                ('dynamic_arguments_seconds', dynamic_finished-started),
                ('local_jacobian_seconds', local_finished-dynamic_finished),
                ('sparse_assembly_and_material_seconds', time.perf_counter()-local_finished)):
            self.timings[key] = self.timings.get(key, 0.)+seconds
        self.timings['jacobian_seconds'] += time.perf_counter()-started
        self.timings['jacobian_evaluations'] += 1
        self.timings['jacobian_nonzeros'] = matrix.nnz
        return matrix

    def solve(self, initial, lower, upper, *, max_nfev=25):
        started = time.perf_counter()
        result = least_squares(self.fun, np.asarray(initial).reshape(-1), jac=self.jac,
            bounds=(np.broadcast_to(lower, self.shape).reshape(-1),
                    np.broadcast_to(upper, self.shape).reshape(-1)),
            max_nfev=max_nfev, tr_solver='lsmr', x_scale='jac',
            tr_options=dict(maxiter=150, atol=1.e-5, btol=1.e-5),
            xtol=None, ftol=None, gtol=1.e-5)
        result.solver_profile = dict(self.timings, total_seconds=time.perf_counter()-started)
        return result
