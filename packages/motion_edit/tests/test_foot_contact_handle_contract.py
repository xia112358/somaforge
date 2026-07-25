from __future__ import annotations

from types import SimpleNamespace

import numpy as np

import motion_edit.generation  # noqa: F401 - installs foot handle contract
from motion_edit.contact.schema import ContactAnchorEditRecord, ContactAnchorRecord
from motion_edit.contact_laplacian.schema import BatchContactLaplacianConfig
from motion_edit.generation import lte_fullbody


def test_split_patch_roles_drive_ankle_and_toe_semantics() -> None:
    frame_count = 4
    keypoints = {
        "left_ankle": np.zeros((frame_count, 3), dtype=np.float64),
        "left_foot": np.tile(
            np.asarray([[0.2, 0.0, 0.0]], dtype=np.float64),
            (frame_count, 1),
        ),
    }
    heel_anchor = ContactAnchorRecord(
        motion_id="motion_a",
        anchor_id="heel_anchor",
        # Split anchors intentionally retain the original canonical foot body.
        body="left_foot",
        start_frame=0,
        end_frame=2,
        metadata={
            "patch_role": "heel",
            "foot_subcontact": {
                "name": "heel",
                "raw_shape_ids": [39, 40],
            },
        },
    )
    sole_anchor = ContactAnchorRecord(
        motion_id="motion_a",
        anchor_id="sole_anchor",
        body="left_foot",
        start_frame=2,
        end_frame=4,
        metadata={
            "patch_role": "sole",
            "foot_subcontact": {
                "name": "sole",
                "heel": {"raw_shape_ids": [39, 40]},
                "toe": {"raw_shape_ids": [43, 44, 45]},
            },
        },
    )
    heel_edit = ContactAnchorEditRecord(
        edit_id="raise_heel",
        motion_id="motion_a",
        anchor_id="heel_anchor",
        body="left_foot",
        delta_world=[0.0, 0.0, 0.1],
        affected_frames=[0, 2],
    )
    graph = SimpleNamespace(anchors=[heel_anchor, sole_anchor])
    config = BatchContactLaplacianConfig(
        edit_contact_weight=1000.0,
        fixed_contact_weight=1000.0,
    )

    handles = lte_fullbody._contact_laplacian_handles_from_edits(
        [heel_edit],
        keypoints,
        graph=graph,
        config=config,
        source_motion=None,
    )

    edited = [handle for handle in handles if handle.kind == "edited_contact"]
    fixed = [handle for handle in handles if handle.kind == "fixed_contact"]

    assert len(edited) == 1
    assert edited[0].anchor_id == "heel_anchor"
    assert edited[0].semantic_name == "left_ankle"
    assert edited[0].body == "left_heel"
    np.testing.assert_allclose(edited[0].target_xyz[:, 2], 0.1)

    assert {handle.semantic_name for handle in fixed} == {
        "left_ankle",
        "left_foot",
    }
    assert {handle.body for handle in fixed} == {
        "left_heel",
        "left_toe",
    }
    assert all(handle.anchor_id == "sole_anchor" for handle in fixed)
    assert {handle.metadata["semantic_contact_role"] for handle in fixed} == {
        "heel",
        "toe",
    }
