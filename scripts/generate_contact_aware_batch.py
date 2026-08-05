#!/usr/bin/env python3
"""Generate contact-aware motions with bounded process parallelism."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BatchJob:
    plan: Path
    output: Path
    work_dir: Path
    log: Path
    semantic_proxy_basis: Path | None


def _manifest_jobs(
    manifest_path: Path,
    *,
    output_dir: Path,
    work_root: Path,
    default_basis: Path | None,
) -> list[BatchJob]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_entries: Any = (
        payload.get("plans")
        if isinstance(payload, dict)
        else payload
    )
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("batch manifest must contain a non-empty plan list")
    jobs: list[BatchJob] = []
    outputs: set[Path] = set()
    for index, entry in enumerate(raw_entries):
        if isinstance(entry, str):
            raw_plan = entry
            raw_output = None
            raw_basis = None
        elif isinstance(entry, dict):
            raw_plan = entry.get("plan_path") or entry.get("plan")
            raw_output = entry.get("output_path") or entry.get("output")
            raw_basis = entry.get("semantic_proxy_basis")
        else:
            raise ValueError(f"manifest entry {index} must be a path or object")
        if not raw_plan:
            raise ValueError(f"manifest entry {index} has no plan_path")
        plan = Path(str(raw_plan)).expanduser()
        if not plan.is_absolute():
            plan = manifest_path.parent / plan
        plan = plan.resolve()
        if not plan.is_file():
            raise FileNotFoundError(plan)
        output = (
            Path(str(raw_output)).expanduser()
            if raw_output
            else output_dir / f"{plan.stem}.npz"
        )
        if not output.is_absolute():
            output = output_dir / output
        output = output.resolve()
        if output in outputs:
            raise ValueError(f"duplicate batch output: {output}")
        outputs.add(output)
        basis = Path(str(raw_basis)).expanduser() if raw_basis else default_basis
        if basis is not None:
            basis = basis.resolve()
            if not basis.is_file():
                raise FileNotFoundError(basis)
        job_root = (work_root / output.stem).resolve()
        jobs.append(
            BatchJob(
                plan=plan,
                output=output,
                work_dir=job_root / "work",
                log=job_root / "generation.log",
                semantic_proxy_basis=basis,
            )
        )
    return jobs


def _job_command(
    job: BatchJob,
    *,
    generator: Path,
    collision_reference_cache: Path,
    ik_conda_env: str,
    newton_device: str,
    overwrite: bool,
) -> list[str]:
    command = [
        sys.executable,
        str(generator),
        "--plan",
        str(job.plan),
        "--output",
        str(job.output),
        "--intermediate-dir",
        str(job.work_dir),
        "--ik-conda-env",
        ik_conda_env,
        "--newton-device",
        newton_device,
        "--ik-collision-reference-cache",
        str(collision_reference_cache),
    ]
    if job.semantic_proxy_basis is not None:
        command.extend(
            ["--semantic-proxy-basis", str(job.semantic_proxy_basis)]
        )
    if overwrite:
        command.append("--overwrite")
    return command


def _run_job(
    job: BatchJob,
    *,
    command: list[str],
    environment: dict[str, str],
) -> tuple[BatchJob, float]:
    import time

    job.work_dir.mkdir(parents=True, exist_ok=True)
    job.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with job.log.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(
            command,
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    elapsed = time.perf_counter() - started
    if completed.returncode != 0:
        raise RuntimeError(
            f"{job.plan.name} failed with exit code {completed.returncode}; "
            f"see {job.log}"
        )
    if not job.output.is_file():
        raise FileNotFoundError(job.output)
    return job, elapsed


def _worker_request(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    address = "\0" + name[1:] if name.startswith("@") else name
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(address)
        stream = client.makefile("rw", encoding="utf-8")
        stream.write(json.dumps(payload) + "\n")
        stream.flush()
        return dict(json.loads(stream.readline()))


def _start_ik_worker(
    *,
    index: int,
    environment: dict[str, str],
    work_root: Path,
) -> tuple[str, subprocess.Popen[str], Any]:
    name = f"@somaforge-ik-{os.getpid()}-{index}"
    script = (
        Path(__file__).resolve().parents[1]
        / "packages/motion_edit/motion_edit/generation/pyroki_fullbody_ik.py"
    )
    log_path = work_root / f"ik_worker_{index}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_stream = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, str(script), "--worker-socket", name],
        env=environment,
        stdout=log_stream,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for _ in range(200):
        if process.poll() is not None:
            log_stream.flush()
            raise RuntimeError(
                f"IK worker {index} exited during startup; see {log_path}"
            )
        try:
            response = _worker_request(name, {"ping": True})
        except OSError:
            time.sleep(0.05)
            continue
        if response.get("ok"):
            return name, process, log_stream
    raise TimeoutError(f"IK worker {index} did not become ready")


def _run_worker_queue(
    jobs: list[BatchJob],
    *,
    worker_name: str,
    commands: dict[BatchJob, list[str]],
    environment: dict[str, str],
) -> list[tuple[BatchJob, float]]:
    worker_environment = dict(environment)
    worker_environment["SOMAFORGE_IK_WORKER_SOCKET"] = worker_name
    return [
        _run_job(
            job,
            command=commands[job],
            environment=worker_environment,
        )
        for job in jobs
    ]


def _batch_environment(work_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment.setdefault("JAX_PLATFORMS", "cpu")
    environment["SOMAFORGE_LAPLACIAN_TOPOLOGY_CACHE"] = str(
        work_root / "source_laplacian_topology.npz"
    )
    return environment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--semantic-proxy-basis", type=Path, default=None)
    parser.add_argument("--collision-reference-cache", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--ik-conda-env", default="env_somaforge")
    parser.add_argument("--newton-device", default="cpu")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be positive")

    manifest = args.plan_manifest.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    work_root = args.work_dir.expanduser().resolve()
    default_basis = (
        args.semantic_proxy_basis.expanduser().resolve()
        if args.semantic_proxy_basis is not None
        else None
    )
    cache = (
        args.collision_reference_cache.expanduser().resolve()
        if args.collision_reference_cache is not None
        else work_root / "source_collision_reference.npz"
    )
    jobs = _manifest_jobs(
        manifest,
        output_dir=output_dir,
        work_root=work_root,
        default_basis=default_basis,
    )
    generator = Path(__file__).with_name(
        "generate_contact_aware_edited_motion.py"
    ).resolve()
    environment = _batch_environment(work_root)
    commands = {
        job: _job_command(
            job,
            generator=generator,
            collision_reference_cache=cache,
            ik_conda_env=args.ik_conda_env,
            newton_device=args.newton_device,
            overwrite=args.overwrite,
        )
        for job in jobs
    }
    failures: list[str] = []
    pending = list(jobs)
    if args.workers > 1:
        if not cache.is_file() and pending:
            warmup = pending.pop(0)
            try:
                _, elapsed = _run_job(
                    warmup,
                    command=commands[warmup],
                    environment=environment,
                )
            except Exception as exc:
                raise RuntimeError(
                    "collision-reference cache warmup failed: "
                    f"{exc}"
                ) from exc
            print(
                f"generated {warmup.output} in {elapsed:.2f}s "
                f"log={warmup.log} cache_warmup=true"
            )
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    _run_job,
                    job,
                    command=commands[job],
                    environment=environment,
                ): job
                for job in pending
            }
            for future in as_completed(futures):
                job = futures[future]
                try:
                    _, elapsed = future.result()
                except Exception as exc:
                    failures.append(str(exc))
                    print(
                        f"failed {job.plan.name}: {exc}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"generated {job.output} in {elapsed:.2f}s "
                        f"log={job.log}"
                    )
        if failures:
            raise RuntimeError(
                f"{len(failures)}/{len(jobs)} batch jobs failed"
            )
        return
    workers: list[tuple[str, subprocess.Popen[str], Any]] = []
    try:
        workers = [
            _start_ik_worker(
                index=index,
                environment=environment,
                work_root=work_root,
            )
            for index in range(min(args.workers, len(jobs)))
        ]
        if not cache.is_file() and pending:
            warmup = pending.pop(0)
            warm_environment = dict(environment)
            warm_environment["SOMAFORGE_IK_WORKER_SOCKET"] = workers[0][0]
            try:
                _, elapsed = _run_job(
                    warmup,
                    command=commands[warmup],
                    environment=warm_environment,
                )
            except Exception as exc:
                raise RuntimeError(
                    "collision-reference cache warmup failed: "
                    f"{exc}"
                ) from exc
            print(
                f"generated {warmup.output} in {elapsed:.2f}s "
                f"log={warmup.log} cache_warmup=true"
            )
        queues = [[] for _ in workers]
        for index, job in enumerate(pending):
            queues[index % len(workers)].append(job)
        with ThreadPoolExecutor(max_workers=len(workers)) as executor:
            futures = {
                executor.submit(
                    _run_worker_queue,
                    queue,
                    worker_name=workers[index][0],
                    commands=commands,
                    environment=environment,
                ): queue
                for index, queue in enumerate(queues)
                if queue
            }
            for future in as_completed(futures):
                queue = futures[future]
                try:
                    results = future.result()
                except Exception as exc:
                    failures.append(str(exc))
                    print(
                        f"failed worker queue {[job.plan.name for job in queue]}: "
                        f"{exc}",
                        file=sys.stderr,
                    )
                else:
                    for job, elapsed in results:
                        print(
                            f"generated {job.output} in {elapsed:.2f}s "
                            f"log={job.log}"
                        )
    finally:
        for name, process, log_stream in workers:
            try:
                _worker_request(name, {"shutdown": True})
            except OSError:
                pass
            try:
                process.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10.0)
            log_stream.close()
    if failures:
        raise RuntimeError(
            f"{len(failures)}/{len(jobs)} batch jobs failed"
        )


if __name__ == "__main__":
    main()
