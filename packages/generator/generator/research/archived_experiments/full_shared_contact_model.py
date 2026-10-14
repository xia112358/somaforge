"""Preserved experiment helpers for regression tests; no training CLI."""
import torch
from torch import nn
from generator.neural_infiller import CanonicalG1CollisionPoints, _matrix_from_rotation6d, _quaternion_matrix_wxyz
from generator.trajectory_budget import densify_qpos
from generator.unified_interaction import _collision_depth_cost
from contact_solver.research.sampled_penetration import penetration as fast_penetration
from generator.research.archived_experiments.infiller_fk_fast import InfillerFK
COLLISION_TOLERANCE_M = 0.002

class FullSharedContact(nn.Module):

    def __init__(self, limits):
        super().__init__()
        self.network = nn.Sequential(nn.Linear(218, 128), nn.Tanh(), nn.Linear(128, 128), nn.Tanh(), nn.Linear(128, 36))
        nn.init.zeros_(self.network[-1].weight)
        nn.init.zeros_(self.network[-1].bias)
        self.fk = InfillerFK()
        self.geometry = CanonicalG1CollisionPoints(24)
        self.register_buffer('scale', torch.tensor([0.3] * 3 + [0.5] * 4 + [1.0] * 29))
        self.keys = list(limits)
        self.register_buffer('limits', torch.tensor([limits[k] for k in self.keys]))

    def decode(self, b):
        base = b['base']
        phase = b['phase']
        q = base + 4 * phase * (1 - phase) * self.scale * torch.tanh(self.network(b['inputs']))
        q = torch.cat((q[..., :3], nn.functional.normalize(q[..., 3:7], dim=-1), q[..., 7:].clamp(self.fk.joint_lower, self.fk.joint_upper)), -1)
        return torch.cat((base[:, :2], q[:, 2:-2], base[:, -2:]), 1)

    @torch.no_grad()
    def prepare(self, b):
        """Cache terms that cannot change during residual training."""
        c = b['contract']
        phase = b['phase']
        T = b['base'].shape[1]
        (bp, br) = self.fk(b['base'][:, :1])
        br = _matrix_from_rotation6d(br)[:, 0, 1:7]
        start = torch.einsum('bpji,bpj->bpi', br, bp[:, 0, 1:7] - c['start_anchor_world'])
        persistent = c['persistent_support'].bool() & (c['start_contact'] > 0.5) & c['active_contact'].bool()
        pm = persistent[:, None].expand(-1, T, -1)
        tm = (c['active_contact'].bool() & ~persistent)[:, None] & (phase >= 0.8)
        lm = ((c['start_contact'] > 0.5) & ~persistent)[:, None] & (phase <= 0.2)
        ref = _matrix_from_rotation6d(b['reference_rotation'])
        b['prepared'] = dict(offsets=(1 - phase[..., None]) * start[:, None] + phase[..., None] * c['contact_local_offset'][:, None], pm=pm, tm=tm, lm=lm, desired=pm | tm | lm, targets=torch.where(tm[..., None], c['end_anchor_world'][:, None], c['start_anchor_world'][:, None]), ref=ref, refstep=ref[:, :-1].transpose(-1, -2) @ ref[:, 1:])
        if 'task_contact_mask' in b:
            actual = b['task_contact_mask'].bool()
            pm = actual & persistent[:, None]
            tm = actual & ~persistent[:, None] & (phase >= 0.5)
            lm = actual & ~persistent[:, None] & (phase < 0.5)
            (p, r) = self.fk(b['base'])
            offsets = torch.einsum('btpji,btpj->btpi', _matrix_from_rotation6d(r)[:, :, 1:7], p[:, :, 1:7] - b['task_contact_position_w'])
            b['prepared'].update(offsets=offsets, pm=pm, tm=tm, lm=lm, desired=actual, targets=b['task_contact_position_w'])
        return b

    def objective(self, b):
        q = self.decode(b)
        c = b['contract']
        phase = b['phase']
        (B, T) = q.shape[:2]
        dense = densify_qpos(q, 10)
        (points, parts) = self.geometry(self.fk, dense)
        (box, ground) = fast_penetration(points, parts, q.new_zeros((B, dense.shape[1], 6)), **b['scene'])
        collision = q.new_zeros(B)
        for (penetration, kind) in ((box, 'box'), (ground, 'ground')):
            excess = (penetration - COLLISION_TOLERANCE_M).relu() / 0.01
            fm = excess.amax(-1)
            occupancy = (1 - torch.exp(-fm)).mean(-1)
            if kind == 'box':
                cost = _collision_depth_cost(excess, 'exponential')
                fc = cost.amax(-1)
                value = cost.mean((1, 2)) + 0.25 * fc.mean(-1) + 0.25 * fc.amax(-1) + 0.25 * occupancy
            else:
                fc = _collision_depth_cost(fm, 'exponential')
                value = fc.mean(-1) + fc.amax(-1) + 0.25 * occupancy
            collision = collision + 10 * value
        (pos, rot6) = self.fk(q)
        rot = _matrix_from_rotation6d(rot6)[:, :, 1:7]
        if 'prepared' not in b:
            self.prepare(b)
        fixed = b['prepared']
        offsets = fixed['offsets']
        cp = pos[:, :, 1:7] - torch.einsum('btpij,btpj->btpi', rot, offsets)
        (pm, tm, lm, desired, targets) = (fixed[k] for k in ('pm', 'tm', 'lm', 'desired', 'targets'))
        residual = (cp - targets).norm(dim=-1)

        def masked(value, mask):
            return (value * mask).sum((1, 2)) / mask.sum((1, 2)).clamp_min(1)
        contact = 10 * masked(residual.square(), pm) / 0.005 ** 2 + 12 * masked(residual.square(), tm) / 0.005 ** 2 + 6 * masked(residual.square(), lm) / 0.005 ** 2
        ref = fixed['ref']
        orientation = masked(((rot - ref) / 0.2).square().mean((-1, -2)), desired)
        step = rot[:, :-1].transpose(-1, -2) @ rot[:, 1:]
        refstep = fixed['refstep']
        angular = masked(((step - refstep) / 0.05).square().mean((-1, -2)), desired[:, :-1] & desired[:, 1:])
        contact = contact + 10 * orientation + 2 * angular
        deviation = ((q - b['base']) / self.scale).square().mean((1, 2))
        acceleration = ((q[:, 2:] - 2 * q[:, 1:-1] + q[:, :-2]) / self.scale).square().mean((1, 2))
        smooth = {}
        for (name, signal) in {'root': q[..., :3], 'joint': q[..., 7:], 'rotation_matrix': _quaternion_matrix_wxyz(q[..., 3:7]).flatten(-2)}.items():
            for order in (1, 2, 3):
                d = torch.diff(signal, n=order, dim=1)
                mag = d.abs().amax(-1) if name == 'joint' else d.norm(dim=-1)
                smooth[f'{name}_d{order}_peak'] = mag.amax(-1)
                smooth[f'{name}_d{order}_rms'] = mag.norm(dim=-1) / mag.shape[1] ** 0.5
        ratios = torch.stack([smooth[k] for k in self.keys], -1) / self.limits
        excess = (ratios - 1).relu().square()
        budget = excess.mean(-1) + excess.amax(-1)
        extra = {}
        if hasattr(self, 'surface_contact_objective'):
            (contact, extra) = self.surface_contact_objective(b, q, pos, rot)
        total = contact + collision + 0.01 * deviation + 0.1 * acceleration + 2000 * budget
        metrics = dict(loss=total, contact_loss=contact, collision_loss=collision, budget_penalty=budget, actual_contact_mean_cm=100 * masked(residual, desired), persistent_mean_cm=100 * masked(residual, pm), persistent_count=pm.sum((1, 2)), penetration_max_cm=100 * torch.maximum(box, ground).amax((1, 2)), root_second_difference_cm=100 * smooth['root_d2_peak'])
        if extra:
            metrics['material_anchor_diagnostic_cm'] = metrics.pop('actual_contact_mean_cm')
            metrics.update(extra)
        return (total, q, metrics)

def batch(records, device):

    def transfer(tensor):
        return tensor.to(device=device, dtype=torch.float32 if tensor.is_floating_point() else tensor.dtype)
    result = {k: transfer(torch.stack([r[k] for r in records])) for k in ('base', 'inputs', 'phase', 'reference_rotation')}
    for key in ('task_contact_mask', 'task_contact_position_w', 'task_contact_surface', 'solver_margin', 'solver_margin_known'):
        if key in records[0]:
            result[key] = transfer(torch.stack([r[key] for r in records]))
    kinds = {r.get('supervision_kind', 'demonstration') for r in records}
    if len(kinds) != 1:
        raise ValueError('Do not mix actual labels and predicted intents in a batch')
    result['supervision_kind'] = next(iter(kinds))
    result['contract'] = {k: transfer(torch.stack([r['contract'][k] for r in records])) for k in records[0]['contract']}
    result['scene'] = {k: transfer(torch.cat([r['scene'][k] for r in records])) if torch.is_tensor(v) else v for (k, v) in records[0]['scene'].items()}
    return result
