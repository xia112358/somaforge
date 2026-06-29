#!/usr/bin/env python3
"""Train a single climbing scene by looking up its motion and obstacle in a manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Manifest not found: {path}\n"
            f"Generate it first with: python scripts/build_climbing_manifest.py --output {path}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _select_scene(manifest: dict[str, Any], seq: int | None, name: str | None, variant: str | None) -> dict[str, Any]:
    scenes = manifest.get("scenes", [])
    if not scenes:
        raise ValueError("Manifest contains no trainable scenes.")

    matches = scenes
    if seq is not None:
        matches = [scene for scene in matches if scene["seq"] == seq]
    if name is not None:
        matches = [scene for scene in matches if scene["name"] == name]
    if variant is not None:
        matches = [scene for scene in matches if scene["variant"] == variant]

    if len(matches) == 1:
        return matches[0]

    if not matches:
        available = "\n".join(f"  seq={s['seq']} variant={s['variant']} name={s['name']}" for s in scenes)
        raise ValueError(f"No matching climbing scene found.\nAvailable scenes:\n{available}")

    available = "\n".join(f"  seq={s['seq']} variant={s['variant']} name={s['name']}" for s in matches)
    raise ValueError(
        "Multiple scenes matched. Specify --variant or --name.\n"
        f"Matching scenes:\n{available}"
    )


def _format_float_list(values: list[float]) -> str:
    return "[" + ",".join(str(float(v)) for v in values) + "]"


def _build_command(args: argparse.Namespace, scene: dict[str, Any], extra_args: list[str]) -> list[str]:
    repo_root = _repo_root()
    train_script = repo_root / "src/holosoma/holosoma/train_agent.py"
    headless = not args.gui

    cmd = [
        sys.executable,
        str(train_script),
        args.exp,
        "simulator:isaaclab3-newton",
        f"--robot.object.object-urdf-path={scene['obstacle_urdf']}",
        "--robot.object.fix-base=True" if scene.get("fix_base", True) else "--robot.object.fix-base=False",
        f"--robot.object.init-pos={_format_float_list(scene['object_init_pos'])}",
        f"--command.setup_terms.motion_command.params.motion_config.motion_file={scene['motion_file']}",
        f"--simulator.config.scene.env_spacing={scene.get('env_spacing', 0.0)}",
        "--training.num_envs",
        str(args.num_envs),
        f"--training.headless={str(headless)}",
        "--logger.video.enabled=False",
    ]
    if args.iterations is not None:
        cmd.append(f"--algo.config.num_learning_iterations={args.iterations}")

    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]
    cmd.extend(extra_args)
    return cmd


def main() -> None:
    repo_root = _repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=repo_root / "configs/climbing_scenes.json")
    parser.add_argument("--seq", type=int, help="Climbing sequence id, for example 0.")
    parser.add_argument("--name", help="Exact scene name from the manifest.")
    parser.add_argument("--variant", default="mj", help="Motion variant to train. Use --variant '' to disable filtering.")
    parser.add_argument("--num-envs", type=int, default=256)
    parser.add_argument("--iterations", type=int, help="Optional short-run iteration limit.")
    parser.add_argument("--gui", action="store_true", help="Run with IsaacSim GUI enabled.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved command without executing it.")
    parser.add_argument("--exp", default="exp:g1-29dof-wbt", help="Holosoma experiment preset.")
    args, extra_args = parser.parse_known_args()

    if args.seq is None and args.name is None:
        raise SystemExit("Specify --seq or --name.")

    variant = args.variant if args.variant else None
    manifest = _load_manifest(args.manifest)
    scene = _select_scene(manifest, args.seq, args.name, variant)
    cmd = _build_command(args, scene, extra_args)

    print(f"Selected climbing scene: {scene['name']}")
    print(f"Motion: {scene['motion_file']}")
    print(f"Obstacle: {scene['obstacle_urdf']}")
    print("Command:")
    print(" ".join(cmd))

    if args.dry_run:
        return

    subprocess.run(cmd, cwd=repo_root, check=True)


if __name__ == "__main__":
    main()
