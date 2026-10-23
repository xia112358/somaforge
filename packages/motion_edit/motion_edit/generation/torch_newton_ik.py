"""Default float32 Torch/Newton trajectory IK, with the editor's NPZ contract.

No JAX/PyRoki code is executed. Task compilation, sparse block assembly and the
existing constrained SQP/QP driver are shared, so this experiment changes the
kinematics and differentiation backend without changing task semantics. Sparse
factorization/QP remain SciPy/Clarabel; this is not an all-GPU solver.

The editor and batch generator select this backend by default. It also runs
directly with --taskspace-spec, --source-motion and --out.
"""
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import time
from types import SimpleNamespace
from functools import partial, lru_cache

import numpy as np
import torch
from scipy.spatial.transform import Rotation

from motion_edit.generation.torch_newton_kinematics import NewtonRobot, quat_apply, quat_multiply


SOLVER_SCHEMA = 'torch_float32_newton_fk_joint_trajectory_pilot_v1'


class TorchArrayAPI:
    """Small explicit array vocabulary for the shared backend-neutral residual."""
    int32 = torch.int64

    def __init__(self, device='cpu'):
        self.device = torch.device(device)

    def asarray(self, value, dtype=None):
        if dtype is not None:
            if isinstance(dtype, torch.dtype):
                dtype = torch.float32 if dtype.is_floating_point else dtype
            else:
                dtype = (torch.float32 if np.issubdtype(np.dtype(dtype), np.floating) else
                    torch.bool if np.dtype(dtype) == bool else torch.int64)
        if isinstance(value, torch.Tensor):
            return value.to(device=self.device, dtype=dtype or (torch.float32 if value.is_floating_point() else value.dtype))
        if isinstance(value, (float, int, bool)):
            dtype = dtype or (torch.bool if isinstance(value, bool) else
                torch.float32 if isinstance(value, float) else torch.int64)
            return torch.tensor(value, dtype=dtype, device=self.device)
        if isinstance(value, (list, tuple)):
            return torch.as_tensor(value, dtype=dtype, device=self.device)
        array = np.asarray(value)
        if dtype is None:
            dtype = (torch.float32 if np.issubdtype(array.dtype, np.floating) else
                torch.bool if array.dtype == bool else torch.int64)
        # Authored reference arrays can be read-only; never alias their storage.
        return torch.as_tensor(array.copy(), dtype=dtype, device=self.device)

    @staticmethod
    def sum(x, axis=None, keepdims=False):
        return torch.sum(x, dim=axis, keepdim=keepdims)

    def maximum(self, a, b):
        return torch.maximum(self.asarray(a), self.asarray(b))

    def minimum(self, a, b):
        return torch.minimum(self.asarray(a), self.asarray(b))

    def sqrt(self, x):
        return torch.sqrt(self.asarray(x))

    @staticmethod
    def cross(a, b):
        return torch.linalg.cross(*torch.broadcast_tensors(a, b), dim=-1)

    def concatenate(self, xs, axis=0):
        return torch.cat([x if isinstance(x, torch.Tensor) else self.asarray(x) for x in xs], dim=axis)

    def stack(self, xs, axis=0):
        return torch.stack([x if isinstance(x, torch.Tensor) else self.asarray(x) for x in xs], dim=axis)

    @staticmethod
    def moveaxis(x, source, destination):
        return torch.movedim(x, source, destination)

    @staticmethod
    def any(x, axis=None):
        return torch.any(x, dim=axis)

    where = staticmethod(torch.where)
    einsum = staticmethod(torch.einsum)
    zeros_like = staticmethod(torch.zeros_like)
    cos = staticmethod(torch.cos)
    sin = staticmethod(torch.sin)
    broadcast_to = staticmethod(torch.broadcast_to)
    diff = staticmethod(torch.diff)
    dot = staticmethod(torch.dot)
    array = asarray


ARRAY_API = TorchArrayAPI()


def _batch_kernel(frame, joint):
    """Compile a bounded batch, reusing its graph across iterations and jobs."""
    kernel = torch.vmap(frame)
    if joint.compile_kernels:
        kernel = torch.compile(kernel, fullgraph=True, dynamic=False)

    def concatenate(parts):
        if isinstance(parts[0], tuple):
            return tuple(concatenate([part[i] for part in parts]) for i in range(len(parts[0])))
        return torch.cat(parts, 0)

    def run(*args):
        parts = []
        for start in range(0, len(args[0]), joint.chunk_size):
            chunk = tuple(a[start:start+joint.chunk_size] for a in args)
            parts.append(kernel(*chunk))
        return concatenate(parts)
    return run


