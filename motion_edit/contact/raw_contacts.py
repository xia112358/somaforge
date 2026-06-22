from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from motion_edit.contact.graph import ContactGraph
from motion_edit.contact.patches import patches_from_anchors
from motion_edit.contact.schema import ContactAnchorRecord, ContactSurfaceRecord
from motion_edit.contact.surface_geometry import point_in_polygon_uv, surface_polygon_uv

PART_ALIASES = {
    "lf": ("lf", "left_foot", "left_ankle", "left_ankle_roll_link"),
    "rf": ("rf", "right_foot", "right_ankle", "right_ankle_roll_link"),
    "lh": ("lh", "left_hand", "left_wrist", "left_wrist_yaw_link"),
    "rh": ("rh", "right_hand", "right_wrist", "right_wrist_yaw_link"),
    "lk": ("lk", "left_knee", "left_knee_link"),
    "rk": ("rk", "right_knee", "right_knee_link"),
}

UP_DOT_THRESHOLD = 0.5
EDGE_DISTANCE_THRESHOLD = 0.05


class RawContactMotion:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.data = np.load(self.path, allow_pickle=True)
        required = [
            "raw_contact_count",
            "raw_contact_point0_w",
            "raw_contact_point1_w",
            "contact_force_part_position_w",
            "contact_force_part_order",
        ]
        missing = [name for name in required if name not in self.data]
        if missing:
            raise ValueError(f"{self.path}: missing raw contact fields: {', '.join(missing)}")
        self.raw_contact_count = np.asarray(self.data["raw_contact_count"], dtype=np.int64)
        self.raw_contact_point0_w = np.asarray(self.data["raw_contact_point0_w"], dtype=np.float64)
        self.raw_contact_point1_w = np.asarray(self.data["raw_contact_point1_w"], dtype=np.float64)
        self.part_position_w = np.asarray(self.data["contact_force_part_position_w"], dtype=np.float64)
        self.part_order = [str(item).lower() for item in np.asarray(self.data["contact_force_part_order"]).tolist()]
        self.part_index_by_alias = _part_index_by_alias(self.part_order)


