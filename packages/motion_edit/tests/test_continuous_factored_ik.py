"""Check the accelerated derivative against the complete coupled JAX graph."""
from types import SimpleNamespace
import numpy as np
import pytest

jax = pytest.importorskip('jax')
import jax.numpy as jnp
from scipy.spatial.transform import Rotation
from motion_edit.generation.continuous_ik import JointResidual
from motion_edit.generation.continuous_factored_ik import FactoredJointProblem
from somaforge_core.loaded_material_motion import tangent_material_rms


@jax.tree_util.register_pytree_node_class
class Robot:
    joints = SimpleNamespace(num_actuated_joints=2)

    def tree_flatten(self):
        return (), None

    @classmethod
    def tree_unflatten(cls, auxiliary, children):
        return cls()

    def forward_kinematics(self, q):
        return jnp.stack((jnp.cos(q[0]*.5), q[0]*0, q[0]*0, jnp.sin(q[0]*.5),
                          q[1], q[0]*.5, q[0]*0))[None]


def problem_data(*, zero=False):
    n, rd, robot = 7, 4, Robot()
    root = np.zeros((n, 7))
    root[:, :3] = np.arange(n)[:, None]*[.005, -.002, .003]
    root[:, 3:] = Rotation.from_euler('xyz', np.arange(n)[:, None]*[.03, -.02, .05]).as_quat()[:, [3, 0, 1, 2]]
    rotations = Rotation.from_quat(root[:, [4, 5, 6, 3]]).as_matrix()
    loaded = SimpleNamespace(reference=dict(phases=[dict(start=1, end=5, part=0),
        dict(start=0, end=3, part=1)], calibration=[dict(allowance_m=.02), dict(allowance_m=.01)]))

    def residual(state, q_previous, q_previous_previous, root_delta_previous,
                 root_delta_previous_previous, root_yaw_axis_base, history_mask,
                 loaded_links, loaded_local, loaded_previous_points, loaded_normals,
                 loaded_weights, loaded_source_step, loaded_remaining, loaded_scale,
                 collision_deeper_weight, self_collision_sqrt_weight, release_weights,
                 fk_override=None):
        fk = robot.forward_kinematics(state[rd:]) if fk_override is None else fk_override
        if fk_override is None:
            half = state[3]*.5
            yaw = jnp.concatenate((jnp.cos(half)[None], root_yaw_axis_base*jnp.sin(half)))
            q = fk[:, :4]
            w = yaw[:1]*q[:, :1]-jnp.sum(yaw[1:]*q[:, 1:], -1, keepdims=True)
            xyz = yaw[:1]*q[:, 1:]+q[:, :1]*yaw[1:]+jnp.cross(yaw[1:], q[:, 1:])
            fk = jnp.concatenate((w, xyz, JointResidual.apply(yaw, fk[:, 4:7])), -1)
        points = fk[loaded_links, 4:]+JointResidual.apply(fk[loaded_links, :4], loaded_local)+state[:3]
        rms = tangent_material_rms(points-loaded_previous_points, loaded_normals, loaded_weights, xp=jnp)
        loaded_res = (jnp.stack((jnp.maximum(jnp.maximum(rms-loaded_source_step, 0.)-loaded_remaining[0], 0.),
                                jnp.maximum(rms-loaded_remaining[1], 0.)))*loaded_scale).reshape(-1)
        return jnp.concatenate((fk.reshape(-1),
            (state[rd:]-q_previous)*2.*history_mask[0],
            (state[rd:]-2*q_previous+q_previous_previous)*8.*history_mask[1],
            (state[:rd]-root_delta_previous)*10.*history_mask[0],
            (state[:rd]-2*root_delta_previous+root_delta_previous_previous)*20.*history_mask[1],
            loaded_res, jnp.minimum(state[:1], 0.)*collision_deeper_weight,
            state[:1]*self_collision_sqrt_weight, state[:1]*release_weights))

    residual.continuous_temporal_weights = (2., 8.)
    joint = JointResidual(residual, robot, root, rd, loaded)
    rows = []
    normal = np.array([.2, .3, 1.]); normal /= np.linalg.norm(normal)
    for t in range(n):
        weights = np.zeros((6, 2)); scale = np.zeros((2, 6))
        for phase in loaded.reference['phases']:
            if phase['start'] < t <= phase['end']:
                weights[phase['part']] = [1.+t, 3.]
                scale[:, phase['part']] = [31., 100.]
        local = np.broadcast_to([[.12, .04, 0.], [-.06, .03, .02]], (6, 2, 3)).copy()+t*.002
        rows.append((np.zeros(2), np.zeros(2), np.zeros(rd), np.zeros(rd), rotations[t, 2],
            np.array([float(t > 0), float(t > 1)]), np.zeros((6, 2), int), local,
            np.zeros((6, 2, 3)), np.broadcast_to(normal, (6, 2, 3)), weights,
            np.full(6, .02), np.ones((2, 6))*999., scale,
            np.ones(1), np.ones(1), np.ones(1)))
    states = np.arange(n)[:, None]*np.array([.003, .007, -.002, .08, .1, .025])
    if zero:
        states[:] = 0
    return joint, states, joint.stack(rows)


