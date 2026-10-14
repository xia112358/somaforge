"""Geometry inequalities cannot be exchanged for a lower total pose cost."""
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csc_matrix, csr_matrix

pytest.importorskip('clarabel')

from motion_edit.generation.continuous_constrained_ik import (
    quadratic_schur, solve_constrained_trajectory, factor_metric)


def quadratic(hessian, gradient, geometry, required, lower, upper):
    gradient = np.asarray(gradient, float)
    return quadratic_schur(csc_matrix(hessian), gradient, csr_matrix(geometry),
        np.asarray(required, float), np.broadcast_to(lower, gradient.shape),
        np.broadcast_to(upper, gradient.shape),
        np.full(len(required), 1.e-9), np.full(len(gradient), 1.e-9))


def test_geometry_and_joint_bound_coordinate_the_coupled_step():
    # Free minimizer (-1, 2) violates x>=0 and y<=1. Both must hold;
    # satisfying x is not allowed to compensate for breaking y.
    hessian = np.array([[2., -1.], [-1., 2.]])
    gradient = -hessian @ [-1., 2.]
    answer = quadratic(hessian, gradient, [[1., 0.]], [0.], [-3., -3.], [3., 1.])
    np.testing.assert_allclose(answer.x, [0., 1.], atol=1.e-9)


def test_redundant_constraints_at_small_dual_value_remain_feasible():
    # An absolute dual objective tolerance must not erase a tiny boundary.
    answer = quadratic(np.eye(2), [-1.e-8, 0.], [[-1., 0.], [-2., 0.]], [0., 0.], -1., 1.)
    assert abs(answer.x[0]) < 1.e-9
    assert np.all(np.isfinite(answer.x))


def test_incompatible_geometry_is_reported_instead_of_accepted():
    with pytest.raises(RuntimeError, match='dual'):
        quadratic(np.eye(1), [0.], [[1.], [-1.]], [1., 0.], -2., 2.)


def test_metric_solve_preserves_temporal_and_distant_phase_coupling():
    from scipy.sparse import diags
    count = 240
    temporal = diags((-.3*np.ones(count-1), 2.*np.ones(count), -.3*np.ones(count-1)),
                     (-1, 0, 1), format='csc')
    rng = np.random.default_rng(20261004)
    rhs = rng.normal(size=(count, 5))
    for matrix in (temporal, temporal+csc_matrix(
            (.2*np.ones(2), ([0, count-1], [count-1, 0])), shape=(count, count))):
        actual = factor_metric(matrix).solve(rhs)
        np.testing.assert_allclose(matrix@actual, rhs, rtol=1.e-12, atol=1.e-12)
        np.testing.assert_allclose(actual, np.linalg.solve(matrix.toarray(), rhs), rtol=1.e-12, atol=1.e-12)


def test_expanding_working_set_keeps_all_previously_active_constraints():
    # The free step activates x>=0; enforcing it then activates y>=0 through
    # the metric coupling. Reused columns must coordinate both constraints.
    hessian = np.array([[2., 1.], [1., 2.]])
    answer = quadratic(hessian, -hessian@[-1., .1], np.eye(2), [0., 0.], -3., 3.)
    np.testing.assert_allclose(answer.x, [0., 0.], atol=1.e-9)


def test_metric_solve_restores_the_callers_blas_configuration():
    from threadpoolctl import threadpool_info, threadpool_limits
    with threadpool_limits(limits=4, user_api='blas'):
        before = [(pool['filepath'], pool['num_threads']) for pool in threadpool_info()
                  if pool['user_api'] == 'blas']
        factor = factor_metric(csc_matrix([[2., -.3], [-.3, 2.]]))
        actual = factor.solve(np.array([1., 2.]))
        np.testing.assert_allclose(np.array([[2., -.3], [-.3, 2.]])@actual, [1., 2.])
        after = [(pool['filepath'], pool['num_threads']) for pool in threadpool_info()
                 if pool['user_api'] == 'blas']
        assert after == before


