"""Explicit translation-only weak references; never realized contact labels."""
import numpy as np


def reference_offsets(frames, record):
    frames=np.asarray(frames,dtype=int)
    if not isinstance(record,dict):record=dict(base=record,windows=[])
    base=np.asarray(record['base'],dtype=float)
    if base.shape!=(3,) or not np.isfinite(base).all():raise ValueError('Invalid reference offset')
    result=np.broadcast_to(base,(len(frames),3)).copy()
    for window in record.get('windows',[]):
        a,b=window['frames'];delta=np.asarray(window['delta'],dtype=float)
        if not a<b or delta.shape!=(3,) or not np.isfinite(delta).all():raise ValueError('Invalid offset window')
        result[(frames>=a)&(frames<b)]+=delta
    return result
