import numpy as np
import pytest
from motion_edit.generation.native_contact_refinement import event_contact_intent


def solid_query(link_names, heights):
    """Independent analytic solids for the native-query test doubles."""
    import torch
    from contact_solver.solid_witness_loss import SolidSceneRouter
    from somaforge_core.robot_assets import canonical_g1_asset_metadata
    from somaforge_core.solid_distance import SOLID_GEOMETRY_SCHEMA
    shapes = [dict(shape=0, body=None, kind='box', scale=[5., 5., .25],
                   transform=[0., 0., -.25, 0., 0., 0., 1.])]
    for index, (name, height) in enumerate(zip(link_names, heights), 1):
        shapes.append(dict(shape=index, body=name, kind='sphere', scale=[.02]*3,
                           transform=[0., 0., height, 0., 0., 0., 1.]))
    router = SolidSceneRouter({0: dict(schema=SOLID_GEOMETRY_SCHEMA, model_fingerprint='f'*64,
        robot_asset=canonical_g1_asset_metadata(), shapes=shapes,
        allowed_pairs=[[0, i] for i in range(1, len(shapes))])}, link_names)
    return lambda fk, q: router(fk, q, torch.zeros(len(q), dtype=torch.long, device=q.device))


def event():
    return dict(start_frame=2,end_frame=8,persistent_parts=['left_foot'],
                source_surfaces=[0,-1,-1,-1,-1,-1],target_surfaces=[0,-1,1,-1,-1,-1],
                touchdown_events=[dict(part_index=2,surface=1)])


def test_event_support_survives_frame_holes_and_touchdown_only_at_endpoint():
    active,face=event_contact_intent([event()],10)
    np.testing.assert_array_equal(np.flatnonzero(active[:,0]),np.arange(2,9))
    np.testing.assert_array_equal(np.flatnonzero(active[:,2]),[8])
    assert np.all(face[2:9,0]==0)


def test_conflicting_surface_intent_fails_closed():
    second=event();second['source_surfaces'][0]=second['target_surfaces'][0]=1
    with pytest.raises(ValueError,match='Conflicting'):
        event_contact_intent([event(),second],10)


def test_missing_authored_surface_task_fails_without_creating_contact_target():
    from motion_edit.generation.native_contact_refinement import require_material_task_coverage
    wanted, _ = event_contact_intent([event()], 10)
    valid = wanted.copy()
    domains = [[dict(normal=[0,0,1], origin=[0,0,0]) if active else None for active in row] for row in wanted]
    tasks = (np.zeros((10,6,3)), np.zeros((10,6,3)), valid, domains)
    require_material_task_coverage([event()], 10, tasks)
    valid[8,2] = False; domains[8][2] = None
    with pytest.raises(ValueError, match='required part-frames.*8, 2'):
        require_material_task_coverage([event()], 10, tasks)
    assert not valid[8,2] and domains[8][2] is None


def test_three_state_events_use_explicit_release_only():
    from motion_edit.generation.native_contact_refinement import event_contact_roles
    e = event(); e['touchdown_events'][0].update(frame=8, release_frame=5)
    assert not event_contact_roles([e], 10)[2].any()
    e['release_events'] = [dict(start_frame=5, end_frame_exclusive=8, part_index=2, scope='whole_endpoint')]
    active, face, release = event_contact_roles([e], 10)
    np.testing.assert_array_equal(np.flatnonzero(release[:, 2]), [5, 6, 7])
    assert active[8, 2] and not release[8, 2]
    assert not release[:, 1].any() and not active[:, 1].any()
    e['release_events'][0]['part_index'] = 0
    with pytest.raises(ValueError, match='conflict'):
        event_contact_roles([e], 10)


def test_joint_continuity_uses_source_and_allows_constant_offsets():
    import torch
    from motion_edit.generation.native_contact_refinement import joint_continuity_terms
    source = torch.arange(5.)[:, None] * .01
    v, a = joint_continuity_terms(source+.2, source)
    assert v < 1.e-10 and a < 1.e-10
    edited = source.clone(); edited[2] += .3; edited.requires_grad_()
    v, a = joint_continuity_terms(edited, source)
    gradient = torch.autograd.grad(v+a, edited)[0]
    assert gradient[2] > 0 and gradient[1] < 0 and gradient[3] < 0
    with pytest.raises(ValueError, match='align'):
        joint_continuity_terms(edited, source[:-1])


