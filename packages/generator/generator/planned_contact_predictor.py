"""Explicit six-part contact intentions conditioning the next endpoint pose.

Raster locations are intentions in the observed heightmap, never contact truth.
Only Newton activation/allocation after primary-face selection establishes the
contacts actually realized by qpos. No analytic scene enters this network.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn
import torch.nn.functional as F

from generator.contact_location_predictor import HeightmapContactLocationPredictor
from generator.next_interaction_heightmap_v3 import DenseHeightmapInteractionPredictor
from somaforge_core.heightmap import HEIGHTMAP_COLS, HEIGHTMAP_ROWS, HEIGHTMAP_RESOLUTION_M
from somaforge_core.heightmap import _root_yaw_basis


@dataclass(frozen=True)
class PlannedContactPrediction:
    qpos: Tensor
    role_logits: Tensor
    location_logits: Tensor
    contact_points_local: Tensor
    conditioned_contact: Tensor
    conditioned_cell: Tensor
    conditioned_points_local: Tensor

    @property
    def role(self) -> Tensor:
        return self.role_logits.argmax(-1)

    @property
    def contact(self) -> Tensor:
        return self.role != 0

    @property
    def cell(self) -> Tensor:
        return self.location_logits.argmax(-1)


class PlannedHeightmapContactPredictor(HeightmapContactLocationPredictor):
    """Choose a hard contact plan before decoding the endpoint pose."""

    PLAN_PREFIXES = ("role_head.", "location_query.", "location_relation.", "plan_fusion.")

    def __init__(self, width=192, layers=3, location_width=32, **kwargs):
        super().__init__(width, layers, location_width, **kwargs)
        self.role_head = nn.Linear(width, 4)
        self.location_query = nn.Linear(width, location_width)
        # Per-part geometry distinguishes cells with the same terrain height.
        self.location_relation = nn.Sequential(
            nn.Linear(width + 3, width), nn.GELU(), nn.Linear(width, 1)
        )
        self.plan_fusion = nn.Linear(4, width, bias=False)
        # A migrated checkpoint initially retains its exact pose function.
        nn.init.zeros_(self.plan_fusion.weight)

    def load_embodied(self, state: dict[str, Tensor]) -> tuple[list[str], list[str]]:
        own = self.state_dict()
        missing = sorted(set(own) - set(state))
        expected = sorted(k for k in own if k.startswith(self.PLAN_PREFIXES))
        if missing != expected or set(state) - set(own):
            raise ValueError("warm start must contain the complete compatible embodied model")
        self.load_state_dict(state, strict=False)
        return sorted(state), missing

    def _predict(self, current_q, current_contact, current_contact_map, heightmap,
                 planned_contact=None, planned_cell=None):
        terrain, keys, geometry, basis, yaw, body, part = self._encode_observation(
            current_q, current_contact, current_contact_map, heightmap
        )
        # Train the newly introduced decision heads without overwriting the
        # pretrained pose representation through classification gradients.
        plan_part, plan_keys = part.detach(), keys.detach()
        role_logits = self.role_head(plan_part)
        location_logits = torch.einsum(
            "bpd,bnd->bpn", self.location_query(plan_part), plan_keys
        ) / keys.shape[-1] ** 0.5
        # Chunk parts to avoid materializing [B,6,4331,width] at once.
        relation = []
        for index in range(6):
            token = plan_part[:, index:index + 1].expand(-1, geometry.shape[1], -1)
            relation.append(self.location_relation(torch.cat((token, geometry), -1)).squeeze(-1))
        location_logits = location_logits + torch.stack(relation, 1)
        predicted_cell = location_logits.argmax(-1)
        points = geometry.gather(1, predicted_cell[..., None].expand(-1, -1, 3))
        if planned_contact is None:
            contact, cell = role_logits.argmax(-1) != 0, predicted_cell
        else:
            if planned_contact.dtype != torch.bool or planned_contact.shape != role_logits.shape[:2]:
                raise ValueError("planned_contact must be bool [B,6]")
            if planned_cell is None or planned_cell.shape != planned_contact.shape:
                raise ValueError("planned_cell must be [B,6]")
            if bool(((planned_cell < 0) | (planned_cell >= geometry.shape[1])).any()):
                raise ValueError("planned_cell is outside the observation raster")
            contact, cell = planned_contact, planned_cell
        conditioned_point = geometry.gather(1, cell[..., None].expand(-1, -1, 3))
        plan = torch.cat((contact[..., None].to(part),
                          conditioned_point * contact[..., None]), -1).detach()
        pooled, basis, yaw = self._decode_interaction_state(
            current_q, current_contact, heightmap, terrain, basis, yaw,
            body, part + self.plan_fusion(plan),
        )
        raw = self.pose_head(pooled)
        qpos = DenseHeightmapInteractionPredictor._decode_pose(raw, current_q, basis, yaw)
        if self.joint_residual_output:
            qpos = torch.cat((qpos[:, :7], current_q[:, 7:] + raw[:, 7:]), -1)
        return PlannedContactPrediction(qpos, role_logits, location_logits, points, contact, cell,
                                        conditioned_point)

    def forward(self, current_q, current_contact, current_contact_map, heightmap):
        return self._predict(current_q, current_contact, current_contact_map, heightmap)

    def forward_with_plan(self, current_q, current_contact, current_contact_map, heightmap,
                          *, planned_contact, planned_cell):
        """Training/diagnostic conditioning; deployment uses forward only."""
        return self._predict(current_q, current_contact, current_contact_map, heightmap,
                             planned_contact, planned_cell)


def contact_plan_objective(prediction, target):
    role = F.cross_entropy(prediction.role_logits.transpose(1, 2), target["role"], reduction="none").mean(-1)
    valid = target["contact_cell_valid"] & (target["role"] != 0)
    cells = F.cross_entropy(prediction.location_logits.transpose(1, 2), target["contact_cell"], reduction="none")
    location = (cells * valid).sum(-1) / valid.sum(-1).clamp_min(1)
    exact_contact = (prediction.contact == (target["role"] != 0)).all(-1)
    row_error = prediction.cell // HEIGHTMAP_COLS - target["contact_cell"] // HEIGHTMAP_COLS
    col_error = prediction.cell % HEIGHTMAP_COLS - target["contact_cell"] % HEIGHTMAP_COLS
    location_error = (row_error.square() + col_error.square()).float().sqrt() * (100 * HEIGHTMAP_RESOLUTION_M)
    return role + location, {
        "plan_role_loss": role,
        "plan_location_loss": location,
        "plan_contact_exact": exact_contact.float(),
        "plan_role_exact": (prediction.role == target["role"]).all(-1).float(),
        "plan_location_error_cm": (location_error * valid).sum(-1) / valid.sum(-1).clamp_min(1),
        "plan_cell_exact": (exact_contact & ((prediction.cell == target["contact_cell"]) | ~valid).all(-1)).float(),
    }


def plan_points_in_pose_frame(current_q: Tensor, points_local: Tensor) -> Tensor:
    """Lift observation-root-yaw locations into the frame containing q."""
    basis, _ = _root_yaw_basis(current_q)
    return current_q[:, None, :3] + torch.einsum("bij,bpj->bpi", basis, points_local)


def translated_observed_plan_cells(cells, active, heightmap, row_shift, column_shift):
    """Counterfactual spatial intentions on the same observed height levels.

    This only selects training intentions. It makes no claim about realized
    contacts or feasibility; every generated pose still requires Newton.
    """
    rows = cells // HEIGHTMAP_COLS + row_shift[:, None]
    columns = cells % HEIGHTMAP_COLS + column_shift[:, None]
    inside = (rows >= 0) & (rows < HEIGHTMAP_ROWS) & (columns >= 0) & (columns < HEIGHTMAP_COLS)
    moved = rows.clamp(0, HEIGHTMAP_ROWS - 1) * HEIGHTMAP_COLS + columns.clamp(0, HEIGHTMAP_COLS - 1)
    heights = heightmap.flatten(1)
    same_height = torch.isclose(heights.gather(1, cells), heights.gather(1, moved), atol=1e-6, rtol=0)
    eligible = ((inside & same_height) | ~active).all(-1) & active.any(-1)
    eligible &= (row_shift != 0) | (column_shift != 0)
    return torch.where(eligible[:, None], moved, cells), eligible


def audit_intended_surfaces(points_world: Tensor, active: Tensor, observed: dict) -> Tensor:
    """Associate spatial intentions with upward Newton faces, outside forward.

    Nearest-plane association describes the intent only. It neither declares
    contact nor converts a side-face collision into a top-face collision.
    """
    if observed.get('schema') == 'newton_device_witness_batch_v1':
        from contact_solver.device_contact_objective import intended_surfaces
        return intended_surfaces(points_world, active, observed)
    from somaforge_core.contact_face_selection import upward_face_mask
    catalogs = observed.get("surface_catalog_by_sample")
    if catalogs is None:
        catalogs = [observed["surface_catalog"]] * len(points_world)
    if len(catalogs) != len(points_world):
        raise ValueError("Newton catalog batch mismatch")
    result = torch.full_like(active, -1, dtype=torch.long)
    for row, catalog in enumerate(catalogs):
        keep = upward_face_mask([face["normal_w"] for face in catalog])
        faces = [face for face, valid in zip(catalog, keep, strict=True) if valid]
        if not faces:
            raise ValueError("Newton catalog contains no valid horizontal primary faces")
        normal = points_world.new_tensor([face["normal_w"] for face in faces])
        offset = points_world.new_tensor([face["plane_offset"] for face in faces])
        distance = (points_world[row].detach() @ normal.T - offset).abs()
        ids = result.new_tensor([face["surface"] for face in faces])
        result[row] = torch.where(active[row], ids[distance.argmin(-1)], -1)
    return result


def relative_contact_layout_loss(model, qpos, points, active, surfaces, rows, *, regions=None):
    """Compare endpoint positions in the same observed-scene frame.

    Use fresh Newton geometric witnesses only. Missing pairs contribute no
    layout term and must be established by the separate Newton/finite-face
    approach objective; absence is never counted as successful contact.
    """
    from contact_solver.device_contact_objective import DeviceWitnessRows
    if isinstance(rows, DeviceWitnessRows):
        return rows.layout(points, active, surfaces, regions=regions)
    from contact_solver.contact_layout import nearest_spatial_pairs, endpoint_position_statistics
    active_cpu, surface_cpu = active.detach().cpu().tolist(), surfaces.detach().cpu().tolist()
    spatial_rows = [[dict(pair) for pair, _ in pairs] for pairs in rows]
    if regions is not None:
        all_pairs = [(sample, pair) for sample, pairs in enumerate(spatial_rows) for pair in pairs]
        if all_pairs:
            sample_ids = torch.tensor([s for s, _ in all_pairs], device=qpos.device)
            parts = torch.tensor([p['part'] for _, p in all_pairs], device=qpos.device)
            witnesses = qpos.new_tensor([p['position_w'] for _, p in all_pairs])
            ids = model.region_geometry.witness_regions(model.fk, qpos, sample_ids, parts, witnesses)
            for (_, pair), region in zip(all_pairs, ids.tolist(), strict=True):
                pair['contact_region'] = region
    selected = [nearest_spatial_pairs(pairs, enabled, face, points[sample].detach().cpu(),
                    regions=None if regions is None else regions[sample].detach().cpu())
                for sample, (pairs, enabled, face) in enumerate(zip(spatial_rows, active_cpu, surface_cpu, strict=True))]
    flat = [(sample, part, pair) for sample, row in enumerate(selected)
            for part, pair in enumerate(row) if pair is not None]
    moving = qpos[:, None, :3].expand(-1, 6, -1) * 0
    observed = torch.zeros_like(active)
    if flat:
        names = tuple(sorted({pair['body_name'] for _, _, pair in flat}))
        # A single batched FK instead of a full robot traversal for every limb.
        positions, rotations = model.fk.link_poses(qpos, names)
        lookup = {name: index for index, name in enumerate(names)}
        si = torch.tensor([sample for sample, _, _ in flat], device=qpos.device)
        pi = torch.tensor([part for _, part, _ in flat], device=qpos.device)
        bi = torch.tensor([lookup[pair['body_name']] for _, _, pair in flat], device=qpos.device)
        position, rotation = positions[si, bi], rotations[si, bi]
        witness = qpos.new_tensor([pair['position_w'] for _, _, pair in flat])
        material = torch.bmm(rotation.detach().transpose(1, 2), (witness - position.detach())[..., None])
        values = position + torch.bmm(rotation, material).squeeze(-1)
        moving = moving.index_put((si, pi), values)
        observed[si, pi] = True
    error, count = endpoint_position_statistics(moving, points.detach(), observed)
    return error / (2 * HEIGHTMAP_RESOLUTION_M) ** 2, {
        'relative_layout_rms_cm': torch.where(count >= 1, 100 * error.clamp_min(1e-16).sqrt(), torch.zeros_like(error)),
        'relative_layout_observed_parts': count.to(qpos),
    }


def spatial_contact_realization_loss(model, qpos, points, active, configured_margin, *, cell_basis=None):
    """Differentiate collision-shape approach to the selected observed cell.

    This is an optimization residual, never a contact classifier. The normal
    is upward under this task's horizontal-primary-face contract. No semantic
    surface IDs, analytic scene, GT material witnesses, or q projection enter
    this residual. Newton supplies the actual margin and verifies realization.
    """
    from contact_solver.contact_constrained_projector import CanonicalContactCollisionGeometry

    if points.shape != (len(qpos), 6, 3) or active.shape != (len(qpos), 6):
        raise ValueError("spatial intentions must have shapes [B,6,3] and [B,6]")
    if configured_margin.shape != (len(qpos),) or not bool((configured_margin > 0).all()):
        raise ValueError("spatial approach requires actual positive Newton margins")
    geometry = getattr(model, "_spatial_plan_geometry", None)
    if geometry is None:
        geometry = CanonicalContactCollisionGeometry().to(qpos.device)
        model._spatial_plan_geometry = geometry
    points = points.detach()
    margin = configured_margin.detach()
    normal = qpos.new_tensor((0., 0., 1.)).expand(len(qpos), -1)
    tangent_u = (qpos.new_tensor((1., 0., 0.)).expand(len(qpos), -1)
                 if cell_basis is None else cell_basis.detach()[:, :, 0])
    tangent_v = (qpos.new_tensor((0., 1., 0.)).expand(len(qpos), -1)
                 if cell_basis is None else cell_basis.detach()[:, :, 1])
    residuals = []
    for part in range(6):
        # Cell extent is a spatial optimization tolerance, not contact truth.
        region = torch.cat((points[:, part], tangent_u, tangent_v,
                            qpos.new_full((len(qpos), 2), HEIGHTMAP_RESOLUTION_M / 2)), -1)
        residual = geometry.approach_residual(
            model.fk, qpos, part, normal, points[:, part, 2] + 0.05 * margin,
            region, points[:, part], qpos.new_zeros(len(qpos)), patch=False,
        )
        residuals.append(residual.square().sum(-1))
    error_sq = torch.stack(residuals, -1)
    normalized = error_sq / margin[:, None].square() * active
    count = active.sum(-1).clamp_min(1)
    loss = normalized.sum(-1) / count + 0.25 * normalized.amax(-1)
    return loss, {
        "spatial_plan_realization_loss": loss,
        "spatial_plan_residual_cm": 100 * (error_sq.clamp_min(1e-16).sqrt() * active).sum(-1) / count,
    }
