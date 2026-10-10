import numpy as np
from scipy.spatial.transform import Rotation
from motion_edit.generation.native_sphere_distance import ConvexTerrain


def cube(rotation=None, translation=None):
    import trimesh
    mesh = trimesh.creation.box(extents=[.6, 1.2, .8])
    vertices = mesh.vertices
    if rotation is not None:
        vertices = rotation.apply(vertices)
    if translation is not None:
        vertices = vertices+translation
    return ConvexTerrain.from_mesh(vertices, mesh.faces)


def test_signed_mesh_distance_matches_closed_box_everywhere():
    rng = np.random.default_rng(20261004)
    rotation = Rotation.from_euler('xyz', [.2, -.4, .7])
    translation = np.array([.7, -.2, .4])
    terrain = cube(rotation, translation)
    local = rng.uniform(-1., 1., (400, 3))
    world = rotation.apply(local)+translation
    d, n, witness = terrain.query(world)
    q = np.abs(local)-[.3, .6, .4]
    expected = np.linalg.norm(np.maximum(q, 0.), axis=-1)+np.minimum(q.max(axis=-1), 0.)
    np.testing.assert_allclose(d, expected, atol=1.e-13)
    np.testing.assert_allclose(world-witness, d[:, None]*n, atol=1.e-13)
    np.testing.assert_allclose(np.linalg.norm(n, axis=-1), 1., atol=1.e-13)
    # Gradient of the queried value, rather than of a frozen witness substitute.
    direction = rng.normal(size=world.shape)
    h = 1.e-7
    plus = terrain.query(world+h*direction)[0]
    minus = terrain.query(world-h*direction)[0]
    np.testing.assert_allclose((plus-minus)/(2*h), np.sum(n*direction, axis=-1), atol=2.e-8)


def test_submillimetre_sphere_overlap_cannot_disappear():
    terrain = cube()
    radius = .005
    points = np.array([[.3+.00012, .15, .1], [.3+.000119, .15, .1],
                       [.3+.000121, .15, .1], [.3, .15, .1]])
    d, normal, _ = terrain.query(points)
    np.testing.assert_allclose(d-radius, [-.00488, -.004881, -.004879, -.005], atol=1.e-14)
    np.testing.assert_array_equal(normal, np.tile([1., 0., 0.], (4, 1)))


def test_empty_query_and_inside_point_remain_well_defined():
    terrain = cube()
    d, n, p = terrain.query(np.empty((0, 3)))
    assert d.shape == (0,) and n.shape == p.shape == (0, 3)
    d, n, p = terrain.query(np.array([[0., 0., 0.], [.299, 0., 0.]]))
    np.testing.assert_allclose(d, [-.3, -.001], atol=1.e-14)
    assert np.isfinite(n).all() and np.isfinite(p).all()
