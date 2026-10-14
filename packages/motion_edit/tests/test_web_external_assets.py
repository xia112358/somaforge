"""Data relocation must preserve URLs without exposing undeclared directories."""
import json

import pytest
from fastapi.testclient import TestClient

from motion_edit.web import server


@pytest.fixture
def external_assets(tmp_path, monkeypatch):
    checkout, data = tmp_path / "code", tmp_path / "data"
    (checkout / "configs").mkdir(parents=True)
    (checkout / "runtime").mkdir()
    data.mkdir()
    (checkout / "runtime/current").symlink_to(data, target_is_directory=True)
    (checkout / "configs/assets_manifest.json").write_text(json.dumps({
        "schema": "somaforge_asset_manifest_v1", "root": "..",
        "external_roots": ["runtime/current"], "assets": [],
    }))
    (data / "motion.json").write_text('{"fixture":true}')
    (checkout / "source.txt").write_text("source fixture")
    secret = tmp_path / "secret.txt"
    secret.write_text("not public")
    (data / "escape.txt").symlink_to(secret)
    (checkout / "unregistered").symlink_to(data, target_is_directory=True)
    monkeypatch.setattr(server, "somaforge_root", lambda: checkout)
    return checkout, data, secret


def test_external_files_use_declared_logical_url_and_remain_readable(external_assets):
    checkout, data, secret = external_assets
    assert server._repo_url(data / "motion.json") == "/repo/runtime/current/motion.json"
    assert server._repo_url(checkout / "source.txt") == "/repo/source.txt"
    with TestClient(server.create_app()) as client:
        response = client.get(server._repo_url(data / "motion.json"))
        assert response.status_code == 200
        assert response.json() == {"fixture": True}
        assert client.get("/repo/source.txt").text == "source fixture"


def test_external_static_mount_rejects_symlink_and_directory_escapes(external_assets):
    checkout, data, secret = external_assets
    with pytest.raises(ValueError, match="outside declared roots"):
        server._repo_url(secret)
    with TestClient(server.create_app()) as client:
        for path in ("/repo/runtime/current/escape.txt", "/repo/unregistered/motion.json",
                     "/repo/runtime/current/%2e%2e/secret.txt"):
            assert client.get(path).status_code == 404
