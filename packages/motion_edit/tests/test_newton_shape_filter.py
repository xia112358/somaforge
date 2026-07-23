from __future__ import annotations

import numpy as np

import motion_edit.generation  # noqa: F401 - installs strict Newton shape filtering
from motion_edit.contact.newton_bindings import bind_newton_contact_patches
from motion_edit.contact.schema import ContactAnchorRecord


def test_split_foot_anchors_use_only_their_raw_shape_ids() -> None:
    frame_count = 1
    motion = {
        "body_names": np.asarray(
            [
                "right_ankle_roll_sphere_1_link",
                "right_ankle_roll_sphere_5_link",
            ],
            dtype=object,
        ),
        "body_pos_w": np.asarray(
            [[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]],
            dtype=np.float64,
        ),
        "body_quat_w": np.asarray(
            [[[1.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0]]],
            dtype=np.float64,
        ),
        "newton_body_labels": np.asarray(
            [
                "/World/envs/env_0/Robot/right_ankle_roll_sphere_1_link",
                "/World/envs/env_0/Robot/right_ankle_roll_sphere_5_link",
                "/World/ground",
            ],
            dtype=object,
        ),
        "newton_shape_labels": np.asarray(
            ["right_heel_collision", "right_toe_collision", "ground"],
            dtype=object,
        ),
        "raw_contact_selected_env_id": np.asarray(0, dtype=np.int32),
        "raw_contact_count": np.asarray([2], dtype=np.int32),
        "raw_contact_shape0": np.asarray([[0, 1]], dtype=np.int32),
        "raw_contact_shape1": np.asarray([[2, 2]], dtype=np.int32),
        "raw_contact_body0": np.asarray([[0, 1]], dtype=np.int32),
        "raw_contact_body1": np.asarray([[2, 2]], dtype=np.int32),
        "raw_contact_point0_w": np.zeros((frame_count, 2, 3), dtype=np.float64),
        "raw_contact_point1_w": np.asarray(
            [[[0.1, 0.0, 0.0], [1.1, 0.0, 0.0]]],
            dtype=np.float64,
        ),
        "raw_contact_normal_w": np.asarray(
            [[[0.0, 0.0, -1.0], [0.0, 0.0, -1.0]]],
            dtype=np.float64,
        ),
        "raw_contact_force_w": np.asarray(
            [[[0.0, 0.0, 100.0], [0.0, 0.0, 100.0]]],
            dtype=np.float64,
        ),
    }
    anchors = [
        ContactAnchorRecord(
            "motion_a",
            "right_heel_anchor",
            "right_heel",
            0,
            1,
            metadata={"foot_subcontact": {"raw_shape_ids": [0]}},
        ),
        ContactAnchorRecord(
            "motion_a",
            "right_toe_anchor",
            "right_toe",
            0,
            1,
            metadata={"foot_subcontact": {"raw_shape_ids": [1]}},
        ),
    ]

    patches, summary = bind_newton_contact_patches(anchors, motion)
    by_anchor = {patch.anchor_id: patch for patch in patches}

    assert by_anchor["right_heel_anchor"].newton_shape_labels == ["right_heel_collision"]
    assert by_anchor["right_toe_anchor"].newton_shape_labels == ["right_toe_collision"]
    assert summary["strict_shape_filter_anchor_count"] == 2
    assert summary["raw_shape_ids_by_anchor"] == {
        "right_heel_anchor": [0],
        "right_toe_anchor": [1],
    }
    assert summary["filtered_raw_contact_count"] == 2
