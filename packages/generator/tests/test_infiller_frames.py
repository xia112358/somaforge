import pytest
import torch

from generator.direct_infiller import (DirectInfiller, frame_objective, generate_segment,
    load_infiller, prepare_frame_prediction, regularized_motion_objective)
from generator.infiller_frame_training import expert_features
from generator.trajectory_budget import derivative_metrics


def inputs(model):
    a=torch.zeros(1,36);a[:,3]=1
    a[:,7:]=(model.fk.joint_lower+model.fk.joint_upper)/2
    z=a.clone();z[:,0]=.2;z[:,3]=-1
    contract={k:torch.zeros(1,6,3) for k in ('start_anchor','end_anchor','end_local_offset')}
    contract.update({k:torch.zeros(1,6) for k in
        ('start_contact','end_contact','keep','start_surface','end_surface')})
    scene=dict(box_center=torch.tensor([[2.,0.,.3]]),box_rotation=torch.eye(3)[None],
        box_half_extents=torch.ones(1,3)*.3,ground_height=torch.zeros(1))
    return a,z,contract,scene


def test_predicted_frames_control_length_and_ignore_external_duration():
    model=DirectInfiller(predict_frames=True)
    a,z,c,s=inputs(model)
    q,meta=generate_segment(model,a,z,c,s,duration=99)
    assert len(q)==51 and meta['duration_s']==1
    assert torch.equal(q[0],a[0]) and torch.equal(q[-1],z[0])
    with torch.no_grad():model.frame_head[-1].bias.fill_(-2)
    short,meta=generate_segment(model,a,z,c,s,duration=99)
    assert len(short)==10 and meta['duration_s']==pytest.approx(.18)
    assert torch.equal(short[-1],z[0])
    with torch.no_grad():model.frame_head[-1].bias.fill_(1e4)
    with pytest.raises(ValueError,match='resource range'):
        generate_segment(model,a,z,c,s)


def test_frame_labels_are_expert_only_and_generated_fake_lengths_have_no_effect():
    predicted=torch.tensor([30.,80.],requires_grad=True)
    batch=dict(predicted_frames=predicted,demo=torch.tensor([True,False]),
        reference_duration=torch.tensor([.5,1.]),duration=(predicted-1)/50)
    supervised,efficiency,_=frame_objective(batch)
    batch['reference_duration'][1]=1000
    new,other,_=frame_objective(batch)
    torch.testing.assert_close(new,supervised);torch.testing.assert_close(other,efficiency)
    supervised.backward(retain_graph=True)
    assert predicted.grad[0]!=0 and predicted.grad[1]==0
    predicted.grad.zero_();efficiency.backward()
    assert predicted.grad[0]==0 and predicted.grad[1]>0  # Longer unknown motion has a cost.
    batch['demo']=torch.zeros(2,dtype=torch.bool)
    assert frame_objective(batch)[2]['frame_mae'] is None  # Unknown accuracy is not zero error.


def test_joint_duration_gradient_is_finite_and_expert_budget_stays_at_reference_time():
    model=DirectInfiller(predict_frames=True,frame_training='joint');a,z,c,s=inputs(model)
    phase=torch.linspace(0,1,9)[None,:,None]
    reference=model(a,z,phase,c,s,torch.tensor([.16])).detach()
    batch=dict(q=reference,phase=phase,contract=c,scene=s,duration=torch.tensor([.16]),
        demo=torch.tensor([True]))
    prepare_frame_prediction(model,batch)
    assert float(batch['reference_duration'][0])==pytest.approx(.16)
    q=model(a,z,phase,c,s,batch['duration'])
    limits={k:torch.tensor(1e-8) for k in derivative_metrics(q,batch['duration'])}
    _,smooth,_=regularized_motion_objective(model,batch,q,limits)
    loss=frame_objective(batch)[0]+smooth
    loss.backward()
    assert torch.isfinite(model.frame_head[-1].bias.grad).all()
    assert model.frame_head[-1].bias.grad.abs().sum()>0


def test_generated_feasibility_does_not_use_fixed_one_second_reference():
    model=DirectInfiller(predict_frames=True);a,z,c,s=inputs(model)
    phase=torch.linspace(0,1,9)[None,:,None]
    q=model(a,z,phase,c,s,torch.ones(1))
    limits={k:torch.tensor(1e-5) for k in derivative_metrics(q,torch.ones(1))}
    batch=dict(q=q.detach(),duration=torch.ones(1),reference_duration=torch.ones(1),
        predicted_frames=torch.tensor([51.]),demo=torch.tensor([False]))
    _,left,_=regularized_motion_objective(model,batch,q,limits)
    batch['reference_duration']=torch.tensor([100.])
    _,right,_=regularized_motion_objective(model,batch,q,limits)
    torch.testing.assert_close(left,right)
    assert left>0


