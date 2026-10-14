import json
from pathlib import Path
import numpy as np
import torch
import pytest
from generator.research.archived_experiments.direct_contact_infiller import DirectContactInfiller
from generator.research.archived_experiments.full_shared_contact_model import batch

ROOT = Path(__file__).absolute().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT/'runtime/current/archives/preserved_inputs_20261010/dropout207_training_v1/corpus.pt').exists(),
                               reason='Requires explicitly built local 207-trajectory training corpus')


def test_direct_infiller_supervision_is_not_input():
    torch.set_num_threads(1)
    payload = torch.load(ROOT/'runtime/current/archives/preserved_inputs_20261010/dropout207_training_v1/corpus.pt', weights_only=False, map_location='cpu')
    record = min(payload['records'], key=lambda r:len(r['base']))
    limits = json.loads((ROOT/'configs/climb00/direct_infiller_v1.json').read_text())['smoothness_limits']
    model = DirectContactInfiller(limits)
    b = batch([record], 'cpu')
    q = model.decode(b)
    changed = {**b, 'base':b['base'].clone(), 'task_contact_mask':~b['task_contact_mask'],
               'task_contact_position_w':b['task_contact_position_w']+10}
    changed['base'][:,1:-1] += .1
    torch.testing.assert_close(model.decode(changed), q, rtol=0, atol=0)
    torch.testing.assert_close(q[:,[0,-1]], b['base'][:,[0,-1]], rtol=0, atol=0)
    model.prepare(b)
    torch.testing.assert_close(b['prepared']['desired'], b['task_contact_mask'])
    loss, _, _ = model.objective(b)
    assert torch.isfinite(loss).all()
    loss.mean().backward()
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.network.parameters())


def test_preserved_dataset_split_and_asset_identity():
    from somaforge_core.robot_assets import decode_robot_asset_json
    root = ROOT/'runtime/current/archives/preserved_inputs_20261010/dropout207_training_v1'
    payload = torch.load(root/'corpus.pt', weights_only=False, map_location='cpu')
    decode_robot_asset_json(payload['robot_asset_json'], context='preserved regression corpus')
    ownership = {}
    for row in payload['records']:
        # This is a preserved historical experiment, not newly certified data.
        assert row['event_contract'] == payload['event_contract']
        assert ownership.setdefault(row['sequence'],row['split']) == row['split']
    assert len(ownership) == 207
    assert payload['frozen_predictor'] is None and payload['frozen_infiller'] is None
