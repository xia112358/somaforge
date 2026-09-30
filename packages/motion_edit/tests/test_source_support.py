import torch
from motion_edit.generation.source_support import support_residuals


def test_material_switch_preserves_rolling_and_rotated_source():
    n = 8
    angle = torch.linspace(0, .4, n)
    from scipy.spatial.transform import Rotation
    r = torch.tensor(Rotation.from_rotvec(torch.stack((angle*0, angle, angle*0), -1)).as_matrix(), dtype=torch.float32)[:, None]
    p = torch.zeros(n, 1, 3)
    local = torch.randn(n, 1, 3)*.1  # different heel/toe sample each frame
    edit = torch.tensor([[0., -1, 0], [1, 0, 0], [0, 0, 1]]).expand(n, 1, 3, 3)
    normal = torch.tensor([0., 0, 1]).expand(n, 1, 3)
    active = torch.ones(n-1, 1, dtype=torch.bool)
    e, drift = support_residuals(p+torch.tensor([1., 2, 0]), edit@r, p, r, local, edit, normal, active)
    assert e.abs().max() < 1.e-6 and drift.abs().max() < 1.e-6


def test_drift_accumulates_across_witness_changes_but_resets_on_release():
    n = 8
    p = torch.zeros(n, 1, 3)
    out = p.clone(); out[:, 0, 0] = torch.arange(n)*.001
    out.requires_grad_()
    r = torch.eye(3).expand(n, 1, 3, 3)
    local = torch.randn(n, 1, 3)
    normal = torch.tensor([0., 0, 1]).expand(n, 1, 3)
    active = torch.tensor([True, True, True, False, True, True, True])[:, None]
    e, drift = support_residuals(out, r, p, r, local, r, normal, active)
    torch.testing.assert_close(drift[:, 0, 0], torch.tensor([.001, .002, .003, 0, .001, .002, .003]))
    loss = drift.square().sum(); loss.backward()
    assert out.grad.isfinite().all() and out.grad.abs().max() > 0


def test_absolute_phase_budget_rejects_sliding_despite_contact():
    import numpy as np
    from motion_edit.generation.source_support import audit_phase_support
    c={'actions':[{'id':'phase','start':0,'end':10,
                   'requirements':[{'kind':'keep','part':0,'surface':0}]}]}
    mask=np.ones((11,6),bool);surface=np.zeros((11,6),int)
    steps=np.zeros((11,6));steps[:10,0]=.008
    r=audit_phase_support(c,steps,mask,surface,tolerance_m=.06)
    assert not r['passed'] and r['phases'][0]['material_tangent_path_m']>.079
    steps[:10,0]=.001
    assert audit_phase_support(c,steps,mask,surface,tolerance_m=.06)['passed']
    steps[4,0]=np.nan
    assert not audit_phase_support(c,steps,mask,surface,tolerance_m=.06)['passed']


def test_unconstrained_first_action_does_not_gain_support_budget():
    import numpy as np
    from motion_edit.generation.source_support import audit_phase_support
    c={'actions':[{'id':'approach','start':0,'end':10,
                   'requirements':[{'kind':'establish','part':1,'surface':0}]},
                  {'id':'support','start':10,'end':14,
                   'requirements':[{'kind':'keep','part':1,'surface':0}]}]}
    steps=np.zeros((15,6));steps[:10]=1.
    r=audit_phase_support(c,steps,np.ones((15,6),bool),np.zeros((15,6),int),tolerance_m=.06)
    assert r['passed'] and len(r['phases'])==1 and r['phases'][0]['start']==10


def test_phase_audit_requires_calibrated_budget_and_missing_is_not_zero():
    import numpy as np
    import pytest
    from motion_edit.generation.source_support import audit_phase_support
    contract={'actions':[{'id':'support','start':0,'end':2,
                         'requirements':[{'kind':'keep','part':0,'surface':0}]}]}
    steps=np.zeros((3,6));mask=np.ones((3,6),bool);faces=np.zeros((3,6),int)
    unknown=audit_phase_support(contract,steps,mask,faces)
    assert unknown['passed'] is None and unknown['budget_source']=='unknown'
    result=audit_phase_support(contract,steps,mask,faces,budgets_m=[.002])
    assert result['passed'] and result['phases'][0]['force_bearing_slip_status'].startswith('unknown')
    steps[1,0]=np.nan
    assert not audit_phase_support(contract,steps,mask,faces,budgets_m=[.002])['passed']


