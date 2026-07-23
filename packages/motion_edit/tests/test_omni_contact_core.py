from __future__ import annotations

import numpy as np

from motion_edit.contact_laplacian import solver
from motion_edit.generation import lte_fullbody, pyroki_taskspace
from motion_edit.generation import omni_contact_graph as omni
from motion_edit.generation.omni_contact_core import CONTACT_CORE_NAMES


def test_contact_core_keeps_heel_and_toe_as_independent_nodes() -> None:
    assert lte_fullbody.LTE_HANDLE_KEYPOINT_NAMES == CONTACT_CORE_NAMES
    assert "left_heel" in lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS
    assert "right_heel" in lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS
    assert (
        lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["left_heel"][0]
        == "left_ankle_roll_sphere_1_link"
    )
    assert (
        lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["right_heel"][0]
        == "right_ankle_roll_sphere_1_link"
    )
    assert (
        lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["left_foot"][0]
        == "left_ankle_roll_sphere_5_link"
    )
    assert (
        lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["right_foot"][0]
        == "right_ankle_roll_sphere_5_link"
    )

    assert "left_heel" in omni.OMNI_SOLVER_POINT_ORDER
    assert "right_heel" in omni.OMNI_SOLVER_POINT_ORDER
    assert ("left_ankle", "left_heel") in omni.OMNI_BODY_EDGES
    assert ("left_ankle", "left_foot") in omni.OMNI_BODY_EDGES
    assert ("right_ankle", "right_heel") in omni.OMNI_BODY_EDGES
    assert ("right_ankle", "right_foot") in omni.OMNI_BODY_EDGES
    assert solver._SEMANTIC_BODY_EDGE_CANDIDATES == omni.OMNI_BODY_EDGES


def test_pyroki_resolves_contact_core_to_real_sphere_links() -> None:
    assert (
        pyroki_taskspace.SEMANTIC_LINK_ALIASES["left_heel"][0]
        == "left_ankle_roll_sphere_1_link"
    )
    assert (
        pyroki_taskspace.SEMANTIC_LINK_ALIASES["right_heel"][0]
        == "right_ankle_roll_sphere_1_link"
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


def test_contact_masks_map_foot_semantic_to_toe_channel() -> None:
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

    left_heel = lte_fullbody._contact_mask_for_keypoint(motion, "left_heel", 2)
    left_foot = lte_fullbody._contact_mask_for_keypoint(motion, "left_foot", 2)

    np.testing.assert_array_equal(left_heel, np.asarray([True, False]))
    np.testing.assert_array_equal(left_foot, np.asarray([False, True]))


def test_dense_proxy_distinguishes_heel_ankle_and_toe() -> None:
    keypoint_names = list(lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS)
    body_names = [
        "left_ankle_roll_sphere_1_link",
        "left_ankle_intermediate_1_link",
        "left_ankle_roll_sphere_5_link",
    ]

    weights = lte_fullbody._semantic_body_weights(body_names, keypoint_names)
    resolved = [keypoint_names[int(np.argmax(row))] for row in weights]

    assert resolved == ["left_heel", "left_ankle", "left_foot"]
