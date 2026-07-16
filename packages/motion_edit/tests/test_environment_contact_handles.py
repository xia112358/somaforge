from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.generation.lte_fullbody import _environment_contact_anchor_arrays
from motion_edit.generation.pyroki_fullbody_ik import TARGET_LINK_GROUPS, _environment_contacts_from_lte
from motion_edit.physics_retarget.whole_trajectory_projector import WholeTrajectoryPhysicsProjector


class EnvironmentContactHandleTests(unittest.TestCase):
    def test_physics_retarget_rejects_legacy_robot_part_handle_lte(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lte_path = Path(tmp) / "legacy_lte.npz"
            np.savez(lte_path, left_hand=np.zeros((2, 3), dtype=np.float64))
            with self.assertRaisesRegex(ValueError, "environment contact anchors"):
                WholeTrajectoryPhysicsProjector(lte_path=lte_path)

    def test_same_robot_body_contacts_remain_separate_environment_handles(self) -> None:
        anchors = [
            ContactAnchorRecord(
                motion_id="demo",
                anchor_id="left_hand_wall_a",
                body="left_hand",
                start_frame=1,
                end_frame=5,
                world_position=[1.0, 0.0, 1.2],
                object_id="wall",
                surface_id="wall_front",
            ),
            ContactAnchorRecord(
                motion_id="demo",
                anchor_id="left_hand_wall_b",
                body="left_hand",
                start_frame=6,
                end_frame=10,
                world_position=[1.0, 0.4, 1.2],
                object_id="wall",
                surface_id="wall_front",
            ),
        ]
        edit = ContactAnchorEditRecord(
            edit_id="move_wall_a",
            motion_id="demo",
            anchor_id="left_hand_wall_a",
            body="left_hand",
            old_world_position=[1.0, 0.0, 1.2],
            new_world_position=[1.0, 0.2, 1.2],
            affected_frames=[1, 5],
        )

        arrays = _environment_contact_anchor_arrays(
            graph=SimpleNamespace(anchors=anchors),
            edits=[edit],
            keypoints={"left_hand": np.zeros((10, 3), dtype=np.float64)},
            n_frames=10,
        )

        self.assertEqual(arrays["environment_contact_anchor_ids"].tolist(), ["left_hand_wall_a", "left_hand_wall_b"])
        self.assertEqual(arrays["environment_contact_anchor_representative_frames"].tolist(), [2, 7])
        np.testing.assert_allclose(
            arrays["environment_contact_anchor_source_position_w"],
            [[1.0, 0.0, 1.2], [1.0, 0.4, 1.2]],
        )
        np.testing.assert_allclose(
            arrays["environment_contact_anchor_target_position_w"],
            [[1.0, 0.2, 1.2], [1.0, 0.4, 1.2]],
        )
        self.assertEqual(arrays["environment_contact_anchor_edited"].tolist(), [True, False])

    def test_pyroki_adapter_preserves_anchor_identity_and_environment_positions(self) -> None:
        first_hand_link = TARGET_LINK_GROUPS["left_hand"][0]
        lte = {
            "environment_contact_anchor_ids": np.asarray(["contact_a", "contact_b"]),
            "environment_contact_anchor_semantic_names": np.asarray(["left_hand", "left_hand"]),
            "environment_contact_anchor_start_frames": np.asarray([0, 4]),
            "environment_contact_anchor_end_frames": np.asarray([4, 8]),
            "environment_contact_anchor_representative_frames": np.asarray([1, 5]),
            "environment_contact_anchor_source_position_w": np.asarray([[0.0, 0.0, 1.0], [0.0, 0.5, 1.0]]),
            "environment_contact_anchor_target_position_w": np.asarray([[0.1, 0.0, 1.0], [0.0, 0.5, 1.0]]),
            "environment_contact_anchor_edited": np.asarray([True, False]),
        }

        contacts = _environment_contacts_from_lte(
            lte,
            n_frames=8,
            link_names=(first_hand_link,),
        )

        self.assertIsNotNone(contacts)
        assert contacts is not None
        self.assertEqual(contacts.anchor_ids, ("contact_a", "contact_b"))
        self.assertEqual(contacts.semantic_names, ("left_hand", "left_hand"))
        self.assertEqual(len(contacts.link_groups), 2)
        np.testing.assert_allclose(contacts.target_position_w[0], [0.1, 0.0, 1.0])


if __name__ == "__main__":
    unittest.main()
