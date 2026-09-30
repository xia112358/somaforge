import torch

from contact_solver.contact_regions import ContactRegions, unified_region_objective
from generator.full1000_position_predictor import Full1000PositionPredictor
from generator.neural_infiller import CanonicalG1ForwardKinematics
from generator.next_interaction_heightmap import HEIGHTMAP_ROWS, HEIGHTMAP_COLS
from contact_solver.device_contact_objective import DeviceWitnessRows


def test_regions_cover_canonical_geometry_and_mask_padded_regions():
    geometry = ContactRegions(CanonicalG1ForwardKinematics())
    assert geometry.valid.sum(-1).tolist() == [4, 4, 2, 2, 3, 3]
    for part in range(6):
        for region in range(len(geometry.names[part])):
            cloud = getattr(geometry, f'cloud_{part}_{region}')
            assert (geometry.classify_local(torch.full((len(cloud),), part), cloud) == region).all()
            assert ((cloud-geometry.landmark[part, region]).abs().sum(-1) == 0).any()
    p = torch.zeros(2, 6, 3); rot = torch.eye(3).expand(2, 6, 3, 3)
    h = torch.zeros(2, HEIGHTMAP_ROWS, HEIGHTMAP_COLS)
    result = geometry(p, rot, h).reshape(2, 6, 4, 8)
    assert torch.isfinite(result).all()
    assert (result[:, ~geometry.valid] == 0).all()
    p[..., 0] += 100
    assert geometry(p, rot, h).reshape(2, 6, 4, 8)[..., -2:].count_nonzero() == 0


def test_regional_plan_warm_start_preserves_pose_and_has_nonempty_valid_subsets():
    torch.manual_seed(4)
    base = Full1000PositionPredictor(24, 1, 8).eval()
    model = Full1000PositionPredictor(24, 1, 8, region_plan=True, unified_contact=True).eval()
    missing = model.load_state_dict(base.state_dict(), strict=False)
    assert not missing.unexpected_keys and all(n.startswith(('region_', 'execution_geometry_encoder.')) for n in missing.missing_keys)
    q = torch.zeros(2, 36); q[:, 2] = .8; q[:, 3] = 1
    obs = dict(current_q=q, current_contact=torch.zeros(2, 6, dtype=torch.bool),
        current_anchor=torch.zeros(2, 6, 3), heightmap=torch.full((2, HEIGHTMAP_ROWS, HEIGHTMAP_COLS), -.8))
    a, b = base(**obs), model(**obs)
    torch.testing.assert_close(a.qpos, b.qpos, rtol=0, atol=0)
    torch.testing.assert_close(a.role_logits, b.role_logits, rtol=0, atol=0)
    assert torch.equal(b.planned_regions.any(-1), b.conditioned_contact)
    assert not (b.planned_regions & ~model.region_geometry.valid).any()
    b.qpos.square().sum().backward()
    assert model.region_plan_encoder.weight.grad.abs().sum() > 0
    assert model.region_geometry_encoder[-1].weight.grad is None
    assert model.execution_geometry_encoder.weight.grad.abs().sum() > 0


class TwoFeet:
    def link_poses(self, q, names):
        p = torch.stack([q[:, :3] if n.startswith('left') else q[:, 7:10] for n in names], 1)
        return p, torch.eye(3).to(q).expand(len(q), len(names), 3, 3)


class TestRegions:
    valid = torch.ones(6, 4, dtype=torch.bool)
    def witness_regions(self, fk, q, sample, part, points):
        return (points[:, 0] > 0).long()
    def missing_region_distance(self, fk, q, surface, scene, margin):
        return q.sum(-1)[:, None, None].expand(-1, 6, 4)*0
    def actual_mask(self, fk, rows, surface):
        from contact_solver.device_contact_objective import group_any
        p = rows.pair
        group = (p['sample']*6+p['part'])*4+self.witness_regions(fk, rows.q, p['sample'], p['part'], rows.points[:, 1])
        return group_any(group, p['eligible'], len(rows)*24).reshape(len(rows), 6, 4)


