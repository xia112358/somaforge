import torch

from climb00_pipeline.parallel_rollout_pool import ParallelRolloutPool


def reference(count):
    return {'current_q':torch.arange(count).float()[:,None],
        'current_contact':torch.zeros(count,1,dtype=torch.bool)}


def observed(q,indices,raw,chosen):
    return {'current_q':q,'current_contact':raw['contact'][chosen]}


def test_pool_keeps_raw_states_across_updates_beyond_six_and_respects_split():
    bank=reference(24);successor=torch.arange(24)+1;successor[-1]=-1
    pool=ParallelRolloutPool(bank,torch.arange(20),successor,2)
    pool.indices[:]=0;pool.observation['current_q'][:]=0
    for step in range(12):
        slots,ids,inputs=pool.batch(2)
        assert ids.tolist()==[step,step]
        q=inputs['current_q']+1
        pool.update(slots,q,{'contact':torch.ones(2,1,dtype=torch.bool)},torch.ones(2,dtype=torch.bool),
            torch.ones(2,dtype=torch.bool),observed)
        assert pool.age.tolist()==[step+1]*2
        assert torch.equal(pool.observation['current_q'],q)
    assert pool.successor[19]==-1  # Never enter validation-only index 20.


def test_independent_success_failure_terminal_reset_and_fields_stay_paired():
    bank=reference(10);successor=torch.arange(10)+1;successor[-1]=-1
    pool=ParallelRolloutPool(bank,torch.arange(10),successor,3)
    pool.indices[:]=torch.tensor([1,3,9])
    pool.draw_references=lambda n:torch.tensor([6,7,8])[:n]
    slots=torch.arange(3);q=torch.tensor([[51.],[53.],[59.]],requires_grad=True)
    result=pool.update(slots,q,{'contact':torch.ones(3,1,dtype=torch.bool)},
        torch.tensor([True,False,True]),torch.ones(3,dtype=torch.bool),observed)
    assert pool.indices.tolist()==[2,7,8]
    assert pool.observation['current_q'].flatten().tolist()==[51,7,8]
    assert pool.observation['current_contact'].flatten().tolist()==[True,False,False]
    assert not pool.observation['current_q'].requires_grad
    assert pool.age.tolist()==[1,0,0] and pool.retries.tolist()==[0,0,0]
    assert result['terminal_resets']==1
    assert result['invalid_resets']==1 and result['retries']==0


def test_bad_geometry_resets_only_affected_slot_and_stalls_have_explicit_limit():
    pool=ParallelRolloutPool(reference(10),torch.arange(10),torch.full((10,),-1),2,max_retries=2)
    pool.indices[:]=torch.tensor([1,3]);pool.draw_references=lambda n:torch.tensor([6,7])[:n]
    for step in range(2):
        pool.update(torch.arange(2),torch.tensor([[51.],[53.]]),{'contact':torch.ones(2,1,dtype=torch.bool)},
            torch.zeros(2,dtype=torch.bool),torch.tensor([False,True]),observed)
        assert pool.indices[0]==6
    assert pool.indices[1]==7 and pool.age[1]==0


def test_failed_prediction_gets_gradient_but_never_becomes_observation():
    pool=ParallelRolloutPool(reference(10),torch.arange(10),torch.arange(10),2)
    pool.draw_references=lambda n:torch.tensor([6,7])[:n]
    output=torch.tensor([[51.],[53.]],requires_grad=True)
    output.square().mean().backward()
    assert output.grad.abs().sum()>0
    def forbidden(*args):
        raise AssertionError('Failed outputs must not be converted into successor observations')
    result=pool.update(torch.arange(2),output,{},torch.zeros(2,dtype=torch.bool),
                      torch.ones(2,dtype=torch.bool),forbidden)
    assert result['resets']==2 and result['retries']==0
    assert pool.observation['current_q'].flatten().tolist()==[6,7]


def test_legacy_recovery_flag_is_rejected():
    import pytest
    with pytest.raises(ValueError,match='retries are disabled'):
        ParallelRolloutPool(reference(2),torch.arange(2),torch.tensor([1,-1]),2,recover_failed_states=True)
