from __future__ import annotations

from pathlib import Path

import numpy as np

from motion_edit.contact.plans import ContactEditPlan
from motion_edit.generation.contact_aware_preview import _resolve_layers_root, merge_pyroki_preview_motion


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
