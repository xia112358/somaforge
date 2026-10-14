"""Optimization-only native contact witnesses; never contact classification."""
import numpy as np


def compile_release_witnesses(metadata, link_names, frame_count):
    rows = [[] for _ in range(frame_count)]
    for row in metadata.get("release_witnesses", []):
        if row.get("contract") != "native_allocated_contact_release_witness_v1":
            raise ValueError("Release witness lacks native contact provenance")
        frame = int(row["frame"])
        if not 0 <= frame < frame_count or row["body"] not in link_names:
            raise ValueError("Invalid release frame/body")
        margin, clearance = float(row["includemargin"]), float(row["clearance"])
        normal = np.asarray(row["normal_w"], float)
        if not np.isfinite([margin, clearance]).all() or clearance < margin:
            raise ValueError("Invalid solver-derived release clearance")
        if normal.shape != (3,) or not np.isclose(np.linalg.norm(normal), 1.):
            raise ValueError("Invalid native face normal")
        rows[frame].append(row)
    width = max(1, max(map(len, rows), default=0))
    indices = np.zeros((frame_count, width), np.int32)
    points = np.zeros((frame_count, width, 3))
    targets = np.zeros_like(points)
    normals = np.zeros_like(points)
    weights = np.zeros((frame_count, width))
    for frame, items in enumerate(rows):
        for slot, row in enumerate(items):
            indices[frame, slot] = link_names.index(row["body"])
            points[frame, slot] = row["point_local"]
            targets[frame, slot] = row["target_w"]
            normals[frame, slot] = row["normal_w"]
            multiplier=float(row.get("penalty_multiplier", 1.))
            if not np.isfinite(multiplier) or multiplier < 1.:
                raise ValueError("Invalid release penalty multiplier")
            weights[frame, slot] = np.sqrt(1000. * multiplier / len(items))
    if not all(np.isfinite(x).all() for x in (points, targets, normals, weights)):
        raise ValueError("Nonfinite release witness")
    return indices, points, targets, normals, weights


def release_residual(points, targets, normals, weights, *, xp=np):
    return xp.minimum(xp.sum((points-targets)*normals, axis=-1), 0.)*weights