def test_source_calibration_is_fixed_when_candidate_samples_refresh(tmp_path):
    import json
    import numpy as np
    from motion_edit.generation.source_support import SourcePhaseMotion
    class FK:
        def link_poses(self,q,names):
            return q[:,None,:3],torch.eye(3).expand(len(q),1,3,3)
    q=torch.tensor([[0.,0,0],[.001,0,0],[.003,0,0]])
    pairs=[[dict(part=0,surface=0,body_name='foot',allocated=True,dist=0.,includemargin=.01,
                 position_w=[float(v),0,0],normal_w=[0,0,1])] for v in q[:,0]]
    labels=tmp_path/'labels.npz'
    np.savez(labels,contact_pairs_json=np.asarray(json.dumps(pairs)),
        contact_semantics_json=np.asarray(json.dumps({'scene':{'surface_catalog':[{'surface':0,'normal_w':[0,0,1]}]}})))
    c={'actions':[{'id':'keep','start':0,'end':2,'requirements':[{'kind':'keep','part':0,'surface':0}]}]}
    loss=SourcePhaseMotion(FK(),q,labels,c)
    np.testing.assert_allclose(loss.tolerance_m.numpy(),[.006],atol=1e-8)
    assert loss(q)==0
    before=loss.tolerance_m.clone()
    loss.refresh([dict(names=('foot',),frames=torch.tensor([0,1]),parts=torch.tensor([0,0]),
        links=torch.tensor([0,0]),local=torch.tensor([[1.,0,0],[-1.,0,0]]),normals=torch.tensor([[0.,0,1]]*2))])
    torch.testing.assert_close(before,loss.tolerance_m)
    shifted=q.clone();shifted[1:,0]+=.01
    assert loss(shifted)>0


def test_fresh_editor_output_is_safe_for_refinement(tmp_path, monkeypatch):
    import json
    import numpy as np
    from motion_edit.generation import rollout_authority
    from motion_edit.generation.source_support import initialize_source_edit
    source = tmp_path/'source.npz'
    np.savez(source, joint_pos=np.zeros((2, 8)))
    plan = tmp_path/'plan.json'
    plan.write_text(json.dumps(dict(source_motion_path=str(source), plan_id='edit')))

    def generate(plan_path, *, output_motion_path, **kwargs):
        output_motion_path.parent.mkdir(parents=True)
        np.savez(output_motion_path, joint_pos=np.ones((2, 8)),
                 joint_names=np.array(['joint'], dtype=object), fps=50.,
                 robot_asset_json=np.asarray('{}'))

    monkeypatch.setattr(rollout_authority, 'generate_contact_aware_pyroki_preview', generate)
    output = tmp_path/'seed.npz'
    initialize_source_edit(source, plan, output)
    with np.load(output, allow_pickle=False) as z:
        assert z['joint_names'].tolist() == ['joint']
        assert (z['joint_pos'] == 1).all()
        provenance = json.loads(z['source_initializer_json'].item())
        assert provenance['archived_augmentation_used'] is False
        assert provenance['source'] == str(source.resolve())


def test_native_motion_does_not_count_changing_witness_location():
    import numpy as np
    from motion_edit.generation.source_support import native_material_steps

    class FK:
        def link_poses(self, q, names):
            return q[:, None, :3], torch.eye(3).expand(len(q), 1, 3, 3)

    q = torch.tensor([[0., 0, 0], [.01, 0, 0], [.02, 0, 0]])
    observed = dict(link_names=['foot'], pairs=dict(
        sample=torch.tensor([0, 1]), part=torch.zeros(2, dtype=torch.long),
        eligible=torch.tensor([True, False]), upward=torch.ones(2, dtype=torch.bool),
        task_pair=torch.ones(2, dtype=torch.bool), body_link0=torch.full((2,), -1),
        body_link1=torch.zeros(2, dtype=torch.long),
        geometry_point1_w=torch.tensor([[0., 0, 0], [1., 0, 0]]),normal_w=torch.tensor([[0.,0,1]]*2)))
    steps = native_material_steps(FK(), q, observed, [0, 1, 2])
    np.testing.assert_allclose(steps[0, 0], .01, atol=1.e-7)
    assert np.isnan(steps[1, 0])  # inactive candidates cannot certify support
    assert np.isnan(steps[2, 0])
    assert not observed['pairs']['eligible'][1]  # geometry did not invent contact


def test_static_contact_on_other_surface_cannot_supply_requested_pivot():
    from motion_edit.generation.source_support import native_material_samples
    class FK:
        def link_poses(self,q,names):
            return torch.zeros(len(q),2,3),torch.eye(3).expand(len(q),2,3,3)
    q=torch.zeros(2,3)
    observed=dict(link_names=['heel','toe'],pairs=dict(sample=torch.tensor([0,0]),
        part=torch.tensor([0,0]),surface=torch.tensor([0,1]),eligible=torch.ones(2,dtype=torch.bool),
        upward=torch.ones(2,dtype=torch.bool),task_pair=torch.ones(2,dtype=torch.bool),
        body_link0=torch.tensor([-1,-1]),body_link1=torch.tensor([0,1]),
        geometry_point1_w=torch.zeros(2,3),normal_w=torch.tensor([[0.,0,1]]*2)))
    wanted=torch.full((2,6),-1,dtype=torch.long);wanted[0,0]=1
    samples=native_material_samples(FK(),q,observed,[0,1],wanted_surfaces=wanted)
    assert samples['links'].tolist()==[1]
    wanted[0,0]=2
    assert native_material_samples(FK(),q,observed,[0,1],wanted_surfaces=wanted)['frames'].numel()==0


