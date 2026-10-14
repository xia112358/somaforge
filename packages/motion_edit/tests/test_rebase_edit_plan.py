import numpy as np
import pytest

from motion_edit.generation.rebase_edit_plan import crop_events,event_clock,rebase_plan
from motion_edit.generation.loaded_material_reference import compare_paths


def test_event_rebind_keeps_authored_offsets_when_shape_fragments_change(tmp_path):
    source=tmp_path/'source.npz';source.write_bytes(b'unchanged source')
    old=[dict(segment_id='a',start_frame=0,end_frame=4)]
    new=[dict(segment_id='a',start_frame=0,end_frame=3)]
    plan=dict(plan_id='edit',source_motion_path='old.npz',pose_edits=[],edits=[],
        metadata=dict(free_surface_reference_offsets={'old_heel':dict(base=[.02,0,0],windows=[])},
            approach_frames=15, support_approach_seconds=.3, support_approach_orientation=True))
    anchors=[dict(anchor_id='old_heel',body='left_heel',surface_id='top',start_frame=0,end_frame=5)]
    fragments=[dict(anchor_id='new1',body='left_heel',surface_id='top',start_frame=0,end_frame=2),
               dict(anchor_id='new2',body='left_heel',surface_id='top',start_frame=2,end_frame=4)]
    result=rebase_plan(plan,anchors,fragments,old,new,source=source,layer=tmp_path,
        labels=tmp_path/'labels.npz',events=tmp_path/'events.jsonl',initial_q=np.zeros(36))
    offsets=result['metadata']['free_surface_reference_offsets']
    assert set(offsets)=={'new1','new2'}
    assert offsets['new2']['windows']==[dict(frames=[2,4],delta=[.02,0.,0.])]
    assert result['metadata']['rebase_provenance']['source_pose_warped'] is False
    assert not {'approach_frames', 'support_approach_seconds', 'support_approach_orientation'} & result['metadata'].keys()
    assert plan['metadata']['support_approach_seconds'] == .3
    assert source.read_bytes()==b'unchanged source'


def test_crop_keeps_independent_blocks_and_rejects_cross_seam_supervision():
    frames=np.r_[np.arange(4),np.arange(8,12)]
    event=dict(segment_id='after',start_frame=8,end_frame=11,
               touchdown_events=[dict(frame=11,release_frame=9,previous_contact_frame=7,part_index=0)])
    new=crop_events([event],frames)[0]
    assert (new['start_frame'],new['end_frame'])==(4,7)
    assert new['touchdown_events'][0]['frame']==7
    assert new['touchdown_events'][0]['release_frame']==5
    assert new['touchdown_events'][0]['previous_contact_frame'] is None
    assert new['touchdown_events'][0]['source_timing']['previous_contact_frame']==7
    assert not new['cross_seam_supervision_allowed']
    assert event['start_frame']==8
    with pytest.raises(ValueError,match='crosses'):
        crop_events([dict(start_frame=3,end_frame=8)],frames)


def test_ambiguous_event_correspondence_is_rejected():
    old=[dict(segment_id='a',start_frame=0,end_frame=4),dict(segment_id='b',start_frame=5,end_frame=8)]
    new=[dict(segment_id='a',start_frame=0,end_frame=3),dict(segment_id='b',start_frame=3,end_frame=7)]
    with pytest.raises(ValueError,match='Ambiguous'):event_clock(old,new,8)


def test_unloaded_source_frames_never_become_static_support_targets():
    source=np.full((3,6),np.nan);source[:,0]=[.01,np.nan,.02]
    edited=source.copy();edited[0,0]=.011
    report=compare_paths(source,edited,[dict(start=0,end=3,part=0,surface=0)],
        load_known=np.ones_like(source,bool),load_bearing=np.isfinite(source))[0]
    assert report['source_loaded_steps']==2
    assert report['source_without_loaded_site_frames']==[1]
    assert report['actual_edited_support']=='unknown_without_new_execution'
    assert report['source_path_cm']==pytest.approx(3.)
    assert report['edited_budget']['within_budget'] is True


def test_crop_differentiation_never_uses_the_removed_transition(tmp_path):
    from motion_edit.generation.regenerate_edits import seal_clip_velocities
    path=tmp_path/'cropped.npz';q=np.zeros((4,36));q[:,3]=1;q[2:,:3]=1
    np.savez(path,fps=50.,joint_pos=q,body_pos_w=q[:,:3,None].transpose(0,2,1),
             body_quat_w=q[:,3:7,None].transpose(0,2,1))
    seal_clip_velocities(path,dict(continuous_clip_ranges=[[0,2],[2,4]]))
    with np.load(path) as z:
        assert not z['joint_vel'].any()
        assert not z['body_lin_vel_w'].any()
        np.testing.assert_array_equal(z['joint_pos'],q)


