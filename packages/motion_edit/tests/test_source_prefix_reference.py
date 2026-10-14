from dataclasses import replace

import numpy as np
import pytest

from motion_edit.generation.source_prefix_reference import (
    SCHEMA, apply_source_prefix, prefix_joint_prior_scales, prefix_weights,
    prefix_root_yaw_condition, rotate_root_reference,
)
from motion_edit.generation.taskspace_spec import ContactAwareTaskspaceMotion


def fixture():
    n = 20
    points = np.stack((np.arange(n)*.02, np.zeros(n), np.ones(n)), axis=-1)[:, None]
    points = np.concatenate((points, points + [0., .2, -.8]), axis=1)
    qpos = np.zeros((n, 8)); qpos[:, 3] = 1.
    spec = ContactAwareTaskspaceMotion(
        motion_id="arbitrary", fps=50., frame_start=0, frame_end=n,
        semantic_names=("root", "foot"), semantic_targets_w=points + [5., 2., 1.],
        semantic_weights=np.ones((n, 2)), contacts=(), source_qpos=qpos,
        source_qvel=np.zeros((n, 7)), source_reference_weights=np.ones((n, 8)),
        boundary_weights=np.zeros(n))
    config = dict(schema=SCHEMA, hold_frames=5, transition_end_frame=12,
                  surface_transform_id="turn", joint_prior_scale=100., semantic_weight=10000.)
    frame = dict(origin=[0., 0., 0.], tangent_u=[1., 0., 0.],
                 tangent_v=[0., 1., 0.], normal=[0., 0., 1.])
    transform = dict(transform_id="turn", source_surface=frame,
                     target_surface=dict(frame, origin=[2., 3., 0.],
                                         tangent_u=[0., 1., 0.], tangent_v=[-1., 0., 0.]))
    return spec, points, config, transform


def test_rigid_prefix_preserves_source_stance_and_velocity_without_splicing_states():
    spec, points, config, transform = fixture()
    updated = apply_source_prefix(spec, dict(zip(spec.semantic_names, points.transpose(1, 0, 2))),
                                  [transform], config)
    expected = points.copy()
    expected[..., 0] = 2-points[..., 1]
    expected[..., 1] = 3+points[..., 0]
    np.testing.assert_allclose(updated.semantic_targets_w[:5], expected[:5])
    np.testing.assert_allclose(np.diff(updated.semantic_targets_w[:5], axis=0),
                               np.diff(expected[:5], axis=0))
    np.testing.assert_array_equal(updated.semantic_targets_w[12:], spec.semantic_targets_w[12:])
    assert updated.source_qpos is spec.source_qpos
    assert updated.source_qvel is spec.source_qvel
    assert updated.contacts is spec.contacts
    np.testing.assert_array_equal(spec.semantic_targets_w, points + [5., 2., 1.])
    assert updated.metadata["source_prefix_reference"] == config
    assert updated.metadata["root_yaw_condition"]["reference_delta_degrees"] == pytest.approx(90.)


def test_transition_and_joint_prior_share_clock_and_restore_unmodified_tail():
    _, _, config, _ = fixture()
    alpha = prefix_weights(config, 20)
    assert np.all(np.diff(alpha) <= 0)
    np.testing.assert_array_equal(alpha[:5], 1)
    np.testing.assert_array_equal(alpha[12:], 0)
    existing = np.ones((20, 29))*2.
    updated = prefix_joint_prior_scales(config, 20, existing)
    np.testing.assert_array_equal(updated[:5], 100)
    np.testing.assert_array_equal(updated[12:], existing[12:])


@pytest.mark.parametrize("change", [{"hold_frames": 0}, {"hold_frames": 12},
    {"transition_end_frame": 20}, {"joint_prior_scale": float("nan")}, {"unknown": 1}])
def test_invalid_config_fails_closed(change):
    _, _, config, _ = fixture()
    with pytest.raises(ValueError):
        prefix_weights(dict(config, **change), 20)


def test_missing_transform_and_nonzero_frame_start_fail_closed():
    spec, points, config, _ = fixture()
    source = dict(zip(spec.semantic_names, points.transpose(1, 0, 2)))
    with pytest.raises(ValueError, match="transform"):
        apply_source_prefix(spec, source, [], config)
    with pytest.raises(ValueError, match="frame-zero"):
        apply_source_prefix(replace(spec, frame_start=1), source, [], config)


