"""Full1000 backbone with observed contact positions instead of surface IDs."""
from dataclasses import dataclass

import torch
from torch import nn

from .conditioned_pose_predictor import ConditionedHeightmapPosePredictor
from .neural_infiller import _matrix_from_rotation6d, _rotation6d
from .next_interaction_heightmap import (heightmap_grid, HEIGHTMAP_ROWS, HEIGHTMAP_COLS,
    HEIGHTMAP_FORWARD_MIN_M, HEIGHTMAP_LATERAL_MIN_M, HEIGHTMAP_RESOLUTION_M)
from .next_interaction_heightmap_v2 import _root_yaw_basis
from .planned_contact_predictor import PlannedContactPrediction


@dataclass(frozen=True)
class Full1000PositionPrediction(PlannedContactPrediction):
    teacher_conditioned: torch.Tensor
    region_logits: torch.Tensor | None = None
    planned_regions: torch.Tensor | None = None


class Full1000PositionPredictor(ConditionedHeightmapPosePredictor):
    """Preserve the original state/terrain/pose architecture and explicit plan.

    Only current Newton contact points and the heightmap enter forward. The
    hard planned point is an observed grid sample; no semantic face category
    exists in either the model parameters or the forward interface.
    """
    NEW_PREFIXES = ('role_head.', 'location_query.', 'location_key.', 'plan_position_encoder.')

    def __init__(self, width=192, layers=3, location_width=32, *, body_geometry=False, part_geometry=False,
                 region_plan=False, unified_contact=False, execution_plan_gradients=True):
        super().__init__(width, layers)
        if body_geometry and part_geometry:
            raise ValueError('Choose one geometry observation ablation')
        self.surface_embedding = None
        self.plan_surface_embedding = None
        self.role_head = nn.Linear(width, 4)
        self.location_query = nn.Linear(width, location_width)
        self.location_key = nn.Sequential(nn.Linear(3, width), nn.GELU(), nn.Linear(width, location_width))
        self.plan_position_encoder = nn.Linear(4, width)
        self.body_geometry = body_geometry
        self.part_geometry = part_geometry
        self.region_plan = region_plan
        self.execution_plan_gradients = execution_plan_gradients
        if region_plan or unified_contact:
            if body_geometry or part_geometry:
                raise ValueError('Regional experiment uses its own compact geometry input')
            from .contact_regions import ContactRegions
            self.region_geometry = ContactRegions(self.fk)
        if region_plan:
            self.region_geometry_encoder = nn.Sequential(nn.Linear(32, width), nn.GELU(), nn.Linear(width, width))
            self.region_head = nn.Linear(width, 15)
            self.region_prior = nn.Parameter(torch.zeros(6, 15))
            self.region_plan_encoder = nn.Linear(4, width, bias=False)
            nn.init.zeros_(self.region_geometry_encoder[-1].weight)
            nn.init.zeros_(self.region_geometry_encoder[-1].bias)
            nn.init.zeros_(self.region_plan_encoder.weight)
            nn.init.zeros_(self.region_head.weight)
            nn.init.zeros_(self.region_head.bias)
        if part_geometry:
            from .part_collision_geometry import PartCollisionGeometry
            self.part_geometry_observation = PartCollisionGeometry(self.fk)
            self.part_geometry_encoder = nn.Sequential(
                nn.Linear(PartCollisionGeometry.feature_count, width), nn.GELU(), nn.Linear(width, width))
            nn.init.zeros_(self.part_geometry_encoder[-1].weight)
            nn.init.zeros_(self.part_geometry_encoder[-1].bias)
        if body_geometry:
            names = tuple(sorted(set(self.geometry.link_names)))
            self.body_geometry_names = names
            lookup = {name: i for i, name in enumerate(names)}
            ids = torch.cat([torch.full((count,), lookup[name], dtype=torch.long)
                for name, count in zip(self.geometry.link_names, self.geometry.point_counts)])
            self.register_buffer('body_geometry_point_link', ids, persistent=False)
            self.body_geometry_encoder = nn.Sequential(nn.Linear(13, width), nn.GELU(), nn.Linear(width, width))
            self.body_geometry_identity = nn.Embedding(len(names), width)
            self.body_geometry_norm = nn.LayerNorm(width)
            self.body_geometry_attention = nn.MultiheadAttention(width, 6, batch_first=True)
            self.body_geometry_output = nn.Linear(width, width)
            nn.init.zeros_(self.body_geometry_output.weight)
            nn.init.zeros_(self.body_geometry_output.bias)

    def geometry_features(self, current_q, heightmap, basis):
        """Per-link collision extent and observed terrain clearance features.

        All points come from the canonical collision asset. Height differences
        are observation features only, never a contact predicate. Out-of-view
        points are explicitly masked rather than assigned a border height.
        """
        points, _ = self.geometry(self.fk, current_q)
        local = torch.einsum('bij,bpj->bpi', basis.transpose(1, 2), points-current_q[:, None, :3])
        b, _, _ = local.shape
        n = len(self.body_geometry_names)
        idx = self.body_geometry_point_link[None, :, None].expand(b, -1, 3)
        low = local.new_full((b, n, 3), torch.inf).scatter_reduce(1, idx, local, reduce='amin', include_self=True)
        high = local.new_full((b, n, 3), -torch.inf).scatter_reduce(1, idx, local, reduce='amax', include_self=True)
        total = local.new_zeros(b, n, 3).scatter_add(1, idx, local)
        ids = self.body_geometry_point_link[None].expand(b, -1)
        count = local.new_zeros(b, n).scatter_add(1, ids, torch.ones_like(local[..., 0]))
        mean = total/count[..., None]
        x = (local[..., 0]-HEIGHTMAP_FORWARD_MIN_M)/HEIGHTMAP_RESOLUTION_M
        y = (local[..., 1]-HEIGHTMAP_LATERAL_MIN_M)/HEIGHTMAP_RESOLUTION_M
        visible = (x >= 0) & (x <= HEIGHTMAP_ROWS-1) & (y >= 0) & (y <= HEIGHTMAP_COLS-1)
        cell = x.round().long().clamp(0, HEIGHTMAP_ROWS-1)*HEIGHTMAP_COLS+y.round().long().clamp(0, HEIGHTMAP_COLS-1)
        gap = local[..., 2]-heightmap.flatten(1).gather(1, cell)
        observed = local.new_zeros(b, n).scatter_add(1, ids, visible.to(local))
        gap_mean = local.new_zeros(b, n).scatter_add(1, ids, torch.where(visible, gap, 0))/observed.clamp_min(1)
        gap_min = local.new_full((b, n), torch.inf).scatter_reduce(1, ids,
            torch.where(visible, gap, torch.inf), reduce='amin', include_self=True)
        gap_max = local.new_full((b, n), -torch.inf).scatter_reduce(1, ids,
            torch.where(visible, gap, -torch.inf), reduce='amax', include_self=True)
        gap_min = torch.where(observed > 0, gap_min, 0)
        gap_max = torch.where(observed > 0, gap_max, 0)
        return torch.cat((mean, low, high, gap_mean[..., None], gap_min[..., None],
                          gap_max[..., None], (observed/count)[..., None]), -1)

    def load_stage_a(self, state):
        kept = {name: value for name, value in state.items()
                if not name.startswith(('surface_embedding.', 'plan_surface_embedding.'))}
        incompatible = self.load_state_dict(kept, strict=False)
        expected = sorted(name for name in self.state_dict()
                          if name.startswith(self.NEW_PREFIXES) or name.startswith(('body_geometry_', 'part_geometry_', 'region_')))
        if incompatible.unexpected_keys or sorted(incompatible.missing_keys) != expected:
            raise ValueError('incompatible full1000 Stage-A backbone')
        return sorted(kept), expected

    def _encode_points(self, current_q, current_contact, current_anchor, heightmap):
        terrain = self.height(heightmap)
        basis, yaw = _root_yaw_basis(current_q)
        positions, rotations6d = self.fk(current_q[:, None])
        positions = positions[:, 0, 1:7]
        rotations = _matrix_from_rotation6d(rotations6d[:, 0, 1:7])
        local_position = torch.einsum('bij,bpj->bpi', basis.transpose(1, 2), positions - current_q[:, None, :3])
        local_rotation = basis[:, None].transpose(-1, -2) @ rotations
        local_anchor = torch.einsum('bij,bpj->bpi', basis.transpose(1, 2), current_anchor - current_q[:, None, :3])
        part = self.part_encoder(torch.cat((local_position, _rotation6d(local_rotation),
            local_anchor * current_contact[..., None], current_contact[..., None].float()), -1))
        part = part + self.part_identity.weight[None]
        if self.part_geometry:
            features = self.part_geometry_observation(local_position, local_rotation, heightmap)
            part = part+self.part_geometry_encoder(features)
        if self.region_plan:
            features = self.region_geometry(local_position, local_rotation, heightmap)
            part = part+self.region_geometry_encoder(features)
        state = self.global_encoder(self._local_state(current_q, basis))[:, None]
        queries = torch.cat((state, part), 1)
        if self.body_geometry:
            features = self.geometry_features(current_q, heightmap, basis)
            memory = self.body_geometry_norm(self.body_geometry_encoder(features)
                                             + self.body_geometry_identity.weight[None])
            extra = self.body_geometry_attention(self.body_geometry_norm(queries), memory, memory,
                                                need_weights=False)[0]
            queries = queries+self.body_geometry_output(extra)
        for block in self.terrain_reasoning:
            queries = block(queries, terrain)
        encoded = self.shared(queries)
        return terrain, basis, yaw, self.norm(encoded[:, :1]), self.norm(encoded[:, 1:])

    def forward(self, current_q, current_contact, current_anchor, heightmap, *,
                teacher_contact=None, teacher_cell=None, teacher_mask=None):
        terrain, basis, yaw, body, part = self._encode_points(current_q, current_contact, current_anchor, heightmap)
        grid = torch.as_tensor(heightmap_grid(), device=heightmap.device, dtype=heightmap.dtype).reshape(-1, 2)
        geometry = torch.cat((grid[None].expand(len(current_q), -1, -1), heightmap.flatten(1)[..., None]), -1)
        # The emitted plan remains discrete. Decoder conditioning can use a
        # straight-through derivative without moving the selected grid point.
        role = self.role_head(part)
        keys = self.location_key(geometry)
        logits = torch.einsum('bpd,bnd->bpn', self.location_query(part), keys) / keys.shape[-1] ** .5
        contact, cell = role.argmax(-1) != 0, logits.argmax(-1)
        predicted_points = geometry.gather(1, cell[..., None].expand(-1, -1, 3))
        if teacher_mask is None:
            teacher_mask = torch.zeros(len(current_q), dtype=torch.bool, device=current_q.device)
        if teacher_mask.shape != (len(current_q),) or teacher_mask.dtype != torch.bool:
            raise ValueError('teacher mask must be boolean [B]')
        if bool(teacher_mask.any()):
            if teacher_contact is None or teacher_cell is None:
                raise ValueError('teacher samples require observed contact and cell labels')
            if teacher_contact.dtype != torch.bool or teacher_contact.shape != contact.shape or teacher_cell.shape != cell.shape:
                raise ValueError('teacher contact/cell shape mismatch')
            contact = torch.where(teacher_mask[:, None], teacher_contact, contact)
            cell = torch.where(teacher_mask[:, None], teacher_cell, cell)
        points = geometry.gather(1, cell[..., None].expand(-1, -1, 3))
        contact_choice = contact.to(part)
        point_choice = points.detach()
        if self.execution_plan_gradients and torch.is_grad_enabled():
            soft_contact = 1-role.softmax(-1)[..., 0]
            soft_points = logits.softmax(-1) @ geometry
            # Parentheses preserve the hard forward value exactly. Teacher
            # choices carry no execution derivative into autonomous heads.
            contact_choice = contact_choice+torch.where(teacher_mask[:, None],
                torch.zeros_like(soft_contact), soft_contact-soft_contact.detach())
            point_choice = point_choice+torch.where(teacher_mask[:, None, None],
                torch.zeros_like(soft_points), soft_points-soft_points.detach())
        plan = torch.cat((contact_choice[..., None], point_choice*contact_choice[..., None]), -1)
        planned_part = part + self.plan_position_encoder(plan)
        region_logits, planned_regions = None, None
        if self.region_plan:
            region_logits = (self.region_head(part)+self.region_prior).masked_fill(~self.region_geometry.valid_subsets, -1e4)
            subsets = self.region_geometry.subsets.to(part)
            hard = subsets[region_logits.argmax(-1)]
            planned_regions = hard.bool() & contact[..., None]
            soft = region_logits.softmax(-1) @ subsets
            # Hard plan on the forward pass; execution gradients also train
            # this new region head through its soft categorical surrogate.
            choice = (hard+(soft-soft.detach()))*contact_choice[..., None]
            planned_part = planned_part+self.region_plan_encoder(choice)
        planned_part = planned_part + self.plan_fusion(planned_part)
        interaction = self.pose_terrain(torch.cat((body, planned_part), 1), terrain)
        interaction = self.interaction_decoder(interaction)
        pooled = self.norm(interaction[:, 0] + interaction[:, 1:].mean(1))
        qpos = self._decode_pose(self.pose_head(pooled), current_q, basis, yaw)
        return Full1000PositionPrediction(qpos, role, logits, predicted_points,
                                         contact, cell, points, teacher_mask, region_logits, planned_regions)
