import numpy as np
import pytest
from motion_edit.generation.stationary_compaction import compact_timeline, remap_retained_interval


def test_certified_middle_hold_keeps_start_and_marks_seam():
    frames, mapping, seams = compact_timeline(1005, [(471, 699)])
    assert len(frames) == 777
    np.testing.assert_array_equal(frames[470:474], [470, 471, 700, 701])
    np.testing.assert_array_equal(seams, [472])
    assert mapping[699] == 471 and mapping[700] == 472
    assert remap_retained_interval(470, 700, frames) is None
    assert remap_retained_interval(700, 720, frames) == (472, 492)


def test_multiple_holds_and_final_hold():
    frames, _, seams = compact_timeline(10, [(1, 3), (7, 9)])
    np.testing.assert_array_equal(frames, [0, 1, 4, 5, 6, 7])
    np.testing.assert_array_equal(seams, [2])


@pytest.mark.parametrize('holds', [[(2, 5), (5, 7)], [(2, 10)], [(2, 2)], [(-1, 2)], [(1.5, 3)]])
def test_reject_ambiguous_holds(holds):
    with pytest.raises(ValueError):
        compact_timeline(10, holds)
