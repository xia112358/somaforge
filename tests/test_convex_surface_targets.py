import numpy as np
from motion_edit.generation.surface_contact_loss import convex_targets,face_edges
from motion_edit.generation.surface_contact_loss import bounded_face_targets


def test_bounded_chart_inside_real_triangle_and_quad_including_edges():
    for count in (3,4):
        p=np.array([[0,0,0],[1,0,1],[1,1,1],[0,1,0]],float)
        n=np.array([-1,0,1.])/np.sqrt(2)
        valid=np.arange(4)<count
        _,e,o=face_edges(dict(normal=n,surface_type='face',polygon_world=p[:count]))
        uv=np.array([[u,v] for u in np.linspace(0,1,11) for v in np.linspace(0,1,11)])
        points,w=bounded_face_targets(uv,np.broadcast_to(p,(len(uv),4,3)),np.broadcast_to(valid,(len(uv),4)))
        assert (w>=0).all()
        np.testing.assert_allclose(w.sum(axis=1),1.,atol=1.e-14)
        assert np.max(points@e.T-o)<1.e-12


def test_coefficients_always_convex_on_rotated_true_face():
    p=np.array([[0,0,0],[1,0,1],[1,1,1],[0,1,0]],float)
    n=np.array([-1,0,1.])/np.sqrt(2)
    _,edges,offsets=face_edges(dict(normal=n,surface_type='face',polygon_world=p))
    logits=np.random.default_rng(42).uniform(-20,20,(100,3))
    points,w=convex_targets(logits,np.broadcast_to(p,(100,4,3)),np.ones((100,4),bool))
    assert (w>=0).all()
    np.testing.assert_allclose(w.sum(axis=1),1.,atol=1.e-14)
    assert np.max(points@edges.T-offsets)<1.e-12
    np.testing.assert_allclose(points@n,0.,atol=1.e-14)


def test_padding_cannot_pull_target_off_triangle():
    vertices=np.array([[[0,0,0],[1,0,0],[0,1,0],[99,99,99]]],float)
    points,w=convex_targets(np.zeros((1,3)),vertices,np.array([[True,True,True,False]]))
    np.testing.assert_allclose(points,[[1/3,1/3,0]])
    assert w[0,3]==0
