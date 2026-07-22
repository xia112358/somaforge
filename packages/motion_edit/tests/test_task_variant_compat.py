from __future__ import annotations

import json

import numpy as np

from motion_edit.contact.plans import ContactEditPlan, read_contact_edit_plan, validate_contact_edit_plan
from motion_edit.contact.schema import ContactAnchorRecord, ContactSurfaceRecord
from motion_edit.generation.task_variant_compat import apply_pose_edits_to_proxy, expand_task_variant_plan


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
