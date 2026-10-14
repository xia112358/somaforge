import pytest
import torch

from generator.direct_infiller import (DirectInfiller, contact_timing_metrics, seam_metrics,
    transfer_constraints,regularized_motion_objective)
from generator.train_frozen_predictor_infiller import validate_observed, supervision_records


def test_exact_boundaries_shortest_quaternion_and_finite_gradient():
    model=DirectInfiller()
    a=torch.zeros(1,36); a[:,3]=1
    a[:,7:]=(model.fk.joint_lower+model.fk.joint_upper)/2
    z=a.clone(); z[:,0]=.2; z[:,3]=-1
    contract={k:torch.zeros(1,6,3) for k in ('start_anchor','end_anchor','end_local_offset')}
    contract.update({k:torch.zeros(1,6) for k in ('start_contact','end_contact','keep','start_surface','end_surface')})
    scene=dict(box_center=torch.tensor([[2.,0.,.3]]),box_rotation=torch.eye(3)[None],
               box_half_extents=torch.ones(1,3)*.3,ground_height=torch.zeros(1))
    phase=torch.linspace(0,1,9)[None,:,None]
    with torch.no_grad(): model.network[-1].weight.fill_(.001)
    q=model(a,z,phase,contract,scene,torch.ones(1))
    assert torch.equal(q[:,0],a) and torch.equal(q[:,-1],z)
    torch.testing.assert_close(q[...,3:7].norm(dim=-1),torch.ones(1,9))
    q[:,1:-1,0].square().sum().backward()
    assert all(torch.isfinite(p.grad).all() for p in model.network.parameters())
    assert model.network[-1].weight.grad.abs().sum()>0


def test_timing_requires_same_surface_and_reports_unfiltered_interruptions():
    mask=torch.zeros(6,6,dtype=torch.bool); surface=torch.full((6,6),-1)
    mask[:,0]=True; surface[:,0]=torch.tensor([0,0,1,1,0,1])
    mask[:,1]=torch.tensor([True,True,False,True,False,True]); surface[:,1]=0
    role=torch.tensor([1,2,0,0,0,0]); start=torch.zeros(6,dtype=torch.long); end=start.clone(); end[0]=1
    rows=contact_timing_metrics(mask,surface,role,start,end,50)
    assert rows[0]['activation_frames']==[2,5]
    assert rows[0]['ending_episode_start_s']==.1
    assert rows[1]['keep_disconnects']==2
    assert rows[1]['keep_missing_sample_seconds']==.04
    assert rows[1]['keep_coverage']==pytest.approx(4/6)


def test_seam_does_not_align_mismatched_world_endpoints():
    a=torch.zeros(4,36); a[:,3]=1
    b=a.clone(); b[:,0]=.4; b[:,3]=-1
    metrics=seam_metrics(a,b,50)
    assert metrics['root_position_jump_m']==pytest.approx(.4)
    assert metrics['root_rotation_jump_rad']==0


def test_unallocated_newton_contact_fails_instead_of_becoming_a_label():
    pairs=dict(type=torch.ones(1,dtype=torch.int32),dist=torch.tensor([0.]),
               includemargin=torch.tensor([.001]),efc_address=torch.tensor([[-1]]),
               constraint_rows=torch.tensor([1]),active=torch.tensor([True]),
               constraint_allocated=torch.tensor([False]),eligible=torch.tensor([False]),
               primary_surface=torch.tensor([0]),part=torch.tensor([0]))
    with pytest.raises(ValueError,match='Unallocated active Newton contact'):
        validate_observed(dict(pairs=pairs))


def test_demonstration_only_excludes_generated_training_and_model_selection():
    records=[dict(split=split,kind=kind,chain_id=chain) for split in ('train','validation','test')
             for kind,chain in [('demonstration','demo'),('predictor_accepted','isolated_0'),
                                ('predictor_accepted','predictor_chain_0')]]
    for split in ('train','validation'):
        selected=supervision_records(records,split,'demonstration_only')
        assert selected==[r for r in records if r['split']==split and r['chain_id']=='demo']
        assert len(supervision_records(records,split,'mixed'))==3
    assert len(records)==9  # Evaluation corpus stays intact.
    with pytest.raises(ValueError,match='Unknown training source'):
        supervision_records(records,'train','unknown')


