from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _batch_module():
    script = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "generate_contact_aware_batch.py"
    )
    spec = importlib.util.spec_from_file_location(
        "generate_contact_aware_batch",
        script,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_batch_manifest_builds_unique_isolated_jobs(tmp_path) -> None:
    module = _batch_module()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")
    manifest = tmp_path / "plans.json"
    manifest.write_text(
        json.dumps(
            {
                "plans": [
                    {"plan_path": first.name},
                    {"plan_path": second.name, "output": "custom.npz"},
                ]
            }
        ),
        encoding="utf-8",
    )

    jobs = module._manifest_jobs(
        manifest,
        output_dir=tmp_path / "output",
        work_root=tmp_path / "work",
        default_basis=None,
    )

    assert [job.output.name for job in jobs] == [
        "first.npz",
        "custom.npz",
    ]
    assert jobs[0].work_dir != jobs[1].work_dir
    assert jobs[0].log != jobs[1].log


def test_batch_manifest_rejects_duplicate_outputs(tmp_path) -> None:
    module = _batch_module()
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")
    manifest = tmp_path / "plans.json"
    manifest.write_text(
        json.dumps(
            [
                {"plan_path": first.name, "output": "same.npz"},
                {"plan_path": second.name, "output": "same.npz"},
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate batch output"):
        module._manifest_jobs(
            manifest,
            output_dir=tmp_path / "output",
            work_root=tmp_path / "work",
            default_basis=None,
        )


def test_persistent_worker_queue_routes_socket_to_each_job(
    tmp_path,
    monkeypatch,
) -> None:
    module = _batch_module()
    plan = tmp_path / "plan.json"
    plan.write_text("{}", encoding="utf-8")
    job = module.BatchJob(
        plan=plan,
        output=tmp_path / "output.npz",
        work_dir=tmp_path / "work",
        log=tmp_path / "generation.log",
        semantic_proxy_basis=None,
    )
    calls = []

    def fake_run_job(job, *, command, environment):
        calls.append((job, command, environment))
        return job, 1.0

    monkeypatch.setattr(module, "_run_job", fake_run_job)
    result = module._run_worker_queue(
        [job],
        worker_name="@worker-test",
        commands={job: ["generate"]},
        environment={"BASE": "1"},
    )

    assert result == [(job, 1.0)]
    assert calls[0][2]["SOMAFORGE_IK_WORKER_SOCKET"] == "@worker-test"
    assert calls[0][2]["BASE"] == "1"


def test_batch_environment_uses_one_source_topology_cache(tmp_path) -> None:
    module = _batch_module()
    work_root = tmp_path / "batch_work"

    environment = module._batch_environment(work_root)

    assert environment["SOMAFORGE_LAPLACIAN_TOPOLOGY_CACHE"] == str(
        work_root / "source_laplacian_topology.npz"
    )


@pytest.mark.parametrize("prefix", [False, True])
def test_persistent_worker_selects_ik_environment_and_isolates_imports(tmp_path, monkeypatch, prefix) -> None:
    module = _batch_module()
    calls = []
    conda = str(tmp_path / "miniforge" / "bin" / "conda")
    target = str(tmp_path / "ik prefix") if prefix else "legacy_ik"
    expected_selector = ["--prefix", target] if prefix else ["-n", target]

    class Process:
        def poll(self):
            return None

    monkeypatch.setattr(module.subprocess, "Popen", lambda cmd, **kwargs: calls.append((cmd, kwargs)) or Process())
    monkeypatch.setattr(module, "_worker_request", lambda *args: {"ok": True})
    _, _, log = module._start_ik_worker(
        index=0, work_root=tmp_path, ik_conda_env=target,
        environment={"CONDA_DEFAULT_ENV": "main", "SOMAFORGE_CONDA_EXE": conda,
                     "PYTHONPATH": "/main/IsaacLab:/old/site-packages", "PYTHONHOME": "/old/python",
                     "SOMAFORGE_ENV_PROFILE": "main", "SOMAFORGE_ENV_PREFIX": str(tmp_path / "main"),
                     "SOMAFORGE_NEWTON_ENV": str(tmp_path / "main")},
    )
    log.close()
    command, kwargs = calls[0]
    assert command[:6] == [conda, "run", "--no-capture-output", *expected_selector, "python"]
    assert "--worker-socket" in command
    assert "/main/IsaacLab" not in kwargs["env"]["PYTHONPATH"]
    assert "/old/site-packages" not in kwargs["env"]["PYTHONPATH"]
    assert "PYTHONHOME" not in kwargs["env"]
    assert kwargs["env"]["SOMAFORGE_ENV_PROFILE"] == "main"
    assert kwargs["env"]["SOMAFORGE_NEWTON_ENV"] == str(tmp_path / "main")
