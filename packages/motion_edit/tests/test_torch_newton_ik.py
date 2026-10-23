"""Numerical and editor-contract checks for the independent native FK pilot."""
import builtins
import json
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from motion_edit.generation.torch_newton_ik import (
    ARRAY_API, TorchJointResidual, TorchFactoredJointProblem, assemble_torch_newton_problem)
from motion_edit.generation.torch_newton_kinematics import NewtonRobot


@pytest.fixture(scope='module')
def robot():
    return NewtonRobot()


def test_native_fk_matches_existing_canonical_torch_fk(robot):
    from somaforge_core.g1_kinematics import CanonicalG1ForwardKinematics, _quaternion_matrix_wxyz
    generator = torch.Generator().manual_seed(20261022)
    cfg = torch.rand((4, 29), generator=generator)*.8-.4
    poses = robot.forward_kinematics(cfg)
    qpos = torch.cat((torch.zeros((4, 3)), torch.tensor([[1., 0., 0., 0.]]).expand(4, -1), cfg), -1)
    position, rotation = CanonicalG1ForwardKinematics().link_poses(qpos, robot.links.names)
    torch.testing.assert_close(poses[..., 4:], position, atol=8.e-7, rtol=2.e-6)
    torch.testing.assert_close(_quaternion_matrix_wxyz(poses[..., :4]), rotation, atol=8.e-7, rtol=2.e-6)
    assert poses.dtype == torch.float32


def test_native_pose_derivative_and_backward_match_finite_difference(robot):
    cfg = torch.linspace(-.25, .25, 29).repeat(2, 1)
    direction = torch.cos(torch.arange(58, dtype=torch.float32)).reshape(2, 29)
    poses, jacobian = robot.evaluate(cfg, derivatives=True)
    step = 1.e-3
    difference = (robot.evaluate(cfg+step*direction)-robot.evaluate(cfg-step*direction))/(2*step)
    predicted = torch.einsum('blpq,bq->blp', jacobian, direction)
    torch.testing.assert_close(predicted, difference, atol=2.e-4, rtol=2.e-3)
    cfg.requires_grad_()
    weights = torch.sin(torch.arange(poses.numel(), dtype=torch.float32)).reshape_as(poses)
    gradient, = torch.autograd.grad((robot.forward_kinematics(cfg)*weights).sum(), cfg)
    torch.testing.assert_close(gradient, torch.einsum('blp,blpq->bq', weights, jacobian))


@pytest.mark.parametrize('root_dofs', [3, 4])
def test_root_yaw_and_native_joint_derivatives_share_the_same_pose(robot, root_dofs):
    root = np.zeros((3, 7)); root[:, 3] = 1.
    def residual(solve_state, q_previous, fk_override=None):
        return solve_state
    joint = TorchJointResidual(residual, robot, root, root_dofs)
    states = torch.linspace(-.15, .15, 3*(29+root_dofs)).reshape(3, -1)
    direction = torch.cos(torch.arange(states.numel(), dtype=torch.float32)).reshape_as(states)
    derivative, poses = joint.pose_derivatives(states)
    torch.testing.assert_close(poses, joint.poses(states))
    step = 1.e-3
    difference = (joint.poses(states+step*direction)-joint.poses(states-step*direction))/(2*step)
    predicted = torch.einsum('blpq,bq->blp', derivative, direction)
    torch.testing.assert_close(predicted, difference, atol=2.e-4, rtol=2.e-3)


def test_array_adapter_keeps_float32_and_symmetric_hinge_derivatives():
    x = torch.tensor([-1., 0., 1.], requires_grad=True)
    y = ARRAY_API.maximum(x, 0.)
    gradient, = torch.autograd.grad(y.sum(), x)
    torch.testing.assert_close(gradient, torch.tensor([0., .5, 1.]))
    assert ARRAY_API.asarray(np.ones(2, dtype=np.float64)).dtype == torch.float32
    assert ARRAY_API.asarray([1, 2]).dtype == torch.int64


