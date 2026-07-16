from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from somaforge_core.contact_schema import (
    CONTACT_FORCE_SCHEMA,
    NEWTON_CONTACT_BACKEND,
    decode_contact_force_provenance,
)

ASSET_MANIFEST_SCHEMA = "somaforge_motion_terrain_manifest_v1"
ASSET_MANIFEST_SOURCE_KIND = "newton_policy_rollout_contact_force_8part"


@dataclass(frozen=True)
class ManifestMotionAsset:
    motion_index: int
    motion_id: str
    motion_asset_id: str
    force_motion_path: Path
    source_motion_path: Path
    terrain_mesh_path: Path
    motion_sha256: str
    source_sha256: str
    terrain_sha256: str
    contact_solver_sha256: str
    provenance: dict[str, Any]
    manifest_path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_file(manifest_path: Path, value: Any, *, field: str) -> Path:
    if not value:
        raise ValueError(f"{manifest_path}: missing {field}")
    path = (manifest_path.parent / str(value)).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _verify_sha256(path: Path, expected: Any, *, field: str) -> str:
    if not expected:
        raise ValueError(f"{path}: missing {field}")
    expected_text = str(expected)
    actual = _sha256(path)
    if actual != expected_text:
        raise ValueError(f"{path}: {field} mismatch: expected {expected_text}, got {actual}")
    return actual


def load_asset_manifest(path: str | Path, *, verify_hashes: bool = True) -> list[ManifestMotionAsset]:
    manifest_path = Path(path).expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != ASSET_MANIFEST_SCHEMA:
        raise ValueError(f"{manifest_path}: unsupported manifest schema {payload.get('schema')!r}")
    if payload.get("source_kind") != ASSET_MANIFEST_SOURCE_KIND:
        raise ValueError(f"{manifest_path}: unsupported source_kind {payload.get('source_kind')!r}")
    if payload.get("contact_force_schema") != CONTACT_FORCE_SCHEMA:
        raise ValueError(f"{manifest_path}: unsupported contact-force schema")
    if payload.get("contact_force_backend") != NEWTON_CONTACT_BACKEND:
        raise ValueError(f"{manifest_path}: contact force is not from the Newton backend")

    terrains = {int(item["terrain_id"]): item for item in payload.get("terrains", [])}
    assets: list[ManifestMotionAsset] = []
    for entry in payload.get("motion_files", []):
        motion_index = int(entry["motion_id"])
        terrain_id = int(entry["terrain_id"])
        if terrain_id not in terrains:
            raise ValueError(f"{manifest_path}: motion {motion_index} references missing terrain {terrain_id}")
        terrain = terrains[terrain_id]
        force_path = _resolve_file(manifest_path, entry.get("motion_file"), field="motion_file")
        source_path = _resolve_file(manifest_path, entry.get("source_file"), field="source_file")
        terrain_path = _resolve_file(manifest_path, terrain.get("terrain_file"), field="terrain_file")
        if verify_hashes:
            motion_sha = _verify_sha256(force_path, entry.get("motion_sha256"), field="motion_sha256")
            source_sha = _verify_sha256(source_path, entry.get("source_sha256"), field="source_sha256")
            terrain_sha = _verify_sha256(terrain_path, terrain.get("terrain_sha256"), field="terrain_sha256")
        else:
            motion_sha = str(entry.get("motion_sha256", ""))
            source_sha = str(entry.get("source_sha256", ""))
            terrain_sha = str(terrain.get("terrain_sha256", ""))
        with np.load(force_path, allow_pickle=False) as data:
            provenance = decode_contact_force_provenance(
                data["contact_force_provenance_json"] if "contact_force_provenance_json" in data else None,
                context=str(force_path),
                require_newton=True,
            )
        solver_sha = str(entry.get("contact_solver_sha256", ""))
        if solver_sha and provenance.get("solver_config_sha256") != solver_sha:
            raise ValueError(f"{force_path}: contact solver fingerprint does not match manifest")
        motion_id = f"climb_{motion_index:02d}"
        assets.append(
            ManifestMotionAsset(
                motion_index=motion_index,
                motion_id=motion_id,
                motion_asset_id=f"{motion_id}_newton_8part",
                force_motion_path=force_path,
                source_motion_path=source_path,
                terrain_mesh_path=terrain_path,
                motion_sha256=motion_sha,
                source_sha256=source_sha,
                terrain_sha256=terrain_sha,
                contact_solver_sha256=solver_sha,
                provenance=provenance,
                manifest_path=manifest_path,
            )
        )
    return assets
