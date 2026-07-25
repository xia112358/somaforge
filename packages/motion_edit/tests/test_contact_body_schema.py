import unittest

from motion_edit.contact.raw_contacts import PART_ALIASES
import numpy as np

from motion_edit.generation.lte_fullbody import (
    CONTACT_BODY_LINK_CANDIDATES,
    LTE_FULLBODY_KEYPOINT_LINKS,
    _semantic_keypoints_from_motion,
)
from motion_edit.generation.pyroki_fullbody_ik import TARGET_LINK_GROUPS
from somaforge_core.contact_schema import CONTACT_BODY_NAMES_BY_PART


class ContactBodySchemaTests(unittest.TestCase):
    def test_lte_tracks_sphere_hand_first_but_keeps_wrist_fallback(self) -> None:
        assert LTE_FULLBODY_KEYPOINT_LINKS["left_hand"][0] == (
            CONTACT_BODY_NAMES_BY_PART["left_hand"][0]
        )
        assert LTE_FULLBODY_KEYPOINT_LINKS["right_hand"][0] == (
            CONTACT_BODY_NAMES_BY_PART["right_hand"][0]
        )
        assert "left_wrist_yaw_link" in LTE_FULLBODY_KEYPOINT_LINKS["left_hand"]
        assert "right_wrist_yaw_link" in LTE_FULLBODY_KEYPOINT_LINKS["right_hand"]

    def test_lte_contact_candidates_only_use_physical_contact_bodies(self) -> None:
        assert CONTACT_BODY_LINK_CANDIDATES["left_hand"][0] == (
            CONTACT_BODY_NAMES_BY_PART["left_hand"][0]
        )
        assert CONTACT_BODY_LINK_CANDIDATES["right_hand"][0] == (
            CONTACT_BODY_NAMES_BY_PART["right_hand"][0]
        )
        assert set(CONTACT_BODY_NAMES_BY_PART["left_foot"]).issubset(
            CONTACT_BODY_LINK_CANDIDATES["left_foot"]
        )
        assert set(CONTACT_BODY_NAMES_BY_PART["right_foot"]).issubset(
            CONTACT_BODY_LINK_CANDIDATES["right_foot"]
        )
        assert CONTACT_BODY_LINK_CANDIDATES["left_foot"][0] == "left_ankle_roll_sphere_5_link"
        assert CONTACT_BODY_LINK_CANDIDATES["right_foot"][0] == "right_ankle_roll_sphere_5_link"

    def test_hand_keypoint_uses_primary_physical_link(self) -> None:
        names = list(dict.fromkeys(aliases[-1] for aliases in LTE_FULLBODY_KEYPOINT_LINKS.values()))
        for part_name in ("left_heel", "left_toe", "right_heel", "right_toe", "left_hand"):
            names.extend(body for body in CONTACT_BODY_NAMES_BY_PART[part_name] if body not in names)
        names = np.asarray(names)
        positions = np.zeros((1, len(names), 3), dtype=np.float64)
        positions[0, list(names).index(CONTACT_BODY_NAMES_BY_PART["left_hand"][0]), 0] = 1.0
        positions[0, list(names).index(CONTACT_BODY_NAMES_BY_PART["left_hand"][1]), 0] = 3.0
        motion = {
            "body_names": names,
            "body_pos_w": positions,
        }

        keypoints = _semantic_keypoints_from_motion(motion)

        np.testing.assert_allclose(keypoints["left_hand"][0], [1.0, 0.0, 0.0])
        assert TARGET_LINK_GROUPS["left_hand"] == CONTACT_BODY_NAMES_BY_PART["left_hand"]

    def test_raw_contact_aliases_resolve_sphere_hands_not_wrists(self) -> None:
        assert set(CONTACT_BODY_NAMES_BY_PART["left_hand"]).issubset(PART_ALIASES["lh"])
        assert set(CONTACT_BODY_NAMES_BY_PART["right_hand"]).issubset(PART_ALIASES["rh"])
        assert "left_wrist_yaw_link" not in PART_ALIASES["lh"]
        assert "right_wrist_yaw_link" not in PART_ALIASES["rh"]