def test_output_smoothness_repairs_jump_instead_of_preserving_candidate():
    import torch
    from motion_edit.generation.native_contact_refinement import marker_acceleration_loss
    points = torch.tensor([0., 1., 4., 3., 4.], requires_grad=True)
    loss = marker_acceleration_loss(points, 1.)
    gradient = torch.autograd.grad(loss, points)[0]
    assert gradient[2] > 0
    assert marker_acceleration_loss(points-.01*gradient, 1.) < loss
    assert marker_acceleration_loss(torch.arange(5.), 1.) == 0


def test_marker_continuity_preserves_source_acceleration_and_constant_corrections():
    import torch
    from motion_edit.generation.native_contact_refinement import marker_acceleration_loss
    source = torch.tensor([0., .1, .6, 1.4, 2.7], requires_grad=True)
    points = source.detach().clone().requires_grad_()
    value = marker_acceleration_loss(points, .01, source)
    assert value == 0 and torch.autograd.grad(value, points)[0].eq(0).all()
    assert marker_acceleration_loss(source, .01) > 0
    shifted = source.detach()+.3+torch.arange(len(source))*.02
    assert marker_acceleration_loss(shifted, .01, source) < 1.e-8
    changed = source.detach().clone(); changed[2] += .3; changed.requires_grad_()
    value = marker_acceleration_loss(changed, .01, source)
    grad, source_grad = torch.autograd.grad(value, (changed, source), allow_unused=True)
    assert source_grad is None  # immutable demonstration, not an optimized target
    assert grad[2] > 0 and grad[1] < 0 and grad[3] < 0
    with pytest.raises(ValueError, match='align'):
        marker_acceleration_loss(changed, .01, source[:-1])


def test_material_guidance_only_for_missing_candidates():
    import torch
    from motion_edit.generation.native_contact_refinement import missing_material_guidance
    class FK:
        def link_poses(self, q, names):
            return q[:,None,:3].expand(-1,6,-1),torch.eye(3).expand(len(q),6,3,3)
    q=torch.tensor([[1.,0.,0.]],requires_grad=True)
    local=torch.zeros(1,6,3);target=torch.zeros_like(local)
    valid=torch.ones(1,6,dtype=torch.bool);missing=torch.zeros_like(valid);missing[0,2]=True
    value=missing_material_guidance(FK(),q,local,target,valid,missing,torch.tensor([.02]))
    assert torch.autograd.grad(value.sum(),q)[0][0,0] > 0
    assert missing_material_guidance(FK(),q,local,target,valid,torch.zeros_like(missing),torch.tensor([.02])).item()==0
    valid[0,2]=False
    with pytest.raises(ValueError,match='no event material target'):
        missing_material_guidance(FK(),q,local,target,valid,missing,torch.tensor([.02]))


def test_approach_keeps_fixed_child_material_coordinates_and_does_not_invent_evidence():
    from types import SimpleNamespace
    import torch
    from motion_edit.generation.native_contact_refinement import demonstrated_approach_tasks
    class FK:
        def link_poses(self, q, names):
            p=torch.zeros((len(q),len(names),3));r=torch.eye(3).expand(len(q),len(names),3,3).clone()
            p[:,names.index('left_ankle_roll_sphere_3_link'),0]=1
            return p,r
    contact=SimpleNamespace(body_label='left_ankle_roll_sphere_3_link',
        metadata={'target_surface_geometry':{'normal':[0,0,1],'origin':[0,0,0],'surface_type':'plane'}},
        frames=np.array([2,8]),points_local=np.zeros((1,3)),points_local_by_frame=None,
        resolved_target_points_w=lambda:np.array([[[1.,0,0]],[[1.,0,0]]]))
    spec=SimpleNamespace(frame_count=10,contacts=[contact])
    local,target,valid,domains=demonstrated_approach_tasks(spec,[event()],FK(),torch.zeros((10,36)),
        [{'surface':0,'normal_w':[0,0,1],'plane_offset':0}])
    np.testing.assert_allclose(local[2:9,0],np.tile([1.,0,0],(7,1)))
    assert valid[2:9,0].all()
    assert not valid[:,2].any()  # no hand observation; cannot invent a task