def test_region_motion_allows_rotation_near_support_but_detects_translation():
    from somaforge_core.contact_motion import contact_region_statistics
    # Three near-pivot samples, two distant moving samples. A median of a
    # whole rigid body's arbitrary cloud is not a support displacement.
    group=torch.zeros(5,dtype=torch.long)
    rotating=torch.tensor([0., .0001, .0002, .01, .02],requires_grad=True)
    stats=contact_region_statistics(rotating,group,2)
    torch.testing.assert_close(stats['lower_quartile'][0],torch.tensor(.0001))
    assert stats['pivot'][0]==0
    assert stats['maximum'][0]>.019 and torch.isnan(stats['pivot'][1])
    translated=contact_region_statistics(rotating+.008,group,2)
    assert translated['pivot'][0]>=.008
    translated['pivot'][0].backward()
    assert rotating.grad.isfinite().all() and rotating.grad.abs().sum()>0


def test_isolated_stationary_sample_does_not_erase_region_translation():
    from somaforge_core.contact_motion import contact_region_statistics
    stats=contact_region_statistics(torch.tensor([0., .01, .01, .01, .01]),
                                    torch.zeros(5,dtype=torch.long),1)
    assert stats['pivot'][0]==0 and stats['lower_quartile'][0]>.009


def test_rotating_contact_region_uses_same_optimization_and_audit_metric():
    import numpy as np
    from motion_edit.generation.source_support import (
        SourcePhaseMotion, native_material_samples, native_material_motion)

    class FK:
        def link_poses(self,q,names):
            angle=q[:,3];c,s=angle.cos(),angle.sin();zero=c*0;one=zero+1
            rotation=torch.stack((c,-s,zero,s,c,zero,zero,zero,one),-1).reshape(-1,1,3,3)
            return q[:,None,:3],rotation

    angle=torch.tensor([0.,.2]);q=torch.stack((-angle.cos(),-angle.sin(),angle*0,angle),-1)
    q.requires_grad_()
    # Body origin moves ~20 cm, while a cluster at the actual pivot stays put.
    local=torch.tensor([[1.,0,0],[1.,.0001,0],[1.,.0002,0],[0.,0,0],[2.,0,0]])
    observed=dict(link_names=['foot'],pairs=dict(
        sample=torch.zeros(5,dtype=torch.long),part=torch.zeros(5,dtype=torch.long),
        eligible=torch.ones(5,dtype=torch.bool),upward=torch.ones(5,dtype=torch.bool),
        task_pair=torch.ones(5,dtype=torch.bool),normal_w=torch.tensor([[0.,0,1]]*5),body_link0=torch.full((5,),-1),
        body_link1=torch.zeros(5,dtype=torch.long),geometry_point1_w=local+q.detach()[0,:3]))
    fk=FK();samples=native_material_samples(fk,q,observed,[0,1])
    audit=native_material_motion(fk,q,observed,[0,1],samples)
    loss=SourcePhaseMotion.__new__(SourcePhaseMotion)
    loss.fk=fk;loss.names=samples['names'];loss.frames=samples['frames']
    loss.links=samples['links'];loss.local=samples['local'];loss.groups=loss.frames*6+samples['parts']
    loss.normals=samples['normals']
    loss.size=6;loss.phases=[(0,1,0)];loss._index_samples()
    path=loss.paths(q)
    np.testing.assert_allclose(path.detach().numpy(),audit['pivot'][:1,0],atol=1.e-7)
    assert path[0]<.0001 and audit['maximum'][0,0]>.19
    shifted=q+torch.tensor([[0.,0,0,0],[.008,0,0,0]])
    assert loss.paths(shifted)[0]>.007
    loss.paths(shifted).sum().backward()
    assert q.grad.isfinite().all() and q.grad.abs().sum()>0


def test_original_keep_motion_is_not_optimized_to_static():
    from motion_edit.generation.source_support import SourcePhaseMotion
    class FK:
        def link_poses(self,q,names):
            return q[:,None,:3],torch.eye(3).expand(len(q),1,3,3)
    original=torch.tensor([[0.,0,0],[.10,0,0]])
    loss=SourcePhaseMotion.__new__(SourcePhaseMotion)
    loss.fk=FK();loss.source_q=original;loss.names=['foot']
    loss.frames=torch.tensor([0]);loss.links=torch.tensor([0]);loss.local=torch.zeros(1,3)
    loss.groups=torch.tensor([0]);loss.normals=torch.tensor([[0.,0,1]])
    loss.size=6;loss.phases=[(0,1,0)];loss.residual_scale_m=.01;loss.tolerance_m=.01
    loss._index_samples()
    q=original.clone().requires_grad_()
    value=loss(q);value.backward()
    assert value.item()==0 and not q.grad.any()
    added=original.clone();added[1,0]+=.03;added.requires_grad_()
    value=loss(added);value.backward()
    assert value.item()>0 and added.grad[1,0]>0