def test_original_loaded_sites_preserve_stationary_pivot_rotation_and_no_cancellation(tmp_path):
    from motion_edit.generation.loaded_material_reference import material_steps
    from scipy.spatial.transform import Rotation
    path=tmp_path/'pose.npz'
    quaternion=Rotation.from_euler('z',np.array([[0.],[90.]]),degrees=True).as_quat()[:,[3,0,1,2]]
    np.savez(path,body_names=['foot'],body_pos_w=np.zeros((2,1,3)),body_quat_w=quaternion[:,None,:])
    sites=dict(frame=np.array([0]),part=np.array([0]),surface=np.array([0]),body=np.array(['foot']),
               local=np.zeros((1,3)),normal=np.array([[0.,0.,1.]]),weight=np.array([1.]))
    assert material_steps(path,sites,2)[0,0]==pytest.approx(0.)
    sites={k:np.repeat(v,2,axis=0) for k,v in sites.items()}
    sites['local']=np.array([[1.,0.,0.],[-1.,0.,0.]])
    measured=material_steps(path,sites,2)
    assert measured[0,0]==pytest.approx(np.sqrt(2.))
    assert np.isnan(measured[0,1:]).all()
    sites['surface']=np.array([0,1])
    with pytest.raises(ValueError,match='different terrain surfaces'):
        material_steps(path,sites,2)


def test_source_load_sites_are_rebound_and_deleted_span_seam_remains_unknown():
    from motion_edit.generation.loaded_material_reference import remap_reference_sites
    from somaforge_core.loaded_material_motion import material_path_report
    sites=dict(frame=np.arange(5),part=np.zeros(5,int),surface=np.zeros(5,int),
        body=np.array(['foot']*5),local=np.zeros((5,3)),normal=np.tile([0.,0.,1.],(5,1)),weight=np.ones(5))
    known=np.ones((5,6),bool);bearing=np.zeros_like(known);bearing[:,0]=True
    rebound,k,b=remap_reference_sites(sites,[0,1,4,5],load_known=known,load_bearing=bearing)
    np.testing.assert_array_equal(rebound['frame'],[0,2])
    assert not k[1].any() and not b[1].any()
    steps=np.full((3,6),np.nan);steps[[0,2],0]=.01
    report=material_path_report(steps,[dict(start=0,end=3,part=0)],load_known=k,load_bearing=b)
    assert report['within_budget'] is None
    assert report['phases'][0]['unknown_intervals']==1


def test_native_binding_export_and_relabel_share_only_identical_inspection(tmp_path):
    from serve_newton_contact_queries import write_verified_inspection
    path=tmp_path/'model.json';info=dict(model_fingerprint='same',shape_body=[0,-1])
    write_verified_inspection(path,info);original=path.read_bytes()
    write_verified_inspection(path,info)
    assert path.read_bytes()==original
    with pytest.raises(ValueError,match='different'):
        write_verified_inspection(path,dict(model_fingerprint='changed',shape_body=[0,-1]))
    assert path.read_bytes()==original


def test_cache_monitor_never_observes_partial_status(tmp_path):
    import json
    import threading
    from motion_edit.generation.regenerate_edits import dump
    path=tmp_path/'status.json';dump(path,dict(stage='editing',items=[]))
    stopped=threading.Event();failures=[];reads=[]
    def monitor():
        while not stopped.is_set():
            try:reads.append(json.loads(path.read_text())['stage'])
            except Exception as error:failures.append(error)
    reader=threading.Thread(target=monitor);reader.start()
    try:
        for index in range(20):dump(path,dict(stage='editing',items=[index]*5000))
    finally:
        stopped.set();reader.join(timeout=5)
    assert not reader.is_alive()
    assert reads and not failures
    assert not list(tmp_path.glob('*.writing'))


def test_crop_completion_cannot_borrow_stability_from_the_next_clip():
    from motion_edit.generation.regenerate_edits import cropped_event_contract
    from motion_edit.generation.event_acceptance import audit_events,build_contract
    mask=np.zeros((8,6),bool);mask[4:,0]=True
    surface=np.full((8,6),-1);surface[4:,0]=0
    events=[dict(segment_id=str(i),start_frame=a,end_frame=b,persistent_parts=[],
        source_surfaces=[-1]*6,target_surfaces=[0,-1,-1,-1,-1,-1],
        touchdown_events=[dict(part_index=0)],release_events=[]) for i,(a,b) in enumerate(((0,3),(4,7)))]
    naive=build_contract(mask,surface,events,50.)
    assert audit_events(naive,mask,surface)[0]['checks'][0]['passed']
    bounded=cropped_event_contract(dict(contact_part_mask=mask,contact_surface=surface),events,50.,[[0,4],[4,8]],
        source_policy=naive['policy'])
    checks=audit_events(bounded,mask,surface)[0]['checks']
    assert not checks[0]['passed'] and checks[1]['passed']


def test_crop_candidate_dropouts_cannot_increase_source_tolerance():
    from motion_edit.generation.regenerate_edits import cropped_event_contract
    from motion_edit.generation.event_acceptance import audit_events,build_contract
    source=np.zeros((12,6),bool);source[:,0]=True
    event=dict(segment_id='keep',start_frame=0,end_frame=11,persistent_parts=['left_foot'],
        source_surfaces=[0,-1,-1,-1,-1,-1],target_surfaces=[0,-1,-1,-1,-1,-1],touchdown_events=[])
    policy=build_contract(source,np.where(source,0,-1),[event],50.)['policy']
    candidate=source.copy();candidate[2:8,0]=False;surface=np.where(candidate,0,-1)
    naive=build_contract(candidate,surface,[event],50.)
    assert naive['policy']['max_dropout_frames']>policy['max_dropout_frames']
    assert audit_events(naive,candidate,surface)[0]['passed']
    bounded=cropped_event_contract(dict(contact_part_mask=candidate,contact_surface=surface),[event],50.,[[0,12]],source_policy=policy)
    assert bounded['policy']==policy
    assert not audit_events(bounded,candidate,surface)[0]['passed']
