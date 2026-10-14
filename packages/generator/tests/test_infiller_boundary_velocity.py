import pytest
import torch

from generator.direct_infiller import DirectInfiller, generate_segment, load_infiller
from generator.infiller_boundary_velocity import (finite_difference_velocity, hermite_pose,
    relative_rotation, rotation_exp, velocity_objective, SelfGeneratedHistory)
from test_infiller_frames import inputs


def test_hermite_preserves_physical_boundary_velocities_and_quaternion_signs():
    model=DirectInfiller(boundary_velocity=True).double()
    a,z,c,s=inputs(model); a,z=a.double(),z.double()
    z[:,3:7]=-rotation_exp(torch.tensor([[.3,-.2,.7]],dtype=torch.double))
    initial=torch.linspace(-.1,.1,35,dtype=torch.double)[None]
    terminal=-initial
    phase=torch.tensor([0.,1e-6,1-1e-6,1.],dtype=torch.double)[None,:,None]
    q=hermite_pose(a,z,phase,torch.tensor([.8],dtype=torch.double),initial,terminal,
                   torch.zeros(1,4,36,dtype=torch.double))
    torch.testing.assert_close(q[:,0,:3],a[:,:3])
    torch.testing.assert_close(q[:,-1,:3],z[:,:3])
    torch.testing.assert_close(q[...,3:7].norm(dim=-1),torch.ones(1,4,dtype=torch.double))
    torch.testing.assert_close(relative_rotation(q[:,-1,3:7],z[:,3:7]),torch.zeros(1,3,dtype=torch.double),atol=1e-12,rtol=0)
    torch.testing.assert_close(finite_difference_velocity(q[:,:2],.8e-6),initial,atol=1e-5,rtol=1e-4)
    torch.testing.assert_close(finite_difference_velocity(q[:,-2:],.8e-6),terminal,atol=1e-5,rtol=1e-4)


@pytest.mark.parametrize('angle',[0.,1e-8,torch.pi-1e-5])
def test_rotation_identity_and_near_pi_have_finite_gradients(angle):
    vector=torch.tensor([[angle,0.,0.]],requires_grad=True)
    quaternion=rotation_exp(vector)
    identity=torch.tensor([[1.,0.,0.,0.]])
    result=relative_rotation(identity,quaternion)
    torch.testing.assert_close(result,vector)
    result.sum().backward()
    assert torch.isfinite(vector.grad).all()


def test_velocity_decoder_keeps_boundaries_time_independence_and_supplied_history():
    model=DirectInfiller(predict_frames=True,boundary_velocity=True)
    a,z,c,s=inputs(model)
    incoming=torch.ones(1,35)*.1
    _,_,estimate,known=model.boundary_velocities(a,z,c,s,torch.ones(1),incoming)
    assert known.all()
    q,meta=generate_segment(model,a,z,c,s,start_velocity=incoming)
    assert torch.equal(q[0],a[0]) and torch.equal(q[-1],z[0])
    torch.testing.assert_close(q[:,3:7].norm(dim=-1),torch.ones(len(q)))
    assert meta['initial_velocity']==pytest.approx(incoming[0].tolist())
    phase=torch.linspace(0,1,17)[None,:,None]
    seconds=(model.frame_count(a,z,c,s)-1)/50
    decoded=model(a,z,phase,c,s,seconds,start_velocity=incoming)
    decoded.square().sum().backward()
    assert all(p.grad is None for p in model.frame_head.parameters())
    assert model.terminal_velocity_head[-1].weight.grad.abs().sum()>0
    for history in (None,incoming):
        torch.testing.assert_close(model.frame_count(a,z,c,s),torch.tensor([51.]))
    saved=dict(model=model.state_dict(),architecture=dict(predicts_frames=True,
        frame_training='decoupled',boundary_velocity=True))
    restored=load_infiller(saved,'cpu')
    torch.testing.assert_close(generate_segment(restored,a,z,c,s,start_velocity=incoming)[0],q)


def test_generated_placeholder_interiors_cannot_supply_history_or_velocity_labels():
    class BoundaryOnly(torch.nn.Module):
        predicts_frames=False
        conditions_on_velocity=True
        def forward(self,start,end,phase,contract,scene,duration,**kwargs):
            return start[:,None]+phase*(end-start)[:,None]
    model=BoundaryOnly()
    start=torch.zeros(36);start[3]=1
    def record(a,z,current,target):
        q=torch.stack((a,torch.ones_like(a)*999,z))
        return dict(q=q,kind='predictor_recursive',split='train',chain_id='chain',
            scene_id=torch.tensor(0),current_frame=current,target_frame=target,
            duration=torch.tensor(.04),scene={},contract={},active=torch.zeros(3,6,dtype=torch.bool),
            surface=torch.zeros(3,6,dtype=torch.long),material=torch.zeros(3,6,3),
            material_link=torch.zeros(3,6,dtype=torch.long),margin=torch.ones(3,6))
    middle=start.clone();middle[0]=.04
    end=middle.clone();end[0]=.08
    records=[record(start,middle,0,2),record(middle,end,2,4)]
    history=SelfGeneratedHistory(model,records,'cpu')
    assert history.incoming(0) is None
    incoming=history.incoming(1)
    assert incoming[0,0]==pytest.approx(1.)
    records[0]['q'][1].fill_(-1e6)
    torch.testing.assert_close(SelfGeneratedHistory(model,records,'cpu').incoming(1),incoming)
    loss,metrics=velocity_objective(model,dict(q=records[0]['q'][None],demo=torch.tensor([False])))
    assert loss==0 and metrics['boundary_velocity_supervision'] is None


def test_mixed_supervision_never_uses_generated_velocity_targets():
    model=DirectInfiller(boundary_velocity=True)
    a,z,c,s=inputs(model)
    phase=torch.linspace(0,1,9)[None,:,None]
    q=model(a,z,phase,c,s,torch.ones(1)).detach().expand(2,-1,-1).clone()
    batch=dict(q=q,demo=torch.tensor([True,False]),duration=torch.ones(2),
        contract={k:v.expand(2,*v.shape[1:]) for k,v in c.items()},
        scene={k:v.expand(2,*v.shape[1:]) for k,v in s.items()})
    loss,_=velocity_objective(model,batch)
    batch['q'][1].fill_(1e6)
    other,_=velocity_objective(model,batch)
    torch.testing.assert_close(loss,other)
