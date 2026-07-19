from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
from somaforge_core.robot_assets import encode_robot_asset_json

from motion_edit.contact import (
    ContactAnchorRecord,
    ContactEventRecord,
    ContactGraph,
    ContactSurfaceRecord,
    ContactTransitionRecord,
    read_contact_edit_plan,
    read_contact_graph,
    write_contact_layer,
    write_contact_surfaces,
)
from motion_edit.generation.robot_mirror_ik import (
    _blended_contact_target,
    _blended_contact_trajectory,
    _dominant_rigid_contact_proxy,
    _project_trajectory_to_surface,
    _smoothed_contact_trajectory,
    _stabilized_hand_force,
)
from motion_edit.robot_mirror import (
    _canonicalize_quaternion_hemisphere_wxyz,
    mirror_motion_npz,
)
from motion_edit.task_variants import create_robot_mirror_task_variant


def _canonical_joint_names() -> list[str]:
    return [
        "left_hip_pitch_joint",
        "left_hip_roll_joint",
        "left_hip_yaw_joint",
        "left_knee_joint",
        "left_ankle_pitch_joint",
        "left_ankle_roll_joint",
        "right_hip_pitch_joint",
        "right_hip_roll_joint",
        "right_hip_yaw_joint",
        "right_knee_joint",
        "right_ankle_pitch_joint",
        "right_ankle_roll_joint",
        "waist_yaw_joint",
        "waist_roll_joint",
        "waist_pitch_joint",
        "left_shoulder_pitch_joint",
        "left_shoulder_roll_joint",
        "left_shoulder_yaw_joint",
        "left_elbow_joint",
        "left_wrist_roll_joint",
        "left_wrist_pitch_joint",
        "left_wrist_yaw_joint",
        "right_shoulder_pitch_joint",
        "right_shoulder_roll_joint",
        "right_shoulder_yaw_joint",
        "right_elbow_joint",
        "right_wrist_roll_joint",
        "right_wrist_pitch_joint",
        "right_wrist_yaw_joint",
    ]


def _write_motion(path: Path, *, with_force: bool) -> None:
    joints = _canonical_joint_names()
    bodies = ["pelvis", "left_ankle_roll_link", "right_ankle_roll_link"]
    qpos = np.zeros((2, 36), dtype=np.float32)
    qpos[:, :3] = [0.5, 0.5, 0.0]
    qpos[:, 3] = 1.0
    qpos[:, 7:] = np.arange(1, 30, dtype=np.float32)
    velocity = np.zeros((2, 35), dtype=np.float32)
    velocity[:, 6:] = np.arange(31, 60, dtype=np.float32)
    body_pos = np.asarray(
        [
            [[0.5, 0.5, 0.9], [0.2, 0.5, 0.1], [0.8, 0.5, 0.1]],
            [[0.5, 0.4, 0.9], [0.25, 0.4, 0.1], [0.75, 0.4, 0.1]],
        ],
        dtype=np.float32,
    )
    body_quat = np.zeros((2, 3, 4), dtype=np.float32)
    body_quat[..., 0] = 1.0
    payload = {
        "fps": np.asarray([50.0], dtype=np.float32),
        "joint_names": np.asarray(joints),
        "body_names": np.asarray(bodies),
        "joint_pos": qpos,
        "joint_vel": velocity,
        "body_pos_w": body_pos,
        "body_quat_w": body_quat,
        "body_lin_vel_w": np.zeros_like(body_pos),
        "body_ang_vel_w": np.zeros_like(body_pos),
        "robot_asset_json": np.asarray(encode_robot_asset_json()),
    }
    if with_force:
        part_order = np.asarray(["LHEE", "LTOE", "RHEE", "RTOE", "LH", "RH", "LK", "RK"])
        force = np.zeros((2, 8, 3), dtype=np.float32)
        force[:, 0] = [1.0, 2.0, 3.0]
        force[:, 2] = [4.0, 5.0, 6.0]
        contact_mask = np.zeros((2, 8), dtype=bool)
        contact_mask[:, [0, 2]] = True
        positions = np.zeros((2, 8, 3), dtype=np.float32)
        positions[:, 0] = [0.2, 0.7, 1.0]
        positions[:, 2] = [0.8, 0.7, 1.0]
        payload.update(
            contact_force_part_order=part_order,
            contact_force_part_w=force,
            contact_force_part_mask=contact_mask,
            contact_force_part_mask_raw=contact_mask,
            contact_force_part_position_w=positions,
            contact_force_part_position_valid=contact_mask,
            contact_force_part_history_w=np.repeat(force[:, None], 3, axis=1),
            raw_contact_count=np.ones(2, dtype=np.int32),
            raw_contact_body0=np.ones((2, 1), dtype=np.int32),
        )
    np.savez(path, **payload)


