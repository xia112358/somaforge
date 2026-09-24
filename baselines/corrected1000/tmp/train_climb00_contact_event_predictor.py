#!/usr/bin/env python3
"""Train a contact-only next-event predictor for the climb00 trajectory family.

The prediction target contains no future body/link pose.  It predicts which
contact parts touch down, the resulting contact mask, the contacted surface,
surface coordinates of each new contact, and event duration.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from build_g1_complete_limb_actions import debounce_binary_states
from eval_next_keyframe_with_infiller import collapse_contact
from train_next_contact_keyframe_predictor import (
    KEY_BODIES,
    grouped_touchdowns,
    keyframe_features,
    quat_wxyz_to_matrix,
    source_contact_schedule,
    task_condition,
    yaw_from_wxyz,
    yaw_inverse_matrix,
)


ROOT = Path.cwd().resolve()
DEFAULT_MANIFEST = ROOT / "tmp/climb00_continuous_coverage/training_manifest_207.json"
DEFAULT_OUTPUT = ROOT / "tmp/climb00_contact_event_v1"
MINIMUM_EVENT_FRAMES = 6
PARTS = ("LF", "RF", "LH", "RH", "LK", "RK")
PART_BODIES = (
    ("left_heel", "left_toe"),
    ("right_heel", "right_toe"),
    ("left_hand",),
    ("right_hand",),
    ("left_knee",),
    ("right_knee",),
)
SURFACES = ("ground", "top")


@dataclass
class ContactEventSample:
    motion_id: int
    source: str
    height: float
    current_frame: int
    target_frame: int
    x: np.ndarray
    touchdown: np.ndarray
    end_contact: np.ndarray
    surface_class: np.ndarray
    surface_uv: np.ndarray
    duration_s: float


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def surface_class(surface_id: str | None) -> int:
    if surface_id is None:
        return -1
    return 0 if surface_id == "terrain_ground_z0" else 1


def surface_catalog(path: Path) -> dict[int, dict]:
    from somaforge_core.contact_face_selection import ground_top_catalog
    return ground_top_catalog(read_jsonl(path))


def resolve_source_layer(plan: dict) -> Path:
    relative = str(plan["source_contact_layer"]).strip("/")
    return ROOT / "runtime/current/motion_edit/data/layers" / relative


def transformed_anchors(plan: dict) -> tuple[list[dict], dict[int, dict]]:
    layer = resolve_source_layer(plan)
    anchors_path = layer / "anchors/climb_00.jsonl"
    anchors = read_jsonl(anchors_path)
    target_surfaces_path = Path(plan["metadata"]["target_surface_catalog"])
    catalog = surface_catalog(target_surfaces_path)
    edit_by_anchor = {
        str(edit["anchor_id"]): edit
        for edit in plan.get("edits", [])
        if edit.get("edit_type") == "move_contact_anchor"
    }
    top_transform = next(iter(plan.get("surface_transforms", [])), None)
    source_top_id = None if top_transform is None else str(top_transform["source_surface"]["surface_id"])

    output = []
    for source in anchors:
        anchor = copy.deepcopy(source)
        edit = edit_by_anchor.get(str(anchor["anchor_id"]))
        if edit is not None:
            anchor["surface_id"] = str(edit["surface_id"])
            anchor["surface_coordinates"] = dict(edit["surface_coordinates_after"])
            anchor["world_position"] = list(edit["new_world_position"])
        if source_top_id is not None and str(anchor.get("surface_id")) == source_top_id:
            target = catalog[1]
            uv = anchor["surface_coordinates"]
            u, v = float(uv["u"]), float(uv["v"])
            origin = np.asarray(target["origin"], dtype=np.float64)
            tangent_u = np.asarray(target["tangent_u"], dtype=np.float64)
            tangent_v = np.asarray(target["tangent_v"], dtype=np.float64)
            anchor["surface_id"] = str(target["surface_id"])
            anchor["world_position"] = (origin + u * tangent_u + v * tangent_v).tolist()
        output.append(anchor)
    return output, catalog


def anchor_for(anchors: list[dict], body: str, frame: int) -> dict | None:
    candidates = [
        anchor for anchor in anchors
        if str(anchor.get("body")) == body
        and int(anchor["start_frame"]) <= frame <= int(anchor["end_frame"])
    ]
    if not candidates:
        candidates = [
            anchor for anchor in anchors
            if str(anchor.get("body")) == body
            and abs(int(anchor["start_frame"]) - frame) <= 4
        ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda anchor: (
            abs(int(anchor["start_frame"]) - frame),
            int(anchor["end_frame"]) - int(anchor["start_frame"]),
        ),
    )


def contact_descriptor(
    anchors: list[dict], contact: np.ndarray, frame: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    surface = np.full(len(PARTS), -1, dtype=np.int64)
    uv = np.zeros((len(PARTS), 2), dtype=np.float32)
    valid = np.zeros(len(PARTS), dtype=np.float32)
    unresolved = 0
    for part, bodies in enumerate(PART_BODIES):
        if not bool(contact[part]):
            continue
        selected = [anchor_for(anchors, body, frame) for body in bodies]
        selected = [anchor for anchor in selected if anchor is not None]
        if not selected:
            unresolved += 1
            continue
        classes = np.asarray([surface_class(str(anchor.get("surface_id"))) for anchor in selected])
        chosen = int(np.bincount(classes, minlength=len(SURFACES)).argmax())
        coordinates = [
            anchor.get("surface_coordinates") or {}
            for anchor, class_id in zip(selected, classes, strict=True)
            if int(class_id) == chosen
        ]
        coordinates = [value for value in coordinates if "u" in value and "v" in value]
        if not coordinates:
            unresolved += 1
            continue
        surface[part] = chosen
        uv[part] = np.asarray(
            [[float(value["u"]), float(value["v"])] for value in coordinates], dtype=np.float32
        ).mean(axis=0)
        valid[part] = 1.0
    return surface, uv, valid, unresolved


def load_state_cache(path: Path | None, manifest_path=None) -> dict[tuple[int, int], np.ndarray]:
    if path is None:
        return {}
    with np.load(path, allow_pickle=False) as loaded:
        from somaforge_core.contact_dataset import validate_contact_cache
        if manifest_path is None:
            raise ValueError('Boundary cache requires its current contact manifest')
        validate_contact_cache(loaded, manifest_path)
        motion_ids = np.asarray(loaded["motion_ids"], dtype=np.int64)
        frames = np.asarray(loaded["frames"], dtype=np.int64)
        features = np.asarray(loaded["pose_features"], dtype=np.float32)
    return {
        (int(motion_id), int(frame)): feature
        for motion_id, frame, feature in zip(motion_ids, frames, features, strict=True)
    }


def build_samples(
    manifest_path: Path, state_cache_path: Path | None = None,
    *, prepared_motions: dict | None = None,
) -> tuple[list[ContactEventSample], dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get('training_ready') is False:
        raise ValueError('Contact manifest is inspection-only; resolve its pending acceptance checks before training')
    state_cache = load_state_cache(state_cache_path, manifest_path)
    samples: list[ContactEventSample] = []
    unresolved_current = 0
    unresolved_target = 0
    touchdown_without_anchor = 0
    cached_pose_inputs = 0
    event_counts = []
    for motion_id, entry in enumerate(manifest["motion_files"]):
        path = Path(entry["motion_file"])
        plan = json.loads(Path(entry["edit_plan_file"]).read_text(encoding="utf-8"))
        from somaforge_core.newton_contact_data import load_entry_contacts, touchdown_events
        verified = load_entry_contacts(entry)
        catalog = surface_catalog(Path(plan['metadata']['target_surface_catalog']))
        def descriptor(mask, frame):
            surface = verified['contact_surface'][frame].copy()
            surface[~mask] = -1
            uv = np.zeros((6, 2), np.float32)
            for p in np.flatnonzero(mask):
                if int(surface[p]) not in catalog:
                    raise ValueError('Actual Newton surface is outside predictor vocabulary; do not map side contact to top')
                record = catalog[int(surface[p])]
                delta = verified['contact_position_w'][frame, p]-np.asarray(record['origin'])
                tangents = np.stack((record['tangent_u'], record['tangent_v']), axis=1)
                uv[p] = np.linalg.lstsq(tangents, delta, rcond=None)[0]
            return surface, uv, mask.astype(np.float32), 0
        with np.load(path, allow_pickle=False) as motion:
            frame_count = len(motion["body_pos_w"])
            fps = float(motion["fps"])
            body_names = motion["body_names"].astype(str).tolist()
            body_indices = np.asarray([body_names.index(name) for name in KEY_BODIES], dtype=np.int64)
            body_positions = np.asarray(motion["body_pos_w"], dtype=np.float64)
            body_quaternions = np.asarray(motion["body_quat_w"], dtype=np.float64)
            body_rotations = quat_wxyz_to_matrix(body_quaternions)
        raw_contact = verified['contact_part_mask']
        if len(raw_contact) != frame_count:
            raise ValueError('Verified contact and body pose timelines differ')
        if prepared_motions is not None:
            # Scope is one build, never a process-global memo of mutable files.
            prepared_motions[motion_id] = dict(
                newton={k:verified[k] for k in ('contact_part_mask','contact_surface','contact_position_w')},
                body_names=tuple(KEY_BODIES),
                position=body_positions[:,body_indices],
                quaternion=body_quaternions[:,body_indices])
        contact = collapse_contact(raw_contact).astype(bool)
        segment_starts = {}
        if entry.get('event_segments_file'):
            from somaforge_core.contact_events import load_segment_rows
            rows = load_segment_rows(entry, verified, fps)
            events = []
            for segment in rows:
                # A certified settled-pose transition is part of the action
                # chain even though it establishes no new contact.  Only
                # explicitly excluded holds/tails are omitted.
                include = segment.get('include_for_infiller')
                if include is False or (include is None and not segment['touchdown_events']):
                    continue
                bits = np.zeros(6, bool)
                for event in segment['touchdown_events']: bits[event['part_index']] = True
                end = segment['end_frame']
                events.append((end, bits))
                segment_starts[end] = segment['start_frame']
        else:
            events = touchdown_events(contact, surfaces=verified['contact_surface'])
        condition = task_condition(entry)
        current_frame = 0
        count = 0
        for target_frame, touchdown in events:
            current_frame = segment_starts.get(target_frame, current_frame)
            # Five-frame events in the source contact layer are sensor/contact
            # chatter, not useful limb cycles.  Keeping the frame-5 false
            # touchdown makes the closed-loop selector learn a 0.1 s
            # self-transition before the actual first step.
            # Certified events have already passed the shared temporal policy;
            # never silently discard their short intervals in a second layer.
            if not entry.get('event_segments_file') and target_frame - current_frame < MINIMUM_EVENT_FRAMES:
                continue
            current_surface, current_uv, current_valid, missed_current = descriptor(contact[current_frame], current_frame)
            target_surface, target_uv, target_valid, missed_target = descriptor(contact[target_frame], target_frame)
            end_valid = contact[target_frame].astype(np.float32)
            unresolved_current += missed_current
            unresolved_target += missed_target
            touchdown_without_anchor += int(np.count_nonzero(touchdown & ~target_valid.astype(bool)))
            if np.any(touchdown & ~target_valid.astype(bool)):
                continue
            current_surface_one_hot = np.zeros((len(PARTS), len(SURFACES)), dtype=np.float32)
            for part in range(len(PARTS)):
                if current_valid[part] and current_surface[part] >= 0:
                    current_surface_one_hot[part, current_surface[part]] = 1.0
            # Contact topology alone is not Markov: the same support set can
            # occur at different whole-body phases.  Current sparse pose is an
            # observation only; the prediction target remains contact-only.
            origin = body_positions[current_frame, body_indices[0]].copy()
            yaw_inverse = yaw_inverse_matrix(yaw_from_wxyz(body_quaternions[current_frame, body_indices[0]]))
            cached_pose = state_cache.get((motion_id, current_frame))
            if cached_pose is None:
                current_position, current_rotation = keyframe_features(
                    body_positions, body_rotations, current_frame, body_indices, origin, yaw_inverse
                )
                current_pose_feature = np.concatenate((current_position.reshape(-1), current_rotation.reshape(-1)))
            else:
                if cached_pose.shape != (63,):
                    raise ValueError(f"cached pose {(motion_id, current_frame)} has shape {cached_pose.shape}")
                current_pose_feature = cached_pose
                cached_pose_inputs += 1
            x = np.concatenate(
                (
                    contact[current_frame].astype(np.float32),
                    current_surface_one_hot.reshape(-1),
                    current_uv.reshape(-1),
                    condition,
                    current_pose_feature,
                )
            ).astype(np.float32)
            samples.append(
                ContactEventSample(
                    motion_id=motion_id,
                    source=str(path),
                    height=float(condition[0]),
                    current_frame=current_frame,
                    target_frame=int(target_frame),
                    x=x,
                    touchdown=touchdown.astype(np.float32),
                    end_contact=contact[target_frame].astype(np.float32),
                    surface_class=target_surface,
                    surface_uv=target_uv,
                    duration_s=float((target_frame - current_frame) / fps),
                )
            )
            current_frame = int(target_frame)
            count += 1
        event_counts.append(count)
    if not samples:
        raise RuntimeError("no contact events")
    return samples, {
        "motions": len(manifest["motion_files"]),
        "samples": len(samples),
        "events_per_motion": {
            "min": int(min(event_counts)),
            "mean": float(np.mean(event_counts)),
            "max": int(max(event_counts)),
        },
        "minimum_event_frames": MINIMUM_EVENT_FRAMES,
        "unresolved_current_active_contacts": unresolved_current,
        "unresolved_target_active_contacts": unresolved_target,
        "touchdown_parts_without_anchor": touchdown_without_anchor,
        "state_cache": None if state_cache_path is None else str(state_cache_path.resolve()),
        "cached_pose_inputs": cached_pose_inputs,
        "input_contract": (
            "current contact bits + current contact surface/uv + task condition + "
            "current torso-yaw-frame 7-body sparse pose; current pose is observation only"
        ),
        "target_contract": "touchdown/end-contact bits + target surface/uv + duration; no future body pose",
    }


class ResidualBlock(nn.Module):
    def __init__(self, width: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(width), nn.Linear(width, 2 * width), nn.SiLU(), nn.Linear(2 * width, width)
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return value + self.net(value)


class ContactEventPredictor(nn.Module):
    def __init__(self, input_dim: int, width: int = 256, blocks: int = 4):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(input_dim, width), nn.SiLU(),
            *(ResidualBlock(width) for _ in range(blocks)), nn.LayerNorm(width),
        )
        self.touchdown = nn.Linear(width, len(PARTS))
        self.end_contact = nn.Linear(width, len(PARTS))
        self.surface = nn.Linear(width, len(PARTS) * len(SURFACES))
        self.uv = nn.Linear(width, len(PARTS) * 2)
        self.duration = nn.Linear(width, 1)

    def forward(self, value: torch.Tensor) -> tuple[torch.Tensor, ...]:
        hidden = self.trunk(value)
        return (
            self.touchdown(hidden),
            self.end_contact(hidden),
            self.surface(hidden).reshape(-1, len(PARTS), len(SURFACES)),
            self.uv(hidden).reshape(-1, len(PARTS), 2),
            self.duration(hidden).squeeze(-1),
        )


class HierarchicalContactEventPredictor(nn.Module):
    """Select an observed discrete action, then predict parameters conditioned on it."""

    def __init__(
        self, input_dim: int, action_count: int, width: int = 256, blocks: int = 4,
        action_embedding_dim: int = 64,
    ):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(input_dim, width), nn.SiLU(),
            *(ResidualBlock(width) for _ in range(blocks)), nn.LayerNorm(width),
        )
        self.action = nn.Linear(width, action_count)
        self.action_embedding = nn.Embedding(action_count, action_embedding_dim)
        self.parameter_trunk = nn.Sequential(
            nn.Linear(width + action_embedding_dim, width), nn.SiLU(),
            ResidualBlock(width), nn.LayerNorm(width),
        )
        self.end_contact = nn.Linear(width, len(PARTS))
        self.surface = nn.Linear(width, len(PARTS) * len(SURFACES))
        self.uv = nn.Linear(width, len(PARTS) * 2)
        self.duration = nn.Linear(width, 1)

    def encode(self, value: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = self.trunk(value)
        return hidden, self.action(hidden)

    def decode_parameters(
        self, hidden: torch.Tensor, action_index: torch.Tensor,
    ) -> tuple[torch.Tensor, ...]:
        conditioned = self.parameter_trunk(
            torch.cat((hidden, self.action_embedding(action_index)), dim=-1)
        )
        return (
            self.end_contact(conditioned),
            self.surface(conditioned).reshape(-1, len(PARTS), len(SURFACES)),
            self.uv(conditioned).reshape(-1, len(PARTS), 2),
            self.duration(conditioned).squeeze(-1),
        )

    def forward(
        self, value: torch.Tensor, action_index: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, ...]:
        hidden, action_logits = self.encode(value)
        if action_index is None:
            action_index = action_logits.argmax(dim=-1)
        return (action_logits, *self.decode_parameters(hidden, action_index))


def decode_nonempty_touchdown(logits: torch.Tensor) -> torch.Tensor:
    """MAP decode over all 2^N-1 non-empty touchdown subsets."""
    selected = logits >= 0.0
    empty = ~selected.any(dim=-1)
    if empty.any():
        rows = torch.arange(len(selected), device=selected.device)[empty]
        selected[rows, logits[empty].argmax(dim=-1)] = True
    return selected


def zero_truncated_multilabel_nll(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Independent Bernoulli NLL conditioned on at least one active bit."""
    if not bool((target.sum(dim=-1) > 0.0).all()):
        raise ValueError("zero-truncated touchdown targets must be non-empty")
    bernoulli_nll = F.binary_cross_entropy_with_logits(logits, target, reduction="none").sum(dim=-1)
    log_probability_empty = F.logsigmoid(-logits).sum(dim=-1).clamp_max(-1.0e-7)
    log_probability_nonempty = torch.log(-torch.expm1(log_probability_empty))
    return (bernoulli_nll + log_probability_nonempty).mean()


