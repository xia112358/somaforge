"""Default persistent Torch/Newton worker using the editor's IK socket protocol.

Only immutable kernels and native models are reused. Every request rebuilds its
task, validates evidence hashes, starts at its own initial state, and re-queries
geometry. No accepted poses, witnesses, multipliers or contact labels are reused.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
import traceback

import torch

from motion_edit.generation.torch_newton_ik import (
    TorchNewtonBackend, assemble_torch_newton_problem, solve_prepared_problem,
)


class TorchNewtonWorker:
    def __init__(self, *, device='cpu', compile_kernels=False, chunk_size=None, cache_size=4,
                 historical_reference_only=False):
        if cache_size < 1:
            raise ValueError('Worker kernel cache must be positive')
        self.backend = TorchNewtonBackend(device=device, compile_kernels=compile_kernels,
            chunk_size=chunk_size)
        self.cache_size, self.kernels = cache_size, OrderedDict()
        self.historical_reference_only = historical_reference_only
        self.last_report = None

    def prepare(self, **kwargs):
        kwargs.setdefault('historical_reference_only', self.historical_reference_only)
        # Task metadata includes the separately verified material-evidence hashes.
        # Include every assembly option; kernels may capture weights and indices.
        options = dict(kwargs)
        for name in ('lte_path', 'source_motion_path'):
            if options.get(name) is not None:
                path = Path(options[name]).expanduser().resolve()
                options[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        key = json.dumps(options, sort_keys=True, default=str)
        problem = assemble_torch_newton_problem(**kwargs, _torch_backend=self.backend)
        cached = self.kernels.get(key)
        if cached is not None:
            self.kernels.move_to_end(key)
            for name, value in cached.items():
                setattr(problem.joint, name, value)
        return problem, key, cached is not None

    def solve(self, *, output_path, **kwargs):
        started = time.perf_counter()
        problem, key, hit = self.prepare(**kwargs)
        assembly = time.perf_counter()-started
        rows = []
        output = solve_prepared_problem(problem, output_path=output_path, started=started,
            max_nfev=kwargs.get('max_nfev', 25), refinements=kwargs.get('collision_max_refinements', 1),
            progress_callback=lambda row, states: rows.append(row) if row['kind']=='solve_finished' else None)
        self.kernels[key] = {name:getattr(problem.joint, name) for name in
            ('_values', '_jacobian', '_material') if hasattr(problem.joint, name)}
        self.kernels.move_to_end(key)
        while len(self.kernels) > self.cache_size:
            self.kernels.popitem(last=False)
        self.last_report = dict(wall_seconds=time.perf_counter()-started,
            assembly_seconds=assembly, kernel_cache_hit=hit, iterations=rows,
            device=str(self.backend.array_api.device),
            imported_jax_or_pyroki=any(name.split('.')[0] in ('jax', 'jaxlib', 'pyroki') for name in sys.modules),
            cuda_peak_allocated_mib=(torch.cuda.max_memory_allocated(self.backend.array_api.device)/2**20
                if self.backend.array_api.device.type == 'cuda' else None))
        return output


def serve_worker(name, worker):
    address = '\0'+name[1:] if name.startswith('@') else name
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(address)
        server.listen(8)
        while True:
            connection, _ = server.accept()
            with connection, connection.makefile('r', encoding='utf-8') as request_stream:
                request = json.loads(request_stream.readline())
                shutdown = bool(request.get('shutdown'))
                try:
                    if request.get('ping') or shutdown:
                        from .ik_runtime import IK_BACKEND
                        response = dict(ok=True, ik_backend=IK_BACKEND,
                            device=str(worker.backend.array_api.device),
                            **({'shutdown':True} if shutdown else {'pong':True}))
                    elif request.get('op') == 'canonicalize':
                        from .newton_direct_fk import canonicalize_motion_with_direct_newton_fk
                        result = canonicalize_motion_with_direct_newton_fk(**request['kwargs'])
                        response = dict(ok=True, canonical=dict(output_path=str(result.output_path),
                            body_names=list(result.body_names), joint_names=list(result.joint_names),
                            frame_count=result.frame_count, backend_metadata=result.backend_metadata))
                    else:
                        output = worker.solve(**request['kwargs'])
                        response = dict(ok=True, output=str(output), output_path=str(output), metrics=worker.last_report)
                except Exception:
                    response = dict(ok=False, traceback=traceback.format_exc())
                connection.sendall((json.dumps(response)+'\n').encode())
                if shutdown:
                    return


def main(argv=None):
    from motion_edit.generation.ik_runtime import RejectJax, add_runtime_arguments, resolve_runtime
    sys.meta_path.insert(0, RejectJax())
    # Canonicalization handled here must not route recursively to a socket
    # inherited from the launching editor or another generation worker.
    os.environ.pop('SOMAFORGE_IK_WORKER_SOCKET', None)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-socket', required=True)
    add_runtime_arguments(parser)
    parser.add_argument('--historical-reference-only', action='store_true',
        help='Archived source optimization weights only; never current contact truth')
    parser.add_argument('--kernel-chunk-size', type=int, help='Defaults to 8 compiled / 64 eager frames')
    parser.add_argument('--torch-threads', type=int, default=int(os.environ.get('OMP_NUM_THREADS', '4')))
    parser.add_argument('--cuda-memory-fraction', type=float, default=.2)
    args = parser.parse_args(argv)
    args.device, args.compile_kernels = resolve_runtime(args.device, args.compile_kernels)
    if args.torch_threads < 1 or not 0 < args.cuda_memory_fraction <= 1:
        parser.error('Positive threads and CUDA memory fraction in (0,1] required')
    torch.set_num_threads(args.torch_threads)
    if torch.device(args.device).type == 'cuda':
        torch.cuda.set_device(args.device)
        torch.cuda.set_per_process_memory_fraction(args.cuda_memory_fraction)
    serve_worker(args.worker_socket, TorchNewtonWorker(device=args.device,
        compile_kernels=args.compile_kernels, chunk_size=args.kernel_chunk_size,
        historical_reference_only=args.historical_reference_only))


if __name__ == '__main__':
    main()