def test_explicit_backend_script_bypasses_a_default_worker(monkeypatch, tmp_path):
    from motion_edit.generation import contact_aware_preview as preview
    monkeypatch.setenv('SOMAFORGE_IK_WORKER_SOCKET', '@unreachable-default-worker')
    monkeypatch.setattr(preview, 'pyroki_subprocess_context', lambda *a, **k: (['python'], {}))
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        (tmp_path/'output.npz').touch()
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(preview.subprocess, 'run', run)
    preview._run_pyroki_preview_subprocess(taskspace_path=tmp_path/'task.npz',
        source_motion_path=tmp_path/'source.npz', ik_output_path=tmp_path/'output.npz',
        ik_script=tmp_path/'torch_backend.py', ik_conda_env='current', ik_max_nfev=2)
    assert str(tmp_path/'torch_backend.py') in calls[0]


def test_default_generation_subprocess_uses_torch_without_jax(robot, tmp_path, monkeypatch):
    import sys
    from motion_edit.generation.contact_aware_preview import _run_pyroki_preview_subprocess
    task, source = _write_authored_task(tmp_path, robot)
    monkeypatch.delenv('SOMAFORGE_IK_WORKER_SOCKET', raising=False)
    monkeypatch.setenv('SOMAFORGE_IK_DEVICE', 'cpu')
    output = tmp_path/'default.npz'
    _run_pyroki_preview_subprocess(taskspace_path=task, source_motion_path=source,
        ik_output_path=output, ik_script=None, ik_conda_env=sys.prefix, ik_max_nfev=4)
    with np.load(output) as z:
        assert z['ik_backend'].item() == 'torch_newton_contact_aware_taskspace'
        assert json.loads(z['ik_diagnostics_json'].item())['ik_residual_dtype'] == 'float32'


def test_default_generation_rejects_an_inherited_legacy_worker(monkeypatch, tmp_path):
    from motion_edit.generation.contact_aware_preview import _run_pyroki_preview_subprocess
    from motion_edit.generation import torch_newton_batch
    monkeypatch.setenv('SOMAFORGE_IK_WORKER_SOCKET', '@legacy-jax-worker')
    monkeypatch.setattr(torch_newton_batch, 'worker_request', lambda *a, **k: dict(ok=True, pong=True))
    with pytest.raises(RuntimeError, match='not the default Torch/Newton'):
        _run_pyroki_preview_subprocess(taskspace_path=tmp_path/'task.npz', source_motion_path=tmp_path/'source.npz',
            ik_output_path=tmp_path/'out.npz', ik_script=None, ik_conda_env='unused', ik_max_nfev=4)


def test_default_cli_runtime_respects_cpu_and_cuda_selection(monkeypatch):
    import argparse
    from motion_edit.generation.ik_runtime import add_runtime_arguments, resolve_runtime
    monkeypatch.delenv('SOMAFORGE_IK_DEVICE', raising=False)
    parser = argparse.ArgumentParser(); add_runtime_arguments(parser)
    args = parser.parse_args([])
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: True)
    assert resolve_runtime(args.device, args.compile_kernels) == ('cuda:0', True)
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)
    assert resolve_runtime(args.device, args.compile_kernels) == ('cpu', False)
    args = parser.parse_args(['--device', 'cuda:1', '--no-compile-kernels'])
    assert resolve_runtime(args.device, args.compile_kernels) == ('cuda:1', False)


