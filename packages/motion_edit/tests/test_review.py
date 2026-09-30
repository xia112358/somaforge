"""Read-only reviews must not create contacts or accept a different robot."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from somaforge_core.robot_assets import canonical_g1_urdf_path, encode_robot_asset_json
from motion_edit.web.review import load_review
from motion_edit.web.server import create_app


def report():
    names = [j.attrib['name'] for j in ET.parse(canonical_g1_urdf_path()).getroot().findall('joint')
             if j.attrib['type'] != 'fixed']
    q = [0., 0., 1., 1., 0., 0., 0.] + [0.] * len(names)
    return dict(robot_asset_json=encode_robot_asset_json(), joint_names=names,
                records=[dict(label='original', q=q), dict(label='method_step10', q=q),
                         dict(label='method_final', q=q)])


def test_report_unknown_contacts_and_readonly(tmp_path):
    path = tmp_path / 'report.json'
    data = report(); data['records'][0]['actual_contact'] = [True] * 6
    path.write_text(json.dumps(data))
    with TestClient(create_app(review_path=str(path))) as client:
        payload = client.get('/api/session').json()
        assert payload['capabilities'] == dict(playback=True, edit_contacts=False, generate=False)
        assert payload['contact_force']['masks'] == []
        assert '历史诊断' in payload['review']['notice']
        assert payload['review']['records'][1]['method'] == 'method'
        assert client.post('/api/session/move', json={'anchor_id':'x'}).status_code == 409
        assert client.post('/api/session/generate', json={}).status_code == 409
        assert client.get('/api/session').json() == payload


@pytest.mark.parametrize('fault', ['fingerprint', 'quaternion', 'duplicate', 'joint', 'normal'])
def test_invalid_report_rejected(tmp_path, fault):
    data = report()
    if fault == 'fingerprint': data.pop('robot_asset_json')
    if fault == 'quaternion': data['records'][0]['q'][3] = 0
    if fault == 'duplicate': data['records'][1]['label'] = 'original'
    if fault == 'joint': data['joint_names'][0] = 'wrong_joint'
    if fault == 'normal': data['records'][0]['penetrating_pairs'] = {'geometry_point1_w': [[0,0,0]], 'normal_w': []}
    path = tmp_path / 'report.json'; path.write_text(json.dumps(data))
    with pytest.raises(ValueError): load_review(path, url=str)


def test_motion_is_not_relabelled(tmp_path):
    data = report(); path = tmp_path / 'motion.npz'
    np.savez(path, qpos=[data['records'][0]['q']], joint_names=data['joint_names'],
             robot_asset_json=data['robot_asset_json'], fps=30, contact_force_part_mask=[[True]*6])
    payload = load_review(path, url=str)
    assert payload['fps'] == 30 and len(payload['qpos']) == 1
    assert payload['contact_force']['masks'] == []
    assert '未知' in payload['review']['notice']


def test_support_motion_review_uses_playback_and_rejects_invalid_tracks(tmp_path):
    data = report()
    motion = tmp_path / 'motion.npz'
    np.savez(motion, qpos=[data['records'][0]['q']] * 3,
             joint_names=data['joint_names'], robot_asset_json=data['robot_asset_json'], fps=50)
    review = tmp_path / 'support.json'
    phase = dict(start=0, end=2, part='left_foot',
                 aggregate=[[0, 0, 0], [0.01, 0, 0], [0.02, 0, 0]],
                 rollouts=[[[0, 0, 0], [0, 0, 0], [0.01, 0, 0]]],
                 aggregate_net_cm=2, rollout_median_net_cm=1)
    review.write_text(json.dumps(dict(kind='support_motion', motion='motion.npz', phases=[phase])))
    payload = load_review(review, url=str)
    assert payload['review']['kind'] == 'support_motion'
    assert payload['contact_force']['masks'] == []
    assert len(payload['qpos']) == 3
    phase['rollouts'][0].pop()
    review.write_text(json.dumps(dict(kind='support_motion', motion='motion.npz', phases=[phase])))
    with pytest.raises(ValueError, match='finite XYZ'):
        load_review(review, url=str)


def test_support_slip_review_draws_actual_same_material_displacements(tmp_path,monkeypatch):
    from somaforge_core import newton_contact_data
    verified=[]
    monkeypatch.setattr(newton_contact_data,'load_raw_contact_labels',lambda motion,labels:verified.append((motion,labels)))
    data=report();motion=tmp_path/'motion.npz';contacts=tmp_path/'contacts.npz'
    np.savez(motion,qpos=[data['records'][0]['q']]*3,joint_names=data['joint_names'],
        robot_asset_json=data['robot_asset_json'],fps=50,newton_direct_fk_metadata_json=np.asarray('{}'),
        body_names=np.asarray(['left_ankle_roll_link']),body_pos_w=np.array([[[0,0,0]],[[.01,0,0]],[[.02,0,0]]]),
        body_quat_w=np.array([[[1,0,0,0]]]*3))
    # Witness selection moves a metre; each actual material point only moves a cm.
    pairs=[[dict(part=0,surface=0,body_name='left_ankle_roll_link',allocated=True,dist=0.,
                 includemargin=.01,position_w=[float(t),0,0],normal_w=[0,0,1])] for t in range(3)]
    np.savez(contacts,contact_pairs_json=np.asarray(json.dumps(pairs)),
        contact_semantics_json=np.asarray(json.dumps({'scene':{'surface_catalog':[{'surface':0,'normal_w':[0,0,1]}]}})))
    review=tmp_path/'slip.json';review.write_text(json.dumps(dict(kind='support_slip',motion='motion.npz',contacts='contacts.npz')))
    payload=load_review(review,url=str)
    assert verified==[(motion.resolve(),contacts.resolve())]
    frames=payload['review']['slip_frames'];assert frames[-1]==[]
    assert frames[0][0]['motion_cm']==pytest.approx(1.)
    assert frames[1][0]['motion_cm']==pytest.approx(1.)
    assert payload['contact_force']['masks']==[]
    assert '承重滑移未知' in payload['review']['notice']
    from somaforge_core import support_evidence
    from somaforge_core.support_semantics import assess_support
    contact=np.zeros((3,6),bool);contact[:,0]=True
    force=np.zeros((3,6));force[:,0]=[100,0,150]
    observed=assess_support(contact,force,np.full((3,6),.01),load_known=np.ones((3,6),bool))
    monkeypatch.setattr(support_evidence,'load_support_observations',lambda motion,evidence:observed)
    review.write_text(json.dumps(dict(kind='support_slip',motion='motion.npz',contacts='contacts.npz',
                                      support_observations='observations.npz')))
    measured=load_review(review,url=str)['review']
    assert measured['support_frames'][0][0]['load_state']=='load_bearing'
    assert measured['support_frames'][1][0]['load_state']=='unloaded'
    assert measured['support_frames'][1][0]['loaded_speed_cm_s'] is None
    assert measured['actual_support_status']=='observed_original_solve_samples'
