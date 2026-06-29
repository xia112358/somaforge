#!/usr/bin/env python3
"""Build a manifest that pairs climbing motions with their obstacle URDFs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_data_root(repo_root: Path) -> Path:
    return repo_root / "src/holosoma_retargeting/holosoma_retargeting/demo_data/climb"


def _default_results_root(repo_root: Path) -> Path:
    return repo_root / "src/holosoma_retargeting/holosoma_retargeting/demo_results/g1/climbing"


def _variant_from_motion(seq: int, motion_file: Path) -> str:
    pattern = re.compile(rf"^mocap_climb_seq_{seq}_(?P<variant>.+)\.npz$")
    match = pattern.match(motion_file.name)
    if match is None:
        raise ValueError(f"Motion file does not match seq {seq}: {motion_file}")
    return match.group("variant")


def build_manifest(
    *,
    repo_root: Path,
    data_root: Path,
    results_root: Path,
    obstacle_name: str,
    object_init_pos: list[float],
) -> dict:
    scenes = []
    seq_dirs = sorted(data_root.glob("mocap_climb_seq_*"))
    for seq_dir in seq_dirs:
        if not seq_dir.is_dir():
            continue
        seq_match = re.match(r"mocap_climb_seq_(\d+)$", seq_dir.name)
        if seq_match is None:
            continue

        seq = int(seq_match.group(1))
        obstacle_urdf = seq_dir / obstacle_name
        motion_files = sorted(results_root.rglob(f"mocap_climb_seq_{seq}_mj*.npz"))

        if not obstacle_urdf.exists():
            print(f"[skip] seq {seq}: missing obstacle URDF: {obstacle_urdf}")
            continue
        if not motion_files:
            print(f"[skip] seq {seq}: no retargeted motion found under: {results_root}")
            continue

        for motion_file in motion_files:
            variant = _variant_from_motion(seq, motion_file)
            scenes.append(
                {
                    "seq": seq,
                    "name": f"mocap_climb_seq_{seq}_{variant}",
                    "variant": variant,
                    "motion_file": str(motion_file.resolve()),
                    "obstacle_urdf": str(obstacle_urdf.resolve()),
                    "object_init_pos": object_init_pos,
                    "fix_base": True,
                    "env_spacing": 0.0,
                }
            )

    return {
        "schema_version": 1,
        "description": "Pairs each retargeted G1 climbing motion with the matching static obstacle URDF.",
        "repo_root": str(repo_root.resolve()),
        "data_root": str(data_root.resolve()),
        "results_root": str(results_root.resolve()),
        "scenes": scenes,
    }


def main() -> None:
    repo_root = _repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=_default_data_root(repo_root))
    parser.add_argument("--results-root", type=Path, default=_default_results_root(repo_root))
    parser.add_argument("--output", type=Path, default=repo_root / "configs/climbing_scenes.json")
    parser.add_argument(
        "--obstacle-name",
        default="multi_boxes_scaled_0.74_0.74_0.74.urdf",
        help="Obstacle URDF filename inside each mocap_climb_seq_* directory.",
    )
    parser.add_argument(
        "--object-init-pos",
        nargs=3,
        type=float,
        default=[0.0, 0.0, 0.0],
        metavar=("X", "Y", "Z"),
        help="Static obstacle initial position passed to train_agent.py.",
    )
    args = parser.parse_args()

    manifest = build_manifest(
        repo_root=repo_root,
        data_root=args.data_root,
        results_root=args.results_root,
        obstacle_name=args.obstacle_name,
        object_init_pos=args.object_init_pos,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(manifest['scenes'])} trainable climbing scene(s) to {args.output}")


if __name__ == "__main__":
    main()
