from __future__ import annotations

import numpy as np

from motion_edit.generation.contact_semantic_aliases import install_lte_contact_semantic_aliases
from motion_edit.generation.lte_fullbody import _resolve_lte_handle_name


def test_wbt_heel_toe_parts_resolve_to_foot_semantics() -> None:
    install_lte_contact_semantic_aliases()
    keypoints = {
        "left_foot": np.zeros((2, 3), dtype=np.float64),
        "right_foot": np.zeros((2, 3), dtype=np.float64),
        "left_hand": np.zeros((2, 3), dtype=np.float64),
        "right_hand": np.zeros((2, 3), dtype=np.float64),
        "left_knee": np.zeros((2, 3), dtype=np.float64),
        "right_knee": np.zeros((2, 3), dtype=np.float64),
    }

    expected = {
        "left_heel": "left_foot",
        "left_toe": "left_foot",
        "right_heel": "right_foot",
        "right_toe": "right_foot",
        "LHEE": "left_foot",
        "LTOE": "left_foot",
        "RHEE": "right_foot",
        "RTOE": "right_foot",
    }
    for body, semantic in expected.items():
        assert _resolve_lte_handle_name(body, keypoints) == semantic
