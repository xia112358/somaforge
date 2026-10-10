import numpy as np
import pytest
import torch

from somaforge_core.loaded_material_motion import (
    loaded_material_steps, tangent_material_rms, phase_added_motion, source_motion_allowances)
from motion_edit.generation.loaded_material_reference import SequentialLoadedMotion
from motion_edit.generation.source_support import SourcePhaseMotion


class FK:
    def link_poses(self, q, names):
        angle = q[:, 3]; c, s = angle.cos(), angle.sin(); z = c*0; one = z+1
        rotation = torch.stack((c, -s, z, s, c, z, z, z, one), -1).reshape(-1, 1, 3, 3)
        return q[:, None, :3], rotation


def reference(q, *, local=None, frames=None):
    frames = np.arange(len(q)-1) if frames is None else np.asarray(frames)
    local = np.zeros((len(frames), 3)) if local is None else np.asarray(local)
    n = len(frames)
    sites = dict(frame=frames, part=np.zeros(n, int), surface=np.zeros(n, int),
        body=np.asarray(['foot']*n), local=local, normal=np.tile([0., 0., 1.], (n, 1)), weight=np.ones(n))
    pos, rot = FK().link_poses(q, ['foot'])
    steps = loaded_material_steps(pos, rot, frames=frames, links=np.zeros(n, int), parts=sites['part'],
        local=local, normals=sites['normal'], loads=sites['weight'], surfaces=sites['surface']).detach().numpy()
    known = np.ones_like(steps, bool); bearing = np.isfinite(steps)
    phases = [dict(event_id='keep', start=0, end=len(q)-1, part=0, surface=0)]
    calibration = source_motion_allowances(steps, phases, load_known=known, load_bearing=bearing)
    return dict(sites=sites, phases=phases, source_steps=steps,
                load_known=known, load_bearing=bearing, calibration=calibration)


def phase_loss(q, ref):
    contract = dict(actions=[dict(id='keep', start=0, end=len(q)-1,
        requirements=[dict(kind='keep', part=0, surface=0)])])
    return SourcePhaseMotion(FK(), q, ref, contract)


def test_original_movement_is_free_but_added_motion_has_recovery_gradient():
    q = torch.tensor([[0., 0., 0., 0.], [.01, 0., 0., 0.], [.02, 0., 0., 0.]], dtype=torch.double)
    loss = phase_loss(q, reference(q))
    original = q.clone().requires_grad_()
    loss(original).backward()
    assert loss(original) == 0 and not original.grad.any()
    candidate = q.clone(); candidate[1:, 0] += .2; candidate.requires_grad_()
    value = loss(candidate); value.backward()
    assert value > 0 and candidate.grad[1, 0] > 0 and torch.isfinite(candidate.grad).all()
    audit = loss.audit(candidate)
    assert audit['passed'] is False
    assert audit['phases'][0]['added_motion_cm'] == pytest.approx(20.)


def test_motion_reduction_at_another_interval_cannot_pay_for_added_slip():
    original = torch.tensor([[0., 0, 0, 0], [.1, 0, 0, 0], [.2, 0, 0, 0]], dtype=torch.double)
    loss = phase_loss(original, reference(original))
    candidate = original.clone(); candidate[1, 0] = .25; candidate[2, 0] = .25
    # Total path grew only 5 cm, but 15 cm was added at the first interval.
    assert loss.paths(candidate).item()-loss.source_paths().item() == pytest.approx(.05)
    assert loss(candidate) > 0 and loss.audit(candidate)['passed'] is False


def test_loaded_pivot_is_free_and_an_unloaded_changing_witness_is_not_pinned():
    angle = torch.tensor([0., .2, .4], dtype=torch.double)
    q = torch.stack((-angle.cos(), -angle.sin(), angle*0, angle), -1)
    ref = reference(q, local=[[1., 0, 0], [1., 0, 0]])
    loss = phase_loss(q, ref)
    assert loss.paths(q).item() < 1.e-12 and loss(q) == 0
    # The second interval is explicitly unloaded, not an artificial stationary target.
    ref['sites'] = {k: v[:1] for k, v in ref['sites'].items()}
    ref['source_steps'][1, 0] = np.nan; ref['load_bearing'][1, 0] = False
    free = phase_loss(q, ref)
    candidate = q.clone(); candidate[2, :3] += 5
    assert free(candidate) == 0 and free.audit(candidate)['passed'] is True
    ref['load_known'][1, 0] = False
    with pytest.raises(ValueError, match='allowance unknown'):
        phase_loss(q, ref)


