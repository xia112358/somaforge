import numpy as np
import pytest
from motion_edit.generation.free_surface_reference import reference_offsets


def test_height_and_uv_translation_preserve_window_boundaries():
    frames=np.arange(6)
    offsets=reference_offsets(frames,dict(base=[.01,0,.07],windows=[dict(frames=[2,4],delta=[0,.05,0])]))
    np.testing.assert_allclose(offsets[:,0],.01)
    np.testing.assert_allclose(offsets[:,2],.07)
    np.testing.assert_array_equal(offsets[:,1],[0,0,.05,.05,0,0])


def test_missing_or_invalid_translation_fails():
    with pytest.raises(ValueError):reference_offsets([0],dict(base=[0,0,float('nan')]))
    with pytest.raises(ValueError):reference_offsets([0],dict(base=[0,0,0],windows=[dict(frames=[2,1],delta=[0,0,0])]))


def test_original_zero_offset_is_unchanged():
    np.testing.assert_array_equal(reference_offsets([1,4,5],[0,0,0]),np.zeros((3,3)))
