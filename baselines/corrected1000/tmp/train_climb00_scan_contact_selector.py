#!/usr/bin/env python3
"""Train a local-scan-only next-contact selector for climb00.

The model never receives edit parameters, exact surface IDs/UVs, polygon
corners or ground height.  Exact geometry is used only to render the same
forward-local height observation available to the deployed robot and to construct
supervised contact-point labels.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT / "tmp"))

from climb00_scan_observation import (  # noqa: E402
    SCAN_CLIP_M, SCAN_COLS, SCAN_ROWS, conform_contact_targets_to_scan, local_scan_grid,
    scans_from_local_box,
)
from train_climb00_contact_conditioned_infiller import build_dataset  # noqa: E402
from train_climb00_contact_event_predictor import (  # noqa: E402
    PARTS, ResidualBlock, action_labels, observed_action_vocabulary, split_name,
)


DEFAULT_MANIFEST = ROOT / "tmp/climb00_continuous_coverage/training_manifest_207.json"
DEFAULT_OUTPUT = ROOT / "tmp/climb00_scan_contact_selector_v1"


class ScanEncoder(nn.Module):
    def __init__(self, width: int, scan_rows: int = SCAN_ROWS, scan_cols: int = SCAN_COLS):
        super().__init__()
        self.scan_rows = int(scan_rows)
        self.scan_cols = int(scan_cols)
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.SiLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.SiLU(),
        )
        reduced_rows = (self.scan_rows + 1) // 2
        reduced_cols = (self.scan_cols + 1) // 2
        self.out = nn.Sequential(
            nn.Flatten(), nn.Linear(64 * reduced_rows * reduced_cols, width), nn.SiLU()
        )

    def forward(self, scan: torch.Tensor) -> torch.Tensor:
        expected = self.scan_rows * self.scan_cols
        if scan.ndim != 2 or scan.shape[1] != expected:
            raise ValueError(f"height scan must be [B,{expected}], got {tuple(scan.shape)}")
        return self.out(self.conv(scan.reshape(-1, 1, self.scan_rows, self.scan_cols)))


class ScanContactSelector(nn.Module):
    def __init__(
        self, state_dim: int, action_count: int, width: int = 256,
        blocks: int = 4, action_embedding_dim: int = 64,
        scan_rows: int = SCAN_ROWS, scan_cols: int = SCAN_COLS,
        transition_end_contact_masks: torch.Tensor | None = None,
    ):
        super().__init__()
        self.scan = ScanEncoder(width, scan_rows, scan_cols)
        self.state = nn.Sequential(nn.Linear(state_dim, width), nn.SiLU(), ResidualBlock(width))
        self.trunk = nn.Sequential(
            nn.Linear(2 * width, width), nn.SiLU(),
            *(ResidualBlock(width) for _ in range(blocks)), nn.LayerNorm(width),
        )
        self.action = nn.Linear(width, action_count)
        self.action_embedding = nn.Embedding(action_count, action_embedding_dim)
        self.parameter_trunk = nn.Sequential(
            nn.Linear(width + action_embedding_dim, width), nn.SiLU(),
            ResidualBlock(width), nn.LayerNorm(width),
        )
        self.end_contact = nn.Linear(width, len(PARTS))
        if transition_end_contact_masks is None:
            transition_end_contact_masks = torch.empty((0, len(PARTS)), dtype=torch.bool)
        self.register_buffer(
            "transition_end_contact_masks", transition_end_contact_masks.bool(), persistent=False
        )
        self.target_contact = nn.Linear(width, len(PARTS) * 3)
        self.duration = nn.Linear(width, 1)

    def encode(self, state: torch.Tensor, scan: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = self.trunk(torch.cat((self.state(state), self.scan(scan)), dim=-1))
        return hidden, self.action(hidden)

    def decode_parameters(
        self, hidden: torch.Tensor, action_index: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        value = self.parameter_trunk(torch.cat((hidden, self.action_embedding(action_index)), dim=-1))
        raw_end_contact = self.end_contact(value)
        if self.transition_end_contact_masks.numel():
            raw_end_contact = 12.0 * (
                2.0 * self.transition_end_contact_masks[action_index].to(value.dtype) - 1.0
            )
        return (
            raw_end_contact,
            self.target_contact(value).reshape(-1, len(PARTS), 3),
            self.duration(value).squeeze(-1),
        )

    def forward(
        self, state: torch.Tensor, scan: torch.Tensor, action_index: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, ...]:
        hidden, action_logits = self.encode(state, scan)
        if action_index is None:
            action_index = action_logits.argmax(dim=-1)
        return action_logits, *self.decode_parameters(hidden, action_index)


def arrays(manifest: Path, phase_frames: int = 64):
    data, samples, event_summary = build_dataset(manifest, phase_frames)
    pose = np.concatenate(
        (data["positions"][:, 0].reshape(len(samples), -1), data["rotations"][:, 0].reshape(len(samples), -1)),
        axis=-1,
    ).astype(np.float32)
    state = np.concatenate((data["start_contacts"], pose), axis=-1).astype(np.float32)
    scan = scans_from_local_box(
        data["box_origin"], data["box_basis"], data["box_edge_start"],
        data["box_edge_inward"], data["box_height"],
    )
    return data, samples, event_summary, state, scan


def contact_stats(target: np.ndarray, touchdown: np.ndarray, indices: np.ndarray):
    mean = np.zeros((len(PARTS), 3), dtype=np.float32)
    std = np.ones((len(PARTS), 3), dtype=np.float32)
    for part in range(len(PARTS)):
        selected = indices[touchdown[indices, part] > 0.5]
        if len(selected):
            mean[part] = target[selected, part].mean(axis=0)
            std[part] = np.maximum(target[selected, part].std(axis=0), 0.01)
    return mean, std


def transition_vocabulary(touchdown: np.ndarray, end_contact: np.ndarray):
    pair = np.concatenate((touchdown.astype(bool), end_contact.astype(bool)), axis=-1)
    pair = np.unique(pair, axis=0)
    return pair[:, : len(PARTS)], pair[:, len(PARTS) :]


def transition_labels(
    touchdown: np.ndarray, end_contact: np.ndarray,
    touchdown_masks: np.ndarray, end_contact_masks: np.ndarray,
) -> np.ndarray:
    lookup = {
        tuple(np.concatenate((touchdown_mask, end_mask)).tolist()): index
        for index, (touchdown_mask, end_mask) in enumerate(zip(touchdown_masks, end_contact_masks, strict=True))
    }
    return np.asarray([
        lookup[tuple(np.concatenate((td.astype(bool), end.astype(bool))).tolist())]
        for td, end in zip(touchdown, end_contact, strict=True)
    ], dtype=np.int64)


@torch.no_grad()
def evaluate(model, tensors, indices, labels, action_masks, stats, device):
    state, scan, end_contact, target_contact, duration, touchdown = tensors
    sm, ss, hm, hs, cm, cs, dm, ds = stats
    idx = torch.as_tensor(indices, dtype=torch.long, device=device)
    output = model(
        (state[idx] - sm.to(device)) / ss.to(device),
        (scan[idx] - hm.to(device)) / hs.to(device),
    )
    action = output[0].argmax(-1).cpu()
    end = output[1].sigmoid().cpu() >= 0.5
    point = output[2].cpu() * cs.cpu() + cm.cpu()
    point = torch.from_numpy(conform_contact_targets_to_scan(
        point.numpy(), touchdown[idx].cpu().numpy(), scan[idx].cpu().numpy()
    ))
    seconds = torch.exp(output[3].cpu() * ds.cpu() + dm.cpu())
    active = touchdown[idx].cpu() > 0.5
    error = torch.linalg.vector_norm(point - target_contact[idx].cpu(), dim=-1)[active].numpy() * 100.0
    return {
        "samples": int(len(indices)),
        "action_exact_accuracy": float((action == labels[idx].cpu()).float().mean()),
        "touchdown_exact_accuracy": float(
            (action_masks[action] == touchdown[idx].cpu().bool()).all(dim=-1).float().mean()
        ),
        "end_contact_exact_accuracy": float((end == end_contact[idx].cpu().bool()).all(dim=-1).float().mean()),
        "target_contact_error_cm": {
            "mean": float(error.mean()), "p95": float(np.quantile(error, 0.95)), "max": float(error.max())
        },
        "duration_error_frames_at_50hz": float((seconds - duration[idx].cpu()).abs().mean() * 50.0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--blocks", type=int, default=4)
    parser.add_argument("--action-embedding-dim", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--boundary-cache", type=Path, action="append")
    parser.add_argument("--seed", type=int, default=20260825)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device(args.device)
    data, samples, event_summary, state_np, scan_np = arrays(args.manifest)
    splits = {
        name: np.asarray([i for i, s in enumerate(samples) if split_name(s.height) == name], dtype=np.int64)
        for name in ("train_height_095_100_105", "validation_height_090", "test_height_110")
    }
    train = splits["train_height_095_100_105"]
    manifest_record = json.loads(args.manifest.read_text())
    cache_data = None
    if args.boundary_cache:
        cache_parts=[]
        required=("state","height_scan","touchdown","end_contact","target_contact","duration")
        geometry=("box_origin","box_basis","box_edge_start","box_edge_inward","box_height")
        for cache_path in args.boundary_cache:
            with np.load(cache_path, allow_pickle=False) as cache:
                missing=[key for key in required if key not in cache]
                if missing:
                    raise ValueError(f"boundary cache {cache_path} missing {missing}")
                if "robot_asset_id" in cache and str(cache["robot_asset_id"])!=manifest_record["robot_asset_id"]:
                    raise ValueError(f"robot asset id mismatch in {cache_path}")
                if "robot_asset_sha256" in cache and str(cache["robot_asset_sha256"])!=manifest_record["robot_asset_sha256"]:
                    raise ValueError(f"robot asset hash mismatch in {cache_path}")
                keys=required+tuple(key for key in geometry if key in cache)
                cache_parts.append({key:np.asarray(cache[key]) for key in keys})
        shared=set.intersection(*(set(part) for part in cache_parts))
        cache_data={key:np.concatenate([part[key] for part in cache_parts],axis=0) for key in shared}
        if all(key in cache_data for key in geometry):
            cache_data["height_scan"] = scans_from_local_box(
                cache_data["box_origin"], cache_data["box_basis"], cache_data["box_edge_start"],
                cache_data["box_edge_inward"], cache_data["box_height"],
            )
        if cache_data["height_scan"].shape[1] != scan_np.shape[1]:
            raise ValueError(
                f"boundary scan dim {cache_data['height_scan'].shape[1]} != training scan dim {scan_np.shape[1]}"
            )
    vocabulary_touchdown = np.asarray(data["touchdown"], dtype=bool)
    vocabulary_end_contact = np.asarray(data["end_contact"], dtype=bool)
    if cache_data is not None:
        vocabulary_touchdown = np.concatenate((vocabulary_touchdown, cache_data["touchdown"].astype(bool)))
        vocabulary_end_contact = np.concatenate((vocabulary_end_contact, cache_data["end_contact"].astype(bool)))
    action_masks_np, end_contact_masks_np = transition_vocabulary(
        vocabulary_touchdown, vocabulary_end_contact
    )
    labels_np = transition_labels(
        data["touchdown"], data["end_contact"], action_masks_np, end_contact_masks_np
    )
    train_state = state_np[train]
    train_scan = scan_np[train]
    train_touchdown = data["touchdown"][train]
    train_end_contact = data["end_contact"][train]
    train_target_contact = data["target_contacts"][train]
    train_duration = data["duration"][train]
    train_labels = labels_np[train]
    cache_samples = 0
    if cache_data is not None:
        cache_touchdown = np.asarray(cache_data["touchdown"], dtype=np.float32)
        cache_end_contact = np.asarray(cache_data["end_contact"], dtype=np.float32)
        cache_labels = transition_labels(
            cache_touchdown, cache_end_contact, action_masks_np, end_contact_masks_np
        )
        train_state = np.concatenate((train_state, np.asarray(cache_data["state"], dtype=np.float32)))
        train_scan = np.concatenate((train_scan, np.asarray(cache_data["height_scan"], dtype=np.float32)))
        train_touchdown = np.concatenate((train_touchdown, cache_touchdown))
        train_end_contact = np.concatenate((train_end_contact, cache_end_contact))
        train_target_contact = np.concatenate((train_target_contact, np.asarray(cache_data["target_contact"], dtype=np.float32)))
        train_duration = np.concatenate((train_duration, np.asarray(cache_data["duration"], dtype=np.float32)))
        train_labels = np.concatenate((train_labels, cache_labels))
        cache_samples = len(cache_labels)
    train_target_contact = conform_contact_targets_to_scan(
        train_target_contact, train_touchdown, train_scan
    )
    state_mean = train_state.mean(0).astype(np.float32)
    state_std = np.maximum(train_state.std(0), 1.0e-5).astype(np.float32)
    scan_mean = train_scan.mean(0).astype(np.float32)
    scan_std = np.maximum(train_scan.std(0), 1.0e-3).astype(np.float32)
    contact_mean, contact_std = contact_stats(
        train_target_contact, train_touchdown, np.arange(len(train_touchdown), dtype=np.int64)
    )
    duration_mean = float(np.log(train_duration).mean())
    duration_std = float(max(np.log(train_duration).std(), 1.0e-3))

    state = torch.from_numpy(state_np).to(device); scan = torch.from_numpy(scan_np).to(device)
    end_contact = torch.from_numpy(data["end_contact"]).to(device)
    canonical_target_contact = conform_contact_targets_to_scan(
        data["target_contacts"], data["touchdown"], scan_np
    )
    target_contact = torch.from_numpy(canonical_target_contact).to(device)
    duration = torch.from_numpy(data["duration"]).to(device)
    touchdown = torch.from_numpy(data["touchdown"]).to(device)
    labels = torch.from_numpy(labels_np).to(device); action_masks = torch.from_numpy(action_masks_np)
    dataset = TensorDataset(
        torch.from_numpy((train_state-state_mean)/state_std).float(),
        torch.from_numpy((train_scan-scan_mean)/scan_std).float(),
        torch.from_numpy(train_labels).long(), torch.from_numpy(train_end_contact).float(),
        torch.from_numpy(train_target_contact).float(), torch.from_numpy(train_touchdown).float(),
        torch.from_numpy(train_duration).float(),
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=False)
    model = ScanContactSelector(
        state_np.shape[1], len(action_masks_np), args.width, args.blocks, args.action_embedding_dim,
        transition_end_contact_masks=torch.from_numpy(end_contact_masks_np),
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-4)
    sm=torch.from_numpy(state_mean).to(device); ss=torch.from_numpy(state_std).to(device)
    hm=torch.from_numpy(scan_mean).to(device); hs=torch.from_numpy(scan_std).to(device)
    cm=torch.from_numpy(contact_mean).to(device); cs=torch.from_numpy(contact_std).to(device)
    dm=torch.tensor(duration_mean,device=device); ds=torch.tensor(duration_std,device=device)
    history=[]; best=None; best_score=math.inf
    for epoch in range(1,args.epochs+1):
        model.train(); losses=[]
        for state_b,scan_b,label_b,end_b,target_b,touchdown_b,duration_b in loader:
            state_b=state_b.to(device); scan_b=scan_b.to(device); label_b=label_b.to(device)
            end_b=end_b.to(device); target_b=target_b.to(device); touchdown_b=touchdown_b.to(device); duration_b=duration_b.to(device)
            output=model(state_b,scan_b,label_b)
            active=touchdown_b>0.5
            point_target=(target_b-cm)/cs
            point_loss=(output[2][active]-point_target[active]).square().mean()
            loss=(
                F.cross_entropy(output[0],label_b)
                +F.binary_cross_entropy_with_logits(output[1],end_b)
                +2.0*point_loss
                +((output[3]-(torch.log(duration_b)-dm)/ds).square().mean())
            )
            optimizer.zero_grad(set_to_none=True); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),2.0); optimizer.step(); losses.append(float(loss.detach()))
        if epoch==1 or epoch%25==0 or epoch==args.epochs:
            model.eval()
            stat_tensors=(state,scan,end_contact,target_contact,duration,touchdown)
            stat_values=(
                torch.from_numpy(state_mean),torch.from_numpy(state_std),torch.from_numpy(scan_mean),torch.from_numpy(scan_std),
                torch.from_numpy(contact_mean),torch.from_numpy(contact_std),torch.tensor(duration_mean),torch.tensor(duration_std),
            )
            metric=evaluate(model,stat_tensors,splits["validation_height_090"],labels,action_masks,stat_values,device)
            record={"epoch":epoch,"loss":float(np.mean(losses)),"validation":metric}; history.append(record); print(json.dumps(record))
            score=metric["target_contact_error_cm"]["mean"]+10.0*(1.0-metric["action_exact_accuracy"])
            if score<best_score: best_score=score; best=copy.deepcopy(model.state_dict())
    assert best is not None; model.load_state_dict(best); model.eval()
    stat_tensors=(state,scan,end_contact,target_contact,duration,touchdown)
    stat_values=(
        torch.from_numpy(state_mean),torch.from_numpy(state_std),torch.from_numpy(scan_mean),torch.from_numpy(scan_std),
        torch.from_numpy(contact_mean),torch.from_numpy(contact_std),torch.tensor(duration_mean),torch.tensor(duration_std),
    )
    metrics={k:evaluate(model,stat_tensors,v,labels,action_masks,stat_values,device) for k,v in splits.items()}
    manifest=manifest_record
    checkpoint={
        "schema":"climb00_scan_contact_selector_v1","model":best,"state_dim":state_np.shape[1],
        "scan_grid":torch.from_numpy(local_scan_grid()),"scan_shape":(SCAN_ROWS,SCAN_COLS),"action_masks":action_masks,
        "end_contact_masks":torch.from_numpy(end_contact_masks_np),
        "state_mean":torch.from_numpy(state_mean),"state_std":torch.from_numpy(state_std),
        "scan_mean":torch.from_numpy(scan_mean),"scan_std":torch.from_numpy(scan_std),
        "contact_mean":torch.from_numpy(contact_mean),"contact_std":torch.from_numpy(contact_std),
        "duration_mean":duration_mean,"duration_std":duration_std,
        "scan_clip_m":SCAN_CLIP_M,
        "contact_surface_parameterization":"scan_surface_v1",
        "parts":PARTS,"config":vars(args),
        "robot_asset_id":manifest["robot_asset_id"],"robot_asset_sha256":manifest["robot_asset_sha256"],
    }
    torch.save(checkpoint,args.output/"model.pt")
    report={
        "schema":"climb00_scan_contact_selector_report_v1","event_dataset":event_summary,
        "splits":{k:int(len(v)) for k,v in splits.items()},"boundary_cache_samples":cache_samples,
        "metrics":metrics,"history":history,
        "model_contract":{
            "input":"current contact bits + torso-yaw 7-body sparse pose + forward-local 20x17 terrain height scan",
            "excluded":"task/edit parameters, surface IDs/UV, polygon corners, ground height, future pose, previous code",
            "output":"observed touchdown topology + end contacts + scan-surface-constrained torso-yaw contact xyz + duration",
        },
    }
    (args.output/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(metrics,indent=2))


if __name__ == "__main__": main()
