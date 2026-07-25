from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from motion_edit.contact.plans import ContactEditPlan
from motion_edit.generation.contact_aware_preview import (
    _resolve_layers_root,
    _run_pyroki_preview_subprocess,
    merge_pyroki_preview_motion,
)
from motion_edit.generation.lte_fullbody import _run_fullbody_ik_subprocess


def test_contact_aware_ik_reuses_current_conda_interpreter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "env_somaforge")
    monkeypatch.setattr(
        "motion_edit.generation.contact_aware_preview.subprocess.run",
        lambda cmd, **kwargs: calls.append((cmd, kwargs)),
    )

    _run_pyroki_preview_subprocess(
        taskspace_path=tmp_path / "taskspace.npz",
        source_motion_path=tmp_path / "source.npz",
        ik_output_path=tmp_path / "ik.npz",
        ik_script=tmp_path / "ik.py",
        ik_conda_env="env_somaforge",
        ik_max_nfev=None,
        ik_collision_similarity_weight=50.0,
        ik_collision_max_refinements=2,
    )

    assert calls[0][0][0] == sys.executable
    assert "conda" not in calls[0][0]
    assert calls[0][0][-4:] == [
        "--collision-similarity-weight",
        "50.0",
        "--collision-max-refinements",
        "2",
    ]
    assert calls[0][1]["check"] is True
    python_path = calls[0][1]["env"]["PYTHONPATH"].split(":")
    assert python_path[0].endswith("/packages/motion_edit")
    assert python_path[1].endswith("/packages/somaforge_core")
    assert all(Path(item).is_absolute() for item in python_path[:2])


def test_legacy_ik_reuses_current_conda_interpreter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "/opt/conda/envs/env_somaforge")
    monkeypatch.setattr(
        "motion_edit.generation.lte_fullbody.subprocess.run",
        lambda cmd, **kwargs: calls.append(cmd),
    )

    _run_fullbody_ik_subprocess(
        lte_path=tmp_path / "lte.npz",
        ik_output_path=tmp_path / "ik.npz",
        lte_repo_root=None,
        ik_script=tmp_path / "ik.py",
        ik_conda_env="env_somaforge",
        ik_max_nfev=None,
    )

    assert calls[0][0] == sys.executable
    assert "conda" not in calls[0]


def test_resolve_layers_root_uses_somaforge_runtime_for_isolated_worktree(tmp_path, monkeypatch) -> None:
    repo_root = tmp_path / "somaforge"
    runtime_layers = repo_root / "runtime" / "current" / "motion_edit" / "data" / "layers"
    contact_layer = "contact/task_variants/climb_00_height_1p100_source"
    (runtime_layers / contact_layer).mkdir(parents=True)
    monkeypatch.setenv("SOMAFORGE_ROOT", str(repo_root))

    assert _resolve_layers_root(None, contact_layer=contact_layer) == runtime_layers


def test_merge_pyroki_preview_overwrites_kinematics_and_drops_stale_provenance() -> None:
    plan = ContactEditPlan(
        plan_id="plan0",
        source_motion_id="motion0",
        source_motion_path="/tmp/source.npz",
        source_contact_layer="contact/source",
        status="validated",
        edits=[],
    )
    source = {
        "fps": np.asarray(50.0),
        "joint_pos": np.zeros((2, 9), dtype=np.float32),
        "joint_vel": np.zeros((2, 8), dtype=np.float32),
        "body_names": np.asarray(["pelvis"], dtype=object),
        "body_pos_w": np.zeros((2, 1, 3), dtype=np.float32),
        "body_quat_w": np.asarray([[[1.0, 0.0, 0.0, 0.0]]] * 2, dtype=np.float32),
        "body_lin_vel_w": np.zeros((2, 1, 3), dtype=np.float32),
        "body_ang_vel_w": np.zeros((2, 1, 3), dtype=np.float32),
        "joint_names": np.asarray(["j0", "j1"], dtype=object),
        "kinematics_provenance_json": np.asarray("stale"),
        "contact_force_provenance_json": np.asarray("stale"),
        "raw_contact_count": np.asarray([1, 1]),
        "contact_force_part_w": np.ones((2, 1, 3), dtype=np.float32),
    }
    ik = {
        "fps": np.asarray(50.0),
        "joint_pos": np.ones((2, 9), dtype=np.float32),
        "joint_vel": np.ones((2, 8), dtype=np.float32),
        "joint_names": np.asarray(["j0", "j1"], dtype=object),
        "body_names": np.asarray(["pelvis", "link1"], dtype=object),
        "body_pos_w": np.ones((2, 2, 3), dtype=np.float32),
        "body_quat_w": np.asarray([[[1.0, 0.0, 0.0, 0.0]] * 2] * 2, dtype=np.float32),
        "body_lin_vel_w": np.ones((2, 2, 3), dtype=np.float32),
        "body_ang_vel_w": np.ones((2, 2, 3), dtype=np.float32),
        "newton_canonicalization_required": np.asarray(True),
        "ik_backend": np.asarray("pyroki_contact_aware_taskspace"),
    }
    generated = merge_pyroki_preview_motion(
        source_motion=source,
        ik_motion=ik,
        plan=plan,
        proxy_metadata={},
        taskspace_path=Path("/tmp/spec.npz"),
        ik_output_path=Path("/tmp/ik.npz"),
        binding_summary={"bound_patch_count": 1},
    )
    assert "kinematics_provenance_json" not in generated
    assert "contact_force_provenance_json" not in generated
    assert "raw_contact_count" not in generated
    assert "contact_force_part_w" not in generated
    assert generated["joint_vel"].shape == (2, 8)
    assert generated["body_pos_w"].shape == (2, 2, 3)
    assert bool(generated["newton_canonicalization_required"].item())
