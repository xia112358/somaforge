from __future__ import annotations

from somaforge_core.motion_schema import (
    G1_29DOF_JOINT_ORDER,
    decode_kinematics_provenance,
    encode_kinematics_provenance,
    newton_kinematics_provenance,
)


def test_newton_kinematics_provenance_round_trip() -> None:
    metadata = newton_kinematics_provenance(
        source_path="motion.npz",
        source_sha256="a" * 64,
        output_fps=50.0,
        body_names=["pelvis"],
    )
    decoded = decode_kinematics_provenance(
        encode_kinematics_provenance(metadata), context="test motion"
    )
    assert tuple(decoded["joint_order"]) == G1_29DOF_JOINT_ORDER
    assert decoded["body_names"] == ["pelvis"]
