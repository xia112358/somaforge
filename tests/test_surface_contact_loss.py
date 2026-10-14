import numpy as np
import pytest
from motion_edit.generation.surface_contact_loss import face_edges, surface_residual


def test_true_polygon_not_xy_bbox():
    n, edges, offsets = face_edges(dict(surface_type='mesh_face', normal=[0,0,1],
        polygon_world=[[0,0,0],[1,0,0],[0,1,0]]))
    # Inside the XY rectangle but outside the actual triangle.
    r=surface_residual(np.array([[.8,.8,0]]),np.array([[.8,.8,0]]),n[None],edges[None],offsets[None],np.ones(1),0.)
    assert np.max(r) > .4


def test_tangent_free_normal_constrained_and_no_pose_projection():
    points=np.array([[2.,3.,.2]]); before=points.copy()
    args=(np.zeros((1,3)),np.array([[0,0,1.]]),np.zeros((1,1,3)),np.zeros((1,1)),np.ones(1))
    r=surface_residual(points,*args,0.)
    assert np.isclose(np.sum(r*r),.04)
    np.testing.assert_array_equal(points,before)
    weak=surface_residual(points,*args,.01)
    assert np.isclose(np.sum(weak*weak),.04+.01*13)


def test_finite_face_missing_polygon_fails():
    with pytest.raises(ValueError,match='actual polygon'):
        face_edges(dict(surface_type='mesh_face',normal=[0,0,1]))


def test_polygon_winding_does_not_change_region():
    p=[[0,0,0],[1,0,0],[1,1,0],[0,1,0]]
    for polygon in (p,p[::-1]):
        n,e,o=face_edges(dict(surface_type='mesh_face',normal=[0,0,1],polygon_world=polygon))
        assert np.max(np.array([.5,.5,0])@e.T-o)<0
