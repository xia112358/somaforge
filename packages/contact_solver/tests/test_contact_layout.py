from types import SimpleNamespace

import torch

from contact_solver.contact_layout import relative_layout_statistics, relative_plan_objective
from generator.next_interaction_heightmap import HEIGHTMAP_ROWS as R, HEIGHTMAP_COLS as C
from generator.planned_contact_predictor import relative_contact_layout_loss


def example(shift=0, wrong=False):
    logits = torch.full((1, 6, R*C), -15.)
    a = 25*C+20
    b = a+5
    logits[0, 0, a+shift] = 15
    logits[0, 1, b+shift+(4 if wrong else 0)] = 15
    prediction = SimpleNamespace(location_logits=logits.requires_grad_(),
        role_logits=torch.zeros(1, 6, 4, requires_grad=True),
        contact=torch.tensor([[True, True, False, False, False, False]]),
        role=torch.tensor([[1, 1, 0, 0, 0, 0]]))
    target = {'role': prediction.role, 'contact_cell': torch.tensor([[a, b, 0, 0, 0, 0]]),
              'contact_cell_valid': prediction.contact}
    return prediction, target, torch.zeros(1, R, C)


def test_planner_penalizes_future_only_translation_and_independent_limb_shift():
    a, label, terrain = example()
    b, _, _ = example(shift=3*C+7)
    wrong, _, _ = example(shift=3*C+7, wrong=True)
    first = relative_plan_objective(a, label, terrain)[0]
    moved = relative_plan_objective(b, label, terrain)[0]
    broken = relative_plan_objective(wrong, label, terrain)[0]
    assert moved > first + 5
    assert broken > first + 5
    broken.sum().backward()
    assert torch.isfinite(wrong.location_logits.grad).all()
    assert wrong.location_logits.grad.abs().sum() > 0


def test_translated_layout_cannot_change_observed_height_levels():
    prediction, label, terrain = example(shift=3*C)
    terrain[:, 28, :] = .9
    _, metrics = relative_plan_objective(prediction, label, terrain)
    assert metrics['plan_location_loss'] > 5


def test_no_visible_contact_positions_have_zero_location_loss_and_finite_gradient():
    prediction, label, terrain = example()
    label['contact_cell_valid'][:] = False
    loss, metrics = relative_plan_objective(prediction, label, terrain)
    assert metrics['plan_location_loss'] == 0
    loss.sum().backward()
    assert torch.isfinite(prediction.location_logits.grad).all()


def test_relative_statistics_translation_and_missing_witness_are_separate():
    target = torch.tensor([[[0., 0., 0.], [.2, .1, 0.]]])
    actual = target + torch.tensor([2., -3., 0.])
    error, shift, count = relative_layout_statistics(actual, target, torch.ones(1, 2, dtype=torch.bool))
    torch.testing.assert_close(error, torch.zeros(1), atol=1e-12, rtol=0)
    torch.testing.assert_close(shift, torch.tensor([[2., -3.]]))
    assert count == 2
    _, _, missing = relative_layout_statistics(actual, target, torch.zeros(1, 2, dtype=torch.bool))
    assert missing == 0


def test_layout_runs_one_fk_for_entire_batch_and_matches_known_gradient():
    class FK:
        calls = 0
        def link_poses(self, q, names):
            self.calls += 1
            pos = torch.stack([q[:, :3] + torch.stack((q[:, 7+i], q[:, 9]*0, q[:, 9]*0), -1)
                               for i in range(len(names))], 1)
            return pos, torch.eye(3).expand(len(q), len(names), 3, 3)
    fk = FK(); q = torch.zeros(2, 36, requires_grad=True)
    target = torch.zeros(2, 6, 3); target[:, 1, 0] = .3
    active = torch.tensor([[True, True, False, False, False, False]]).expand(2, -1)
    surface = torch.zeros(2, 6, dtype=torch.long)
    rows = [[({'part': p, 'surface': 0, 'body_name': str(p), 'dist': 0,
              'position_w': [p*.2, 0, 0]}, None) for p in (0, 1)] for _ in range(2)]
    loss, _ = relative_contact_layout_loss(SimpleNamespace(fk=fk), q, target, active, surface, rows)
    assert fk.calls == 1
    torch.testing.assert_close(loss, torch.full((2,), .1**2/2/.04**2))
    loss.sum().backward()
    torch.testing.assert_close(q.grad[:, 0], torch.full((2,), -.1/.04**2))
    torch.testing.assert_close(q.grad[:, 7], torch.zeros(2))
    torch.testing.assert_close(q.grad[:, 8], torch.full((2,), -.1/.04**2))