def test_frame_checkpoint_requires_matching_architecture_and_old_loader_still_works():
    model=DirectInfiller(predict_frames=True)
    with pytest.raises(ValueError,match='metadata/state mismatch'):
        load_infiller(dict(model=model.state_dict()),'cpu')
    restored=load_infiller(dict(model=model.state_dict(),architecture=dict(predicts_frames=True)),'cpu')
    assert restored.frame_training=='joint'  # Preserve historical frame checkpoints.
    decoupled=load_infiller(dict(model=model.state_dict(),architecture=dict(
        predicts_frames=True,frame_training='decoupled')),'cpu')
    assert decoupled.frame_training=='decoupled'
    args=inputs(model)
    torch.testing.assert_close(model.frame_count(*args),restored.frame_count(*args))
    old=load_infiller(dict(model=DirectInfiller().state_dict()),'cpu')
    assert not old.predicts_frames


def test_warmup_refuses_generated_timing_labels():
    model=DirectInfiller(predict_frames=True)
    with pytest.raises(ValueError,match='exclusively from expert'):
        expert_features(model,[dict(kind='predictor_recursive')],'cpu')


def test_decoupled_motion_cannot_update_frame_head_but_remains_time_conditioned():
    model=DirectInfiller(predict_frames=True);a,z,c,s=inputs(model)
    with torch.no_grad():model.network[-1].weight.normal_(0,.01)
    phase=torch.linspace(0,1,9)[None,:,None]
    reference=model(a,z,phase,c,s,torch.tensor([.16])).detach()
    b=dict(q=reference,phase=phase,contract=c,scene=s,duration=torch.tensor([.16]),demo=torch.tensor([True]))
    prepare_frame_prediction(model,b)
    assert b['predicted_frames'].requires_grad
    assert not b['duration'].requires_grad and not b['motion_frames'].requires_grad
    q=model(a,z,phase,c,s,b['duration'])
    limits={k:torch.tensor(1e-8) for k in derivative_metrics(q,b['duration'])}
    pose,smooth,_=regularized_motion_objective(model,b,q,limits)
    (pose+smooth).backward()
    assert all(p.grad is None for p in model.frame_head.parameters())
    assert model.network[-1].weight.grad.abs().sum()>0
    assert not torch.allclose(q,model(a,z,phase,c,s,torch.tensor([2.])))
    model.zero_grad(set_to_none=True)
    supervised,efficiency,_=frame_objective(b)
    assert efficiency==0
    supervised.backward()
    assert model.frame_head[-1].bias.grad.abs().sum()>0


def test_decoupled_generated_records_have_no_time_objective_gradient():
    predicted=torch.tensor([30.,80.],requires_grad=True)
    b=dict(predicted_frames=predicted,frame_training='decoupled',demo=torch.tensor([False,False]),
        reference_duration=torch.tensor([1.,1000.]),duration=(predicted.detach()-1)/50)
    supervised,efficiency,metrics=frame_objective(b)
    (supervised+efficiency).backward()
    assert torch.equal(predicted.grad,torch.zeros_like(predicted))
    assert metrics['frame_mae'] is None


@pytest.mark.parametrize('mode',['joint','decoupled'])
def test_seam_phase_sampling_respects_time_gradient_mode(mode):
    from generator.direct_infiller import collate,decode_batch
    from generator.recursive_refinement import seam_objective
    model=DirectInfiller(predict_frames=True,frame_training=mode)
    a,z,c,s=inputs(model);end=z.clone();end[:,0]+=.4
    phase=torch.linspace(0,1,9)[None,:,None]
    rows=[]
    for start,finish in [(a,z),(z,end)]:
        q=model(start,finish,phase,c,s,torch.tensor([.16]))[0].detach()
        rows.append(dict(q=q,active=torch.zeros(9,6,dtype=torch.bool),surface=torch.zeros(9,6,dtype=torch.long),
            material=torch.zeros(9,6,3),material_link=torch.zeros(9,6,dtype=torch.long),margin=torch.zeros(9,6),
            duration=torch.tensor(.16),scene_id=torch.tensor(0),kind='demonstration',
            contract={k:v[0] for k,v in c.items()},scene={k:v[0] for k,v in s.items()}))
    b=prepare_frame_prediction(model,collate([rows[0]],'cpu'));q=decode_batch(model,b)
    loss,pairs=seam_objective(model,rows,[0],{0:1},q,'cpu')
    assert pairs==1
    loss.backward()
    if mode=='decoupled':
        assert all(p.grad is None for p in model.frame_head.parameters())
    else:
        assert model.frame_head[-1].bias.grad.abs().sum()>0
    assert model.network[-1].weight.grad.abs().sum()>0