def test_finite_face_approach_preserves_clearance_and_moves_off_edge():
    from motion_edit.generation.native_contact_refinement import interior_approach_goal
    geometry=dict(normal=[0,0,1],origin=[0,0,0],surface_type='mesh',
                  polygon_world=[[-1,-1,0],[1,-1,0],[1,1,0],[-1,1,0]])
    for point in ([1,0,.02],[1.1,0,.02]):
        goal=interior_approach_goal(point,geometry)
        assert goal[2]==.02
        assert -1 < goal[0] < 1
        assert goal[1]==0


def test_absent_witness_has_region_approach_gradient_but_no_contact_truth():
    import torch
    from motion_edit.generation.native_contact_refinement import refine_trajectory, RefinementConfig
    from somaforge_core.g1_kinematics import CanonicalG1ForwardKinematics
    fk = CanonicalG1ForwardKinematics()
    def query(q):
        ints = ('sample', 'part', 'primary_surface', 'body_link0', 'body_link1', 'full_kind', 'type')
        bools = ('task_pair', 'upward', 'eligible', 'active', 'constraint_allocated')
        p = {k: torch.empty(0, dtype=torch.long) for k in ints}
        p.update({k: torch.empty(0, dtype=torch.bool) for k in bools})
        p.update({k: q.new_empty(0, 3) for k in ('geometry_point0_w', 'geometry_point1_w', 'normal_w')})
        p.update(dist=q.new_empty(0), includemargin=q.new_empty(0))
        return dict(schema='newton_device_witness_batch_v1', pairs=p,
                    link_names=('left_ankle_roll_link',), configured_margin=q.new_full((len(q),), .02),
                    provenance={'model_fingerprint': 'test'})
    q = torch.zeros(3, 36); q[:, 3] = 1; q[:, 2] = 1.2
    wanted_event = dict(start_frame=0, end_frame=2, persistent_parts=['left_foot'],
        source_surfaces=[0,-1,-1,-1,-1,-1], target_surfaces=[0,-1,-1,-1,-1,-1], touchdown_events=[])
    local=np.zeros((3,6,3)); valid=np.zeros((3,6),bool); valid[:,0]=True
    geometry=dict(normal=[0,0,1], origin=[0,0,0], surface_type='plane')
    result, history = refine_trajectory(q, fk, [wanted_event], query, 'test',
        config=RefinementConfig(steps=1, audit_every=1),
        solid_query=solid_query(('left_ankle_roll_link',), (.03,)),
        approach_tasks=(local, local, valid, [[geometry]*6 for _ in range(3)]))
    assert torch.all(result[:,2] < q[:,2])
    assert history[-1]['missing_contacts'] == 3
    assert history[-1]['objective_schema'] == 'event_material_recovery_output_smoothness_v1'
    # Geometrically feasible input still needs the source-continuity update.
    jump = q.clone(); jump[1, 7] = .2
    _, continuous = refine_trajectory(jump, fk, [], query, 'test',
        config=RefinementConfig(steps=1, audit_every=1), continuity_reference=q,
        solid_query=solid_query(('left_ankle_roll_link',), (.03,)),
        approach_tasks=(local, local, valid, [[geometry]*6 for _ in range(3)]))
    assert continuous[0]['passed'] and continuous[-1]['step'] == 1
    assert continuous[-1]['joint_velocity_residual'] < continuous[0]['joint_velocity_residual']
    assert not history[-1]['passed']