def test_demonstration_validation_is_not_halved_and_rejects_prediction_leakage(monkeypatch):
    from generator import train_frozen_predictor_infiller as trainer
    cfg=trainer.Config(training_source='demonstration_only')
    demo=dict(q=torch.zeros(4,36),kind='demonstration')
    prediction=dict(q=torch.zeros(4,36),kind='predictor_accepted')
    monkeypatch.setattr(trainer,'collate',lambda records,device:records)
    monkeypatch.setattr(trainer,'decode_batch',lambda model,b:b)
    monkeypatch.setattr(trainer,'trajectory_objective',lambda model,b,q,limits,names,**kw:
                        (torch.tensor(2. if b[0]['kind']=='demonstration' else 100.),{}))
    score,metrics=trainer.validation_loss(None,[demo],{},[],cfg,'cpu')
    assert score==2. and metrics=={'demonstration':2.}
    with pytest.raises(ValueError,match='Validation boundary kinds'):
        trainer.validation_loss(None,[demo,prediction],{},[],cfg,'cpu')


@pytest.mark.parametrize('learned',[False,True])
@pytest.mark.parametrize('velocity',[False,True])
def test_recursion_continues_rejections_and_feeds_generated_state_and_actual_contacts(monkeypatch,learned,velocity):
    from types import SimpleNamespace
    from generator import train_frozen_predictor_infiller as trainer

    model=DirectInfiller(predict_frames=learned,boundary_velocity=velocity).eval()
    if learned:
        monkeypatch.setattr(model,'frame_count',lambda start,*args: 5+start[:,0]*10)
    initial=torch.zeros(36); initial[3]=1
    initial[7:]=(model.fk.joint_lower+model.fk.joint_upper)/2
    scene=dict(box_center=torch.tensor([2.,0.,.3]),box_rotation=torch.eye(3),
               box_half_extents=torch.ones(3)*.3,ground_height=torch.tensor(0.))
    calls=[]

    class Queries:
        def observed(self,q,ids):
            mask=torch.zeros(len(q),6,dtype=torch.bool)
            mask[:,0]=q[:,0]>=.15; mask[:,1]=~mask[:,0]
            surface=torch.where(mask,0,-1)
            anchors=torch.zeros(len(q),6,3)
            anchors[:,0]=torch.tensor([9.,8.,7.])
            return dict(contact_part_mask=mask,contact_surface=surface,contact_position_w=anchors)

        def timeline(self,q,scene_id,audit_dir=None):
            observed=self.observed(q,None)
            return dict(mask=observed['contact_part_mask'],surface=observed['contact_surface'],
                        depth=torch.zeros(len(q),2),invalid=torch.zeros(len(q),dtype=torch.bool))

    query=Queries()

    class Predictor:
        fk=model.fk

        def __call__(self,**inputs):
            calls.append({k:v.clone() for k,v in inputs.items()})
            q=inputs['current_q'].clone(); q[:,0]+=.1
            contact=torch.tensor([[True,False,False,False,False,False]])
            points=torch.zeros(1,6,3); points[:,0,0]=.3
            return SimpleNamespace(qpos=q,conditioned_contact=contact,
                conditioned_role=contact.long(),conditioned_points_local=points)

    # These synthetic query results exercise control flow, not Newton physics.
    monkeypatch.setattr(trainer,'audit_prediction',lambda predictor,query,prediction,*args:
        (query.observed(prediction.qpos,None),dict(accepted=False,reasons=['actual_contact_plan'])))
    monkeypatch.setattr(trainer,'audit_intended_surfaces',lambda points,active,observed:
                        torch.where(active,0,-1))
    segments=list(trainer.recursive_segments(Predictor(),model,query,initial,scene,4,None,
                  events=3,duration=.08,dense_factor=2))
    assert len(segments)==3 and all(not segment[3]['accepted'] for segment in segments)
    assert [int(call['current_contact'][0].nonzero()[0]) for call in calls]==[1,1,0]
    for index,(q,native,dense,record,endpoints) in enumerate(segments):
        expected=5+index if learned else 5
        assert len(q)==expected and len(dense['depth'])==(expected-1)*2+1
        assert record['frames']==expected and record['duration_s']==pytest.approx((expected-1)/50)
        torch.testing.assert_close(calls[index]['current_q'][0],initial if index==0 else segments[index-1][0][-1])
        assert torch.equal(q[0],calls[index]['current_q'][0])
        assert float(q[-1,0])==pytest.approx(.1*(index+1))
        assert not q.requires_grad
        if velocity:
            from generator.infiller_boundary_velocity import finite_difference_velocity
            if index==0:
                assert record['incoming_velocity_source'].startswith('unknown history')
            else:
                expected_velocity=finite_difference_velocity(segments[index-1][0][None,-2:],.02)[0]
                torch.testing.assert_close(torch.tensor(record['initial_velocity']),expected_velocity)
    assert segments[0][3]['end_anchor_source'][0]=='declared_unrealized_intent'
    assert not bool(segments[0][4]['observed']['contact_part_mask'][0,0])
    assert segments[1][3]['end_anchor_source'][0]=='observed_actual'
    torch.testing.assert_close(segments[1][4]['contract']['end_anchor'][0],torch.tensor([9.,8.,7.]))


