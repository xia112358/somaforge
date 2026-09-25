"""Stable optimization samples; never new contact labels or contact truth."""
from dataclasses import replace

import numpy as np

from .pyroki_taskspace import quat_apply_wxyz, resolve_link_index


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
            # Prefer the richest observed manifold, then earliest frame. Sampling
            # changes within the episode no longer change the optimization basis.
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
            targets = positions[:, None, :] + quat_apply_wxyz(rotations[:, None, :], points[None, :, :])
            targets = targets + np.asarray(key[-1])
            anchors = sorted({c.anchor_id for f in run for c, _ in observations[int(f)]})
            result.append(replace(template,
                anchor_id=f"{template.anchor_id}:stable:{run[0]}:{run[-1]+1}",
                frames=run, points_local=points.copy(), points_local_by_frame=None,
                shape_labels=tuple(label for c, _ in entries for label in c.shape_labels),
                target_points_w=targets, normals_local=None,
                metadata={**template.metadata,
                    "optimization_sample_contract": "fixed_material_set_per_active_episode_v1",
                    "optimization_samples_are_contact_truth": False,
                    "source_contact_anchor_ids": anchors,
                    "material_sample_source_frame": int(representative)}))
    return replace(spec, contacts=tuple(result))
