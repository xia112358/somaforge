from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from motion_edit.contact_laplacian.kinematics import BodyPositionTrajectoryKinematicsProvider
from motion_edit.contact_laplacian.schema import InteractionMeshSpec


# OmniRetarget's mapped climbing graph, with the existing torso trajectory kept as
# an additional core point. ``left_foot/right_foot`` retain the public/core
# semantic names but denote the toe endpoint; the ankle is represented explicitly.
OMNI_KEYPOINT_LINKS: dict[str, tuple[str, ...]] = {
    "pelvis": ("pelvis", "pelvis_contour_link"),
    "left_hip": ("left_hip_pitch_link", "left_hip_roll_link", "left_hip_yaw_link"),
    "left_knee": ("left_knee_link",),
    "left_ankle": (
        "left_ankle_intermediate_1_link",
        "left_ankle_pitch_link",
        "left_ankle_roll_link",
    ),
    "left_foot": ("left_ankle_roll_sphere_5_link",),
    "right_hip": ("right_hip_pitch_link", "right_hip_roll_link", "right_hip_yaw_link"),
    "right_knee": ("right_knee_link",),
    "right_ankle": (
        "right_ankle_intermediate_1_link",
        "right_ankle_pitch_link",
        "right_ankle_roll_link",
    ),
    "right_foot": ("right_ankle_roll_sphere_5_link",),
    "torso": ("torso_link",),
    "left_shoulder": ("left_shoulder_roll_link", "left_shoulder_pitch_link"),
    "left_elbow": ("left_elbow_link",),
    "left_hand": (
        "left_sphere_hand_link",
        "left_sphere_hand_tip_link",
        "left_rubber_hand_link",
        "left_wrist_yaw_link",
    ),
    "right_shoulder": ("right_shoulder_roll_link", "right_shoulder_pitch_link"),
    "right_elbow": ("right_elbow_link",),
    "right_hand": (
        "right_sphere_hand_link",
        "right_sphere_hand_tip_link",
        "right_rubber_hand_link",
        "right_wrist_yaw_link",
    ),
}

OMNI_SOLVER_POINT_ORDER: tuple[str, ...] = (
    "root",
    "torso",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_foot",
    "right_foot",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_hand",
    "right_hand",
)

