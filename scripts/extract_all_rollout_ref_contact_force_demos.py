#!/usr/bin/env python3
"""Run parallel eval recordings and extract rollout-ref contact-force demos."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
CLIMB_RE = re.compile(r"climb[_-](\d+)")

DEFAULT_BASE_MANIFEST = REPO_ROOT / "configs/motion_matched/climb29_z1_unmasked_manifest.json"
DEFAULT_WORK_DIR = REPO_ROOT / "logs/rollout_ref_contact_force_extract"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data/rollout_ref_contact_force_demos"
DEFAULT_MANIFEST_OUTPUT = REPO_ROOT / "configs/motion_matched/climb29_z1_rollout_ref_contact_force_manifest.json"
DEFAULT_FAILURE_REPORT = REPO_ROOT / "logs/rollout_ref_contact_force_extract/failures.json"
DEFAULT_CONDA_PYTHON = Path("/home/xiaz/miniforge3/envs/env_holosoma_isaaclab3_newton/bin/python")
DEFAULT_PARALLEL_ENVS = 16

DEFAULT_CHECKPOINT = (
    REPO_ROOT
    / "logs/WholeBodyTracking/20260601_124155-g1_29dof_wbt_manager-locomotion/model_16000.pt"
)
SPECIAL_CHECKPOINTS = {
    0: REPO_ROOT
    / "logs/WholeBodyTracking/20260531_102342-g1_29dof_wbt_manager-locomotion/model_09999.pt",
    13: REPO_ROOT
    / "logs/WholeBodyTracking/20260603_061801-g1_29dof_wbt_single_climb13_4096_10k_h20-locomotion/model_09999.pt",
    21: REPO_ROOT
    / "logs/WholeBodyTracking/20260604_061113-g1_29dof_wbt_single_climb21_actionscale025_4096_10k_h20-locomotion/model_09999.pt",
    25: REPO_ROOT
    / "logs/WholeBodyTracking/20260605_104652-g1_29dof_wbt_single_climb25_4096_10k_h20-locomotion/model_09999.pt",
    26: REPO_ROOT
    / "logs/WholeBodyTracking/20260605_181648-g1_29dof_wbt_single_climb26_4096_10k_h20-locomotion/model_09999.pt",
    27: REPO_ROOT
    / "logs/WholeBodyTracking/20260606_005611-g1_29dof_wbt_single_climb27_4096_10k_h20-locomotion/model_09999.pt",
    28: REPO_ROOT
    / "logs/WholeBodyTracking/20260606_090821-g1_29dof_wbt_single_climb28_4096_10k_h20-locomotion/model_09999.pt",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _resolve_manifest_path(path: Path, manifest_path: Path) -> Path:
    if path.is_absolute():
        return path
    return (manifest_path.parent / path).resolve()


def _climb_id(path_or_entry: str) -> int:
    match = CLIMB_RE.search(path_or_entry)
    if match is None:
        raise ValueError(f"Could not infer climb id from: {path_or_entry}")
    return int(match.group(1))


def _select_checkpoint(climb_id: int) -> Path:
    return SPECIAL_CHECKPOINTS.get(climb_id, DEFAULT_CHECKPOINT)


def _single_motion_manifest(
    base: dict[str, Any],
    base_manifest_path: Path,
    motion_entry: dict[str, Any],
    climb_id: int,
) -> dict[str, Any]:
    terrain_id = motion_entry["terrain_id"]
    terrains = [entry for entry in base["terrains"] if entry["terrain_id"] == terrain_id]
    if len(terrains) != 1:
        raise ValueError(f"Expected exactly one terrain for climb {climb_id} terrain_id={terrain_id}, got {len(terrains)}")
    terrain = dict(terrains[0])
    terrain_file = Path(str(terrain["terrain_file"]))
    if not terrain_file.is_absolute():
        terrain["terrain_file"] = str((base_manifest_path.parent / terrain_file).resolve())
    return {
        "schema_version": base.get("schema_version", 1),
        "description": f"Single-motion rollout-ref extraction manifest for climb {climb_id:02d}.",
        "terrains": [terrain],
        "motion_files": [motion_entry],
    }


def _default_python() -> str:
    if DEFAULT_CONDA_PYTHON.exists():
        return str(DEFAULT_CONDA_PYTHON)
    return sys.executable


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    isaaclab_path = Path(env.get("ISAACLAB_PATH", str(Path.home() / "isaaclab_3.0")))
    env.setdefault("OMNI_KIT_ACCEPT_EULA", "YES")
    env.setdefault("ISAACLAB_PATH", str(isaaclab_path))
    env.setdefault(
        "HOLOSOMA_ISAACLAB3_NEWTON_HEADLESS_EXPERIENCE",
        str(REPO_ROOT / "apps/holosoma.isaaclab3_newton.headless.kit"),
    )
    env.setdefault(
        "HOLOSOMA_ISAACLAB3_NEWTON_KIT_EXPERIENCE",
        str(REPO_ROOT / "apps/holosoma.isaaclab3_newton.kit"),
    )
    env.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".cache/matplotlib"))
    env.setdefault("WARP_CACHE_PATH", str(REPO_ROOT / ".cache/warp"))
    source_paths = [
        str(REPO_ROOT / "src/holosoma"),
        str(REPO_ROOT / "src/holosoma_retargeting"),
        str(isaaclab_path / "source/isaaclab"),
        str(isaaclab_path / "source/isaaclab_assets"),
        str(isaaclab_path / "source/isaaclab_mimic"),
        str(isaaclab_path / "source/isaaclab_newton"),
        str(isaaclab_path / "source/isaaclab_ov"),
        str(isaaclab_path / "source/isaaclab_rl"),
        str(isaaclab_path / "source/isaaclab_tasks"),
        str(isaaclab_path / "source/isaaclab_tasks_experimental"),
        str(isaaclab_path / "source/isaaclab_visualizers"),
    ]
    existing = env.get("PYTHONPATH")
    if existing:
        source_paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(source_paths)
    return env


def _run(cmd: list[str], dry_run: bool) -> bool:
    print("+", " ".join(cmd), flush=True)
    if dry_run:
        return True
    result = subprocess.run(cmd, cwd=REPO_ROOT, check=False, env=_subprocess_env())
    return result.returncode == 0


def _eval_command(
    python_executable: str,
    checkpoint: Path,
    single_manifest: Path,
    recording_path: Path,
    max_eval_steps: int,
    parallel_envs: int,
) -> list[str]:
    cmd = [
        python_executable,
        "-m",
        "holosoma.eval_agent",
        "termination:g1-29dof-wbt",
        "--headless",
        "--device",
        "cuda:0",
        "--checkpoint",
        str(checkpoint),
        "--recording.config.enabled",
        "--recording.config.record-initial-state",
        "--recording.config.env-id",
        str(-1 if parallel_envs > 1 else 0),
        "--recording.config.output-path",
        str(recording_path),
        "--training.num-envs",
        str(parallel_envs),
        "--training.max-eval-steps",
        str(max_eval_steps),
        "--training.export-onnx",
        "False",
        "--command.setup-terms.motion-command.params.motion-config.motion-manifest",
        str(single_manifest),
        "--command.setup-terms.motion-command.params.motion-config.start-at-timestep-zero-prob",
        "1.0",
        "--command.setup-terms.motion-command.params.motion-config.freeze-at-timestep-zero-prob",
        "0.0",
        "--command.setup-terms.motion-command.params.motion-config.noise-to-initial-pose.overall-noise-scale",
        "0.0",
        "--terrain.terrain-term.motion-matched-manifest",
        str(single_manifest),
    ]
    return cmd


def _extract_command(python_executable: str, motion_path: Path, recording_path: Path, output_path: Path) -> list[str]:
    return [
        python_executable,
        str(REPO_ROOT / "scripts/extract_rollout_ref_contact_force_demo.py"),
        "--motion",
        str(motion_path),
        "--recording",
        str(recording_path),
        "--output",
        str(output_path),
    ]


def _build_output_manifest(base: dict[str, Any], output_dir: Path, output_manifest: Path, allow_missing: bool) -> None:
    demo_by_id = {_climb_id(str(path)): path for path in sorted(output_dir.glob("climb_*_rollout_ref_contact_force.npz"))}
    motion_files = []
    missing = []
    for entry in base["motion_files"]:
        cid = _climb_id(str(entry["motion_file"]))
        demo = demo_by_id.get(cid)
        if demo is None:
            missing.append(cid)
            if allow_missing:
                continue
            continue
        motion_files.append(
            {
                "motion_file": str(demo.resolve()),
                "terrain_id": entry["terrain_id"],
                "weight": entry.get("weight", 1.0),
            }
        )
    if missing and not allow_missing:
        raise ValueError(f"Missing rollout-ref demos for climb ids: {sorted(missing)}")
    _write_json(
        output_manifest,
        {
            "schema_version": base.get("schema_version", 1),
            "description": "Rollout-ref contact-force manifest generated entirely from successful eval recordings.",
            "terrains": base["terrains"],
            "motion_files": motion_files,
        },
    )
    print(f"Wrote {output_manifest} motions={len(motion_files)} terrains={len(base['terrains'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-manifest", type=Path, default=DEFAULT_MANIFEST_OUTPUT)
    parser.add_argument("--failure-report", type=Path, default=DEFAULT_FAILURE_REPORT)
    parser.add_argument("--python", default=_default_python())
    parser.add_argument("--motion-id", type=int, action="append", help="Only process selected climb id; repeatable.")
    parser.add_argument("--max-eval-steps", type=int, default=None)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument(
        "--parallel-envs",
        type=int,
        default=DEFAULT_PARALLEL_ENVS,
        help=(
            "Run this many eval envs per attempt and extract the first complete rollout. "
            "The standard extraction flow records all envs with env_id=-1; pass 1 only for single-env debugging."
        ),
    )
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--record-only", action="store_true")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.attempts < 1:
        raise ValueError("--attempts must be at least 1.")
    if args.parallel_envs < 1:
        raise ValueError("--parallel-envs must be at least 1.")

    base = _read_json(args.base_manifest)
    selected = set(args.motion_id or [])
    manifest_dir = args.work_dir / "manifests"
    recording_dir = args.work_dir / "recordings"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    recording_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, Any]] = []
    successes: list[dict[str, Any]] = []

    for motion_entry in base["motion_files"]:
        motion_path = Path(motion_entry["motion_file"])
        climb_id = _climb_id(str(motion_path))
        if selected and climb_id not in selected:
            continue
        motion_npz_path = _resolve_manifest_path(motion_path, args.base_manifest)
        with np.load(motion_npz_path) as motion_npz:
            motion_frame_count = int(motion_npz["joint_pos"].shape[0])
        eval_steps = int(args.max_eval_steps) if args.max_eval_steps is not None else max(motion_frame_count - 1, 1)

        single_manifest = manifest_dir / f"climb_{climb_id:02d}_manifest.json"
        output_path = args.output_dir / f"climb_{climb_id:02d}_rollout_ref_contact_force.npz"
        _write_json(single_manifest, _single_motion_manifest(base, args.base_manifest, motion_entry, climb_id))

        if args.skip_existing and output_path.exists():
            print(f"Skip existing {output_path}")
            successes.append({"climb_id": climb_id, "attempt": 0, "output": str(output_path)})
            continue

        checkpoint = _select_checkpoint(climb_id)
        if not checkpoint.exists():
            raise FileNotFoundError(f"Missing checkpoint for climb {climb_id:02d}: {checkpoint}")

        if output_path.exists():
            output_path.unlink()

        attempt_errors = []
        success = False
        for attempt in range(1, args.attempts + 1):
            recording_path = recording_dir / f"climb_{climb_id:02d}_attempt_{attempt:02d}_eval_recording.npz"
            if recording_path.exists():
                recording_path.unlink()
            if output_path.exists():
                output_path.unlink()

            print(f"=== climb_{climb_id:02d} attempt {attempt}/{args.attempts} ===", flush=True)
            if not args.extract_only:
                eval_ok = _run(
                    _eval_command(args.python, checkpoint, single_manifest, recording_path, eval_steps, args.parallel_envs),
                    args.dry_run,
                )
                if not eval_ok:
                    attempt_errors.append({"attempt": attempt, "stage": "eval", "error": "eval command failed"})
                    continue
                if not args.dry_run and not recording_path.exists():
                    attempt_errors.append({"attempt": attempt, "stage": "eval", "error": "recording was not produced"})
                    continue

            if args.record_only:
                success = True
                successes.append(
                    {
                        "climb_id": climb_id,
                        "attempt": attempt,
                        "checkpoint": str(checkpoint),
                        "recording": str(recording_path),
                    }
                )
                break

            extract_ok = _run(_extract_command(args.python, motion_npz_path, recording_path, output_path), args.dry_run)
            if extract_ok and (args.dry_run or output_path.exists()):
                success = True
                successes.append(
                    {
                        "climb_id": climb_id,
                        "attempt": attempt,
                        "checkpoint": str(checkpoint),
                        "recording": str(recording_path),
                        "output": str(output_path),
                    }
                )
                break
            attempt_errors.append(
                {
                    "attempt": attempt,
                    "stage": "extract",
                    "error": "recording was not a complete successful rollout",
                }
            )

        if not success:
            failures.append(
                {
                    "climb_id": climb_id,
                    "motion_file": str(motion_npz_path),
                    "checkpoint": str(checkpoint),
                    "attempts": args.attempts,
                    "errors": attempt_errors,
                }
            )
            print(f"FAILED climb_{climb_id:02d} after {args.attempts} attempts", flush=True)

    if not selected and not args.record_only:
        _build_output_manifest(base, args.output_dir, args.output_manifest, allow_missing=True)
        _write_json(
            args.failure_report,
            {
                "successes": successes,
                "failures": failures,
            },
        )
        print(f"Wrote {args.failure_report} successes={len(successes)} failures={len(failures)}")


if __name__ == "__main__":
    main()