class TorchJointResidual:
    def __init__(self, residual, robot, root_source, root_dofs, loaded_motion=None,
                 *, array_api=None, compile_kernels=False, chunk_size=64):
        self.residual, self.robot = residual, robot
        self.root_dofs, self.loaded = root_dofs, loaded_motion
        parameters = tuple(inspect.signature(residual).parameters)
        self.names = tuple(name for name in parameters[1:] if name != 'fk_override')
        self.accepts_fk_override = 'fk_override' in parameters
        self.jnp = array_api or TorchArrayAPI(getattr(robot, 'device', 'cpu'))
        self.compile_kernels, self.chunk_size = compile_kernels, chunk_size
        self.root = self.jnp.asarray(root_source)
        self.rotations = self.jnp.asarray(Rotation.from_quat(
            np.asarray(root_source)[:, [4, 5, 6, 3]]).as_matrix())
        self.apply = quat_apply

    @staticmethod
    def to_numpy(value):
        return value.detach().cpu().numpy() if isinstance(value, torch.Tensor) else np.asarray(value)

    def stack(self, rows):
        if any(len(row) != len(self.names) for row in rows):
            raise ValueError('Per-frame residual argument layout changed')
        return tuple(np.stack(values) for values in zip(*rows))

    def pose_derivatives(self, states, rotations=None):
        states = self.jnp.asarray(states)
        rotations = self.rotations if rotations is None else self.jnp.asarray(rotations)
        rd = self.root_dofs
        fk, joint_jac = self.robot.evaluate(states[:, rd:], derivatives=True)
        derivative = torch.cat((torch.zeros((*fk.shape, rd), dtype=torch.float32, device=fk.device), joint_jac), -1)
        if rd == 4:
            axis = rotations[:, 2]
            half = states[:, 3]*.5
            yaw = torch.cat((half.cos()[:, None], axis*half.sin()[:, None]), -1)
            fk = torch.cat((quat_multiply(yaw[:, None], fk[..., :4]),
                quat_apply(yaw[:, None], fk[..., 4:])), -1)
            dq = quat_multiply(yaw[:, None, None], derivative[..., :4, :].transpose(-1, -2))
            dp = quat_apply(yaw[:, None, None], derivative[..., 4:, :].transpose(-1, -2))
            derivative = torch.cat((dq, dp), -1).transpose(-1, -2)
            omega = torch.cat((torch.zeros_like(axis[:, :1]), axis), -1)
            derivative[..., :4, 3] = .5*quat_multiply(omega[:, None], fk[..., :4])
            derivative[..., 4:, 3] = torch.linalg.cross(
                axis[:, None].expand_as(fk[..., 4:]), fk[..., 4:])
        return derivative, fk

    def poses(self, states):
        # Value evaluations do not need to materialize the FK Jacobian.
        states = self.jnp.asarray(states)
        fk = self.robot.forward_kinematics(states[:, self.root_dofs:])
        if self.root_dofs == 4:
            half = states[:, 3]*.5
            yaw = torch.cat((half.cos()[:, None], self.rotations[:, 2]*half.sin()[:, None]), -1)
            fk = torch.cat((quat_multiply(yaw[:, None], fk[..., :4]),
                quat_apply(yaw[:, None], fk[..., 4:])), -1)
        return fk

    def dynamic_arguments(self, states, *arguments, poses_override=None):
        args = dict(zip(self.names, arguments))
        previous = torch.cat((states[:1], states[:-1]), 0)
        previous_previous = torch.cat((states[:1], previous[:-1]), 0)
        args.update(q_previous=previous[:, self.root_dofs:],
            q_previous_previous=previous_previous[:, self.root_dofs:],
            root_delta_previous=previous[:, :self.root_dofs],
            root_delta_previous_previous=previous_previous[:, :self.root_dofs])
        if self.loaded is not None:
            from somaforge_core.loaded_material_motion import tangent_material_rms, DEFAULT_MATERIAL_PATH_BUDGET_M
            fk = self.poses(states) if poses_override is None else poses_override
            links, local = args['loaded_links'][1:], args['loaded_local'][1:]
            times = torch.arange(len(states)-1, device=states.device)[:, None, None]
            now, before = fk[times+1, links], fk[times, links]
            current = now[..., 4:]+quat_apply(now[..., :4], local)+states[1:, None, None, :3]
            prior = before[..., 4:]+quat_apply(before[..., :4], local)+states[:-1, None, None, :3]
            world = self.root[:-1, None, None, :3]+torch.einsum('tij,tpnj->tpni', self.rotations[:-1], prior)
            prior_base = torch.einsum('tji,tpnj->tpni', self.rotations[1:], world-self.root[1:, None, None, :3])
            args['loaded_previous_points'] = torch.cat((args['loaded_previous_points'][:1], prior_base), 0)
            rms = tangent_material_rms(current-prior_base, args['loaded_normals'][1:],
                args['loaded_weights'][1:], xp=self.jnp)
            extra = torch.maximum(rms-args['loaded_source_step'][1:], torch.zeros_like(rms))
            remaining = torch.zeros_like(args['loaded_remaining'])
            for i, phase in enumerate(self.loaded.reference['phases']):
                a, b, p = (int(phase[k]) for k in ('start', 'end', 'part'))
                allowance = self.loaded.reference['calibration'][i]['allowance_m']
                remaining[a+1:b+1, 0, p] = allowance-(extra[a:b, p].cumsum(0)-extra[a:b, p])
                remaining[a+1:b+1, 1, p] = DEFAULT_MATERIAL_PATH_BUDGET_M-(rms[a:b, p].cumsum(0)-rms[a:b, p])
            args['loaded_remaining'] = remaining
        return args

    def __call__(self, states, *arguments):
        states = self.jnp.asarray(states)
        arguments = tuple(self.jnp.asarray(a) for a in arguments)
        fk = self.poses(states) if self.accepts_fk_override else None
        args = self.dynamic_arguments(states, *arguments, poses_override=fk)
        ordered = tuple(args[name] for name in self.names)
        if not hasattr(self, '_values'):
            self._values = (_batch_kernel(lambda state, pose, *row:
                self.residual(state, *row, fk_override=pose), self) if self.accepts_fk_override
                else _batch_kernel(self.residual, self))
        return (self._values(states, fk, *ordered) if self.accepts_fk_override
                else self._values(states, *ordered))


