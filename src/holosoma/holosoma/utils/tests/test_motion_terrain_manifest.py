import hashlib
import json

import pytest

from holosoma.utils.motion_terrain_manifest import load_motion_terrain_manifest


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest(tmp_path):
    motion = tmp_path / "motion.npz"
    source = tmp_path / "source.npz"
    terrain = tmp_path / "terrain.obj"
    motion.write_bytes(b"motion")
    source.write_bytes(b"source")
    terrain.write_bytes(b"terrain")
    payload = {
        "schema": "somaforge_motion_terrain_manifest_v1",
        "robot_asset_id": "robot.g1.spherehand",
        "kinematics_backend": "isaaclab3_newton_fk",
        "motion_files": [
            {
                "motion_id": 7,
                "motion_file": motion.name,
                "motion_sha256": _sha256(b"motion"),
                "source_file": source.name,
                "source_sha256": _sha256(b"source"),
                "terrain_id": 3,
                "kinematics_schema": "somaforge_canonical_motion_v1",
            }
        ],
        "terrains": [
            {
                "terrain_id": 3,
                "terrain_file": terrain.name,
                "terrain_sha256": _sha256(b"terrain"),
            }
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_canonical_manifest_validates_hashes_and_preserves_metadata(tmp_path) -> None:
    payload = load_motion_terrain_manifest(str(_manifest(tmp_path)))

    assert payload["motion_files"][0]["motion_id"] == 7
    assert payload["motion_files"][0]["kinematics_schema"] == "somaforge_canonical_motion_v1"
    assert payload["terrains"][0]["terrain_sha256"] == _sha256(b"terrain")


def test_canonical_manifest_rejects_changed_motion(tmp_path) -> None:
    path = _manifest(tmp_path)
    (tmp_path / "motion.npz").write_bytes(b"changed")

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        load_motion_terrain_manifest(str(path))
