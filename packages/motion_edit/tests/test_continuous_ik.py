import numpy as np
import pytest

jax = pytest.importorskip('jax')
import jax.numpy as jnp
from motion_edit.generation.continuous_ik import JointResidual, solve_matrix_free
from motion_edit.generation.continuous_sparse_ik import SparseJointProblem


def assert_sparse_matches_full_autodiff(joint, states, arguments):
    problem = SparseJointProblem(joint, states.shape)
    problem.set_arguments(arguments)
    dense = jax.jacfwd(lambda x: joint(x.reshape(states.shape), *arguments).reshape(-1))(
        jnp.asarray(states).reshape(-1))
    sparse = problem.jac(states.reshape(-1))
    np.testing.assert_allclose(sparse.toarray(), dense, rtol=1.e-10, atol=1.e-10)
    np.testing.assert_allclose(problem.fun(states.reshape(-1)),
                               joint(jnp.asarray(states), *arguments).reshape(-1), atol=1.e-12)
    return problem


def test_future_contact_gradient_reaches_preceding_pose():
    n = 8
    root = np.zeros((n, 7)); root[:, 3] = 1.
    def residual(state, q_previous, q_previous_previous, root_delta_previous,
                 root_delta_previous_previous, target, weight, history):
        return jnp.concatenate(((state[3:]-target)*weight,
            (state[3:]-q_previous)*history,
            (state[3:]-2*q_previous+q_previous_previous)*history))
    joint = JointResidual(residual, None, root, 3)
    states = np.zeros((n, 4)); states[-1, 3] = .2
    rows = [(np.zeros(1), np.zeros(1), np.zeros(3), np.zeros(3),
             np.array([.2 if t==n-1 else 0.]), np.array([10. if t in (0,n-1) else .01]),
             np.array([float(t>0)])) for t in range(n)]
    args = joint.stack(rows)
    problem = assert_sparse_matches_full_autodiff(joint, states, args)
    grad = jax.grad(lambda x: jnp.sum(joint(x, *args)**2))(jnp.asarray(states))
    assert grad[-2, 3] < 0  # preceding pose must move toward the future task
    result = solve_matrix_free(joint, np.zeros_like(states), -1., 1., max_nfev=30, arguments=args)
    solved = result.x.reshape(states.shape)
    assert result.success
    assert solved[-1, 3] > .19
    assert solved[-2, 3] > .1
    assert np.diff(solved[:, 3]).max() < .08
    sparse_result = problem.solve(np.zeros_like(states), -1., 1., max_nfev=30)
    assert sparse_result.success
    # Both solvers stop at gtol=1e-5, with different column preconditioners.
    np.testing.assert_allclose(sparse_result.x, result.x, atol=1.e-5)
    no_initial_observation = [tuple(value.copy() for value in row) for row in rows]
    no_initial_observation[0][5][:] = 0.
    scaling = joint.diagonal_scale(np.zeros_like(states), joint.stack(no_initial_observation))
    # Frame zero still has incoming temporal columns from frames one/two.
    assert scaling[0, 3] == pytest.approx(1./np.sqrt(6.))


def test_joint_matrix_free_jacobian_handles_bounded_variables():
    def residual(x):
        return jnp.concatenate((x-jnp.asarray([2., -.5]), jnp.diff(x)))
    result = solve_matrix_free(residual, np.zeros(2), np.array([0., -1.]),
                               np.array([1., 1.]), max_nfev=40)
    assert result.success
    assert result.x[0] == pytest.approx(1., abs=1.e-4)
    assert result.x[1] == pytest.approx(.25, abs=1.e-4)


def test_trial_and_jacobian_use_current_geometry_not_last_outer_witness():
    n = 1
    root = np.zeros((n, 7)); root[:, 3] = 1.
    def residual(state, q_previous, q_previous_previous, root_delta_previous,
                 root_delta_previous_previous, normal, plane):
        return state[3:]*normal-plane
    joint = JointResidual(residual, None, root, 3)
    states = np.zeros((n, 4)); states[0, 3] = .6
    observed = []
    def refresh(current):
        q = current[0, 3]
        observed.append(float(q))
        return joint.stack([(np.zeros(1), np.zeros(1), np.zeros(3), np.zeros(3),
            np.array([np.cos(q)]), np.array([q*np.cos(q)-np.sin(q)]))])
    problem = SparseJointProblem(joint, states.shape)
    problem.set_arguments(refresh(states), refresh=refresh)
    result = problem.solve(states, -1., 1., max_nfev=20)
    assert result.success
    assert abs(result.x[3]) < 1.e-5
    assert len(set(observed)) > 2
    trial = result.x.copy(); trial[3] = .4
    problem.fun(trial)
    # A rejected trial may have changed the cached witness. Explicitly asking
    # for the accepted pose's Jacobian must restore its own geometry.
    matrix = problem.jac(result.x)
    assert observed[-1] == pytest.approx(result.x[3])
    assert matrix[0, 3] == pytest.approx(np.cos(result.x[3]))