def test_refinement_does_not_reintroduce_marker_penalty_for_a_stationary_loaded_pivot():
    from motion_edit.generation.native_contact_refinement import trajectory_support_regularizer
    source = torch.tensor([[-1., 0, 0, 0]]*3, dtype=torch.double)
    loss = phase_loss(source, reference(source, local=[[1., 0, 0]]*2))
    angle = torch.tensor([0., .2, .4], dtype=torch.double)
    candidate = torch.stack((-angle.cos(), -angle.sin(), angle*0, angle), -1).requires_grad_()
    offsets = source.new_tensor([[0,0,0],[.1,0,0],[0,.1,0],[0,0,.1]])
    def markers(q):
        p, r = FK().link_poses(q, ['foot'])
        return p[...,None,:]+torch.einsum('...ij,kj->...ki',r,offsets)
    points, original = markers(candidate), markers(source)
    persistent = torch.ones((2,1), dtype=torch.bool)
    # Rotation moves the endpoint origin and markers while its loaded point is fixed.
    old = trajectory_support_regularizer(candidate, points, original, persistent, .001)
    assert old > 0
    def forbidden_extra_prior(q):
        raise AssertionError('A loaded reference must bypass the old marker prior')
    value = trajectory_support_regularizer(candidate, points, original, persistent, .001,
        phase_motion_loss=loss, source_support=forbidden_extra_prior)
    assert value < 1.e-20
    assert torch.isfinite(torch.autograd.grad(value, candidate)[0]).all()
    moved = candidate.detach().clone(); moved[1:,0] += .02; moved.requires_grad_()
    value = trajectory_support_regularizer(moved, markers(moved), original, persistent, .001,
        phase_motion_loss=loss)
    assert value > 0 and torch.autograd.grad(value, moved)[0][1,0] > 0


def test_static_labels_cannot_replace_loaded_execution_reference():
    with pytest.raises(ValueError, match='not static labels'):
        SourcePhaseMotion(FK(), torch.zeros(2, 4), 'labels.npz', {})


def test_known_unloaded_phase_is_not_pinned_or_certified_as_physical_support():
    q = torch.zeros(2, 4, dtype=torch.double)
    ref = reference(q)
    ref['sites'] = {k: v[:0] for k,v in ref['sites'].items()}
    ref['source_steps'][:] = np.nan; ref['load_bearing'][:] = False
    loss = phase_loss(q, ref)
    moved = q.clone(); moved[1, 0] = 3.; moved.requires_grad_()
    loss(moved).backward()
    assert not moved.grad.any() and loss(moved) == 0
    row = loss.audit(moved)['phases'][0]
    assert row['reference_motion_status'] == 'known_unloaded_not_constrained'
    assert row['reference_motion_passed'] is None
    assert row['actual_edited_support'] == 'unknown_without_new_execution'


def test_dense_rms_matches_shared_material_steps_and_jax_gradients():
    jax = pytest.importorskip('jax'); import jax.numpy as jnp
    delta = np.asarray([[[0., 0, 0], [.02, 0, 0], [-.02, 0, 0]]], np.float32)
    normals = np.broadcast_to([0., 0, 1.], delta.shape).astype(np.float32)
    weights = np.asarray([[1., 2., 2.]], np.float32)
    expected = (.0004*4/5)**.5
    value = tangent_material_rms(torch.tensor(delta), torch.tensor(normals), torch.tensor(weights), xp=torch)
    assert value.item() == pytest.approx(expected)
    function = lambda x: tangent_material_rms(x, jnp.asarray(normals), jnp.asarray(weights), xp=jnp).sum()
    assert float(function(jnp.asarray(delta))) == pytest.approx(expected)
    assert np.isfinite(jax.grad(function)(jnp.zeros_like(jnp.asarray(delta)))).all()
    np.testing.assert_allclose(jax.grad(function)(jnp.asarray(delta)),
        torch.autograd.functional.jacobian(lambda x: tangent_material_rms(x,
            torch.tensor(normals), torch.tensor(weights), xp=torch).sum(), torch.tensor(delta)).numpy(), atol=1.e-6)


