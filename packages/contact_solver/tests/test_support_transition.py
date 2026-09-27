from types import SimpleNamespace
import pytest
import torch
from contact_solver.support_transition import support_transition, predicted_support_loss

class FK:
    def link_poses(self,q,names):
        pos=q[:,:6].reshape(-1,2,3)
        rot=torch.eye(3).expand(len(q),2,3,3).clone()
        return pos,rot

def rows(q,parts=(0,1),surface=0):
    n=len(parts);ids=torch.tensor(parts,dtype=torch.long)
    p=dict(sample=torch.zeros(n,dtype=torch.long),part=ids,primary_surface=torch.full((n,),surface),
        body_link0=torch.full((n,),-1),body_link1=ids,
        type=torch.ones(n,dtype=torch.long),dist=torch.zeros(n),includemargin=torch.full((n,),.02),
        efc_address=torch.zeros(n,4,dtype=torch.long),constraint_rows=torch.full((n,),4))
    for key in ('active','constraint_allocated','eligible','upward','task_pair'):p[key]=torch.ones(n,dtype=torch.bool)
    points=torch.zeros(n,2,3);points[:,1]=q.detach().reshape(-1,2,3)[0,ids]
    return SimpleNamespace(q=q,pair=p,points=points,normal_valid=torch.ones(n,dtype=torch.bool),world_frame=None,observed={'link_names':('left','right')})

def test_one_stationary_support_allows_other_limb_motion_without_gradient_or_loss():
    a=torch.zeros(1,6);b=torch.tensor([[0.,0.,0.,.2,0.,0.]],requires_grad=True)
    result=support_transition(FK(),rows(a),rows(b))
    assert result['support_transition_valid'].item()
    assert not result['support_displacement_m'].requires_grad
    assert not any('loss' in k for k in result)

def test_rigid_sliding_rejected_even_with_both_contacts_still_active():
    a=torch.zeros(1,6);b=torch.tensor([[.07,0.,0.,.07,0.,0.]])
    result=support_transition(FK(),rows(a),rows(b))
    assert not result['support_transition_valid'].item()
    assert result['support_displacement_m'].item()==pytest.approx(.07)

def test_new_witness_cannot_hide_motion_of_initial_material_point():
    a=torch.zeros(1,6);b=torch.full((1,6),.07)
    end=rows(b);end.points[:]=0
    assert not support_transition(FK(),rows(a),end)['support_transition_valid'].item()

def test_surface_witness_change_preserves_endpoint():
    a=torch.zeros(1,6)
    assert support_transition(FK(),rows(a),rows(a,surface=1))['support_transition_valid'].item()

def test_disappearing_old_support_or_no_initial_contact_is_rejected():
    a=torch.zeros(1,6)
    assert not support_transition(FK(),rows(a),rows(a,parts=()))['support_transition_valid'].item()
    assert not support_transition(FK(),rows(a,parts=()),rows(a))['support_transition_valid'].item()

def test_endpoint_allows_internal_support_change():
    a=torch.zeros(1,6);b=torch.tensor([[.03,0.,0.,0.,0.,0.]])
    before=rows(a);after=rows(b)
    before.pair['part'][:]=0;after.pair['part'][:]=0
    # Two witnesses in one endpoint: one retained support point suffices.
    assert support_transition(FK(),before,after)['support_transition_valid'].item()

def test_vertical_lift_and_unallocated_evidence_not_allowed():
    a=torch.zeros(1,6);b=torch.tensor([[0.,0.,.07,0.,0.,.07]])
    assert not support_transition(FK(),rows(a),rows(b))['support_transition_valid'].item()
    bad=rows(a);bad.pair['efc_address'][:]=-1;bad.pair['constraint_allocated'][:]=False
    with pytest.raises(ValueError,match='Unallocated'):support_transition(FK(),rows(a),bad)


