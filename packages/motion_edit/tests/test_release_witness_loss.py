import numpy as np
import pytest
from motion_edit.generation.release_witness_loss import compile_release_witnesses, release_residual


def test_one_sided_release_does_not_pin_or_reclassify():
    points = np.array([[0., 0., -.1], [2., 3., .1]])
    result = release_residual(points, np.zeros((2, 3)), np.array([[0., 0., 1.]]*2), np.ones(2))
    np.testing.assert_allclose(result, [-.1, 0.])


def test_empty_release_is_zero():
    values = compile_release_witnesses({}, ["foot"], 3)
    assert values[-1].sum() == 0


def test_unverified_release_fails():
    with pytest.raises(ValueError, match="provenance"):
        compile_release_witnesses({"release_witnesses": [{"frame": 0}]}, ["foot"], 3)


def test_clearance_cannot_be_below_native_margin():
    row = dict(contract="native_allocated_contact_release_witness_v1", frame=0,
               body="foot", includemargin=.017, clearance=.016, normal_w=[0.,0.,1.])
    with pytest.raises(ValueError, match="clearance"):
        compile_release_witnesses({"release_witnesses": [row]}, ["foot"], 3)


def test_refinement_only_increases_selected_penalty():
    row = dict(contract="native_allocated_contact_release_witness_v1", frame=1,
               body="foot", includemargin=.017, clearance=.019, normal_w=[0.,0.,1.],
               point_local=[0.,0.,0.], target_w=[0.,0.,.019])
    base = compile_release_witnesses({"release_witnesses": [row]}, ["foot"], 3)
    refined = compile_release_witnesses({"release_witnesses": [{**row, "penalty_multiplier": 10.}]}, ["foot"], 3)
    np.testing.assert_allclose(refined[-1], base[-1]*np.sqrt(10.))
    assert refined[-1][0].sum() == refined[-1][2].sum() == 0
