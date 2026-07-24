from __future__ import annotations

import numpy as np

from motion_edit.generation.pyroki_taskspace import (
    compile_pyroki_taskspace,
    holosoma_joint_velocities,
    quat_apply_wxyz,
    world_body_poses_from_pyroki_fk,
)
from motion_edit.generation.taskspace_spec import ContactAwareTaskspaceMotion, ContactPatchTarget


def _spec() -> ContactAwareTaskspaceMotion:
    contact = ContactPatchTarget(
        anchor_id="left_foot_0",
        kind="edited_contact",
        body_label="/World/envs/env_0/Robot/left_ankle_roll_link",
        shape_labels=("left_sole",),
        points_local=np.asarray([[0.1, 0.0, -0.05]], dtype=np.float64),
        frames=np.asarray([11, 12], dtype=np.int64),
        target_points_w=np.asarray([[[1.0, 2.0, 0.0]], [[1.1, 2.0, 0.0]]], dtype=np.float64),
    )
    return ContactAwareTaskspaceMotion(
        motion_id="demo",
        fps=50.0,
        frame_start=10,
        frame_end=13,
        semantic_names=("pelvis", "left_foot", "left_elbow"),
        semantic_targets_w=np.zeros((3, 3, 3), dtype=np.float64),
        semantic_weights=np.ones((3, 3), dtype=np.float64),
        contacts=(contact,),
        source_qpos=np.zeros((3, 9), dtype=np.float64),
        source_qvel=np.zeros((3, 8), dtype=np.float64),
        source_reference_weights=np.full((3, 9), 0.01, dtype=np.float64),
        boundary_weights=np.asarray([1.0, 0.0, 1.0], dtype=np.float64),
    )


def test_compile_pyroki_taskspace_resolves_semantics_and_global_contact_frames() -> None:
    spec = _spec()
    compiled = compile_pyroki_taskspace(
        spec,
        ("pelvis", "left_ankle_roll_link", "left_elbow_link"),
        edited_contact_weight=123.0,
    )
    assert compiled.semantic_names == ("pelvis", "left_foot", "left_elbow")
    assert compiled.semantic_link_indices.tolist() == [0, 1, 2]
    assert compiled.contact_weights[:, 0].tolist() == [0.0, 123.0, 123.0]
    np.testing.assert_allclose(compiled.contact_points_local[1, 0], [0.1, 0.0, -0.05])
    np.testing.assert_allclose(compiled.contact_targets_w[2, 0], [1.1, 2.0, 0.0])
    assert compiled.unresolved_semantics == ()
    assert compiled.unresolved_contacts == ()


def test_compile_pyroki_taskspace_keeps_full_contact_weight_at_boundaries() -> None:
    spec = _spec()
    compiled = compile_pyroki_taskspace(
        spec,
        ("pelvis", "left_ankle_roll_link", "left_elbow_link"),
        edited_contact_weight=123.0,
    )
    assert compiled.contact_weights[:, 0].tolist() == [0.0, 123.0, 123.0]


def test_compile_pyroki_taskspace_keeps_short_fixed_contact() -> None:
    edited = _spec()
    fixed_contact = ContactPatchTarget(
        **{
            **edited.contacts[0].__dict__,
            "anchor_id": "fixed_left_foot_0",
            "kind": "fixed_contact",
        }
    )
    fixed = ContactAwareTaskspaceMotion(
        **{
            **edited.__dict__,
            "contacts": (fixed_contact,),
        }
    )

    compiled = compile_pyroki_taskspace(
        fixed,
        ("pelvis", "left_ankle_roll_link", "left_elbow_link"),
        fixed_contact_weight=123.0,
    )

    assert compiled.contact_weights[:, 0].tolist() == [0.0, 123.0, 123.0]


def test_world_body_poses_compose_root_and_link_pose() -> None:
    angle = np.pi / 2.0
    root_quat = np.asarray([np.cos(angle / 2.0), 0.0, 0.0, np.sin(angle / 2.0)])
    root = np.asarray([[1.0, 2.0, 3.0, *root_quat]], dtype=np.float64)
    fk = np.asarray([[[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0]]], dtype=np.float64)
    body_pos, body_quat = world_body_poses_from_pyroki_fk(root, fk)
    np.testing.assert_allclose(body_pos[0, 0], [1.0, 3.0, 3.0], atol=1.0e-6)
    np.testing.assert_allclose(body_quat[0, 0], root_quat, atol=1.0e-6)
    np.testing.assert_allclose(quat_apply_wxyz(root_quat, [1.0, 0.0, 0.0]), [0.0, 1.0, 0.0], atol=1.0e-6)


def test_holosoma_joint_velocities_use_six_root_velocity_columns() -> None:
    qpos = np.zeros((3, 9), dtype=np.float64)
    qpos[:, 0] = [0.0, 0.1, 0.2]
    qpos[:, 3] = 1.0
    qpos[:, 7] = [0.0, 0.2, 0.4]
    velocity = holosoma_joint_velocities(qpos, 10.0)
    assert velocity.shape == (3, 8)
    np.testing.assert_allclose(velocity[:, 0], 1.0, atol=1.0e-6)
    np.testing.assert_allclose(velocity[:, 6], 2.0, atol=1.0e-6)