def test_regional_refinement_keeps_attraction_and_separation_after_activation():
    """Activation must not suppress either interval derivative."""
    import torch
    from motion_edit.generation.regional_contact_refinement import regional_terms
    class FK:
        def link_poses(self, q, names):
            pos = torch.stack([q[:, :3] if name.startswith('left') else q[:, 7:10] for name in names], 1)
            return pos, torch.eye(3).to(q).expand(len(q), len(names), 3, 3)
    class Regions:
        valid = torch.ones(6, 4, dtype=torch.bool)
        def witness_regions(self, fk, q, sample, part, points):
            return torch.zeros_like(part)
        def missing_region_distance(self, fk, q, surface, scene, margin):
            return q.new_full((len(q), 6, 4), 100.)
        def actual_mask(self, fk, rows, surface):
            result = torch.zeros(len(rows), 6, 4, dtype=torch.bool)
            result[:, :2, 0] = True
            return result
    q = torch.zeros(1, 36, requires_grad=True)
    pair = dict(sample=torch.zeros(2, dtype=torch.long), part=torch.tensor([0, 1]),
        primary_surface=torch.zeros(2, dtype=torch.long), type=torch.ones(2, dtype=torch.long),
        task_pair=torch.ones(2,dtype=torch.bool), upward=torch.ones(2,dtype=torch.bool),
        active=torch.ones(2,dtype=torch.bool), constraint_allocated=torch.ones(2,dtype=torch.bool),
        eligible=torch.ones(2,dtype=torch.bool), dist=torch.tensor([.01,-.01]),
        includemargin=torch.tensor([.02,.02]), full_kind=torch.zeros(2,dtype=torch.long),
        body_link0=torch.tensor([-1,-1]), body_link1=torch.tensor([0,1]),
        geometry_point0_w=torch.zeros(2,3), geometry_point1_w=torch.zeros(2,3),
        normal_w=torch.tensor([[0.,0.,1.],[0.,0.,1.]]))
    observed=dict(schema='newton_device_witness_batch_v1', pairs=pair,
        configured_margin=torch.tensor([.02]), link_names=('left_ankle_roll_link','right_ankle_roll_link'))
    wanted=torch.tensor([[True,True,False,False,False,False]])
    query_solid = solid_query(observed['link_names'], (.03, .01))
    loss,depth,missing,off,metrics=regional_terms(FK(),Regions(),q,observed,wanted,torch.zeros(1,6,dtype=torch.long),[[None]*6], solid=query_solid(FK(), q))
    grad=torch.autograd.grad(loss.sum(),q)[0]
    assert grad[0,2]==0  # activated left foot is already inside its actual margin
    assert grad[0,9]<0  # active right foot penetrates and must leave the surface
    assert not missing.any() and not off.any()
    torch.testing.assert_close(depth,torch.tensor([.01]))
    torch.testing.assert_close(loss,metrics['unified_attraction_component']+metrics['unified_separation_component'])
    # Sparse intent: an unrequested positive-gap contact is unconstrained;
    # penetration still repels. Only an explicit release moves the first foot.
    none = torch.zeros_like(wanted)
    faces = torch.zeros(1,6,dtype=torch.long)
    free_loss,_,_,_,free_metrics = regional_terms(FK(),Regions(),q,observed,none,faces,[[None]*6], solid=query_solid(FK(), q))
    free_grad = torch.autograd.grad(free_loss.sum(),q)[0]
    assert free_grad[0,2] == 0 and free_grad[0,9] < 0
    released = none.clone(); released[0,0] = True
    release_loss,_,_,_,release_metrics = regional_terms(FK(),Regions(),q,observed,none,faces,[[None]*6],released, solid=query_solid(FK(), q))
    release_grad = torch.autograd.grad(release_loss.sum(),q)[0]
    assert release_grad[0,2] < 0
    assert release_metrics['release_violations'][0,0]
    assert not free_metrics['release_violations'].any()
    # Preserve complete-plan training semantics when the new argument is absent.
    from types import SimpleNamespace
    from contact_solver.contact_regions import unified_region_objective
    from contact_solver.device_contact_objective import DeviceWitnessRows
    rows = DeviceWitnessRows(FK(), q, observed)
    rows.solid = query_solid(FK(), q)
    legacy,_ = unified_region_objective(SimpleNamespace(fk=FK(),region_geometry=Regions()),
        rows,none,faces,{})
    assert torch.autograd.grad(legacy.sum(),q)[0][0,2] < 0
    pair['constraint_allocated'][0]=False
    with pytest.raises(ValueError,match='Unallocated'):
        regional_terms(FK(),Regions(),q,observed,wanted,torch.zeros(1,6,dtype=torch.long),[[None]*6])


