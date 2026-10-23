"""Exact host-side sparse assembly for temporal and material phase coupling."""
import time
import numpy as np
from scipy.sparse import coo_matrix


class FactoredJointProblem:
    """Assembly shared by the Torch derivative provider; no FK or AD backend."""
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
