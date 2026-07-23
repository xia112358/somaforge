from __future__ import annotations

import numpy as np

from motion_edit.generation.contact_semantic_aliases import install_lte_contact_semantic_aliases
from motion_edit.generation.lte_fullbody import _resolve_lte_handle_name


def test_wbt_heel_toe_parts_resolve_to_ankle_and_toe_semantics() -> None:
    install_lte_contact_semantic_aliases()
    keypoints = {
        "left_ankle": np.zeros((2, 3), dtype=np.float64),
        "left_foot": np.zeros((2, 3), dtype=np.float64),
        "right_ankle": np.zeros((2, 3), dtype=np.float64),
        "right_foot": np.zeros((2, 3), dtype=np.float64),
        "left_hand": np.zeros((2, 3), dtype=np.float64),
        "right_hand": np.zeros((2, 3), dtype=np.float64),
        "left_knee": np.zeros((2, 3), dtype=np.float64),
        "right_knee": np.zeros((2, 3), dtype=np.float64),
    }

    expected = {
        "left_heel": "left_ankle",
        "left_toe": "left_foot",
        "right_heel": "right_ankle",
        "right_toe": "right_foot",
        "LHEE": "left_ankle",
        "LTOE": "left_foot",
        "RHEE": "right_ankle",
        "RTOE": "right_foot",
    }
    for body, semantic in expected.items():
        assert _resolve_lte_handle_name(body, keypoints) == semantic


def test_heel_alias_falls_back_for_legacy_sparse_foot_proxy() -> None:
    keypoints = {
        "left_foot": np.zeros((2, 3), dtype=np.float64),
        "right_foot": np.zeros((2, 3), dtype=np.float64),
    }
    assert _resolve_lte_handle_name("left_heel", keypoints) == "left_foot"
    assert _resolve_lte_handle_name("right_heel", keypoints) == "right_foot"