def _part_index_by_alias(part_order: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for index, part in enumerate(part_order):
        aliases = PART_ALIASES.get(part.lower(), (part.lower(),))
        for alias in aliases:
            out[alias] = index
    return out


def _anchor_part_index(anchor: ContactAnchorRecord, raw: RawContactMotion) -> int | None:
    body = anchor.body.lower()
    if body in raw.part_index_by_alias:
        return raw.part_index_by_alias[body]
    for canonical, aliases in PART_ALIASES.items():
        if any(alias in body for alias in aliases):
            return raw.part_index_by_alias.get(canonical)
    return None


def _project_sample_to_surface(point: np.ndarray, surface: ContactSurfaceRecord, max_distance: float) -> tuple[np.ndarray, dict[str, Any]] | None:
    surface.validate()
    origin = np.asarray(surface.origin, dtype=np.float64)
    normal = np.asarray(surface.normal, dtype=np.float64)
    tangent_u = np.asarray(surface.tangent_u, dtype=np.float64)
    tangent_v = np.asarray(surface.tangent_v, dtype=np.float64)
    signed_distance = float(np.dot(point - origin, normal))
    if abs(signed_distance) > max_distance:
        return None
    projected = point - signed_distance * normal
    local = projected - origin
    u = float(np.dot(local, tangent_u))
    v = float(np.dot(local, tangent_v))
    polygon = surface_polygon_uv(
        surface.metadata,
        origin=surface.origin,
        tangent_u=surface.tangent_u,
        tangent_v=surface.tangent_v,
    )
    if surface.surface_type == "mesh_face" and not polygon:
        return None
    if polygon:
        inside = point_in_polygon_uv((u, v), polygon)
    else:
        inside = _inside_bounds(u, v, surface.bounds)
    if not inside:
        return None
    metadata = {
        "surface_id": surface.surface_id,
        "object_id": surface.object_id,
        "surface_type": surface.surface_type,
        "signed_surface_distance": signed_distance,
        "surface_coordinates": {"u": u, "v": v},
    }
    return projected, metadata


def _sample_surface_relation(point: np.ndarray, surface: ContactSurfaceRecord) -> dict[str, Any] | None:
    surface.validate()
    origin = np.asarray(surface.origin, dtype=np.float64)
    normal = np.asarray(surface.normal, dtype=np.float64)
    tangent_u = np.asarray(surface.tangent_u, dtype=np.float64)
    tangent_v = np.asarray(surface.tangent_v, dtype=np.float64)
    signed_distance = float(np.dot(point - origin, normal))
    projected = point - signed_distance * normal
    local = projected - origin
    u = float(np.dot(local, tangent_u))
    v = float(np.dot(local, tangent_v))
    polygon = surface_polygon_uv(
        surface.metadata,
        origin=surface.origin,
        tangent_u=surface.tangent_u,
        tangent_v=surface.tangent_v,
    )
    if polygon:
        inside = point_in_polygon_uv((u, v), polygon)
        distance_to_boundary = _distance_to_polygon_boundary((u, v), polygon)
    else:
        inside = _inside_bounds(u, v, surface.bounds)
        distance_to_boundary = _distance_to_bounds_boundary(u, v, surface.bounds)
    return {
        "surface_id": surface.surface_id,
        "surface_type": surface.surface_type,
        "normal": surface.normal,
        "normal_z": float(surface.normal[2]),
        "signed_surface_distance": signed_distance,
        "abs_surface_distance": abs(signed_distance),
        "surface_coordinates": {"u": u, "v": v},
        "inside": inside,
        "distance_to_boundary": distance_to_boundary,
    }


def _distance_to_polygon_boundary(point: tuple[float, float], polygon: list[tuple[float, float]]) -> float | None:
    if len(polygon) < 2:
        return None
    return min(_point_segment_distance(point, polygon[index], polygon[(index + 1) % len(polygon)]) for index in range(len(polygon)))


def _point_segment_distance(point: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    closest = _closest_point_on_segment(point, a, b)
    return float(np.hypot(point[0] - closest[0], point[1] - closest[1]))


def _closest_point_on_segment(point: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    ab = (b[0] - a[0], b[1] - a[1])
    ap = (point[0] - a[0], point[1] - a[1])
    denom = ab[0] * ab[0] + ab[1] * ab[1]
    if denom == 0.0:
        return a
    t = max(0.0, min(1.0, (ap[0] * ab[0] + ap[1] * ab[1]) / denom))
    return (a[0] + t * ab[0], a[1] + t * ab[1])


def _distance_to_bounds_boundary(u: float, v: float, bounds: dict[str, Any] | None) -> float | None:
    if bounds is None:
        return None
    u_bounds = bounds.get("u")
    v_bounds = bounds.get("v")
    if not isinstance(u_bounds, list) or len(u_bounds) != 2:
        return None
    if not isinstance(v_bounds, list) or len(v_bounds) != 2:
        return None
    return min(abs(u - float(u_bounds[0])), abs(u - float(u_bounds[1])), abs(v - float(v_bounds[0])), abs(v - float(v_bounds[1])))


def _inside_bounds(u: float, v: float, bounds: dict[str, Any] | None) -> bool:
    if bounds is None:
        return True
    u_bounds = bounds.get("u")
    v_bounds = bounds.get("v")
    if not isinstance(u_bounds, list) or len(u_bounds) != 2:
        return False
    if not isinstance(v_bounds, list) or len(v_bounds) != 2:
        return False
    return float(u_bounds[0]) <= u <= float(u_bounds[1]) and float(v_bounds[0]) <= v <= float(v_bounds[1])


def _classify_surface_candidates(
    *,
    assigned_points: list[np.ndarray],
    accepted_count: int,
    surfaces: list[ContactSurfaceRecord] | None,
    max_surface_distance: float,
) -> dict[str, Any]:
    if accepted_count > 0:
        accepted_relations = [
            relation
            for point in assigned_points
            for surface in surfaces or []
            if (relation := _sample_surface_relation(point, surface)) is not None
            and bool(relation["inside"])
            and float(relation["abs_surface_distance"]) <= max_surface_distance
        ]
        if accepted_relations:
            hits = _count_by_surface(accepted_relations)
            selected_surface_id = max(hits.items(), key=lambda item: item[1])[0]
            selected = next(relation for relation in accepted_relations if relation["surface_id"] == selected_surface_id)
            if selected_surface_id == "terrain_ground_z0":
                return {"binding_candidate_class": "ground"}
            if float(selected["normal_z"]) > UP_DOT_THRESHOLD:
                return {"binding_candidate_class": "top"}
            return {"binding_candidate_class": "side_filtered"}
        return {"binding_candidate_class": "top"}
    if not assigned_points:
        return {"binding_candidate_class": "raw_missing"}
    if not surfaces:
        return {"binding_candidate_class": "outside_known_surfaces"}
    relations = [
        relation
        for point in assigned_points
        for surface in surfaces
        if (relation := _sample_surface_relation(point, surface)) is not None
    ]
    near_relations = [relation for relation in relations if float(relation["abs_surface_distance"]) <= max_surface_distance]
    if not near_relations:
        return {"binding_candidate_class": "outside_known_surfaces"}
    side_hits = [
        relation
        for relation in near_relations
        if abs(float(relation["normal_z"])) <= UP_DOT_THRESHOLD and bool(relation["inside"])
    ]
    if side_hits:
        return {
            "binding_candidate_class": "side_filtered",
            "side_filtered_surface_hits": _count_by_surface(side_hits),
            "side_filtered_example": side_hits[0],
        }
    edge_hits = [
        relation
        for relation in near_relations
        if float(relation["normal_z"]) > UP_DOT_THRESHOLD
        and relation.get("distance_to_boundary") is not None
        and float(relation["distance_to_boundary"]) <= EDGE_DISTANCE_THRESHOLD
    ]
    if edge_hits:
        return {
            "binding_candidate_class": "edge_candidate",
            "edge_candidate_surface_hits": _count_by_surface(edge_hits),
            "edge_candidate_example": edge_hits[0],
        }
    return {
        "binding_candidate_class": "outside_known_surfaces",
        "nearest_surface_examples": sorted(near_relations, key=lambda item: float(item["abs_surface_distance"]))[:5],
    }


def _count_by_surface(relations: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for relation in relations:
        surface_id = str(relation["surface_id"])
        counts[surface_id] = counts.get(surface_id, 0) + 1
    return counts


def estimate_anchor_position_from_raw_contacts(
    anchor: ContactAnchorRecord,
    raw: RawContactMotion,
    *,
    surfaces: list[ContactSurfaceRecord] | None = None,
    max_part_distance: float = 0.25,
    max_surface_distance: float = 0.05,
) -> tuple[list[float] | None, dict[str, Any]]:
    part_index = _anchor_part_index(anchor, raw)
    metadata: dict[str, Any] = {
        "raw_contact_source": str(raw.data["raw_contact_source"]) if "raw_contact_source" in raw.data else "raw_contact",
        "anchor_body": anchor.body,
        "part_index": part_index,
        "part_order": raw.part_order,
    }
    if part_index is None:
        metadata["failure_reason"] = "anchor_body_not_in_contact_force_part_order"
        return None, metadata
    start = max(0, int(anchor.start_frame))
    end = min(int(anchor.end_frame), raw.raw_contact_count.shape[0])
    if end <= start:
        metadata["failure_reason"] = "anchor_interval_outside_motion"
        return None, metadata

    samples: list[np.ndarray] = []
    raw_samples = 0
    assigned_samples = 0
    rejected_surface_samples = 0
    nearest_distances: list[float] = []
    surface_hits: dict[str, int] = {}
    surface_sample_metadata: list[dict[str, Any]] = []
    assigned_surface_points: list[np.ndarray] = []
    for frame in range(start, end):
        count = int(raw.raw_contact_count[frame])
        if count <= 0:
            continue
        count = min(count, raw.raw_contact_point0_w.shape[1])
        part_positions = raw.part_position_w[frame]
        for contact_index in range(count):
            raw_samples += 1
            robot_point = raw.raw_contact_point1_w[frame, contact_index]
            distances = np.linalg.norm(part_positions - robot_point[None, :], axis=1)
            nearest = int(np.argmin(distances))
            nearest_distance = float(distances[nearest])
            if nearest != part_index or nearest_distance > max_part_distance:
                continue
            assigned_samples += 1
            nearest_distances.append(nearest_distance)
            surface_point = raw.raw_contact_point0_w[frame, contact_index]
            assigned_surface_points.append(surface_point)
            if surfaces:
                projected_candidates = [
                    candidate
                    for surface in surfaces
                    if (candidate := _project_sample_to_surface(surface_point, surface, max_surface_distance)) is not None
                ]
                if not projected_candidates:
                    rejected_surface_samples += 1
                    continue
                projected, sample_meta = min(projected_candidates, key=lambda item: abs(float(item[1]["signed_surface_distance"])))
                samples.append(projected)
                surface_id = str(sample_meta["surface_id"])
                surface_hits[surface_id] = surface_hits.get(surface_id, 0) + 1
                surface_sample_metadata.append(sample_meta)
            else:
                samples.append(surface_point)

    metadata.update(
        {
            "raw_contact_frame_start": start,
            "raw_contact_frame_end": end,
            "raw_contact_sample_count": raw_samples,
            "assigned_raw_contact_sample_count": assigned_samples,
            "accepted_raw_contact_sample_count": len(samples),
            "rejected_surface_sample_count": rejected_surface_samples,
            "max_part_distance": max_part_distance,
            "max_surface_distance": max_surface_distance,
        }
    )
    metadata.update(
        _classify_surface_candidates(
            assigned_points=assigned_surface_points,
            accepted_count=len(samples),
            surfaces=surfaces,
            max_surface_distance=max_surface_distance,
        )
    )
    if nearest_distances:
        distances = np.asarray(nearest_distances, dtype=np.float64)
        metadata["nearest_part_distance_median"] = float(np.median(distances))
        metadata["nearest_part_distance_max"] = float(np.max(distances))
    if surface_hits:
        metadata["surface_hits"] = surface_hits
        metadata["selected_surface_id"] = max(surface_hits.items(), key=lambda item: item[1])[0]

    if not samples:
        metadata["failure_reason"] = "no_raw_contact_points_inside_surface_polygon" if surfaces else "no_assigned_raw_contact_points"
        return None, metadata

    positions = np.asarray(samples, dtype=np.float64)
    position = np.median(positions, axis=0)
    metadata["mean_raw_contact_point0_w"] = np.mean(positions, axis=0).tolist()
    metadata["median_raw_contact_point0_w"] = position.tolist()
    metadata["first_raw_contact_point0_w"] = positions[0].tolist()
    metadata["last_raw_contact_point0_w"] = positions[-1].tolist()
    if surface_sample_metadata:
        metadata["surface_sample_metadata"] = surface_sample_metadata[:10]
    return position.tolist(), metadata


def refine_contact_graph_anchor_positions_from_raw_contacts(
    graph: ContactGraph,
    motion_path: str | Path,
    *,
    surfaces: list[ContactSurfaceRecord] | None = None,
    max_part_distance: float = 0.25,
    max_surface_distance: float = 0.05,
) -> ContactGraph:
    raw = RawContactMotion(motion_path)
    anchors: list[ContactAnchorRecord] = []
    for anchor in graph.anchors:
        position, raw_metadata = estimate_anchor_position_from_raw_contacts(
            anchor,
            raw,
            surfaces=surfaces,
            max_part_distance=max_part_distance,
            max_surface_distance=max_surface_distance,
        )
        metadata = dict(anchor.metadata)
        metadata["raw_contact_position_refinement"] = raw_metadata
        if position is None:
            metadata["raw_contact_position_refinement_failed"] = True
            anchors.append(replace(anchor, metadata=metadata))
            continue
        metadata["raw_contact_position_refinement_failed"] = False
        anchors.append(
            replace(
                anchor,
                world_position=position,
                position_source="raw_contact_point0_w_polygon_median" if surfaces else "raw_contact_point0_w_median",
                metadata=metadata,
            )
        )
    return replace(graph, anchors=anchors, patches=patches_from_anchors(anchors))
