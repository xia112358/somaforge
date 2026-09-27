"""Frame selection for certified stationary intervals, without pose blending.

This module does not detect contact or certify a hold. The caller supplies
verified source intervals and must audit the new seams on the edited motion.
"""
import numpy as np


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
