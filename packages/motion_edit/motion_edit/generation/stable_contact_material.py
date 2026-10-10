"""Stable optimization samples; never new contact labels or contact truth."""
from dataclasses import replace

import numpy as np

from .pyroki_taskspace import quat_apply_wxyz, resolve_link_index

MATERIAL_SAMPLE_SCHEMA = 'fixed_observed_material_basis_per_active_episode_v2'


def observed_rigid_material_basis(initial, observations, *, roundoff):
    """Keep the observed rigid task's rank when choosing stable samples.

    Two points from one frame can discard orientation information available in
    the same uninterrupted episode. Add only observed points needed for rigid
    rank two. A truly collinear contact remains collinear; no off-line point is
    fabricated, and no gap in activation is bridged.
    """
    points = np.asarray(initial, float).copy()
    pool = np.asarray(observations, float)
    if points.ndim != 2 or pool.ndim != 2 or points.shape[1] != 3 or pool.shape[1] != 3:
        raise ValueError('Observed material samples must be three dimensional')
    if not len(points) or not len(pool) or not np.isfinite(points).all() or not np.isfinite(pool).all():
        raise ValueError('Missing finite observed material basis')
    additions = []
    for _ in range(2):
        _, singular, axes = np.linalg.svd(points-points[0], full_matrices=False)
        rank = int(np.count_nonzero(singular > roundoff))
        if rank >= 2:
            break
        delta = pool-points[0]
        if rank:
            delta = delta-(delta @ axes[:rank].T) @ axes[:rank]
        distance = np.linalg.norm(delta, axis=-1)
        chosen = int(np.argmax(distance))
        if distance[chosen] <= roundoff:
            break
        points = np.vstack((points, pool[chosen]))
        additions.append(chosen)
    return points, additions


def stabilize_contact_material_samples(spec, source_motion):
    """Use one observed material-point set per uninterrupted shape/face episode.

    Activation frames are unchanged. Targets follow these material points in the
    source FK, preserving demonstrated rolling rather than fixing a world pose.
    These points need not be Newton manifold points at every frame: they are
    explicitly optimization samples, and must never be exported as contact truth.
    """
    groups = {}
    for contact in spec.contacts:
        surface = contact.metadata.get("target_surface_id")
        if not surface or not contact.shape_labels:
            raise ValueError("Stable material samples require shape/face identity")
        if contact.metadata.get("target_contract") != "unrotated_demonstration_weak_reference":
            raise ValueError("Stable material pilot requires unrotated source references")
        offset = tuple(contact.metadata.get("free_surface_reference_offset_world", [0., 0., 0.]))
        if len(offset) != 3 or not np.isfinite(offset).all():
            raise ValueError("Invalid weak-reference offset")
        key = (contact.body_label, tuple(sorted(set(contact.shape_labels))), surface, contact.kind, offset)
        frames = groups.setdefault(key, {})
        for offset, frame in enumerate(contact.frames):
            points = (contact.points_local_by_frame[offset]
                      if contact.points_local_by_frame is not None else contact.points_local)
            frames.setdefault(int(frame), []).append((contact, np.asarray(points)))
    links = tuple(map(str, source_motion["body_names"]))
    result = []
    for key, observations in groups.items():
        frames = np.array(sorted(observations), dtype=int)
        for run in np.split(frames, np.flatnonzero(np.diff(frames) != 1) + 1):
            # Retain the richest observed frame, but do not let that frame
            # discard rigid information present elsewhere in this episode.
            representative = max(run, key=lambda f: sum(len(p) for _, p in observations[int(f)]))
            entries = observations[int(representative)]
            template = entries[0][0]
            points = np.concatenate([p for _, p in entries], axis=0)
            if len(points) == 0:
                raise ValueError("Empty contact material sample set")
            index = resolve_link_index(links, template.body_label, (template.body_label,))
            if index is None:
                raise ValueError(f"Missing source FK body: {template.body_label}")
            positions = np.asarray(source_motion["body_pos_w"])[run, index]
            rotations = np.asarray(source_motion["body_quat_w"])[run, index]
            pool = np.concatenate([p for f in run for _, p in observations[int(f)]])
            pool_shapes = [label for f in run for contact, _ in observations[int(f)]
                           for label in contact.shape_labels]
            pool_frames = [int(f) for f in run for _, p in observations[int(f)] for _ in p]
            labels = [label for contact, _ in entries for label in contact.shape_labels]
            sample_frames = [int(representative)] * len(points)
            if len(pool_shapes) != len(pool) or len(labels) != len(points):
                raise ValueError('Observed material sample shape mapping is incomplete')
            # Newton's float32 world witnesses and their local conversion have
            # roundoff. It cannot turn an actually collinear set into a rigid
            # basis. This numerical guard does not classify contact or motion.
            roundoff = 32 * np.finfo(np.float32).eps * max(1., float(np.abs(positions).max()))
            points, additions = observed_rigid_material_basis(points, pool, roundoff=roundoff)
            labels.extend(pool_shapes[i] for i in additions)
            sample_frames.extend(pool_frames[i] for i in additions)
            targets = positions[:, None, :] + quat_apply_wxyz(rotations[:, None, :], points[None, :, :])
            targets = targets + np.asarray(key[-1])
            anchors = sorted({c.anchor_id for f in run for c, _ in observations[int(f)]})
            result.append(replace(template,
                anchor_id=f"{template.anchor_id}:stable:{run[0]}:{run[-1]+1}",
                frames=run, points_local=points.copy(), points_local_by_frame=None,
                shape_labels=tuple(labels),
                target_points_w=targets, normals_local=None,
                metadata={**template.metadata,
                    "optimization_sample_contract": MATERIAL_SAMPLE_SCHEMA,
                    "optimization_samples_are_contact_truth": False,
                    "source_contact_anchor_ids": anchors,
                    "material_sample_source_frame": int(representative),
                    "material_basis_source_frames": sample_frames,
                    "material_basis_observed_additions": len(additions),
                    "material_basis_roundoff_m": float(roundoff)}))
    return replace(spec, contacts=tuple(result))
