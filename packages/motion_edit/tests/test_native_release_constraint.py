import numpy as np
import pytest
from motion_edit.generation import native_release_constraint as module


def test_native_contact_is_never_accepted_as_tolerable_residual(monkeypatch):
    pair=dict(part=2,robot_shape=94,surface=1,allocated=True,
              dist=.02-1.e-12,includemargin=.02,position_w=[0,0,1])
    monkeypatch.setattr(module,'query_contacts',lambda q:dict(
        provenance={'model_fingerprint':'test'},pairs=[[pair]],candidate_pairs=[[pair]],surface_catalog=[dict(surface=1,normal_w=[0,0,1])]))
    monkeypatch.setattr(module,'select_contact_pairs',lambda pairs,catalog:dict(contact_pairs=pairs))
    constraint=module.NativeReleaseConstraint(np.zeros(6,bool),'test',lambda x:np.zeros(36),lambda *a:None)
    assert constraint.fun(np.zeros(1))[2]<-1.e-8
    assert not constraint.feasible(np.zeros(1))


def test_missing_scene_fails_closed(monkeypatch):
    monkeypatch.setattr(module,'query_contacts',lambda q:dict(provenance={'model_fingerprint':'wrong'}))
    constraint=module.NativeReleaseConstraint(np.zeros(6,bool),'test',lambda x:np.zeros(36),lambda *a:None)
    with pytest.raises(ValueError,match='different native model'):constraint.fun(np.zeros(1))


def test_every_new_candidate_rechecks_shapes_without_cached_witnesses(monkeypatch):
    calls=[]
    def query(q):
        calls.append(q[0,0])
        pairs=[] if q[0,0]>0 else [dict(part=2,robot_shape=123,surface=1,
            allocated=True,dist=.01,includemargin=.02,position_w=[0,0,1])]
        return dict(provenance={'model_fingerprint':'test'},pairs=[pairs],candidate_pairs=[pairs],surface_catalog=[dict(surface=1,normal_w=[0,0,1])])
    monkeypatch.setattr(module,'query_contacts',query)
    monkeypatch.setattr(module,'select_contact_pairs',lambda pairs,catalog:dict(contact_pairs=pairs))
    constraint=module.NativeReleaseConstraint(np.zeros(6,bool),'test',
        lambda x:np.r_[x[0],np.zeros(35)],lambda *a:None)
    assert constraint.feasible(np.array([1.]))
    assert constraint.feasible(np.array([1.]))
    assert not constraint.feasible(np.array([-1.]))
    assert calls==[1.,-1.]


def test_unknown_face_trial_is_rejected_not_relabeled(monkeypatch):
    def query(q):raise RuntimeError('ValueError: Actual contact face absent: diagnostic')
    monkeypatch.setattr(module,'query_contacts',query)
    constraint=module.NativeReleaseConstraint(np.zeros(6,bool),'test',lambda x:np.zeros(36),lambda *a:None)
    assert not constraint.feasible(np.zeros(1))
    assert constraint.invalid_candidates==1
    assert (constraint.fun(np.zeros(1))<0).all()