@pytest.mark.parametrize("angle", [-90., -10., 20., 90., 180.])
def test_rotated_path_root_heading_body_attitude_and_velocities_share_one_map(angle):
    from scipy.spatial.transform import Rotation
    from motion_edit.contact.surface_frame import map_points_between_surface_frames
    from motion_edit.generation.pyroki_taskspace import (
        holosoma_joint_velocities, holosoma_body_velocities, world_body_poses_from_pyroki_fk,
    )
    spec, points, config, transform = fixture()
    edit = Rotation.from_euler("z", angle, degrees=True)
    transform["target_surface"] = dict(transform["target_surface"],
        tangent_u=edit.apply([1., 0., 0.]).tolist(), tangent_v=edit.apply([0., 1., 0.]).tolist())
    q = spec.source_qpos.copy(); q[:, :3] = points[:, 0]
    # Nonzero source yaw/pitch and time-varying attitude expose overwrite and
    # right-composition bugs that identity source quaternions would hide.
    source_rotation = Rotation.from_euler("zyx", np.column_stack((
        123.+np.arange(len(q))*.3, np.full(len(q), 27.), np.full(len(q), -8.))), degrees=True)
    q[:, 3:7] = source_rotation.as_quat()[:, [3, 0, 1, 2]]
    updated = apply_source_prefix(replace(spec, source_qpos=q),
        dict(zip(spec.semantic_names, points.transpose(1, 0, 2))), [transform], config)
    condition = updated.metadata["root_yaw_condition"]
    assert condition["reference_delta_degrees"] == pytest.approx(angle)
    mapped_root = q[:, :7].copy()
    mapped_root[:, :3] = map_points_between_surface_frames(q[:, :3],
        transform["source_surface"], transform["target_surface"])
    edited_root = rotate_root_reference(mapped_root, condition["reference_delta_degrees"])
    np.testing.assert_allclose(Rotation.from_quat(edited_root[:, [4, 5, 6, 3]]).as_matrix(),
                               (edit*source_rotation).as_matrix(), atol=1.e-12)
    fk = np.zeros((len(q), 2, 7)); fk[..., 0] = 1.; fk[:, 1, 4:7] = [.2, -.1, -.8]
    source_pos, source_quat = world_body_poses_from_pyroki_fk(q[:, :7], fk)
    new_pos, new_quat = world_body_poses_from_pyroki_fk(edited_root, fk)
    np.testing.assert_allclose(new_pos, map_points_between_surface_frames(source_pos,
        transform["source_surface"], transform["target_surface"]), atol=1.e-6)
    # The production FK/export functions store float32 poses. Differentiation
    # at 50 Hz amplifies that quantization; retain the float64 root check above.
    np.testing.assert_allclose(Rotation.from_quat(new_quat[..., [1,2,3,0]].reshape(-1,4)).as_matrix(),
        (edit*Rotation.from_quat(source_quat[..., [1,2,3,0]].reshape(-1,4))).as_matrix(), atol=1.e-7)
    q_new = np.column_stack((edited_root, q[:, 7:]))
    v_old, v_new = holosoma_joint_velocities(q, 50.), holosoma_joint_velocities(q_new, 50.)
    np.testing.assert_allclose(v_new[:, :3], edit.apply(v_old[:, :3]), atol=1.e-7)
    np.testing.assert_allclose(v_new[:, 3:6], edit.apply(v_old[:, 3:6]), atol=1.e-7)
    lin_old, ang_old = holosoma_body_velocities(source_pos, source_quat, 50.)
    lin_new, ang_new = holosoma_body_velocities(new_pos, new_quat, 50.)
    velocity_quantization = 4*np.finfo(np.float32).eps*50.*max(1., float(np.abs(new_pos).max()))
    np.testing.assert_allclose(lin_new, edit.apply(lin_old.reshape(-1,3)).reshape(lin_old.shape), atol=velocity_quantization)
    np.testing.assert_allclose(ang_new, edit.apply(ang_old.reshape(-1,3)).reshape(ang_old.shape), atol=1.e-5)


def test_prefix_rejects_conflicting_heading_and_tilted_surface_map():
    spec, _, config, transform = fixture()
    with pytest.raises(ValueError, match="heading conflicts"):
        prefix_root_yaw_condition(config, [transform], spec.source_qpos,
                                  dict(reference_delta_degrees=0., initial_qpos=spec.source_qpos[0].tolist()))
    transform["target_surface"] = dict(transform["source_surface"],
        tangent_v=[0., 0., 1.], normal=[0., -1., 0.])
    with pytest.raises(ValueError, match="world-Z"):
        prefix_root_yaw_condition(config, [transform], spec.source_qpos)
