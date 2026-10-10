import numpy as np
import pytest
from motion_edit.generation.stationary_compaction import compact_timeline, remap_retained_interval, compact_qpos


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


def test_soft_join_preserves_clock_and_joins_real_exit_pose():
    q = np.zeros((60, 8), dtype=np.float32)
    q[:, 3] = 1
    q[:, 0] = np.arange(60)*.001
    q[35:, 7] = .4
    out, frames, _, seams, joins = compact_qpos(q, [(19, 39)], blend_frames=8)
    assert len(out) == 40
    np.testing.assert_array_equal(out[:12], q[:12])
    np.testing.assert_array_equal(out[20:], q[40:])
    np.testing.assert_array_equal(out[12], q[12])
    np.testing.assert_array_equal(out[19], q[39])
    assert np.max(np.abs(np.diff(out[:, 7]))) < .4
    assert joins[0]['right_source_frames'] == list(range(32, 40))
    assert joins[0]['contact_audit_required'] is True
    np.testing.assert_array_equal(seams, [20])


def test_soft_join_normalizes_antipodal_quaternions():
    q = np.zeros((60, 7)); q[:, 3] = 1; q[30:, 3] = -1
    out, *_ = compact_qpos(q, [(19, 39)], blend_frames=8)
    np.testing.assert_allclose(np.linalg.norm(out[:, 3:7], axis=-1), 1)
    assert np.isfinite(out).all()


def test_soft_join_rejects_window_crossing_another_cut():
    q = np.zeros((60, 7)); q[:, 3] = 1
    with pytest.raises(ValueError, match='overlap|removed'):
        compact_qpos(q, [(19, 29), (33, 43)], blend_frames=8)