def test_formal_batch_launcher_serves_default_generation_and_canonical_fk(robot, tmp_path, monkeypatch):
    import importlib.util
    import os
    from pathlib import Path
    import sys
    from motion_edit.generation.contact_aware_preview import _run_pyroki_preview_subprocess
    from motion_edit.generation.newton_direct_fk import canonicalize_motion_with_direct_newton_fk
    path = Path(__file__).resolve().parents[3]/'scripts/generate_contact_aware_batch.py'
    spec = importlib.util.spec_from_file_location('default_backend_batch_test', path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module); spec.loader.exec_module(module)
    task, source = _write_authored_task(tmp_path, robot)
    name, process, log = module._start_ik_worker(index=0, environment=dict(os.environ,
        SOMAFORGE_IK_DEVICE='cpu', PYTHONDONTWRITEBYTECODE='1'), work_root=tmp_path, ik_conda_env=sys.prefix)
    try:
        identity = module._worker_request(name, dict(ping=True))
        assert identity['ik_backend'] == 'torch_newton_contact_aware_taskspace'
        assert identity['device'] == 'cpu'
        monkeypatch.setenv('SOMAFORGE_IK_WORKER_SOCKET', name)
        output = tmp_path/'batch_default.npz'
        _run_pyroki_preview_subprocess(taskspace_path=task, source_motion_path=source,
            ik_output_path=output, ik_script=None, ik_conda_env=sys.prefix, ik_max_nfev=4)
        canonical = tmp_path/'canonical.npz'
        canonicalize_motion_with_direct_newton_fk(output, canonical, device='cpu')
        with np.load(canonical) as z:
            assert z['ik_backend'].item() == 'torch_newton_contact_aware_taskspace'
            assert z['kinematics_backend'].item() == 'newton_direct_fk'
            assert z['newton_canonicalization_required'].item() is False
    finally:
        module._worker_request(name, dict(shutdown=True))
        process.wait(timeout=20); log.close()


def test_merge_preserves_independent_backend_and_editor_playback(tmp_path):
    from motion_edit.contact.plans import ContactEditPlan
    from motion_edit.generation.contact_aware_preview import merge_pyroki_preview_motion
    from motion_edit.web.motion_data import load_motion_sequence
    from somaforge_core import G1_29DOF_JOINT_ORDER
    from somaforge_core.robot_assets import encode_robot_asset_json
    qpos = np.zeros((3, 36), np.float32); qpos[:, 3] = 1.
    ik = dict(fps=np.array(50.), joint_pos=qpos, joint_vel=np.zeros((3, 35), np.float32),
        joint_names=np.array(G1_29DOF_JOINT_ORDER), body_names=np.array(['pelvis']),
        body_pos_w=np.zeros((3, 1, 3)), body_quat_w=np.tile([1., 0., 0., 0.], (3, 1, 1)),
        body_lin_vel_w=np.zeros((3, 1, 3)), body_ang_vel_w=np.zeros((3, 1, 3)),
        ik_backend=np.array('torch_newton_contact_aware_taskspace'),
        kinematics_backend=np.array('newton_urdf_fk_preview'), robot_asset_json=np.array(encode_robot_asset_json()))
    plan = ContactEditPlan(plan_id='pilot', source_motion_path='source.npz', source_motion_id='source',
        source_contact_layer='contact/source')
    merged = merge_pyroki_preview_motion(source_motion={'robot_asset_json': ik['robot_asset_json']},
        ik_motion=ik, plan=plan, proxy_metadata={}, taskspace_path=tmp_path/'task.npz',
        ik_output_path=tmp_path/'ik.npz', binding_summary={})
    metadata = json.loads(str(merged['motion_edit_generation_metadata']))
    assert metadata['joint_consistency'] == 'newton_urdf_fk_preview'
    assert metadata['newton_canonicalization_required'] is True
    output = tmp_path/'preview.npz'; np.savez_compressed(output, **merged)
    sequence, fps, names = load_motion_sequence(output)
    assert sequence.shape == (3, 36) and fps == 50.
    assert names == tuple(G1_29DOF_JOINT_ORDER)


