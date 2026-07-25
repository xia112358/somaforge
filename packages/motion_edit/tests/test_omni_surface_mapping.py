from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from motion_edit.generation.omni_surface_mapping import _target_object_points_from_plan


def _surface(surface_id: str, z: float) -> dict:
    return {
        "surface_id": surface_id,
        "object_id": "box",
        "origin": [0.0, 0.0, z],
        "normal": [0.0, 0.0, 1.0],
        "tangent_u": [1.0, 0.0, 0.0],
        "tangent_v": [0.0, 1.0, 0.0],
        "bounds": {"u": [-0.5, 0.5], "v": [-0.5, 0.5]},
    }


def test_height_surface_follow_moves_box_top_but_not_ground() -> None:
    points = np.asarray(
        [
            [0.1, 0.1, 0.70],
            [-0.2, 0.2, 0.70],
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 0.70],
        ],
        dtype=np.float64,
    )
    plan = SimpleNamespace(
        surface_transforms=[
            {
                "transform_id": "height_110",
                "source_surface": _surface("box_1p0_top", 0.70),
                "target_surface": _surface("box_1p1_top", 0.77),
                "translation_world": [0.0, 0.0, 0.07],
            }
        ]
    )

    target, warnings = _target_object_points_from_plan(plan, points)

    np.testing.assert_allclose(target[:2], points[:2] + [0.0, 0.0, 0.07])
    np.testing.assert_allclose(target[2], points[2])
    np.testing.assert_allclose(target[3], points[3])
    assert warnings == []


def test_surface_follow_preserves_uv_for_rotated_target_basis() -> None:
    points = np.asarray([[0.2, 0.1, 0.0]], dtype=np.float64)
    source = _surface("source", 0.0)
    target = _surface("target", 1.0)
    target["tangent_u"] = [0.0, 1.0, 0.0]
    target["tangent_v"] = [-1.0, 0.0, 0.0]
    plan = SimpleNamespace(
        surface_transforms=[
            {
                "transform_id": "rotate_surface",
                "source_surface": source,
                "target_surface": target,
            }
        ]
    )

    mapped, warnings = _target_object_points_from_plan(plan, points)

    np.testing.assert_allclose(mapped[0], [-0.1, 0.2, 1.0], atol=1.0e-9)
    assert warnings == []


def test_translation_only_plan_keeps_legacy_global_behavior() -> None:
    points = np.asarray([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]], dtype=np.float64)
    plan = SimpleNamespace(
        surface_transforms=[
            {
                "transform_id": "legacy_translate",
                "translation_world": [0.0, 0.0, 0.1],
            }
        ]
    )

    mapped, warnings = _target_object_points_from_plan(plan, points)

    np.testing.assert_allclose(mapped, points + [0.0, 0.0, 0.1])
    assert warnings == []