def test_robot_only_mirror_swaps_leading_side_and_keeps_obstacle_identity() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        motion = root / "motion.npz"
        force = root / "force.npz"
        terrain = root / "box.obj"
        terrain.write_text("v 0 0 0\nv 1 0 0\nv 1 1 1\n", encoding="utf-8")
        _write_motion(motion, with_force=False)
        _write_motion(force, with_force=True)
        surfaces = [
            ContactSurfaceRecord(
                motion_id="climb_00",
                surface_id="box_top",
                object_id="box",
                surface_type="box_face",
                origin=[0.5, 0.5, 1.0],
                normal=[0.0, 0.0, 1.0],
                tangent_u=[1.0, 0.0, 0.0],
                tangent_v=[0.0, 1.0, 0.0],
                bounds={"u": [-0.5, 0.5], "v": [-0.5, 0.5]},
            )
        ]
        surface_path = root / "surfaces.jsonl"
        write_contact_surfaces(surface_path, surfaces)
        graph = ContactGraph(
            motion_id="climb_00",
            events=[
                ContactEventRecord(
                    motion_id="climb_00",
                    event_id="left-touch",
                    frame=0,
                    body="left_toe",
                    event_type="touchdown",
                    contact_after=["left_toe"],
                )
            ],
            anchors=[
                ContactAnchorRecord(
                    motion_id="climb_00",
                    anchor_id="left-box",
                    body="left_toe",
                    start_frame=0,
                    end_frame=2,
                    world_position=[0.2, 0.7, 1.0],
                    surface_id="box_top",
                    surface_origin=[0.5, 0.5, 1.0],
                    surface_normal=[0.0, 0.0, 1.0],
                    surface_tangent_u=[1.0, 0.0, 0.0],
                    surface_tangent_v=[0.0, 1.0, 0.0],
                    surface_bounds={"u": [-0.5, 0.5], "v": [-0.5, 0.5]},
                    surface_coordinates={"u": -0.3, "v": 0.2},
                )
            ],
            transitions=[
                ContactTransitionRecord(
                    motion_id="climb_00",
                    transition_id="left-step",
                    start_frame=0,
                    end_frame=2,
                    active_body="left_foot",
                    support_bodies=["right_foot"],
                    source_anchor_id="left-box",
                )
            ],
        )
        layers = root / "layers"
        write_contact_layer(layers / "contact/source", graph)

        artifacts = create_robot_mirror_task_variant(
            motion_id="climb_00",
            source_motion_path=motion,
            contact_force_source_path=force,
            source_contact_layer="contact/source",
            source_surface_catalog=surface_path,
            source_terrain_mesh=terrain,
            output_dir=root / "output",
            layers_root=layers,
        )

        with np.load(artifacts.initial_motion_path, allow_pickle=True) as mirrored:
            names = list(map(str, mirrored["joint_names"]))
            left_pitch = names.index("left_hip_pitch_joint")
            right_pitch = names.index("right_hip_pitch_joint")
            left_roll = names.index("left_hip_roll_joint")
            right_roll = names.index("right_hip_roll_joint")
            assert mirrored["joint_pos"][0, 7 + left_pitch] == 1 + right_pitch
            assert mirrored["joint_pos"][0, 7 + right_pitch] == 1 + left_pitch
            assert mirrored["joint_pos"][0, 7 + left_roll] == -(1 + right_roll)
            assert mirrored["joint_pos"][0, 7 + right_roll] == -(1 + left_roll)
            assert np.array_equal(mirrored["joint_pos"][:, :7], np.asarray([[0.5, 0.5, 0, 1, 0, 0, 0]] * 2))
            assert mirrored["body_pos_w"].shape == (2, 3, 3)
            assert np.isfinite(mirrored["body_pos_w"]).all()
            assert np.isfinite(mirrored["body_quat_w"]).all()

        with np.load(artifacts.output_motion_path, allow_pickle=True) as output, np.load(
            artifacts.initial_motion_path, allow_pickle=True
        ) as initial:
            assert np.array_equal(output["joint_pos"], initial["joint_pos"])
            assert np.array_equal(output["body_pos_w"], initial["body_pos_w"])

        with np.load(artifacts.output_contact_force_path, allow_pickle=True) as mirrored_force:
            assert "raw_contact_count" not in mirrored_force.files
            assert not bool(mirrored_force["raw_contact_available"])
            assert np.allclose(mirrored_force["contact_force_part_w"][0, 0], [4.0, -5.0, 6.0])
            assert np.allclose(mirrored_force["contact_force_part_position_w"][0, 0], [0.8, 0.3, 1.0])

        mirrored_graph = read_contact_graph(layers / artifacts.output_contact_layer, "climb_00")
        anchors = {anchor.body: anchor for anchor in mirrored_graph.anchors}
        assert set(anchors) == {"left_heel", "right_heel"}
        assert np.allclose(anchors["left_heel"].world_position, [0.8, 0.3, 1.0])
        assert np.allclose(anchors["right_heel"].world_position, [0.2, 0.3, 1.0])
        assert all(anchor.position_source == "body_pos_w_mean" for anchor in anchors.values())
        assert all(anchor.source == "robot_local_mirror_redetected" for anchor in anchors.values())

        plan = read_contact_edit_plan(artifacts.plan_path)
        manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
        assert plan.status == "generated"
        assert plan.metadata["generation_mode"] == "direct_robot_local_reflection"
        assert plan.metadata["world_contact_anchor_lock"] is False
        assert plan.metadata["obstacle_transform"] == "identity"
        assert artifacts.terrain_path == terrain.resolve()
        assert manifest["source_terrain_mesh"] == manifest["target_terrain_mesh"]
        assert manifest["terrain_sha256_before"] == manifest["terrain_sha256_after"]


