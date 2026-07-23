from __future__ import annotations

import unittest

import numpy as np

import motion_edit.generation  # noqa: F401 - installs current Newton binding policy
from motion_edit.contact.newton_bindings import (
    bind_newton_contact_patches,
    body_local_point_to_world,
    world_point_to_body_local,
)
from motion_edit.contact.schema import ContactAnchorRecord


class NewtonContactBindingTests(unittest.TestCase):
    def test_world_body_point_roundtrip(self) -> None:
        point_w = np.asarray([1.2, -0.4, 0.7], dtype=np.float64)
        body_pos = np.asarray([1.0, -0.5, 0.5], dtype=np.float64)
        body_quat_wxyz = np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.float64)

        point_b = world_point_to_body_local(point_w, body_pos, body_quat_wxyz)
        reconstructed = body_local_point_to_world(point_b, body_pos, body_quat_wxyz)

        np.testing.assert_allclose(point_b, [0.2, 0.1, 0.2], atol=1.0e-9)
        np.testing.assert_allclose(reconstructed, point_w, atol=1.0e-9)

    def test_bind_patch_uses_newton_body_shape_and_robot_local_point(self) -> None:
        frame_count = 3
        body_pos = np.zeros((frame_count, 1, 3), dtype=np.float64)
        body_pos[:, 0, 0] = np.arange(frame_count, dtype=np.float64)
        body_quat = np.zeros((frame_count, 1, 4), dtype=np.float64)
        body_quat[..., 0] = 1.0

        point1 = np.zeros((frame_count, 1, 3), dtype=np.float64)
        point1[:, 0] = body_pos[:, 0] + np.asarray([0.0, 0.0, -0.1])

        motion = {
            "body_names": np.asarray(["left_ankle_roll_link"], dtype=object),
            "body_pos_w": body_pos,
            "body_quat_w": body_quat,
            "newton_body_labels": np.asarray(
                [
                    "/World/envs/env_0/Robot/left_ankle_roll_link",
                    "/World/ground",
                ],
                dtype=object,
            ),
            "newton_shape_labels": np.asarray(
                [
                    "/World/envs/env_0/Robot/left_ankle_roll_link/heel_collision",
                    "/World/ground/collision",
                ],
                dtype=object,
            ),
            "raw_contact_selected_env_id": np.asarray(0, dtype=np.int32),
            "raw_contact_count": np.ones(frame_count, dtype=np.int32),
            "raw_contact_shape0": np.zeros((frame_count, 1), dtype=np.int32),
            "raw_contact_shape1": np.ones((frame_count, 1), dtype=np.int32),
            "raw_contact_body0": np.zeros((frame_count, 1), dtype=np.int32),
            "raw_contact_body1": np.ones((frame_count, 1), dtype=np.int32),
            "raw_contact_point0_w": np.zeros((frame_count, 1, 3), dtype=np.float64),
            "raw_contact_point1_w": point1,
            "raw_contact_normal_w": np.tile(np.asarray([0.0, 0.0, -1.0]), (frame_count, 1, 1)),
            "raw_contact_force_w": np.tile(np.asarray([0.0, 0.0, 100.0]), (frame_count, 1, 1)),
        }
        anchor = ContactAnchorRecord(
            motion_id="motion_a",
            anchor_id="anchor_lf",
            body="left_foot",
            start_frame=0,
            end_frame=frame_count,
            world_position=[1.0, 0.0, -0.1],
        )

        patches, summary = bind_newton_contact_patches([anchor], motion, min_force_norm=10.0)

        self.assertEqual(summary["bound_patch_count"], 1)
        self.assertEqual(summary["fallback_patch_count"], 0)
        self.assertEqual(summary["raw_sample_count"], frame_count)
        self.assertEqual(len(patches), 1)

        patch = patches[0]
        self.assertEqual(patch.robot_binding_backend, "newton_mjwarp")
        self.assertEqual(patch.robot_binding_source, "newton_raw_contact")
        self.assertEqual(patch.newton_body_label, "/World/envs/env_0/Robot/left_ankle_roll_link")
        self.assertEqual(patch.newton_shape_labels, ["/World/envs/env_0/Robot/left_ankle_roll_link/heel_collision"])
        np.testing.assert_allclose(np.asarray(patch.robot_points_local), [[0.0, 0.0, -0.1]], atol=1.0e-9)
        self.assertLess(
            float(patch.metadata["newton_robot_contact_binding"]["reconstruction_error_max_m"]),
            1.0e-9,
        )

    def test_unmatched_anchor_falls_back_without_inventing_local_point(self) -> None:
        motion = {
            "body_names": np.asarray(["left_ankle_roll_link"], dtype=object),
            "body_pos_w": np.zeros((1, 1, 3), dtype=np.float64),
            "body_quat_w": np.asarray([[[1.0, 0.0, 0.0, 0.0]]], dtype=np.float64),
            "newton_body_labels": np.asarray(["/World/envs/env_0/Robot/left_ankle_roll_link"], dtype=object),
            "raw_contact_count": np.zeros(1, dtype=np.int32),
            "raw_contact_shape0": np.full((1, 1), -1, dtype=np.int32),
            "raw_contact_shape1": np.full((1, 1), -1, dtype=np.int32),
            "raw_contact_body0": np.full((1, 1), -1, dtype=np.int32),
            "raw_contact_body1": np.full((1, 1), -1, dtype=np.int32),
            "raw_contact_point0_w": np.zeros((1, 1, 3), dtype=np.float64),
            "raw_contact_point1_w": np.zeros((1, 1, 3), dtype=np.float64),
            "raw_contact_normal_w": np.zeros((1, 1, 3), dtype=np.float64),
            "raw_contact_force_w": np.zeros((1, 1, 3), dtype=np.float64),
        }
        anchor = ContactAnchorRecord("motion_a", "anchor_lh", "left_hand", 0, 1)

        patches, summary = bind_newton_contact_patches([anchor], motion)

        self.assertEqual(summary["bound_patch_count"], 0)
        self.assertEqual(patches[0].robot_binding_source, "legacy_center")
        self.assertIsNone(patches[0].robot_points_local)

    def test_heel_and_toe_bind_to_distinct_ankle_and_toe_shapes(self) -> None:
        frame_count = 1
        motion = {
            "body_names": np.asarray(
                ["right_ankle_roll_sphere_1_link", "right_ankle_roll_sphere_5_link"],
                dtype=object,
            ),
            "body_pos_w": np.asarray([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]], dtype=np.float64),
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
            "raw_contact_count": np.asarray([2], dtype=np.int32),
            "raw_contact_shape0": np.asarray([[0, 1]], dtype=np.int32),
            "raw_contact_shape1": np.asarray([[2, 2]], dtype=np.int32),
            "raw_contact_body0": np.asarray([[0, 1]], dtype=np.int32),
            "raw_contact_body1": np.asarray([[2, 2]], dtype=np.int32),
            "raw_contact_point0_w": np.zeros((frame_count, 2, 3), dtype=np.float64),
            "raw_contact_point1_w": np.asarray(
                [[[0.05, 0.0, 0.0], [1.05, 0.0, 0.0]]],
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
            ContactAnchorRecord("motion_a", "right_heel", "right_heel", 0, 1),
            ContactAnchorRecord("motion_a", "right_toe", "right_toe", 0, 1),
        ]

        patches, summary = bind_newton_contact_patches(anchors, motion)
        by_anchor = {patch.anchor_id: patch for patch in patches}

        self.assertEqual(summary["bound_patch_count"], 2)
        self.assertEqual(by_anchor["right_heel"].newton_shape_labels, ["right_heel_collision"])
        self.assertEqual(by_anchor["right_toe"].newton_shape_labels, ["right_toe_collision"])


if __name__ == "__main__":
    unittest.main()
