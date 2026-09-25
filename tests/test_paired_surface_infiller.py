import copy
import json
from pathlib import Path
import torch
import pytest
from direct_surface_infiller import DirectSurfaceInfiller
from full_shared_contact_model import batch


@pytest.mark.parametrize('kind',['demonstration','predictor_intent'])
def test_endpoints_gradients_and_supervision_not_input(kind):
    torch.set_num_threads(2)
    path=Path('tmp/paired_surface_v1/corpus_smoke_all_splits/corpus.pt')
    if not path.exists():pytest.skip('paired smoke corpus not built')
    payload=torch.load(path,map_location='cpu',weights_only=False)
    record=min((r for r in payload['records'] if r['supervision_kind']==kind),key=lambda r:len(r['base']))
    limits=json.loads(Path('configs/climb00/direct_infiller_v1.json').read_text())['smoothness_limits']
    model=DirectSurfaceInfiller(limits)
    b=batch([record],'cpu')
    q=model.decode(b)
    assert torch.equal(q[:,0],b['base'][:,0]) and torch.equal(q[:,-1],b['base'][:,-1])
    altered=copy.deepcopy(b);altered['base'][:,1:-1]=torch.randn_like(altered['base'][:,1:-1])
    altered['reference_rotation']=torch.randn_like(altered['reference_rotation'])
    if 'task_contact_mask' in altered:altered['task_contact_mask']=~altered['task_contact_mask']
    torch.testing.assert_close(model.decode(altered),q,atol=0,rtol=0)
    loss,_,metrics=model.objective(b)
    assert torch.isfinite(loss).all()
    assert 'actual_contact_mean_cm' not in metrics
    assert bool(metrics['realized_label_supervision'][0]) == (kind=='demonstration')
    loss.mean().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.network.parameters())


def test_no_mixing_intents_and_actual_labels():
    path=Path('tmp/paired_surface_v1/corpus_smoke_all_splits/corpus.pt')
    if not path.exists():pytest.skip('paired smoke corpus not built')
    p=torch.load(path,map_location='cpu',weights_only=False)
    r=p['records'][0];s=copy.deepcopy(r);s['supervision_kind']='predictor_intent'
    with pytest.raises(ValueError,match='mix'):batch([r,s],'cpu')