def _write_authored_task(directory, robot, frames=4):
    """Authored pose targets only: no synthetic contact truth or support loads."""
    from motion_edit.generation.taskspace_spec import ContactAwareTaskspaceMotion, write_contact_aware_taskspace_motion
    from somaforge_core.robot_assets import encode_robot_asset_json
    cfg = np.broadcast_to(np.linspace(-.1, .1, 29), (frames, 29)).copy()
    cfg += np.arange(frames)[:, None]*.001
    root = np.zeros((frames, 7)); root[:, 2] = 1.1; root[:, 3] = 1.
    qpos = np.column_stack((root, cfg))
    semantic_names = ('pelvis', 'left_hand', 'right_hand')
    link_names = ('pelvis', 'left_sphere_hand_link', 'right_sphere_hand_link')
    indices = [robot.links.names.index(name) for name in link_names]
    targets = robot.numpy_fk(cfg)[:, indices, 4:]+root[:, None, :3]
    targets[:, 1:, 0] += .02
    source = directory/'source.npz'
    np.savez_compressed(source, fps=50., joint_pos=qpos.astype(np.float32),
        joint_names=np.array(robot.joints.actuated_names), robot_asset_json=encode_robot_asset_json())
    spec = ContactAwareTaskspaceMotion(motion_id='authored_pose_regression', fps=50., frame_start=0,
        frame_end=frames, semantic_names=semantic_names, semantic_targets_w=targets,
        semantic_weights=np.full((frames, 3), 100.), contacts=(), source_qpos=qpos,
        source_qvel=np.zeros((frames, 35)), source_reference_weights=np.ones((frames, 36)),
        boundary_weights=np.zeros(frames), metadata=dict(augmentation_objective='consolidated_v1',
            free_surface_contacts=True, support_surface_transforms=[],
            experiment_scope='authored_targets_not_contact_labels'))
    task = directory/'task.npz'; write_contact_aware_taskspace_motion(task, spec)
    return task, source


