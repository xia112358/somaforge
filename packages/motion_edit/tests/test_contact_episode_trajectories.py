from __future__ import annotations

import numpy as np
import pytest

from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.generation.contact_episodes import build_contact_episode_trajectories


def _anchor(anchor_id: str, body: str, start: int, end: int, x: float) -> ContactAnchorRecord:
    return ContactAnchorRecord(
        motion_id="demo",
        anchor_id=anchor_id,
        body=body,
        start_frame=start,
        end_frame=end,
        world_position=[x, 0.0, 0.0],
        object_id="platform",
        surface_id="platform_top",
        surface_origin=[0.0, 0.0, 0.0],
        surface_normal=[0.0, 0.0, 1.0],
        surface_tangent_u=[1.0, 0.0, 0.0],
        surface_tangent_v=[0.0, 1.0, 0.0],
        surface_coordinates={"u": x, "v": 0.0},
    )


def _edit(anchor: ContactAnchorRecord, delta: list[float]) -> ContactAnchorEditRecord:
    old = np.asarray(anchor.world_position, dtype=np.float64)
    return ContactAnchorEditRecord(
        edit_id=f"move::{anchor.anchor_id}",
        motion_id=anchor.motion_id,
        anchor_id=anchor.anchor_id,
        body=anchor.body,
        old_world_position=old.tolist(),
        new_world_position=(old + np.asarray(delta)).tolist(),
        affected_frames=[anchor.start_frame, anchor.end_frame],
        surface_id=anchor.surface_id,
    )


def test_heel_and_toe_fragments_produce_one_force_bound_foot_episode() -> None:
    heel = _anchor("heel", "left_heel", 2, 6, 0.0)
    toe = _anchor("toe", "left_toe", 5, 9, 0.2)
    force = np.zeros((12, 2, 3), dtype=np.float64)
    force[:, :, 2] = 10.0
    mask = np.zeros((12, 2), dtype=bool)
    mask[2:6, 0] = True
    mask[5:9, 1] = True
    position = np.zeros_like(force)
    position[:, 0, 0] = 0.0
    position[:, 1, 0] = 0.2
    episodes = build_contact_episode_trajectories(
        anchors=[heel, toe],
        edits=[_edit(heel, [0.0, 0.1, 0.0]), _edit(toe, [0.0, 0.1, 0.0])],
        keypoints={"left_foot": np.zeros((12, 3), dtype=np.float64)},
        n_frames=12,
        contact_motion={
            "contact_force_part_order": np.asarray(["LHEE", "LTOE"]),
            "contact_force_part_w": force,
            "contact_force_part_mask": mask,
            "contact_force_part_position_w": position,
            "contact_force_part_position_valid": mask,
        },
    )

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.body == "left_foot"
    assert (episode.start_frame, episode.end_frame) == (2, 9)
    assert episode.member_anchor_ids == ("heel", "toe")
    assert episode.member_edit_ids == ("move::heel", "move::toe")
    expected_delta = np.broadcast_to([0.0, 0.1, 0.0], episode.source_semantic_xyz.shape)
    np.testing.assert_allclose(episode.target_semantic_xyz - episode.source_semantic_xyz, expected_delta)
    np.testing.assert_allclose(episode.target_contact_xyz - episode.source_contact_xyz, expected_delta)
    np.testing.assert_allclose(episode.contact_force_w[3], [0.0, 0.0, 20.0])
    assert episode.contact_mask.all()


def test_divergent_fragment_deltas_are_rejected_at_episode_boundary() -> None:
    first = _anchor("a", "left_hand", 0, 5, 0.0)
    second = _anchor("b", "left_hand", 5, 10, 0.1)
    with pytest.raises(ValueError, match="divergent fragment edits"):
        build_contact_episode_trajectories(
            anchors=[first, second],
            edits=[_edit(first, [0.0, 0.1, 0.0]), _edit(second, [0.0, 0.2, 0.0])],
            keypoints={"left_hand": np.zeros((10, 3), dtype=np.float64)},
            n_frames=10,
        )


def test_one_rigid_surface_transform_allows_position_dependent_yaw_deltas() -> None:
    first = _anchor("a", "left_hand", 0, 15, 0.0)
    second = _anchor("b", "left_hand", 15, 30, 0.1)
    edits = [_edit(first, [0.0, 0.001, 0.0]), _edit(second, [0.0, 0.002, 0.0])]
    transform = {
        "source_surface": {"surface_id": "platform_top"},
        "target_surface": {"surface_id": "platform_top_yaw"},
    }
    edits = [
        ContactAnchorEditRecord(
            **{**edit.__dict__, "metadata": {"surface_transform": transform}}
        )
        for edit in edits
    ]

    episodes = build_contact_episode_trajectories(
        anchors=[first, second],
        edits=edits,
        keypoints={"left_hand": np.zeros((30, 3), dtype=np.float64)},
        n_frames=30,
    )

    assert len(episodes) == 1
    np.testing.assert_allclose(episodes[0].delta_world, [0.0, 0.0015, 0.0])


def test_already_edited_semantic_trajectory_is_not_translated_twice() -> None:
    anchor = _anchor("hand", "left_hand", 1, 5, 0.0)
    target = np.zeros((6, 3), dtype=np.float64)
    target[1:5, 2] = 0.1
    episodes = build_contact_episode_trajectories(
        anchors=[anchor],
        edits=[_edit(anchor, [0.0, 0.0, 0.1])],
        keypoints={"left_hand": target},
        n_frames=6,
        contact_positions_are_target=True,
    )

    assert len(episodes) == 1
    np.testing.assert_allclose(episodes[0].source_semantic_xyz, 0.0)
    np.testing.assert_allclose(episodes[0].target_semantic_xyz[:, 2], 0.1)
