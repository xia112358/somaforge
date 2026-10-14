"""Preserved experiment helpers for regression tests; no training CLI."""
import torch
from generator.research.archived_experiments.direct_contact_infiller import DirectContactInfiller
from generator.neural_infiller import _matrix_from_rotation6d
from contact_solver.surface_contact_proxy import primary_face_cost

def scene_faces(scene):
    (center, rotation, half, ground) = (scene[k] for k in ('box_center', 'box_rotation', 'box_half_extents', 'ground_height'))
    top = torch.cat((center + rotation[:, :, 2] * half[:, 2:3], rotation[:, :, 2], rotation[:, :, 0], rotation[:, :, 1], half[:, :2], torch.zeros_like(ground[:, None])), -1)
    floor = torch.zeros_like(top)
    floor[:, 2] = ground
    floor[:, 5] = 1
    floor[:, 6] = 1
    floor[:, 10] = 1
    floor[:, 14] = 1
    return torch.stack((floor, top), 1)

class DirectSurfaceInfiller(DirectContactInfiller):

    def surface_contact_objective(self, b, q, pos, rotation):
        (B, T) = q.shape[:2]
        c = b['contract']
        phase = b['phase']
        persistent = c['persistent_support'].bool() & c['start_contact'].bool() & c['active_contact'].bool()
        demo = b['supervision_kind'] == 'demonstration'
        if demo:
            active = b['task_contact_mask'].bool()
            surface = b['task_contact_surface'].long()
        else:
            persistent3 = persistent[:, None].expand(-1, T, -1)
            leaving = (c['start_contact'].bool() & ~persistent)[:, None] & (phase <= 0.2)
            arriving = (c['active_contact'].bool() & ~persistent)[:, None] & (phase >= 0.8)
            active = persistent3 | leaving | arriving
            surface = torch.where(arriving, c['contact_surface'][:, None], c['start_surface'][:, None]).expand(-1, T, -1).long()
        (points, parts) = self.geometry(self.fk, q)
        faces = scene_faces(b['scene'])[:, None].expand(-1, T, -1, -1).reshape(B * T, 2, 15)
        cloud = points.reshape(B * T, -1, 3)
        (face_cost, _, face_excess, face_edge) = primary_face_cost(cloud, parts, faces, b['solver_margin'][:, None].expand(-1, T, -1, -1).reshape(B * T, 6, 2))
        idx = surface.clamp_min(0)[..., None]
        known = b['solver_margin_known'][:, None].expand(-1, T, -1, -1).gather(3, idx)[..., 0]
        if demo and (active & ~known).any():
            raise ValueError('Unknown margin for demonstrated active contact')
        used = active & known
        excess = face_excess.reshape(B, T, 6, 2).gather(3, idx)[..., 0] * used

        def masked(value, mask):
            return (value * mask).sum((1, 2)) / mask.sum((1, 2)).clamp_min(1)
        start_offset = torch.einsum('bpji,bpj->bpi', rotation[:, 0], pos[:, 0, 1:7] - c['start_anchor_world'])
        material = pos[:, :, 1:7] - torch.einsum('btpij,bpj->btpi', rotation, start_offset)
        hold = active & persistent[:, None]
        drift = (material - c['start_anchor_world'][:, None]).norm(dim=-1)
        face_cost = face_cost.reshape(B, T, 6, 2).gather(3, idx)[..., 0]
        face_edge = face_edge.reshape(B, T, 6, 2).gather(3, idx)[..., 0]
        contact = 12 * masked(face_cost / 0.005 ** 2, used) + 10 * masked((drift / 0.005).square(), hold)
        if demo:
            ref = _matrix_from_rotation6d(b['reference_rotation'])
            contact = contact + 0.2 * masked(((rotation - ref) / 0.2).square().mean((-1, -2)), active)
        return (contact, dict(surface_margin_excess_mean_cm=100 * masked(excess, used), surface_face_ownership_excess_max_cm=100 * (face_edge * used).amax((1, 2)), surface_margin_excess_max_cm=100 * excess.amax((1, 2)), persistent_mean_cm=100 * masked(drift, hold), persistent_count=hold.sum((1, 2)), unknown_intent_margin_count=(active & ~known).sum((1, 2)).float(), realized_label_supervision=q.new_full((B,), float(demo))))
