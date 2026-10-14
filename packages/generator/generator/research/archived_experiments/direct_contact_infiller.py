"""Preserved experiment helpers for regression tests; no training CLI."""
import torch
from torch import nn
from generator.research.archived_experiments.full_shared_contact_model import FullSharedContact

class DirectContactInfiller(FullSharedContact):

    def __init__(self, limits):
        super().__init__(limits)
        self.network = nn.Sequential(nn.Linear(182, 256), nn.Tanh(), nn.Linear(256, 256), nn.Tanh(), nn.Linear(256, 256), nn.Tanh(), nn.Linear(256, 36))
        nn.init.zeros_(self.network[-1].weight)
        nn.init.zeros_(self.network[-1].bias)

    def forward(self, start, end, phase, contract, scene, duration):
        """World qpos boundaries [B,36], phase [B,T,1]; output [B,T,36].

        The analytical boundary interpolation is part of this decoder, not an
        upstream learned trajectory. Quaternion sign alignment takes the short
        interpolation branch; returned boundary representations remain exact.
        """
        origin = start[:, :3]
        (a, z) = (start.clone(), end.clone())
        a[:, :3] -= origin
        z[:, :3] -= origin
        z[:, 3:7] = torch.where((a[:, 3:7] * z[:, 3:7]).sum(-1, keepdim=True) < 0, -z[:, 3:7], z[:, 3:7])
        (norm_a, norm_z) = (a.clone(), z.clone())
        for v in (norm_a, norm_z):
            v[:, 3:7] = torch.where(v[:, 3:4] < 0, -v[:, 3:7], v[:, 3:7])
            v[:, 7:] /= torch.pi
        (c, s) = (contract, scene)
        static = torch.cat((norm_a, norm_z, (c['start_anchor_world'] - origin[:, None]).flatten(1), (c['end_anchor_world'] - origin[:, None]).flatten(1), c['contact_local_offset'].flatten(1), c['start_contact'].float(), c['active_contact'].float(), c['persistent_support'].float(), c['start_surface'].float(), c['contact_surface'].float(), s['box_center'] - origin, s['box_rotation'].flatten(1), s['box_half_extents'].flatten(1), (s['ground_height'].reshape(-1) - origin[:, 2])[:, None], duration.reshape(-1, 1)), -1)
        features = torch.cat([phase] + [f(phase * torch.pi * k) for k in (1, 2, 4, 8) for f in (torch.sin, torch.cos)], -1)
        inputs = torch.cat((features, static[:, None].expand(-1, phase.shape[1], -1)), -1)
        u = phase
        blend = u.square() * (3 - 2 * u)
        q = (1 - blend) * a[:, None] + blend * z[:, None]
        q = q + 16 * u.square() * (1 - u).square() * self.scale * torch.tanh(self.network(inputs))
        q = torch.cat((q[..., :3] + origin[:, None], nn.functional.normalize(q[..., 3:7], dim=-1), q[..., 7:].clamp(self.fk.joint_lower, self.fk.joint_upper)), -1)
        return torch.cat((start[:, None], q[:, 1:-1], end[:, None]), 1)

    def decode(self, b):
        base = b['base']
        return self(base[:, 0], base[:, -1], b['phase'], b['contract'], b['scene'], base.new_full((base.shape[0],), (base.shape[1] - 1) / 50))