def split_name(height: float) -> str:
    if height >= 1.075:
        return "test_height_110"
    if height <= 0.925:
        return "validation_height_090"
    return "train_height_095_100_105"


def normalize(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = values.mean(axis=0).astype(np.float32)
    std = values.std(axis=0).astype(np.float32)
    std = np.where(std < 1.0e-5, 1.0, std).astype(np.float32)
    return mean, std


def active_uv_stats(samples: list[ContactEventSample], indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = np.zeros((len(PARTS), 2), dtype=np.float32)
    std = np.ones((len(PARTS), 2), dtype=np.float32)
    for part in range(len(PARTS)):
        values = np.asarray([
            samples[int(i)].surface_uv[part]
            for i in indices if samples[int(i)].surface_class[part] >= 0
        ], dtype=np.float32)
        if len(values):
            mean[part] = values.mean(axis=0)
            std[part] = np.maximum(values.std(axis=0), 1.0e-3)
    return mean, std


def batch_arrays(samples: list[ContactEventSample], indices: np.ndarray) -> tuple[np.ndarray, ...]:
    return (
        np.stack([samples[int(i)].x for i in indices]),
        np.stack([samples[int(i)].touchdown for i in indices]),
        np.stack([samples[int(i)].end_contact for i in indices]),
        np.stack([samples[int(i)].surface_class for i in indices]),
        np.stack([samples[int(i)].surface_uv for i in indices]),
        np.asarray([samples[int(i)].duration_s for i in indices], dtype=np.float32),
    )


def observed_action_vocabulary(samples: list[ContactEventSample]) -> np.ndarray:
    """Return every certified event action, including settled-pose waypoints.

    An all-zero touchdown mask is not a no-op: its end-contact, duration and
    pose-conditioned successor describe a posture phase boundary without a
    newly established contact.
    """
    masks = np.unique(np.asarray([sample.touchdown for sample in samples], dtype=bool), axis=0)
    if not len(masks):
        raise ValueError("observed action vocabulary is empty")
    return masks


def action_labels(samples: list[ContactEventSample], vocabulary: np.ndarray) -> np.ndarray:
    lookup = {tuple(mask.tolist()): index for index, mask in enumerate(vocabulary)}
    return np.asarray([lookup[tuple(sample.touchdown.astype(bool).tolist())] for sample in samples], dtype=np.int64)


@torch.no_grad()
def evaluate_hierarchical(
    model: HierarchicalContactEventPredictor,
    samples: list[ContactEventSample],
    indices: np.ndarray,
    labels: np.ndarray,
    vocabulary: np.ndarray,
    x_mean: np.ndarray,
    x_std: np.ndarray,
    uv_mean: np.ndarray,
    uv_std: np.ndarray,
    duration_mean: float,
    duration_std: float,
    device: torch.device,
) -> dict:
    x, touchdown, end_contact, surface, uv, duration = batch_arrays(samples, indices)
    outputs = model(torch.as_tensor((x - x_mean) / x_std, dtype=torch.float32, device=device))
    action_p = outputs[0].argmax(dim=-1).cpu().numpy()
    touchdown_p = vocabulary[action_p]
    end_p = outputs[1].sigmoid().cpu().numpy() >= 0.5
    surface_p = outputs[2].argmax(dim=-1).cpu().numpy()
    uv_p = outputs[3].cpu().numpy() * uv_std[None] + uv_mean[None]
    duration_p = np.exp(outputs[4].cpu().numpy() * duration_std + duration_mean)
    active = surface >= 0
    uv_error_cm = np.linalg.norm(uv_p - uv, axis=-1)[active] * 100.0

    def summary(values: np.ndarray) -> dict[str, float]:
        values = np.asarray(values, dtype=np.float64)
        return {
            "mean": float(values.mean()),
            "p95": float(np.quantile(values, 0.95)),
            "max": float(values.max()),
        }

    return {
        "samples": int(len(indices)),
        "action_exact_accuracy": float((action_p == labels[indices]).mean()),
        "touchdown_exact_accuracy": float(np.all(touchdown_p == touchdown.astype(bool), axis=1).mean()),
        "decoded_empty_touchdown_fraction": float((~touchdown_p.any(axis=-1)).mean()),
        "end_contact_exact_accuracy": float(np.all(end_p == end_contact.astype(bool), axis=1).mean()),
        "active_surface_accuracy": float((surface_p[active] == surface[active]).mean()),
        "active_surface_uv_error_cm": summary(uv_error_cm),
        "duration_error_frames_at_50hz": summary(np.abs(duration_p - duration) * 50.0),
    }


@torch.no_grad()
def evaluate(
    model: ContactEventPredictor,
    samples: list[ContactEventSample],
    indices: np.ndarray,
    x_mean: np.ndarray,
    x_std: np.ndarray,
    uv_mean: np.ndarray,
    uv_std: np.ndarray,
    duration_mean: float,
    duration_std: float,
    device: torch.device,
) -> dict:
    x, touchdown, end_contact, surface, uv, duration = batch_arrays(samples, indices)
    outputs = model(torch.as_tensor((x - x_mean) / x_std, dtype=torch.float32, device=device))
    raw_touchdown_p = outputs[0] >= 0.0
    touchdown_p = decode_nonempty_touchdown(outputs[0]).cpu().numpy()
    end_p = (outputs[1].sigmoid().cpu().numpy() >= 0.5)
    surface_p = outputs[2].argmax(dim=-1).cpu().numpy()
    uv_p = outputs[3].cpu().numpy() * uv_std[None] + uv_mean[None]
    duration_p = np.exp(outputs[4].cpu().numpy() * duration_std + duration_mean)
    active = surface >= 0
    uv_error_cm = np.linalg.norm(uv_p - uv, axis=-1)[active] * 100.0
    surface_correct = surface_p[active] == surface[active]
    tp = np.count_nonzero(touchdown_p & touchdown.astype(bool))
    fp = np.count_nonzero(touchdown_p & ~touchdown.astype(bool))
    fn = np.count_nonzero(~touchdown_p & touchdown.astype(bool))

    def summary(values: np.ndarray) -> dict[str, float]:
        values = np.asarray(values, dtype=np.float64)
        return {
            "mean": float(values.mean()),
            "p95": float(np.quantile(values, 0.95)),
            "max": float(values.max()),
        }

    return {
        "samples": int(len(indices)),
        "touchdown_exact_accuracy": float(np.all(touchdown_p == touchdown.astype(bool), axis=1).mean()),
        "raw_unconstrained_empty_touchdown_fraction": float((~raw_touchdown_p.any(dim=-1)).float().mean().cpu()),
        "decoded_empty_touchdown_fraction": float((~touchdown_p.any(axis=-1)).mean()),
        "touchdown_micro_f1": float(2 * tp / max(2 * tp + fp + fn, 1)),
        "end_contact_exact_accuracy": float(np.all(end_p == end_contact.astype(bool), axis=1).mean()),
        "active_surface_accuracy": float(surface_correct.mean()),
        "active_surface_uv_error_cm": summary(uv_error_cm),
        "duration_error_frames_at_50hz": summary(np.abs(duration_p - duration) * 50.0),
        "decoded_contact_surface_distance_m": 0.0,
        "decoded_contact_surface_distance_note": "surface point is reconstructed from predicted surface class and uv by construction",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--state-cache", type=Path)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--blocks", type=int, default=4)
    parser.add_argument("--action-embedding-dim", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--seed", type=int, default=20260824)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device(args.device)

    samples, dataset_summary = build_samples(args.manifest, args.state_cache)
    splits = {
        name: np.asarray([i for i, sample in enumerate(samples) if split_name(sample.height) == name], dtype=np.int64)
        for name in ("train_height_095_100_105", "validation_height_090", "test_height_110")
    }
    if any(len(value) == 0 for value in splits.values()):
        raise RuntimeError({key: len(value) for key, value in splits.items()})
    train = splits["train_height_095_100_105"]
    action_vocabulary = observed_action_vocabulary(samples)
    labels = action_labels(samples, action_vocabulary)
    train_arrays = batch_arrays(samples, train)
    x_mean, x_std = normalize(train_arrays[0])
    uv_mean, uv_std = active_uv_stats(samples, train)
    train_log_duration = np.log(np.maximum(train_arrays[5], 1.0e-4))
    duration_mean = float(train_log_duration.mean())
    duration_std = float(max(train_log_duration.std(), 1.0e-3))
    uv_normalized = (train_arrays[4] - uv_mean[None]) / uv_std[None]
    surface_target = train_arrays[3].copy()
    active = surface_target >= 0

    loader = DataLoader(
        TensorDataset(
            torch.from_numpy((train_arrays[0] - x_mean) / x_std).float(),
            torch.from_numpy(labels[train]).long(),
            torch.from_numpy(train_arrays[2]).float(),
            torch.from_numpy(surface_target).long(),
            torch.from_numpy(uv_normalized).float(),
            torch.from_numpy(active),
            torch.from_numpy((train_log_duration - duration_mean) / duration_std).float(),
        ),
        batch_size=args.batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(args.seed),
    )
    model = HierarchicalContactEventPredictor(
        train_arrays[0].shape[1], len(action_vocabulary), args.width, args.blocks,
        args.action_embedding_dim,
    ).to(device)
    action_counts = np.bincount(labels[train], minlength=len(action_vocabulary)).astype(np.float32)
    action_weights = np.sqrt(action_counts.sum() / np.maximum(action_counts, 1.0))
    action_weights /= action_weights.mean()
    action_weights_t = torch.from_numpy(action_weights).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-4)
    best_state = None
    best_score = math.inf
    history = []
    validation = splits["validation_height_090"]
    for epoch in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        for x, action_index, end_contact, surface, uv, active_mask, duration in loader:
            x, action_index, end_contact = x.to(device), action_index.to(device), end_contact.to(device)
            surface, uv, active_mask, duration = (
                surface.to(device), uv.to(device), active_mask.to(device), duration.to(device)
            )
            outputs = model(x, action_index)
            surface_loss = F.cross_entropy(outputs[2][active_mask], surface[active_mask])
            uv_loss = F.smooth_l1_loss(outputs[3][active_mask], uv[active_mask])
            loss = (
                F.cross_entropy(outputs[0], action_index, weight=action_weights_t, label_smoothing=0.02)
                + 0.2 * F.binary_cross_entropy_with_logits(outputs[1], end_contact)
                + 0.5 * surface_loss
                + uv_loss
                + 0.2 * F.mse_loss(outputs[4], duration)
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            running += float(loss.detach()) * len(x)
        if epoch == 1 or epoch % 10 == 0 or epoch == args.epochs:
            model.eval()
            probe = evaluate_hierarchical(
                model, samples, validation, labels, action_vocabulary, x_mean, x_std, uv_mean, uv_std,
                duration_mean, duration_std, device,
            )
            score = probe["active_surface_uv_error_cm"]["mean"] + 10.0 * (1.0 - probe["action_exact_accuracy"])
            history.append({"epoch": epoch, "train_loss": running / len(train), "validation": probe})
            print(json.dumps(history[-1]))
            if score < best_score:
                best_score = score
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    assert best_state is not None
    model.load_state_dict(best_state)
    model.eval()
    metrics = {
        name: evaluate_hierarchical(
            model, samples, indices, labels, action_vocabulary, x_mean, x_std, uv_mean, uv_std,
            duration_mean, duration_std, device,
        )
        for name, indices in splits.items()
    }
    checkpoint = {
        "schema": "climb00_hierarchical_contact_event_predictor_v2",
        "model": best_state,
        "input_dim": train_arrays[0].shape[1],
        "width": args.width,
        "blocks": args.blocks,
        "action_embedding_dim": args.action_embedding_dim,
        "action_masks": torch.from_numpy(action_vocabulary),
        "action_counts": torch.from_numpy(action_counts),
        "parts": PARTS,
        "surfaces": SURFACES,
        "x_mean": torch.from_numpy(x_mean),
        "x_std": torch.from_numpy(x_std),
        "uv_mean": torch.from_numpy(uv_mean),
        "uv_std": torch.from_numpy(uv_std),
        "duration_mean": duration_mean,
        "duration_std": duration_std,
        "duration_parameterization": "log_seconds",
        "action_semantics": "observed touchdown masks; all-zero denotes a certified settled-pose waypoint",
        "config": vars(args),
    }
    torch.save(checkpoint, args.output / "model.pt")
    report = {
        "schema": "climb00_hierarchical_contact_event_predictor_report_v2",
        "dataset": dataset_summary,
        "splits": {key: int(len(value)) for key, value in splits.items()},
        "metrics": metrics,
        "history": history,
        "model_contract": {
            "input": dataset_summary["input_contract"],
            "output": dataset_summary["target_contract"],
            "explicitly_excluded": ["future torso pose", "future hand/foot/knee link pose", "future full-body keyframe"],
            "touchdown_output_space": (
                f"categorical over {len(action_vocabulary)} observed masks; "
                "all-zero is a certified settled-pose waypoint"
            ),
            "parameterization": "end-contact/surface/uv/duration explicitly conditioned on selected action",
        },
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
