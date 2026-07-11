#!/usr/bin/env python3
"""Validate repository-local motion manifest paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OLD_DATA_ROOT = "/home/xiaz/holosoma/OmniRetarget_Dataset"
DEFAULT_MANIFESTS = [
    "runtime/current/manifests/motion_edit_ref_v1.json",
    "runtime/current/manifests/climb00_motion_edit_ref.json",
    "tmp/gmvq_play/climb00_gmvq_fixed_code_theta_manifest.json",
]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return data


def _resolve(path_value: str, base_dir: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _iter_manifest_paths(data: dict[str, Any]) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    for terrain in data.get("terrains", []):
        if isinstance(terrain, dict) and terrain.get("terrain_file"):
            paths.append(("terrain_file", str(terrain["terrain_file"])))
    for motion in data.get("motion_files", []):
        if isinstance(motion, dict) and motion.get("motion_file"):
            paths.append(("motion_file", str(motion["motion_file"])))
    for scene in data.get("scenes", []):
        if not isinstance(scene, dict):
            continue
        for key in ("terrain_file", "terrain_obj", "obstacle_urdf", "motion_file"):
            if scene.get(key):
                paths.append((key, str(scene[key])))
    return paths


def check_manifest(manifest_path: Path, *, require_files: bool) -> list[str]:
    errors: list[str] = []
    data = _load_json(manifest_path)
    base_dir = manifest_path.parent

    entries = _iter_manifest_paths(data)
    if not entries:
        errors.append(f"{manifest_path}: no terrain or motion paths found")
        return errors

    for key, value in entries:
        if OLD_DATA_ROOT in value:
            errors.append(f"{manifest_path}: {key} still uses old absolute root: {value}")
        resolved = _resolve(value, base_dir)
        if require_files and not resolved.exists():
            errors.append(f"{manifest_path}: missing {key}: {value} -> {resolved}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check every JSON manifest under configs/motion_matched.",
    )
    parser.add_argument(
        "--manifest",
        action="append",
        default=[],
        help="Additional manifest path to check, relative to the repository root unless absolute.",
    )
    parser.add_argument(
        "--no-require-files",
        action="store_true",
        help="Only check path shape and old absolute roots; do not require local data files.",
    )
    args = parser.parse_args()

    manifests: list[Path] = []
    if args.all:
        # In CI / remote checkouts, ignored tmp/ manifests are intentionally absent.
        # When they exist locally, include them; otherwise check only repository manifests.
        manifests.extend(REPO_ROOT / item for item in DEFAULT_MANIFESTS if (REPO_ROOT / item).exists())
        manifests.extend(sorted((REPO_ROOT / "configs/motion_matched").rglob("*.json")))
    else:
        manifests.extend(REPO_ROOT / item for item in DEFAULT_MANIFESTS)

    manifests.extend(Path(item) if Path(item).is_absolute() else REPO_ROOT / item for item in args.manifest)

    seen: set[Path] = set()
    errors: list[str] = []
    for manifest in manifests:
        manifest = manifest.resolve()
        if manifest in seen:
            continue
        seen.add(manifest)
        if not manifest.exists():
            errors.append(f"missing manifest: {manifest}")
            continue
        errors.extend(check_manifest(manifest, require_files=not args.no_require_files))

    if errors:
        print("Data layout check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Data layout check passed for {len(seen)} manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