def test_transfer_constraints_preserve_expert_retouch_and_leave_generated_timing_unknown():
    active=torch.zeros(2,5,6,dtype=torch.bool)
    active[0,:,0]=torch.tensor([True,False,False,True,True])
    active[1,:,:2]=True  # Historical pseudo-timing must not enter the new loss.
    contact=dict(start_contact=torch.tensor([[True,False,False,False,False,False]]).expand(2,-1),
        end_contact=torch.tensor([[True,True,False,False,False,False]]).expand(2,-1),
        keep=torch.tensor([[False,False,False,False,False,False]]).expand(2,-1),
        start_surface=torch.zeros(2,6,dtype=torch.long),end_surface=torch.zeros(2,6,dtype=torch.long))
    b=dict(q=torch.zeros(2,5,36),active=active,surface=torch.zeros(2,5,6,dtype=torch.long),
           contract=contact,demo=torch.tensor([True,False]))
    observed,surface,release=transfer_constraints(b)
    assert torch.equal(observed[0],active[0]) and torch.equal(release[0],~active[0])
    assert not bool(observed[1,1:-1].any()) and not bool(release[1,1:-1].any())
    assert bool(observed[1,-1,1]) and not bool(observed[1,0,1])
    assert bool((surface[~observed]==-1).all())
    b['contract']['keep']=torch.zeros(2,6,dtype=torch.bool); b['contract']['keep'][1,0]=True
    observed,_,_=transfer_constraints(b)
    assert bool(observed[1,:,0].all()) and not bool(observed[1,1:-1,1].any())


def test_reference_feasible_smoothness_and_expert_supervision_do_not_impose_generated_pose_targets():
    from generator.trajectory_budget import derivative_metrics
    model=DirectInfiller()
    q=torch.zeros(2,5,36); q[:,:,3]=1
    q[:,:,0]=torch.linspace(0,.4,5)
    limits={k:torch.tensor(1e-8) for k in derivative_metrics(q,torch.ones(2))}
    b=dict(q=q.clone(),duration=torch.tensor([.08,.08]),demo=torch.tensor([True,False]))
    pose,smooth,_=regularized_motion_objective(model,b,q,limits)
    assert float(pose)==0 and float(smooth)==0  # Reference is a feasibility witness.
    changed=q.clone(); changed[1,2,7]=.1
    pose,_,_=regularized_motion_objective(model,b,changed,limits)
    assert float(pose)==0  # Generated cubic is not an expert pose target.
    changed[0,2,7]=.1; changed.requires_grad_(True)
    pose,smooth,_=regularized_motion_objective(model,b,changed,limits)
    assert float(pose.detach())>0
    (pose+smooth).backward()
    assert bool(torch.isfinite(changed.grad).all()) and bool(changed.grad[0,2,7]!=0)
    with pytest.raises(ValueError,match='at least one'):
        regularized_motion_objective(model,b,q,limits,budget_ratio=.5)


