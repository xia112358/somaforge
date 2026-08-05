from __future__ import annotations

import torch

from holosoma.managers.command.terms.gmvq_wbt import _tracking_gate_error, _tracking_gate_handshake


def test_tracking_gate_compares_robot_to_current_reference_frame() -> None:
    current_reference = torch.tensor([[[0.08, 0.0, 0.0], [0.0, 0.12, 0.0]]])
    robot_position = torch.zeros_like(current_reference)
    gate_indices = torch.tensor([0, 1])

    error = _tracking_gate_error(current_reference, robot_position, gate_indices)

    torch.testing.assert_close(error, torch.tensor([0.12]))


def test_tracking_gate_exposes_next_frame_before_committing_cursor() -> None:
    advance, pending = _tracking_gate_handshake(
        next_ready=torch.tensor([False, False]),
        current_ready=torch.tensor([True, False]),
        pending_next=torch.tensor([False, False]),
    )
    assert advance.tolist() == [False, False]
    assert pending.tolist() == [True, False]

    advance, pending = _tracking_gate_handshake(
        next_ready=torch.tensor([True, False]),
        current_ready=torch.tensor([True, False]),
        pending_next=pending,
    )
    assert advance.tolist() == [True, False]
    assert pending.tolist() == [False, False]
