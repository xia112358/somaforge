"""The maintained trainer imports without executing scratch training scripts."""
import subprocess
import sys


def test_training_helpers_do_not_import_scratch_trainers():
    subprocess.run([sys.executable, '-c', '''
import sys
from generator.training_data import prepare, take, box_obbs, split_name
from generator.scene_workers import Workers
from generator.research.isolated_gradients import audit
assert 'train_conditioned_pose_baseline' not in sys.modules
assert 'train_first_touch_geometry' not in sys.modules
assert 'newton_scene_router_audit' not in sys.modules
assert not any(n.startswith('climb00_pipeline') for n in sys.modules)
'''], check=True)


def test_box_chart_rotation_does_not_expand_terrain():
    import numpy as np
    from generator.training_data import box_obbs
    # A 45-degree chart of a square must keep the true edge lengths.
    polygon = np.array([[[0., 1.], [1., 0.], [0., -1.], [-1., 0.]]])
    center, rotation, half, ground = box_obbs(dict(
        box_edge_start=polygon, box_origin=np.array([[0., 0., 1.]]),
        box_basis=np.eye(3)[None], box_height=np.array([1.])))
    np.testing.assert_allclose(half, [[2**-.5, 2**-.5, .5]])
    np.testing.assert_allclose(center, [[0., 0., .5]])
    np.testing.assert_allclose(rotation[0].T @ rotation[0], np.eye(3), atol=1e-7)
    np.testing.assert_allclose(ground, [0.])
