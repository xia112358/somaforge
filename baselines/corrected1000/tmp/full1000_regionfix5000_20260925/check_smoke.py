import json
from pathlib import Path
import torch

root=Path(__file__).resolve().parent
a=torch.load(root/'smoke_adapter1/last.pt',map_location='cpu',weights_only=False)
b=torch.load(root/'smoke_parallel2/last.pt',map_location='cpu',weights_only=False)
state=torch.load(root/'smoke_parallel2/parallel_training_state.pt',map_location='cpu',weights_only=False)
history=json.loads((root/'smoke_parallel2/progress.json').read_text())['history']
assert a['step']==1 and b['step']==2 and state['step']==2
assert b['dataset']['contact_position_contract']=='observed_endpoint_region_geometry_v3'
assert b['config']['event_roles'] and not b['config']['recover_failed_states'] and not b['config']['pending_plan_repair']
assert not state['pool']['retries'].any() and state['pending_plan'] is None
for checkpoint in (a,b):
    assert all(torch.isfinite(v).all() for v in checkpoint['model'].values())
for row in history:
    assert row['teacher_probability']==0
    for key in ('loss','optimized_loss','mean_gradient_norm_before_clip'):
        assert __import__('math').isfinite(row[key]),key
    assert row['mean_gradient_norm_before_clip']>0
    assert row['parallel_pool']['retries']==0
    assert row['metrics']['region_gradient_valid']>0
assert not torch.equal(a['model']['role_head.weight'],b['model']['role_head.weight'])
assert not torch.equal(a['model']['execution_role_encoder.weight'],b['model']['execution_role_encoder.weight'])
assert not torch.equal(a['model']['pose_head.weight'],b['model']['pose_head.weight'])
result=dict(runtime_validation_passed=True,checkpoint_finite=True,autonomous_updates=True,
    planner_updated=True,executor_updated=True,execution_role_embedding_updated=True,
    no_retries=True,no_pending_plan=True,predictions=state['training_predictions'],
    last_pool=history[-1]['parallel_pool'],smoke_weights_used_for_formal_training=False)
(root/'READY_FOR_TRAINING.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
