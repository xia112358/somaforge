from __future__ import annotations

import json

import numpy as np

from motion_edit.contact.plans import ContactEditPlan, read_contact_edit_plan, validate_contact_edit_plan
from motion_edit.contact.schema import (
    ContactAnchorEditRecord,
    ContactAnchorRecord,
    ContactSurfaceRecord,
)
from motion_edit.generation.task_variant_compat import (
    apply_pose_edits_to_proxy,
    expand_task_variant_plan,
    pose_edits_for_semantic_proxy,
)


def _surface(surface_id: str, z: float) -> dict:
    return {
        "surface_id": surface_id,
        "object_id": surface_id.removesuffix("_top"),
        "surface_type": "plane",
        "origin": [0.5, -0.3, z],
        "normal": [0.0, 0.0, 1.0],
        "tangent_u": [1.0, 0.0, 0.0],
        "tangent_v": [0.0, 1.0, 0.0],
        "bounds": {"u": [-1.0, 1.0], "v": [-1.0, 1.0]},
    }


def test_reader_accepts_task_variant_fields(tmp_path) -> None:
    payload = {
        "plan_id": "height_110",
        "source_motion_path": "/tmp/source.npz",
        "source_motion_id": "climb_00",
        "source_contact_layer": "contact/source",
        "edits": [],
        "pose_edits": [],
        "surface_transforms": [
            {
                "transform_id": "height_follow",
                "kind": "surface_follow",
                "height_scale": 1.1,
                "translation_world": [0.0, 0.0, 0.07],
                "source_surface": _surface("box_1p0_top", 0.70),
                "target_surface": _surface("box_1p1_top", 0.77),
            }
        ],
        "status": "validated",
        "metadata": {"schema": "motion_edit_height_task_variant_v1"},
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    plan = read_contact_edit_plan(path)

    assert plan.pose_edits == []
    assert len(plan.surface_transforms) == 1
    assert validate_contact_edit_plan(plan) == []


def test_surface_follow_expands_anchor_with_preserved_uv() -> None:
    source_raw = _surface("box_1p0_top", 0.70)
    target_raw = _surface("box_1p1_top", 0.77)
    source = ContactSurfaceRecord(motion_id="climb_00", source="test", **source_raw)
    anchor = ContactAnchorRecord(
        motion_id="climb_00",
        anchor_id="right_toe_anchor",
        body="right_toe",
        start_frame=10,
        end_frame=20,
        world_position=[0.7, -0.4, 0.70],
        object_id="box_1p0",
        surface_id="box_1p0_top",
        surface_type="plane",
        surface_normal=[0.0, 0.0, 1.0],
        surface_coordinates={"u": 0.2, "v": -0.1},
    )
    plan = ContactEditPlan(
        plan_id="height_110",
        source_motion_path="/tmp/source.npz",
        source_motion_id="climb_00",
        source_contact_layer="contact/source",
        surface_transforms=[
            {
                "transform_id": "height_follow",
                "kind": "surface_follow",
                "height_scale": 1.1,
                "translation_world": [0.0, 0.0, 0.07],
                "source_surface": source_raw,
                "target_surface": target_raw,
            }
        ],
        status="validated",
    )

    expanded = expand_task_variant_plan(plan, anchors=[anchor], surfaces=[source])

    assert len(expanded.edits) == 1
    edit = expanded.edits[0]
    np.testing.assert_allclose(edit.delta_world, [0.0, 0.0, 0.07], atol=1.0e-9)
    np.testing.assert_allclose(edit.tangent_delta, [0.0, 0.0], atol=1.0e-9)
    assert edit.surface_id == "box_1p1_top"
    assert edit.body == "right_toe"
    assert edit.affected_frames == [10, 20]
    assert {surface.surface_id for surface in expanded.surfaces} == {"box_1p0_top", "box_1p1_top"}
    assert expanded.metadata["expanded_surface_follow_edit_count"] == 1


def test_surface_follow_composes_explicit_uv_edit_on_target_surface() -> None:
    source_raw = _surface("box_1p0_top", 0.70)
    target_raw = _surface("box_1p1_top", 0.77)
    source = ContactSurfaceRecord(motion_id="climb_00", source="test", **source_raw)
    anchor = ContactAnchorRecord(
        motion_id="climb_00",
        anchor_id="right_toe_anchor",
        body="right_toe",
        start_frame=10,
        end_frame=20,
        world_position=[0.7, -0.4, 0.70],
        object_id="box_1p0",
        surface_id="box_1p0_top",
        surface_type="plane",
        surface_normal=[0.0, 0.0, 1.0],
        surface_coordinates={"u": 0.2, "v": -0.1},
    )
    uv_edit = ContactAnchorEditRecord(
        edit_id="right_toe_u_plus",
        motion_id="climb_00",
        anchor_id=anchor.anchor_id,
        body=anchor.body,
        old_world_position=[0.7, -0.4, 0.70],
        new_world_position=[0.8, -0.4, 0.70],
        requested_delta_world=[0.1, 0.0, 0.0],
        delta_world=[0.1, 0.0, 0.0],
        tangent_delta=[0.1, 0.0],
        affected_frames=[10, 20],
        surface_id="box_1p0_top",
        surface_normal=[0.0, 0.0, 1.0],
        surface_coordinates_before={"u": 0.2, "v": -0.1},
        surface_coordinates_after={"u": 0.3, "v": -0.1},
        constraint_mode="reject",
        metadata={
            "compose_with_surface_transform": True,
            "surface_uv_delta": [0.1, 0.0],
        },
    )
    plan = ContactEditPlan(
        plan_id="height_and_uv",
        source_motion_path="/tmp/source.npz",
        source_motion_id="climb_00",
        source_contact_layer="contact/source",
        edits=[uv_edit.to_dict()],
        surface_transforms=[
            {
                "transform_id": "height_follow",
                "kind": "surface_follow",
                "height_scale": 1.1,
                "translation_world": [0.0, 0.0, 0.07],
                "source_surface": source_raw,
                "target_surface": target_raw,
            }
        ],
        status="validated",
    )

    expanded = expand_task_variant_plan(plan, anchors=[anchor], surfaces=[source])

    assert len(expanded.edits) == 1
    edit = expanded.edits[0]
    np.testing.assert_allclose(edit.new_world_position, [0.8, -0.4, 0.77], atol=1.0e-9)
    np.testing.assert_allclose(edit.delta_world, [0.1, 0.0, 0.07], atol=1.0e-9)
    assert edit.surface_id == "box_1p1_top"
    np.testing.assert_allclose(
        [edit.surface_coordinates_after["u"], edit.surface_coordinates_after["v"]],
        [0.3, -0.1],
        atol=1.0e-9,
    )
    assert edit.metadata["surface_transform_then_uv"] is True
    assert expanded.metadata["composed_surface_uv_edit_count"] == 1


def test_surface_follow_rejects_failed_binding_instead_of_fixed_world_target() -> None:
    source_raw = _surface("box_1p0_top", 0.70)
    target_raw = _surface("box_1p1_top", 0.77)
    source = ContactSurfaceRecord(motion_id="climb_00", source="test", **source_raw)
    failed_hand = ContactAnchorRecord(
        motion_id="climb_00",
        anchor_id="left_hand_failed",
        body="left_hand",
        start_frame=10,
        end_frame=20,
        world_position=[0.7, -0.4, 0.75],
        metadata={
            "surface_binding_failed": True,
            "surface_binding_failure_reason": (
                "left_hand_failed: surface box_1p0_top is farther than max_distance"
            ),
        },
    )
    bound_foot = ContactAnchorRecord(
        motion_id="climb_00",
        anchor_id="right_toe",
        body="right_toe",
        start_frame=10,
        end_frame=20,
        world_position=[0.7, -0.4, 0.70],
        object_id="box_1p0",
        surface_id="box_1p0_top",
        surface_coordinates={"u": 0.2, "v": -0.1},
    )
    plan = ContactEditPlan(
        plan_id="height_110",
        source_motion_path="/tmp/source.npz",
        source_motion_id="climb_00",
        source_contact_layer="contact/source",
        surface_transforms=[
            {
                "transform_id": "height_follow",
                "kind": "surface_follow",
                "translation_world": [0.0, 0.0, 0.07],
                "source_surface": source_raw,
                "target_surface": target_raw,
            }
        ],
        status="validated",
    )

    with np.testing.assert_raises_regex(
        ValueError,
        "rebuild it with raw-contact surface refinement",
    ):
        expand_task_variant_plan(
            plan,
            anchors=[bound_foot, failed_hand],
            surfaces=[source],
        )


def test_surface_follow_uses_one_translation_for_inconsistent_foot_anchors() -> None:
    source_raw = _surface("box_1p0_top", 0.70)
    target_raw = _surface("box_1p1_top", 0.77)
    source = ContactSurfaceRecord(motion_id="climb_00", source="test", **source_raw)
    anchors = [
        ContactAnchorRecord(
            motion_id="climb_00",
            anchor_id="right_heel",
            body="right_heel",
            start_frame=10,
            end_frame=20,
            world_position=[0.48, -0.08, 0.70],
            object_id="box_1p0",
            surface_id="box_1p0_top",
            surface_coordinates={"u": -0.10, "v": 0.22},
        ),
        ContactAnchorRecord(
            motion_id="climb_00",
            anchor_id="right_toe",
            body="right_toe",
            start_frame=15,
            end_frame=25,
            world_position=[0.42, -0.24, 0.70],
            object_id="box_1p0",
            surface_id="box_1p0_top",
            surface_coordinates={"u": -0.16, "v": 0.06},
        ),
    ]
    plan = ContactEditPlan(
        plan_id="height_110",
        source_motion_path="/tmp/source.npz",
        source_motion_id="climb_00",
        source_contact_layer="contact/source",
        surface_transforms=[
            {
                "transform_id": "height_follow",
                "kind": "surface_follow",
                "translation_world": [0.0, 0.0, 0.07],
                "source_surface": source_raw,
                "target_surface": target_raw,
            }
        ],
        status="validated",
    )

    expanded = expand_task_variant_plan(plan, anchors=anchors, surfaces=[source])

    assert len(expanded.edits) == 2
    for anchor, edit in zip(anchors, expanded.edits):
        np.testing.assert_allclose(edit.delta_world, [0.0, 0.0, 0.07])
        np.testing.assert_allclose(
            np.asarray(edit.new_world_position)
            - np.asarray(edit.old_world_position),
            [0.0, 0.0, 0.07],
        )
        np.testing.assert_allclose(edit.old_world_position, anchor.world_position)
        assert edit.metadata["uniform_surface_translation"] is True


def test_surface_follow_rotates_anchor_while_preserving_uv() -> None:
    source_raw = _surface("box_source_top", 0.70)
    target_raw = _surface("box_rotated_top", 0.70)
    target_raw["tangent_u"] = [0.0, 1.0, 0.0]
    target_raw["tangent_v"] = [-1.0, 0.0, 0.0]
    source = ContactSurfaceRecord(motion_id="climb_00", source="test", **source_raw)
    anchor = ContactAnchorRecord(
        motion_id="climb_00",
        anchor_id="left_hand",
        body="left_hand",
        start_frame=10,
        end_frame=20,
        world_position=[0.7, -0.4, 0.70],
        object_id="box_source",
        surface_id="box_source_top",
        surface_coordinates={"u": 0.2, "v": -0.1},
    )
    plan = ContactEditPlan(
        plan_id="yaw_90",
        source_motion_path="/tmp/source.npz",
        source_motion_id="climb_00",
        source_contact_layer="contact/source",
        surface_transforms=[
            {
                "transform_id": "yaw_follow",
                "kind": "surface_follow",
                "translation_world": [0.0, 0.0, 0.0],
                "source_surface": source_raw,
                "target_surface": target_raw,
            }
        ],
        status="validated",
    )

    expanded = expand_task_variant_plan(plan, anchors=[anchor], surfaces=[source])

    edit = expanded.edits[0]
    np.testing.assert_allclose(edit.new_world_position, [0.6, -0.1, 0.70])
    np.testing.assert_allclose(edit.delta_world, [-0.1, 0.3, 0.0])
    assert edit.surface_coordinates_before == edit.surface_coordinates_after
    assert edit.metadata["uniform_surface_translation"] is False


def test_translate_pose_updates_semantic_and_dense_targets() -> None:
    proxy = {
        "fps": np.asarray([50.0]),
        "body_names": np.asarray(["pelvis", "right_ankle_roll_link"]),
        "body_pos_w": np.zeros((3, 2, 3), dtype=np.float64),
        "body_lin_vel_w": np.zeros((3, 2, 3), dtype=np.float64),
        "keypoint_pelvis": np.zeros((3, 3), dtype=np.float64),
        "keypoint_right_foot": np.zeros((3, 3), dtype=np.float64),
    }
    pose_edits = [
        {
            "edit_id": "move_root_and_foot",
            "edit_type": "translate_pose",
            "affected_frames": [1, 3],
            "translation_world": [0.0, 0.0, 0.1],
            "semantic_names": ["root", "right_foot"],
            "weight_scale": 1.0,
        }
    ]

    edited, metadata = apply_pose_edits_to_proxy(proxy, pose_edits)

    np.testing.assert_allclose(edited["keypoint_pelvis"][1:, 2], 0.1)
    np.testing.assert_allclose(edited["keypoint_right_foot"][1:, 2], 0.1)
    assert float(np.max(edited["body_pos_w"][1:, :, 2])) > 0.0
    assert metadata["applied_pose_edit_count"] == 1


def test_approach_pose_edit_is_not_applied_twice_to_semantic_proxy() -> None:
    approach = ContactAnchorEditRecord(
        edit_id="approach:left_toe",
        motion_id="climb_00",
        anchor_id="left_toe",
        body="left_toe",
        delta_world=[0.0, 0.05, 0.0],
        affected_frames=[139, 141],
        metadata={
            "task_variant": "approach_position",
            "pose_interval": [139, 148],
        },
    )
    ordinary = ContactAnchorEditRecord(
        edit_id="manual:right_hand",
        motion_id="climb_00",
        anchor_id="right_hand",
        body="right_hand",
        delta_world=[0.0, 0.0, 0.02],
        affected_frames=[200, 220],
    )
    pose_edits = [
        {
            "edit_type": "translate_pose",
            "affected_frames": [139, 148],
            "translation_world": [0.0, 0.05, 0.0],
        }
    ]

    retained = pose_edits_for_semantic_proxy(
        [approach, ordinary],
        pose_edits,
    )

    assert retained == ()


def test_unpaired_pose_edit_remains_in_semantic_proxy() -> None:
    approach = ContactAnchorEditRecord(
        edit_id="approach:left_toe",
        motion_id="climb_00",
        anchor_id="left_toe",
        body="left_toe",
        delta_world=[0.0, 0.05, 0.0],
        affected_frames=[139, 141],
        metadata={
            "task_variant": "approach_position",
            "pose_interval": [139, 148],
        },
    )

    pose_edit = {
        "edit_type": "translate_pose",
        "affected_frames": [139, 148],
        "translation_world": [0.0, 0.04, 0.0],
    }
    retained = pose_edits_for_semantic_proxy(
        [approach],
        [pose_edit],
    )

    assert retained == (pose_edit,)