OMNI_BODY_EDGES: tuple[tuple[str, str], ...] = (
    ("root", "torso"),
    ("root", "left_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("left_ankle", "left_foot"),
    ("root", "right_hip"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("right_ankle", "right_foot"),
    ("torso", "left_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_hand"),
    ("torso", "right_shoulder"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_hand"),
)

OMNI_SEMANTIC_WEIGHTS: dict[str, float] = {
    "pelvis": 10.0,
    "torso": 5.0,
    "left_hip": 2.0,
    "right_hip": 2.0,
    "left_knee": 4.0,
    "right_knee": 4.0,
    "left_ankle": 4.0,
    "right_ankle": 4.0,
    "left_foot": 8.0,
    "right_foot": 8.0,
    "left_shoulder": 2.0,
    "right_shoulder": 2.0,
    "left_elbow": 3.0,
    "right_elbow": 3.0,
    "left_hand": 5.0,
    "right_hand": 5.0,
}

_ORIGINAL_ADD_INTERACTION_MESH: Any | None = None
_INSTALLED = False


def _omni_solver_keypoints(keypoints: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    resolved = {"root": np.asarray(keypoints["pelvis"], dtype=np.float64)}
    for name in OMNI_SOLVER_POINT_ORDER:
        if name == "root":
            continue
        resolved[name] = np.asarray(keypoints[name], dtype=np.float64)
    return resolved


def _merge_omni_solver_keypoints(
    original: dict[str, np.ndarray],
    solver_edited: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    edited = {name: np.asarray(value, dtype=np.float64).copy() for name, value in original.items()}
    if "root" in solver_edited:
        edited["pelvis"] = np.asarray(solver_edited["root"], dtype=np.float64)
    for name in OMNI_SOLVER_POINT_ORDER:
        if name != "root" and name in solver_edited:
            edited[name] = np.asarray(solver_edited[name], dtype=np.float64)
    return edited


def _semantic_body_weights(body_names: list[str], keypoint_names: list[str]) -> np.ndarray:
    weights = np.zeros((len(body_names), len(keypoint_names)), dtype=np.float64)
    semantic = {name: index for index, name in enumerate(keypoint_names)}

    def assign(row: int, name: str, value: float = 1.0) -> bool:
        column = semantic.get(name)
        if column is None:
            return False
        weights[row, column] += float(value)
        return True

    for index, raw_name in enumerate(body_names):
        name = str(raw_name).lower()
        if name == "world":
            continue
        if name in {"pelvis", "pelvis_contour_link"}:
            assign(index, "pelvis")
        elif name.startswith(("waist", "torso")):
            assign(index, "torso")
        elif name.startswith("left_"):
            _assign_limb_body_weight(index, name, "left", assign)
        elif name.startswith("right_"):
            _assign_limb_body_weight(index, name, "right", assign)
        else:
            assign(index, "pelvis")

    missing = weights.sum(axis=1) <= 0.0
    pelvis_column = semantic.get("pelvis", 0)
    weights[missing, pelvis_column] = 1.0
    return weights / weights.sum(axis=1, keepdims=True)


def _assign_limb_body_weight(
    row: int,
    body_name: str,
    side: str,
    assign: Any,
) -> None:
    if "hip" in body_name:
        assign(row, f"{side}_hip")
    elif "knee" in body_name:
        assign(row, f"{side}_knee")
    elif "ankle_roll_sphere_5" in body_name or any(
        token in body_name for token in ("toe", "heel", "sole", "foot_contact")
    ):
        assign(row, f"{side}_foot")
    elif any(token in body_name for token in ("ankle", "foot")):
        assign(row, f"{side}_ankle")
    elif "shoulder" in body_name:
        assign(row, f"{side}_shoulder")
    elif "elbow" in body_name:
        assign(row, f"{side}_elbow")
    elif any(
        token in body_name
        for token in (
            "sphere_hand",
            "rubber_hand",
            "wrist",
            "hand",
            "palm",
            "finger",
            "thumb",
            "pinky",
        )
    ):
        assign(row, f"{side}_hand")
    else:
        assign(row, "torso")


def _dedupe_points(points: np.ndarray, eps: float = 1.0e-5) -> np.ndarray:
    unique: list[np.ndarray] = []
    seen: set[tuple[int, int, int]] = set()
    for point in np.asarray(points, dtype=np.float64).reshape(-1, 3):
        key = tuple(np.round(point / eps).astype(np.int64).tolist())
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
    return np.asarray(unique, dtype=np.float64)


def _object_points_from_graph(graph: Any, surfaces: Sequence[Any]) -> tuple[np.ndarray, list[str]]:
    warnings: list[str] = []
    points: list[np.ndarray] = []
    surface_by_id = {surface.surface_id: surface for surface in surfaces}
    used_surfaces: set[str] = set()
    for anchor in graph.anchors:
        surface = surface_by_id.get(anchor.surface_id or "")
        polygon = None
        if surface is not None and isinstance(surface.metadata, dict):
            polygon = surface.metadata.get("polygon_world")
        if polygon is not None and anchor.surface_id not in used_surfaces:
            array = np.asarray(polygon, dtype=np.float64)
            if array.ndim == 2 and array.shape[1] == 3:
                points.extend(array)
                used_surfaces.add(anchor.surface_id)
                continue
        if anchor.world_position is not None:
            center = np.asarray(anchor.world_position, dtype=np.float64)
            if center.shape == (3,):
                points.append(center)
    if not points:
        warnings.append("Omni interaction graph has no object points; using origin fallback")
        points.append(np.zeros(3, dtype=np.float64))
    return _dedupe_points(np.asarray(points, dtype=np.float64)), warnings


def _target_object_points_from_plan(
    plan: Any,
    source_points: np.ndarray,
) -> tuple[np.ndarray, list[str]]:
    transforms = list(getattr(plan, "surface_transforms", ()) or ())
    if not transforms:
        return np.asarray(source_points, dtype=np.float64).copy(), []

    translations: list[np.ndarray] = []
    for raw in transforms:
        value = raw.get("translation_world")
        if value is None:
            source = raw.get("source_surface") or {}
            target = raw.get("target_surface") or {}
            if source.get("origin") is not None and target.get("origin") is not None:
                value = np.asarray(target["origin"], dtype=np.float64) - np.asarray(
                    source["origin"],
                    dtype=np.float64,
                )
        if value is not None:
            translation = np.asarray(value, dtype=np.float64)
            if translation.shape == (3,) and np.all(np.isfinite(translation)):
                translations.append(translation)

    if not translations:
        return np.asarray(source_points, dtype=np.float64).copy(), [
            "surface transforms do not expose a usable object translation; "
            "Omni object vertices remain at the source pose"
        ]
    if not all(np.allclose(value, translations[0], atol=1.0e-8, rtol=0.0) for value in translations[1:]):
        return np.asarray(source_points, dtype=np.float64).copy(), [
            "surface transforms have different translations; "
            "Omni object vertices remain at the source pose"
        ]
    return np.asarray(source_points, dtype=np.float64) + translations[0][None, :], []


def _simplex_edges(simplices: np.ndarray) -> set[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    for simplex in np.asarray(simplices, dtype=np.int64):
        values = [int(value) for value in simplex.tolist()]
        for first in range(len(values)):
            for second in range(first + 1, len(values)):
                a, b = sorted((values[first], values[second]))
                if a != b:
                    edges.add((a, b))
    return edges


def _anatomical_index_edges(robot_points: Sequence[str]) -> set[tuple[int, int]]:
    index_by_name = {str(name): index for index, name in enumerate(robot_points)}
    edges: set[tuple[int, int]] = set()
    for parent, child in OMNI_BODY_EDGES:
        if parent not in index_by_name or child not in index_by_name:
            continue
        edges.add(tuple(sorted((index_by_name[parent], index_by_name[child]))))
    return edges


def _delaunay_edges(vertices: np.ndarray) -> tuple[set[tuple[int, int]], bool]:
    from scipy.spatial import Delaunay, QhullError

    points = np.asarray(vertices, dtype=np.float64)
    try:
        tetrahedra = Delaunay(points).simplices
    except QhullError:
        try:
            tetrahedra = Delaunay(points, qhull_options="QJ").simplices
        except QhullError:
            return set(), False
    return _simplex_edges(tetrahedra), True


def _build_omni_interaction_mesh(
    *,
    robot_points: Sequence[str],
    reference_robot_points: np.ndarray,
    source_object_points: np.ndarray,
    target_object_points: np.ndarray,
) -> InteractionMeshSpec:
    names = tuple(str(name) for name in robot_points)
    reference = np.asarray(reference_robot_points, dtype=np.float64)
    source_objects = np.asarray(source_object_points, dtype=np.float64)
    target_objects = np.asarray(target_object_points, dtype=np.float64)
    if reference.ndim != 3 or reference.shape[1:] != (len(names), 3):
        raise ValueError(
            f"reference_robot_points must have shape [T,{len(names)},3], got {reference.shape}"
        )
    if source_objects.ndim != 2 or source_objects.shape[1] != 3:
        raise ValueError(f"source_object_points must have shape [N,3], got {source_objects.shape}")
    if target_objects.shape != source_objects.shape:
        raise ValueError(
            f"target_object_points must have shape {source_objects.shape}, got {target_objects.shape}"
        )

    mesh = InteractionMeshSpec(
        robot_points=names,
        object_points=target_objects,
        edges=(),
        knn_k=0,
        reference_robot_points=reference,
        reference_object_points=source_objects,
        metadata={
            "topology": "omniretarget_delaunay_per_frame",
            "body_edges": [list(edge) for edge in OMNI_BODY_EDGES],
            "robot_point_count": len(names),
            "object_point_count": int(source_objects.shape[0]),
        },
    )
    mesh.validate()
    return mesh


def _reference_robot_points(
    mesh: InteractionMeshSpec,
    q_reference: np.ndarray,
    kinematics: Any,
    robot_points: Sequence[str],
) -> np.ndarray:
    if mesh.reference_robot_points is not None:
        reference = np.asarray(mesh.reference_robot_points, dtype=np.float64)
        if reference.ndim == 2:
            return np.repeat(reference[None, :, :], q_reference.shape[0], axis=0)
        return reference
    return np.asarray(
        [
            kinematics.fk_points(q_reference[frame], robot_points)
            for frame in range(q_reference.shape[0])
        ],
        dtype=np.float64,
    )


def _add_omni_interaction_mesh_laplacian_residuals(
    system: Any,
    *,
    q: np.ndarray,
    q_reference: np.ndarray,
    kinematics: Any,
    mesh: InteractionMeshSpec,
    weight: float,
) -> dict[str, Any]:
    topology = str(mesh.metadata.get("topology", ""))
    if topology != "omniretarget_delaunay_per_frame":
        if _ORIGINAL_ADD_INTERACTION_MESH is None:
            raise RuntimeError("original interaction-mesh residual is not installed")
        return _ORIGINAL_ADD_INTERACTION_MESH(
            system,
            q=q,
            q_reference=q_reference,
            kinematics=kinematics,
            mesh=mesh,
            weight=weight,
        )
    if weight <= 0.0:
        return {"active": False, "rows": 0}

    residuals = importlib.import_module("motion_edit.contact_laplacian.residuals")
    mesh.validate()
    q_array = np.asarray(q, dtype=np.float64)
    q_ref = np.asarray(q_reference, dtype=np.float64)
    if q_array.shape != q_ref.shape:
        raise ValueError(f"q_reference must have shape {q_array.shape}, got {q_ref.shape}")

    n_frames, nq = q_array.shape
    robot_points = tuple(str(point) for point in mesh.robot_points)
    object_points = np.asarray(mesh.object_points, dtype=np.float64)
    reference_object_points = (
        np.asarray(mesh.reference_object_points, dtype=np.float64)
        if mesh.reference_object_points is not None
        else object_points
    )
    robot_count = len(robot_points)
    vertex_count = robot_count + object_points.shape[0]
    reference_robot = _reference_robot_points(mesh, q_ref, kinematics, robot_points)
    anatomical_edges = _anatomical_index_edges(robot_points)

    row_count = 0
    edge_counts: list[int] = []
    active_counts: list[int] = []
    failed_frames: list[int] = []
    for frame in range(n_frames):
        reference_vertices = np.vstack([reference_robot[frame], reference_object_points])
        edges, succeeded = _delaunay_edges(reference_vertices)
        if not succeeded:
            failed_frames.append(frame)
        edges.update(anatomical_edges)
        if not edges:
            continue

        laplacian = residuals.build_uniform_laplacian_matrix(
            vertex_count,
            tuple(sorted(edges)),
        )
        active_rows = tuple(
            row
            for row in range(vertex_count)
            if np.any(laplacian[row, :robot_count])
        )
        if not active_rows:
            continue

        robot_current = kinematics.fk_points(q_array[frame], robot_points)
        robot_jacobian = kinematics.jacobian_points(q_array[frame], robot_points)
        current_vertices = np.vstack([robot_current, object_points])
        residual = laplacian @ reference_vertices - laplacian @ current_vertices
        row_weight = float(weight) / float(len(active_rows))

        for laplacian_row in active_rows:
            robot_coefficients = laplacian[laplacian_row, :robot_count]
            for axis in range(3):
                values: dict[int, float] = {}
                for robot_index, coefficient in enumerate(robot_coefficients):
                    if coefficient == 0.0:
                        continue
                    jacobian_axis = robot_jacobian[robot_index, axis]
                    for dof in range(nq):
                        contribution = float(coefficient) * float(jacobian_axis[dof])
                        if contribution == 0.0:
                            continue
                        column = residuals.variable_index(frame, dof, nq)
                        values[column] = values.get(column, 0.0) + contribution
                if values:
                    system.add_row(
                        values,
                        float(residual[laplacian_row, axis]),
                        "mesh_laplacian",
                        row_weight,
                    )
                    row_count += 1
        edge_counts.append(len(edges))
        active_counts.append(len(active_rows))

    if row_count == 0:
        return {
            "active": False,
            "rows": 0,
            "warning": "OmniRetarget Delaunay graph produced no robot-coupled rows",
            "delaunay_failed_frames": failed_frames,
        }
    return {
        "active": True,
        "rows": int(row_count),
        "vertex_count": int(vertex_count),
        "robot_vertex_count": int(robot_count),
        "object_vertex_count": int(object_points.shape[0]),
        "edge_count": int(round(float(np.mean(edge_counts)))) if edge_counts else 0,
        "edge_count_min": int(min(edge_counts)) if edge_counts else 0,
        "edge_count_max": int(max(edge_counts)) if edge_counts else 0,
        "active_laplacian_vertex_count": (
            int(round(float(np.mean(active_counts)))) if active_counts else 0
        ),
        "family_weight": float(weight),
        "normalization": "per_frame_mean_over_robot_coupled_laplacian_vertices",
        "topology": topology,
        "delaunay_failed_frame_count": len(failed_frames),
        "delaunay_failed_frames": failed_frames,
        "anatomical_edge_count": len(anatomical_edges),
    }


def _batch_contact_laplacian_proxy_motion(
    *,
    motion: dict[str, Any],
    source_motion: Path,
    graph: Any,
    contact_layer_root: Path,
    edits: list[Any],
    config: Any,
    source_plan_path: str | Path | None,
    plan: Any,
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    lte = importlib.import_module("motion_edit.generation.lte_fullbody")

    original_keypoints = lte._semantic_keypoints_from_motion(motion)
    solver_keypoints = _omni_solver_keypoints(original_keypoints)
    provider = BodyPositionTrajectoryKinematicsProvider(tuple(solver_keypoints))
    frame_count = len(next(iter(solver_keypoints.values())))
    q_init = np.stack(
        [solver_keypoints[name] for name in provider.point_names],
        axis=1,
    ).reshape(frame_count, -1)
    handles = lte._contact_laplacian_handles_from_edits(
        edits,
        solver_keypoints,
        graph=graph,
        config=config,
        source_motion=motion,
    )
    surfaces = lte._read_contact_layer_surfaces(contact_layer_root, graph.motion_id)
    source_object_points, object_warnings = _object_points_from_graph(graph, surfaces)
    target_object_points, target_warnings = _target_object_points_from_plan(
        plan,
        source_object_points,
    )
    reference_robot_points = q_init.reshape(
        frame_count,
        len(provider.point_names),
        3,
    )
    mesh = _build_omni_interaction_mesh(
        robot_points=provider.point_names,
        reference_robot_points=reference_robot_points,
        source_object_points=source_object_points,
        target_object_points=target_object_points,
    )
    result = lte.solve_batch_contact_laplacian(
        q_init,
        provider,
        handles,
        list(provider.point_names),
        config,
        q_prior=q_init,
        body_edges=OMNI_BODY_EDGES,
        interaction_mesh=mesh if float(config.mesh_laplacian_weight) > 0.0 else None,
    )
    edited_solver = {
        name: result.q.reshape(
            q_init.shape[0],
            len(provider.point_names),
            3,
        )[:, index, :]
        for index, name in enumerate(provider.point_names)
    }
    evaluation = lte._contact_laplacian_evaluation_summary(
        q_before=q_init,
        q_after=result.q,
        provider=provider,
        handles=handles,
        semantic_points=tuple(provider.point_names),
    )
    edited_keypoints = _merge_omni_solver_keypoints(
        original_keypoints,
        edited_solver,
    )
    arrays = lte._dense_taskspace_from_keypoints(
        motion,
        original_keypoints,
        edited_keypoints,
        source_motion,
        source_motion.with_suffix(".batch_contact_laplacian_proxy.npz"),
    )
    warnings = [
        "batch_contact_laplacian uses OmniRetarget per-frame Delaunay graph",
        *object_warnings,
        *target_warnings,
        *result.warnings,
    ]
    metadata = {
        "source_plan": (
            str(Path(source_plan_path).expanduser())
            if source_plan_path is not None
            else plan.plan_id
        ),
        "source_plan_id": plan.plan_id,
        "source_motion": str(source_motion),
        "generation_mode": "lte_fullbody",
        "fullbody_solver": "batch_contact_laplacian",
        "proxy_kinematics": "body_pos_w_omni_semantic_points",
        "interaction_graph_profile": "omniretarget_delaunay_per_frame",
        "solver_point_names": list(provider.point_names),
        "core_handle_point_names": list(lte.LTE_HANDLE_KEYPOINT_NAMES),
        "num_edits": len(edits),
        "moving_contact_handle_count": sum(
            1 for handle in handles if handle.kind == "edited_contact"
        ),
        "fixed_contact_handle_count": sum(
            1 for handle in handles if handle.kind == "fixed_contact"
        ),
        "force_load_profile_count": sum(
            1 for handle in handles if handle.load_profile is not None
        ),
        "force_load_profiles_active": any(
            handle.load_profile is not None for handle in handles
        ),
        "force_load_profile_interval_mapping": "same_frame_interval",
        "contact_laplacian_config": config.__dict__,
        "interaction_mesh": mesh.metadata,
        "solver_metadata": result.metadata,
        "evaluation_summary": evaluation,
        "warnings": warnings,
        "edits": [edit.to_dict() for edit in edits],
    }
    arrays["motion_edit_generation_metadata"] = lte._json_npz_value(metadata)
    arrays["source_motion_path"] = np.asarray(str(source_motion), dtype=object)
    arrays["source_contact_edit_plan"] = np.asarray(plan.plan_id, dtype=object)
    for key in ("joint_pos", "joint_vel", "joint_names"):
        if key in motion:
            arrays[key] = np.asarray(motion[key])
    return arrays, warnings, metadata


def install_omni_contact_graph() -> None:
    """Install OmniRetarget-compatible semantic points and interaction graph."""

    global _INSTALLED, _ORIGINAL_ADD_INTERACTION_MESH
    if _INSTALLED:
        return

    lte = importlib.import_module("motion_edit.generation.lte_fullbody")
    solver = importlib.import_module("motion_edit.contact_laplacian.solver")
    pyroki = importlib.import_module("motion_edit.generation.pyroki_taskspace")

    lte.LTE_FULLBODY_KEYPOINT_LINKS.clear()
    lte.LTE_FULLBODY_KEYPOINT_LINKS.update(OMNI_KEYPOINT_LINKS)
    lte.CONTACT_BODY_LINK_CANDIDATES["left_foot"] = (
        "left_ankle_roll_sphere_5_link",
        "left_ankle_roll_sphere_4_link",
        "left_ankle_roll_sphere_3_link",
        "left_ankle_roll_sphere_2_link",
        "left_ankle_roll_sphere_1_link",
        "left_ankle_roll_link",
        "left_ankle_pitch_link",
    )
    lte.CONTACT_BODY_LINK_CANDIDATES["right_foot"] = (
        "right_ankle_roll_sphere_5_link",
        "right_ankle_roll_sphere_4_link",
        "right_ankle_roll_sphere_3_link",
        "right_ankle_roll_sphere_2_link",
        "right_ankle_roll_sphere_1_link",
        "right_ankle_roll_link",
        "right_ankle_pitch_link",
    )
    lte.CONTACT_BODY_LINK_CANDIDATES["left_hand"] = OMNI_KEYPOINT_LINKS["left_hand"]
    lte.CONTACT_BODY_LINK_CANDIDATES["right_hand"] = OMNI_KEYPOINT_LINKS["right_hand"]
    lte._legacy_lte_solver_keypoints = _omni_solver_keypoints
    lte._merge_solver_keypoints = _merge_omni_solver_keypoints
    lte._semantic_body_weights = _semantic_body_weights
    lte._batch_contact_laplacian_proxy_motion = _batch_contact_laplacian_proxy_motion

    solver._SEMANTIC_BODY_EDGE_CANDIDATES = OMNI_BODY_EDGES
    _ORIGINAL_ADD_INTERACTION_MESH = solver.add_interaction_mesh_laplacian_residuals
    solver.add_interaction_mesh_laplacian_residuals = (
        _add_omni_interaction_mesh_laplacian_residuals
    )

    pyroki.SEMANTIC_LINK_ALIASES.clear()
    pyroki.SEMANTIC_LINK_ALIASES.update(OMNI_KEYPOINT_LINKS)
    pyroki.SEMANTIC_DEFAULT_WEIGHTS.clear()
    pyroki.SEMANTIC_DEFAULT_WEIGHTS.update(OMNI_SEMANTIC_WEIGHTS)

    _INSTALLED = True
