from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from somaforge_core import (
    G1_SPHEREHAND_USD_BUNDLE_SHA256,
    canonical_g1_source_metadata,
    decode_kinematics_provenance,
    decode_robot_asset_json,
    sha256_file,
)
from somaforge_core.contact_schema import decode_contact_force_provenance

from .schema import PhysicsRollout


class NewtonSubprocessRunner:
    """Run WBT tracking and canonical force extraction in the Newton environment."""

    def __init__(
        self,
        *,
        base_manifest_path: str | Path,
        target_force_motion_path: str | Path,
        motion_id: str | int,
        checkpoint_path: str | Path,
        python_executable: str | Path,
        repo_root: str | Path,
        parallel_envs: int = 16,
        device: str = "cuda:0",
        output_fps: float = 50.0,
    ) -> None:
        self.base_manifest_path = Path(base_manifest_path).expanduser().resolve()
        self.target_force_motion_path = Path(target_force_motion_path).expanduser().resolve()
        self.motion_id = str(motion_id)
        self.checkpoint_path = Path(checkpoint_path).expanduser().resolve()
        self.python_executable = str(Path(python_executable).expanduser().resolve())
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.parallel_envs = int(parallel_envs)
        self.device = str(device)
        self.output_fps = float(output_fps)
        if self.parallel_envs < 1:
            raise ValueError("parallel_envs must be positive")
        if not np.isfinite(self.output_fps) or self.output_fps <= 0.0:
            raise ValueError("output_fps must be finite and positive")
        if not self.base_manifest_path.is_file():
            raise FileNotFoundError(self.base_manifest_path)
        if not self.target_force_motion_path.is_file():
            raise FileNotFoundError(self.target_force_motion_path)
        if not self.checkpoint_path.is_file():
            raise FileNotFoundError(self.checkpoint_path)

    def run(self, *, motion_path: Path, iteration: int, output_dir: Path) -> PhysicsRollout:
        candidate = Path(motion_path).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        output_dir.mkdir(parents=True, exist_ok=True)
        canonical_dir = output_dir / "canonical"
        canonical_candidate = canonical_dir / candidate.name
        conditioned_candidate = canonical_dir / f"{candidate.stem}.force_target.npz"
        manifest_path = output_dir / "newton_candidate_manifest.json"
        recording_path = output_dir / "newton_eval_recording.npz"
        rollout_path = output_dir / "newton_rollout_ref.npz"
        self._run(self._canonicalize_command(candidate=candidate, canonical_dir=canonical_dir))
        if not canonical_candidate.is_file():
            raise RuntimeError(f"Newton canonicalizer did not produce {canonical_candidate}")
        self._attach_target_force(canonical_candidate, conditioned_candidate)
        manifest = self._candidate_manifest(candidate, conditioned_candidate)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with np.load(conditioned_candidate, allow_pickle=False) as data:
            frame_count = int(data["joint_pos"].shape[0])

        self._run(
            self._eval_command(
                manifest_path=manifest_path,
                recording_path=recording_path,
                frame_count=frame_count,
            )
        )
        if not recording_path.is_file():
            raise RuntimeError(f"Newton evaluation did not produce recording: {recording_path}")
        self._run(
            self._extract_command(
                canonical_candidate=conditioned_candidate,
                recording_path=recording_path,
                rollout_path=rollout_path,
            )
        )
        return load_newton_rollout(
            rollout_path,
            iteration=iteration,
            python_executable=self.python_executable,
        )

    def _attach_target_force(self, canonical_candidate: Path, output_path: Path) -> None:
        """Condition the tracking policy on the requested Newton force reference."""

        with np.load(canonical_candidate, allow_pickle=False) as candidate_data:
            arrays = {name: np.asarray(candidate_data[name]) for name in candidate_data.files}
        with np.load(self.target_force_motion_path, allow_pickle=False) as target_data:
            decode_contact_force_provenance(
                target_data.get("contact_force_provenance_json"),
                context=f"force target {self.target_force_motion_path}",
                require_newton=True,
            )
            required = (
                "contact_force_part_w",
                "contact_force_part_mask",
                "contact_force_part_order",
                "contact_force_provenance_json",
            )
            missing = [name for name in required if name not in target_data]
            if missing:
                raise KeyError(f"Force target is missing required arrays: {missing}")
            frame_count = int(arrays["joint_pos"].shape[0])
            target_force = np.asarray(target_data["contact_force_part_w"])
            target_mask = np.asarray(target_data["contact_force_part_mask"])
            if target_force.shape != (frame_count, 8, 3):
                raise ValueError(
                    f"Force target must have shape ({frame_count}, 8, 3), got {target_force.shape}"
                )
            if target_mask.shape != (frame_count, 8):
                raise ValueError(f"Force target mask must have shape ({frame_count}, 8), got {target_mask.shape}")
            for name in required:
                arrays[name] = np.asarray(target_data[name])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(output_path, **arrays)

    def _canonicalize_command(self, *, candidate: Path, canonical_dir: Path) -> list[str]:
        return [
            self.python_executable,
            str(self.repo_root / "scripts/canonicalize_omniretarget_newton.py"),
            str(candidate),
            "--output-dir",
            str(canonical_dir),
            "--input-format",
            "holosoma_joint_pos",
            "--output-fps",
            str(self.output_fps),
            "--batch-size",
            "1",
            "--overwrite",
            "--headless",
            "--device",
            self.device,
        ]

    def _eval_command(self, *, manifest_path: Path, recording_path: Path, frame_count: int) -> list[str]:
        return [
            self.python_executable,
            "-m",
            "holosoma.eval_agent",
            "termination:g1-29dof-wbt",
            "--headless",
            "--device",
            self.device,
            "--checkpoint",
            str(self.checkpoint_path),
            "--recording.config.enabled",
            "True",
            "--recording.config.record-initial-state",
            "True",
            "--recording.config.env-id",
            str(-1 if self.parallel_envs > 1 else 0),
            "--recording.config.output-path",
            str(recording_path),
            "--num-envs",
            str(self.parallel_envs),
            "--max-steps",
            str(max(frame_count - 1, 1)),
            "--export-onnx",
            "False",
            "--command.setup-terms.motion-command.params.motion-config.motion-manifest",
            str(manifest_path),
            "--command.setup-terms.motion-command.params.motion-config.start-at-timestep-zero-prob",
            "1.0",
            "--command.setup-terms.motion-command.params.motion-config.freeze-at-timestep-zero-prob",
            "0.0",
            "--command.setup-terms.motion-command.params.motion-config.noise-to-initial-pose.overall-noise-scale",
            "0.0",
            "--terrain.terrain-term.motion-matched-manifest",
            str(manifest_path),
        ]

    def _extract_command(
        self,
        *,
        canonical_candidate: Path,
        recording_path: Path,
        rollout_path: Path,
    ) -> list[str]:
        return [
            self.python_executable,
            str(self.repo_root / "scripts/extract_rollout_ref_contact_force_demo.py"),
            "--motion",
            str(canonical_candidate),
            "--recording",
            str(recording_path),
            "--output",
            str(rollout_path),
            "--forces-only",
        ]

    def _run(self, command: list[str]) -> None:
        result = subprocess.run(command, cwd=self.repo_root, env=self._subprocess_env(), check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Newton subprocess failed with exit code {result.returncode}: {' '.join(command)}")

    def _candidate_manifest(self, candidate: Path, canonical_candidate: Path) -> dict[str, Any]:
        base = json.loads(self.base_manifest_path.read_text(encoding="utf-8"))
        entries = list(base.get("motion_files", []))
        matches = [entry for entry in entries if str(entry.get("motion_id")) == self.motion_id]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one motion_id={self.motion_id} in {self.base_manifest_path}, got {len(matches)}"
            )
        source_entry = dict(matches[0])
        terrain_id = source_entry["terrain_id"]
        terrains = [dict(entry) for entry in base.get("terrains", []) if entry.get("terrain_id") == terrain_id]
        if len(terrains) != 1:
            raise ValueError(f"Expected one terrain_id={terrain_id}, got {len(terrains)}")
        terrain_path = Path(str(terrains[0]["terrain_file"]))
        if not terrain_path.is_absolute():
            terrain_path = (self.base_manifest_path.parent / terrain_path).resolve()
        else:
            terrain_path = terrain_path.resolve()
        terrains[0]["terrain_file"] = str(terrain_path)
        terrains[0]["terrain_sha256"] = sha256_file(terrain_path)

        with np.load(canonical_candidate, allow_pickle=False) as data:
            provenance = decode_kinematics_provenance(
                data.get("kinematics_provenance_json"),
                context=str(canonical_candidate),
            )
            decode_robot_asset_json(data.get("robot_asset_json"), context=str(canonical_candidate))
        candidate_sha256 = sha256_file(candidate)
        if provenance.get("source_sha256") != candidate_sha256:
            raise ValueError("Newton canonical motion provenance does not match the PyRoki candidate")

        source_entry["motion_file"] = str(canonical_candidate)
        source_entry["motion_sha256"] = sha256_file(canonical_candidate)
        source_entry["source_file"] = str(candidate)
        source_entry["source_sha256"] = candidate_sha256
        source_entry["kinematics_schema"] = provenance["schema"]
        source_entry["kinematics_backend"] = provenance["kinematics_backend"]
        source_entry["velocity_derivation"] = provenance["velocity_derivation"]
        reference_motion = source_entry.get("reference_motion_file")
        if reference_motion:
            reference_path = Path(str(reference_motion))
            if not reference_path.is_absolute():
                reference_path = (self.base_manifest_path.parent / reference_path).resolve()
            else:
                reference_path = reference_path.resolve()
            source_entry["reference_motion_file"] = str(reference_path)
        source_entry["contact_force_target_file"] = str(self.target_force_motion_path)
        source_entry["contact_force_target_sha256"] = sha256_file(self.target_force_motion_path)
        robot_asset = canonical_g1_source_metadata()
        return {
            **{
                key: value
                for key, value in base.items()
                if key not in {"motion_files", "terrains"}
            },
            "schema": "somaforge_motion_terrain_manifest_v1",
            "schema_version": 1,
            "description": f"Newton force-guided retarget iteration for motion {self.motion_id}",
            "source_kind": "newton_force_guided_physics_retarget_candidate",
            "robot_asset_id": "robot.g1.spherehand",
            "robot_asset_sha256": robot_asset["urdf_sha256"],
            "robot_asset_bundle_sha256": robot_asset["asset_bundle_sha256"],
            "robot_asset_usd_bundle_sha256": G1_SPHEREHAND_USD_BUNDLE_SHA256,
            "kinematics_backend": provenance["kinematics_backend"],
            "motion_files": [source_entry],
            "terrains": terrains,
        }

    def _subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        isaaclab_path = Path(env.get("ISAACLAB_PATH", str(Path.home() / "isaaclab_3.0")))
        env.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")
        env.setdefault("ISAACLAB_PATH", str(isaaclab_path))
        env.setdefault(
            "HOLOSOMA_ISAACLAB3_NEWTON_HEADLESS_EXPERIENCE",
            str(self.repo_root / "apps/holosoma.isaaclab3_newton.headless.kit"),
        )
        paths = [
            self.repo_root / "packages/somaforge_core",
            self.repo_root / "packages/motion_edit",
            self.repo_root / "packages/climb00_pipeline",
            self.repo_root / "src/holosoma",
            self.repo_root / "src/holosoma_retargeting",
            isaaclab_path / "source/isaaclab",
            isaaclab_path / "source/isaaclab_assets",
            isaaclab_path / "source/isaaclab_newton",
            isaaclab_path / "source/isaaclab_rl",
            isaaclab_path / "source/isaaclab_tasks",
        ]
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = os.pathsep.join([*(str(path) for path in paths), *([existing] if existing else [])])
        return env


def load_newton_rollout(
    path: str | Path,
    *,
    iteration: int = 0,
    python_executable: str | None = None,
) -> PhysicsRollout:
    rollout_path = Path(path).expanduser().resolve()
    with np.load(rollout_path, allow_pickle=False) as data:
        provenance = decode_contact_force_provenance(
            data["contact_force_provenance_json"] if "contact_force_provenance_json" in data else None,
            context=str(rollout_path),
            require_newton=True,
        )
        rollout = PhysicsRollout(
            motion_path=rollout_path,
            force_w=np.asarray(data["contact_force_part_w"], dtype=np.float64),
            mask=np.asarray(data["contact_force_part_mask"], dtype=bool),
            joint_pos=np.asarray(data["joint_pos"], dtype=np.float64),
            provenance=provenance,
            metadata={
                "runner": "isaaclab3_newton_wbt_subprocess",
                "iteration": int(iteration),
                "python": str(python_executable or sys.executable),
            },
        )
    rollout.validate()
    return rollout
