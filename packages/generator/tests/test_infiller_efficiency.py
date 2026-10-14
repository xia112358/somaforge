import pytest
import torch

from generator.direct_infiller import DirectInfiller,collate,decode_batch,prepare_frame_prediction
from generator.infiller_boundary_velocity import SelfGeneratedHistory
from generator.infiller_efficiency import BoundaryRecordCache
from generator.recursive_refinement import adjacent_records,seam_objective
from test_infiller_frames import inputs


def chain_records(model):
    a,z,c,s=inputs(model)
    records=[]
    for chain in range(2):
        for step in range(4):
            q0=a[0].clone();q0[0]=step*.02+chain
            q1=q0.clone();q1[0]+=.02
            q=torch.stack((q0,torch.ones_like(q0)*999,q1))
            records.append(dict(q=q,kind='predictor_recursive',split='train',chain_id=f'chain{chain}',
                scene_id=torch.tensor(0),current_frame=step*2,target_frame=step*2+2,
                duration=torch.tensor(.04),scene={k:v[0] for k,v in s.items()},
                contract={k:v[0] for k,v in c.items()},active=torch.zeros(3,6,dtype=torch.bool),
                surface=torch.zeros(3,6,dtype=torch.long),material=torch.zeros(3,6,3),
                material_link=torch.zeros(3,6,dtype=torch.long),margin=torch.ones(3,6)))
    return records


def test_batched_prefix_and_seams_preserve_scalar_loss_and_gradients():
    torch.manual_seed(5)
    model=DirectInfiller(predict_frames=True,boundary_velocity=True)
    for p in model.frame_head.parameters():p.requires_grad_(False)
    records=chain_records(model);indices=[2,6]
    cache=BoundaryRecordCache(model,records,'cpu')
    for i,r in enumerate(records):
        original=prepare_frame_prediction(model,collate([r],'cpu'))
        assert torch.equal(cache.predicted[i],original['predicted_frames'][0])
    legacy=SelfGeneratedHistory(model,records,'cpu')
    fast=SelfGeneratedHistory(model,records,'cpu',boundary_cache=cache)
    batch=prepare_frame_prediction(model,collate([records[i] for i in indices],'cpu'))
    left=legacy.condition(dict(batch),indices);right=fast.condition(dict(batch),indices)
    torch.testing.assert_close(left['start_velocity'],right['start_velocity'])
    assert torch.equal(left['velocity_known'],right['velocity_known'])
    q=decode_batch(model,left)
    old,count=seam_objective(model,records,indices,adjacent_records(records),q,'cpu',history=legacy)
    new,new_count=seam_objective(model,records,indices,adjacent_records(records),q,'cpu',history=fast,boundary_cache=cache)
    assert count==new_count==2
    torch.testing.assert_close(old,new)
    old.backward();grad={k:p.grad.clone() for k,p in model.named_parameters() if p.grad is not None}
    model.zero_grad(set_to_none=True);new.backward()
    for k,p in model.named_parameters():
        if k in grad:torch.testing.assert_close(p.grad,grad[k],atol=1e-5,rtol=1e-4)
    assert all(p.grad is None for p in model.frame_head.parameters())
    assert model.terminal_velocity_head[-1].weight.grad.abs().sum()>0
    assert cache.q.shape==(len(records),2,36)


def test_duration_cache_refuses_trainable_or_joint_time_heads():
    model=DirectInfiller(predict_frames=True,boundary_velocity=True)
    with pytest.raises(ValueError,match='frozen independent'):
        BoundaryRecordCache(model,chain_records(model),'cpu')


def test_fk_cache_reuses_same_tensor_and_releases_after_exception():
    model=DirectInfiller()
    a,_,_,_=inputs(model)
    names=(model.fk.root_link,)
    ordinary=model.fk.link_poses(a,names)
    model.fk.begin_link_pose_cache(a)
    try:
        first=model.fk.link_poses(a,names)
        second=model.fk.link_poses(a,names)
        assert model.fk._link_pose_cache[0] is a
        torch.testing.assert_close(first[0],second[0]);torch.testing.assert_close(first[0],ordinary[0])
    finally:model.fk.end_link_pose_cache()
    assert model.fk._link_pose_cache is None


def test_device_activation_validation_matches_shared_numpy_rule_and_rejects_bad_rows():
    import numpy as np
    from generator.train_frozen_predictor_infiller import validate_observed
    from somaforge_core.newton_contacts import constraint_decision
    rng=np.random.default_rng(7)
    dist=rng.normal(size=100).astype('float32')
    margin=rng.normal(size=100).astype('float32')
    kind=rng.integers(0,4,size=100)
    rows=rng.integers(1,4,size=100)
    address=np.tile(np.arange(3),(100,1))
    active,allocated=constraint_decision(dist,margin,kind,address,100,rows)
    pairs={k:torch.as_tensor(v) for k,v in dict(dist=dist,includemargin=margin,type=kind,
        efc_address=address,constraint_rows=rows,active=active,constraint_allocated=allocated).items()}
    pairs.update({k:torch.zeros(100) for k in ('eligible','primary_surface','part')})
    validate_observed(dict(pairs=pairs))
    where=int(np.flatnonzero(active)[0])
    pairs['efc_address'][where,0]=-1;pairs['constraint_allocated'][where]=False
    with pytest.raises(ValueError,match='Unallocated active'):validate_observed(dict(pairs=pairs))
    pairs['efc_address'][where,0]=0;pairs['constraint_allocated'][where]=True
    pairs['active'][where]=False
    with pytest.raises(ValueError,match='disagreement'):validate_observed(dict(pairs=pairs))
