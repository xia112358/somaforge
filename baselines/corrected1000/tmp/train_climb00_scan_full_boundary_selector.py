#!/usr/bin/env python3
"""Train a scan selector that owns the complete next sparse-body boundary."""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

from climb00_scan_observation import SCAN_CLIP_M, conform_contact_targets_to_scan, local_scan_grid
from climb00_privileged_geometry import (
    PRIVILEGED_GEOMETRY_DIM,
    PrivilegedGeometryEncoder,
    conform_contact_targets_to_geometry,
    privileged_geometry_array,
    privileged_geometry_torch,
)
from train_climb00_contact_conditioned_infiller import (
    BODY_NAMES, PART_BODY_INDEX, contact_aware_sparse_clearance,
)
from train_climb00_contact_event_predictor import PARTS, split_name
from train_climb00_scan_contact_selector import (
    DEFAULT_MANIFEST,
    ROOT,
    ScanContactSelector,
    arrays,
    contact_stats,
    transition_labels,
    transition_vocabulary,
)
from train_g1_touchdown_keyframe_infiller import rotation_matrix_6d


class ScanFullBoundarySelector(ScanContactSelector):
    """Select contact topology, contact point, duration, and the full end pose."""

    def __init__(self, state_dim: int, action_count: int, boundary_dim: int = 63, contact_offset_dim: int = 0, **kwargs):
        super().__init__(state_dim, action_count, **kwargs)
        width = self.duration.in_features
        self.boundary = nn.Sequential(
            nn.Linear(width, width), nn.SiLU(), nn.Linear(width, boundary_dim),
        )
        self.contact_offset = None if contact_offset_dim <= 0 else nn.Linear(width, contact_offset_dim)

    def decode_parameters(self, hidden: torch.Tensor, action_index: torch.Tensor):
        end_contact, target_contact, duration = super().decode_parameters(hidden, action_index)
        value = self.parameter_trunk(torch.cat((hidden, self.action_embedding(action_index)), dim=-1))
        output=(end_contact, target_contact, duration, self.boundary(value))
        return output if self.contact_offset is None else output+(self.contact_offset(value),)


class PrivilegedFullBoundarySelector(ScanFullBoundarySelector):
    """Offline generator selector conditioned on exact terrain geometry."""

    def __init__(self, state_dim: int, action_count: int, **kwargs):
        super().__init__(state_dim, action_count, **kwargs)
        width = self.duration.in_features
        self.scan = PrivilegedGeometryEncoder(width)


def boundary_delta(data: dict[str, np.ndarray]) -> np.ndarray:
    position = data["positions"][:, -1] - data["positions"][:, 0]
    rotation = data["rotations"][:, -1] - data["rotations"][:, 0]
    return np.concatenate((position.reshape(len(position), -1), rotation.reshape(len(rotation), -1)), -1).astype(np.float32)


BODY_STRUCTURE_PAIRS = (
    (5, 1, "left_shank"), (6, 2, "right_shank"),
    (0, 5, "torso_left_knee"), (0, 6, "torso_right_knee"),
    (0, 3, "torso_left_wrist"), (0, 4, "torso_right_wrist"),
    (0, 1, "torso_left_ankle"), (0, 2, "torso_right_ankle"),
)


def body_structure_statistics(position: np.ndarray) -> dict[str, np.ndarray]:
    """Measure fixed and bounded sparse-body spans from valid training motion."""
    flat = np.asarray(position, dtype=np.float32).reshape(-1, len(BODY_NAMES), 3)
    distance = np.stack(
        [np.linalg.norm(flat[:, first] - flat[:, second], axis=-1) for first, second, _ in BODY_STRUCTURE_PAIRS],
        axis=-1,
    )
    return {
        "target": np.median(distance, axis=0).astype(np.float32),
        "lower": np.quantile(distance, 0.001, axis=0).astype(np.float32),
        "upper": np.quantile(distance, 0.999, axis=0).astype(np.float32),
    }


