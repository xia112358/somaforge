"""Utilities for motion-to-terrain binding manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from holosoma.utils.path import resolve_data_file_path


def _load_manifest_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - depends on optional local install
            raise ImportError(f"PyYAML is required to read motion-terrain manifest: {path}") from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Motion-terrain manifest must contain a mapping: {path}")
    return data


def load_motion_terrain_manifest(manifest_path: str) -> dict[str, Any]:
    """Load a motion-terrain manifest and resolve relative paths.

    Supported shapes:
    - InstinctLab-style:
      {"motion_files": [{"motion_file": "...", "terrain_id": 0}],
       "terrains": [{"terrain_file": "...", "terrain_id": 0}]}
    - Holosoma scene-style:
      {"scenes": [{"motion_file": "...", "terrain_file": "...", "terrain_id": 0}]}
    """
    path = Path(resolve_data_file_path(manifest_path)).expanduser().resolve()
    data = _load_manifest_file(path)
    base_dir = path.parent

    terrains = _normalize_terrains(data, base_dir)
    motion_files = _normalize_motion_files(data, base_dir, terrains)
    if not terrains:
        raise ValueError(f"Manifest contains no terrains: {path}")
    if not motion_files:
        raise ValueError(f"Manifest contains no motion files: {path}")

    return {
        "path": str(path),
        "base_dir": str(base_dir),
        "terrains": terrains,
        "motion_files": motion_files,
    }


def _resolve_manifest_path(value: str, base_dir: Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve())


def _normalize_terrains(data: dict[str, Any], base_dir: Path) -> list[dict[str, Any]]:
    if "terrains" in data:
        terrains = data["terrains"]
    elif "scenes" in data:
        seen: dict[Any, dict[str, Any]] = {}
        for idx, scene in enumerate(data["scenes"]):
            terrain_file = scene.get("terrain_file") or scene.get("terrain_obj") or scene.get("obstacle_urdf")
            if not terrain_file:
                continue
            terrain_id = scene.get("terrain_id", scene.get("seq", idx))
            seen.setdefault(
                terrain_id,
                {
                    "terrain_id": terrain_id,
                    "terrain_file": terrain_file,
                },
            )
        terrains = list(seen.values())
    else:
        terrains = []

    normalized = []
    for idx, terrain in enumerate(terrains):
        terrain_id = terrain.get("terrain_id", idx)
        terrain_file = terrain.get("terrain_file")
        if not terrain_file:
            raise ValueError(f"Terrain entry is missing terrain_file: {terrain}")
        normalized.append(
            {
                "terrain_id": int(terrain_id),
                "terrain_file": _resolve_manifest_path(str(terrain_file), base_dir),
            }
        )
    return normalized


def _normalize_motion_files(
    data: dict[str, Any],
    base_dir: Path,
    terrains: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if "motion_files" in data:
        motion_files = data["motion_files"]
    elif "scenes" in data:
        terrain_by_file = {terrain["terrain_file"]: terrain["terrain_id"] for terrain in terrains}
        motion_files = []
        for idx, scene in enumerate(data["scenes"]):
            motion_file = scene.get("motion_file")
            if not motion_file:
                continue
            terrain_id = scene.get("terrain_id")
            if terrain_id is None:
                terrain_file = scene.get("terrain_file") or scene.get("terrain_obj") or scene.get("obstacle_urdf")
                terrain_id = terrain_by_file.get(_resolve_manifest_path(str(terrain_file), base_dir), scene.get("seq", idx))
            motion_files.append(
                {
                    "motion_file": motion_file,
                    "terrain_id": terrain_id,
                    "weight": scene.get("weight", 1.0),
                }
            )
    else:
        motion_files = []

    terrain_ids = {terrain["terrain_id"] for terrain in terrains}
    normalized = []
    for motion in motion_files:
        terrain_id = int(motion["terrain_id"])
        if terrain_id not in terrain_ids:
            raise ValueError(f"Motion references unknown terrain_id={terrain_id}: {motion}")
        normalized.append(
            {
                "motion_file": _resolve_manifest_path(str(motion["motion_file"]), base_dir),
                "terrain_id": terrain_id,
                "weight": float(motion.get("weight", 1.0)),
            }
        )
    return normalized
