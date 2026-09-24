#!/usr/bin/env python3
"""Train a sparse-body infiller conditioned on a future contact event.

Unlike the historical infiller, this model never receives the future full-body
keyframe.  Its command is the next contact topology and the exact contact point
on a terrain surface.  The active contact body's endpoint is hard-constructed
from that contact point plus a learned dataset-level link/contact offset.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from build_g1_complete_limb_actions import debounce_binary_states
from climb00_pipeline.fullbody_dataset import inherit_active_contact_descriptors
from eval_next_keyframe_with_infiller import collapse_contact
from train_climb00_contact_event_predictor import (
    DEFAULT_MANIFEST,
    PARTS,
    SURFACES,
    ContactEventSample,
    build_samples,
    split_name,
    surface_catalog,
)
from train_g1_touchdown_keyframe_infiller import quat_matrix_wxyz, rotation_6d, rotation_matrix_6d, yaw_matrix
from train_next_contact_keyframe_predictor import source_contact_schedule, task_condition


ROOT = Path.cwd().resolve()
DEFAULT_OUTPUT = ROOT / "tmp/climb00_contact_conditioned_infiller_v1"
BODY_NAMES = (
    "torso_link",
    "left_ankle_roll_link", "right_ankle_roll_link",
    "left_wrist_yaw_link", "right_wrist_yaw_link",
    "left_knee_link", "right_knee_link",
)
PART_BODY_INDEX = np.asarray((1, 2, 3, 4, 5, 6), dtype=np.int64)
# Conservative sphere clearances around the seven sparse link origins.  These
# are not a replacement for full-link collision geometry, but make the sparse
# command itself strictly non-penetrating with a safety margin.
BODY_CLEARANCE_M = np.asarray((0.10, 0.025, 0.025, 0.025, 0.025, 0.04, 0.04), dtype=np.float32)


def phase_resample(values: np.ndarray, frames: int) -> np.ndarray:
    source = np.linspace(0.0, 1.0, len(values), dtype=np.float64)
    target = np.linspace(0.0, 1.0, frames, dtype=np.float64)
    flat = values.reshape(len(values), -1)
    output = np.stack([np.interp(target, source, flat[:, index]) for index in range(flat.shape[1])], axis=-1)
    return output.reshape((frames,) + values.shape[1:]).astype(np.float32)


def contact_world(catalog: dict[int, dict], surface: np.ndarray, uv: np.ndarray) -> np.ndarray:
    output = np.zeros((len(PARTS), 3), dtype=np.float32)
    for part, class_id in enumerate(surface):
        if int(class_id) < 0:
            continue
        record = catalog[int(class_id)]
        origin = np.asarray(record["origin"], dtype=np.float32)
        tangent_u = np.asarray(record["tangent_u"], dtype=np.float32)
        tangent_v = np.asarray(record["tangent_v"], dtype=np.float32)
        output[part] = origin + uv[part, 0] * tangent_u + uv[part, 1] * tangent_v
    return output


def build_dataset(
    manifest_path: Path, phase_frames: int,
) -> tuple[dict[str, np.ndarray], list[ContactEventSample], dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prepared_motions = {}
    samples, event_summary = build_samples(manifest_path, prepared_motions=prepared_motions)
    count = len(samples)
    positions = np.zeros((count, phase_frames, len(BODY_NAMES), 3), dtype=np.float32)
    rotations = np.zeros((count, phase_frames, len(BODY_NAMES), 6), dtype=np.float32)
    contacts = np.zeros((count, phase_frames, len(PARTS)), dtype=np.float32)
    start_contacts = np.zeros((count, len(PARTS)), dtype=np.float32)
    persistent_raw = np.zeros_like(start_contacts)
    current_contacts = np.zeros((count, len(PARTS), 3), dtype=np.float32)
    current_surfaces = np.full((count, len(PARTS)), -1, dtype=np.int64)
    target_contacts = np.zeros((count, len(PARTS), 3), dtype=np.float32)
    target_surfaces = np.full((count, len(PARTS)), -1, dtype=np.int64)
    touchdown = np.zeros((count, len(PARTS)), dtype=np.float32)
    end_contact = np.zeros((count, len(PARTS)), dtype=np.float32)
    task = np.zeros((count, 6), dtype=np.float32)
    duration = np.zeros(count, dtype=np.float32)
    runtime_lengths = np.zeros(count, dtype=np.int64)
    motion_ids = np.zeros(count, dtype=np.int64)
    box_origin = np.zeros((count, 3), dtype=np.float32)
    box_basis = np.zeros((count, 3, 3), dtype=np.float32)
    box_edge_start = np.zeros((count, 4, 2), dtype=np.float32)
    box_edge_inward = np.zeros((count, 4, 2), dtype=np.float32)
    box_height = np.zeros(count, dtype=np.float32)
    box_corners_local = np.zeros((count, 4, 3), dtype=np.float32)
    ground_height_local = np.zeros(count, dtype=np.float32)
    motion_cache: dict[int, dict] = {}
    boundary_descriptor: dict[int, tuple[int, np.ndarray, np.ndarray, np.ndarray]] = {}

    for row, sample in enumerate(samples):
        motion_id = sample.motion_id
        if motion_id not in motion_cache:
            entry = manifest["motion_files"][motion_id]
            prepared = prepared_motions.pop(motion_id)
            if prepared['body_names'] != tuple(BODY_NAMES):
                raise ValueError('Prepared body order differs from dataset body order')
            position_w = np.asarray(prepared['position'], dtype=np.float32)
            rotation_w = quat_matrix_wxyz(np.asarray(prepared['quaternion'], dtype=np.float32))
            verified = prepared['newton']
            raw_contact = verified['contact_part_mask']
            robust_contact = collapse_contact(raw_contact).astype(bool)
            plan = json.loads(Path(entry["edit_plan_file"]).read_text(encoding="utf-8"))
            catalog = surface_catalog(Path(plan["metadata"]["target_surface_catalog"]))
            motion_cache[motion_id] = {
                "position": position_w,
                "rotation": rotation_w,
                "contact": robust_contact,
                "newton": verified,
                "catalog": catalog,
                "task": task_condition(entry),
            }
        cached = motion_cache[motion_id]
        start, end = sample.current_frame, sample.target_frame
        position_w = cached["position"][start : end + 1]
        rotation_w = cached["rotation"][start : end + 1]
        origin = position_w[0, 0]
        torso = rotation_w[0, 0]
        heading = math.atan2(float(torso[1, 0]), float(torso[0, 0]))
        world_to_local = yaw_matrix(-heading)
        local_position = np.einsum("ij,tbj->tbi", world_to_local, position_w - origin)
        local_rotation = np.einsum("ij,tbjk->tbik", world_to_local, rotation_w)
        positions[row] = phase_resample(local_position, phase_frames)
        rotations[row] = phase_resample(rotation_6d(local_rotation), phase_frames)
        label_frames = np.rint(np.linspace(start, end, phase_frames)).astype(int)
        contacts[row] = cached['contact'][label_frames]
        persistent_raw[row] = cached['contact'][start:end+1].all(axis=0)
        persistent_raw[row] *= (cached['newton']['contact_surface'][start:end+1] == cached['newton']['contact_surface'][start]).all(axis=0)
        persistent_raw[row] *= ~sample.touchdown.astype(bool)
        start_contacts[row] = contacts[row, 0]
        # The command describes every contact that must remain active at the
        # boundary, not only newly created touchdowns.  Persistent support
        # inherits its exact surface anchor from the current boundary.
        command_surface = sample.surface_class.copy()
        command_uv = sample.surface_uv.copy()
        current_surface_one_hot = sample.x[len(PARTS) : len(PARTS) + len(PARTS) * len(SURFACES)].reshape(
            len(PARTS), len(SURFACES)
        )
        current_uv = sample.x[
            len(PARTS) + len(PARTS) * len(SURFACES) :
            len(PARTS) + len(PARTS) * len(SURFACES) + len(PARTS) * 2
        ].reshape(len(PARTS), 2).copy()
        current_valid = current_surface_one_hot.max(axis=-1) > 0.5
        current_surfaces[row, current_valid] = current_surface_one_hot[current_valid].argmax(axis=-1)
        previous = boundary_descriptor.get(motion_id)
        if previous is not None and previous[0] == start:
            current_surfaces[row], current_uv, unresolved = inherit_active_contact_descriptors(
                start_contacts[row], current_surfaces[row], current_uv,
                previous[1], previous[2], previous[3],
            )
            if bool(unresolved.any()):
                raise ValueError(
                    f"active contacts lack boundary descriptors at motion {motion_id}, frame {start}: "
                    f"{np.flatnonzero(unresolved).tolist()}"
                )
        current_valid = current_surfaces[row] >= 0
        current_world = contact_world(cached["catalog"], current_surfaces[row], current_uv)
        current_local = np.einsum("ij,bj->bi", world_to_local, current_world - origin)
        current_contacts[row, current_valid] = current_local[current_valid]
        persistent = (sample.end_contact > 0.5) & (sample.touchdown < 0.5)
        for part in np.flatnonzero(persistent):
            if current_valid[part]:
                command_surface[part] = int(current_surfaces[row, part])
                command_uv[part] = current_uv[part]
        unresolved_target = (sample.end_contact > 0.5) & (command_surface < 0)
        if bool(unresolved_target.any()):
            raise ValueError(
                f"active target contacts lack descriptors at motion {motion_id}, frame {end}: "
                f"{np.flatnonzero(unresolved_target).tolist()}"
            )
        target_world = contact_world(cached["catalog"], command_surface, command_uv)
        target_contacts[row] = np.einsum("ij,bj->bi", world_to_local, target_world - origin)
        # Use actual solver positions including their normal coordinate, not
        # the old surface-projected UV reconstruction or inherited descriptors.
        for frame, positions_out, surfaces_out, mask in (
                (start, current_contacts, current_surfaces, cached['contact'][start]),
                (end, target_contacts, target_surfaces, cached['contact'][end])):
            positions_out[row] = np.einsum('ij,pj->pi', world_to_local,
                cached['newton']['contact_position_w'][frame]-origin)
            positions_out[row, ~mask] = 0
            surfaces_out[row] = cached['newton']['contact_surface'][frame]
        top = cached["catalog"][1]
        top_origin_world = np.asarray(top["origin"], dtype=np.float32)
        tangent_u_world = np.asarray(top["tangent_u"], dtype=np.float32)
        tangent_v_world = np.asarray(top["tangent_v"], dtype=np.float32)
        normal_world = np.asarray(top["normal"], dtype=np.float32)
        box_origin[row] = world_to_local @ (top_origin_world - origin)
        box_basis[row] = np.stack(
            (world_to_local @ tangent_u_world, world_to_local @ tangent_v_world, world_to_local @ normal_world),
            axis=-1,
        )
        polygon = np.asarray(
            [[float(value["u"]), float(value["v"])] for value in top["metadata"]["polygon_surface_coordinates"]],
            dtype=np.float32,
        )
        if len(polygon) != 4:
            raise ValueError(f"expected four-sided climb box top, got {len(polygon)}")
        signed_area = 0.5 * np.sum(
            polygon[:, 0] * np.roll(polygon[:, 1], -1) - np.roll(polygon[:, 0], -1) * polygon[:, 1]
        )
        orientation = 1.0 if signed_area >= 0.0 else -1.0
        edge = np.roll(polygon, -1, axis=0) - polygon
        inward = orientation * np.stack((-edge[:, 1], edge[:, 0]), axis=-1)
        inward /= np.maximum(np.linalg.norm(inward, axis=-1, keepdims=True), 1.0e-8)
        box_edge_start[row] = polygon
        box_edge_inward[row] = inward
        box_height[row] = float(top_origin_world[2])
        corner_world = (
            top_origin_world[None]
            + polygon[:, :1] * tangent_u_world[None]
            + polygon[:, 1:] * tangent_v_world[None]
        )
        box_corners_local[row] = np.einsum("ij,bj->bi", world_to_local, corner_world - origin)
        ground_height_local[row] = -float(origin[2])
        target_surfaces[row] = cached['newton']['contact_surface'][end]
        touchdown[row] = sample.touchdown
        end_contact[row] = sample.end_contact
        task[row] = cached["task"]
        duration[row] = sample.duration_s
        runtime_lengths[row] = max(int(round(sample.duration_s * 50.0)) + 1, 6)
        motion_ids[row] = motion_id
        boundary_descriptor[motion_id] = (
            end,
            sample.end_contact.astype(bool).copy(),
            command_surface.copy(),
            command_uv.copy(),
        )
    return {
        "positions": positions,
        "rotations": rotations,
        "contacts": contacts,
        "start_contacts": start_contacts,
        "current_contacts": current_contacts,
        "current_surfaces": current_surfaces,
        "target_contacts": target_contacts,
        "target_surfaces": target_surfaces,
        "touchdown": touchdown,
        "end_contact": end_contact,
        "persistent_contact": persistent_raw,
        "interaction_touchdown": touchdown if manifest.get('event_contract') else (
            end_contact.astype(bool) & ~persistent_raw.astype(bool)
        ).astype(np.float32),
        "interaction_liftoff": (
            start_contacts.astype(bool) & ~persistent_raw.astype(bool)
        ).astype(np.float32),
        "task": task,
        "duration": duration,
        "runtime_lengths": runtime_lengths,
        "motion_ids": motion_ids,
        "box_origin": box_origin,
        "box_basis": box_basis,
        "box_edge_start": box_edge_start,
        "box_edge_inward": box_edge_inward,
        "box_height": box_height,
        "box_corners_local": box_corners_local,
        "ground_height_local": ground_height_local,
    }, samples, event_summary


def sparse_box_clearance(
    position: torch.Tensor,
    box_origin: torch.Tensor,
    box_basis: torch.Tensor,
    edge_start: torch.Tensor,
    edge_inward: torch.Tensor,
    box_height: torch.Tensor,
) -> torch.Tensor:
    """Signed clearance from an expanded convex box; negative means safe.

    The returned value is positive only when a sparse body sphere intersects
    the solid box.  The top polygon is treated as a convex prism down to the
    ground plane.
    """
    relative = position - box_origin[:, None, None]
    surface_coordinates = torch.einsum("btpj,bjk->btpk", relative, box_basis)
    planar = surface_coordinates[..., :2]
    edge_depth = torch.einsum(
        "btpvi,bvi->btpv", planar[..., None, :] - edge_start[:, None, None], edge_inward
    ).amin(dim=-1)
    normal = surface_coordinates[..., 2]
    top_depth = -normal
    bottom_depth = normal + box_height[:, None, None]
    inside_depth = torch.minimum(torch.minimum(edge_depth, top_depth), bottom_depth)
    margin = torch.as_tensor(BODY_CLEARANCE_M, dtype=position.dtype, device=position.device)
    box_violation = inside_depth + margin[None, None]
    ground_height = box_origin[:, 2] - box_height
    ground_violation = ground_height[:, None, None] + margin[None, None] - position[..., 2]
    return torch.maximum(box_violation, ground_violation)


def contact_aware_sparse_clearance(
    position: torch.Tensor,
    dense_contact: torch.Tensor,
    target_surface: torch.Tensor,
    box_origin: torch.Tensor,
    box_basis: torch.Tensor,
    edge_start: torch.Tensor,
    edge_inward: torch.Tensor,
    box_height: torch.Tensor,
) -> torch.Tensor:
    """Obstacle clearance matching the final strict swept checker."""
    relative = position - box_origin[:, None, None]
    surface_coordinates = torch.einsum("btpj,bjk->btpk", relative, box_basis)
    planar = surface_coordinates[..., :2]
    edge_depth = torch.einsum(
        "btpvi,bvi->btpv", planar[..., None, :] - edge_start[:, None, None], edge_inward
    ).amin(dim=-1)
    normal = surface_coordinates[..., 2]
    inside_depth = torch.minimum(
        torch.minimum(edge_depth, -normal), normal + box_height[:, None, None]
    )
    base_margin = torch.as_tensor(BODY_CLEARANCE_M, dtype=position.dtype, device=position.device)
    margin = base_margin[None, None].expand_as(inside_depth).clone()
    for part, body in enumerate(PART_BODY_INDEX):
        margin[:, :, body] = torch.where(
            dense_contact[:, :, part] > 0.999,
            torch.zeros_like(margin[:, :, body]),
            margin[:, :, body],
        )
    box_violation = inside_depth + margin
    ground_height = box_origin[:, 2] - box_height
    ground_violation = ground_height[:, None, None] + margin - position[..., 2]
    return torch.maximum(box_violation, ground_violation)


def dense_swept_samples(values: torch.Tensor, subdivisions: int = 4) -> torch.Tensor:
    """Sample every frame interval, including its swept interior."""
    if subdivisions < 1:
        raise ValueError(f"subdivisions must be positive, got {subdivisions}")
    alpha = torch.arange(
        1, subdivisions + 1, dtype=values.dtype, device=values.device
    ) / float(subdivisions)
    alpha_shape = (1, 1, subdivisions) + (1,) * (values.ndim - 2)
    interior = values[:, :-1, None] + alpha.reshape(alpha_shape) * (
        values[:, 1:, None] - values[:, :-1, None]
    )
    return torch.cat((values[:, :1], interior.flatten(1, 2)), dim=1)


def runtime_resample_batch(values: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
    """Differentiably match deployment's linear phase resampling."""
    lengths = lengths.long().clamp_min(2)
    maximum = int(lengths.max().item())
    target = torch.arange(maximum, dtype=values.dtype, device=values.device)[None]
    source_index = target / (lengths[:, None] - 1).to(values.dtype) * float(values.shape[1] - 1)
    source_index = torch.minimum(source_index, torch.full_like(source_index, float(values.shape[1] - 1)))
    left = source_index.floor().long()
    right = (left + 1).clamp_max(values.shape[1] - 1)
    weight = source_index - left.to(values.dtype)
    batch = torch.arange(len(values), device=values.device)[:, None]
    left_value = values[batch, left]
    right_value = values[batch, right]
    extra = (None,) * (values.ndim - 2)
    return left_value + weight[(...,) + extra] * (right_value - left_value)


