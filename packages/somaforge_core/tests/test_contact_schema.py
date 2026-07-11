from __future__ import annotations

import pytest

from somaforge_core.contact_schema import (
    CONTACT_FORCE_PART_ORDER,
    decode_contact_force_provenance,
    diagnostic_contact_provenance,
    encode_contact_force_provenance,
    newton_contact_provenance,
)


def test_newton_contact_provenance_round_trip() -> None:
    metadata = newton_contact_provenance(solver_config={"nconmax": 64, "njmax": 512})
    decoded = decode_contact_force_provenance(
        encode_contact_force_provenance(metadata), context="test force reference"
    )
    assert tuple(decoded["part_order"]) == CONTACT_FORCE_PART_ORDER
    assert decoded["training_eligible"] is True
    assert decoded["solver_config_sha256"]


def test_diagnostic_contact_force_is_rejected_for_training() -> None:
    metadata = diagnostic_contact_provenance(source_backend="mujoco_prescribed")
    with pytest.raises(ValueError, match="not sourced from the Newton"):
        decode_contact_force_provenance(
            encode_contact_force_provenance(metadata), context="test force reference"
        )


def test_diagnostic_contact_force_can_be_inspected() -> None:
    metadata = diagnostic_contact_provenance(source_backend="mujoco_prescribed")
    decoded = decode_contact_force_provenance(
        encode_contact_force_provenance(metadata), context="test force reference", require_newton=False
    )
    assert decoded["training_eligible"] is False
