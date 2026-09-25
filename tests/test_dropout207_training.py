import json
from pathlib import Path
import numpy as np
import torch
import pytest
from direct_contact_infiller import DirectContactInfiller
from full_shared_contact_model import batch

ROOT = Path(__file__).absolute().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT/'tmp/dropout207_training_v1/corpus.pt').exists(),
                               reason='Requires explicitly built local 207-trajectory training corpus')


def test_direct_infiller_supervision_is_not_input():
    torch.set_num_threads(1)
    payload = torch.load(ROOT/'tmp/dropout207_training_v1/corpus.pt', weights_only=False, map_location='cpu')
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


def test_dataset_split_and_cache_identity():
    from somaforge_core.contact_dataset import validate_contact_cache
    from somaforge_core.contact_events import event_contract
    root = ROOT/'tmp/dropout207_training_v1'
    with np.load(root/'q_cache.npz') as cache:
        validate_contact_cache(cache, root/'manifest.json')
    payload = torch.load(root/'corpus.pt', weights_only=False, map_location='cpu')
    ownership = {}
    for row in payload['records']:
        assert row['event_contract'] == event_contract(50)
        assert ownership.setdefault(row['sequence'],row['split']) == row['split']
    assert len(ownership) == 207
    assert payload['frozen_predictor'] is None and payload['frozen_infiller'] is None
