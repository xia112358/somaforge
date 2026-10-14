from types import SimpleNamespace
import numpy as np
from motion_edit.generation.support_motion import compile_support_motion


def fixture():
    n=6
    indices=np.array([[0],[0],[1],[1],[0],[0]])
    pos=np.zeros((n,2,3));pos[:,:,0]=np.arange(n)[:,None]*.01
    rot=np.broadcast_to(np.eye(3),(n,2,3,3)).copy()
    target=pos[np.arange(n)[:,None],indices].copy()
    target[:,:,0]+=np.array([.1,.1,.3,.3,.5,.5])[:,None]
    c=SimpleNamespace(frame_count=n,contact_link_indices=indices,contact_points_local=np.zeros((n,1,3)),
                      contact_targets_w=target,contact_weights=np.ones((n,1)))
    normals=np.broadcast_to([0.,0.,1.],(n,1,3))
    return c,pos,rot,normals


def test_temporal_terms_need_real_history():
    from motion_edit.generation.support_motion import temporal_history_mask
    np.testing.assert_array_equal([temporal_history_mask(t) for t in range(4)],
                                  [[0,0],[1,0],[1,1],[1,1]])


def test_shape_switch_keeps_one_endpoint_edit_and_source_motion():
    c,p,r,n=fixture()
    target,mask,episodes=compile_support_motion(c,['left_ankle_roll_link','left_ankle_roll_sphere_1_link'],p,r,np.eye(3),n)
    assert len(episodes)==1
    assert mask.all()
    np.testing.assert_allclose(np.diff(target[:,0,0]),.01)
    np.testing.assert_allclose(target[:,:,2],c.contact_targets_w[:,:,2])


def test_release_allows_a_new_landing_edit():
    c,p,r,n=fixture();c.contact_weights[3]=0
    target,mask,episodes=compile_support_motion(c,['left_ankle_roll_link','left_ankle_roll_sphere_1_link'],p,r,np.eye(3),n)
    assert len(episodes)==2 and not mask[3,0]
    np.testing.assert_allclose(target[4:,0,0]-p[4:,0,0],.5)


def test_other_endpoint_does_not_merge_into_same_support():
    c,p,r,n=fixture()
    _,_,episodes=compile_support_motion(c,['left_ankle_roll_link','right_ankle_roll_link'],p,r,np.eye(3),n)
    assert len(episodes)==3


def test_rotated_edit_tracks_material_points_and_preserves_normal_targets():
    c,p,r,n=fixture()
    c.contact_points_local[:,0,0]=np.arange(6)*.002
    yaw=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    source=p[np.arange(6)[:,None],c.contact_link_indices]+c.contact_points_local
    rotated=np.einsum('ij,tnj->tni',yaw,source)
    c.contact_targets_w=rotated+np.array([.2,.3,.04])
    c.contact_targets_w[:,0,0]+=np.array([-.02,-.01,0.,0.,.01,.02])
    c.contact_targets_w[:,0,2]+=np.arange(6)*.001
    target,_,_=compile_support_motion(c,['left_ankle_roll_link','left_ankle_roll_sphere_1_link'],p,r,yaw,n)
    np.testing.assert_allclose(target[:,:,:2],(rotated+np.array([.2,.3,.04]))[:,:,:2])
    np.testing.assert_allclose(target[:,:,2],c.contact_targets_w[:,:,2])


def test_authored_surface_edit_is_not_unrotated_weak_reference():
    from motion_edit.generation.support_motion import authored_support_targets
    c,p,r,n=fixture()
    surface=dict(surface_id='ground',origin=[0.,0.,0.],normal=[0.,0.,1.],tangent_u=[1.,0.,0.],tangent_v=[0.,1.,0.])
    edited={**surface,'origin':[.8,.4,0.],'tangent_u':[0.,1.,0.],'tangent_v':[-1.,0.,0.]}
    contacts=[SimpleNamespace(body_label='left_ankle_roll_link',frames=np.arange(6),points_local=np.zeros((1,3)),surface_id='ground',
        metadata={'source_surface_id':'ground','target_surface_geometry':{'normal':[0.,0.,1.]}})]
    spec=SimpleNamespace(frame_start=0,contacts=contacts,metadata={'support_surface_transforms':[dict(source_surface=surface,target_surface=edited)]})
    c.contact_link_indices[:]=0
    target=authored_support_targets(spec,c,['left_ankle_roll_link','right_ankle_roll_link'],p,r)
    np.testing.assert_allclose(target[:,0,0],.8)
    np.testing.assert_allclose(target[:,0,1],.4+np.arange(6)*.01)
    target, edit_rotations = authored_support_targets(spec,c,['left_ankle_roll_link','right_ankle_roll_link'],p,r,return_rotations=True)
    np.testing.assert_allclose(edit_rotations[:,0],np.broadcast_to([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]],(6,3,3)))


