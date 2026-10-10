"""Physical penetration semantics and multiplier linearizations share witnesses."""
from types import SimpleNamespace

import numpy as np
import pytest

from motion_edit.generation.continuous_ik import NativeCollisionRows


def scene_problem(gap, *, source_gap, desired=True, multipliers=None, self_pair=False,
                  collect_linearizations=False, normal_defined=True):
    names = ('collision_link_indices', 'collision_points_local', 'collision_normals_base',
             'collision_terrain_points_base', 'collision_similarity_weight', 'collision_deeper_weight',
             'self_collision_link_a', 'self_collision_point_a_local', 'self_collision_link_b',
             'self_collision_point_b_local', 'self_collision_normals_base', 'self_collision_sqrt_weight')
    vectors = {name for name in names if 'point' in name or 'normal' in name}
    rows = [tuple(np.zeros((1, 3) if name in vectors else (1,),
                          int if 'indices' in name or name in ('self_collision_link_a', 'self_collision_link_b')
                          else float) for name in names)]
    joint = SimpleNamespace(root=np.array([[0., 0., 0., 1., 0., 0., 0.]]),
        rotations=np.eye(3)[None], root_dofs=3, jnp=np, names=names,
        poses=lambda states: np.array([[[1., 0., 0., 0., 0., 0., 0.],
                                       [1., 0., 0., 0., 0., 0., 0.]]]))
    contacts = SimpleNamespace(robot_body_indices=np.array([], int) if self_pair else np.array([0]),
        robot_body_names=() if self_pair else ('left_ankle_roll_link',),
        shape0=np.array([0]), shape1=np.array([1]),
        body0=np.array([0 if self_pair else -1]), body1=np.array([1 if self_pair else 0]),
        geometry_distance_m=np.array([gap]),
        robot_points_w=np.array([[0., 0., gap]]), terrain_points_w=np.zeros((1, 3)),
        outward_normals_w=np.array([[0., 0., 1.]]),
        normal_a_to_b_w=np.array([[0., 0., 1.]]),
        point0_w=np.zeros((1, 3)), point1_w=np.array([[0., 0., gap]]),
        shape_labels=('terrain_ground', 'foot'))
    scene = SimpleNamespace(query_qpos=lambda q: contacts,
                            body_names=('left_ankle_roll_link', 'right_ankle_roll_link'))
    if not normal_defined:
        contacts.normal_a_to_b_w[:]=0.
        contacts.outward_normals_w[:]=0.
    refresh = NativeCollisionRows(joint, scene, list(scene.body_names),
        [{('left_ankle_roll_link', 'terrain_ground:ground'): source_gap}],
        [{('LF', 'ground'): 1.} if desired else {}], depth_weight=100., self_weight=100.,
        constraint_multipliers=multipliers, collect_linearizations=collect_linearizations)
    row = dict(zip(names, refresh(np.zeros((1, 4)), rows)[0]))
    return refresh, row


@pytest.mark.parametrize('source,gap,desired,excess', [
    (.008, .004, True, 0.),  # Closing a positive gap is not penetration.
    (-.002, -.001, True, 0.),
    (-.002, -.004, True, .002),
    (-.002, -.001, False, .001),
])
def test_only_observed_negative_clearance_can_be_a_penetration_allowance(source, gap, desired, excess):
    refresh, row = scene_problem(gap, source_gap=source, desired=desired)
    audit = refresh.audits[-1]
    assert audit['terrain_excess_max_m'] == pytest.approx(excess)
    normal = row['collision_normals_base'][0]
    signed = normal @ (row['collision_points_local'][0]-row['collision_terrain_points_base'][0])
    assert max(0., -signed) == pytest.approx(excess)


def test_multiplier_retains_separated_pair_without_faking_physical_overlap():
    key = ('terrain', 0, 'left_ankle_roll_link', 'terrain_ground')
    refresh, row = scene_problem(.004, source_gap=0., desired=False, multipliers={key: 12.8})
    # Non-requested contact-capable body's original penalty is 1600.
    signed = row['collision_normals_base'][0] @ (
        row['collision_points_local'][0]-row['collision_terrain_points_base'][0])
    assert signed == pytest.approx(-.004)
    assert refresh.constraint_values[key] == pytest.approx((.004, 1600.))
    assert refresh.audits[-1]['terrain_max_m'] == 0.
    assert refresh.audits[-1]['terrain_excess_max_m'] == 0.


def test_self_multiplier_linearization_does_not_change_physical_audit():
    key = ('self', 0, 'left_ankle_roll_link', 'right_ankle_roll_link')
    refresh, row = scene_problem(.004, source_gap=0., multipliers={key: .8}, self_pair=True)
    signed = row['self_collision_normals_base'][0] @ (
        row['self_collision_point_b_local'][0]-row['self_collision_point_a_local'][0])
    assert signed == pytest.approx(-.004)
    assert refresh.constraint_values[key] == pytest.approx((.004, 100.))
    assert refresh.audits[-1]['self_max_m'] == 0.
    assert not refresh.audits[-1]['self_pairs']


def test_positive_clearance_constraint_survives_zero_penalty_and_multiplier():
    refresh, row = scene_problem(.004, source_gap=.008, desired=False,
                                collect_linearizations=True)
    assert not row['collision_deeper_weight'].any()
    record, = refresh.constraint_linearizations
    assert record[2] == 0 and record[4] == -1
    assert record[-1] == pytest.approx(.004)
    np.testing.assert_array_equal(record[6], [0., 0., 1.])


def test_separated_self_constraint_keeps_actual_witness_and_signed_normal():
    refresh, row = scene_problem(.004, source_gap=0., self_pair=True,
                                collect_linearizations=True)
    assert not row['self_collision_sqrt_weight'].any()
    record, = refresh.constraint_linearizations
    assert (record[2], record[4]) == (0, 1)
    assert record[-1] == pytest.approx(.004)
    assert record[6] @ (record[3]-record[5]) == pytest.approx(record[-1])


@pytest.mark.parametrize('self_pair', [False, True])
def test_zero_normal_is_unknown_geometry_not_a_satisfied_zero_gap(self_pair):
    with pytest.raises(RuntimeError, match='zero witness projection is not a known signed distance'):
        scene_problem(0.,source_gap=0.,self_pair=self_pair,normal_defined=False,
                      collect_linearizations=True)


def test_live_witness_refresh_retains_fixed_targets_and_requeries_changed_geometry():
    refresh, original = scene_problem(.004, source_gap=0., desired=False,
        collect_linearizations=True)
    # An authored target is independent of the collision witnesses. The fresh
    # penetrating query must activate its own penalty without replacing it.
    target = np.array([[1., 2., 3.]])
    refresh.joint.names += ('semantic_target',)
    rows = [tuple(original[name] for name in refresh.joint.names[:-1])+(target,)]
    arguments = tuple(np.stack([row[index] for row in rows])
        for index in range(len(refresh.joint.names)))
    contacts = refresh.scene.query_qpos(None)
    contacts.geometry_distance_m[:] = -.03
    contacts.robot_points_w[:, 2] = -.03
    states = np.zeros((1, 4))
    complete = refresh(states, rows)
    actual = refresh.stacked_arguments(states, rows, arguments)
    for index, name in enumerate(refresh.joint.names):
        np.testing.assert_array_equal(actual[index], np.stack([row[index] for row in complete]),
            err_msg=name)
    assert actual[-1] is arguments[-1]
    assert actual[refresh.joint.names.index('collision_deeper_weight')].any()
    assert refresh.constraint_linearizations[0][-1] == pytest.approx(-.03)