def test_loaded_phase_budget_depends_on_earlier_pose_not_frozen_spending():
    from types import SimpleNamespace
    from somaforge_core.loaded_material_motion import tangent_material_rms

    n = 8
    root = np.zeros((n, 7)); root[:, 3] = 1.
    class Robot:
        def forward_kinematics(self, q):
            return jnp.array([[1., 0., 0., 0., q[0], 0., 0.]])
    loaded = SimpleNamespace(reference=dict(phases=[dict(start=0, end=n-1, part=0)],
                                            calibration=[dict(allowance_m=0.)]))
    def residual(state, q_previous, q_previous_previous, root_delta_previous,
                 root_delta_previous_previous, loaded_links, loaded_local,
                 loaded_previous_points, loaded_normals, loaded_weights,
                 loaded_source_step, loaded_remaining, loaded_scale):
        current = jnp.broadcast_to(state[:3]+jnp.array([state[3], 0., 0.]), (6, 1, 3))
        rms = tangent_material_rms(current-loaded_previous_points, loaded_normals, loaded_weights, xp=jnp)
        return (jnp.stack((jnp.maximum(rms-loaded_source_step-loaded_remaining[0], 0.),
                           jnp.maximum(rms-loaded_remaining[1], 0.)))*loaded_scale).reshape(-1)
    joint = JointResidual(residual, Robot(), root, 3, loaded)
    rows = []
    for t in range(n):
        weights = np.zeros((6, 1)); weights[0] = float(t > 0)
        scale = np.zeros((2, 6)); scale[:, 0] = 100.*float(t > 0)
        rows.append((np.zeros(1), np.zeros(1), np.zeros(3), np.zeros(3),
            np.zeros((6, 1), int), np.zeros((6, 1, 3)), np.zeros((6, 1, 3)),
            np.broadcast_to([0., 0., 1.], (6, 1, 3)), weights,
            np.zeros(6), np.ones((2, 6))*999., scale))
    states = np.zeros((n, 4)); states[:, 3] = np.arange(n)*.02
    args = joint.stack(rows)
    assert_sparse_matches_full_autodiff(joint, states, args)
    values = joint(jnp.asarray(states), *args)
    assert values[-1, 6] == pytest.approx(8., abs=1.e-10)
    gradient = jax.grad(lambda x: joint(x, *args)[-1, 6]**2)(jnp.asarray(states))
    assert gradient[0, 3] < 0 and gradient[-1, 3] > 0
    np.testing.assert_allclose(gradient[1:-1, 3], 0., atol=1.e-10)


def test_sparse_material_chain_handles_root_yaw_and_changing_loaded_sites():
    from types import SimpleNamespace
    from scipy.spatial.transform import Rotation
    from somaforge_core.loaded_material_motion import tangent_material_rms

    n = 7
    root = np.zeros((n, 7))
    root[:, :3] = np.arange(n)[:, None]*np.array([.005, -.002, .003])
    root[:, 3:] = Rotation.from_euler('xyz', np.arange(n)[:, None]*np.array([.03, -.02, .05])).as_quat()[:, [3, 0, 1, 2]]
    rotations = Rotation.from_quat(root[:, [4, 5, 6, 3]]).as_matrix()
    class Robot:
        def forward_kinematics(self, q):
            return jnp.stack((jnp.cos(q[0]*.5), 0., 0., jnp.sin(q[0]*.5), q[1], q[0]*.5, 0.))[None]
    robot = Robot()
    loaded = SimpleNamespace(reference=dict(
        phases=[dict(start=1, end=5, part=0), dict(start=0, end=3, part=1)],
        calibration=[dict(allowance_m=.02), dict(allowance_m=.01)]))

    def residual(state, q_previous, q_previous_previous, root_delta_previous,
                 root_delta_previous_previous, root_yaw_axis_base, loaded_links, loaded_local,
                 loaded_previous_points, loaded_normals, loaded_weights,
                 loaded_source_step, loaded_remaining, loaded_scale):
        fk = robot.forward_kinematics(state[4:])
        half = state[3]*.5
        yaw = jnp.concatenate((jnp.cos(half)[None], root_yaw_axis_base*jnp.sin(half)))
        points = fk[loaded_links, 4:]+JointResidual.apply(fk[loaded_links, :4], loaded_local)
        points = JointResidual.apply(yaw, points)+state[:3]
        rms = tangent_material_rms(points-loaded_previous_points, loaded_normals, loaded_weights, xp=jnp)
        return (jnp.stack((jnp.maximum(jnp.maximum(rms-loaded_source_step, 0.)-loaded_remaining[0], 0.),
                           jnp.maximum(rms-loaded_remaining[1], 0.)))*loaded_scale).reshape(-1)

    joint = JointResidual(residual, robot, root, 4, loaded)
    rows = []
    for t in range(n):
        weights = np.zeros((6, 2)); scale = np.zeros((2, 6))
        for phase in loaded.reference['phases']:
            if phase['start'] < t <= phase['end']:
                p = phase['part']
                weights[p] = [1.+t, 3.]
                scale[:, p] = [31., 100.]
        local = np.broadcast_to([[.12, .04, 0.], [-.06, .03, .02]], (6, 2, 3)).copy()
        local += t*.002
        normal = np.array([.2, .3, 1.]); normal /= np.linalg.norm(normal)
        rows.append((np.zeros(2), np.zeros(2), np.zeros(4), np.zeros(4), rotations[t, 2],
            np.zeros((6, 2), int), local, np.zeros((6, 2, 3)),
            np.broadcast_to(normal, (6, 2, 3)), weights, np.full(6, .02),
            np.ones((2, 6))*999., scale))
    states = np.arange(n)[:, None]*np.array([.003, .007, -.002, .08, .1, .025])
    assert_sparse_matches_full_autodiff(joint, states, joint.stack(rows))
