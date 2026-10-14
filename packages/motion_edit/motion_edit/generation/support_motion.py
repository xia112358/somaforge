"""Preserve source endpoint motion across changes of contact shape.

This compiles optimization targets, never contact truth. A contiguous endpoint
episode gets one rigid edit, rather than independently movable frame targets.
The source's rolling and internal contact transitions remain in the targets.
"""
import numpy as np


def temporal_history_mask(frame):
    """Only actual preceding samples may contribute finite differences."""
    return np.asarray([frame >= 1, frame >= 2], dtype=float)


def full_contact_episode_edits(edits, anchors):
    """Keep contact activation intervals independent of displacement windows."""
    from dataclasses import replace
    by_id = {anchor.anchor_id: anchor for anchor in anchors}
    return [replace(edit, affected_frames=[by_id[edit.anchor_id].start_frame,
                                           by_id[edit.anchor_id].end_frame])
            for edit in edits]


def endpoint(name):
    name = name.rsplit('/', 1)[-1].lower()
    side = 'left' if name.startswith('left_') else 'right' if name.startswith('right_') else None
    if side is None:
        return None
    for kind, words in [('foot', ('ankle', 'foot', 'toe', 'heel')),
                        ('hand', ('wrist', 'hand')), ('knee', ('knee',))]:
        if any(word in name for word in words):
            return side + '_' + kind
    return None


def compile_support_motion(compiled, link_names, source_positions, source_rotations,
                           edit_rotation, normals, reference_targets=None, *, origin_policy='median'):
    """Fit one edit translation per uninterrupted endpoint episode.

    FK arrays use the same canonical link order as compiled contact indices.
    Surface-normal references remain authoritative; only tangential targets
    are replaced. Shape changes cannot reset the endpoint episode.
    """
    indices = compiled.contact_link_indices
    if origin_policy not in ('median', 'landing'):
        raise ValueError('Unknown support episode origin policy')
    times = np.arange(len(indices))[:, None]
    source_points = source_positions[times, indices] + np.einsum(
        'tnij,tnj->tni', source_rotations[times, indices], compiled.contact_points_local)
    edited_points = np.einsum('...ij,...j->...i', edit_rotation, source_points)
    original = compiled.contact_targets_w
    reference = original if reference_targets is None else reference_targets
    targets = original.copy()
    mask = np.zeros(indices.shape, dtype=bool)
    part_by_link = np.asarray([endpoint(n) or '' for n in link_names])
    part = part_by_link[indices]
    records = []
    for name in sorted(set(part_by_link) - {''}):
        active = (part == name) & (compiled.contact_weights > 0)
        occupied = active.any(-1)
        boundaries = np.diff(np.r_[False, occupied, False].astype(int))
        for start, stop in zip(np.flatnonzero(boundaries == 1), np.flatnonzero(boundaries == -1)):
            if stop-start < 2:
                continue
            rows = active.copy()
            rows[:start] = False
            rows[stop:] = False
            # Each frame gets equal weight regardless of manifold density.
            offsets = reference - edited_points
            per_frame = [np.median(offsets[t, active[t]], axis=0) for t in range(start, stop)]
            translation = per_frame[0] if origin_policy == 'landing' else np.median(per_frame, axis=0)
            desired = edited_points + translation
            error = desired-original
            tangent = error - (error*normals).sum(-1, keepdims=True)*normals
            targets[rows] = (original+tangent)[rows]
            mask[rows] = True
            records.append(dict(endpoint=name, start=int(start), stop=int(stop),
                                translation_world=translation.tolist(), origin_policy=origin_policy))
    if not np.isfinite(targets).all():
        raise ValueError('Nonfinite support motion target')
    return targets, mask, records


def authored_support_targets(spec, compiled, link_names, positions, rotations, *, return_rotations=False):
    """Resolve the plan's surface edit, not its weak free-landing reference."""
    from .pyroki_taskspace import resolve_link_index
    from motion_edit.contact.surface_frame import map_points_between_surface_frames
    transforms = {t['source_surface']['surface_id']: t
                  for t in spec.metadata.get('support_surface_transforms', [])}
    if 'support_surface_transforms' not in spec.metadata:
        raise ValueError('Support-preserving generation requires authored surface transforms')
    result = compiled.contact_targets_w.copy()
    edit_rotations = np.broadcast_to(np.eye(3), (*compiled.contact_weights.shape, 3, 3)).copy()
    cursor = np.zeros(compiled.frame_count, dtype=int)
    for contact in spec.contacts:
        link = resolve_link_index(link_names, contact.body_label, (contact.body_label,))
        if link is None:
            continue
        transform = transforms.get(contact.metadata.get('source_surface_id') or contact.surface_id)
        edit_rotation = np.eye(3)
        if transform is not None:
            basis = map_points_between_surface_frames(np.vstack((np.zeros(3), np.eye(3))),
                transform['source_surface'], transform['target_surface'])
            edit_rotation = (basis[1:] - basis[0]).T
            if not np.allclose(edit_rotation.T @ edit_rotation, np.eye(3), atol=1.e-7):
                raise ValueError('Support surface edit must be rigid')
        for frame in contact.frames:
            t = int(frame)-int(spec.frame_start)
            for _ in contact.points_local:
                slot = cursor[t]; cursor[t] += 1
                edit_rotations[t, slot] = edit_rotation
                local = compiled.contact_points_local[t, slot]
                source = positions[t, link] + rotations[t, link] @ local
                if transform is None:
                    target = source.copy()
                else:
                    target = map_points_between_surface_frames(source[None],
                        transform['source_surface'], transform['target_surface'])[0]
                # Terrain height is already in the surface transform. Only the
                # optional in-surface position edit is added here.
                offset = np.asarray(contact.metadata.get('free_surface_reference_offset_world', [0.,0.,0.]))
                normal = np.asarray(contact.metadata['target_surface_geometry']['normal'])
                result[t, slot] = target + offset - normal * np.dot(offset, normal)
    return (result, edit_rotations) if return_rotations else result


def orientation_completion_projectors(compiled, link_names, positions, rotations, support_mask):
    """Stabilize single-point support without locking rolling line contacts.

    Three non-collinear points already constrain a rigid endpoint. Collinear
    points leave a rolling axis, which remains free. Only coincident points
    receive the source orientation regularizer.
    """
    indices=compiled.contact_link_indices
    times=np.arange(len(indices))[:,None]
    points=positions[times,indices]+np.einsum('tnij,tnj->tni',rotations[times,indices],compiled.contact_points_local)
    names=np.asarray([endpoint(n) or '' for n in link_names])[indices]
    projectors=np.zeros((*support_mask.shape,3,3))
    for t in range(len(indices)):
        for name in set(names[t,support_mask[t]])- {''}:
            slots=support_mask[t] & (names[t]==name)
            cloud=points[t,slots]
            # Numerical rank threshold; this is not a contact/slip tolerance.
            centered=cloud-cloud.mean(0)
            rank=np.linalg.matrix_rank(centered,tol=1.e-8)
            if rank==0:
                projectors[t,slots]=np.eye(3)
    return projectors
