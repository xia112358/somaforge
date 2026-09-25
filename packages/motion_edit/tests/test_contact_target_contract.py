from __future__ import annotations

import numpy as np

from motion_edit.contact.schema import (
    ContactAnchorEditRecord,
    ContactAnchorRecord,
    ContactPatchRecord,
    ContactSurfaceRecord,
)
from motion_edit.generation.taskspace_builder import (
    build_contact_aware_taskspace_motion,
)


def test_edited_patch_uses_same_world_delta_as_semantic_handle() -> None:
    frame_count = 2
    source_motion = {
        "fps": np.asarray(50.0),
        "joint_pos": np.zeros((frame_count, 36), dtype=np.float64),
        "joint_vel": np.zeros((frame_count, 35), dtype=np.float64),
        "body_names": np.asarray(["left_ankle_roll_link"], dtype=object),
        "body_pos_w": np.tile(
            np.asarray([[[0.0, 0.0, 1.0]]], dtype=np.float64),
            (frame_count, 1, 1),
        ),
        "body_quat_w": np.tile(
            np.asarray([[[1.0, 0.0, 0.0, 0.0]]], dtype=np.float64),
            (frame_count, 1, 1),
        ),
    }
    anchor = ContactAnchorRecord(
        motion_id="motion_a",
        anchor_id="left_toe_anchor",
        body="left_toe",
        start_frame=0,
        end_frame=frame_count,
        surface_id="raised_top",
    )
    patch = ContactPatchRecord(
        motion_id="motion_a",
        patch_id="left_toe_patch",
        body="left_toe",
        start_frame=0,
        end_frame=frame_count,
        anchor_id="left_toe_anchor",
        link_names=["left_ankle_roll_link"],
        newton_body_label="left_ankle_roll_link",
        newton_shape_labels=["left_toe_collision"],
        robot_points_local=[[0.14, 0.0, -0.95]],
        robot_normals_local=[[0.0, 0.0, -1.0]],
        robot_binding_backend="newton_mjwarp",
        robot_binding_source="newton_raw_contact",
    )
    # The source patch is at z=0.05. The target plane is at z=0.10. A UV
    # projection would move it by only 0.05, while the motion edit requires the
    # same +0.10 displacement used by the semantic Laplacian handle.
    surface = ContactSurfaceRecord(
        motion_id="motion_a",
        surface_id="raised_top",
        object_id="box",
        surface_type="box_face",
        origin=[0.0, 0.0, 0.10],
        normal=[0.0, 0.0, 1.0],
        tangent_u=[1.0, 0.0, 0.0],
        tangent_v=[0.0, 1.0, 0.0],
    )
    edit = ContactAnchorEditRecord(
        edit_id="raise_toe",
        motion_id="motion_a",
        anchor_id="left_toe_anchor",
        body="left_toe",
        delta_world=[0.0, 0.0, 0.10],
        affected_frames=[0, frame_count],
        surface_id="raised_top",
    )

    spec = build_contact_aware_taskspace_motion(
        motion_id="motion_a",
        source_motion=source_motion,
        semantic_names=("left_foot",),
        semantic_targets_w=np.zeros((frame_count, 1, 3), dtype=np.float64),
        patches=[patch],
        anchors=[anchor],
        surfaces=[surface],
        edits=[edit],
    )

    assert len(spec.contacts) == 1
    contact = spec.contacts[0]
    assert contact.target_uv is None
    np.testing.assert_allclose(
        contact.resolved_target_points_w()[:, 0],
        np.asarray([[0.14, 0.0, 0.15], [0.14, 0.0, 0.15]]),
        atol=1.0e-9,
    )
    assert contact.metadata["target_contract"] == (
        "source_patch_world_plus_edit_delta_world"
    )
    assert contact.metadata["authoritative_delta_world"] == [0.0, 0.0, 0.1]
    assert contact.metadata["target_surface_geometry"]["normal"] == surface.normal
    assert contact.metadata["target_surface_geometry"]["origin"] == surface.origin
    assert spec.metadata["semantic_patch_displacement_contract"] == (
        "same_world_delta"
    )
