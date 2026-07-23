from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.contact_laplacian import solver
from motion_edit.contact_laplacian.schema import BatchContactLaplacianConfig
from motion_edit.generation import lte_fullbody, pyroki_taskspace
from motion_edit.generation import omni_contact_graph as omni
from motion_edit.generation.omni_contact_core import CONTACT_CORE_NAMES


def test_contact_core_uses_only_ankle_and_toe_foot_nodes() -> None:
    assert lte_fullbody.LTE_HANDLE_KEYPOINT_NAMES == CONTACT_CORE_NAMES
    assert CONTACT_CORE_NAMES == (
        "left_ankle",
        "left_foot",
        "right_ankle",
        "right_foot",
        "left_hand",
        "right_hand",
        "left_knee",
        "right_knee",
    )

    assert "left_heel" not in lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS
    assert "right_heel" not in lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS
    assert "left_heel" not in omni.OMNI_SOLVER_POINT_ORDER
    assert "right_heel" not in omni.OMNI_SOLVER_POINT_ORDER

    assert (
        lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["left_ankle"][0]
        == "left_ankle_intermediate_1_link"
    )
    assert (
        lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["left_foot"][0]
        == "left_ankle_roll_sphere_5_link"
    )
    assert ("left_knee", "left_ankle") in omni.OMNI_BODY_EDGES
    assert ("left_ankle", "left_foot") in omni.OMNI_BODY_EDGES
    assert ("right_knee", "right_ankle") in omni.OMNI_BODY_EDGES
    assert ("right_ankle", "right_foot") in omni.OMNI_BODY_EDGES
    assert solver._SEMANTIC_BODY_EDGE_CANDIDATES == omni.OMNI_BODY_EDGES


def test_pyroki_resolves_ankle_toe_and_hemisphere_hand_links() -> None:
    assert (
        pyroki_taskspace.SEMANTIC_LINK_ALIASES["left_ankle"][0]
        == "left_ankle_intermediate_1_link"
    )
    assert (
        pyroki_taskspace.SEMANTIC_LINK_ALIASES["right_ankle"][0]
        == "right_ankle_intermediate_1_link"
    )
    assert (
        pyroki_taskspace.SEMANTIC_LINK_ALIASES["left_foot"][0]
        == "left_ankle_roll_sphere_5_link"
    )
    assert (
        pyroki_taskspace.SEMANTIC_LINK_ALIASES["right_foot"][0]
        == "right_ankle_roll_sphere_5_link"
    )
    assert (
        pyroki_taskspace.SEMANTIC_LINK_ALIASES["left_hand"][0]
        == "left_sphere_hand_link"
    )
    assert (
        pyroki_taskspace.SEMANTIC_LINK_ALIASES["right_hand"][0]
        == "right_sphere_hand_link"
    )
    assert "left_heel" not in pyroki_taskspace.SEMANTIC_LINK_ALIASES
    assert "right_heel" not in pyroki_taskspace.SEMANTIC_LINK_ALIASES


def test_contact_masks_map_heel_to_ankle_and_toe_to_foot() -> None:
    motion = {
        "part_order": np.asarray(
            [
                "left_heel",
                "left_toe",
                "right_heel",
                "right_toe",
                "left_hand",
                "right_hand",
                "left_knee",
                "right_knee",
            ],
            dtype=object,
        ),
        "contact_part_mask": np.asarray(
            [
                [True, False, False, False, False, False, False, False],
                [False, True, False, False, False, False, False, False],
            ],
            dtype=bool,
        ),
    }

    left_ankle = lte_fullbody._contact_mask_for_keypoint(motion, "left_ankle", 2)
    left_foot = lte_fullbody._contact_mask_for_keypoint(motion, "left_foot", 2)

    np.testing.assert_array_equal(left_ankle, np.asarray([True, False]))
    np.testing.assert_array_equal(left_foot, np.asarray([False, True]))


def test_laplacian_handles_map_heel_to_ankle_and_toe_to_toe() -> None:
    keypoints = {
        "left_ankle": np.zeros((2, 3), dtype=np.float64),
        "left_foot": np.ones((2, 3), dtype=np.float64),
    }
    anchors = [
        ContactAnchorRecord("motion_a", "heel_anchor", "left_heel", 0, 2),
        ContactAnchorRecord("motion_a", "toe_anchor", "left_toe", 0, 2),
    ]
    edits = [
        ContactAnchorEditRecord(
            edit_id="heel_edit",
            motion_id="motion_a",
            anchor_id="heel_anchor",
            body="left_heel",
            delta_world=[0.0, 0.0, 0.1],
            affected_frames=[0, 2],
        ),
        ContactAnchorEditRecord(
            edit_id="toe_edit",
            motion_id="motion_a",
            anchor_id="toe_anchor",
            body="left_toe",
            delta_world=[0.0, 0.0, 0.1],
            affected_frames=[0, 2],
        ),
    ]

    handles = lte_fullbody._contact_laplacian_handles_from_edits(
        edits,
        keypoints,
        graph=SimpleNamespace(anchors=anchors),
        config=BatchContactLaplacianConfig(),
        source_motion=None,
    )
    by_anchor = {handle.anchor_id: handle for handle in handles}

    assert by_anchor["heel_anchor"].semantic_name == "left_ankle"
    assert by_anchor["toe_anchor"].semantic_name == "left_foot"
    np.testing.assert_allclose(by_anchor["heel_anchor"].target_xyz[:, 2], 0.1)
    np.testing.assert_allclose(by_anchor["toe_anchor"].target_xyz[:, 2], 1.1)


def test_dense_proxy_maps_rear_foot_to_ankle_and_forefoot_to_toe() -> None:
    keypoint_names = list(lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS)
    body_names = [
        "left_ankle_roll_sphere_1_link",
        "left_ankle_intermediate_1_link",
        "left_ankle_roll_sphere_5_link",
    ]

    weights = lte_fullbody._semantic_body_weights(body_names, keypoint_names)
    resolved = [keypoint_names[int(np.argmax(row))] for row in weights]

    assert resolved == ["left_ankle", "left_ankle", "left_foot"]
