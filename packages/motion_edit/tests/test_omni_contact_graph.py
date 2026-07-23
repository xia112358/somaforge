from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from motion_edit.contact_laplacian.kinematics import BodyPositionTrajectoryKinematicsProvider
from motion_edit.contact_laplacian.residuals import LeastSquaresSystem
from motion_edit.contact_laplacian import solver
from motion_edit.generation import lte_fullbody
from motion_edit.generation import pyroki_taskspace
from motion_edit.generation.omni_contact_graph import (
    OMNI_BODY_EDGES,
    OMNI_KEYPOINT_LINKS,
    OMNI_SOLVER_POINT_ORDER,
    _build_omni_interaction_mesh,
    _target_object_points_from_plan,
)


def test_omni_semantics_use_sphere_hand_and_separate_ankle_toe() -> None:
    assert lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["left_hand"][0] == "left_sphere_hand_link"
    assert lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["right_hand"][0] == "right_sphere_hand_link"
    assert lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["left_ankle"][0] == "left_ankle_intermediate_1_link"
    assert lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["right_ankle"][0] == "right_ankle_intermediate_1_link"
    assert lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["left_foot"][0] == "left_ankle_roll_sphere_5_link"
    assert lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS["right_foot"][0] == "right_ankle_roll_sphere_5_link"

    assert pyroki_taskspace.SEMANTIC_LINK_ALIASES["left_hand"][0] == "left_sphere_hand_link"
    assert pyroki_taskspace.SEMANTIC_LINK_ALIASES["right_hand"][0] == "right_sphere_hand_link"
    assert pyroki_taskspace.SEMANTIC_LINK_ALIASES["left_foot"][0] == "left_ankle_roll_sphere_5_link"
    assert pyroki_taskspace.SEMANTIC_LINK_ALIASES["right_foot"][0] == "right_ankle_roll_sphere_5_link"


def test_batch_solver_keeps_core_points_and_restores_structure_points() -> None:
    keypoints = {
        name: np.full((3, 3), float(index), dtype=np.float64)
        for index, name in enumerate(OMNI_KEYPOINT_LINKS)
    }

    solver_keypoints = lte_fullbody._legacy_lte_solver_keypoints(keypoints)

    assert tuple(solver_keypoints) == OMNI_SOLVER_POINT_ORDER
    np.testing.assert_allclose(solver_keypoints["root"], keypoints["pelvis"])
    for name in (
        "torso",
        "left_hand",
        "right_hand",
        "left_foot",
        "right_foot",
        "left_knee",
        "right_knee",
    ):
        assert name in solver_keypoints
    for name in (
        "left_hip",
        "right_hip",
        "left_ankle",
        "right_ankle",
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
    ):
        assert name in solver_keypoints


def test_anatomical_graph_contains_ankle_to_toe_and_full_arm_chains() -> None:
    assert ("left_knee", "left_ankle") in OMNI_BODY_EDGES
    assert ("left_ankle", "left_foot") in OMNI_BODY_EDGES
    assert ("right_knee", "right_ankle") in OMNI_BODY_EDGES
    assert ("right_ankle", "right_foot") in OMNI_BODY_EDGES
    assert ("left_shoulder", "left_elbow") in OMNI_BODY_EDGES
    assert ("left_elbow", "left_hand") in OMNI_BODY_EDGES
    assert ("right_shoulder", "right_elbow") in OMNI_BODY_EDGES
    assert ("right_elbow", "right_hand") in OMNI_BODY_EDGES
    assert solver._SEMANTIC_BODY_EDGE_CANDIDATES == OMNI_BODY_EDGES


def test_omni_mesh_uses_per_frame_delaunay_residuals() -> None:
    rng = np.random.default_rng(7)
    frame_count = 2
    robot_count = len(OMNI_SOLVER_POINT_ORDER)
    reference = rng.normal(size=(frame_count, robot_count, 3))
    reference[1] += np.asarray([0.01, -0.02, 0.03])
    source_object = np.asarray(
        [
            [2.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 2.0],
            [2.0, 2.0, 2.0],
        ],
        dtype=np.float64,
    )
    target_object = source_object + np.asarray([0.0, 0.0, 0.1])
    mesh = _build_omni_interaction_mesh(
        robot_points=OMNI_SOLVER_POINT_ORDER,
        reference_robot_points=reference,
        source_object_points=source_object,
        target_object_points=target_object,
    )

    provider = BodyPositionTrajectoryKinematicsProvider(OMNI_SOLVER_POINT_ORDER)
    q_reference = reference.reshape(frame_count, -1)
    system = LeastSquaresSystem()
    metadata = solver.add_interaction_mesh_laplacian_residuals(
        system,
        q=q_reference.copy(),
        q_reference=q_reference,
        kinematics=provider,
        mesh=mesh,
        weight=1.0,
    )

    assert metadata["active"]
    assert metadata["rows"] > 0
    assert metadata["topology"] == "omniretarget_delaunay_per_frame"
    assert metadata["anatomical_edge_count"] == len(OMNI_BODY_EDGES)
    assert mesh.knn_k == 0
    assert not mesh.edges


def test_surface_translation_moves_current_object_vertices() -> None:
    source = np.asarray([[0.0, 0.0, 0.7], [1.0, 0.0, 0.7]], dtype=np.float64)
    plan = SimpleNamespace(
        surface_transforms=[
            {
                "translation_world": [0.0, 0.0, 0.07],
            }
        ]
    )

    target, warnings = _target_object_points_from_plan(plan, source)

    np.testing.assert_allclose(target, source + np.asarray([0.0, 0.0, 0.07]))
    assert warnings == []


def test_dense_proxy_maps_sphere_hand_and_foot_endpoint_to_correct_semantics() -> None:
    keypoint_names = list(lte_fullbody.LTE_FULLBODY_KEYPOINT_LINKS)
    body_names = [
        "left_sphere_hand_link",
        "right_sphere_hand_tip_link",
        "left_ankle_intermediate_1_link",
        "right_ankle_intermediate_1_link",
        "left_ankle_roll_sphere_5_link",
        "right_ankle_roll_sphere_5_link",
    ]

    weights = lte_fullbody._semantic_body_weights(body_names, keypoint_names)
    resolved = [keypoint_names[int(np.argmax(row))] for row in weights]

    assert resolved == [
        "left_hand",
        "right_hand",
        "left_ankle",
        "right_ankle",
        "left_foot",
        "right_foot",
    ]
