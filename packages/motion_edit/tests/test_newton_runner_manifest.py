from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from holosoma.utils.motion_terrain_manifest import load_motion_terrain_manifest
from motion_edit.physics_retarget.newton_runner import NewtonSubprocessRunner
from somaforge_core import (
    canonical_g1_asset_metadata,
    encode_kinematics_provenance,
    encode_robot_asset_json,
    newton_kinematics_provenance,
    sha256_file,
)
from somaforge_core.contact_schema import encode_contact_force_provenance, newton_contact_provenance


def test_candidate_manifest_binds_canonical_motion_to_pyroki_source(tmp_path: Path) -> None:
    terrain = tmp_path / "terrain.obj"
    terrain.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", encoding="utf-8")
    candidate = tmp_path / "candidate.npz"
    np.savez(candidate, joint_pos=np.zeros((2, 36), dtype=np.float32))
    canonical = tmp_path / "canonical.npz"
    reference = tmp_path / "reference.npz"
    np.savez(reference, joint_pos=np.zeros((2, 36), dtype=np.float32))
    provenance = newton_kinematics_provenance(
        source_path=str(candidate),
        source_sha256=sha256_file(candidate),
        output_fps=50.0,
        body_names=["pelvis"],
    )
    np.savez(
        canonical,
        joint_pos=np.zeros((2, 36), dtype=np.float32),
        robot_asset_json=np.asarray(encode_robot_asset_json()),
        kinematics_provenance_json=np.asarray(encode_kinematics_provenance(provenance)),
    )
    base_manifest = tmp_path / "base_manifest.json"
    base_manifest.write_text(
        json.dumps(
            {
                "motion_files": [
                    {
                        "motion_id": "00",
                        "motion_file": "old.npz",
                        "terrain_id": 7,
                        "reference_motion_file": reference.name,
                        "reference_motion_sha256": sha256_file(reference),
                    }
                ],
                "terrains": [{"terrain_id": 7, "terrain_file": terrain.name}],
            }
        ),
        encoding="utf-8",
    )
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"checkpoint")
    target_force = tmp_path / "target_force.npz"
    np.savez(
        target_force,
        contact_force_part_w=np.zeros((2, 8, 3), dtype=np.float32),
        contact_force_part_mask=np.zeros((2, 8), dtype=bool),
        contact_force_part_order=np.asarray(["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"]),
        contact_force_provenance_json=np.asarray(
            encode_contact_force_provenance(newton_contact_provenance(solver_config={"solver": "mjwarp"}))
        ),
    )
    runner = NewtonSubprocessRunner(
        base_manifest_path=base_manifest,
        target_force_motion_path=target_force,
        motion_id="00",
        checkpoint_path=checkpoint,
        python_executable=Path("/usr/bin/python3"),
        repo_root=Path(__file__).resolve().parents[3],
    )

    payload = runner._candidate_manifest(candidate, canonical)
    output_manifest = tmp_path / "candidate_manifest.json"
    output_manifest.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_motion_terrain_manifest(str(output_manifest))
    entry = loaded["motion_files"][0]

    asset = canonical_g1_asset_metadata()
    assert payload["robot_asset_sha256"] == asset["urdf_sha256"]
    assert entry["motion_file"] == str(canonical)
    assert entry["motion_sha256"] == sha256_file(canonical)
    assert entry["source_file"] == str(candidate)
    assert entry["source_sha256"] == sha256_file(candidate)
    assert entry["reference_motion_file"] == str(reference)
    assert entry["kinematics_backend"] == "isaaclab3_newton_fk"
    assert entry["contact_force_target_file"] == str(target_force)
    assert entry["contact_force_target_sha256"] == sha256_file(target_force)

    conditioned = tmp_path / "conditioned.npz"
    runner._attach_target_force(canonical, conditioned)
    with np.load(conditioned, allow_pickle=False) as data:
        assert data["contact_force_part_w"].shape == (2, 8, 3)
        assert data["contact_force_part_mask"].shape == (2, 8)
        assert "contact_force_provenance_json" in data

    canonicalize = runner._canonicalize_command(candidate=candidate, canonical_dir=tmp_path / "canonical")
    assert "holosoma_joint_pos" in canonicalize
    eval_command = runner._eval_command(
        manifest_path=output_manifest,
        recording_path=tmp_path / "recording.npz",
        frame_count=2,
    )
    assert eval_command[eval_command.index("--recording.config.enabled") + 1] == "True"
    assert eval_command[eval_command.index("--recording.config.record-initial-state") + 1] == "True"
    assert eval_command[eval_command.index("--max-steps") + 1] == "1"
    extract = runner._extract_command(
        canonical_candidate=canonical,
        recording_path=tmp_path / "recording.npz",
        rollout_path=tmp_path / "rollout.npz",
    )
    assert "--forces-only" in extract
