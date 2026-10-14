import torch

from generator.direct_infiller import DirectInfiller, regularized_motion_objective
from generator.trajectory_budget import boundary_cubic_reference, derivative_metrics
from generator.recursive_refinement import sampled_seam_budget_loss, seam_objective, adjacent_records


def test_segment_budget_uses_chosen_time_and_only_generated_endpoints():
    from test_infiller_frames import inputs
    model=DirectInfiller()
    a,z,_,_=inputs(model)
    z[:,0]=a[:,0]+2
    phase=torch.linspace(0,1,21)[None,:,None]
    reference=boundary_cubic_reference(a,z,phase)
    limits={k:torch.tensor(1e-7) for k in derivative_metrics(reference,torch.tensor([.4]))}
    batch=dict(q=reference.clone(),demo=torch.tensor([False]),phase=phase,
               duration=torch.tensor([.4]),reference_duration=torch.tensor([4.]),predicted_frames=torch.tensor([21.]))
    old=regularized_motion_objective(model,batch,reference,limits)[1]
    new=regularized_motion_objective(model,batch,reference,limits,witnessed_budgets=True)[1]
    assert old>0 and new==0
    batch['q'][:,1:-1]=1e6
    assert regularized_motion_objective(model,batch,reference,limits,witnessed_budgets=True)[1]==0
    batch['q']=reference.clone();batch['demo'].fill_(True)
    pose,smooth,_=regularized_motion_objective(model,batch,reference,limits,witnessed_budgets=True)
    assert pose==0 and smooth==0


def test_seam_budget_units_reference_floor_and_gradients():
    left=torch.zeros(1,2,36);left[...,3]=1;left[:,0,7]=-.02
    right=left.clone();right[:,0,7]=0;right[:,1,7]=.06
    dt=torch.tensor([.02])
    limits={k:torch.tensor(.001) for k in ('root_d2_peak','joint_d2_peak','rotation_matrix_d2_peak')}
    # The actual reference acceleration is permitted even above the old cap.
    assert sampled_seam_budget_loss(left,right,dt,dt,left,right,limits,1.5)==0
    # A linear reference has zero seam acceleration. Current acceleration is
    # .04 rad per native sample squared, with gradients through both sides.
    reference_right=right.clone();reference_right[:,1,7]=.02
    limits['joint_d2_peak']=torch.tensor(.04)
    assert sampled_seam_budget_loss(left,right,dt,dt,left,reference_right,limits,1.)==0
    limits['joint_d2_peak']=torch.tensor(.02)
    left.requires_grad_();right.requires_grad_()
    loss=sampled_seam_budget_loss(left,right,dt,dt,left.detach(),reference_right,limits,1.)
    loss.backward()
    assert loss>0 and left.grad.abs().sum()>0 and right.grad.abs().sum()>0
    assert torch.isfinite(left.grad).all() and torch.isfinite(right.grad).all()
    # Different sampling intervals preserve a fixed physical acceleration.
    other=right.detach().clone();other[:,1,7]=.2
    limits['joint_d2_peak']=torch.tensor(.06)
    assert sampled_seam_budget_loss(left.detach(),other,dt,dt*2,left.detach(),reference_right,limits,1.)<1e-10


def test_generated_seams_are_budgeted_without_interior_teachers_cached_or_scalar():
    from test_infiller_efficiency import chain_records
    from generator.infiller_efficiency import BoundaryRecordCache
    from generator.infiller_boundary_velocity import SelfGeneratedHistory
    from generator.direct_infiller import collate,prepare_frame_prediction,decode_batch
    torch.manual_seed(5)
    model=DirectInfiller(predict_frames=True,boundary_velocity=True,conditional_boundary=True,residual_extension=True)
    with torch.no_grad():model.terminal_velocity_head[-1].bias[6]=.5
    for p in model.frame_head.parameters():p.requires_grad_(False)
    records=chain_records(model);indices=[2,6]
    cache=BoundaryRecordCache(model,records,'cpu')
    history=SelfGeneratedHistory(model,records,'cpu',boundary_cache=cache)
    batch=prepare_frame_prediction(model,collate([records[i] for i in indices],'cpu'))
    history.condition(batch,indices);q=decode_batch(model,batch)
    limits={k:torch.tensor(1e-6) for k in ('root_d2_peak','joint_d2_peak','rotation_matrix_d2_peak')}
    successors=adjacent_records(records)
    old,count=seam_objective(model,records,indices,successors,q,'cpu',history=history)
    assert count==0 and old==0
    scalar,count=seam_objective(model,records,indices,successors,q,'cpu',history=history,derivative_limits=limits)
    cached,n=seam_objective(model,records,indices,successors,q,'cpu',history=history,boundary_cache=cache,derivative_limits=limits)
    assert count==n==2 and cached>0
    torch.testing.assert_close(scalar,cached)
    cached.backward(retain_graph=True)
    assert model.terminal_velocity_head[-1].weight.grad.abs().sum()>0
    assert model.initial_velocity_head[-1].weight.grad.abs().sum()>0
    gradients={k:p.grad.clone() for k,p in model.named_parameters() if p.grad is not None}
    model.zero_grad(set_to_none=True);scalar.backward()
    for k,p in model.named_parameters():
        if k in gradients:torch.testing.assert_close(p.grad,gradients[k],atol=1e-5,rtol=1e-4)
    for r in records:r['q'][1].fill_(-1e6)
    changed,n=seam_objective(model,records,indices,successors,q,'cpu',history=history,boundary_cache=cache,derivative_limits=limits)
    torch.testing.assert_close(changed,cached.detach())
    assert n==2 and all(p.grad is None for p in model.frame_head.parameters())
