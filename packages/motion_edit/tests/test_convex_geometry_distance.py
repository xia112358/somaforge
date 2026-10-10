"""Geometry uses actual model sizes/poses and keeps raw native evidence intact."""
from types import SimpleNamespace
from dataclasses import fields, replace

import numpy as np
import pytest

pytest.importorskip('coal')
newton = pytest.importorskip('newton')

from motion_edit.generation.convex_geometry_distance import ConvexGeometryDistance
from motion_edit.generation.newton_collision import NewtonCollisionContacts


def field(size=.12):
    def native(value):
        return SimpleNamespace(numpy=lambda: np.asarray(value))
    model = SimpleNamespace(shape_type=native([int(newton.GeoType.PLANE), int(newton.GeoType.SPHERE)]),
        shape_body=native([-1, 0]), shape_scale=native([[0.,0.,0.],[size,0.,0.]]),
        shape_transform=native([[0.,0.,.04,0.,0.,0.,1.],[.05,0.,.05,0.,0.,0.,1.]]))
    scene = SimpleNamespace(model=model, body_names=('moving',))
    return ConvexGeometryDistance(scene, ('moving',))


def raw_contacts():
    return NewtonCollisionContacts(shape0=np.array([0]),shape1=np.array([1]),
        body0=np.array([-1]),body1=np.array([0]),point0_w=np.zeros((1,3)),point1_w=np.zeros((1,3)),
        normal_a_to_b_w=np.zeros((1,3)),geometry_distance_m=np.zeros(1),
        constraint_distance_m=np.array([-.02]),margin0_m=np.array([.01]),margin1_m=np.array([.01]),
        shape_labels=('plane','sphere'),robot_body_names=('moving',),robot_body_indices=np.array([0]),
        robot_points_w=np.zeros((1,3)),terrain_points_w=np.zeros((1,3)),outward_normals_w=np.zeros((1,3)))


def test_false_zero_witness_is_requeried_with_actual_radius_transform_and_pose():
    original = raw_contacts()
    corrected = field().refine(original, np.array([[0.,0.,.10]]), np.eye(3)[None])
    assert corrected.geometry_distance_m[0] == pytest.approx(-.01, abs=1.e-12)
    assert corrected.robot_points_w[0,2] == pytest.approx(.03)
    assert corrected.terrain_points_w[0,2] == pytest.approx(.04)
    np.testing.assert_allclose(corrected.outward_normals_w, [[0.,0.,1.]], atol=1.e-12)
    # Activation fields are retained as raw evidence; corrected geometry is not
    # a new contact criterion or an inflated collision shape.
    np.testing.assert_array_equal(corrected.constraint_distance_m, original.constraint_distance_m)
    assert original.geometry_distance_m[0] == 0.
    assert not original.normal_a_to_b_w.any()


def test_requeried_signed_distance_derivative_matches_returned_witness_normal():
    geometry, original = field(), raw_contacts()
    h = 1.e-6
    values = [geometry.refine(original,np.array([[0.,0.,.10+d]]),np.eye(3)[None]) for d in (h,-h)]
    derivative=(values[0].geometry_distance_m[0]-values[1].geometry_distance_m[0])/(2*h)
    assert derivative == pytest.approx(1., abs=1.e-9)
    assert derivative == pytest.approx(values[0].outward_normals_w[0,2])


def test_model_radius_changes_geometry_without_importing_solver_margin():
    first=field(.12).refine(raw_contacts(),np.array([[0.,0.,.10]]),np.eye(3)[None])
    second=field(.07).refine(raw_contacts(),np.array([[0.,0.,.10]]),np.eye(3)[None])
    assert second.geometry_distance_m[0]-first.geometry_distance_m[0] == pytest.approx(.05)


def test_manifold_reuses_shapes_only_within_one_pose_query():
    geometry, original = field(), raw_contacts()
    repeated = {}
    for item in fields(original):
        value = getattr(original, item.name)
        if isinstance(value, np.ndarray):
            repeated[item.name] = np.concatenate((value, value), axis=0)
    repeated['robot_body_indices'] = np.array([0, 1])
    repeated['robot_body_names'] = ('moving', 'moving')
    contacts = replace(original, **repeated)
    transform = geometry.transform
    queried = []

    def counted(shape, positions, rotations):
        queried.append(shape)
        return transform(shape, positions, rotations)

    geometry.transform = counted
    first = geometry.refine(contacts, np.array([[0.,0.,.10]]), np.eye(3)[None])
    np.testing.assert_allclose(first.geometry_distance_m, [-.01, -.01], atol=1.e-12)
    assert queried == [0, 1]
    second = geometry.refine(contacts, np.array([[0.,0.,.13]]), np.eye(3)[None])
    np.testing.assert_allclose(second.geometry_distance_m, [.02, .02], atol=1.e-12)
    assert queried == [0, 1, 0, 1]
    np.testing.assert_array_equal(contacts.normal_a_to_b_w, np.zeros((2, 3)))