def witness_fixture(depths):
    q = torch.zeros(1, 36, requires_grad=True)
    point = torch.tensor([[-.1, 0., 0.], [.1, 0., 0.]])
    p = dict(sample=torch.tensor([0, 0]), part=torch.tensor([0, 1]), task_pair=torch.ones(2, dtype=torch.bool),
        dist=torch.tensor(depths), geometry_point0_w=point, geometry_point1_w=point,
        normal_w=torch.tensor([[0., 0., 1.]]*2), body_link0=torch.tensor([-1, -1]), body_link1=torch.tensor([0, 1]),
        full_kind=torch.zeros(2, dtype=torch.long), primary_surface=torch.zeros(2, dtype=torch.long),
        upward=torch.ones(2, dtype=torch.bool), active=torch.tensor(depths)<.02,
        constraint_allocated=torch.tensor(depths)<.02, includemargin=torch.full((2,), .02), eligible=torch.tensor(depths)<.02)
    observed=dict(schema='newton_device_witness_batch_v1', pairs=p,
        link_names=('left_ankle_roll_link', 'right_ankle_roll_link'), configured_margin=torch.tensor([.02]))
    model=type('Model', (), {'fk':TwoFeet(), 'region_geometry':TestRegions()})()
    active=torch.tensor([[True, True, False, False, False, False]])
    regions=torch.zeros(1, 6, 4, dtype=torch.bool);regions[0,0,0]=True;regions[0,1,1]=True
    return q, observed, model, active, regions


def test_unified_contact_remains_repulsive_after_activation_and_both_feet_receive_gradient():
    q, obs, model, active, regions = witness_fixture([-.02, -.01])
    rows=DeviceWitnessRows(model.fk,q,obs)
    loss,metrics=unified_region_objective(model,rows,active,torch.zeros(1,6,dtype=torch.long),{},regions)
    assert metrics['region_plan_realized'].item() == 1
    grad=torch.autograd.grad(loss.sum(),q)[0]
    assert grad[0,2]<0 and grad[0,9]<0
    duplicate=dict(obs,pairs={k:v.repeat_interleave(3,0) for k,v in obs['pairs'].items()})
    other,_=unified_region_objective(model,DeviceWitnessRows(model.fk,q,duplicate),active,torch.zeros(1,6,dtype=torch.long),{},regions)
    torch.testing.assert_close(loss,other)


def test_unified_contact_attracts_above_band_and_allows_unselected_regions_to_lift():
    q,obs,model,active,regions=witness_fixture([.025,.0005])
    loss,_=unified_region_objective(model,DeviceWitnessRows(model.fk,q,obs),active,torch.zeros(1,6,dtype=torch.long),{},regions)
    grad=torch.autograd.grad(loss.sum(),q)[0]
    assert grad[0,2]>0 and grad[0,9]==0
    # The rear-only plan does not demand every regional point to touch.
    assert regions.sum()==2 and loss>0


def test_region_truth_requires_selected_allocated_witnesses():
    geo=ContactRegions(CanonicalG1ForwardKinematics())
    q=torch.zeros(1,36);q[:,3]=1
    fk=CanonicalG1ForwardKinematics()
    p,r=fk.link_poses(q,('left_ankle_roll_link',))
    point=(p[0,0]+r[0,0]@geo.landmark[0,2]).tolist()
    required=torch.zeros(6,4,dtype=torch.bool);required[0,2]=True
    assert not geo.audit_pairs(fk,q,[],[0]*6,required)['realized']
    pair=dict(part=0,surface=0,allocated=True,constraint_active=True,position_w=point)
    assert geo.audit_pairs(fk,q,[pair],[0]*6,required)['realized']


def test_front_and_rear_of_same_foot_are_independent_and_extra_collision_cannot_reduce_loss():
    q,obs,model,active,regions=witness_fixture([-.02,-.01])
    obs['pairs']['part'][:]=0;obs['pairs']['body_link1'][:]=0
    active[:,1]=False;regions[:,1]=False
    # Rear is planned; the forefoot still has to avoid penetration.
    loss,_=unified_region_objective(model,DeviceWitnessRows(model.fk,q,obs),active,torch.zeros(1,6,dtype=torch.long),{},regions)
    torch.testing.assert_close(loss,torch.tensor([7+(7+3)/24]))
    lifted=dict(obs,pairs={k:v.clone() for k,v in obs['pairs'].items()})
    lifted['pairs']['dist'][1]=.03;lifted['pairs']['eligible'][1]=False
    less,_=unified_region_objective(model,DeviceWitnessRows(model.fk,q,lifted),active,torch.zeros(1,6,dtype=torch.long),{},regions)
    assert loss>less


