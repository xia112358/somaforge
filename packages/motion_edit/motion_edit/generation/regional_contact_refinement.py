"""Use the training interval objective with arbitrary event-bound finite faces."""
import torch
from contact_solver.contact_regions import ContactRegions, unified_region_objective
from contact_solver.device_contact_objective import DeviceWitnessRows, group_any
from contact_solver.contact_surface_interval import finite_face_band_cost, convex_face_tangent_distance
from .surface_contact_loss import face_edges


class EventContactRegions(ContactRegions):
    """Same canonical regions; generic authored faces replace box-only guidance."""
    def missing_region_distance(self, fk, q, surface, scene, margin):
        from somaforge_core.motion_contracts import BODY_NAMES
        position, rotation = fk.link_poses(q, BODY_NAMES[1:7])
        result = q.new_zeros(len(q), 6, 4)
        groups = {}
        wanted = scene['wanted'].detach().cpu().tolist()
        for sample, active in enumerate(wanted):
            for part in range(6):
                if not active[part]:
                    continue
                geometry = scene['domains'][sample][part]
                if geometry is None:
                    raise ValueError('Missing event-bound finite face for regional approach')
                # Group the same authored geometry without changing its surface identity.
                key = (part, id(geometry))
                groups.setdefault(key, (geometry, []))[1].append(sample)
        for (part, _), (geometry, samples) in groups.items():
            normal, edges, offsets = face_edges(geometry)
            from somaforge_core.contact_face_selection import upward_face_mask
            if not upward_face_mask([normal])[0]:
                raise ValueError('Regional approach requires an upward event surface')
            indices = torch.tensor(samples, device=q.device)
            normal = q.new_tensor(normal); origin = q.new_tensor(geometry['origin'])
            for region in range(len(self.names[part])):
                cloud = getattr(self, f'cloud_{part}_{region}')
                points = position[indices, part, None]+torch.einsum('bij,vj->bvi', rotation[indices, part], cloud)
                gap = (points-origin)@normal
                outside = torch.zeros_like(gap[..., None])
                if len(edges):
                    outside = convex_face_tangent_distance(points, normal,
                        q.new_tensor(geometry['polygon_world']), q.new_tensor(edges), q.new_tensor(offsets))
                cost = finite_face_band_cost(gap, outside, margin[indices, None])
                result[indices, part, region] = cost.amin(-1)/(.25*margin[indices]).square()
        return result


def regional_terms(fk, geometry, q, observed, wanted, faces, domains, release_mask=None, *, solid=None):
    """One exact shared loss; activation/allocation remain separate evidence."""
    from types import SimpleNamespace
    rows = DeviceWitnessRows(fk, q, observed)
    pair = rows.pair
    actual = ((pair['type'].long() & 1) != 0) & (pair['dist'] < pair['includemargin'])
    if not torch.equal(actual, pair['active']):
        raise ValueError('Inconsistent native activation')
    if bool((actual & ~pair['constraint_allocated']).any()):
        raise ValueError('Unallocated native contact')
    rows.solid = solid
    if release_mask is None:
        release_mask = torch.zeros_like(wanted)
    loss, metrics = unified_region_objective(
        SimpleNamespace(fk=fk, region_geometry=geometry), rows, wanted, faces,
        dict(domains=domains, wanted=wanted), release_mask=release_mask)
    part = pair['part'].clamp(0, 5)
    match = pair['task_pair'] & pair['upward'] & (pair['primary_surface'] == faces[pair['sample'], part])
    group = pair['sample']*6+part
    exists = group_any(group, match, len(q)*6).reshape(len(q), 6)
    realized = group_any(group, match & pair['eligible'], len(q)*6).reshape(len(q), 6)
    metrics['matched_candidate_exists'] = exists
    metrics['matched_contact_realized'] = realized
    any_contact = group_any(group, pair['task_pair'] & pair['upward'] & pair['eligible'], len(q)*6).reshape(len(q), 6)
    metrics['release_violations'] = release_mask & any_contact
    depth, invalid = rows.full_body()
    if bool(invalid.any()):
        raise ValueError('Invalid penetrating native normal')
    depth = torch.maximum(depth, solid.depths().amax(-1))
    return loss, depth, wanted & ~exists, wanted & ~realized, metrics
