from __future__ import annotations

import unittest

import numpy as np

from motion_edit.contact.schema import (
    ContactAnchorEditRecord,
    ContactAnchorRecord,
    ContactPatchRecord,
    ContactSurfaceRecord,
)
from motion_edit.generation.taskspace_builder import build_contact_aware_taskspace_motion


class ContactAwareTaskspaceBuilderTests(unittest.TestCase):
    def test_edited_patch_translates_in_surface_uv_and_source_q_is_weak_reference(self) -> None:
        frame_count = 3
        source_motion = {
            "fps": np.asarray(50.0),
            "joint_pos": np.zeros((frame_count, 36), dtype=np.float64),
            "joint_vel": np.zeros((frame_count, 35), dtype=np.float64),
            "body_names": np.asarray(["left_ankle_roll_link"], dtype=object),
            "body_pos_w": np.tile(np.asarray([[[0.0, 0.0, 1.0]]]), (frame_count, 1, 1)),
            "body_quat_w": np.tile(np.asarray([[[1.0, 0.0, 0.0, 0.0]]]), (frame_count, 1, 1)),
        }
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=frame_count,
            world_position=[0.05, 0.0, 0.0],
            surface_id="box_top",
            surface_coordinates={"u": 0.05, "v": 0.0},
        )
        patch = ContactPatchRecord(
            motion_id="motion_a",
            patch_id="anchor_lf_patch",
            body="left_foot",
            start_frame=0,
            end_frame=frame_count,
            patch_type="foot",
            link_names=["left_ankle_roll_link"],
            anchor_id="anchor_lf",
            newton_body_label="/World/envs/env_0/Robot/left_ankle_roll_link",
            newton_shape_labels=["heel", "toe"],
            robot_points_local=[[0.0, 0.0, -1.0], [0.1, 0.0, -1.0]],
            robot_normals_local=[[0.0, 0.0, -1.0], [0.0, 0.0, -1.0]],
            robot_binding_backend="newton_mjwarp",
            robot_binding_source="newton_raw_contact",
        )
        surface = ContactSurfaceRecord(
            motion_id="motion_a",
            surface_id="box_top",
            object_id="box",
            surface_type="box_face",
            origin=[0.0, 0.0, 0.0],
            normal=[0.0, 0.0, 1.0],
            tangent_u=[1.0, 0.0, 0.0],
            tangent_v=[0.0, 1.0, 0.0],
        )
        edit = ContactAnchorEditRecord(
            edit_id="edit_lf",
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            tangent_delta=[0.2, 0.0],
            delta_world=[0.2, 0.0, 0.0],
            affected_frames=[0, frame_count],
            surface_id="box_top",
        )
        semantic_targets = np.zeros((frame_count, 2, 3), dtype=np.float64)

        spec = build_contact_aware_taskspace_motion(
            motion_id="motion_a",
            source_motion=source_motion,
            semantic_names=("pelvis", "left_foot"),
            semantic_targets_w=semantic_targets,
            patches=[patch],
            anchors=[anchor],
            surfaces=[surface],
            edits=[edit],
            source_reference_weight=0.01,
            boundary_ramp_frames=1,
        )

        self.assertEqual(len(spec.contacts), 1)
        contact = spec.contacts[0]
        self.assertEqual(contact.kind, "edited_contact")
        expected_frame = np.asarray([[0.2, 0.0, 0.0], [0.3, 0.0, 0.0]], dtype=np.float64)
        np.testing.assert_allclose(contact.resolved_target_points_w()[0], expected_frame)
        self.assertTrue(np.all(spec.source_reference_weights == 0.01))
        self.assertEqual(spec.metadata["old_motion_role"], "initializer_and_weak_tie_breaker")

    def test_unedited_patch_keeps_original_world_trajectory(self) -> None:
        frame_count = 2
        source_motion = {
            "joint_pos": np.zeros((frame_count, 8), dtype=np.float64),
            "joint_vel": np.zeros((frame_count, 7), dtype=np.float64),
            "body_names": np.asarray(["left_knee_link"], dtype=object),
            "body_pos_w": np.asarray([[[0.0, 0.0, 0.5]], [[0.1, 0.0, 0.5]]], dtype=np.float64),
            "body_quat_w": np.tile(np.asarray([[[1.0, 0.0, 0.0, 0.0]]]), (frame_count, 1, 1)),
        }
        contact_pose_motion = {
            "body_names": np.asarray(["left_knee_link"], dtype=object),
            "body_pos_w": np.asarray([[[1.0, 0.0, 0.5]], [[1.2, 0.0, 0.5]]], dtype=np.float64),
            "body_quat_w": np.tile(
                np.asarray([[[1.0, 0.0, 0.0, 0.0]]]),
                (frame_count, 1, 1),
            ),
        }
        anchor = ContactAnchorRecord("motion_a", "anchor_lk", "left_knee", 0, frame_count)
        patch = ContactPatchRecord(
            motion_id="motion_a",
            patch_id="anchor_lk_patch",
            body="left_knee",
            start_frame=0,
            end_frame=frame_count,
            anchor_id="anchor_lk",
            link_names=["left_knee_link"],
            robot_points_local=[[0.0, 0.0, -0.1]],
            newton_shape_labels=["knee_collision"],
            robot_binding_backend="newton_mjwarp",
            robot_binding_source="newton_raw_contact",
        )

        spec = build_contact_aware_taskspace_motion(
            motion_id="motion_a",
            source_motion=source_motion,
            contact_pose_motion=contact_pose_motion,
            semantic_names=("left_knee",),
            semantic_targets_w=np.zeros((frame_count, 1, 3), dtype=np.float64),
            patches=[patch],
            anchors=[anchor],
            surfaces=[],
            edits=[],
        )

        contact = spec.contacts[0]
        self.assertEqual(contact.kind, "fixed_contact")
        np.testing.assert_allclose(
            contact.resolved_target_points_w()[:, 0],
            np.asarray([[1.0, 0.0, 0.4], [1.2, 0.0, 0.4]], dtype=np.float64),
        )


if __name__ == "__main__":
    unittest.main()