def endpoint_offsets(data: dict[str, np.ndarray], indices: np.ndarray) -> np.ndarray:
    """Median contact-to-link offset expressed in the contacted link frame."""
    offsets = np.zeros((len(PARTS), len(SURFACES), 3), dtype=np.float32)
    for part, body in enumerate(PART_BODY_INDEX):
        for surface in range(len(SURFACES)):
            selected = indices[
                (data["touchdown"][indices, part] > 0.5)
                & (data["target_surfaces"][indices, part] == surface)
            ]
            if len(selected):
                link_rotation = rotation_matrix_6d(
                    torch.from_numpy(data["rotations"][selected, -1, body])
                ).numpy()
                local_offset = data["positions"][selected, -1, body] - data["target_contacts"][selected, part]
                body_offset = np.einsum("bij,bj->bi", link_rotation.transpose(0, 2, 1), local_offset)
                offsets[part, surface] = np.median(
                    body_offset, axis=0
                )
    return offsets


class AdaLNBlock(nn.Module):
    def __init__(self, width: int, heads: int, ffn_width: int):
        super().__init__()
        self.norm1 = nn.LayerNorm(width, elementwise_affine=False)
        self.norm2 = nn.LayerNorm(width, elementwise_affine=False)
        self.modulation = nn.Sequential(nn.SiLU(), nn.Linear(width, 4 * width))
        nn.init.zeros_(self.modulation[-1].weight)
        nn.init.zeros_(self.modulation[-1].bias)
        self.attention = nn.MultiheadAttention(width, heads, batch_first=True)
        self.ffn = nn.Sequential(nn.Linear(width, ffn_width), nn.GELU(), nn.Linear(ffn_width, width))

    def forward(self, value: torch.Tensor, condition: torch.Tensor) -> torch.Tensor:
        ga, ba, gf, bf = self.modulation(condition).chunk(4, dim=-1)
        normalized = (1.0 + ga[:, None]) * self.norm1(value) + ba[:, None]
        value = value + self.attention(normalized, normalized, normalized, need_weights=False)[0]
        normalized = (1.0 + gf[:, None]) * self.norm2(value) + bf[:, None]
        return value + self.ffn(normalized)