def test_destination_region_can_supply_pivot():
    class RotatingFK:
        def link_poses(self,q,names):
            c,s=q[:,0].cos(),q[:,0].sin()
            r=torch.eye(3).repeat(len(q),2,1,1)
            r[:,0,0,0]=c;r[:,0,0,1]=-s;r[:,0,1,0]=s;r[:,0,1,1]=c
            pos=torch.zeros(len(q),2,3)
            pos[:,0,0]=.2*(1-c);pos[:,0,1]=-.2*s
            return pos,r
    a=torch.zeros(1,6);b=a.clone();b[0,0]=torch.pi/2
    before=rows(a,parts=(0,));after=rows(b,parts=(0,))
    before.points[0,1]=torch.tensor([0.,0.,0.])
    after.points[0,1]=torch.tensor([.2,0.,0.])
    result=support_transition(RotatingFK(),before,after)
    assert result['support_transition_valid'].item()
    assert result['support_displacement_m'].item()<1e-6


def test_six_cm_boundary():
    a=torch.zeros(1,6)
    for distance,expected in [(.059,True),(.061,False)]:
        b=a.clone();b[:,0]=distance;b[:,3]=distance
        assert support_transition(FK(),rows(a),rows(b))['support_transition_valid'].item()==expected


def roles(left=2,right=2):
    return torch.tensor([[left,right,0,0,0,0]],dtype=torch.long)


def test_predicted_support_penalizes_each_declared_part_not_only_best_support():
    a=torch.zeros(1,6,requires_grad=True)
    b=torch.tensor([[0.,0.,0.,.12,0.,0.]],requires_grad=True)
    loss,metrics=predicted_support_loss(FK(),rows(a),rows(b),roles())
    assert loss.item()==pytest.approx(.5)
    assert metrics['predicted_support_count'].item()==2
    loss.sum().backward()
    assert b.grad[0,3]>0 and b.grad[0,0]==0
    assert a.grad is None


def test_disappearing_support_still_receives_gradient():
    a=torch.zeros(1,6)
    b=torch.tensor([[0.,0.,.12,0.,0.,0.]],requires_grad=True)
    loss,metrics=predicted_support_loss(FK(),rows(a),rows(b,parts=()),roles(2,0))
    assert loss.item()==pytest.approx(1.)
    assert metrics['predicted_support_count'].item()==1
    loss.sum().backward()
    assert b.grad[0,2]>0


@pytest.mark.parametrize('role',[0,1,3])
def test_nonpersistent_predicted_roles_do_not_enable_loss(role):
    a=torch.zeros(1,6)
    b=torch.full((1,6),.2,requires_grad=True)
    loss,_=predicted_support_loss(FK(),rows(a),rows(b),roles(role,role))
    loss.sum().backward()
    assert loss.item()==0 and not b.grad.any()


def test_no_initial_contact_is_reported_without_fabricating_anchor():
    a=torch.zeros(1,6)
    b=torch.full((1,6),.2,requires_grad=True)
    loss,metrics=predicted_support_loss(FK(),rows(a,parts=()),rows(b),roles())
    loss.sum().backward()
    assert not b.grad.any() and metrics['predicted_support_count'].item()==0
    assert metrics['predicted_support_without_initial_contact'].item()==2


def test_support_loss_tolerance_and_internal_region_minimum():
    a=torch.zeros(1,6)
    b=torch.tensor([[.12,0.,0.,.03,0.,0.]],requires_grad=True)
    before,after=rows(a),rows(b)
    # Fixture part and link IDs share storage; preserve distinct link IDs.
    before.pair['part']=torch.zeros(2,dtype=torch.long)
    after.pair['part']=torch.zeros(2,dtype=torch.long)
    loss,_=predicted_support_loss(FK(),before,after,roles(2,0))
    loss.sum().backward()
    assert loss.item()==0 and not b.grad.any()


def test_predicted_role_gate_does_not_backpropagate_to_logits():
    a=torch.zeros(1,6)
    b=torch.full((1,6),.12,requires_grad=True)
    logits=torch.zeros(1,6,4,requires_grad=True)
    with torch.no_grad():logits[:,:,2]=1
    loss,_=predicted_support_loss(FK(),rows(a),rows(b),logits.argmax(-1))
    loss.sum().backward()
    assert logits.grad is None and b.grad.abs().sum()>0


def test_support_loss_rejects_unallocated_input_contact():
    q=torch.zeros(1,6)
    before=rows(q);before.pair['efc_address'][:]=-1
    before.pair['constraint_allocated'][:]=False
    with pytest.raises(ValueError,match='Unallocated'):
        predicted_support_loss(FK(),before,rows(q),roles())
