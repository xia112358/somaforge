"""Canonical asset identity, joint ordering and FK survive MuJoCo import."""
import mujoco
import numpy as np
import pytest
import torch

from somaforge_core.g1_kinematics import CanonicalG1ForwardKinematics
from somaforge_core.retarget_model import load_retarget_model
from somaforge_core.robot_assets import canonical_g1_urdf_path


def test_retarget_fk_matches_canonical_torch_at_nonzero_poses():
    model = load_retarget_model(canonical_g1_urdf_path())
    assert (model.nq, model.nv) == (36, 35)
    data = mujoco.MjData(model)
    fk = CanonicalG1ForwardKinematics().double()
    names = tuple(model.body(i).name for i in range(1, model.nbody))
    rng = np.random.default_rng(42)
    q = rng.normal(0, .15, (8, 36))
    q[:, 2] += 1.
    q[:, 3:7] /= np.linalg.norm(q[:, 3:7], axis=1, keepdims=True)
    expected, _ = fk.link_poses(torch.tensor(q), names)
    positions = []
    for pose in q:
        data.qpos[:] = pose
        mujoco.mj_forward(model, data)
        positions.append(data.xpos[1:].copy())
    np.testing.assert_allclose(positions, expected.numpy(), atol=2.e-7, rtol=0)


def test_retarget_rejects_alternative_g1_asset(tmp_path):
    with pytest.raises(ValueError, match='canonical G1'):
        load_retarget_model(tmp_path / 'other_g1.urdf')


def test_static_terrain_keeps_robot_dofs_and_fixed_landmarks():
    root = canonical_g1_urdf_path().parents[5]
    path = root / 'holosoma_retargeting/holosoma_retargeting/demo_data/climb/mocap_climb_seq_1/multi_boxes.urdf'
    model = load_retarget_model(canonical_g1_urdf_path(), path, object_name='multi_boxes')
    assert model.nq == 36
    assert model.body('left_ankle_roll_sphere_1_link').id > 0
    object_geoms = [model.geom(i).name for i in range(model.ngeom) if model.geom(i).name.lstrip('/').startswith('multi_boxes_')]
    assert len(object_geoms) == 2