class QuadraticProblem:
    """Independent linear objective with the production refresh/cache contract."""
    def __init__(self, joint, shape):
        self.shape = shape
        self.target = joint.target
        self.cached = {}
        self.timings = {}
        self.evaluations = 0

    def set_arguments(self, arguments, refresh):
        self.refresh = refresh

    def fun(self, flat):
        if not self.cached or not np.array_equal(flat, self.cached['state']):
            self.refresh(flat.reshape(self.shape))
            self.cached = dict(state=flat.copy(), value=flat-self.target)
            self.evaluations += 1
        return self.cached['value']

    def jac(self, flat):
        return csr_matrix(np.eye(len(flat)))


def toy_problem(monkeypatch, *, target=-1.):
    from motion_edit.generation import continuous_constrained_ik as module
    refresh = SimpleNamespace(constraint_linearizations=(), audits=[], calls=[])

    class Refresh:
        def __init__(self):
            self.__dict__.update(refresh.__dict__)

        def __call__(self, states, rows):
            gap = states[0, 0]
            self.calls.append(states.copy())
            self.constraint_linearizations = ((None, 0, 0, None, -1, None, None, gap),)
            self.audits.append(dict(terrain_excess_max_m=max(0., -gap), self_max_m=0.))
            return rows

    def linearize(problem, states, records):
        return np.array([states[0, 0]]), csr_matrix([[1.]])

    monkeypatch.setattr(module, 'linearize_signed_geometry', linearize)
    return SimpleNamespace(stack=lambda rows: rows, root_dofs=0,
                           target=np.array([target])), Refresh()


def test_accepted_pose_is_not_requeried_at_the_next_iteration(monkeypatch):
    joint, refresh = toy_problem(monkeypatch)
    result = solve_constrained_trajectory(joint, (), np.array([[.2]]), -2., 2., refresh,
        max_nfev=12, problem_class=QuadraticProblem)
    assert abs(result.states[0, 0]) < 1.e-8
    assert result.solves[-1]['success']
    assert result.solves[-1]['termination'] == 'kkt_stationary'
    assert len(refresh.calls) == 2
    assert sum(row['nfev'] for row in result.solves) == len(refresh.calls)


def test_evaluation_budget_does_not_claim_stationarity(monkeypatch):
    joint, refresh = toy_problem(monkeypatch, target=1.)
    result = solve_constrained_trajectory(joint, (), np.array([[.2]]), -2., 2., refresh,
        max_nfev=2, problem_class=QuadraticProblem)
    assert .9 < result.states[0, 0] < 1.
    assert not result.solves[-1]['success']
    assert result.solves[-1]['termination'] == 'evaluation_budget'
    assert len(refresh.calls) == 2


def test_curved_feasible_set_reaches_its_analytic_projection(monkeypatch):
    from motion_edit.generation import continuous_constrained_ik as module

    target=np.array([2., .1])
    class CircleRefresh:
        constraint_linearizations=()
        def __init__(self):
            self.audits=[]
        def __call__(self, states, rows):
            gap=1.-float(states.ravel()@states.ravel())
            self.constraint_linearizations=((None,0,0,None,-1,None,None,gap),)
            self.audits.append(dict(terrain_excess_max_m=max(0.,-gap),self_max_m=0.))
            return rows

    def linearize(problem, states, records):
        flat=states.ravel()
        return np.array([1.-flat@flat]),csr_matrix(-2.*flat[None])

    monkeypatch.setattr(module,'linearize_signed_geometry',linearize)
    joint=SimpleNamespace(stack=lambda rows:rows,root_dofs=0,target=target)
    result=solve_constrained_trajectory(joint,(),np.array([[1.,0.]]),-3.,3.,CircleRefresh(),
        max_nfev=125,problem_class=QuadraticProblem)
    expected=target/np.linalg.norm(target)
    np.testing.assert_allclose(result.states.ravel(),expected,atol=1.e-5,rtol=1.e-5)
    assert result.solves[-1]['success']
    assert np.linalg.norm(result.states) <= 1.+1.e-8
    assert any(trial.get('second_order_correction',{}).get('model_ratio',-1.) >= .1
               for row in result.solves for trial in row['trials'])
