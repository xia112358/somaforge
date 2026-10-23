"""Sparse SciPy driver and host-side state cache for Torch trajectory problems."""
import time
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import csr_matrix


class SparseJointProblem:
    """Generic Torch Jacobian path; production uses factored sparse derivatives."""
    def __init__(self, joint, shape):
        from .torch_newton_ik import ARRAY_API
        self.joint, self.shape, self.jnp = joint, shape, ARRAY_API
        self.arguments, self.refresh_arguments, self.progress = None, None, None
        self.cached, self.evaluations = {}, 0
        self.timings = dict(value_seconds=0., jacobian_seconds=0., jacobian_evaluations=0)
        self.value = lambda flat, *args: joint(flat.reshape(shape), *args).reshape(-1)

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
        import torch
        started = time.perf_counter()
        if self.refresh_arguments is not None and (not self.cached or not np.array_equal(x, self.cached['state'])):
            self.fun(x)
        state = self.jnp.asarray(x).requires_grad_()
        matrix = torch.autograd.functional.jacobian(
            lambda flat: self.joint(flat.reshape(self.shape), *self.arguments).reshape(-1),
            state, vectorize=True).detach().cpu().numpy()
        result = csr_matrix(matrix)
        self.timings['jacobian_seconds'] += time.perf_counter()-started
        self.timings['jacobian_evaluations'] += 1
        self.timings['jacobian_nonzeros'] = result.nnz
        return result

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