def test_unknown_penetration_requires_audit_and_has_no_training_gradient(tmp_path):
    import pytest
    q,obs,model,active,regions=witness_fixture([-.02,-.01])
    obs['pairs']['task_pair'][1]=False
    obs['pairs']['normal_w'][1]=float('nan')
    rows=DeviceWitnessRows(model.fk,q,obs)
    with pytest.raises(ValueError,match='explicit audit'):
        unified_region_objective(model,rows,active,torch.zeros(1,6,dtype=torch.long),{},regions)
    loss,m=unified_region_objective(model,rows,active,torch.zeros(1,6,dtype=torch.long),{},regions,audit_path=tmp_path/'audit.jsonl')
    assert m['region_gradient_valid'].item()==0 and m['region_invalid_penetrating_normals'].item()==1
    loss.sum().backward()
    assert q.grad.abs().sum()==0 and (tmp_path/'audit.jsonl').exists()


def test_opposite_violations_in_one_region_both_receive_gradients():
    q, obs, model, active, regions = witness_fixture([.03, -.02])
    class IndependentFootLinks:
        def link_poses(self, q, names):
            p = torch.stack([q[:, :3], q[:, 7:10]], 1)
            return p, torch.eye(3).to(q).expand(len(q), 2, 3, 3)
    model.fk = IndependentFootLinks()
    obs['link_names'] = ('left_ankle_roll_link', 'left_ankle_roll_sphere_1_link')
    obs['pairs']['geometry_point0_w'][:, 0] = -.1
    obs['pairs']['geometry_point1_w'][:, 0] = -.1
    obs['pairs']['part'][:] = 0
    # A top-face gap and a different side collision belong to the same
    # anatomical region, but only the top face is a valid contact target.
    obs['pairs']['upward'][1] = False
    obs['pairs']['eligible'][:] = False
    active[:, 1] = False; regions[:, 1] = False
    loss, metrics = unified_region_objective(model, DeviceWitnessRows(model.fk, q, obs),
        active, torch.zeros(1, 6, dtype=torch.long), {}, regions)
    torch.testing.assert_close(loss, torch.tensor([10+10/24]))
    grad = torch.autograd.grad(loss.sum(), q, retain_graph=True)[0]
    assert grad[0, 2] > 0  # Pull the top-facing witness down.
    assert grad[0, 9] < 0  # Push the other witness out of penetration.
    pieces = metrics['unified_attraction_component']+metrics['unified_separation_component']
    torch.testing.assert_close(pieces, loss)
    torch.testing.assert_close(torch.autograd.grad(pieces.sum(), q)[0], grad)


def test_activated_contacts_inside_actual_margin_have_no_attraction_gradient():
    q, obs, model, active, regions = witness_fixture([.019, .002])
    loss, metrics = unified_region_objective(model, DeviceWitnessRows(model.fk, q, obs),
        active, torch.zeros(1, 6, dtype=torch.long), {}, regions)
    assert metrics['region_plan_realized'].item() == 1
    assert loss.item() == 0
    assert torch.autograd.grad(loss.sum(), q)[0].abs().sum() == 0


def test_frozen_activated_witness_still_attracts_after_fk_crosses_margin():
    q, obs, model, active, regions = witness_fixture([.019, .002])
    rows = DeviceWitnessRows(model.fk, q, obs)
    # Move a frozen differentiable witness without changing query-time flags.
    rows.distances = rows.distances + q.new_tensor([.003, 0.])
    loss, _ = unified_region_objective(model, rows,
        active, torch.zeros(1, 6, dtype=torch.long), {}, regions)
    assert obs['pairs']['eligible'][0]
    assert torch.autograd.grad(loss.sum(), q)[0][0, 2] > 0


def test_regional_attraction_uses_each_actual_pair_margin():
    q, obs, model, active, regions = witness_fixture([.019, .019])
    obs['pairs']['includemargin'] = torch.tensor([.01, .03])
    for key in ('active', 'constraint_allocated', 'eligible'):
        obs['pairs'][key] = torch.tensor([False, True])
    loss, metrics = unified_region_objective(model, DeviceWitnessRows(model.fk, q, obs),
        active, torch.zeros(1, 6, dtype=torch.long), {}, regions)
    gradient = torch.autograd.grad(loss.sum(), q)[0]
    assert gradient[0, 2] > 0 and gradient[0, 9] == 0
    assert metrics['region_plan_realized'].item() == 0


def test_zero_regional_residual_at_margin_does_not_certify_contact():
    q, obs, model, active, regions = witness_fixture([.02, .002])
    loss, metrics = unified_region_objective(model, DeviceWitnessRows(model.fk, q, obs),
        active, torch.zeros(1, 6, dtype=torch.long), {}, regions)
    assert loss.item() == 0
    assert not obs['pairs']['eligible'][0]
    assert metrics['region_plan_realized'].item() == 0