def test_sequential_objective_and_final_phase_audit_use_same_reference():
    q = torch.tensor([[0., 0, 0, 0], [.001, 0, 0, 0], [.002, 0, 0, 0]], dtype=torch.double)
    ref = reference(q); sequence = SequentialLoadedMotion(ref, ['foot'])
    candidate = q.clone(); candidate[1:, 0] += .01
    pos, rot = FK().link_poses(candidate, ['foot'])
    for frame in range(1, len(q)):
        args = sequence.frame_args(frame, pos[frame-1].numpy(), rot[frame-1].numpy(),
            np.zeros(3), np.eye(3))
        links, local, previous, normals, weights, source, remaining, scale = args
        current = pos[frame].numpy()[links]+np.einsum('...ij,...j->...i', rot[frame].numpy()[links], local)
        rms = tangent_material_rms(current-previous, normals, weights, xp=np)
        residual = np.stack((np.maximum(np.maximum(rms-source, 0)-remaining[0], 0),
                             np.maximum(rms-remaining[1], 0)))*scale
        assert residual[0,0] > 0  # source preservation is soft guidance
        assert residual[1,0] == 0  # below 6 cm, so the motion constraint passes
        sequence.commit(frame, pos[frame-1].numpy(), rot[frame-1].numpy(), pos[frame].numpy(), rot[frame].numpy())
    report = sequence.report(); full = phase_loss(q, ref).audit(candidate)
    assert report['phases'][0]['added_motion_cm'] == pytest.approx(full['phases'][0]['added_motion_cm'])
    assert report['phases'][0]['reference_motion_passed'] is False
    assert report['phases'][0]['motion_budget_passed'] is True
    assert full['passed'] is True
    assert report['actual_edited_support'] == 'unknown_without_new_execution'


def test_absolute_phase_budget_has_gradient_even_without_source_added_motion():
    q = torch.tensor([[0.,0,0,0],[.04,0,0,0],[.08,0,0,0]],dtype=torch.double)
    loss = phase_loss(q,reference(q))
    candidate=q.clone().requires_grad_()
    value=loss(candidate)
    gradient=torch.autograd.grad(value,candidate)[0]
    assert value > 0 and gradient[-1,0] > 0 and gradient[0,0] < 0
    audit=loss.audit(candidate)
    assert audit['phases'][0]['reference_motion_passed'] is True
    assert audit['passed'] is False


def test_sequential_budget_spends_actual_path_without_cross_interval_cancellation():
    q=torch.zeros(3,4,dtype=torch.double)
    sequence=SequentialLoadedMotion(reference(q),['foot'])
    candidate=q.clone();candidate[1,0]=.04;candidate[2,0]=.08
    pos,rot=FK().link_poses(candidate,['foot'])
    for frame in (1,2):
        args=sequence.frame_args(frame,pos[frame-1].numpy(),rot[frame-1].numpy(),np.zeros(3),np.eye(3))
        remaining=args[-2]
        assert remaining[1,0] == pytest.approx(.06 if frame==1 else .02)
        sequence.commit(frame,pos[frame-1].numpy(),rot[frame-1].numpy(),pos[frame].numpy(),rot[frame].numpy())
    assert sequence.report()['phases'][0]['motion_budget_passed'] is False


