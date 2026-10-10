"""Frame selection and explicit soft joins for certified stationary intervals.

This module does not detect contact or certify a hold. The caller supplies
verified source intervals and must audit the new seams on the edited motion.
"""
import numpy as np


def quintic_slerp(first, second, weight):
    """Shortest-arc quaternion interpolation, including antipodal endpoints."""
    first = np.asarray(first, dtype=np.float64)
    second = np.asarray(second, dtype=np.float64)
    first = first / np.linalg.norm(first, axis=-1, keepdims=True)
    second = second / np.linalg.norm(second, axis=-1, keepdims=True)
    dot = np.sum(first * second, axis=-1, keepdims=True)
    second = np.where(dot < 0, -second, second)
    angle = np.arccos(np.abs(dot).clip(0, 1))
    sine = np.sin(angle)
    linear = sine < 1.e-7
    safe_sine = np.where(linear, 1., sine)
    weight = np.asarray(weight).reshape((-1,) + (1,) * (first.ndim - 1))
    result = np.sin((1-weight)*angle)/safe_sine*first + np.sin(weight*angle)/safe_sine*second
    result = np.where(linear, (1-weight)*first+weight*second, result)
    return result / np.linalg.norm(result, axis=-1, keepdims=True)


def compact_qpos(qpos, holds, *, blend_frames=16):
    """Crossfade retained hold-entry tails into hold-exit tails.

    Keep the existing compact clock and frame count. Only the retained tail
    preceding each cut changes; the right-hand continuation is untouched.
    Source-frame indices alone are NOT provenance for mixed poses: return the
    two complete source windows and their weights, and require fresh FK/contact
    queries. Continuity of poses does not certify contact or physical support.
    """
    qpos = np.asarray(qpos)
    if qpos.ndim != 2 or qpos.shape[1] < 7 or not np.isfinite(qpos).all():
        raise ValueError('Expected finite root-position/quaternion/joint poses')
    if np.any(np.linalg.norm(qpos[:,3:7],axis=-1) < 1.e-12):
        raise ValueError('Root quaternion cannot be zero')
    if int(blend_frames) != blend_frames or blend_frames < 3:
        raise ValueError('Soft joins require at least three blend frames')
    frames, mapping, seams = compact_timeline(len(qpos), holds)
    output = qpos[frames].copy()
    phase = np.linspace(0., 1., int(blend_frames))
    weight = phase**3 * (phase*(6*phase-15)+10)
    joins = []
    previous_output_end = -1
    for start, end in sorted(holds):
        if end == len(qpos)-1:
            continue
        left = np.arange(start+1-blend_frames, start+1, dtype=int)
        right = np.arange(end+1-blend_frames, end+1, dtype=int)
        if left[0] < 0 or right[0] <= start:
            raise ValueError('Hold has insufficient independent frames for the blend window')
        mapped = np.searchsorted(frames, left)
        if not np.array_equal(frames[mapped], left) or mapped[0] <= previous_output_end:
            raise ValueError('Soft join windows overlap or contain removed source frames')
        mixed = (1-weight[:, None])*qpos[left] + weight[:, None]*qpos[right]
        mixed[:, 3:7] = quintic_slerp(qpos[left, 3:7], qpos[right, 3:7], weight)
        output[mapped] = mixed.astype(qpos.dtype)
        previous_output_end = int(mapped[-1])
        joins.append(dict(output_window=[int(mapped[0]), int(mapped[-1])+1],
                          left_source_frames=left.tolist(), right_source_frames=right.tolist(),
                          right_weights=weight.tolist(), seam_frame=int(mapping[start])+1,
                          method='quintic_crossfade_root_slerp', contact_audit_required=True))
    return output, frames, mapping, seams, joins


def compact_timeline(frame_count, holds):
    """Keep each hold's first frame and remove (start, end], both in source time.

    A seam is explicitly NOT an ordinary consecutive source transition. Data
    consumers must split supervision there unless a separate seam audit passes.
    """
    if frame_count < 2:
        raise ValueError("Compaction requires at least two frames")
    keep = np.ones(frame_count, dtype=bool)
    previous_end = -1
    for start, end in sorted(holds):
        if not (int(start) == start and int(end) == end and 0 <= start < end < frame_count):
            raise ValueError(f"Invalid inclusive hold: {(start, end)}")
        if start <= previous_end:
            raise ValueError("Stationary intervals overlap")
        keep[int(start) + 1:int(end) + 1] = False
        previous_end = end
    source_frames = np.flatnonzero(keep)
    # One compact index per original frame, including removed hold frames.
    old_to_new = np.cumsum(keep, dtype=np.int64) - 1
    seams = np.flatnonzero(np.diff(source_frames) != 1) + 1
    return source_frames, old_to_new, seams


def remap_retained_interval(start, end, source_frames):
    """Map an inclusive action interval only if every source frame survived."""
    source_frames = np.asarray(source_frames)
    left = int(np.searchsorted(source_frames, start))
    right = int(np.searchsorted(source_frames, end))
    if (start > end or right >= len(source_frames) or left >= len(source_frames)
            or source_frames[left] != start or source_frames[right] != end
            or right - left != end - start):
        return None
    return left, right