def test_top_support_does_not_inherit_ground_heading_rotation():
    c,p,r,n=fixture()
    c.contact_link_indices[:]=0
    # Box top translates vertically only; its support trajectory keeps the
    # original horizontal motion even if a different surface was yaw-edited.
    rotations=np.broadcast_to(np.eye(3),(*c.contact_weights.shape,3,3))
    reference=p[:,0:1]+np.array([.2,.3,-.07])
    c.contact_targets_w=reference.copy()
    target,_,_=compile_support_motion(c,['left_ankle_roll_link','right_ankle_roll_link'],p,r,rotations,n,reference)
    np.testing.assert_allclose(target,reference)


def test_landing_anchor_is_not_changed_by_later_reference_offsets():
    c,p,r,n=fixture()
    targets,_,records=compile_support_motion(c,['left_ankle_roll_link','left_ankle_roll_sphere_1_link'],p,r,np.eye(3),n,origin_policy='landing')
    np.testing.assert_allclose(targets[:,0,0]-p[:,0,0],.1)
    assert records[0]['origin_policy']=='landing'
    c.contact_targets_w[2:,:,0]+=10.
    changed,_,_=compile_support_motion(c,['left_ankle_roll_link','left_ankle_roll_sphere_1_link'],p,r,np.eye(3),n,origin_policy='landing')
    np.testing.assert_allclose(changed,targets,atol=1.e-12)


def test_displacement_window_does_not_erase_source_contact_interval():
    from motion_edit.contact.schema import ContactAnchorRecord, ContactAnchorEditRecord
    from motion_edit.generation.support_motion import full_contact_episode_edits
    anchor=ContactAnchorRecord(motion_id='m',anchor_id='a',body='left_foot',start_frame=10,end_frame=30,world_position=[0.,0.,0.])
    edit=ContactAnchorEditRecord(motion_id='m',anchor_id='a',edit_id='e',body='left_foot',affected_frames=[15,20],delta_world=[.01,0.,0.])
    result=full_contact_episode_edits([edit],[anchor])
    assert result[0].affected_frames==[10,30]
    assert edit.affected_frames==[15,20]
    assert result[0].delta_world==edit.delta_world


def test_orientation_completion_only_for_degenerate_material_layouts():
    from motion_edit.generation.support_motion import orientation_completion_projectors
    c=SimpleNamespace(contact_link_indices=np.zeros((2,3),int),contact_points_local=np.array([
        [[0.,0.,0.],[.1,0.,0.],[0.,.1,0.]],
        [[0.,0.,0.],[.1,0.,0.],[.2,0.,0.]]]))
    p=np.zeros((2,1,3));r=np.broadcast_to(np.eye(3),(2,1,3,3))
    projectors=orientation_completion_projectors(c,['left_ankle_roll_link'],p,r,np.ones((2,3),bool))
    assert not projectors[0].any()
    assert not projectors[1].any()  # Preserve rolling about the contact line.
    yaw=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    rotated=orientation_completion_projectors(c,['left_ankle_roll_link'],p,
        np.broadcast_to(yaw,(2,1,3,3)),np.ones((2,3),bool))
    # Residual axes are link-local, so a world yaw cannot change this projector.
    np.testing.assert_allclose(rotated,projectors,atol=1.e-12)
    c.contact_points_local[:]=0.
    single=orientation_completion_projectors(c,['left_ankle_roll_link'],p,r,np.ones((2,3),bool))
    np.testing.assert_allclose(single,np.broadcast_to(np.eye(3),(2,3,3,3)))