def test_generic_event_face_proxy_matches_training_box_proxy():
    import torch
    from contact_solver.contact_regions import ContactRegions
    from motion_edit.generation.regional_contact_refinement import EventContactRegions
    from somaforge_core.g1_kinematics import CanonicalG1ForwardKinematics
    fk=CanonicalG1ForwardKinematics()
    base=ContactRegions(fk); generic=EventContactRegions(fk)
    q=torch.zeros(2,36);q[:,3]=1;q[:,2]=.9;q[1,0]=.6
    faces=torch.tensor([[0]*6,[1]*6]);margin=torch.full((2,),.02)
    ground=dict(normal=[0,0,1],origin=[0,0,0],surface_type='plane')
    top=dict(normal=[0,0,1],origin=[0,0,.8],surface_type='mesh',
        polygon_world=[[-.5,-.3,.8],[.5,-.3,.8],[.5,.3,.8],[-.5,.3,.8]])
    scene=dict(box_center=torch.tensor([[0.,0.,.4]]*2),box_rotation=torch.eye(3).repeat(2,1,1),
        box_half_extents=torch.tensor([[.5,.3,.4]]*2),ground_height=torch.zeros(2))
    expected=base.missing_region_distance(fk,q,faces,scene,margin)
    actual=generic.missing_region_distance(fk,q,faces,
        dict(domains=[[ground]*6,[top]*6],wanted=torch.ones(2,6,dtype=torch.bool)),margin)
    torch.testing.assert_close(actual,expected)


def test_both_missing_contact_proxies_use_the_full_actual_margin():
    from types import SimpleNamespace
    import torch
    from contact_solver.contact_regions import ContactRegions
    from motion_edit.generation.regional_contact_refinement import EventContactRegions

    class FK:
        def link_poses(self, q, names):
            return q[:, None, :3].expand(-1, len(names), -1), torch.eye(3).to(q).expand(len(q), len(names), 3, 3)

    geometry = SimpleNamespace(names=[('only',)]*6, material_skin=None,
        **{f'cloud_{part}_0': torch.zeros(1, 3) for part in range(6)})
    ground = dict(normal=[0, 0, 1], origin=[0, 0, 0], surface_type='plane')
    for proxy in (ContactRegions.missing_region_distance, EventContactRegions.missing_region_distance):
        q = torch.zeros(2, 36); q[:, 2] = torch.tensor([.019, .024]); q.requires_grad_()
        faces = torch.zeros(2, 6, dtype=torch.long)
        scene = dict(box_center=torch.zeros(2, 3), box_rotation=torch.eye(3).repeat(2, 1, 1),
            box_half_extents=torch.ones(2, 3), ground_height=torch.zeros(2),
            domains=[[ground]*6]*2, wanted=torch.ones(2, 6, dtype=torch.bool))
        loss = proxy(geometry, FK(), q, faces, scene, torch.full((2,), .02))
        gradient = torch.autograd.grad(loss.sum(), q)[0]
        assert loss[0].sum() == 0 and gradient[0, 2] == 0
        assert loss[1].sum() > 0 and gradient[1, 2] > 0


def test_refinement_selection_cannot_prefer_a_stationary_marker_over_material_budget():
    from motion_edit.generation.native_contact_refinement import loaded_material_candidate_rank
    from somaforge_core.loaded_material_motion import MATERIAL_MOTION_SCHEMA

    def candidate(path, marker_drift, passed):
        return dict(event_acceptance=dict(failed_checks=0), max_penetration_mm=1.,
            source_support=dict(accumulated_drift_max_mm=marker_drift),
            phase_support=dict(schema=MATERIAL_MOTION_SCHEMA,
                phases=[dict(passed=passed, edited_budget=dict(material_tangent_path_m=path))]))

    within_budget = candidate(.04, 100., True)
    over_budget = candidate(.08, 0., False)
    assert loaded_material_candidate_rank(within_budget) < loaded_material_candidate_rank(over_budget)
    within_budget['source_support']['accumulated_drift_max_mm'] = 10000.
    assert loaded_material_candidate_rank(within_budget) < loaded_material_candidate_rank(over_budget)
    # Partial known motion is not a measured zero-motion reference.
    unknown = candidate(0., 0., None)
    assert loaded_material_candidate_rank(within_budget) < loaded_material_candidate_rank(unknown)
    assert loaded_material_candidate_rank(dict(phase_support=dict(phases=[]))) is None