class TorchFactoredJointProblem:
    """Float32 local derivatives with the existing exact sparse trajectory layout."""
    def __init__(self, joint, shape):
        self.joint, self.shape = joint, shape
        self.jnp = ARRAY_API
        self.dtype = np.dtype('float32')
        self.weights = joint.residual.continuous_temporal_weights
        # The unchanged SciPy driver owns host arrays; device transfers are
        # explicit at this boundary, including signed-geometry derivatives.
        self.root, self.rotations = map(joint.to_numpy, (joint.root, joint.rotations))
        self.pose_derivatives = lambda states, rotations=None: tuple(map(joint.to_numpy,
            joint.pose_derivatives(states, rotations)))
        self.value = lambda flat, *args: joint.to_numpy(joint(flat.reshape(shape), *args).reshape(-1))
        self.arguments = None
        self.refresh_arguments = None
        self.cached = {}
        self.evaluations = 0
        self.timings = {}

    def set_arguments(self, arguments, progress=None, refresh=None):
        from motion_edit.generation.continuous_sparse_ik import SparseJointProblem
        SparseJointProblem.set_arguments(self, arguments, progress, refresh)

    def fun(self, flat):
        from motion_edit.generation.continuous_sparse_ik import SparseJointProblem
        return SparseJointProblem.fun(self, flat)

    def jac(self, flat):
        from motion_edit.generation.continuous_factored_ik import FactoredJointProblem
        return FactoredJointProblem.jac(self, flat)

    def solve(self, initial, lower, upper, *, max_nfev=25):
        from motion_edit.generation.continuous_sparse_ik import SparseJointProblem
        return SparseJointProblem.solve(self, initial, lower, upper, max_nfev=max_nfev)

    def geometry(self, states, *arguments):
        joint = self.joint
        states = joint.jnp.asarray(states)
        arguments = tuple(joint.jnp.asarray(a) for a in arguments)
        fk_jac, fk = joint.pose_derivatives(states)
        dynamic = joint.dynamic_arguments(states, *arguments, poses_override=fk)
        ordered = tuple(dynamic[name] for name in joint.names)

        def frame(state, pose, derivative, *row):
            args = dict(zip(joint.names, row))
            args['loaded_scale'] = torch.zeros_like(args['loaded_scale'])
            row = tuple(args[name] for name in joint.names)
            def linearized(s):
                # Only the derivative of this expression is used. Newton owns
                # the actual pose; FK is evaluated exactly once per frame.
                local_pose = pose+(derivative*(s-state)[None, None]).sum(-1)
                return joint.residual(s, *row, fk_override=local_pose)
            # Reverse-mode avoids Torch 2.11's CUDA compile bugs with nested
            # forward AD. Eager execution retains the cheaper 33-direction sweep.
            jacobian = torch.func.jacrev if joint.compile_kernels else torch.func.jacfwd
            return jacobian(linearized)(state)

        if not hasattr(joint, '_jacobian'):
            joint._jacobian = _batch_kernel(frame, joint)
        blocks = joint._jacobian(states, fk, fk_jac, *ordered)
        if joint.loaded is None:
            return joint.to_numpy(blocks), (), ()

        def material(s, previous, pose, before, derivative, before_derivative,
                     links, local, normals, weights, root, rotation, old_root, old_rotation):
            from somaforge_core.loaded_material_motion import tangent_material_rms
            def linearized(current, old):
                now = (pose+(derivative*(current-s)[None, None]).sum(-1))[links]
                prior = (before+(before_derivative*(old-previous)[None, None]).sum(-1))[links]
                current_point = now[..., 4:]+quat_apply(now[..., :4], local)+current[:3]
                prior_point = prior[..., 4:]+quat_apply(prior[..., :4], local)+old[:3]
                world = old_root[:3]+(old_rotation[None, None]*prior_point[..., None, :]).sum(-1)
                base = (rotation.T[None, None]*(world-root[:3])[..., None, :]).sum(-1)
                return tangent_material_rms(current_point-base, normals, weights, xp=joint.jnp)
            rms = linearized(s, previous)
            jacobian = torch.func.jacrev if joint.compile_kernels else torch.func.jacfwd
            current_jac, previous_jac = jacobian(linearized, argnums=(0, 1))(s, previous)
            return rms, current_jac, previous_jac

        a = dynamic
        if not hasattr(joint, '_material'):
            joint._material = _batch_kernel(material, joint)
        material_data = joint._material(states[1:], states[:-1], fk[1:], fk[:-1],
            fk_jac[1:], fk_jac[:-1], a['loaded_links'][1:], a['loaded_local'][1:],
            a['loaded_normals'][1:], a['loaded_weights'][1:], joint.root[1:], joint.rotations[1:],
            joint.root[:-1], joint.rotations[:-1])
        return (joint.to_numpy(blocks), tuple(map(joint.to_numpy, material_data)),
            (joint.to_numpy(a['loaded_remaining']), joint.to_numpy(a['loaded_scale'])))


