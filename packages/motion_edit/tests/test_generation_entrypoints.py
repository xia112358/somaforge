import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from motion_edit import cli
from motion_edit.contact.plans import ContactEditPlan


@pytest.mark.parametrize('command', ['generate-augmentations', 'generate-lte-augmentation',
                                     'batch-generate-lte-augmentations'])
def test_retired_commands_are_not_registered(command):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([command])


@pytest.mark.parametrize('batch', [False, True])
def test_single_and_batch_use_contact_aware_backend(tmp_path, batch):
    plan = ContactEditPlan(plan_id='candidate', source_motion_path='source.npz',
        source_motion_id='source', source_contact_layer='contacts', status='validated',
        metadata={'augmentation_objective': 'consolidated_v1', 'free_surface_contacts': True})
    prefix = None
    if batch:
        import numpy as np
        from motion_edit.generation.source_prefix_reference import SCHEMA
        source=tmp_path/'source.npz';q=np.zeros((20,36));q[:,3]=1.
        np.savez(source,joint_pos=q)
        surface=dict(surface_id='ground',origin=[0.,0.,0.],tangent_u=[1.,0.,0.],tangent_v=[0.,1.,0.],normal=[0.,0.,1.])
        prefix=dict(schema=SCHEMA,hold_frames=5,transition_end_frame=12,
                    surface_transform_id='start',joint_prior_scale=100.,semantic_weight=10000.)
        plan=replace(plan,source_motion_path=str(source),
            surface_transforms=[dict(transform_id='start',kind='surface_follow',
                translation_world=[0.,0.,0.],source_surface=surface,target_surface=surface)],
            metadata=dict(plan.metadata,source_prefix_reference=prefix))
    path = tmp_path/'plan.json';path.write_text(json.dumps(plan.to_dict()))
    output = tmp_path/'candidate.npz'
    args = ['generate-ref']
    if batch:
        manifest = tmp_path/'batch.json'
        manifest.write_text(json.dumps({'plans': [{'plan_path': 'plan.json'}]}))
        args += ['--plan-manifest', str(manifest), '--output-motion-dir', str(tmp_path)]
    else:
        args += ['--plan', str(path), '--output-motion', str(output)]
    args += ['--ik-q-acceleration-weight', '8', '--ik-script', str(tmp_path/'experimental_ik.py')]
    result = SimpleNamespace(output_motion_path=output, taskspace_spec_path=tmp_path/'task.npz',
        ik_output_path=tmp_path/'ik.npz', diagnostics={'augmentation_objective':'consolidated_v1', 'free_surface_contacts':True,
            'source_prefix_reference':prefix,'root_yaw_condition':dict(reference_delta_degrees=0.),'root_yaw_optimized':True})
    with patch('motion_edit.generation.generate_contact_aware_pyroki_preview', return_value=result) as generate:
        parsed=cli.build_parser().parse_args(args);parsed.func(parsed)
    assert generate.call_count == 1
    assert generate.call_args.kwargs['ik_q_acceleration_weight'] == 8
    assert generate.call_args.kwargs['ik_script'] == tmp_path/'experimental_ik.py'
    if batch:
        assert generate.call_args.args[0].metadata['source_prefix_reference']==prefix
    else:
        assert generate.call_args.args[0] == path.resolve()
    receipt=json.loads(output.with_suffix('.generation.json').read_text())
    assert receipt['status']=='requires_native_validation'
    assert receipt['training_ready'] is False
    import hashlib
    assert hashlib.sha256(Path(receipt['plan']).read_bytes()).hexdigest() == receipt['plan_sha256']


def test_retired_python_entrypoints_are_absent():
    import importlib.util
    import motion_edit.generation as generation
    from motion_edit.generation import lte_fullbody
    assert not hasattr(generation, 'apply_contact_aware_edit_plan_to_motion')
    assert not hasattr(generation, 'ContactAwareGenerationResult')
    assert not hasattr(generation, 'apply_contact_edit_plan_to_motion')
    assert not hasattr(lte_fullbody, 'apply_contact_edit_plan_to_motion')
    for module in ('motion_edit.contact.generation', 'motion_edit.generation.diagnostics',
                   'motion_edit.generation.contact_aware_cli', 'motion_edit.augmentation'):
        assert importlib.util.find_spec(module) is None


@pytest.mark.parametrize('metadata', [{}, {'augmentation_objective': 'legacy'},
    {'augmentation_objective': 'consolidated_v1'},
    {'augmentation_objective': 'consolidated_v1', 'free_surface_contacts': False}])
def test_backend_rejects_old_plan_before_reading_source(tmp_path, metadata):
    import motion_edit.generation as generation
    plan = ContactEditPlan(plan_id='old', source_motion_path='does-not-exist.npz',
        source_motion_id='old', source_contact_layer='old', status='validated', metadata=metadata)
    with pytest.raises(ValueError, match='Generation requires'):
        generation.generate_contact_aware_pyroki_preview(plan, output_motion_path=tmp_path/'out.npz')
    assert not (tmp_path/'out.npz').exists()


def test_ik_rejects_legacy_keypoints():
    from motion_edit.generation.trajectory_problem import _input_problem
    with pytest.raises(ValueError, match='Legacy LTE keypoints'):
        _input_problem({}, link_names=(), actuated_count=0, robot_joint_names=(),
                       source_motion_path=None, edited_contact_weight=1, fixed_contact_weight=1)


def test_robot_mapping_does_not_guess_from_substrings():
    from motion_edit.generation.taskspace_kinematics import resolve_link_index
    assert resolve_link_index(('left_ankle_roll_link',), 'left_ankle_roll', ()) is None
    assert resolve_link_index(('left_ankle_roll_link',), '/Robot/left_ankle_roll_link', ()) == 0


def test_source_without_robot_asset_is_rejected(tmp_path):
    from motion_edit.generation.rollout_authority import _load_source_motion
    source = tmp_path/'source.npz'
    source.touch()
    plan = SimpleNamespace(source_motion_path=str(source), metadata={})
    with pytest.raises(ValueError, match='robot asset'):
        _load_source_motion(plan, SimpleNamespace(_load_motion_npz=lambda path: {}))
