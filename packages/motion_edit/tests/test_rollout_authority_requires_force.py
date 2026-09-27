from __future__ import annotations

from pathlib import Path

import numpy as np
from somaforge_core.robot_assets import encode_robot_asset_json
import pytest

import motion_edit.generation  # noqa: F401
from motion_edit.contact.plans import ContactEditPlan
from motion_edit.generation import contact_aware_preview as preview
from motion_edit.generation.rollout_authority import _load_source_motion


def test_nonforce_plan_source_is_not_accepted_as_geometry_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = tmp_path / "kinematic_reference_only.npz"
    original.touch()
    plan = ContactEditPlan(
        plan_id="plan",
        source_motion_id="motion",
        source_motion_path=str(original),
        source_contact_layer="contact/source",
        status="validated",
        edits=[],
        metadata={},
    )
    nonforce = {
        "robot_asset_json": np.asarray(encode_robot_asset_json()),
        "fps": np.asarray(50.0),
        "joint_pos": np.zeros((1, 8), dtype=np.float64),
        "joint_vel": np.zeros((1, 7), dtype=np.float64),
        "joint_names": np.asarray(["joint_0"], dtype=object),
        "body_names": np.asarray(["pelvis"], dtype=object),
        "body_pos_w": np.zeros((1, 1, 3), dtype=np.float64),
        "body_quat_w": np.asarray([[[1.0, 0.0, 0.0, 0.0]]]),
    }
    monkeypatch.setattr(preview, "_load_motion_npz", lambda path: nonforce)

    with pytest.raises(ValueError, match="sole reference"):
        _load_source_motion(plan, preview)
