from __future__ import annotations

from pathlib import Path

import numpy as np

from motion_edit.cli import build_parser
from motion_edit.physics_retarget.target import load_newton_force_target
from somaforge_core import encode_robot_asset_json
from somaforge_core.contact_schema import (
    CONTACT_FORCE_PART_ORDER,
    encode_contact_force_provenance,
    newton_contact_provenance,
)


def test_newton_force_target_reorders_canonical_parts(tmp_path: Path) -> None:
    path = tmp_path / "target.npz"
    reverse_order = tuple(reversed(CONTACT_FORCE_PART_ORDER))
    force = np.zeros((2, 8, 3), dtype=np.float32)
    for index, part in enumerate(reverse_order):
        force[:, index, 2] = float(CONTACT_FORCE_PART_ORDER.index(part) + 1)
    np.savez(
        path,
        contact_force_part_w=force,
        contact_force_part_mask=force[..., 2] > 0.0,
        contact_force_part_order=np.asarray(reverse_order),
        joint_pos=np.zeros((2, 36), dtype=np.float32),
        robot_asset_json=np.asarray(encode_robot_asset_json()),
        contact_force_provenance_json=np.asarray(
            encode_contact_force_provenance(
                newton_contact_provenance(solver_config={"nconmax": 64, "control_decimation": 4})
            )
        ),
    )

    target = load_newton_force_target(path)

    np.testing.assert_array_equal(target.force_w[0, :, 2], np.arange(1, 9))
    np.testing.assert_array_equal(target.mask, True)
    assert target.joint_pos is not None


def test_force_retarget_cli_is_retired() -> None:
    import pytest
    with pytest.raises(SystemExit):
        build_parser().parse_args(["force-retarget"])
