"""Episode boundaries, not a replacement for Newton contact activation."""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class TerminationLimits:
    penetration_m: float = .03
    joint_excess_rad: float = .15
    stalled_steps: int = 8

def pose_failure(q,lower,upper,limits=TerminationLimits()):
    q=np.asarray(q)
    if q.shape!=(36,) or not np.isfinite(q).all():return 'nonfinite_pose'
    if abs(np.linalg.norm(q[3:7])-1)>1e-3:return 'invalid_quaternion'
    if np.maximum(lower-q[7:],q[7:]-upper).max()>limits.joint_excess_rad:return 'joint_limit'
    return None

def geometry_failure(separation,limits=TerminationLimits()):
    # Invalid geometry is unknown, never interpreted as certified penetration.
    if separation.get('invalid_penetrating_witnesses'):
        return 'invalid_geometry'
    for key in ('worst_terrain','worst_self','closest_terrain','closest_self'):
        w=separation.get(key)
        if w is not None:
            normal=np.asarray(w['normal_w'])
            if not np.isfinite(normal).all() or not np.isclose(np.linalg.norm(normal),1,atol=1e-4,rtol=0):
                return 'invalid_geometry'
    depth=max(separation['terrain_penetration_m'],separation['self_penetration_m'])
    if not np.isfinite(depth):return 'invalid_geometry'
    return 'large_penetration' if depth>limits.penetration_m else None

def training_rollout_safety_mask(q,penetration_cm,invalid_witnesses,joint_violation_rad,
                                 limits=TerminationLimits()):
    """Keep recoverable model states without redefining contact success.

    Contact mismatch is intentionally absent: it is precisely the error a
    self-fed correction rollout must retain.  This gate only mirrors the
    established episode safety boundaries.
    """
    import torch
    return (torch.isfinite(q).all(-1)
            & (invalid_witnesses == 0)
            & (penetration_cm <= 100.0*limits.penetration_m)
            & (joint_violation_rad <= limits.joint_excess_rad))

class ProgressWatch:
    def __init__(self,frame,limits=TerminationLimits()):
        self.frame=frame;self.stalled=0;self.limits=limits
    def update(self,frame):
        if frame is not None and frame>self.frame:self.frame=frame;self.stalled=0
        else:self.stalled+=1
        return 'stalled' if self.stalled>=self.limits.stalled_steps else None
