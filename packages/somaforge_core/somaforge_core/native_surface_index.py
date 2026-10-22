"""Exact spatial broad phase for native finite-face attribution.

Bounding spheres only prune triangles that cannot be nearest. They never decide
contact activation. Final distances/ties use the existing native face semantics.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from .newton_contacts import triangle_distance_squared


class NativeSurfaceIndex:
    def __init__(self, faces):
        self.faces = faces
        triangles, owners = [], []
        for index, face in enumerate(faces):
            values = np.asarray(face["triangles_w"], np.float64)
            triangles.extend(values)
            owners.extend([index] * len(values))
        self.triangles = np.asarray(triangles)
        if not len(self.triangles) or not np.isfinite(self.triangles).all():
            raise ValueError("Missing finite native triangle geometry")
        self.owners = np.asarray(owners)
        centers = self.triangles.mean(1)
        radii = np.linalg.norm(self.triangles-centers[:, None], axis=-1).max(-1)
        if (radii <= 0).any():
            raise ValueError("Degenerate native triangle")
        self.tree = cKDTree(centers)
        # Radius buckets prevent a large ground triangle from forcing a search
        # over every small box triangle in a multi-motion shared terrain mesh.
        bucket = np.floor(np.log2(radii)).astype(np.int64)
        self.buckets = []
        for key in np.unique(bucket):
            ids = np.flatnonzero(bucket == key)
            self.buckets.append((ids, cKDTree(centers[ids]), float(radii[ids].max())))
        self.normals = np.asarray([f["normal_w"] for f in faces], np.float64)
        self.surface_ids = np.asarray([f["surface"] for f in faces], np.int64)

    def query(self, points, normals):
        points, normals = np.asarray(points, np.float64), np.asarray(normals, np.float64)
        if points.ndim != 2 or points.shape[1:] != (3,) or normals.shape != points.shape:
            raise ValueError("Invalid native surface witness shape")
        if not np.isfinite(points).all() or not np.isfinite(normals).all():
            raise ValueError("Nonfinite native surface witness")
        output = []
        nearest = self.tree.query(points)[1]
        for point, normal, initial in zip(points, normals, nearest):
            best = float(triangle_distance_squared(point, self.triangles[initial:initial+1])[0])
            # Match actual_primary_face_indices' squared-distance tie rule.
            bound = np.sqrt(best + 1e-12 + 1e-9*abs(best))
            candidates = {int(initial)}
            for ids, tree, radius in self.buckets:
                selected = tree.query_ball_point(point, np.nextafter(bound+radius, np.inf))
                candidates.update(ids[selected].tolist())
            ids = np.asarray(sorted(candidates), np.int64)
            distance = triangle_distance_squared(point, self.triangles[ids])
            keep = np.isclose(distance, distance.min(), rtol=1e-9, atol=1e-12)
            owners = np.unique(self.owners[ids[keep]])
            score = self.normals[owners] @ normal
            order = np.lexsort((self.surface_ids[owners], -score))
            output.append(int(owners[order[0]]))
        return np.asarray(output, np.int64)
