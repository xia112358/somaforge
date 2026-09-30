import json
from pathlib import Path

import pytest
from generator.support_path_acceptance import SCHEMA, file_evidence, validate_support_paths


def fixture(tmp_path):
    motion = tmp_path / 'motion.npz'; motion.write_bytes(b'canonical motion')
    labels = tmp_path / 'labels.npz'; labels.write_bytes(b'actual Newton evidence')
    events = tmp_path / 'events.jsonl'
    events.write_text(json.dumps(dict(start_frame=10,end_frame=20))+'\n')
    certificate = tmp_path / 'certificate.json'
    certificate.write_text(json.dumps(dict(schema=SCHEMA,
        support_assessment_schema='newton_contact_load_slip_assessment_v1',
        evidence=dict(motion=file_evidence(motion),labels=file_evidence(labels)),
        segments=[dict(start_frame=10,end_frame=20,accepted=True),
                  dict(start_frame=20,end_frame=30,accepted=False)])))
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps(dict(support_path_acceptance=[dict(file_evidence(certificate),motion_id=0)],
        motion_files=[dict(motion_file=str(motion),newton_contact_file=str(labels),
                           event_segments_file=str(events),event_segments_sha256=file_evidence(events)['sha256'])])))
    return manifest, motion, labels


def sample(a=10,b=20):
    return dict(motion_id=0,current_frame=a,target_frame=b)


def test_accepted_exact_event_path(tmp_path):
    manifest,_,_ = fixture(tmp_path)
    assert validate_support_paths(manifest,[sample()])['status'] == 'verified_reference_contact_paths'


@pytest.mark.parametrize('a,b',[(10,30),(20,30),(11,20),(0,10)])
def test_rejected_or_bridged_or_stale_frame_samples(tmp_path,a,b):
    manifest,_,_ = fixture(tmp_path)
    with pytest.raises(ValueError,match='lacks accepted whole-path'):
        validate_support_paths(manifest,[sample(a,b)])


def test_modified_actual_contact_evidence_is_rejected(tmp_path):
    manifest,_,labels = fixture(tmp_path)
    labels.write_bytes(b'changed contact truth')
    with pytest.raises(ValueError,match='Stale support-path evidence'):
        validate_support_paths(manifest,[sample()])


def test_certificate_cannot_be_reused_for_other_motion(tmp_path):
    manifest,_,_ = fixture(tmp_path)
    other = tmp_path / 'other.npz'; other.write_bytes(b'other motion')
    data = json.loads(manifest.read_text()); data['motion_files'][0]['motion_file'] = str(other)
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='does not belong'):
        validate_support_paths(manifest,[sample()])


def test_legacy_is_explicitly_unchecked(tmp_path):
    manifest = tmp_path/'manifest.json'; manifest.write_text('{}')
    assert validate_support_paths(manifest,[sample()])['status'] == 'legacy_unchecked'


def test_empty_declaration_cannot_disable_checks(tmp_path):
    manifest = tmp_path/'manifest.json'; manifest.write_text('{"support_path_acceptance":[]}')
    with pytest.raises(ValueError,match='Empty support-path'):
        validate_support_paths(manifest,[sample()])
