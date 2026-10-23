"""Generate a manifest of complete edits with explicit persistent IK workers.

The manifest contains ``jobs`` with the same keyword arguments as the selected
IK function (``lte_path``, ``source_motion_path``, ``output_path``, solver options).
All jobs use the maintained Torch/Newton backend.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid


def worker_request(name, request, *, timeout=3600.):
    address = '\0'+name[1:] if name.startswith('@') else name
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(address)
        client.sendall((json.dumps(request)+'\n').encode())
        with client.makefile('r', encoding='utf-8') as stream:
            result = json.loads(stream.readline())
    if not result.get('ok'):
        raise RuntimeError(result.get('traceback', str(result)))
    return result


def run_batch(manifest, output_dir, *, workers=1, device='cpu', compile_kernels=False,
              chunk_size=None, threads=4, python=None):
    chunk_size = (8 if compile_kernels else 64) if chunk_size is None else chunk_size
    if workers < 1 or threads < 1 or chunk_size < 1:
        raise ValueError('Positive workers, threads and chunk size required')
    data = json.loads(Path(manifest).read_text())
    jobs = data['jobs']
    if not jobs:
        raise ValueError('Batch requires at least one job')
    outputs = [str(Path(job['output_path']).resolve()) for job in jobs]
    if len(set(outputs)) != len(outputs):
        raise ValueError('Batch output paths must be unique')
    if any(Path(path).exists() for path in outputs):
        raise FileExistsError('Batch preserves existing outputs; choose fresh output paths')
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        OMP_NUM_THREADS=str(threads), NUMEXPR_NUM_THREADS=str(threads),
        TORCHINDUCTOR_COMPILE_THREADS='2', PYTHONDONTWRITEBYTECODE='1')
    pool = []
    cpus = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else []
    started = time.perf_counter()
    try:
        for index in range(min(workers, len(jobs))):
            name = '@somaforge-torch-'+uuid.uuid4().hex
            command = [str(python or sys.executable), '-m',
                'motion_edit.generation.torch_newton_worker', '--worker-socket', name,
                '--device', device, '--torch-threads', str(threads), '--kernel-chunk-size', str(chunk_size),
                '--compile-kernels' if compile_kernels else '--no-compile-kernels']
            log = (directory/f'worker_{index}.log').open('x')
            process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
            pool.append((name, process, log))
            if len(cpus) >= threads*min(workers, len(jobs)):
                os.sched_setaffinity(process.pid, cpus[index*threads:(index+1)*threads])
        for name, process, log in pool:
            deadline = time.monotonic()+120.
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f'Worker exited; see {log.name}')
                try:
                    worker_request(name, dict(ping=True), timeout=1.)
                    break
                except (OSError, ValueError):
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f'Worker did not become ready; see {log.name}')
                    time.sleep(.1)
        ready = time.perf_counter()

        def queue(index):
            results = []
            for job_index in range(index, len(jobs), len(pool)):
                began = time.perf_counter()
                response = worker_request(pool[index][0], dict(kwargs=jobs[job_index]))
                result = dict(job_index=job_index, worker=index, output_path=outputs[job_index],
                    wall_seconds=time.perf_counter()-began,
                    completion_seconds=time.perf_counter()-ready, metrics=response.get('metrics'))
                with (directory/f'job_{job_index}.json').open('x') as stream:
                    json.dump(result, stream, indent=2)
                print(json.dumps({k:v for k,v in result.items() if k!='metrics'}), flush=True)
                results.append(result)
            return results

        with ThreadPoolExecutor(max_workers=len(pool)) as executor:
            groups = list(executor.map(queue, range(len(pool))))
        rows = sorted([row for group in groups for row in group], key=lambda row:row['job_index'])
        finished = time.perf_counter()
        report = dict(backend='torch', device=device, compile_kernels=compile_kernels,
            workers=len(pool), threads_per_worker=threads, blas_threads=1,
            cpu_affinity_per_worker=([cpus[i*threads:(i+1)*threads] for i in range(len(pool))]
                if len(cpus) >= threads*len(pool) else None),
            startup_seconds=ready-started, generation_wall_seconds=finished-ready,
            total_seconds=finished-started, trajectories_per_minute=60*len(jobs)/(finished-ready),
            warm_state_definition='later jobs in the same worker; includes task assembly and validation',
            jobs=rows)
        with (directory/'batch_report.json').open('x') as stream:
            json.dump(report, stream, indent=2)
        return report
    finally:
        for name, process, log in pool:
            if process.poll() is None:
                try:
                    worker_request(name, dict(shutdown=True), timeout=5.)
                except (OSError, RuntimeError, ValueError):
                    process.terminate()  # Only this invocation's dedicated IK worker.
                try:
                    process.wait(timeout=10.)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=10.)
            log.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-manifest', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--compile-kernels', action='store_true')
    parser.add_argument('--kernel-chunk-size', type=int, help='Defaults to 8 compiled / 64 eager frames')
    parser.add_argument('--torch-threads', type=int, default=4)
    parser.add_argument('--worker-python', type=Path)
    args = parser.parse_args(argv)
    report = run_batch(args.batch_manifest, args.output_dir, workers=args.workers,
        device=args.device, compile_kernels=args.compile_kernels,
        chunk_size=args.kernel_chunk_size, threads=args.torch_threads,
        python=args.worker_python)
    print(json.dumps({k:v for k,v in report.items() if k!='jobs'}), flush=True)


if __name__ == '__main__':
    main()
