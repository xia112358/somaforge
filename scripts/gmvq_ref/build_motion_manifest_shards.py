#!/usr/bin/env python3
"""Build sharded motion-matched manifests for large motion-edit force refs."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


DEFAULT_GROUP_PATTERN = r"surface_jitter_(\d+)"
DEFAULT_GROUPS_PER_SHARD = 4


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Manifest must be a JSON object: {path}")
    return data


def _resolve_path(value: str, base_dir: Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve())


def _normalize_terrain_entry(entry: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    out = dict(entry)
    if "terrain_file" in out:
        out["terrain_file"] = _resolve_path(str(out["terrain_file"]), base_dir)
    return out


def _normalize_motion_entry(entry: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    out = dict(entry)
    if "motion_file" not in out:
        raise ValueError(f"Motion entry is missing motion_file: {entry}")
    out["motion_file"] = _resolve_path(str(out["motion_file"]), base_dir)
    out["terrain_id"] = int(out["terrain_id"])
    out["weight"] = float(out.get("weight", 1.0))
    return out


def _group_motion_entries(
    entries: list[dict[str, Any]],
    *,
    pattern: re.Pattern[str],
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    missing: list[str] = []
    for entry in entries:
        motion_file = str(entry["motion_file"])
        match = pattern.search(Path(motion_file).name)
        if match is None:
            missing.append(motion_file)
            continue
        key = match.group(1)
        groups.setdefault(key, []).append(entry)
    if missing:
        preview = "\n".join(missing[:5])
        raise ValueError(
            f"{len(missing)} motion files did not match group pattern {pattern.pattern!r}. "
            f"Examples:\n{preview}"
        )
    return groups


def _sort_group_keys(keys: list[str]) -> list[str]:
    def key_fn(value: str) -> tuple[int, str]:
        try:
            return int(value), value
        except ValueError:
            return math.inf, value

    return sorted(keys, key=key_fn)


def _build_shards(group_keys: list[str], groups_per_shard: int) -> list[list[str]]:
    if groups_per_shard <= 0:
        raise ValueError(f"groups_per_shard must be positive, got {groups_per_shard}")
    return [group_keys[i : i + groups_per_shard] for i in range(0, len(group_keys), groups_per_shard)]


def build_motion_manifest_shards(
    manifest_path: Path,
    output_dir: Path,
    *,
    group_pattern: str = DEFAULT_GROUP_PATTERN,
    groups_per_shard: int = DEFAULT_GROUPS_PER_SHARD,
    overwrite: bool = False,
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    source = _load_json(manifest_path)
    base_dir = manifest_path.parent

    terrains = [
        _normalize_terrain_entry(dict(entry), base_dir)
        for entry in source.get("terrains", [])
    ]
    motions = [
        _normalize_motion_entry(dict(entry), base_dir)
        for entry in source.get("motion_files", [])
    ]
    if not terrains:
        raise ValueError(f"Manifest has no terrains: {manifest_path}")
    if not motions:
        raise ValueError(f"Manifest has no motion_files: {manifest_path}")

    groups = _group_motion_entries(motions, pattern=re.compile(group_pattern))
    group_keys = _sort_group_keys(list(groups))
    shard_group_keys = _build_shards(group_keys, groups_per_shard)

    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "shard_index.json"
    if index_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing shard index: {index_path}")

    shards: list[dict[str, Any]] = []
    manifest_stem = manifest_path.stem
    for shard_id, keys in enumerate(shard_group_keys):
        shard_motion_entries: list[dict[str, Any]] = []
        for key in keys:
            shard_motion_entries.extend(groups[key])
        shard_manifest_path = output_dir / f"{manifest_stem}_shard_{shard_id:02d}.json"
        if shard_manifest_path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite existing shard manifest: {shard_manifest_path}")
        shard_manifest = {
            "schema_version": source.get("schema_version", 1),
            "description": (
                f"Shard {shard_id:02d} from {manifest_path.name}; "
                f"group keys {keys[0]}..{keys[-1]}."
            ),
            "terrains": terrains,
            "motion_files": shard_motion_entries,
        }
        shard_manifest_path.write_text(json.dumps(shard_manifest, indent=2) + "\n", encoding="utf-8")
        shards.append(
            {
                "shard_id": shard_id,
                "manifest_path": shard_manifest_path.name,
                "group_keys": keys,
                "motion_count": len(shard_motion_entries),
                "terrain_count": len(terrains),
            }
        )

    index = {
        "kind": "motion_edit_force_ref_shard_index",
        "schema_version": 1,
        "source_manifest": str(manifest_path),
        "group_pattern": group_pattern,
        "groups_per_shard": groups_per_shard,
        "num_groups": len(group_keys),
        "num_shards": len(shards),
        "total_motion_count": len(motions),
        "total_terrain_count": len(terrains),
        "shards": shards,
    }
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="Full motion-matched force-ref manifest.")
    parser.add_argument("--output-dir", type=Path, help="Directory for shard manifests and shard_index.json.")
    parser.add_argument("--group-pattern", default=DEFAULT_GROUP_PATTERN)
    parser.add_argument("--groups-per-shard", type=int, default=DEFAULT_GROUPS_PER_SHARD)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    manifest = args.manifest.expanduser()
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = manifest.parent / f"{manifest.stem}_shards"

    index = build_motion_manifest_shards(
        manifest,
        output_dir,
        group_pattern=args.group_pattern,
        groups_per_shard=args.groups_per_shard,
        overwrite=args.overwrite,
    )
    print(json.dumps(index, indent=2))


if __name__ == "__main__":
    main()
