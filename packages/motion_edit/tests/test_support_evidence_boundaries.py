"""Keep edit intentions while preventing inherited execution truth at boundaries."""
import json
import hashlib

import numpy as np
import pytest

from motion_edit.adapters.holosoma_npz import subset_arrays
from motion_edit.editing.splice import splice_motions
from somaforge_core.support_evidence import reference_only_support


def test_archived_optimization_reference_preserves_provenance_and_content_binding(tmp_path):
    from motion_edit.generation.loaded_material_reference import _archived_reference_masks
    from somaforge_core.robot_assets import canonical_g1_source_metadata
    from somaforge_core.support_evidence import load_support_observations
    from somaforge_core.support_semantics import SUPPORT_ASSESSMENT_SCHEMA
    motion, recording, evidence = (tmp_path/name for name in ('motion.npz', 'recording.npz', 'evidence.npz'))
    motion.write_bytes(b'content-bound reference pose')
    recording.write_bytes(b'original archived execution')
    meta = dict(schema=SUPPORT_ASSESSMENT_SCHEMA, status='observed',
        motion_sha256=hashlib.sha256(motion.read_bytes()).hexdigest(),
        recording=dict(path=str(recording), sha256=hashlib.sha256(recording.read_bytes()).hexdigest()),
        robot_asset=canonical_g1_source_metadata(), newton_runtime=dict(runtime_id='archived_test_fixture'),
        scene_fingerprint='archived_test_scene', sampling=dict(clock='original same solve'))
    # Mathematical fixture, never written as a production evidence artifact.
    np.savez(evidence, support_assessment_json=np.array(json.dumps(meta)),
        contact_activated=np.ones((2, 6), bool), normal_force_n=np.ones((2, 6)),
        rms_tangent_speed_m_s=np.zeros((2, 6)), load_known=np.ones((2, 6), bool))
    with pytest.raises(ValueError):
        load_support_observations(motion, evidence)
    result = _archived_reference_masks(motion, evidence)
    assert result['provenance'] == meta
    assert result['load_bearing'].all()
    assert 'contact_activated' not in result
    recording.write_bytes(b'changed recording')
    with pytest.raises(ValueError, match='Stale original reference recording'):
        _archived_reference_masks(motion, evidence)
    motion.write_bytes(b'changed trajectory')
    with pytest.raises(ValueError, match='does not belong'):
        _archived_reference_masks(motion, evidence)


def test_crop_preserves_native_pose_and_intent_but_requires_rebinding():
    q = np.arange(4*36).reshape(4,36)
    intent = np.zeros((4,6),bool); intent[1:3,0] = True
    observed = np.ones((4,6),bool)
    source = dict(joint_pos=q,contact_keep_intent_mask=intent,
                  observed_support_load_bearing=observed,
                  support_assessment_json=np.asarray(json.dumps(dict(status='observed'))))
    cropped = subset_arrays(source,1,3)
    np.testing.assert_array_equal(cropped['joint_pos'],q[1:3])
    np.testing.assert_array_equal(cropped['contact_keep_intent_mask'],intent[1:3])
    np.testing.assert_array_equal(cropped['source_reference_observed_support_load_bearing'],observed[1:3])
    assert 'observed_support_load_bearing' not in cropped
    assert json.loads(cropped['support_assessment_json'].item())['status'] == 'unknown'
    assert json.loads(source['support_assessment_json'].item())['status'] == 'observed'
    assert 'source_reference_observed_support_load_bearing' not in source


def test_splice_converts_legacy_roles_and_preserves_new_intent(tmp_path):
    a,b,out = (tmp_path/name for name in ('a.npz','b.npz','combined.npz'))
    keep_a = np.zeros((2,6),bool); keep_a[:,0] = True
    keep_b = np.zeros((3,6),bool); keep_b[:,1] = True
    np.savez(a,joint_pos=np.zeros((2,36)),support_part_mask=keep_a,
             observed_support_load_bearing=keep_a)
    np.savez(b,joint_pos=np.ones((3,36)),contact_keep_intent_mask=keep_b,
             observed_support_load_bearing=keep_b)
    original_a,original_b = a.read_bytes(),b.read_bytes()
    splice_motions([a,b],out)
    with np.load(out,allow_pickle=False) as z:
        np.testing.assert_array_equal(z['contact_keep_intent_mask'],np.concatenate([keep_a,keep_b]))
        np.testing.assert_array_equal(z['joint_pos'],np.concatenate([np.zeros((2,36)),np.ones((3,36))]))
        assert 'observed_support_load_bearing' not in z
        assert json.loads(z['support_assessment_json'].item())['status'] == 'unknown'
    assert a.read_bytes() == original_a and b.read_bytes() == original_b


def test_repeated_edit_does_not_overwrite_original_force_provenance():
    original_provenance = np.asarray(json.dumps(dict(source='original_native_solve')))
    payload = dict(contact_force_part_w=np.ones((2,6,3)),
                   contact_force_provenance_json=original_provenance,
                   contact_keep_intent_mask=np.ones((2,6),bool),
                   support_assessment_json=np.asarray(json.dumps(dict(status='observed'))))
    reference_only_support(payload,reason='first edit',retain_force_targets=True)
    reference_only_support(payload,reason='second edit',retain_force_targets=True)
    assert payload['source_reference_contact_force_provenance_json'].item() == original_provenance.item()
    assert json.loads(payload['source_reference_support_assessment_json'].item())['status'] == 'observed'
    assert json.loads(payload['support_assessment_json'].item())['status'] == 'unknown'
    assert payload['contact_keep_intent_mask'].all()