def test_robot_mirror_canonicalizes_equivalent_root_quaternion_signs() -> None:
    quaternions = np.asarray(
        [
            [1.0, 0.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    canonical = _canonicalize_quaternion_hemisphere_wxyz(quaternions)
    assert np.all(np.sum(canonical[:-1] * canonical[1:], axis=1) >= 0.0)
    assert np.allclose(np.abs(canonical[:, 0]), 1.0)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source.npz"
        output = root / "mirrored.npz"
        _write_motion(source, with_force=False)
        with np.load(source, allow_pickle=True) as data:
            payload = {key: np.asarray(data[key]) for key in data.files}
        qpos = np.repeat(np.asarray(payload["joint_pos"][:1]), 3, axis=0)
        qpos[:, 3:7] = quaternions
        payload["joint_pos"] = qpos
        for key in ("joint_vel", "body_pos_w", "body_quat_w", "body_lin_vel_w", "body_ang_vel_w"):
            payload[key] = np.repeat(np.asarray(payload[key][:1]), 3, axis=0)
        np.savez(source, **payload)

        mirror_motion_npz(source, output)
        with np.load(output, allow_pickle=True) as mirrored:
            root_quaternion = np.asarray(mirrored["joint_pos"][:, 3:7])
            assert np.all(np.sum(root_quaternion[:-1] * root_quaternion[1:], axis=1) >= 0.0)


def test_rigid_contact_proxy_does_not_switch_across_recording_gaps() -> None:
    frames = 6
    root_qpos = np.zeros((frames, 7), dtype=np.float64)
    root_qpos[:, 3] = 1.0
    fk = np.zeros((frames, 2, 7), dtype=np.float64)
    fk[..., 0] = 1.0
    fk[:, 1, 4] = 1.0
    points = np.zeros((frames, 3), dtype=np.float64)
    points[:, 1] = [0.10, 0.11, 9.0, 0.20, 0.09, 0.10]
    points[3, 0] = 1.0

    link_index, local_offset = _dominant_rigid_contact_proxy(
        recorded_points_w=points,
        recorded_root_qpos=root_qpos,
        recorded_fk=fk,
        link_group=np.asarray([0, 1], dtype=np.int32),
        active_frames=np.asarray([0, 1, 3, 4, 5], dtype=np.int64),
    )

    assert link_index == 0
    assert np.allclose(local_offset, [0.0, 0.10, 0.0])


def test_contact_target_fades_into_and_out_of_one_fixed_handle() -> None:
    source = np.zeros((12, 3), dtype=np.float64)
    target, start, end = _blended_contact_target(
        source_trajectory_w=source,
        target_position_w=np.asarray([1.0, 0.0, 0.0]),
        contact_start=4,
        contact_end=8,
        fade_frames=3,
    )

    assert (start, end) == (1, 11)
    assert np.allclose(target[4:8], [1.0, 0.0, 0.0])
    assert target[1, 0] == 0.0
    assert 0.0 < target[2, 0] < target[3, 0] < 1.0
    assert 0.0 < target[9, 0] < target[8, 0] < 1.0
    assert target[10, 0] == 0.0


def test_one_handle_moves_a_smoothed_contact_trajectory_instead_of_collapsing_it() -> None:
    frames = 30
    recorded = np.zeros((frames, 3), dtype=np.float64)
    recorded[:, 0] = np.linspace(0.0, 0.2, frames)
    recorded[:, 1] = 0.02 * ((-1.0) ** np.arange(frames))
    recorded[:, 2] = 0.01
    active = np.asarray([*range(4, 12), *range(15, 26)], dtype=np.int64)
    contact = _smoothed_contact_trajectory(
        recorded_positions_w=recorded,
        active_frames=active,
        contact_start=4,
        contact_end=26,
        handle_position_w=np.asarray([0.4, -0.1, 0.0]),
        surface_origin_w=np.zeros(3),
        surface_normal_w=np.asarray([0.0, 0.0, 1.0]),
        smoothing_window=9,
    )

    assert contact.shape == (22, 3)
    assert np.allclose(np.mean(contact, axis=0), [0.4, -0.1, 0.0])
    assert np.ptp(contact[:, 0]) > 0.1
    assert np.max(np.abs(np.diff(contact[:, 1], n=2))) < 0.03

    source = np.zeros((frames, 3), dtype=np.float64)
    blended, start, end = _blended_contact_trajectory(
        source_trajectory_w=source,
        contact_target_w=contact,
        contact_start=4,
        contact_end=26,
        fade_frames=3,
    )
    assert (start, end) == (1, 29)
    assert np.allclose(blended[4:26], contact)


def test_hand_force_mask_gaps_are_filled_only_inside_the_contact_episode() -> None:
    frames = 30
    force = np.zeros((frames, 2, 3), dtype=np.float64)
    force[:, 0, 2] = np.linspace(10.0, 20.0, frames)
    mask = np.zeros((frames, 2), dtype=bool)
    mask[5:12, 0] = True
    mask[15:25, 0] = True
    valid = mask.copy()
    graph = ContactGraph(
        motion_id="climb_00",
        anchors=[
            ContactAnchorRecord(
                motion_id="climb_00",
                anchor_id="left-hand-stage",
                body="left_hand",
                start_frame=5,
                end_frame=25,
                world_position=[0.0, 0.0, 0.0],
                surface_id="box_top",
                surface_origin=[0.0, 0.0, 0.0],
                surface_normal=[0.0, 0.0, 1.0],
                surface_tangent_u=[1.0, 0.0, 0.0],
                surface_tangent_v=[0.0, 1.0, 0.0],
                surface_bounds={"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
                surface_coordinates={"u": 0.0, "v": 0.0},
            )
        ],
    )
    stabilized = _stabilized_hand_force(
        recorded_force={
            "contact_force_part_order": np.asarray(["LH", "RH"]),
            "contact_force_part_w": force,
            "contact_force_part_mask": mask,
            "contact_force_part_position_valid": valid,
        },
        graph=graph,
        end_frame=30,
    )

    result_mask = stabilized["contact_force_part_mask"]
    assert np.all(result_mask[5:25, 0])
    assert not np.any(result_mask[:5, 0])
    assert not np.any(result_mask[25:, 0])
    assert not np.any(result_mask[:, 1])
    assert np.all(stabilized["contact_force_part_w"][12:15, 0, 2] > 0.0)


def test_reference_contact_projection_changes_only_the_surface_normal_component() -> None:
    source = np.asarray(
        [[0.1, -0.2, 0.05], [0.2, -0.1, 0.08], [0.4, 0.3, -0.02]],
        dtype=np.float64,
    )
    projected = _project_trajectory_to_surface(
        source,
        surface_origin_w=np.asarray([0.0, 0.0, 0.7]),
        surface_normal_w=np.asarray([0.0, 0.0, 1.0]),
    )

    assert np.allclose(projected[:, :2], source[:, :2])
    assert np.allclose(projected[:, 2], 0.7)
