"""Compact canonical collision regions and actual-Newton witness attribution.

Regions partition physical body coordinates; they never define contact truth.
Only selected, activated and allocated Newton pairs produce contact labels.
"""
import itertools

import torch
from torch import nn

from somaforge_core import CONTACT_BODY_NAMES_BY_PART
from somaforge_core.motion_contracts import BODY_NAMES
from contact_solver.part_collision_geometry import PartCollisionGeometry
from somaforge_core.heightmap import HEIGHTMAP_ROWS, HEIGHTMAP_COLS, HEIGHTMAP_FORWARD_MIN_M, HEIGHTMAP_LATERAL_MIN_M, HEIGHTMAP_RESOLUTION_M


CONTACT_INTERVAL_SCHEMA = 'native_activation_upper_gap_v1'
PART_NAMES = ('left_foot', 'right_foot', 'left_hand', 'right_hand', 'left_knee', 'right_knee')


class ContactRegions(nn.Module):
    schema = 'canonical_contact_regions_4_4_2_2_3_3_v1'
    feature_count = 32
    names = (('rear_negative_y', 'rear_positive_y', 'front_negative_y', 'front_positive_y'),)*2 + (
        ('proximal', 'distal'),)*2 + (('lower_shin', 'middle_shin', 'knee_end'),)*2

    def __init__(self, fk):
        super().__init__()
        source = PartCollisionGeometry(fk)
        # Fixed, actual surface samples provide compact regional landmarks.
        # Spheres use 26 analytical surface directions, not an enclosing box.
        directions = torch.tensor([x for x in itertools.product((-1., 0., 1.), repeat=3) if any(x)])
        directions = directions/directions.norm(dim=-1, keepdim=True)
        lows, highs, clouds = [], [], []
        for part in range(6):
            v, c, r = (getattr(source, f'{name}_{part}') for name in ('vertices', 'centers', 'radii'))
            sphere = (c[:, None]+r[:, None, None]*directions.to(c)).reshape(-1, 3)
            cloud = torch.cat((v, sphere))
            clouds.append(cloud)
            lows.append(cloud.amin(0)); highs.append(cloud.amax(0))
        self.register_buffer('low', torch.stack(lows), persistent=False)
        self.register_buffer('high', torch.stack(highs), persistent=False)
        self.register_buffer('valid', torch.arange(4)[None] < torch.tensor([4, 4, 2, 2, 3, 3])[:, None], persistent=False)
        landmarks, extents = [], []
        self.asset_counts = source.asset_counts
        for part, cloud in enumerate(clouds):
            ids = self.classify_local(torch.full((len(cloud),), part, dtype=torch.long), cloud)
            points, sizes = [], []
            for region in range(4):
                if not self.valid[part, region]:
                    points.append(cloud.new_zeros(3)); sizes.append(cloud.new_zeros(3)); continue
                section = cloud[ids == region]
                if not len(section): raise ValueError(f'Empty canonical region {part}/{region}')
                lo, hi = section.amin(0), section.amax(0)
                desired = (lo+hi)/2
                # Sole / hand underside; anterior shin for kneeling contacts.
                desired[2 if part < 4 else 0] = lo[2] if part < 4 else hi[0]
                point = section[(section-desired).square().sum(-1).argmin()]
                points.append(point); sizes.append(hi-lo)
                self.register_buffer(f'cloud_{part}_{region}', section, persistent=False)
            landmarks.append(torch.stack(points)); extents.append(torch.stack(sizes))
        self.register_buffer('landmark', torch.stack(landmarks), persistent=False)
        self.register_buffer('extent', torch.stack(extents), persistent=False)
        subsets = ((torch.arange(1, 16)[:, None] >> torch.arange(4)) & 1).bool()
        self.register_buffer('subsets', subsets, persistent=False)
        self.register_buffer('valid_subsets', ~(subsets[None] & ~self.valid[:, None]).any(-1), persistent=False)

    def classify_local(self, part, points):
        middle = (self.low[part]+self.high[part])/2
        foot = 2*(points[..., 0] >= middle[..., 0]).long()+(points[..., 1] >= middle[..., 1]).long()
        hand = (points[..., 0] >= middle[..., 0]).long()
        shin = ((points[..., 2]-self.low[part, 2])/(self.high[part, 2]-self.low[part, 2])*3).floor().long().clamp(0, 2)
        return torch.where(part < 2, foot, torch.where(part < 4, hand, shin))

    def witness_regions(self, fk, q, sample, part, points):
        position, rotation = fk.link_poses(q, BODY_NAMES[1:7])
        local = torch.einsum('nij,nj->ni', rotation[sample, part].transpose(-1, -2), points-position[sample, part])
        return self.classify_local(part, local.detach())

    def actual_mask(self, fk, rows, surface):
        from contact_solver.device_contact_objective import group_any
        p = rows.pair; part = p['part'].clamp(0, 5)
        region = self.witness_regions(fk, rows.q, p['sample'], part, rows.points[:, 1])
        eligible = p['eligible'] & (p['primary_surface'] == surface[p['sample'], part])
        return group_any((p['sample']*6+part)*4+region, eligible, len(rows)*24).reshape(len(rows), 6, 4)

    def audit_pairs(self, fk, q, pairs, surface, planned_regions):
        """Audit a single pose using already primary-face-selected Newton pairs."""
        actual = torch.zeros(6, 4, dtype=torch.bool, device=q.device)
        records = [p for p in pairs if p['surface'] == int(surface[p['part']])]
        if records:
            if any(not p['allocated'] or not p['constraint_active'] for p in records):
                raise ValueError('Region audit requires actual activated+allocated pairs')
            part = torch.tensor([p['part'] for p in records], device=q.device)
            point = q.new_tensor([p['position_w'] for p in records])
            region = self.witness_regions(fk, q, torch.zeros_like(part), part, point)
            actual[part, region] = True
        required = planned_regions.to(device=q.device, dtype=torch.bool)
        missing = required & ~actual
        return {'schema': self.schema, 'actual_regions': actual.tolist(),
            'planned_regions': required.tolist(), 'missing_regions': missing.tolist(),
            'realized': bool(required.any() and not missing.any())}

    def forward(self, position, rotation, heightmap):
        point = position[:, :, None]+torch.einsum('bpij,prj->bpri', rotation, self.landmark)
        x = (point[..., 0]-HEIGHTMAP_FORWARD_MIN_M)/HEIGHTMAP_RESOLUTION_M
        y = (point[..., 1]-HEIGHTMAP_LATERAL_MIN_M)/HEIGHTMAP_RESOLUTION_M
        visible = (x >= 0) & (x <= HEIGHTMAP_ROWS-1) & (y >= 0) & (y <= HEIGHTMAP_COLS-1) & self.valid
        cell = x.round().long().clamp(0, HEIGHTMAP_ROWS-1)*HEIGHTMAP_COLS+y.round().long().clamp(0, HEIGHTMAP_COLS-1)
        gap = point[..., 2]-heightmap.flatten(1).gather(1, cell.flatten(1)).reshape_as(x)
        offset = point-position[:, :, None]
        feature = torch.cat((offset/.1, self.extent[None].expand(len(point), -1, -1, -1)/.1,
            torch.where(visible, gap, 0)[..., None]/.1, visible[..., None].to(point)), -1)
        return (feature*self.valid[None, :, :, None]).flatten(2)

    def missing_region_distance(self, fk, q, surface, scene, margin):
        """Loss-only finite-face approach proxy, never a contact label.

        Uses each region's full mesh vertices and analytical sphere surface
        samples. Exact actual Newton witnesses replace this proxy on arrival.
        """
        position, rotation = fk.link_poses(q, BODY_NAMES[1:7])
        top_normal = scene['box_rotation'][:, :, 2]
        top_center = scene['box_center']+top_normal*scene['box_half_extents'][:, 2:3]
        result = q.new_zeros(len(q), 6, 4)
        for part in range(6):
            for region in range(len(self.names[part])):
                cloud = getattr(self, f'cloud_{part}_{region}')
                point = position[:, part, None]+torch.einsum('bij,vj->bvi', rotation[:, part], cloud)
                ground_gap = point[..., 2]-scene['ground_height'][:, None]
                delta = point-top_center[:, None]
                box_local = torch.einsum('bvi,bij->bvj', delta, scene['box_rotation'])
                outside = (box_local[..., :2].abs()-scene['box_half_extents'][:, None, :2]).relu().square().sum(-1)
                gap = torch.where(surface[:, part, None] == 0, ground_gap, box_local[..., 2])
                cost = (gap-margin[:, None]).relu().square()+(-gap).relu().square()
                cost = cost+torch.where(surface[:, part, None] == 0, 0, outside)
                result[:, part, region] = cost.amin(-1)/(.25*margin).square()
        return result


