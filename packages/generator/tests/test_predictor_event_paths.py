import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from somaforge_core.support_semantics import assess_support

scripts = Path(__file__).resolve().parents[3] / 'scripts'
sys.path.insert(0,str(scripts))
spec = importlib.util.spec_from_file_location('predictor_event_paths',scripts/'prepare_predictor_event_paths.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def region(a,b,passed=True,required=False):
    return dict(start=a,end=b,passed=passed,required_keep=required)


def test_support_can_transfer_inside_event_without_new_event():
    assert module.contact_geometry_diagnostics([region(10,15),region(15,20)],10,20) == ([],[])


def test_optional_moving_region_does_not_invalidate_stationary_support():
    assert module.contact_geometry_diagnostics([region(10,20),region(10,20,False)],10,20) == ([],[])


def test_required_keep_cannot_be_replaced_by_other_support():
    reasons,missing = module.contact_geometry_diagnostics([region(10,20),region(10,20,False,True)],10,20)
    assert reasons == ['declared_keep_geometry_exceeds_budget_or_unknown']
    assert missing == []


def test_intermediate_hole_is_not_hidden_by_supported_endpoints():
    reasons,missing = module.contact_geometry_diagnostics([region(10,13),region(14,20)],10,20)
    assert reasons == ['incomplete_geometric_pivot_coverage']
    assert missing == [13]


def test_unknown_measurement_is_json_null():
    assert module.json_known(dict(step=[float('nan'),0.])) == dict(step=[None,0.])


def test_path_certificate_retains_unloaded_sample_without_new_implicit_rejection(tmp_path,monkeypatch):
    motion,labels,events,evidence = (tmp_path/name for name in ('motion.npz','labels.npz','events.jsonl','loads.npz'))
    np.savez(motion,joint_pos=np.zeros((3,36)))
    np.savez(labels,contact_semantics_json=np.asarray(json.dumps(dict(provenance=dict(newton_runtime='fixture')))))
    event = dict(id='transfer',start_frame=0,end_frame=2)
    events.write_text(json.dumps(event)+'\n')
    evidence.write_bytes(b'observation fixture')
    contact = np.zeros((3,6),bool); contact[:,0] = True
    force = np.zeros((3,6)); force[[0,2],0] = 100
    observations = assess_support(contact,force,np.zeros_like(force),load_known=np.ones_like(contact))
    monkeypatch.setattr(module,'load_contact_labels',lambda *args:dict(contact_part_mask=contact,contact_surface=np.zeros((3,6),int)))
    monkeypatch.setattr(module,'load_support_observations',lambda *args:observations)
    monkeypatch.setattr(module,'materialize_contract',lambda *args:dict(
        actions=[dict(id='transfer',start=0,end=2,requirements=[dict(kind='establish',part=0,surface=0)])],
        policy=dict(stable_frames=4),retained_blocks=[]))
    monkeypatch.setattr(module,'audit_events',lambda *args:(dict(checks=[dict(action='transfer',passed=True)]),None))
    monkeypatch.setattr(module,'analyze',lambda *args:dict(phases=[]))
    common = (motion,labels,motion,labels,events)
    baseline = module.prepare(*common,tmp_path/'without_observations')
    attached = module.prepare(*common,tmp_path/'with_observations',evidence)
    assert baseline['accepted_count'] == attached['accepted_count'] == 1
    assert attached['segments'][0]['observed_support']['unloaded_sample_frames'] == [1]
    assert attached['segments'][0]['observed_support']['load_coverage_passed'] is False
    certificate = json.loads((tmp_path/'with_observations/support_path_acceptance.json').read_text())
    assert certificate['segments'][0]['observed_support']['unloaded_sample_frames'] == [1]
    required = module.prepare(*common,tmp_path/'explicit_load_requirement',evidence,require_observed_load_coverage=True)
    assert required['accepted_count'] == 0
    assert required['segments'][0]['reasons'] == ['required_observed_load_coverage_failure_or_unknown']


def test_explicit_load_coverage_requirement_rejects_unknown_evidence():
    assert module.observed_load_acceptance_reasons(dict(load_coverage_passed=None),required=True)
    assert module.observed_load_acceptance_reasons(dict(load_coverage_passed=True),required=True) == []
