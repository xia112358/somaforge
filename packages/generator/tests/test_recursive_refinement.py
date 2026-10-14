import pytest
import torch

from generator.recursive_refinement import role_consistency_loss, adjacent_records, sampled_seam_loss
from generator.extend_recursive_corpus import recursive_seed_records


def test_role_consistency_learns_from_actual_contact_without_forcing_another_role():
    logits=torch.tensor([[[0.,0.,8.,0.],[0.,0.,8.,0.]]],requires_grad=True)
    actual=torch.tensor([[False,True]])
    loss=role_consistency_loss(logits,actual).sum()
    loss.backward()
    assert torch.isfinite(logits.grad).all()
    assert logits.grad[0,0,2]>0
    assert bool((logits.grad[0,0,[0,1,3]]<0).all())
    assert torch.equal(logits.grad[0,1],torch.zeros(4))
    assert logits.argmax(-1).tolist()==[[2,2]]  # No inference mask/mutation.


def test_role_consistency_is_finite_with_confident_impossible_keep():
    logits=torch.tensor([[[0.,-1000.,1000.,-1000.]]],requires_grad=True)
    loss=role_consistency_loss(logits,torch.tensor([[False]])).sum()
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(logits.grad).all()


def record(split='train',start=0,end=1,scene=0):
    q=torch.zeros(4,36);q[:,3]=1;q[:,0]=torch.linspace(start,end,4)
    return dict(kind='demonstration',split=split,current_frame=start,target_frame=end,
        chain_id='demo_0',scene_id=scene,scene=dict(center=torch.zeros(3)),q=q)


def test_seams_require_real_adjacency_and_never_cross_splits():
    records=[record(),record(start=1,end=2),record(split='validation',start=2,end=3)]
    assert adjacent_records(records)=={0:1}
    records[1]['scene']['center'][0]=torch.finfo(torch.float32).eps
    assert adjacent_records(records)=={0:1}
    records[1]['scene']['center'][0]=.1
    with pytest.raises(ValueError,match='scene coordinates'): adjacent_records(records)
    records[1]['scene']['center'][0]=0
    records[1]['q'][0,0]+=.01
    with pytest.raises(ValueError,match='exact boundary'): adjacent_records(records)


def test_recursive_collection_never_selects_test_seeds_or_later_demo_frames():
    rows=[record(split=s,start=t,end=t+1) for s in ['train','validation','test'] for t in [0,1]]
    seeds=recursive_seed_records(rows)
    assert len(seeds)==2 and {r['split'] for r in seeds}=={'train','validation'}


def test_sampled_seam_uses_actual_duration_and_sign_invariant_rotation():
    a=torch.zeros(1,2,36);a[...,3]=1
    b=a.clone();a[:,0,0]=-.02;b[:,1,0]=.04;b[...,3]=-1
    scale=torch.ones(36)
    loss=sampled_seam_loss(a,b,torch.tensor([.02]),torch.tensor([.04]),scale)
    torch.testing.assert_close(loss,torch.zeros(1))
    a.requires_grad_();b.requires_grad_()
    loss=sampled_seam_loss(a,b,torch.tensor([.02]),torch.tensor([.02]),scale).sum()
    loss.backward()
    assert a.grad.abs().sum()>0 and b.grad.abs().sum()>0
    assert torch.isfinite(a.grad).all() and torch.isfinite(b.grad).all()


def test_role_refinement_never_uses_generated_future_roles_as_expert_labels():
    from types import SimpleNamespace
    from generator.refine_predictor_roles import role_objective
    torch.manual_seed(11)
    model=SimpleNamespace(role_head=torch.nn.Linear(3,4))
    data=dict(part=torch.randn(2,6,3),contact=torch.zeros(2,6,dtype=torch.bool),
        demo=torch.tensor([True,False]),role=torch.zeros(2,6,dtype=torch.long),
        old_logits=torch.randn(2,6,4))
    ids=torch.arange(2)
    a=role_objective(model,data,ids)
    data['role'][1]=3
    b=role_objective(model,data,ids)
    torch.testing.assert_close(a,b)
    b.backward()
    assert model.role_head.weight.grad.abs().sum()>0
    assert torch.isfinite(model.role_head.weight.grad).all()