@pytest.mark.parametrize('zero', [False, True])
def test_shared_pose_and_analytic_history_match_full_graph(zero):
    jax.config.update('jax_enable_x64', True)
    joint, states, arguments = problem_data(zero=zero)
    problem = FactoredJointProblem(joint, states.shape)
    problem.set_arguments(arguments)
    expected = np.asarray(jax.jacfwd(lambda x: joint(x.reshape(states.shape), *arguments).reshape(-1))(
        jnp.asarray(states).reshape(-1)))
    np.testing.assert_allclose(problem.jac(states.reshape(-1)).toarray(), expected, atol=1.e-10, rtol=1.e-10)
    # Fresh arguments must invalidate cached values and change historical masks.
    changed = list(arguments); changed[joint.names.index('history_mask')] = np.zeros((len(states), 2))
    problem.set_arguments(tuple(changed))
    expected = np.asarray(jax.jacfwd(lambda x: joint(x.reshape(states.shape), *changed).reshape(-1))(
        jnp.asarray(states).reshape(-1)))
    np.testing.assert_allclose(problem.jac(states.reshape(-1)).toarray(), expected, atol=1.e-10, rtol=1.e-10)


def test_fp32_derivative_matches_same_precision_complete_graph():
    # The nonlinear material reduction itself can differ between precisions;
    # validate the factored derivative against the same independent graph.
    # Production remains FP64, checked separately above.
    previous_precision = jax.config.jax_enable_x64
    try:
        jax.config.update('jax_enable_x64', False)
        joint, states, arguments = problem_data()
        problem = FactoredJointProblem(joint, states.shape, dtype=np.float32)
        problem.set_arguments(arguments)
        expected = np.asarray(jax.jacfwd(lambda x: joint(x.reshape(states.shape),
            *problem.arguments).reshape(-1))(jnp.asarray(states).reshape(-1)))
        actual = problem.jac(states.reshape(-1)).toarray()
        np.testing.assert_allclose(actual, expected, atol=5.e-5, rtol=5.e-5)
        assert np.isfinite(actual).all()
    finally:
        jax.config.update('jax_enable_x64', previous_precision)


def test_live_refresh_restores_arguments_after_rejected_trial():
    jax.config.update('jax_enable_x64', True)
    joint, states, arguments = problem_data()
    problem = FactoredJointProblem(joint, states.shape)
    calls = []

    def refreshed(candidate):
        changed = list(arguments)
        changed[joint.names.index('release_weights')] = np.full((len(states), 1),
                                                               1.+abs(candidate[0, 0]))
        changed[joint.names.index('history_mask')] = np.asarray(arguments[
            joint.names.index('history_mask')])*(1.+abs(candidate[0, 0]))
        calls.append(candidate.copy())
        return tuple(changed)

    problem.set_arguments(arguments, refresh=refreshed)
    flat = states.reshape(-1)
    accepted = problem.fun(flat).copy()
    rejected = flat.copy(); rejected[0] += .2
    problem.fun(rejected)
    actual = problem.jac(flat).toarray()
    np.testing.assert_array_equal(calls[-1], states)
    expected = np.asarray(jax.jacfwd(lambda x: joint(x.reshape(states.shape),
        *problem.arguments).reshape(-1))(jnp.asarray(flat)))
    np.testing.assert_allclose(actual, expected, atol=1.e-10, rtol=1.e-10)
    np.testing.assert_array_equal(problem.fun(flat), accepted)


def test_signed_witness_derivative_preserves_root_yaw_and_self_cancellation():
    from motion_edit.generation.continuous_signed_geometry import linearize_signed_geometry

    jax.config.update('jax_enable_x64', True)
    joint, states, _ = problem_data()
    problem = FactoredJointProblem(joint, states.shape)
    records = (
        ('terrain', 2, 0, np.array([.12, -.03, .04]), -1, np.zeros(3),
         np.array([.2, -.3, .9]), .01),
        ('moving', 4, 0, np.array([.1, .02, -.03]), 0,
         np.array([-.08, .09, .02]), np.array([-.1, .8, .4]), .02))
    gaps, matrix = linearize_signed_geometry(problem, states, records)

    def witnesses(flat):
        value = flat.reshape(states.shape)
        poses = joint.poses(value)
        outputs = []
        for _, t, a, pa, b, pb, normal, _ in records:
            first = poses[t, a, 4:]+joint.apply(poses[t, a, :4], pa)+value[t, :3]
            second = (0. if b < 0 else poses[t, b, 4:]
                      +joint.apply(poses[t, b, :4], pb)+value[t, :3])
            outputs.append(jnp.dot(normal, first-second))
        return jnp.stack(outputs)

    expected = np.asarray(jax.jacfwd(witnesses)(jnp.asarray(states.ravel())))
    np.testing.assert_allclose(matrix.toarray(), expected, atol=1.e-11, rtol=1.e-11)
    np.testing.assert_array_equal(gaps, [.01, .02])
    np.testing.assert_array_equal(matrix.toarray()[1, 4*states.shape[1]:4*states.shape[1]+3], 0.)