class TorchNewtonBackend:
    array_api = ARRAY_API
    joint_residual_class = TorchJointResidual
    cache_namespace = 'newton_urdf_fk_float32_pilot_v1'

    def __init__(self, *, device='cpu', compile_kernels=False, chunk_size=None):
        chunk_size = (8 if compile_kernels else 64) if chunk_size is None else chunk_size
        if chunk_size < 1:
            raise ValueError('Torch kernel chunk size must be positive')
        self.array_api = TorchArrayAPI(device)
        self.joint_residual_class = partial(TorchJointResidual, array_api=self.array_api,
            compile_kernels=compile_kernels, chunk_size=chunk_size)

    @lru_cache(maxsize=1)
    def load_robot(self, path):
        robot = NewtonRobot(path, device=self.array_api.device)
        return robot, robot.joints.actuated_names, robot.links.names, robot.joints.num_actuated_joints


def assemble_torch_newton_problem(*, device='cpu', compile_kernels=False, chunk_size=None,
                                  _torch_backend=None, **kwargs):
    from motion_edit.generation.trajectory_problem import assemble_trajectory_problem
    cache = kwargs.get('collision_reference_cache_path')
    if cache is not None:
        cache = Path(cache)
        kwargs['collision_reference_cache_path'] = cache.with_name(cache.stem+'.torch-newton-f32'+cache.suffix)
    backend = _torch_backend or TorchNewtonBackend(
        device=device, compile_kernels=compile_kernels, chunk_size=chunk_size)
    problem = assemble_trajectory_problem(**kwargs, _backend=backend)
    if problem.refresh is not None:
        # COAL consumes rigid transforms in double precision. Rounding a fixed
        # source-root rotation to float32 makes it slightly non-orthogonal and
        # can produce invalid distance normals. Keep this immutable coordinate
        # frame exact; Newton FK, residuals and derivatives remain float32.
        joint = problem.joint
        root = np.asarray(problem.context['root_source'], dtype=np.float64)
        rotations = Rotation.from_quat(root[:, [4, 5, 6, 3]]).as_matrix()
        problem.refresh.joint = SimpleNamespace(root=root, rotations=rotations,
            root_dofs=joint.root_dofs, names=joint.names, jnp=ARRAY_API,
            poses=lambda states: joint.to_numpy(joint.poses(states)))
    return problem