@pytest.mark.parametrize('learned',[False,True])
def test_unified_training_keeps_physics_gradients_and_excludes_immutable_boundary_maxima(monkeypatch,learned):
    from types import SimpleNamespace
    from generator import train_frozen_predictor_infiller as trainer
    from generator.trajectory_budget import derivative_metrics
    import contact_solver.contact_regions as regions
    model=DirectInfiller(predict_frames=learned)
    reference=torch.zeros(1,5,36); reference[:,:,3]=1
    reference[:,0,0]=10.; reference[:,-1,0]=10.
    q=reference.clone().requires_grad_(True)
    limits={k:torch.tensor(1.) for k in derivative_metrics(q,torch.ones(1))}
    contacts=torch.zeros(1,6,dtype=torch.bool); surfaces=torch.full((1,6),-1,dtype=torch.long)
    b=dict(q=reference,demo=torch.tensor([False]),duration=torch.ones(1),scene_id=torch.zeros(1,dtype=torch.long),
        scene=dict(box_center=torch.zeros(1,3),box_rotation=torch.eye(3)[None],
                   box_half_extents=torch.ones(1,3),ground_height=torch.zeros(1)),
        active=torch.zeros(1,5,6,dtype=torch.bool),surface=torch.full((1,5,6),-1,dtype=torch.long),
        contract=dict(start_contact=contacts,end_contact=contacts,keep=contacts,
                      start_surface=surfaces,end_surface=surfaces))
    if learned:b.update(reference_duration=torch.ones(1),predicted_frames=torch.tensor([51.]))
    query=SimpleNamespace(batch_size=3,observed=lambda q,ids:{},workers=SimpleNamespace(
        solid_router=lambda *args:None,target_interval=lambda *args:None))
    monkeypatch.setattr(trainer,'DeviceWitnessRows',lambda fk,q,observed:SimpleNamespace(q=q))
    monkeypatch.setattr(regions,'unified_region_objective',lambda model,rows,*args,**kw:
        ((rows.q[:,0]-.2).square(),dict(solid_terrain_penetration_cm=torch.zeros(len(rows.q)),
                                      solid_self_penetration_cm=torch.zeros(len(rows.q)))))
    loss,metrics=trainer.unified_objective(model,b,q,limits,query,trainer.Config(objective='unified'))
    assert loss.requires_grad and metrics['physical_samples']==9
    assert metrics['immutable_boundary_physics']==pytest.approx(9.8**2)
    assert float(metrics['unified_physics'].detach())<2*9.8**2
    loss.backward()
    assert bool(torch.isfinite(q.grad).all()) and bool(q.grad[:,2,0]!=0)


def test_smoke_cap_preserves_sources_and_cannot_leak_into_formal_training():
    from generator import train_frozen_predictor_infiller as trainer
    rows=[dict(kind=kind,index=i) for kind in ('demonstration','predictor_accepted') for i in range(5)]
    limited=trainer.smoke_records(rows,trainer.Config(smoke=True,maximum_samples=4))
    assert len(limited)==4 and sum(r['kind']=='demonstration' for r in limited)==2
    with pytest.raises(ValueError,match='explicit smoke'):
        trainer.smoke_records(rows,trainer.Config(maximum_samples=4))
    assert trainer.smoke_records(rows,trainer.Config()) is rows
