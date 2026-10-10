"""Hard contact-plan selection shared by versioned predictor architectures.

This changes neither demonstrated Newton labels nor teacher/repair semantics.
Only discrete intent leaves this module; execution never backpropagates to plan heads.
"""
from dataclasses import dataclass
import torch
from somaforge_core.heightmap import heightmap_grid
from generator.planned_contact_predictor import PlannedContactPrediction


@dataclass(frozen=True)
class Full1000PositionPrediction(PlannedContactPrediction):
    teacher_conditioned: torch.Tensor
    region_logits: torch.Tensor | None = None
    planned_regions: torch.Tensor | None = None
    conditioned_role: torch.Tensor | None = None


@dataclass(frozen=True)
class PositionPlan:
    role_logits: torch.Tensor
    location_logits: torch.Tensor
    contact_points_local: torch.Tensor
    conditioned_contact: torch.Tensor
    conditioned_cell: torch.Tensor
    conditioned_points_local: torch.Tensor
    teacher_conditioned: torch.Tensor
    region_logits: torch.Tensor | None
    planned_regions: torch.Tensor | None
    conditioned_role: torch.Tensor

    def prediction(self, qpos):
        return Full1000PositionPrediction(qpos, self.role_logits, self.location_logits,
            self.contact_points_local, self.conditioned_contact, self.conditioned_cell,
            self.conditioned_points_local, self.teacher_conditioned, self.region_logits,
            self.planned_regions, self.conditioned_role)


def select_position_plan(model, current_q, heightmap, basis, part, *,
        teacher_contact=None, teacher_cell=None, teacher_mask=None, teacher_role=None, teacher_regions=None,
        repair_mask=None, repair_role=None, repair_points_world=None, repair_regions=None):
    grid = torch.as_tensor(heightmap_grid(), device=heightmap.device, dtype=heightmap.dtype).reshape(-1, 2)
    geometry = torch.cat((grid[None].expand(len(current_q), -1, -1), heightmap.flatten(1)[..., None]), -1)
    # Hard plan heads remain supervised only by planning losses.
    role = model.role_head(part)
    keys = model.location_key(geometry)
    logits = torch.einsum('bpd,bnd->bpn', model.location_query(part), keys) / keys.shape[-1] ** .5
    contact, cell = role.argmax(-1) != 0, logits.argmax(-1)
    conditioned_role = role.argmax(-1)
    predicted_points = geometry.gather(1, cell[..., None].expand(-1, -1, 3))
    if teacher_mask is None:
        teacher_mask = torch.zeros(len(current_q), dtype=torch.bool, device=current_q.device)
    if teacher_mask.shape != (len(current_q),) or teacher_mask.dtype != torch.bool:
        raise ValueError('teacher mask must be boolean [B]')
    if bool(teacher_mask.any()):
        if model.event_roles:
            if teacher_role is None or teacher_role.shape != contact.shape:
                raise ValueError('Event-role conditioning requires explicit teacher roles')
            if teacher_role.dtype != torch.long or bool(((teacher_role < 0) | (teacher_role > 3)).any()):
                raise ValueError('Teacher roles must be long values in [0,3]')
            if teacher_contact is None or not torch.equal((teacher_role != 0)[teacher_mask], teacher_contact[teacher_mask]):
                raise ValueError('Teacher role/contact mismatch')
            conditioned_role = torch.where(teacher_mask[:, None], teacher_role, conditioned_role)
        if teacher_contact is None or teacher_cell is None:
            raise ValueError('teacher samples require observed contact and cell labels')
        if teacher_contact.dtype != torch.bool or teacher_contact.shape != contact.shape or teacher_cell.shape != cell.shape:
            raise ValueError('teacher contact/cell shape mismatch')
        contact = torch.where(teacher_mask[:, None], teacher_contact, contact)
        cell = torch.where(teacher_mask[:, None], teacher_cell, cell)
    points = geometry.gather(1, cell[..., None].expand(-1, -1, 3))
    region_logits, planned_regions = None, None
    if model.region_plan:
        region_logits = (model.region_head(part)+model.region_prior).masked_fill(~model.region_geometry.valid_subsets, -1e4)
        subsets = model.region_geometry.subsets.to(part)
        hard = subsets[region_logits.argmax(-1)]
        planned_regions = hard.bool() & contact[..., None]
        if bool(teacher_mask.any()):
            if (teacher_regions is None or teacher_regions.dtype != torch.bool
                    or teacher_regions.shape != planned_regions.shape):
                raise ValueError('Regional teacher conditioning requires actual demonstrated regions [B,6,4]')
            selected = teacher_regions[teacher_mask]
            active = contact[teacher_mask]
            if bool((selected & ~model.region_geometry.valid[None]).any()):
                raise ValueError('Teacher regions contain an invalid anatomical region')
            if not torch.equal(selected.any(-1), active):
                raise ValueError('Teacher regions/contact mismatch or missing native regional evidence')
            planned_regions = torch.where(teacher_mask[:, None, None], teacher_regions, planned_regions)

    if repair_mask is not None:
        if not model.event_roles or repair_mask.dtype != torch.bool or repair_mask.shape != (len(current_q),):
            raise ValueError('Plan repair requires event roles and a boolean batch mask')
        if bool(repair_mask.any()):
            if repair_role is None or repair_points_world is None:
                raise ValueError('Repair requires the previously issued role and world points')
            if repair_role.shape != contact.shape or repair_role.dtype != torch.long or repair_points_world.shape != points.shape:
                raise ValueError('Invalid stored plan shapes/dtypes')
            if bool(((repair_role < 0) | (repair_role > 3)).any()) or not bool(torch.isfinite(repair_points_world).all()):
                raise ValueError('Invalid stored plan values')
            local = torch.einsum('bji,bpj->bpi', basis,
                repair_points_world.detach()-current_q[:, None, :3])
            conditioned_role = torch.where(repair_mask[:, None], repair_role, conditioned_role)
            contact = conditioned_role != 0
            points = torch.where(repair_mask[:, None, None], local, points)
            cell = torch.where(repair_mask[:, None], -1, cell)
            if model.region_plan:
                if repair_regions is None or repair_regions.shape != planned_regions.shape or repair_regions.dtype != torch.bool:
                    raise ValueError('Regional repair requires stored regional intent')
                planned_regions = torch.where(repair_mask[:, None, None], repair_regions, planned_regions)

    return PositionPlan(role, logits, predicted_points, contact, cell, points, teacher_mask,
                        region_logits, planned_regions, conditioned_role)