class ContactConditionedInfiller(nn.Module):
    def __init__(
        self, condition_dim: int, offsets: torch.Tensor,
        width: int = 192, layers: int = 4, heads: int = 6, ffn_width: int = 768,
    ):
        super().__init__()
        self.register_buffer("endpoint_offsets", offsets.clone())
        self.condition = nn.Sequential(nn.Linear(condition_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.phase = nn.Sequential(nn.Linear(9, width), nn.SiLU(), nn.Linear(width, width))
        self.blocks = nn.ModuleList([AdaLNBlock(width, heads, ffn_width) for _ in range(layers)])
        self.norm = nn.LayerNorm(width)
        self.state = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 63))
        self.endpoint = nn.Sequential(nn.Linear(width, width), nn.GELU(), nn.Linear(width, 21))
        self.contact = nn.Linear(width, len(PARTS))

    @staticmethod
    def phase_features(phase: torch.Tensor) -> torch.Tensor:
        values = [phase]
        for frequency in (1.0, 2.0, 4.0, 8.0):
            values.extend((torch.sin(math.pi * frequency * phase), torch.cos(math.pi * frequency * phase)))
        return torch.stack(values, dim=-1)

    def forward(
        self,
        condition_input: torch.Tensor,
        phase: torch.Tensor,
        start_position: torch.Tensor,
        start_rotation: torch.Tensor,
        start_contact: torch.Tensor,
        target_contact: torch.Tensor,
        target_surface: torch.Tensor,
        touchdown: torch.Tensor,
        end_contact: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        condition = self.condition(condition_input)
        hidden = self.phase(self.phase_features(phase)) + condition[:, None]
        for block in self.blocks:
            hidden = block(hidden, condition)
        hidden = self.norm(hidden)
        raw = self.state(hidden)
        raw_rotation = raw[..., 21:].reshape(-1, phase.shape[1], len(BODY_NAMES), 6)
        endpoint_rotation = rotation_matrix_6d(raw_rotation[:, -1])
        endpoint = self.endpoint(condition).reshape(-1, len(BODY_NAMES), 3)
        for part, body in enumerate(PART_BODY_INDEX):
            active = touchdown[:, part] > 0.5
            if active.any():
                rows = torch.arange(len(active), device=active.device)[active]
                surface = target_surface[active, part].clamp_min(0)
                rotated_offset = torch.einsum(
                    "bij,bj->bi", endpoint_rotation[active, body], self.endpoint_offsets[part, surface]
                )
                endpoint[rows, body] = target_contact[active, part] + rotated_offset
        u = phase[..., None, None]
        envelope = 4.0 * u * (1.0 - u)
        base = (1.0 - u) * start_position[:, None] + u * endpoint[:, None]
        position = base + envelope * raw[..., :21].reshape(-1, phase.shape[1], len(BODY_NAMES), 3)
        rotation = (1.0 - u) * start_rotation[:, None] + u * raw_rotation

        # Parameterize persistent supports by a fixed world/local contact
        # anchor inside the decoder itself.  This is not a post-generation
        # correction: every generated frame for a persistent support is
        # produced on the contact manifold.  Deriving the anchor from the
        # exact input boundary also preserves the segment seam exactly.
        start_rotation_matrix = rotation_matrix_6d(start_rotation)
        rotation_matrix = rotation_matrix_6d(rotation)
        persistent = (start_contact > 0.5) & (end_contact > 0.5) & (touchdown < 0.5)
        for part, body in enumerate(PART_BODY_INDEX):
            valid = persistent[:, part] & (target_surface[:, part] >= 0)
            if valid.any():
                surface = target_surface[:, part].clamp_min(0)
                offset = self.endpoint_offsets[part, surface]
                start_rotated_offset = torch.einsum(
                    "bij,bj->bi", start_rotation_matrix[:, body], offset
                )
                anchor = start_position[:, body] - start_rotated_offset
                rotated_offset = torch.einsum(
                    "btij,bj->bti", rotation_matrix[:, :, body], offset
                )
                supported_position = anchor[:, None] + rotated_offset
                position[:, :, body] = torch.where(
                    valid[:, None, None], supported_position, position[:, :, body]
                )
        logits = self.contact(hidden)
        start_logits = 12.0 * (2.0 * start_contact - 1.0)
        end_logits = 12.0 * (2.0 * end_contact - 1.0)
        logits = torch.where((phase <= 0.0)[..., None], start_logits[:, None], logits)
        logits = torch.where((phase >= 1.0)[..., None], end_logits[:, None], logits)
        return position, rotation, logits


def condition_arrays(
    data: dict[str, np.ndarray], indices: np.ndarray, duration_mean: float, duration_std: float,
) -> np.ndarray:
    surface_one_hot = np.zeros((len(indices), len(PARTS), len(SURFACES)), dtype=np.float32)
    for row in range(len(indices)):
        for part, surface in enumerate(data["target_surfaces"][indices[row]]):
            if surface >= 0:
                surface_one_hot[row, part, surface] = 1.0
    start_state = np.concatenate(
        (data["positions"][indices, 0].reshape(len(indices), -1), data["rotations"][indices, 0].reshape(len(indices), -1)),
        axis=-1,
    )
    return np.concatenate(
        (
            start_state,
            data["start_contacts"][indices],
            data["touchdown"][indices],
            data["end_contact"][indices],
            surface_one_hot.reshape(len(indices), -1),
            data["target_contacts"][indices].reshape(len(indices), -1),
            data["box_corners_local"][indices].reshape(len(indices), -1),
            data["ground_height_local"][indices, None],
            data["task"][indices],
            ((data["duration"][indices] - duration_mean) / duration_std)[:, None],
        ),
        axis=-1,
    ).astype(np.float32)


@torch.no_grad()
def evaluate(
    model: ContactConditionedInfiller, data: dict[str, np.ndarray], indices: np.ndarray,
    condition_mean: np.ndarray, condition_std: np.ndarray,
    duration_mean: float, duration_std: float, device: torch.device,
) -> dict:
    condition = torch.from_numpy(
        (condition_arrays(data, indices, duration_mean, duration_std) - condition_mean) / condition_std
    ).float().to(device)
    phase = torch.linspace(0.0, 1.0, data["positions"].shape[1], device=device)[None].expand(len(indices), -1)
    position, rotation, logits = model(
        condition, phase,
        torch.from_numpy(data["positions"][indices, 0]).to(device),
        torch.from_numpy(data["rotations"][indices, 0]).to(device),
        torch.from_numpy(data["start_contacts"][indices]).to(device),
        torch.from_numpy(data["target_contacts"][indices]).to(device),
        torch.from_numpy(data["target_surfaces"][indices]).to(device),
        torch.from_numpy(data["touchdown"][indices]).to(device),
        torch.from_numpy(data["end_contact"][indices]).to(device),
    )
    target_position = torch.from_numpy(data["positions"][indices]).to(device)
    target_rotation = torch.from_numpy(data["rotations"][indices]).to(device)
    position_error = torch.linalg.vector_norm(position - target_position, dim=-1).cpu().numpy() * 100.0
    endpoint_active = []
    for row in range(len(indices)):
        for part in np.flatnonzero(data["touchdown"][indices[row]] > 0.5):
            endpoint_active.append(position_error[row, -1, PART_BODY_INDEX[part]])
    predicted_contact = logits.sigmoid() >= 0.5
    contact_target = torch.from_numpy(data["contacts"][indices]).bool().to(device)
    rotation_matrix = rotation_matrix_6d(rotation)
    target_matrix = rotation_matrix_6d(target_rotation)
    relative = rotation_matrix.transpose(-1, -2) @ target_matrix
    cosine = ((relative.diagonal(dim1=-2, dim2=-1).sum(-1) - 1.0) * 0.5).clamp(-1.0, 1.0)
    angle = torch.rad2deg(torch.acos(cosine)).cpu().numpy()
    runtime_lengths = torch.from_numpy(data["runtime_lengths"][indices]).to(device)
    runtime_position = runtime_resample_batch(position, runtime_lengths)
    runtime_contact = runtime_resample_batch(contact_target.float(), runtime_lengths)
    dense_position = dense_swept_samples(runtime_position)
    dense_contact = dense_swept_samples(runtime_contact)
    collision_clearance = contact_aware_sparse_clearance(
        dense_position, dense_contact,
        torch.from_numpy(data["target_surfaces"][indices]).to(device),
        torch.from_numpy(data["box_origin"][indices]).to(device),
        torch.from_numpy(data["box_basis"][indices]).to(device),
        torch.from_numpy(data["box_edge_start"][indices]).to(device),
        torch.from_numpy(data["box_edge_inward"][indices]).to(device),
        torch.from_numpy(data["box_height"][indices]).to(device),
    ).cpu().numpy()

    def summary(values: np.ndarray) -> dict[str, float]:
        values = np.asarray(values, dtype=np.float64)
        return {"mean": float(values.mean()), "p95": float(np.quantile(values, 0.95)), "max": float(values.max())}

    return {
        "all_keypoint_position_error_cm": summary(position_error),
        "endpoint_active_link_error_cm": summary(np.asarray(endpoint_active)),
        "all_keypoint_rotation_error_deg": summary(angle),
        "contact_bit_accuracy": float((predicted_contact == contact_target).float().mean()),
        "first_frame_position_error_cm": summary(position_error[:, 0]),
        "strict_sparse_collision_free_fraction": float((collision_clearance <= 0.0).all(axis=(1, 2)).mean()),
        "maximum_sparse_penetration_cm": summary(np.maximum(collision_clearance, 0.0) * 100.0),
        "endpoint_contract": "active link endpoint is contact point plus fixed part/surface offset by construction",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--phase-frames", type=int, default=64)
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--width", type=int, default=192)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--heads", type=int, default=6)
    parser.add_argument("--ffn-width", type=int, default=768)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--init-checkpoint", type=Path)
    parser.add_argument("--eval-every", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260824)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device(args.device)

    data, samples, event_summary = build_dataset(args.manifest, args.phase_frames)
    splits = {
        name: np.asarray([index for index, sample in enumerate(samples) if split_name(sample.height) == name], dtype=np.int64)
        for name in ("train_height_095_100_105", "validation_height_090", "test_height_110")
    }
    train = splits["train_height_095_100_105"]
    duration_mean = float(data["duration"][train].mean())
    duration_std = float(max(data["duration"][train].std(), 1.0e-3))
    condition_train = condition_arrays(data, train, duration_mean, duration_std)
    condition_mean = condition_train.mean(axis=0).astype(np.float32)
    condition_std = np.maximum(condition_train.std(axis=0), 1.0e-5).astype(np.float32)
    offsets = endpoint_offsets(data, train)
    dataset = TensorDataset(
        torch.from_numpy((condition_train - condition_mean) / condition_std).float(),
        torch.from_numpy(data["positions"][train]).float(),
        torch.from_numpy(data["rotations"][train]).float(),
        torch.from_numpy(data["contacts"][train]).float(),
        torch.from_numpy(data["start_contacts"][train]).float(),
        torch.from_numpy(data["target_contacts"][train]).float(),
        torch.from_numpy(data["target_surfaces"][train]).long(),
        torch.from_numpy(data["touchdown"][train]).float(),
        torch.from_numpy(data["end_contact"][train]).float(),
        torch.from_numpy(data["runtime_lengths"][train]).long(),
        torch.from_numpy(data["box_origin"][train]).float(),
        torch.from_numpy(data["box_basis"][train]).float(),
        torch.from_numpy(data["box_edge_start"][train]).float(),
        torch.from_numpy(data["box_edge_inward"][train]).float(),
        torch.from_numpy(data["box_height"][train]).float(),
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=True)
    iterator = iter(loader)
    model = ContactConditionedInfiller(
        condition_train.shape[1], torch.from_numpy(offsets), args.width, args.layers, args.heads, args.ffn_width
    ).to(device)
    if args.init_checkpoint is not None:
        initial = torch.load(args.init_checkpoint, map_location="cpu", weights_only=False)
        if int(initial["condition_dim"]) != condition_train.shape[1]:
            raise ValueError(
                f"init checkpoint condition_dim={initial['condition_dim']} != {condition_train.shape[1]}"
            )
        model.load_state_dict(initial["model"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-4)
    phase = torch.linspace(0.0, 1.0, args.phase_frames, device=device)[None]
    best_state = None
    best_error = math.inf
    history = []
    for step in range(1, args.steps + 1):
        try:
            batch = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            batch = next(iterator)
        (
            condition, position_t, rotation_t, contact_t, start_contact, target_contact,
            target_surface, touchdown, end_contact, runtime_length, box_origin, box_basis,
            box_edge_start, box_edge_inward, box_height,
        ) = [
            value.to(device) for value in batch
        ]
        phase_batch = phase.expand(len(condition), -1)
        position, rotation, logits = model(
            condition, phase_batch, position_t[:, 0], rotation_t[:, 0], start_contact,
            target_contact, target_surface, touchdown, end_contact,
        )
        position_loss = ((position - position_t) / 0.1).square().mean()
        rotation_loss = (rotation - rotation_t).square().mean()
        velocity_loss = (
            ((position[:, 1:] - position[:, :-1]) - (position_t[:, 1:] - position_t[:, :-1])) / 0.05
        ).square().mean()
        endpoint_position_loss = ((position[:, -1] - position_t[:, -1]) / 0.05).square().mean()
        endpoint_rotation_loss = (rotation[:, -1] - rotation_t[:, -1]).square().mean()
        runtime_position = runtime_resample_batch(position, runtime_length)
        runtime_contact = runtime_resample_batch(contact_t, runtime_length)
        dense_position = dense_swept_samples(runtime_position)
        dense_contact = dense_swept_samples(runtime_contact)
        collision_clearance = contact_aware_sparse_clearance(
            dense_position, dense_contact, target_surface,
            box_origin, box_basis, box_edge_start, box_edge_inward, box_height
        )
        positive_collision = F.relu(collision_clearance) / 0.02
        # The dense mean shapes the whole trajectory; the per-segment maximum
        # prevents a severe local penetration from disappearing among safe
        # frames and bodies.
        collision_loss = (
            positive_collision.square().mean()
            + positive_collision.amax(dim=(1, 2)).square().mean()
        )
        contact_loss = F.binary_cross_entropy_with_logits(logits, contact_t)
        loss = (
            position_loss + rotation_loss + 0.25 * velocity_loss + 0.1 * contact_loss
            + endpoint_position_loss + 0.5 * endpoint_rotation_loss
            + 4.0 * collision_loss
        )
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        optimizer.step()
        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            model.eval()
            probe_indices = splits["validation_height_090"][:512]
            probe = evaluate(
                model, data, probe_indices, condition_mean, condition_std,
                duration_mean, duration_std, device,
            )
            history.append({"step": step, "loss": float(loss.detach()), "validation": probe})
            print(json.dumps(history[-1]))
            error = probe["all_keypoint_position_error_cm"]["mean"]
            if error < best_error:
                best_error = error
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            model.train()
    assert best_state is not None
    model.load_state_dict(best_state)
    model.eval()
    metrics = {
        name: evaluate(
            model, data, indices, condition_mean, condition_std,
            duration_mean, duration_std, device,
        )
        for name, indices in splits.items()
    }
    checkpoint = {
        "schema": "climb00_contact_conditioned_infiller_v1",
        "model": best_state,
        "body_names": BODY_NAMES,
        "parts": PARTS,
        "surfaces": SURFACES,
        "phase_frames": args.phase_frames,
        "condition_dim": condition_train.shape[1],
        "condition_mean": torch.from_numpy(condition_mean),
        "condition_std": torch.from_numpy(condition_std),
        "duration_mean": duration_mean,
        "duration_std": duration_std,
        "endpoint_offsets": torch.from_numpy(offsets),
        "config": vars(args),
    }
    torch.save(checkpoint, args.output / "model.pt")
    report = {
        "schema": "climb00_contact_conditioned_infiller_report_v1",
        "event_dataset": event_summary,
        "splits": {name: int(len(indices)) for name, indices in splits.items()},
        "metrics": metrics,
        "history": history,
        "model_contract": {
            "input": (
                "current 7-body pose + current contacts + next contact surface/point/topology + "
                "current torso-yaw-frame box corners/ground height + task + duration"
            ),
            "excluded": "future 7-body keyframe",
            "hard_constraint": (
                "active endpoint = exact surface contact point + predicted endpoint rotation * "
                "calibrated body-frame link/contact offset"
            ),
            "collision_constraint": (
                "convex box-prism signed clearance on all 64 generated phase samples; "
                "10 cm torso, 2.5 cm hand/ankle, 4 cm knee sparse-body margins"
            ),
        },
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