@pytest.mark.parametrize('loaded', [False, True])
def test_sparse_complete_trajectory_derivative_including_material_prefix(robot, tmp_path, loaded):
    task, source = _write_authored_task(tmp_path, robot)
    problem = assemble_torch_newton_problem(lte_path=task, source_motion_path=source)
    joint = problem.joint
    if loaded:
        # Test-only mathematical data exercises the exact cumulative derivative.
        # This object is never written as measured support evidence.
        joint.loaded = SimpleNamespace(reference=dict(phases=[dict(start=0, end=3, part=p) for p in range(6)],
            calibration=[dict(allowance_m=0.) for _ in range(6)]))
        rows = []
        for frame, row in enumerate(problem.rows):
            args = dict(zip(joint.names, row))
            args['loaded_links'] = np.full((6, 1), joint.robot.links.names.index('left_sphere_hand_link'))
            args['loaded_normals'] = np.tile([0., 0., 1.], (6, 1, 1))
            args['loaded_weights'] = np.ones((6, 1))
            args['loaded_scale'] = np.ones((2, 6))*(30. if frame else 0.)
            rows.append(tuple(args[name] for name in joint.names))
        problem.rows = rows
    solver = TorchFactoredJointProblem(joint, problem.initial.shape)
    solver.set_arguments(joint.stack(problem.rows))
    states = problem.initial+np.sin(np.arange(problem.initial.size)).reshape(problem.initial.shape)*.008
    direction = np.cos(np.arange(states.size)*.3).reshape(states.shape).astype(np.float32)
    step = 1.e-4
    difference = (solver.fun((states+step*direction).ravel())-solver.fun((states-step*direction).ravel()))/(2*step)
    predicted = solver.jac(states.ravel())@direction.ravel()
    bad = np.flatnonzero(np.abs(predicted-difference) > .02+.01*np.abs(difference))
    details = [(int(i//(len(difference)//len(states))), int(i % (len(difference)//len(states))),
                float(predicted[i]), float(difference[i])) for i in bad[:12]]
    np.testing.assert_allclose(predicted, difference, atol=.02, rtol=.01, err_msg=str(details))
    assert solver.fun(states.ravel()).dtype == np.float32


def test_independent_backend_solves_and_exports_without_jax_or_pyroki(robot, tmp_path, monkeypatch):
    from motion_edit.generation.torch_newton_ik import solve_torch_newton_ik
    task, source = _write_authored_task(tmp_path, robot)
    original_import = builtins.__import__
    def no_jax(name, *args, **kwargs):
        if name.split('.')[0] in {'jax', 'jaxlib', 'jaxlie', 'jaxls', 'pyroki'}:
            raise AssertionError('Independent backend imported '+name)
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', no_jax)
    output = solve_torch_newton_ik(lte_path=task, source_motion_path=source,
        output_path=tmp_path/'out.npz', max_nfev=8)
    with np.load(output) as z:
        assert z['joint_pos'].shape == (4, 36)
        assert z['ik_backend'].item() == 'torch_newton_contact_aware_taskspace'
        diagnostics = json.loads(z['ik_diagnostics_json'].item())
        assert diagnostics['ik_residual_dtype'] == 'float32'
        assert diagnostics['semantic_target_error_m']['mean'] < .014
    from motion_edit.web.review import load_review
    payload = load_review(output, url=str)
    assert payload['capabilities']['playback'] is True
    assert len(payload['qpos']) == 4


def test_material_reporting_uses_exported_native_poses_without_jax(robot, tmp_path):
    from motion_edit.generation.torch_newton_ik import solve_prepared_problem

    task, source = _write_authored_task(tmp_path, robot)
    problem = assemble_torch_newton_problem(lte_path=task, source_motion_path=source)
    recorded = []
    # Exercise the export ledger only. This fixture supplies no contact truth.
    problem.context['loaded_motion'] = SimpleNamespace(
        reference=dict(reference_scope='test_reporting_only', original_provenance={}),
        commit=lambda frame, before, rotations_before, points, rotations:
            recorded.append((frame, points.copy())),
        report=lambda: dict(status='unknown', optimization_enabled=False))
    output = solve_prepared_problem(problem, output_path=tmp_path/'reported.npz', max_nfev=2)
    with np.load(output) as motion:
        assert [frame for frame, _ in recorded] == list(range(4))
        np.testing.assert_allclose(np.stack([points for _, points in recorded]),
                                   motion['body_pos_w'], atol=2.e-6)
        report = json.loads(motion['ik_diagnostics_json'].item())
        assert report['actual_edited_support'] == 'unknown_without_new_execution'


def test_native_pose_derivatives_drive_the_complete_hard_constrained_solve(robot, tmp_path):
    """An authored mathematical plane tests SQP, never simulation contact truth."""
    from motion_edit.generation.continuous_constrained_ik import solve_constrained_trajectory
    task, source = _write_authored_task(tmp_path, robot)
    problem = assemble_torch_newton_problem(lte_path=task, source_motion_path=source)
    joint = problem.joint
    link = joint.robot.links.names.index('left_sphere_hand_link')
    initial_pose = joint.poses(ARRAY_API.asarray(problem.initial)).numpy()
    ceiling = initial_pose[:, link, 4].copy()

    class Plane:
        def __init__(self):
            self.audits = []
            self.constraint_linearizations = ()

        def __call__(self, states, rows):
            fk = joint.poses(ARRAY_API.asarray(states)).numpy()
            gaps = ceiling-fk[:, link, 4]-states[:, 0]
            self.constraint_linearizations = tuple(('unit_test_plane', t, link, np.zeros(3),
                -1, np.zeros(3), np.array([-1., 0., 0.]), gap) for t, gap in enumerate(gaps))
            self.audits.append(dict(terrain_excess_max_m=float(np.maximum(-gaps, 0).max()), self_max_m=0.))
            return rows

    refresh = Plane()
    result = solve_constrained_trajectory(joint, problem.rows, problem.initial,
        problem.lower, problem.upper, refresh, max_nfev=12, problem_class=TorchFactoredJointProblem)
    refresh(result.states, problem.rows)
    assert max(-r[7] for r in refresh.constraint_linearizations) < 5.e-7
    # The constrained hand cannot reach the requested +2 cm x target.
    fk = joint.poses(ARRAY_API.asarray(result.states)).numpy()
    requested = problem.context['compiled'].semantic_targets_w[:, 1, 0]
    actual = joint.root.numpy()[:, 0]+fk[:, link, 4]+result.states[:, 0]
    assert np.min(requested-actual) > .019


def test_native_collision_queries_with_rotated_source_keep_rigid_frames(robot, tmp_path):
    """Actual COAL witnesses must remain defined with a float32 FK backend."""
    pytest.importorskip('coal')
    import trimesh
    from dataclasses import replace
    from scipy.spatial.transform import Rotation
    from motion_edit.generation.taskspace_spec import read_contact_aware_taskspace_motion, write_contact_aware_taskspace_motion
    task, source = _write_authored_task(tmp_path, robot)
    spec = read_contact_aware_taskspace_motion(task)
    q = spec.source_qpos.copy()
    q[:, 3:7] = Rotation.from_euler('xyz', [.2, -.13, .8]).as_quat()[[3, 0, 1, 2]]
    with np.load(source) as z:
        payload = {k:z[k].copy() for k in z.files}
    np.savez_compressed(source, **dict(payload, joint_pos=q.astype(np.float32)))
    terrain = tmp_path/'box.obj'
    mesh = trimesh.creation.box(extents=(.4, .4, .4))
    mesh.apply_translation([3., 3., .2]); mesh.export(terrain)
    spec = replace(spec, source_qpos=q, metadata=dict(spec.metadata,
        target_terrain_mesh=str(terrain), source_terrain_mesh=str(terrain), collision_reference_motion=str(source)))
    write_contact_aware_taskspace_motion(task, spec)
    problem = assemble_torch_newton_problem(lte_path=task, source_motion_path=source)
    native_frame = problem.refresh.joint.rotations
    np.testing.assert_allclose(native_frame.transpose(0, 2, 1)@native_frame,
        np.broadcast_to(np.eye(3), native_frame.shape), atol=1.e-14)
    assert problem.joint.poses(ARRAY_API.asarray(problem.initial)).dtype == torch.float32
    problem.refresh(problem.initial, problem.rows)
    assert problem.refresh.audits[-1]['geometry_distance_known'] is True


def test_persistent_worker_reuses_kernels_without_reusing_solution(robot, tmp_path):
    from motion_edit.generation.torch_newton_worker import TorchNewtonWorker
    task, source = _write_authored_task(tmp_path, robot)
    worker = TorchNewtonWorker(chunk_size=4)
    kwargs = dict(lte_path=task, source_motion_path=source, max_nfev=4)
    strict, _, _ = worker.prepare(**kwargs)
    assert strict.context['historical_reference_only'] is False
    archived = TorchNewtonWorker(chunk_size=4, historical_reference_only=True)
    reference, _, _ = archived.prepare(**kwargs)
    assert reference.context['historical_reference_only'] is True
    strict_override, _, _ = archived.prepare(**kwargs, historical_reference_only=False)
    assert strict_override.context['historical_reference_only'] is False
    a = worker.solve(output_path=tmp_path/'first.npz', **kwargs)
    assert worker.last_report['kernel_cache_hit'] is False
    b = worker.solve(output_path=tmp_path/'second.npz', **kwargs)
    assert worker.last_report['kernel_cache_hit'] is True
    with np.load(a) as za, np.load(b) as zb:
        np.testing.assert_array_equal(za['joint_pos'], zb['joint_pos'])
    _, _, hit = worker.prepare(**dict(kwargs, q_prior_weight=.75))
    assert hit is False
    # Mutating the authored task at the same path also invalidates the cache.
    from dataclasses import replace
    from motion_edit.generation.taskspace_spec import read_contact_aware_taskspace_motion, write_contact_aware_taskspace_motion
    spec = read_contact_aware_taskspace_motion(task)
    write_contact_aware_taskspace_motion(task, replace(spec, semantic_targets_w=spec.semantic_targets_w+.001))
    _, _, hit = worker.prepare(**kwargs)
    assert hit is False


@pytest.mark.skipif(not torch.cuda.is_available(), reason='CUDA required for GPU parity')
@pytest.mark.parametrize('compiled', [False, True])
@pytest.mark.parametrize('loaded', [False, True])
def test_gpu_residual_and_derivatives_match_cpu(robot, tmp_path, compiled, loaded):
    task, source = _write_authored_task(tmp_path, robot, frames=5)
    cpu = assemble_torch_newton_problem(lte_path=task, source_motion_path=source)
    gpu = assemble_torch_newton_problem(lte_path=task, source_motion_path=source,
        device='cuda:0', compile_kernels=compiled, chunk_size=4)
    if loaded:
        for problem in (cpu, gpu):
            joint = problem.joint
            # Mathematical material-path inputs only; never contact/support truth.
            joint.loaded = SimpleNamespace(reference=dict(phases=[dict(start=0, end=4, part=p) for p in range(6)],
                calibration=[dict(allowance_m=0.) for _ in range(6)]))
            rows = []
            for frame, row in enumerate(problem.rows):
                args = dict(zip(joint.names, row))
                args['loaded_links'] = np.full((6, 1), joint.robot.links.names.index('left_sphere_hand_link'))
                args['loaded_normals'] = np.tile([0., 0., 1.], (6, 1, 1))
                args['loaded_weights'] = np.ones((6, 1))
                args['loaded_scale'] = np.ones((2, 6))*(30. if frame else 0.)
                rows.append(tuple(args[name] for name in joint.names))
            problem.rows = rows
    cfg = torch.linspace(-.2, .2, 29).repeat(5, 1)
    for a, b in zip(robot.evaluate(cfg, derivatives=True), gpu.joint.robot.evaluate(cfg, derivatives=True)):
        torch.testing.assert_close(a, b.cpu(), atol=8.e-7, rtol=3.e-6)
    solvers = []
    for problem in (cpu, gpu):
        solver = TorchFactoredJointProblem(problem.joint, problem.initial.shape)
        solver.set_arguments(problem.joint.stack(problem.rows))
        solvers.append(solver)
    state = cpu.initial.ravel()+np.sin(np.arange(cpu.initial.size))*.003
    value = solvers[1].fun(state)
    np.testing.assert_allclose(solvers[0].fun(state), value, atol=4.e-5, rtol=3.e-5)
    a, b = (s.jac(state).toarray() for s in solvers)
    if loaded:
        count = len(value)//len(cpu.initial)
        args = dict(zip(cpu.joint.names, cpu.joint.stack(cpu.rows)))
        safety = sum(args[n].shape[1] for n in
            ('collision_deeper_weight', 'self_collision_sqrt_weight', 'release_weights'))
        start = count-safety-12
        material = (np.arange(len(value))%count >= start) & (np.arange(len(value))%count < start+12)
        np.testing.assert_allclose(a[~material], b[~material], atol=4.e-5, rtol=3.e-5)
        # Normalizing tiny material displacements amplifies the independently
        # verified float32 CPU/CUDA FK rounding. Check the sparse derivative
        # against full-trajectory autodiff on identical GPU poses as well.
        np.testing.assert_allclose(a[material], b[material], atol=.0025, rtol=.001)
        gpu_state = gpu.joint.jnp.asarray(state).requires_grad_()
        with torch.compiler.set_stance('force_eager'):
            dense = torch.autograd.functional.jacobian(lambda x:
                gpu.joint(x.reshape(gpu.initial.shape), *solvers[1].arguments).reshape(-1),
                gpu_state, vectorize=True).detach().cpu().numpy()
        np.testing.assert_allclose(b, dense, atol=4.e-5, rtol=3.e-5)
    else:
        np.testing.assert_allclose(a, b, atol=4.e-5, rtol=3.e-5)
    if compiled:
        # Same native poses and inputs: compilation must preserve the Jacobian.
        with torch.compiler.set_stance('force_eager'):
            eager = solvers[1].jac(state).toarray()
        np.testing.assert_allclose(eager, b, atol=4.e-5, rtol=3.e-5)


def test_worker_socket_recovers_after_failed_request():
    import socket
    import threading
    import time
    import uuid
    from motion_edit.generation.torch_newton_worker import serve_worker
    from motion_edit.generation.torch_newton_batch import worker_request
    class Broken:
        backend = SimpleNamespace(array_api=SimpleNamespace(device='cpu'))
        def solve(self, **kwargs):
            raise ValueError('deliberate invalid request')
    name = '@torch-worker-test-'+uuid.uuid4().hex
    thread = threading.Thread(target=serve_worker, args=(name, Broken()), daemon=True)
    thread.start()
    for _ in range(100):
        try:
            assert worker_request(name, dict(ping=True))['pong'] is True
            break
        except (ConnectionRefusedError, FileNotFoundError):
            time.sleep(.01)
    else:
        pytest.fail('worker failed to bind')
    try:
        with pytest.raises(RuntimeError, match='deliberate invalid request'):
            worker_request(name, dict(kwargs={}))
        assert worker_request(name, dict(ping=True))['pong'] is True
    finally:
        worker_request(name, dict(shutdown=True))
        thread.join(timeout=2.)
    assert not thread.is_alive()