def test_resume_rejects_old_objective_or_changed_evidence_and_scale(tmp_path):
    import hashlib
    from motion_edit.generation.regenerate_edits import GENERATION_SCHEMA, validate_completed_generation, generation_objective
    paths = {key: tmp_path/key for key in ('sites', 'observations', 'phases', 'plan', 'motion', 'labels', 'events', 'contract')}
    for key, path in paths.items():
        path.write_text(key)
    digests = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}
    objective = generation_objective(.01, .01, 4)
    record = dict(schema=GENERATION_SCHEMA, plan_sha256=digests['plan'],
        requested_objective=objective, effective_objective=objective, loaded_reference=dict(
        **{key: str(paths[key]) for key in ('sites', 'observations', 'phases')},
        sha256={key: digests[key] for key in ('sites', 'observations', 'phases')}, residual_scale_m=.01),
        event_reference=dict(**{key:str(paths[key]) for key in ('motion','labels','events','contract')},
            sha256={key:digests[key] for key in ('motion','labels','events','contract')}))
    validate_completed_generation(record, paths['plan'], .01)
    with pytest.raises(ValueError, match='predates'):
        validate_completed_generation(dict(record, schema='native_execution_edit_collection_v1'), paths['plan'], .01)
    with pytest.raises(ValueError, match='predates'):
        validate_completed_generation(dict(record, schema='native_observed_source_loaded_material_budget_edit_v6'), paths['plan'], .01)
    with pytest.raises(ValueError, match='predates'):
        validate_completed_generation(dict(record, schema='native_observed_source_loaded_material_budget_edit_v7'), paths['plan'], .01)
    with pytest.raises(ValueError, match='predates'):
        validate_completed_generation(dict(record, schema='native_observed_source_loaded_material_budget_edit_v8'), paths['plan'], .01)
    with pytest.raises(ValueError, match='predates'):
        validate_completed_generation(dict(record, schema='native_observed_source_joint_trajectory_material_budget_edit_v9'), paths['plan'], .01)
    with pytest.raises(ValueError, match='predates'):
        validate_completed_generation(dict(record, schema='native_observed_source_joint_trajectory_material_budget_edit_v10'), paths['plan'], .01)
    with pytest.raises(ValueError, match='different.*scale'):
        validate_completed_generation(record, paths['plan'], .001)
    with pytest.raises(ValueError, match='lacks observed'):
        validate_completed_generation({k:v for k,v in record.items() if k!='event_reference'}, paths['plan'], .01)
    with pytest.raises(ValueError, match='unverified IK objective'):
        validate_completed_generation(dict(record, effective_objective=dict(objective,
            environment_depth_residual_scale_m=.1)), paths['plan'], .01)
    with pytest.raises(ValueError, match='different or unverified'):
        validate_completed_generation(record, paths['plan'], .01, collision_refinements=1)
    paths['events'].write_text('changed event roles')
    with pytest.raises(ValueError, match='changed observed source event'):
        validate_completed_generation(record, paths['plan'], .01)
    paths['events'].write_text('events')
    paths['sites'].write_text('changed force reference')
    with pytest.raises(ValueError, match='changed loaded material'):
        validate_completed_generation(record, paths['plan'], .01)


def test_generation_rejects_silently_dropped_ik_configuration():
    from motion_edit.generation.regenerate_edits import generation_objective, verify_effective_objective
    from motion_edit.generation.stable_contact_material import MATERIAL_SAMPLE_SCHEMA
    from motion_edit.generation.continuous_ik import SOLVER_SCHEMA
    from motion_edit.generation.optimization_geometry import OPTIMIZATION_GEOMETRY_SCHEMA, SPHERE_DISTANCE_SCHEMA
    requested = generation_objective(.01, .003, 4)
    diagnostics = dict(environment_depth_residual_scale_m=.1, environment_collision_max_refinements=4,
        environment_collision_witness_schema='newton_geometry_surface_witness_v3',
        optimization_sample_contract=MATERIAL_SAMPLE_SCHEMA, ik_residual_dtype='float64',
        ik_solver_schema=SOLVER_SCHEMA, optimization_geometry_schema=OPTIMIZATION_GEOMETRY_SCHEMA,
        sphere_distance_schema=SPHERE_DISTANCE_SCHEMA, per_frame_optimization_calls=0,
        loaded_material_motion=dict(residual_scale_m=.01,
            objective='loaded_material_phase_budget_source_regularizer_v2'))
    with pytest.raises(ValueError, match='not applied'):
        verify_effective_objective(diagnostics, requested)
    diagnostics['environment_depth_residual_scale_m'] = .003
    assert verify_effective_objective(diagnostics, requested) == requested
    with pytest.raises(ValueError, match='not applied'):
        verify_effective_objective(dict(diagnostics, ik_residual_dtype='float32'), requested)
    with pytest.raises(ValueError, match='not applied'):
        verify_effective_objective(dict(diagnostics, ik_solver_schema='per_frame_ik'), requested)
    with pytest.raises(ValueError, match='not applied'):
        verify_effective_objective(dict(diagnostics,
            ik_solver_schema='joint_trajectory_shared_fk_live_geometry_v2'), requested)
    with pytest.raises(ValueError, match='not applied'):
        verify_effective_objective(dict(diagnostics, per_frame_optimization_calls=932), requested)
    with pytest.raises(ValueError, match='not applied'):
        verify_effective_objective(dict(diagnostics,
            optimization_sample_contract='fixed_observed_material_set_per_active_episode_v1'), requested)
