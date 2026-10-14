import pytest
import torch
from generator.direct_infiller import DirectInfiller,load_infiller
from generator.infiller_boundary_velocity import velocity_objective,sample_expert_phase,finite_difference_velocity
from generator.recursive_refinement import sampled_seam_loss
from test_infiller_frames import inputs


def test_history_is_condition_and_pose_loss_reaches_initial_predictor():
    model=DirectInfiller(predict_frames=True,boundary_velocity=True,conditional_boundary=True,residual_extension=True)
    a,z,c,s=inputs(model);incoming=torch.ones(1,35)*2
    initial,_,estimate,known=model.boundary_velocities(a,z,c,s,torch.ones(1),incoming)
    assert known.all() and torch.equal(initial,estimate)
    assert not torch.equal(initial,incoming)
    # Enable a history-sensitive predictor and check it uses the conditioning.
    with torch.no_grad():model.initial_velocity_head[-1].weight.fill_(.01)
    first=model.boundary_velocities(a,z,c,s,torch.ones(1),incoming)[0]
    second=model.boundary_velocities(a,z,c,s,torch.ones(1),-incoming)[0]
    assert not torch.equal(first,second)
    phase=torch.linspace(0,1,11)[None,:,None]
    q=model(a,z,phase,c,s,torch.ones(1),incoming)
    assert torch.equal(q[:,0],a) and torch.equal(q[:,-1],z)
    q[:,1:-1].square().sum().backward()
    assert model.initial_velocity_head[-1].weight.grad.abs().sum()>0
    assert model.residual_extension.weight.grad.abs().sum()>0
    assert all(p.grad is None for p in model.frame_head.parameters())
    saved=dict(model=model.state_dict(),architecture=dict(predicts_frames=True,frame_training='decoupled',
        boundary_velocity=True,conditional_boundary=True,residual_extension=True))
    torch.testing.assert_close(load_infiller(saved,'cpu')(a,z,phase,c,s,torch.ones(1),incoming),q)


def test_extension_preserves_initial_decoder_and_can_exceed_old_amplitude():
    torch.manual_seed(5)
    old=DirectInfiller(boundary_velocity=True)
    new=DirectInfiller(boundary_velocity=True,residual_extension=True)
    new.load_state_dict(old.state_dict(),strict=False)
    features=torch.randn(1,8,182)
    torch.testing.assert_close(new.trajectory_residual(features),old.trajectory_residual(features))
    with torch.no_grad():new.residual_extension.bias[7]=3
    assert (new.trajectory_residual(features)[...,7]>1).all()


def test_sampled_velocity_targets_follow_chosen_time_and_exclude_generated_interiors():
    model=DirectInfiller(predict_frames=True,boundary_velocity=True,conditional_boundary=True)
    a,z,c,s=inputs(model)
    phase=torch.linspace(0,1,11)[None,:,None]
    expert=model(a,z,phase,c,s,torch.ones(1)).detach()
    batch=dict(q=expert.expand(2,-1,-1).clone(),demo=torch.tensor([True,False]),
        duration=torch.ones(2),motion_frames=torch.tensor([51.,51.]),
        contract={k:v.expand(2,*v.shape[1:]) for k,v in c.items()},
        scene={k:v.expand(2,*v.shape[1:]) for k,v in s.items()},
        start_velocity=torch.ones(2,35),velocity_known=torch.ones(2,dtype=torch.bool))
    loss,_=velocity_objective(model,batch)
    batch['q'][1].fill_(1e6)
    other,_=velocity_objective(model,batch)
    torch.testing.assert_close(loss,other)
    loss.backward()
    assert model.initial_velocity_head[-1].weight.grad.abs().sum()>0
    assert all(p.grad is None for p in model.frame_head.parameters())
    # Linear expert motion resampled to a different duration has the correct speed.
    expert=torch.zeros(1,11,36);expert[...,3]=1;expert[0,:,0]=torch.linspace(0,1,11)
    sampled=sample_expert_phase(expert,torch.tensor([0.,.01])[None,:,None])
    assert finite_difference_velocity(sampled,.02)[0,0].item()==pytest.approx(.5)


def test_expert_sampled_seam_change_is_not_penalized():
    left=torch.zeros(1,2,36);left[...,3]=1;left[:,0,7]=-.02
    right=left.clone();right[:,0,7]=0;right[:,1,7]=.06
    dt=torch.tensor([.02]);scale=torch.ones(36)
    assert sampled_seam_loss(left,right,dt,dt,scale).item()>0
    loss=sampled_seam_loss(left,right,dt,dt,scale,target_left=left,target_right=right)
    torch.testing.assert_close(loss,torch.zeros(1))


def test_conditional_cached_and_scalar_expert_seams_have_same_gradients():
    from generator.direct_infiller import collate,prepare_frame_prediction,decode_batch
    from generator.infiller_efficiency import BoundaryRecordCache
    from generator.infiller_boundary_velocity import SelfGeneratedHistory
    from generator.recursive_refinement import adjacent_records,seam_objective
    from test_infiller_efficiency import chain_records
    model=DirectInfiller(predict_frames=True,boundary_velocity=True,conditional_boundary=True,residual_extension=True)
    for p in model.frame_head.parameters():p.requires_grad_(False)
    records=chain_records(model)
    for r in records:
        r['kind']='demonstration';r['q'][1]=(r['q'][0]+r['q'][-1])/2
    indices=[2,6];cache=BoundaryRecordCache(model,records,'cpu')
    history=SelfGeneratedHistory(model,records,'cpu',boundary_cache=cache)
    batch=prepare_frame_prediction(model,collate([records[i] for i in indices],'cpu'))
    history.condition(batch,indices);q=decode_batch(model,batch);successors=adjacent_records(records)
    old,count=seam_objective(model,records,indices,successors,q,'cpu',history=history)
    new,new_count=seam_objective(model,records,indices,successors,q,'cpu',history=history,boundary_cache=cache)
    assert count==new_count==2
    torch.testing.assert_close(old,new)
    old.backward();grad={k:p.grad.clone() for k,p in model.named_parameters() if p.grad is not None}
    model.zero_grad(set_to_none=True);new.backward()
    for k,p in model.named_parameters():
        if k in grad:torch.testing.assert_close(p.grad,grad[k],atol=1e-5,rtol=1e-4)
    for r in records:r['kind']='predictor_recursive';r['q'][1].fill_(1e6)
    loss,count=seam_objective(model,records,indices,adjacent_records(records),q,'cpu',history=history,boundary_cache=cache)
    assert count==0 and loss.item()==0
