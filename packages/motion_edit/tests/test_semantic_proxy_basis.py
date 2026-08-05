from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from motion_edit.generation.semantic_proxy_basis import (
    reuse_proportional_semantic_proxy,
)


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        damping=1.0e-4,
        edit_contact_weight=1000.0,
        fixed_contact_weight=1000.0,
        temporal_laplacian_weight=40.0,
        body_relative_weight=10.0,
        q_prior_weight=0.02,
        q_smooth_weight=0.0,
        mesh_laplacian_weight=1.0,
    )


def _edit(anchor_id: str, delta: list[float]) -> dict[str, object]:
    return {
        "anchor_id": anchor_id,
        "affected_frames": [0, 2],
        "delta_world": delta,
    }


def test_reuses_converged_proxy_for_proportional_variant(tmp_path) -> None:
    source_path = tmp_path / "source.npz"
    basis_path = tmp_path / "basis.npz"
    source_body = np.zeros((3, 2, 3), dtype=np.float64)
    offset = np.zeros((3, 3), dtype=np.float64)
    offset[:, 2] = [0.1, 0.2, 0.3]
    metadata = {
        "source_motion": str(source_path),
        "contact_laplacian_config": _config().__dict__,
        "edits": [_edit("anchor", [0.0, 0.0, 0.1])],
        "solver_metadata": {
            "iterations": [
                {
                    "accepted": True,
                    "relative_improvement": 1.0e-12,
                }
            ]
        },
    }
    np.savez_compressed(
        basis_path,
        body_pos_w=source_body + offset[:, None, :],
        body_lin_vel_w=np.zeros_like(source_body),
        keypoint_left_hand=offset,
        offset_left_hand=offset,
        motion_edit_generation_metadata=np.asarray(json.dumps(metadata)),
    )
    source_motion = {
        "fps": np.asarray([50.0]),
        "body_pos_w": source_body,
    }

    proxy, scale, reused_metadata = reuse_proportional_semantic_proxy(
        basis_path=basis_path,
        source_motion=source_motion,
        source_motion_path=source_path,
        edits=[_edit("anchor", [0.0, 0.0, -0.05])],
        config=_config(),
    )

    assert scale == pytest.approx(-0.5)
    np.testing.assert_allclose(proxy["offset_left_hand"], -0.5 * offset)
    np.testing.assert_allclose(
        proxy["body_pos_w"],
        np.repeat(-0.5 * offset[:, None, :], 2, axis=1),
    )
    assert reused_metadata["semantic_proxy_reuse"]["active"] is True


def test_rejects_nonproportional_variant(tmp_path) -> None:
    source_path = tmp_path / "source.npz"
    basis_path = tmp_path / "basis.npz"
    metadata = {
        "source_motion": str(source_path),
        "contact_laplacian_config": _config().__dict__,
        "edits": [
            _edit("first", [0.1, 0.0, 0.0]),
            _edit("second", [0.0, 0.1, 0.0]),
        ],
        "solver_metadata": {
            "iterations": [
                {
                    "accepted": True,
                    "relative_improvement": 1.0e-12,
                }
            ]
        },
    }
    np.savez_compressed(
        basis_path,
        body_pos_w=np.zeros((3, 1, 3)),
        body_lin_vel_w=np.zeros((3, 1, 3)),
        motion_edit_generation_metadata=np.asarray(json.dumps(metadata)),
    )

    with pytest.raises(ValueError, match="not proportional"):
        reuse_proportional_semantic_proxy(
            basis_path=basis_path,
            source_motion={
                "fps": np.asarray([50.0]),
                "body_pos_w": np.zeros((3, 1, 3)),
            },
            source_motion_path=source_path,
            edits=[
                _edit("first", [0.2, 0.0, 0.0]),
                _edit("second", [0.0, 0.3, 0.0]),
            ],
            config=_config(),
        )
