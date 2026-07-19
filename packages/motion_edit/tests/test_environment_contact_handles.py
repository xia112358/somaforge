from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.generation.lte_fullbody import _environment_contact_anchor_arrays
from motion_edit.generation.pyroki_fullbody_ik import TARGET_LINK_GROUPS, _environment_contacts_from_lte
from motion_edit.generation.pyroki_trajectory_optimizer import (
    EnvironmentContactAnchors,
    _edited_environment_contacts,
    _edited_foot_pose_episodes,
    _environment_contact_constraint_samples,
)
from motion_edit.physics_retarget.whole_trajectory_projector import WholeTrajectoryPhysicsProjector


class EnvironmentContactHandleTests(unittest.TestCase):
    def test_edited_foot_pose_episode_merges_heel_toe_and_foot_fragments(self) -> None:
        contacts = EnvironmentContactAnchors(
            anchor_ids=("left_heel_a", "left_toe_a", "left_foot_a", "right_toe_short"),
            semantic_names=("left_heel", "left_toe", "left_foot", "right_toe"),
            start_frames=np.asarray([5, 20, 42, 0]),
            end_frames=np.asarray([15, 40, 50, 5]),
            representative_frames=np.asarray([9, 29, 45, 2]),
            source_position_w=np.zeros((4, 3), dtype=np.float64),
            target_position_w=np.asarray(
                [
                    [0.0, 0.0, -0.1],
                    [0.0, 0.0, -0.1],
                    [0.0, 0.0, -0.1],
                    [0.0, 0.0, -0.1],
                ]
            ),
            edited=np.ones(4, dtype=bool),
            link_groups=[np.asarray([0], dtype=np.int32) for _ in range(4)],
        )

        episodes = _edited_foot_pose_episodes(contacts, frames=60)

        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].side, "left")
        self.assertEqual((episodes[0].start_frame, episodes[0].end_frame), (5, 50))
        self.assertEqual(episodes[0].anchor_ids, ("left_heel_a", "left_toe_a", "left_foot_a"))
        np.testing.assert_allclose(episodes[0].translation_w, [0.0, 0.0, -0.1])

    def test_physics_retarget_rejects_legacy_robot_part_handle_lte(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lte_path = Path(tmp) / "legacy_lte.npz"
            np.savez(lte_path, left_hand=np.zeros((2, 3), dtype=np.float64))
            with self.assertRaisesRegex(ValueError, "environment contact anchors"):
                WholeTrajectoryPhysicsProjector(lte_path=lte_path)

    def test_same_robot_body_fragments_become_one_environment_episode(self) -> None:
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
                surface_origin=[1.0, 0.0, 1.2],
                surface_normal=[-1.0, 0.0, 0.0],
                surface_tangent_u=[0.0, 1.0, 0.0],
                surface_tangent_v=[0.0, 0.0, 1.0],
                surface_coordinates={"u": 0.0, "v": 0.0},
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
                surface_origin=[1.0, 0.0, 1.2],
                surface_normal=[-1.0, 0.0, 0.0],
                surface_tangent_u=[0.0, 1.0, 0.0],
                surface_tangent_v=[0.0, 0.0, 1.0],
                surface_coordinates={"u": 0.4, "v": 0.0},
            ),
        ]
        edits = [
            ContactAnchorEditRecord(
                edit_id=f"move_{suffix}",
                motion_id="demo",
                anchor_id=f"left_hand_wall_{suffix}",
                body="left_hand",
                old_world_position=old,
                new_world_position=[old[0], old[1] + 0.2, old[2]],
                affected_frames=frames,
            )
            for suffix, old, frames in (
                ("a", [1.0, 0.0, 1.2], [1, 5]),
                ("b", [1.0, 0.4, 1.2], [6, 10]),
            )
        ]

        arrays = _environment_contact_anchor_arrays(
            graph=SimpleNamespace(anchors=anchors),
            edits=edits,
            keypoints={"left_hand": np.zeros((10, 3), dtype=np.float64)},
            n_frames=10,
        )

        self.assertEqual(arrays["environment_contact_anchor_schema"].item(), "motion_edit_contact_episode_trajectory_v1")
        self.assertEqual(len(arrays["environment_contact_anchor_ids"]), 1)
        self.assertEqual(arrays["environment_contact_anchor_start_frames"].tolist(), [1])
        self.assertEqual(arrays["environment_contact_anchor_end_frames"].tolist(), [10])
        self.assertEqual(arrays["environment_contact_anchor_representative_frames"].tolist(), [5])
        np.testing.assert_allclose(
            arrays["environment_contact_anchor_target_position_w"]
            - arrays["environment_contact_anchor_source_position_w"],
            [[0.0, 0.2, 0.0]],
        )
        self.assertEqual(arrays["environment_contact_anchor_edited"].tolist(), [True])
        self.assertIn("environment_contact_anchor_contact_source_trajectory_w", arrays)
        self.assertIn("environment_contact_anchor_contact_target_trajectory_w", arrays)

    def test_pyroki_adapter_preserves_anchor_identity_and_environment_positions(self) -> None:
        first_hand_link = TARGET_LINK_GROUPS["left_hand"][0]
        target_hand_trajectory = np.asarray(
            [[0.1 + 0.01 * frame, 0.0, 1.0] for frame in range(8)],
            dtype=np.float64,
        )
        lte = {
            "left_hand": target_hand_trajectory,
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

        hard_contacts = _edited_environment_contacts(contacts)
        self.assertIsNotNone(hard_contacts)
        assert hard_contacts is not None
        self.assertEqual(hard_contacts.anchor_ids, ("contact_a",))
        self.assertEqual(hard_contacts.semantic_names, ("left_hand",))
        self.assertEqual(hard_contacts.representative_frames.tolist(), [1])
        np.testing.assert_allclose(hard_contacts.target_position_w, [[0.1, 0.0, 1.0]])
        np.testing.assert_allclose(hard_contacts.target_trajectory_w[0], target_hand_trajectory)
        np.testing.assert_allclose(
            hard_contacts.source_trajectory_w[0, :4],
            target_hand_trajectory[:4] - np.asarray([0.1, 0.0, 0.0]),
        )

        sample_ids, sample_frames, sample_source, sample_target, sample_groups = (
            _environment_contact_constraint_samples(hard_contacts)
        )
        self.assertEqual(sample_ids, ("contact_a",) * 4)
        self.assertEqual(sample_frames.tolist(), [0, 1, 2, 3])
        np.testing.assert_allclose(sample_source, target_hand_trajectory[:4] - [0.1, 0.0, 0.0])
        np.testing.assert_allclose(sample_target, target_hand_trajectory[:4])
        self.assertEqual(len(sample_groups), 4)


if __name__ == "__main__":
    unittest.main()