def solve_torch_newton_ik(*, output_path, **kwargs):
    started = time.perf_counter()
    problem = assemble_torch_newton_problem(**kwargs)
    return solve_prepared_problem(problem, output_path=output_path, started=started,
        max_nfev=kwargs.get('max_nfev', 25), refinements=kwargs.get('collision_max_refinements', 1))


def solve_prepared_problem(problem, *, output_path, max_nfev=25, refinements=1,
                           started=None, progress_callback=None):
    from motion_edit.generation.continuous_ik import solve_joint_trajectory
    from motion_edit.generation.trajectory_problem import _write_fullbody_joint_result
    started = time.perf_counter() if started is None else started
    problem.context.update(solver_schema=SOLVER_SCHEMA, ik_backend='torch_newton_contact_aware_taskspace',
        kinematics_backend='newton_urdf_fk_preview')
    def progress(row, states):
        if row['kind'] == 'solve_finished':
            print('torch-newton '+json.dumps(row, sort_keys=True), flush=True)
        if progress_callback is not None:
            progress_callback(row, states)
    result = solve_joint_trajectory(problem.joint, problem.rows, problem.initial,
        problem.lower, problem.upper, max_nfev=max_nfev,
        refinements=refinements, refresh=problem.refresh,
        progress=progress, problem_class=TorchFactoredJointProblem)
    if problem.refresh is not None:
        problem.refresh(result.states, problem.rows)
    output = _write_fullbody_joint_result(problem, result, output_path)
    print(json.dumps(dict(output=str(output), backend=SOLVER_SCHEMA,
        wall_seconds=time.perf_counter()-started), sort_keys=True), flush=True)
    return output


def main(argv=None):
    import sys
    from motion_edit.generation.ik_runtime import RejectJax, add_runtime_arguments, resolve_runtime
    sys.meta_path.insert(0, RejectJax())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--taskspace-spec', required=True)
    parser.add_argument('--source-motion')
    parser.add_argument('--out', required=True)
    parser.add_argument('--max-nfev', type=int, default=25)
    parser.add_argument('--q-acceleration-weight', type=float, default=1.)
    parser.add_argument('--collision-similarity-weight', type=float, default=25.)
    parser.add_argument('--collision-max-refinements', type=int, default=1)
    parser.add_argument('--collision-reference-cache')
    parser.add_argument('--historical-reference-only', action='store_true',
        help='Use content-bound archived source weights only; never current contact truth')
    parser.add_argument('--torch-threads', type=int, default=4)
    add_runtime_arguments(parser)
    parser.add_argument('--kernel-chunk-size', type=int, help='Defaults to 8 compiled / 64 eager frames')
    args = parser.parse_args(argv)
    args.device, args.compile_kernels = resolve_runtime(args.device, args.compile_kernels)
    if args.torch_threads < 1:
        parser.error('--torch-threads must be positive')
    torch.set_num_threads(args.torch_threads)
    solve_torch_newton_ik(lte_path=args.taskspace_spec, source_motion_path=args.source_motion,
        output_path=args.out, max_nfev=args.max_nfev,
        q_acceleration_weight=args.q_acceleration_weight,
        collision_similarity_weight=args.collision_similarity_weight,
        collision_max_refinements=args.collision_max_refinements,
        collision_reference_cache_path=args.collision_reference_cache,
        historical_reference_only=args.historical_reference_only,
        device=args.device, compile_kernels=args.compile_kernels, chunk_size=args.kernel_chunk_size)


if __name__ == '__main__':
    main()
