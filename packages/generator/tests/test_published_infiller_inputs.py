"""Relocation fixes saved input identities without relaxing Infiller checks."""
import json
import shutil
from types import SimpleNamespace

import pytest
import torch

from generator import train_frozen_predictor_infiller as trainer
from somaforge_core import published_data
from somaforge_core.robot_assets import encode_robot_asset_json


def relocated_copy(tmp_path, monkeypatch, source):
    target = tmp_path / "other_disk/inputs"
    shutil.copytree(source, target)
    mapping = tmp_path / "installed_mapping.json"
    mapping.write_text(json.dumps({"schema": published_data.SCHEMA, "prefixes": [
        {"source": str(source), "target": str(target)}]}))
    # Keep the real canonical asset root; only this test's install metadata is
    # redirected. Asset identity validation itself is never mocked.
    monkeypatch.setattr(published_data, "_mapping_path", lambda: mapping)
    return target


def test_checkpoint_and_parent_corpus_compare_actual_relocated_file_evidence(tmp_path, monkeypatch):
    source = tmp_path / "original"
    source.mkdir()
    predictor = source / "predictor.pt"
    predictor.write_bytes(b"fixed predictor content for evidence hashing")
    parent = source / "parent.pt"
    torch.save({"records": [], "predictor": trainer.evidence(predictor)}, parent)
    corpus = source / "extended.pt"
    torch.save({"records": [], "predictor": trainer.evidence(predictor),
                "parent_corpus": trainer.evidence(parent)}, corpus)
    checkpoint = source / "infiller.pt"
    torch.save({"corpus": trainer.evidence(parent), "predictor": trainer.evidence(predictor),
                "model": {"weight": torch.arange(3.)}, "optimizer": {"step": torch.tensor(4)},
                "scene_fingerprints": {"0": "immutable-native-fingerprint"},
                "config": {"corpus": corpus}}, checkpoint)
    before = {path.name: path.read_bytes() for path in source.iterdir()}
    target = relocated_copy(tmp_path, monkeypatch, source)
    saved = trainer.load_published_infiller_input(checkpoint)
    data = trainer.load_published_infiller_input(corpus)
    assert saved["predictor"] == trainer.evidence(target / "predictor.pt") == data["predictor"]
    assert trainer.checkpoint_corpus_matches(saved, data, corpus)
    assert saved["config"]["corpus"] == target / "extended.pt"
    assert saved["scene_fingerprints"] == {"0": "immutable-native-fingerprint"}
    torch.testing.assert_close(saved["model"]["weight"], torch.arange(3.))
    assert {path.name: path.read_bytes() for path in source.iterdir()} == before
    assert {path.name: path.read_bytes() for path in target.iterdir()} == before
    (target / "parent.pt").write_bytes(b"changed parent corpus")
    assert not trainer.checkpoint_corpus_matches(saved, data, corpus)


def test_loader_does_not_traverse_model_optimizer_or_record_payloads(monkeypatch):
    weight = torch.arange(4.)
    model = {"weight": weight}
    optimizer = {"state": {0: {"exp_avg": weight}}}
    records = [{"q": weight, "source_record": "/unchanged/record/metadata"}]
    payload = {"model": model, "optimizer": optimizer, "records": records,
               "scene_fingerprints": {"0": "same"}, "predictor": {"path": "/old/predictor.pt", "sha256": "same-hash"}}
    monkeypatch.setattr(trainer.torch, "load", lambda *args, **kwargs: payload)
    loaded = trainer.load_published_infiller_input("/unused/input.pt")
    assert loaded["model"] is model
    assert loaded["optimizer"] is optimizer
    assert loaded["records"] is records
    assert loaded["model"]["weight"] is weight


@pytest.mark.parametrize("fault", [None, "contact_semantics", "heldout", "asset"])
def test_relocated_material_source_preserves_asset_contact_and_split_checks(tmp_path, monkeypatch, fault):
    from contact_solver import contact_regions

    source = tmp_path / "original_material_inputs"
    source.mkdir()
    predictor = source / "predictor.pt"
    predictor.write_bytes(b"predictor evidence")
    asset = encode_robot_asset_json()
    parent = source / "material_source.pt"
    torch.save({"robot_asset_json": asset, "predictor": trainer.evidence(predictor),
                "records": [{"split": "train", "sample_id": 1}, {"split": "validation", "sample_id": 2}]}, parent)
    corpus = source / "corpus.pt"
    torch.save({"robot_asset_json": asset, "predictor": trainer.evidence(predictor),
                "material_source_corpus": trainer.evidence(parent),
                "records": [{"split": "train", "sample_id": 1}]}, corpus)
    bank = source / "materials.pt"
    metadata = {"contact_semantics": trainer.NEWTON_CONTACT_SCHEMA, "face_selection": trainer.FACE_POLICY,
                "link_names": ["foot"], "source_ids": [2 if fault == "heldout" else 1], "source_contact_count": 0}
    if fault == "contact_semantics":
        metadata["contact_semantics"] = "old-geometry-only"
    torch.save({"robot_asset_json": '{}' if fault == "asset" else asset, "metadata": metadata,
                "buffers": {"known": torch.zeros(6, 1, dtype=torch.bool)}}, bank)
    baseline = source / "baseline.json"
    baseline.write_text(json.dumps({"training_geometry_materials": {"contact_material_skin.pt": trainer.evidence(bank)}}))
    before = {path.name: path.read_bytes() for path in source.iterdir()}
    target = relocated_copy(tmp_path, monkeypatch, source)
    monkeypatch.setattr(contact_regions, "ContactRegions", lambda fk: SimpleNamespace(
        valid=torch.zeros(6, 1, dtype=torch.bool), names=(("region",),) * 6))
    loaded = trainer.load_published_infiller_input(corpus)
    args = (SimpleNamespace(fk=object()), loaded, SimpleNamespace(baseline=baseline), SimpleNamespace(names=("foot",)))
    if fault is None:
        result = trainer.attach_shared_materials(*args)
        assert result["inherited_training_corpus"] == trainer.evidence(target / "material_source.pt")
        assert result["evidence"] == trainer.evidence(target / "materials.pt")
    else:
        match = {"contact_semantics": "rematerialization", "heldout": "held-out", "asset": "incompatible robot asset"}[fault]
        with pytest.raises(ValueError, match=match):
            trainer.attach_shared_materials(*args)
    assert {path.name: path.read_bytes() for path in source.iterdir()} == before
    assert {path.name: path.read_bytes() for path in target.iterdir()} == before