def unified_region_objective(model, rows, active, surface, scene, planned_regions=None, *, audit_path=None, release_mask=None):
    """One interval-violation objective across intended regions and all bodies."""
    from contact_solver.device_contact_objective import reduce_groups, group_any
    geometry = model.region_geometry
    if release_mask is not None:
        if release_mask.shape != active.shape or release_mask.dtype != torch.bool:
            raise ValueError('Release mask must be boolean with the contact intent shape')
        if bool((release_mask & active).any()):
            raise ValueError('Required contact and release intents conflict')
    p = rows.pair; q = rows.q; batch = len(q); sample = p['sample']
    scale = .25*rows.observed['configured_margin']
    if bool((scale <= 0).any()): raise ValueError('Unified loss needs actual positive configured margins')
    relevant = (p['full_kind'] >= 0)
    invalid = relevant & (p['dist'] < 0) & ~rows.normal_valid
    invalid_counts = torch.zeros(batch, device=q.device).scatter_add(0, sample, invalid.float())
    if bool(invalid.any()):
        if audit_path is None:
            raise ValueError('Invalid penetrating full-body normal requires explicit audit and sample rejection')
        import json
        ids=(invalid_counts > 0).nonzero().flatten()
        with open(audit_path, 'a') as stream:
            stream.write(json.dumps({'schema':'newton_unknown_region_gradient_v1',
                'action':'whole_sample_excluded_from_training_and_rollout',
                'q':q[ids].detach().cpu().tolist(), 'sample_indices':ids.cpu().tolist(),
                'link_names':list(rows.observed['link_names']),
                'world_frame':None if rows.world_frame is None else [x[ids].detach().cpu().tolist() for x in rows.world_frame],
                'pairs':{k:v[invalid].detach().cpu().tolist() for k,v in p.items()},
                'transformed_normal':rows.transformed_normal[invalid].detach().cpu().tolist()})+'\n')
    part = p['part'].clamp(0, 5)
    region = geometry.witness_regions(model.fk, q, sample, part, rows.points[:, 1])
    region_group = (sample*6+part)*4+region
    match = p['task_pair'] & p['upward'] & (p['primary_surface'] == surface[sample, part])
    desired = (geometry.valid[None] & active[..., None] if planned_regions is None else planned_regions & active[..., None])
    # A coarse intended part needs one region; an explicit plan needs every
    # selected region. Neither forces all other regions to touch or lift.
    # Use the same upper boundary as the existing execution interval loss.
    # Activation/allocation remain native evidence; a zero gap residual alone
    # neither certifies contact nor turns off a frozen-witness gradient.
    upper = ((rows.distances-p['includemargin']).relu()/scale[sample]).square()
    near = reduce_groups(upper, region_group, match, batch*24, minimum=True).reshape(batch, 6, 4)
    exists = group_any(region_group, match, batch*24).reshape(batch, 6, 4)
    approach = geometry.missing_region_distance(model.fk, q, surface, scene, rows.observed['configured_margin'])
    near = torch.where(exists, near, approach)
    if planned_regions is None:
        best = near.masked_fill(~geometry.valid, torch.inf).argmin(-1)
        desired = torch.nn.functional.one_hot(best, 4).bool() & active[..., None]
    near = torch.where(desired, near, 0)
    # Contact regions share groups across all attached shapes. Other body
    # links retain independent groups; every raw terrain/self pair is audited.
    link_names = rows.observed['link_names']; groups_per_sample = 24+len(link_names)
    mapping = {name:i for i,key in enumerate(PART_NAMES) for name in CONTACT_BODY_NAMES_BY_PART[key]}
    link_part = torch.tensor([mapping.get(n, -1) for n in link_names], device=q.device)
    costs, groups, valid = [], [], []
    for side in (0, 1):
        link = p[f'body_link{side}']; lp = link_part[link.clamp_min(0)]
        rp = geometry.witness_regions(model.fk, q, sample, lp.clamp_min(0), rows.points[:, side])
        slot = torch.where(lp >= 0, lp*4+rp, 24+link.clamp_min(0))
        # Existing task acceptance permits only shallow extra activations;
        # derive the unwanted-part lower bound from each real pair margin.
        released = ~active if release_mask is None else release_mask
        unwanted = (side == 1) & p['task_pair'] & p['upward'] & released[sample, part]
        from contact_solver.interaction_acceptance import DEFAULT_ACCEPTANCE
        # Legacy complete plans tolerate shallow extra activations. An explicit
        # event release instead targets the actual activation boundary.
        fraction = 1-DEFAULT_ACCEPTANCE.extra_activation_margin_fraction if release_mask is None else 1.
        lower = torch.where(unwanted, fraction*p['includemargin'], 0)
        costs.append(((lower-rows.distances).relu()/scale[sample]).square())
        groups.append(sample*groups_per_sample+slot)
        valid.append(relevant & (link >= 0))
    lower_cost = reduce_groups(torch.cat(costs), torch.cat(groups), torch.cat(valid), batch*groups_per_sample).reshape(batch, groups_per_sample)
    upper_cost = torch.cat((near.flatten(1), q.new_zeros(batch, len(link_names))), -1)
    # The same robust interval penalty applies on both sides. A far missing
    # contact must not dominate all near-surface clearances quadratically.
    def penalty(cost):
        return torch.where(cost <= 1, cost, 2*cost.clamp_min(1).sqrt()-1)
    lower_penalty, upper_penalty = penalty(lower_cost), penalty(upper_cost)
    # Different witnesses in one anatomical region can violate opposite
    # bounds (e.g. top-face separation and a side/self penetration). Keep
    # both derivatives instead of hiding the smaller cost behind max().
    error = lower_penalty+upper_penalty
    # Fixed anatomical normalization: adding a new small collision must not
    # lower the average by increasing a count of currently violating groups.
    group_count = geometry.valid.sum()+(link_part < 0).sum()
    loss = error.sum(-1)/group_count.clamp_min(1)+error.amax(-1)
    # Exact additive diagnostics, including the equal-share subgradient used
    # by amax at ties. These terms sum to loss; they are not extra penalties.
    dominant = (error == error.amax(-1, keepdim=True)).to(error)
    dominant = (dominant/dominant.sum(-1, keepdim=True)).detach()
    attraction = upper_penalty.sum(-1)/group_count.clamp_min(1)+(upper_penalty*dominant).sum(-1)
    separation = lower_penalty.sum(-1)/group_count.clamp_min(1)+(lower_penalty*dominant).sum(-1)
    valid_sample = invalid_counts == 0
    loss = loss*valid_sample
    actual = geometry.actual_mask(model.fk, rows, surface)
    realized = ((actual | ~desired).all((-1, -2)) & active.any(-1))
    return loss, dict(unified_region_loss=loss, region_plan_realized=realized.float(),
        unified_attraction_component=attraction*valid_sample,
        unified_separation_component=separation*valid_sample,
        region_missing_count=(desired & ~actual).sum((-1, -2)).float(),
        region_lower_bound_violating_groups=(lower_cost > 0).sum(-1).float(),
        region_gradient_valid=valid_sample.float(), region_invalid_penetrating_normals=invalid_counts,
        region_invalid_nonpenetrating_normals=torch.zeros(batch, device=q.device).scatter_add(0, sample,
            (relevant & (p['dist'] >= 0) & ~rows.normal_valid).float()))
