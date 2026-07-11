from __future__ import annotations

import json

import pytest

from somaforge_core import AssetManifest


def test_manifest_resolves_verified_robot_asset() -> None:
    manifest = AssetManifest.load()
    path = manifest.resolve("robot.g1.spherehand", "urdf")
    assert path.name == "g1_29dof_spherehand.urdf"


def test_manifest_does_not_register_removed_legacy_asset() -> None:
    manifest = AssetManifest.load()
    assert "legacy.wrong-urdf" not in manifest.ids()
    with pytest.raises(KeyError, match="not registered"):
        manifest.resolve("legacy.wrong-urdf", "root")


def test_manifest_detects_duplicate_ids(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema": "somaforge_asset_manifest_v1",
                "root": ".",
                "assets": [
                    {"id": "duplicate", "kind": "motion", "files": {}},
                    {"id": "duplicate", "kind": "motion", "files": {}},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate asset id"):
        AssetManifest.load(path)
