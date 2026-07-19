from __future__ import annotations

import unittest

from motion_edit.contact.schema import ContactAnchorRecord
from motion_edit.workbench.edit_handles import build_contact_episode_handles, contact_episode_handle_payloads


def _anchor(
    anchor_id: str,
    body: str,
    start: int,
    end: int,
    *,
    surface_id: str = "platform_top",
    object_id: str = "platform",
) -> ContactAnchorRecord:
    return ContactAnchorRecord(
        motion_id="motion_a",
        anchor_id=anchor_id,
        body=body,
        start_frame=start,
        end_frame=end,
        world_position=[float(start), 0.0, 0.0],
        object_id=object_id,
        surface_id=surface_id,
        surface_origin=[0.0, 0.0, 0.0],
        surface_normal=[0.0, 0.0, 1.0],
        surface_tangent_u=[1.0, 0.0, 0.0],
        surface_tangent_v=[0.0, 1.0, 0.0],
        surface_coordinates={"u": float(start), "v": 0.0},
        metadata={"patch_role": body.rsplit("_", 1)[-1]},
    )


class ContactEpisodeHandleTests(unittest.TestCase):
    def test_contiguous_heel_sole_toe_contacts_share_one_foot_handle(self) -> None:
        handles = build_contact_episode_handles(
            [
                _anchor("heel", "left_heel", 10, 14),
                _anchor("sole", "left_sole", 14, 18),
                _anchor("toe", "left_toe", 17, 21),
            ]
        )

        self.assertEqual(len(handles), 1)
        handle = handles[0]
        self.assertEqual(handle.body, "left_foot")
        self.assertEqual((handle.start_frame, handle.end_frame), (10, 21))
        self.assertEqual(handle.member_anchor_ids, ["heel", "sole", "toe"])
        self.assertEqual(handle.metadata["source_bodies"], ["left_heel", "left_sole", "left_toe"])

    def test_gap_surface_or_parent_body_starts_a_distinct_episode(self) -> None:
        handles = build_contact_episode_handles(
            [
                _anchor("left_a", "left_toe", 0, 4),
                _anchor("left_gap", "left_heel", 5, 8),
                _anchor("left_other_surface", "left_sole", 0, 4, surface_id="wall"),
                _anchor("right_a", "right_heel", 0, 4),
            ]
        )

        self.assertEqual(len(handles), 4)
        self.assertEqual([handle.body for handle in handles].count("left_foot"), 3)
        self.assertEqual([handle.body for handle in handles].count("right_foot"), 1)

    def test_payload_reports_tangent_offset_from_initial_episode(self) -> None:
        initial = build_contact_episode_handles([_anchor("left", "left_sole", 0, 4)])[0]
        current_anchor = _anchor("left", "left_sole", 0, 4)
        current_anchor = ContactAnchorRecord(
            **{
                **current_anchor.__dict__,
                "world_position": [0.03, -0.02, 0.0],
                "surface_coordinates": {"u": 0.03, "v": -0.02},
            }
        )
        current = build_contact_episode_handles([current_anchor])[0]

        payload = contact_episode_handle_payloads([current], [initial])[0]

        self.assertEqual(payload["initial_world_position"], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(payload["position_offset"]["u"], 0.03)
        self.assertAlmostEqual(payload["position_offset"]["v"], -0.02)
        self.assertTrue(payload["has_position_offset"])


if __name__ == "__main__":
    unittest.main()
