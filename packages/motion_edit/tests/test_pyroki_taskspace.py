from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from motion_edit.generation.pyroki_fullbody_ik import (
    CONTACT_REFERENCE_BODY_BY_PART,
    _contact_part_for_body_name,
    _contact_target_surface_class,
    _environment_deeper_weight_for_body,
    _is_contact_reference_body,
    _least_squares_sqrt_weight,
    _load_collision_reference_cache,
    _robot_min_geometry_distance_by_body,
    _robot_min_geometry_distance_by_body_surface,
    _robot_penetration_depth_by_body,
    _surface_class,
    _write_collision_reference_cache,
    self_collision_barrier_residual,
)
from motion_edit.generation.pyroki_taskspace import (
    compile_pyroki_taskspace,
    holosoma_joint_velocities,
    quat_apply_wxyz,
    world_body_poses_from_pyroki_fk,
)
from motion_edit.generation.taskspace_spec import ContactAwareTaskspaceMotion, ContactPatchTarget


def test_collision_reference_cache_roundtrip_and_identity_guard(
    tmp_path,
) -> None:
    cache_path = tmp_path / "reference_cache.npz"
    metadata = {
        "schema": "newton_collision_reference_v1",
        "source_terrain_sha256": "terrain",
        "reference_qpos_sha256": "motion",
        "robot_urdf_sha256": "robot",
        "frame_count": 2,
    }
    frames = [
        {
            ("left_ankle_roll_link", "terrain_ground:ground"): -0.001,
            ("left_knee_link", "terrain_obstacle:top"): 0.002,
        },
        {},
    ]

    _write_collision_reference_cache(
        cache_path,
        metadata=metadata,
        frames=frames,
    )

    assert _load_collision_reference_cache(
        cache_path,
        expected_metadata=metadata,
    ) == frames
    assert (
        _load_collision_reference_cache(
            cache_path,
            expected_metadata={**metadata, "reference_qpos_sha256": "other"},
        )
        is None
    )


def test_contact_capable_bodies_receive_priority_environment_barrier() -> None:
    assert _environment_deeper_weight_for_body("left_ankle_roll_link", 100.0) == 1600.0
    assert _environment_deeper_weight_for_body("right_sphere_hand_link", 100.0) == 1600.0
    assert _environment_deeper_weight_for_body("left_knee_link", 100.0) == 1600.0
    assert _environment_deeper_weight_for_body("left_hip_pitch_link", 100.0) == 400.0
    assert (
        _environment_deeper_weight_for_body(
            "left_ankle_roll_link",
            100.0,
            is_active_contact=True,
        )
        == 100.0
    )
    assert _is_contact_reference_body("left_ankle_roll_link", "LF")
    assert not _is_contact_reference_body("left_ankle_roll_sphere_1_link", "LF")
    assert _is_contact_reference_body("right_sphere_hand_link", "RH")
    assert set(CONTACT_REFERENCE_BODY_BY_PART) == {"LF", "RF", "LH", "RH", "LK", "RK"}


def test_reference_penetration_uses_true_geometry_depth_per_body() -> None:
    contacts = SimpleNamespace(
        robot_body_indices=np.asarray([3, 7, 8], dtype=np.int32),
        robot_body_names=(
            "left_ankle_roll_link",
            "left_ankle_roll_link",
            "right_ankle_roll_link",
        ),
        geometry_distance_m=np.asarray(
            [1.0, 1.0, 1.0, -0.002, 1.0, 1.0, 1.0, -0.004, 0.003],
            dtype=np.float64,
        ),
    )

    assert _robot_penetration_depth_by_body(contacts) == {
        "left_ankle_roll_link": 0.004,
        "right_ankle_roll_link": 0.0,
    }
    assert _robot_min_geometry_distance_by_body(contacts) == {
        "left_ankle_roll_link": -0.004,
        "right_ankle_roll_link": 0.003,
    }


def test_self_collision_barrier_only_penalizes_geometry_penetration() -> None:
    residual = self_collision_barrier_residual(
        np.asarray([-0.01, 0.0, 0.02]),
        np.asarray([10.0, 10.0, 10.0]),
    )
    np.testing.assert_allclose(residual, [-0.1, 0.0, 0.0])


