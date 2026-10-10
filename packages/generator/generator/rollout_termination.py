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


def physical_reset_masks(q, penetration_cm, invalid_witnesses, joint_violation_rad,
                         actual_contact, limits=TerminationLimits()):
    """Episode failures using already validated primary-face Newton contacts.

    Missing contact evidence is an error, never a geometry/intent fallback.
    Reasons are mutually exclusive: invalid state, deep penetration, no contact.
    """
    import torch
    if actual_contact is None or actual_contact.dtype != torch.bool or actual_contact.shape != (len(q), 6):
        raise ValueError('Expected actual Newton primary-face contact mask [B,6]')
    invalid = (~torch.isfinite(q).all(-1) | ~torch.isfinite(penetration_cm)
               | ~torch.isfinite(joint_violation_rad) | (invalid_witnesses != 0)
               | ((q[:,3:7].norm(dim=-1)-1).abs() > 1e-3)
               | (joint_violation_rad > limits.joint_excess_rad))
    deep = ~invalid & (penetration_cm > 100*limits.penetration_m)
    no_contact = ~invalid & ~deep & ~actual_contact.any(-1)
    reasons = dict(invalid=invalid, severe_penetration=deep, no_contact=no_contact)
    return ~(invalid | deep | no_contact), reasons


def native_continuation_masks(q, metrics, actual_contact, *, pair=None,
                              limits=TerminationLimits()):
    """Use actual contacts and complete penetration distances for boundaries.

    A conservative shape/box support-plane bound is not a penetration depth.
    Its negative value must not veto an otherwise valid native pose query.
    """
    import torch
    required = ('newton_penetration_cm', 'newton_invalid_fullbody_witnesses',
                'joint_violation_rad')
    if any(key not in metrics for key in required):
        raise ValueError('Missing actual Newton continuation metrics')
    invalid = metrics['newton_invalid_fullbody_witnesses'].clone()
    if pair is not None:
        required_pair = ('type', 'dist', 'includemargin', 'active',
                         'constraint_allocated', 'sample')
        if any(key not in pair for key in required_pair):
            raise ValueError('Missing actual Newton activation/allocation fields')
        active = ((pair['type'].long() & 1) != 0) & (pair['dist'] < pair['includemargin'])
        if not torch.equal(active, pair['active']):
            raise ValueError('Newton activation metadata mismatch')
        bad = active & ~pair['constraint_allocated']
        invalid.scatter_add_(0, pair['sample'], bad.to(invalid))
    depth = metrics['newton_penetration_cm']
    if 'solid_penetration_cm' in metrics:
        # Signed GJK/EPA on the enabled native solids is an actual depth,
        # unlike the old conservative support-plane diagnostic.
        depth = torch.maximum(depth, metrics['solid_penetration_cm'])
    return physical_reset_masks(q, depth, invalid,
        metrics['joint_violation_rad'], actual_contact, limits)


def demonstration_loss(value, supervised):
    """Zero demonstration terms on rows with no remaining demonstration target."""
    import torch
    return torch.where(supervised, value, torch.zeros_like(value))
