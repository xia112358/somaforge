"""Expert-only frame-count warmup before joint Newton trajectory training."""
import json

import torch
from torch.nn import functional as F


def expert_features(model, records, device):
    if not records or any(r['kind'] != 'demonstration' for r in records):
        raise ValueError('Frame targets must come exclusively from expert segments')
    values=[]
    for first in range(0,len(records),128):
        rows=records[first:first+128]
        start=torch.stack([r['q'][0] for r in rows]).to(device)
        end=torch.stack([r['q'][-1] for r in rows]).to(device)
        contract={k:torch.stack([r['contract'][k] for r in rows]).to(device) for k in rows[0]['contract']}
        scene={k:torch.stack([r['scene'][k] for r in rows]).to(device) for k in rows[0]['scene']}
        with torch.no_grad():values.append(model.boundary_features(start,end,contract,scene)[0])
    target=torch.tensor([len(r['q']) for r in records],device=device,dtype=values[0].dtype)
    seconds=torch.stack([r['duration'] for r in records]).to(device)
    if not torch.allclose(target,1+50*seconds,rtol=1e-6,atol=1e-5):
        raise ValueError('Expert frame counts must agree with 50 Hz durations')
    return torch.cat(values),target


def warmup_frame_head(model, training, validation, cfg, device):
    train=[r for r in training if r['kind']=='demonstration']
    val=[r for r in validation if r['kind']=='demonstration']
    x,y=expert_features(model,train,device);vx,vy=expert_features(model,val,device)
    optimizer=torch.optim.Adam(model.frame_head.parameters(),lr=.001)
    generator=torch.Generator(device=device).manual_seed(cfg.seed)
    initial_decoder={k:v.detach().clone() for k,v in model.network.state_dict().items()}
    decoupled=model.frame_training=='decoupled'
    best=float('inf');best_state=None;history=[]
    for step in range(cfg.frame_warmup_steps+1):
        if step:
            indices=torch.randint(len(x),(128,),device=device,generator=generator)
            count=model.frame_count_from_features(x[indices])
            loss=(F.smooth_l1_loss(count,y[indices]) if decoupled
                else F.smooth_l1_loss(count.log(),y[indices].log()))
            optimizer.zero_grad(set_to_none=True);loss.backward()
            torch.nn.utils.clip_grad_norm_(model.frame_head.parameters(),10,error_if_nonfinite=True)
            optimizer.step()
        if step%250==0 or step==cfg.frame_warmup_steps:
            with torch.no_grad():
                predicted=model.frame_count_from_features(vx)
                score=float((predicted-vy).abs().mean()) if decoupled else float(F.smooth_l1_loss(predicted.log(),vy.log()))
                record=dict(stage='frame_warmup',step=step,validation_log_loss=score,
                    validation_mae_frames=float((predicted.round()-vy).abs().mean()),
                    train_experts=len(train),validation_experts=len(val),test_used=False)
                if decoupled:
                    record.pop('validation_log_loss')
                    record.update(validation_mae_continuous_frames=score,
                        validation_p95_error_frames=float(torch.quantile((predicted.round()-vy).abs(),.95)))
            if score<best:
                best=score;best_state={k:v.detach().clone() for k,v in model.frame_head.state_dict().items()}
                best_step=step
            history.append(record)
            print(json.dumps(record),flush=True)
            (cfg.report/'frame_warmup_progress.json').write_text(json.dumps(record,indent=2)+'\n')
    model.frame_head.load_state_dict(best_state)
    if any(not torch.equal(v,model.network.state_dict()[k]) for k,v in initial_decoder.items()):
        raise AssertionError('Frame warmup altered trajectory parameters')
    result=dict(best_step=best_step,history=history,
        target='expert total frame count including endpoints at 50 Hz',test_used=False)
    result['best_validation_mae_continuous_frames' if decoupled else 'best_validation_log_loss']=best
    (cfg.output/'frame_warmup.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