def test_environment_objective_weights_use_residual_space_square_root() -> None:
    assert _least_squares_sqrt_weight(100.0) == 10.0
    assert _least_squares_sqrt_weight(0.0) == 0.0


def test_collision_body_names_resolve_to_force_weight_parts() -> None:
    assert _contact_part_for_body_name("left_ankle_roll_link") == "LF"
    assert _contact_part_for_body_name("right_sphere_hand_link") == "RH"
    assert _contact_part_for_body_name("left_knee_link") == "LK"
    assert _contact_part_for_body_name("right_hip_roll_link") == "RHIP"
    assert _contact_part_for_body_name("pelvis") is None


def test_reference_distances_are_paired_by_body_and_surface() -> None:
    contacts = SimpleNamespace(
        robot_body_indices=np.asarray([0, 1, 2], dtype=np.int32),
        robot_body_names=(
            "right_ankle_roll_link",
            "right_ankle_roll_link",
            "right_ankle_roll_link",
        ),
        geometry_distance_m=np.asarray(
            [-0.001, -0.002, -0.003],
            dtype=np.float64,
        ),
        body0=np.asarray([-1, -1, -1], dtype=np.int32),
        body1=np.asarray([4, 4, 4], dtype=np.int32),
        shape0=np.asarray([0, 1, 1], dtype=np.int32),
        shape1=np.asarray([8, 8, 8], dtype=np.int32),
        shape_labels=("terrain_ground", "terrain_obstacle"),
        outward_normals_w=np.asarray(
            [
                [0.0, 0.0, 1.0],
                [0.0, 0.0, 1.0],
                [1.0, 0.0, 0.0],
            ],
            dtype=np.float64,
        ),
    )

    assert _robot_min_geometry_distance_by_body_surface(contacts) == {
        ("right_ankle_roll_link", "terrain_ground:ground"): -0.001,
        ("right_ankle_roll_link", "terrain_obstacle:top"): -0.002,
        ("right_ankle_roll_link", "terrain_obstacle:side"): -0.003,
    }


def test_contact_similarity_is_scoped_to_explicit_target_surface() -> None:
    top = ContactPatchTarget(
        anchor_id="left_foot_top",
        kind="edited_contact",
        body_label="left_ankle_roll_link",
        shape_labels=("sole",),
        points_local=np.zeros((1, 3), dtype=np.float64),
        frames=np.asarray([0], dtype=np.int64),
        surface_id="multi_boxes_z_scale_1.100_top",
        target_points_w=np.zeros((1, 1, 3), dtype=np.float64),
    )
    ground = ContactPatchTarget(
        anchor_id="left_foot_ground",
        kind="fixed_contact",
        body_label="left_ankle_roll_link",
        shape_labels=("sole",),
        points_local=np.zeros((1, 3), dtype=np.float64),
        frames=np.asarray([0], dtype=np.int64),
        target_points_w=np.zeros((1, 1, 3), dtype=np.float64),
        metadata={"target_surface_id": "terrain_ground_z0"},
    )

    assert _contact_target_surface_class(top) == "top"
    assert _contact_target_surface_class(ground) == "ground"
    assert _surface_class("terrain_obstacle:side") == "side"
    assert _surface_class("terrain_ground:ground") == "ground"
    assert _surface_class("unclassified_surface") is None


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


def test_compile_pyroki_taskspace_uses_rolling_local_points_by_frame() -> None:
    spec = _spec()
    rolling = ContactPatchTarget(
        **{
            **spec.contacts[0].__dict__,
            "points_local_by_frame": np.asarray(
                [[[0.2, 0.0, -0.05]], [[0.3, 0.0, -0.05]]],
                dtype=np.float64,
            ),
        }
    )
    rolling_spec = ContactAwareTaskspaceMotion(
        **{**spec.__dict__, "contacts": (rolling,)}
    )

    compiled = compile_pyroki_taskspace(
        rolling_spec,
        ("pelvis", "left_ankle_roll_link", "left_elbow_link"),
    )

    np.testing.assert_allclose(compiled.contact_points_local[1, 0], [0.2, 0.0, -0.05])
    np.testing.assert_allclose(compiled.contact_points_local[2, 0], [0.3, 0.0, -0.05])


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
