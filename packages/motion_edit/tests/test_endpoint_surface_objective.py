import numpy as np

from motion_edit.generation.surface_contact_loss import endpoint_surface_residual, surface_residual


def test_support_has_one_three_dimensional_target_without_double_normal_penalty():
    p = np.array([[.03, .04, -.02]])
    ref = np.zeros_like(p)
    n = np.array([[0., 0., 1.]])
    edges = np.zeros((1, 1, 3))
    offsets = np.ones((1, 1))
    r = endpoint_surface_residual(p, ref, n, edges, offsets,
                                  np.array([2.]), np.array([10.]), .01)
    np.testing.assert_allclose(r @ r, 100. * np.sum(p * p))


def test_non_support_keeps_surface_clearance_and_weak_tangent_reference():
    p = np.array([[.03, .04, -.02], [.01, .02, .05]])
    ref = np.zeros_like(p)
    n = np.tile([0., 0., 1.], (2, 1))
    edges = np.zeros((2, 1, 3))
    offsets = np.ones((2, 1))
    w = np.array([2., 0.])
    np.testing.assert_allclose(
        endpoint_surface_residual(p, ref, n, edges, offsets, w, np.zeros(2), .01),
        surface_residual(p, ref, n, edges, offsets, w, .01))


def test_support_does_not_disable_finite_face_containment():
    p = np.array([[.3, 0., 0.]])
    # Even a matching support target cannot waive the finite-face restriction.
    r = endpoint_surface_residual(p, p, np.array([[0., 0., 1.]]),
        np.array([[[1., 0., 0.]]]), np.array([[.1]]), np.ones(1), np.array([100.]), .01)
    np.testing.assert_allclose(r @ r, .04)