def enforce_fixed_body_structure(position: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Hard-parameterize both knees at the measured shank length."""
    output = position.clone()
    for pair, knee, ankle in ((0, 5, 1), (1, 6, 2)):
        direction = output[..., knee, :] - output[..., ankle, :]
        direction = direction / torch.linalg.vector_norm(direction, dim=-1, keepdim=True).clamp_min(1.0e-6)
        output[..., knee, :] = output[..., ankle, :] + target[pair] * direction
    return output


def body_structure_loss(
    position: torch.Tensor, target: torch.Tensor, lower: torch.Tensor, upper: torch.Tensor,
) -> torch.Tensor:
    distance = torch.stack(
        [torch.linalg.vector_norm(position[..., first, :] - position[..., second, :], dim=-1)
         for first, second, _ in BODY_STRUCTURE_PAIRS],
        dim=-1,
    )
    fixed = ((distance[..., :2] - target[:2]) / 0.005).square().mean()
    bounded = (
        (F.relu(lower[2:] - distance[..., 2:]) / 0.02).square()
        + (F.relu(distance[..., 2:] - upper[2:]) / 0.02).square()
    ).mean()
    return fixed + bounded


def decode_boundary(
    normalized_delta: torch.Tensor, start_position: torch.Tensor, start_rotation: torch.Tensor,
    mean: torch.Tensor, std: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    delta = normalized_delta * std + mean
    position = start_position + delta[:, :21].reshape(-1, len(BODY_NAMES), 3)
    rotation = start_rotation + delta[:, 21:].reshape(-1, len(BODY_NAMES), 6)
    matrix = rotation_matrix_6d(rotation)
    rotation = matrix[..., :, :2].reshape_as(rotation)
    return position, rotation


def contact_offsets(data: dict[str, np.ndarray], indices: np.ndarray) -> np.ndarray:
    offsets=np.zeros((len(PARTS),3),np.float32)
    for part,body in enumerate(PART_BODY_INDEX):
        selected=indices[data["touchdown"][indices,part]>.5]
        if len(selected):
            matrix=rotation_matrix_6d(torch.from_numpy(data["rotations"][selected,-1,body])).numpy()
            world_offset=data["positions"][selected,-1,body]-data["target_contacts"][selected,part]
            offsets[part]=np.median(np.einsum("bij,bj->bi",matrix.transpose(0,2,1),world_offset),axis=0)
    return offsets


def per_sample_contact_offsets(data: dict[str, np.ndarray]) -> np.ndarray:
    output=np.zeros((len(data["positions"]),len(PARTS),3),np.float32)
    for part,body in enumerate(PART_BODY_INDEX):
        selected=np.flatnonzero(data["touchdown"][:,part]>.5)
        matrix=rotation_matrix_6d(torch.from_numpy(data["rotations"][selected,-1,body])).numpy()
        world_offset=data["positions"][selected,-1,body]-data["target_contacts"][selected,part]
        output[selected,part]=np.einsum("bij,bj->bi",matrix.transpose(0,2,1),world_offset)
    return output


def enforce_contact_boundary(
    position: torch.Tensor, rotation6d: torch.Tensor, start_position: torch.Tensor,
    start_rotation6d: torch.Tensor, target_contact: torch.Tensor, touchdown: torch.Tensor,
    end_contact: torch.Tensor, offsets: torch.Tensor | None = None,
    raw_target_contact: torch.Tensor | None = None,
    persistent_offsets: torch.Tensor | None = None,
) -> torch.Tensor:
    """Construct contacting link positions from exact contact anchors."""
    output=position.clone()
    if raw_target_contact is not None:
        for part,body in enumerate(PART_BODY_INDEX):
            shifted=output[:,body]+target_contact[:,part]-raw_target_contact[:,part]
            output[:,body]=torch.where(touchdown[:,part,None]>.5,shifted,output[:,body])
        if persistent_offsets is not None:
            end_matrix=rotation_matrix_6d(rotation6d)
            start_matrix=rotation_matrix_6d(start_rotation6d)
            for part,body in enumerate(PART_BODY_INDEX):
                offset=persistent_offsets[part].expand(len(output),-1)
                start_offset=torch.einsum("bij,bj->bi",start_matrix[:,body],offset)
                end_offset=torch.einsum("bij,bj->bi",end_matrix[:,body],offset)
                persistent_position=start_position[:,body]-start_offset+end_offset
                persistent=(end_contact[:,part]>.5)&(touchdown[:,part]<=.5)
                output[:,body]=torch.where(persistent[:,None],persistent_position,output[:,body])
        return output
    if offsets is None:
        return output
    if offsets.ndim == 3:
        end_matrix=rotation_matrix_6d(rotation6d)
        start_matrix=rotation_matrix_6d(start_rotation6d)
        support_offsets=offsets if persistent_offsets is None else persistent_offsets
        for part,body in enumerate(PART_BODY_INDEX):
            end_offset=torch.einsum("bij,bj->bi",end_matrix[:,body],offsets[:,part])
            touchdown_position=target_contact[:,part]+end_offset
            output[:,body]=torch.where(touchdown[:,part,None]>.5,touchdown_position,output[:,body])
            support_offset=(
                support_offsets[:,part]
                if support_offsets.ndim == 3
                else support_offsets[part].expand(len(output),-1)
            )
            start_support_offset=torch.einsum("bij,bj->bi",start_matrix[:,body],support_offset)
            end_support_offset=torch.einsum("bij,bj->bi",end_matrix[:,body],support_offset)
            persistent_position=start_position[:,body]-start_support_offset+end_support_offset
            persistent=(end_contact[:,part]>.5)&(touchdown[:,part]<=.5)
            output[:,body]=torch.where(persistent[:,None],persistent_position,output[:,body])
        return output
    end_matrix=rotation_matrix_6d(rotation6d); start_matrix=rotation_matrix_6d(start_rotation6d)
    for part,body in enumerate(PART_BODY_INDEX):
        offset=offsets[part]
        end_offset=torch.einsum("bij,j->bi",end_matrix[:,body],offset)
        touchdown_position=target_contact[:,part]+end_offset
        start_offset=torch.einsum("bij,j->bi",start_matrix[:,body],offset)
        persistent_position=start_position[:,body]-start_offset+end_offset
        output[:,body]=torch.where(touchdown[:,part,None]>.5,touchdown_position,output[:,body])
        persistent=(end_contact[:,part]>.5)&(touchdown[:,part]<=.5)
        output[:,body]=torch.where(persistent[:,None],persistent_position,output[:,body])
    return output


def relocalized_state(
    position: torch.Tensor, rotation6d: torch.Tensor, contacts: torch.Tensor,
) -> torch.Tensor:
    """Differentiably express a predicted end boundary in its next torso-yaw frame."""
    matrix = rotation_matrix_6d(rotation6d)
    yaw = torch.atan2(matrix[:, 0, 1, 0], matrix[:, 0, 0, 0])
    cosine, sine = torch.cos(yaw), torch.sin(yaw)
    world_to_next = torch.zeros((len(position), 3, 3), dtype=position.dtype, device=position.device)
    world_to_next[:, 0, 0] = cosine; world_to_next[:, 0, 1] = sine
    world_to_next[:, 1, 0] = -sine; world_to_next[:, 1, 1] = cosine
    world_to_next[:, 2, 2] = 1.0
    local_position = torch.einsum("bij,bpj->bpi", world_to_next, position-position[:, :1])
    local_matrix = torch.einsum("bij,bpjk->bpik", world_to_next, matrix)
    local_rotation6d = local_matrix[..., :, :2].reshape_as(rotation6d)
    return torch.cat((contacts, local_position.flatten(1), local_rotation6d.flatten(1)), -1)


def relocalized_geometry(
    position: torch.Tensor, rotation6d: torch.Tensor, box_origin: torch.Tensor, box_basis: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Move local box geometry into the torso-yaw frame of a predicted boundary."""
    matrix=rotation_matrix_6d(rotation6d)
    yaw=torch.atan2(matrix[:,0,1,0],matrix[:,0,0,0]); cosine,sine=torch.cos(yaw),torch.sin(yaw)
    world_to_next=torch.zeros((len(position),3,3),dtype=position.dtype,device=position.device)
    world_to_next[:,0,0]=cosine; world_to_next[:,0,1]=sine
    world_to_next[:,1,0]=-sine; world_to_next[:,1,1]=cosine; world_to_next[:,2,2]=1.0
    next_origin=torch.einsum("bij,bj->bi",world_to_next,box_origin-position[:,0])
    next_basis=torch.einsum("bij,bjk->bik",world_to_next,box_basis)
    return next_origin,next_basis


def render_scan_torch(
    box_origin: torch.Tensor, box_basis: torch.Tensor, edge_start: torch.Tensor,
    edge_inward: torch.Tensor, box_height: torch.Tensor,
) -> torch.Tensor:
    """Runtime-equivalent local height scan for differentiable unroll geometry."""
    grid=torch.as_tensor(local_scan_grid(),dtype=box_origin.dtype,device=box_origin.device)
    points=grid[None].expand(len(box_origin),-1,-1)
    coordinates=torch.einsum("bpj,bjk->bpk",points-box_origin[:,None],box_basis)
    edge_depth=torch.einsum("bpvi,bvi->bpv",coordinates[...,None,:2]-edge_start[:,None],edge_inward).amin(-1)
    ground=box_origin[:,2]-box_height
    heights=torch.where(edge_depth>=0.0,box_origin[:,None,2],ground[:,None])
    return heights.clamp(-float(SCAN_CLIP_M),float(SCAN_CLIP_M))


def metric_summary(value: np.ndarray) -> dict[str, float]:
    value = np.asarray(value, dtype=np.float64)
    return {"mean": float(value.mean()), "p95": float(np.quantile(value, .95)), "max": float(value.max())}


@torch.no_grad()
def evaluate(model, tensors, indices, labels, action_masks, stats, offsets, offset_stats, device, terrain_conditioning="scan"):
    (state, scan, target_contact, duration, touchdown, target_boundary, start_position, start_rotation,
     end_contact, target_surface, box_origin, box_basis, edge_start, edge_inward, box_height) = tensors
    sm, ss, hm, hs, cm, cs, dm, ds, bm, bs = stats
    idx = torch.as_tensor(indices, dtype=torch.long, device=device)
    output = model((state[idx]-sm)/ss, (scan[idx]-hm)/hs)
    action = output[0].argmax(-1)
    predicted_contact = output[2] * cs + cm
    if terrain_conditioning == "privileged":
        predicted_contact_np = conform_contact_targets_to_geometry(
            predicted_contact.cpu().numpy(), touchdown[idx].cpu().numpy(),
            box_origin[idx].cpu().numpy(), box_basis[idx].cpu().numpy(),
            edge_start[idx].cpu().numpy(), box_height[idx].cpu().numpy(),
        )
    else:
        predicted_contact_np = conform_contact_targets_to_scan(
            predicted_contact.cpu().numpy(), touchdown[idx].cpu().numpy(), scan[idx].cpu().numpy(),
        )
    predicted_position, predicted_rotation = decode_boundary(
        output[4], start_position[idx], start_rotation[idx], bm, bs,
    )
    predicted_contact_t=torch.from_numpy(predicted_contact_np).to(device)
    offset_mean,offset_std=offset_stats
    predicted_offsets=output[5].reshape(-1,len(PARTS),3)*offset_std+offset_mean
    predicted_position=enforce_contact_boundary(
        predicted_position,predicted_rotation,start_position[idx],start_rotation[idx],predicted_contact_t,
        action_masks[action].float(),end_contact[idx],offsets=predicted_offsets,
        persistent_offsets=offsets,
    )
    target_position, target_rotation = decode_boundary(
        target_boundary[idx], start_position[idx], start_rotation[idx], bm, bs,
    )
    position_error = torch.linalg.vector_norm(predicted_position-target_position, dim=-1).cpu().numpy()*100.0
    predicted_matrix = rotation_matrix_6d(predicted_rotation)
    target_matrix = rotation_matrix_6d(target_rotation)
    relative = predicted_matrix.transpose(-1,-2) @ target_matrix
    cosine = ((relative.diagonal(dim1=-2,dim2=-1).sum(-1)-1.0)*.5).clamp(-1,1)
    rotation_error = torch.rad2deg(torch.acos(cosine)).cpu().numpy()
    active = touchdown[idx].cpu().numpy() > .5
    contact_error = np.linalg.norm(predicted_contact_np-target_contact[idx].cpu().numpy(), axis=-1)[active]*100.0
    active_link = []
    for row, part in zip(*np.nonzero(active), strict=True):
        active_link.append(position_error[row, PART_BODY_INDEX[part]])
    seconds = torch.exp(output[3]*ds+dm)
    clearance=contact_aware_sparse_clearance(
        predicted_position[:,None],end_contact[idx][:,None],target_surface[idx],box_origin[idx],box_basis[idx],
        edge_start[idx],edge_inward[idx],box_height[idx],
    ).cpu().numpy()
    return {
        "samples": int(len(indices)),
        "action_exact_accuracy": float((action == labels[idx]).float().mean()),
        "touchdown_exact_accuracy": float((action_masks[action] == touchdown[idx].bool()).all(-1).float().mean()),
        "target_contact_error_cm": metric_summary(contact_error),
        "full_boundary_position_error_cm": metric_summary(position_error),
        "torso_boundary_position_error_cm": metric_summary(position_error[:, 0]),
        "active_link_boundary_position_error_cm": metric_summary(np.asarray(active_link)),
        "full_boundary_rotation_error_deg": metric_summary(rotation_error),
        "duration_error_frames_at_50hz": float((seconds-duration[idx]).abs().mean()*50.0),
        "endpoint_collision_free_fraction": float((clearance<=0.0).all(axis=(1,2)).mean()),
        "maximum_endpoint_penetration_cm": metric_summary(np.maximum(clearance,0.0).max(axis=(1,2))*100.0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=ROOT/"tmp/climb00_scan_full_boundary_selector_v1")
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--blocks", type=int, default=4)
    parser.add_argument("--action-embedding-dim", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--endpoint-collision-weight", type=float, default=4.0)
    parser.add_argument("--unroll-weight", type=float, default=0.5)
    parser.add_argument("--unroll-steps", type=int, default=4)
    parser.add_argument("--initial-checkpoint", type=Path)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--terrain-conditioning", choices=("scan", "privileged"), default="scan")
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device(args.device)
    data, samples, event_summary, state_np, scan_np = arrays(args.manifest)
    if args.terrain_conditioning == "privileged":
        scan_np = privileged_geometry_array(data)
    splits = {name: np.asarray([i for i,s in enumerate(samples) if split_name(s.height)==name], np.int64)
              for name in ("train_height_095_100_105","validation_height_090","test_height_110")}
    train = splits["train_height_095_100_105"]
    touchdown_masks, end_masks = transition_vocabulary(data["touchdown"][train], data["end_contact"][train])
    labels_np = transition_labels(data["touchdown"], data["end_contact"], touchdown_masks, end_masks)
    boundary_np = boundary_delta(data)
    state_mean, state_std = state_np[train].mean(0), np.maximum(state_np[train].std(0), 1e-3)
    scan_mean, scan_std = scan_np[train].mean(0), np.maximum(scan_np[train].std(0), 1e-3)
    contact_mean, contact_std = contact_stats(data["target_contacts"], data["touchdown"], train)
    duration_mean = float(np.log(data["duration"][train]).mean())
    duration_std = float(max(np.log(data["duration"][train]).std(), 1e-3))
    boundary_mean = boundary_np[train].mean(0)
    boundary_std = np.maximum(boundary_np[train].std(0), 1e-3)
    offsets_np=contact_offsets(data,train)
    sample_offsets=per_sample_contact_offsets(data)
    offset_mean=np.zeros((len(PARTS),3),np.float32); offset_std=np.ones((len(PARTS),3),np.float32)
    for part in range(len(PARTS)):
        selected=train[data["touchdown"][train,part]>.5]
        offset_mean[part]=sample_offsets[selected,part].mean(0); offset_std[part]=np.maximum(sample_offsets[selected,part].std(0),.005)
    normalized_offsets=(sample_offsets-offset_mean)/offset_std
    normalized_boundary = (boundary_np-boundary_mean)/boundary_std
    normalized_contact = (data["target_contacts"]-contact_mean)/contact_std
    successor_lookup={(sample.motion_id,sample.current_frame):i for i,sample in enumerate(samples)}
    successor=np.asarray([successor_lookup.get((sample.motion_id,sample.target_frame),-1) for sample in samples],np.int64)
    if args.unroll_steps < 1:
        raise ValueError("unroll steps must be positive")
    chain=np.full((len(train),args.unroll_steps),-1,np.int64)
    cursor=train.copy()
    for depth in range(args.unroll_steps):
        cursor=np.where(cursor>=0,successor[np.maximum(cursor,0)],-1)
        chain[:,depth]=cursor
    chain_valid=chain>=0; safe_chain=np.maximum(chain,0)
    dataset = TensorDataset(
        torch.from_numpy(((state_np[train]-state_mean)/state_std).astype(np.float32)),
        torch.from_numpy(((scan_np[train]-scan_mean)/scan_std).astype(np.float32)),
        torch.from_numpy(labels_np[train]),
        torch.from_numpy(normalized_contact[train].astype(np.float32)),
        torch.from_numpy(data["touchdown"][train]),
        torch.from_numpy(((np.log(data["duration"][train])-duration_mean)/duration_std).astype(np.float32)),
        torch.from_numpy(normalized_boundary[train].astype(np.float32)),
        torch.from_numpy(data["positions"][train,0]), torch.from_numpy(data["rotations"][train,0]),
        torch.from_numpy(data["end_contact"][train]), torch.from_numpy(data["target_surfaces"][train]),
        torch.from_numpy(data["box_origin"][train]), torch.from_numpy(data["box_basis"][train]),
        torch.from_numpy(data["box_edge_start"][train]), torch.from_numpy(data["box_edge_inward"][train]),
        torch.from_numpy(data["box_height"][train]), torch.from_numpy(chain_valid),
        torch.from_numpy(((scan_np[safe_chain]-scan_mean)/scan_std).astype(np.float32)),
        torch.from_numpy(labels_np[safe_chain]), torch.from_numpy(normalized_contact[safe_chain].astype(np.float32)),
        torch.from_numpy(data["touchdown"][safe_chain]),
        torch.from_numpy(((np.log(data["duration"][safe_chain])-duration_mean)/duration_std).astype(np.float32)),
        torch.from_numpy(normalized_boundary[safe_chain].astype(np.float32)),
        torch.from_numpy(data["end_contact"][safe_chain]), torch.from_numpy(normalized_offsets[safe_chain].astype(np.float32)),
        torch.from_numpy(data["target_surfaces"][safe_chain]), torch.from_numpy(data["box_origin"][safe_chain]),
        torch.from_numpy(data["box_basis"][safe_chain]), torch.from_numpy(data["box_edge_start"][safe_chain]),
        torch.from_numpy(data["box_edge_inward"][safe_chain]), torch.from_numpy(data["box_height"][safe_chain]),
        torch.from_numpy(normalized_offsets[train].astype(np.float32)),
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=False)
    model_class = PrivilegedFullBoundarySelector if args.terrain_conditioning == "privileged" else ScanFullBoundarySelector
    model = model_class(
        state_np.shape[1], len(touchdown_masks), boundary_dim=boundary_np.shape[1], contact_offset_dim=len(PARTS)*3, width=args.width,
        blocks=args.blocks, action_embedding_dim=args.action_embedding_dim,
        transition_end_contact_masks=torch.from_numpy(end_masks),
    ).to(device)
    if args.initial_checkpoint is not None:
        initial=torch.load(args.initial_checkpoint,map_location="cpu",weights_only=False)
        if int(initial["condition_dim"])!=state_np.shape[1]:
            raise ValueError("initial selector condition dimension mismatch")
        if not torch.equal(initial["action_touchdown_masks"].bool(),torch.from_numpy(touchdown_masks).bool()):
            raise ValueError("initial selector touchdown vocabulary mismatch")
        if not torch.equal(initial["action_end_contact_masks"].bool(),torch.from_numpy(end_masks).bool()):
            raise ValueError("initial selector end-contact vocabulary mismatch")
        if initial.get("schema","").startswith("climb00_privileged_") == (args.terrain_conditioning == "privileged"):
            model.load_state_dict(initial["model"])
        else:
            current=model.state_dict()
            transferable={
                key:value for key,value in initial["model"].items()
                if not key.startswith("scan.") and key in current and current[key].shape == value.shape
            }
            incompatible=model.load_state_dict(transferable,strict=False)
            print(json.dumps({
                "cross_conditioning_warm_start":str(args.initial_checkpoint),
                "transferred_tensors":len(transferable),
                "reinitialized_prefix":"scan.",
                "missing_tensors":len(incompatible.missing_keys),
            }))
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    labels = torch.from_numpy(labels_np).to(device)
    stats = tuple(torch.from_numpy(x).float().to(device) for x in (
        state_mean,state_std,scan_mean,scan_std,contact_mean,contact_std,
    )) + (torch.tensor(duration_mean,device=device),torch.tensor(duration_std,device=device),
          torch.from_numpy(boundary_mean).to(device),torch.from_numpy(boundary_std).to(device))
    tensors = (
        torch.from_numpy(state_np).to(device), torch.from_numpy(scan_np).to(device),
        torch.from_numpy(data["target_contacts"]).to(device), torch.from_numpy(data["duration"]).to(device),
        torch.from_numpy(data["touchdown"]).to(device), torch.from_numpy(normalized_boundary).to(device),
        torch.from_numpy(data["positions"][:,0]).to(device), torch.from_numpy(data["rotations"][:,0]).to(device),
        torch.from_numpy(data["end_contact"]).to(device), torch.from_numpy(data["target_surfaces"]).to(device),
        torch.from_numpy(data["box_origin"]).to(device), torch.from_numpy(data["box_basis"]).to(device),
        torch.from_numpy(data["box_edge_start"]).to(device), torch.from_numpy(data["box_edge_inward"]).to(device),
        torch.from_numpy(data["box_height"]).to(device),
    )
    action_masks = torch.from_numpy(touchdown_masks).bool().to(device)
    offsets=torch.from_numpy(offsets_np).to(device)
    offset_stats=(torch.from_numpy(offset_mean).to(device),torch.from_numpy(offset_std).to(device))
    best_score, best_state, history = math.inf, None, []
    for epoch in range(1,args.epochs+1):
        model.train(); running=[]
        for batch in loader:
            (state_b,scan_b,label_b,contact_b,touchdown_b,duration_b,boundary_b,start_p_b,start_r_b,
             end_b,surface_b,box_origin_b,box_basis_b,edge_start_b,edge_inward_b,box_height_b,
             chain_valid_b,chain_scan_b,chain_label_b,chain_contact_b,chain_touchdown_b,chain_duration_b,
             chain_boundary_b,chain_end_b,chain_offset_b,chain_surface_b,chain_box_origin_b,chain_box_basis_b,
             chain_edge_start_b,chain_edge_inward_b,chain_box_height_b,offset_b)=batch
            state_b,scan_b,label_b = state_b.to(device),scan_b.to(device),label_b.to(device)
            contact_b,touchdown_b,duration_b,boundary_b = contact_b.to(device),touchdown_b.to(device),duration_b.to(device),boundary_b.to(device)
            start_p_b,start_r_b,end_b=start_p_b.to(device),start_r_b.to(device),end_b.to(device)
            surface_b,box_origin_b,box_basis_b=surface_b.to(device),box_origin_b.to(device),box_basis_b.to(device)
            edge_start_b,edge_inward_b,box_height_b=edge_start_b.to(device),edge_inward_b.to(device),box_height_b.to(device)
            chain_valid_b,chain_scan_b,chain_label_b=chain_valid_b.to(device),chain_scan_b.to(device),chain_label_b.to(device)
            chain_contact_b,chain_touchdown_b=chain_contact_b.to(device),chain_touchdown_b.to(device)
            chain_duration_b,chain_boundary_b=chain_duration_b.to(device),chain_boundary_b.to(device)
            chain_end_b,chain_offset_b=chain_end_b.to(device),chain_offset_b.to(device)
            chain_surface_b,chain_box_origin_b,chain_box_basis_b=chain_surface_b.to(device),chain_box_origin_b.to(device),chain_box_basis_b.to(device)
            chain_edge_start_b,chain_edge_inward_b,chain_box_height_b=chain_edge_start_b.to(device),chain_edge_inward_b.to(device),chain_box_height_b.to(device)
            offset_b=offset_b.to(device)
            output=model(state_b,scan_b,label_b)
            active=touchdown_b[...,None]
            contact_loss=((output[2]-contact_b).square()*active).sum()/active.sum().clamp_min(1.0)/3.0
            predicted_p,predicted_r=decode_boundary(output[4],start_p_b,start_r_b,stats[-2],stats[-1])
            predicted_contact=output[2]*stats[5]+stats[4]
            predicted_offsets=output[5].reshape(-1,len(PARTS),3)*offset_stats[1]+offset_stats[0]
            predicted_p=enforce_contact_boundary(
                predicted_p,predicted_r,start_p_b,start_r_b,predicted_contact,touchdown_b,end_b,
                offsets=predicted_offsets,persistent_offsets=offsets,
            )
            clearance=contact_aware_sparse_clearance(
                predicted_p[:,None],end_b[:,None],surface_b,box_origin_b,box_basis_b,
                edge_start_b,edge_inward_b,box_height_b,
            )
            positive=F.relu(clearance)/.02
            endpoint_collision=positive.square().mean()+positive.amax((1,2)).square().mean()
            unroll=torch.zeros((),device=device); unroll_terms=0
            recurrent_end=end_b
            recurrent_raw_state=relocalized_state(predicted_p,predicted_r,recurrent_end)
            recurrent_p=recurrent_raw_state[:,len(PARTS):len(PARTS)+21].reshape(-1,len(BODY_NAMES),3)
            recurrent_r=recurrent_raw_state[:,len(PARTS)+21:].reshape(-1,len(BODY_NAMES),6)
            recurrent_state=(recurrent_raw_state-stats[0])/stats[1]
            recurrent_box_origin,recurrent_box_basis=relocalized_geometry(
                predicted_p,predicted_r,box_origin_b,box_basis_b,
            )
            recurrent_edge_start=edge_start_b; recurrent_edge_inward=edge_inward_b; recurrent_box_height=box_height_b
            for depth in range(args.unroll_steps):
                valid=chain_valid_b[:,depth]
                if not valid.any():
                    continue
                state_d=recurrent_state[valid]
                if args.terrain_conditioning == "privileged":
                    scan_raw_d=privileged_geometry_torch(
                        recurrent_box_origin[valid],recurrent_box_basis[valid],recurrent_edge_start[valid],
                        recurrent_edge_inward[valid],recurrent_box_height[valid],
                    )
                else:
                    scan_raw_d=render_scan_torch(
                        recurrent_box_origin[valid],recurrent_box_basis[valid],recurrent_edge_start[valid],
                        recurrent_edge_inward[valid],recurrent_box_height[valid],
                    )
                scan_d=(scan_raw_d-stats[2])/stats[3]; label_d=chain_label_b[valid,depth]
                output_d=model(state_d,scan_d,label_d)
                touchdown_d=chain_touchdown_b[valid,depth]; end_d=chain_end_b[valid,depth]
                active_d=touchdown_d[...,None]
                contact_d=((output_d[2]-chain_contact_b[valid,depth]).square()*active_d).sum()/active_d.sum().clamp_min(1.0)/3.0
                offset_d=((output_d[5].reshape(-1,len(PARTS),3)-chain_offset_b[valid,depth]).square()*active_d).sum()/active_d.sum().clamp_min(1.0)/3.0
                next_p,next_r=decode_boundary(output_d[4],recurrent_p[valid],recurrent_r[valid],stats[-2],stats[-1])
                predicted_contact_d=output_d[2]*stats[5]+stats[4]
                predicted_offset_d=output_d[5].reshape(-1,len(PARTS),3)*offset_stats[1]+offset_stats[0]
                next_p=enforce_contact_boundary(
                    next_p,next_r,recurrent_p[valid],recurrent_r[valid],predicted_contact_d,touchdown_d,end_d,
                    offsets=predicted_offset_d,persistent_offsets=offsets,
                )
                clearance_d=contact_aware_sparse_clearance(
                    next_p[:,None],end_d[:,None],chain_surface_b[valid,depth],recurrent_box_origin[valid],
                    recurrent_box_basis[valid],recurrent_edge_start[valid],recurrent_edge_inward[valid],
                    recurrent_box_height[valid],
                )
                positive_d=F.relu(clearance_d)/.02
                collision_d=positive_d.square().mean()+positive_d.amax((1,2)).square().mean()
                step_loss=(F.cross_entropy(output_d[0],label_d)+contact_d+offset_d+
                           (output_d[3]-chain_duration_b[valid,depth]).square().mean()+
                           2.0*(output_d[4]-chain_boundary_b[valid,depth]).square().mean()+
                           args.endpoint_collision_weight*collision_d)
                unroll=unroll+step_loss; unroll_terms+=1
                updated_p=recurrent_p.clone(); updated_r=recurrent_r.clone(); updated_end=recurrent_end.clone()
                updated_p[valid]=next_p; updated_r[valid]=next_r; updated_end[valid]=end_d
                next_box_origin,next_box_basis=relocalized_geometry(
                    next_p,next_r,recurrent_box_origin[valid],recurrent_box_basis[valid],
                )
                updated_box_origin=recurrent_box_origin.clone(); updated_box_basis=recurrent_box_basis.clone()
                updated_box_origin[valid]=next_box_origin; updated_box_basis[valid]=next_box_basis
                recurrent_raw_state=relocalized_state(updated_p,updated_r,updated_end)
                recurrent_p=recurrent_raw_state[:,len(PARTS):len(PARTS)+21].reshape(-1,len(BODY_NAMES),3)
                recurrent_r=recurrent_raw_state[:,len(PARTS)+21:].reshape(-1,len(BODY_NAMES),6)
                recurrent_end=updated_end
                recurrent_box_origin,recurrent_box_basis=updated_box_origin,updated_box_basis
                recurrent_state=(recurrent_raw_state-stats[0])/stats[1]
            if unroll_terms:
                unroll=unroll/float(unroll_terms)
            offset_loss=((output[5].reshape_as(offset_b)-offset_b).square()*active).sum()/active.sum().clamp_min(1.0)/3.0
            loss=(F.cross_entropy(output[0],label_b)+contact_loss+offset_loss+(output[3]-duration_b).square().mean()+2.0*(output[4]-boundary_b).square().mean()+args.endpoint_collision_weight*endpoint_collision+args.unroll_weight*unroll)
            optimizer.zero_grad(set_to_none=True); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),2.0); optimizer.step()
            running.append(float(loss.detach()))
        if epoch==1 or epoch%20==0 or epoch==args.epochs:
            model.eval(); metric=evaluate(model,tensors,splits["validation_height_090"],labels,action_masks,stats,offsets,offset_stats,device,args.terrain_conditioning)
            score=(metric["full_boundary_position_error_cm"]["mean"]+5.0*(1.0-metric["action_exact_accuracy"])
                   +20.0*(1.0-metric["endpoint_collision_free_fraction"]))
            record={"epoch":epoch,"train_loss":float(np.mean(running)),"validation":metric}; history.append(record)
            print(json.dumps(record))
            if score<best_score: best_score=score; best_state=copy.deepcopy(model.state_dict())
    assert best_state is not None; model.load_state_dict(best_state); model.eval()
    metrics={name:evaluate(model,tensors,index,labels,action_masks,stats,offsets,offset_stats,device,args.terrain_conditioning) for name,index in splits.items()}
    checkpoint={
        "schema":("climb00_privileged_full_boundary_selector_v1" if args.terrain_conditioning == "privileged" else "climb00_scan_full_boundary_selector_v1"),"model":best_state,"body_names":BODY_NAMES,
        "parts":PARTS,"condition_dim":state_np.shape[1],"action_touchdown_masks":torch.from_numpy(touchdown_masks),
        "action_end_contact_masks":torch.from_numpy(end_masks),"state_mean":torch.from_numpy(state_mean),
        "state_std":torch.from_numpy(state_std),"scan_mean":torch.from_numpy(scan_mean),"scan_std":torch.from_numpy(scan_std),
        "contact_mean":torch.from_numpy(contact_mean),"contact_std":torch.from_numpy(contact_std),
        "duration_mean":duration_mean,"duration_std":duration_std,"boundary_mean":torch.from_numpy(boundary_mean),
        "boundary_std":torch.from_numpy(boundary_std),"contact_offsets":torch.from_numpy(offsets_np),"contact_offset_mean":torch.from_numpy(offset_mean),"contact_offset_std":torch.from_numpy(offset_std),"config":vars(args),
    }
    torch.save(checkpoint,args.output/"model.pt")
    report={"schema":("climb00_privileged_full_boundary_selector_report_v1" if args.terrain_conditioning == "privileged" else "climb00_scan_full_boundary_selector_report_v1"),"event_dataset":event_summary,
            "splits":{k:int(len(v)) for k,v in splits.items()},"metrics":metrics,"history":history,
            "model_contract":{"input":("current full sparse boundary + contacts + exact local terrain geometry" if args.terrain_conditioning == "privileged" else "current full sparse boundary + contacts + local height scan"),
                              "output":"next contact topology + contact targets + duration + complete next 7-body position/rotation boundary",
                              "state_ownership":"the selected next boundary is authoritative; a downstream deformer may not alter it"}}
    (args.output/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(args.output),"metrics":metrics}))


if __name__=="__main__": main()
