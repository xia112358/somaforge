import numpy as np
import pytest
from motion_edit.generation.native_contact_refinement import event_contact_intent


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


def test_side_witness_guides_pose_without_relabeling_it_as_target_contact():
    import torch
    from motion_edit.generation.native_contact_refinement import refine_trajectory,RefinementConfig
    class FK:
        joint_lower=torch.full((29,),-1.)
        joint_upper=torch.ones(29)
        def link_poses(self,q,names):
            return q[:,None,:3].expand(-1,len(names),-1),torch.eye(3).expand(len(q),len(names),3,3)
    def query(q,scene):
        rows=[]
        for pose in q:
            rows.append([dict(part=0,surface=9,body_name='left_ankle_roll_link',
                witness_schema='newton_geometry_pair_v1',geometry_witness_available=True,
                constraint_type=1,dist=.01,includemargin=.02,constraint_active=True,
                allocated=True,efc_address=[0],position_w=pose[:3].tolist(),
                terrain_position_w=(pose[:3]-[.01,0,0]).tolist(),normal_w=[1,0,0])])
        return dict(candidate_pairs=rows,provenance={'model_fingerprint':'test'},
                    full_robot_separation=[dict(worst_terrain=None,worst_self=None) for _ in q])
    q=torch.zeros((3,36));q[:,3]=1;q[:,2]=.03
    wanted_event=dict(start_frame=0,end_frame=2,persistent_parts=['left_foot'],
        source_surfaces=[0,-1,-1,-1,-1,-1],target_surfaces=[0,-1,-1,-1,-1,-1],touchdown_events=[])
    local=np.zeros((3,6,3));target=local.copy();target[:,:,2]=.01
    valid=np.zeros((3,6),bool);valid[:,0]=True
    geometry=dict(normal=[0,0,1],origin=[0,0,0],surface_type='plane')
    result,history=refine_trajectory(q,FK(),[wanted_event],query,'test',
        config=RefinementConfig(steps=1,audit_every=1),
        approach_tasks=(local,target,valid,[[geometry]*6 for _ in range(3)]))
    assert torch.all(result[:,2]<q[:,2])
    assert history[-1]['missing_contacts']==3
    assert not history[-1]['passed']
