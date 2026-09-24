from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from somaforge_core.robot_assets import decode_robot_asset_json


ROOT = Path(__file__).absolute().parents[1]
DEFAULT_ATOMS = (
    ROOT
    / "tmp/original28_historical_touchdown_atoms"
    / "original28_historical_touchdown_qonly.npz"
)
DEFAULT_METADATA = ROOT / "tmp/original28_historical_touchdown_atoms/atoms.jsonl"
DEFAULT_CONTACT_ROOT = ROOT / "tmp/original28_historical_segmentation/masked"
DEFAULT_OUTPUT = ROOT / "tmp/g1_touchdown_keyframe_infiller_v1"

BODY_NAMES = (
    "torso_link",
    "left_ankle_roll_link",
    "right_ankle_roll_link",
    "left_wrist_yaw_link",
    "right_wrist_yaw_link",
    "left_knee_link",
    "right_knee_link",
)
PART_NAMES = (
    "left_foot",
    "right_foot",
    "left_hand",
    "right_hand",
    "left_knee",
    "right_knee",
)


def quat_matrix_wxyz(quaternion: np.ndarray) -> np.ndarray:
    q = np.asarray(quaternion, dtype=np.float64)
    q /= np.maximum(np.linalg.norm(q, axis=-1, keepdims=True), 1.0e-8)
    w, x, y, z = np.moveaxis(q, -1, 0)
    return np.stack(
        (
            1 - 2 * (y * y + z * z),
            2 * (x * y - z * w),
            2 * (x * z + y * w),
            2 * (x * y + z * w),
            1 - 2 * (x * x + z * z),
            2 * (y * z - x * w),
            2 * (x * z - y * w),
            2 * (y * z + x * w),
            1 - 2 * (x * x + y * y),
        ),
        axis=-1,
    ).reshape(q.shape[:-1] + (3, 3)).astype(np.float32)


def heading_wxyz(quaternion: np.ndarray) -> float:
    w, x, y, z = np.asarray(quaternion, dtype=np.float64)
    return float(math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z)))


def yaw_matrix(angle: float) -> np.ndarray:
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.asarray(
        [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float32,
    )


def rotation_6d(matrix: np.ndarray) -> np.ndarray:
    return matrix[..., :, :2].reshape(matrix.shape[:-2] + (6,)).astype(np.float32)


def rotation_matrix_6d(values: torch.Tensor) -> torch.Tensor:
    columns = values.reshape(*values.shape[:-1], 3, 2)
    first = F.normalize(columns[..., 0], dim=-1)
    second_raw = columns[..., 1] - (first * columns[..., 1]).sum(dim=-1, keepdim=True) * first
    second = F.normalize(second_raw, dim=-1)
    third = torch.cross(first, second, dim=-1)
    return torch.stack((first, second, third), dim=-1)


@dataclass
class TrajectoryDataset:
    states: torch.Tensor
    contacts: torch.Tensor
    mask: torch.Tensor
    lengths: torch.Tensor
    motion_ids: np.ndarray
    segment_ids: np.ndarray
    touchdown: torch.Tensor
    robot_asset_json: str


def load_metadata(path: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            result[str(item["segment_id"])] = item
    return result


def validate_asset(payload: object, *, context: str) -> str:
    decoded = decode_robot_asset_json(payload, context=context)
    urdf_path = str(decoded["urdf_path"])
    expected = "src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.urdf"
    if not urdf_path.endswith(expected):
        raise ValueError(f"{context}: unexpected robot asset {urdf_path}")
    return str(np.asarray(payload).item())


def load_dataset(atoms_path: Path, metadata_path: Path, contact_root: Path) -> TrajectoryDataset:
    metadata = load_metadata(metadata_path)
    with np.load(atoms_path, allow_pickle=False) as atoms:
        robot_asset_json = validate_asset(atoms["robot_asset_json"], context=str(atoms_path))
        source_paths = atoms["source_paths"].astype(str)
        contact_source_paths = (
            atoms["contact_source_paths"].astype(str)
            if "contact_source_paths" in atoms.files
            else np.full(len(source_paths), "", dtype=str)
        )
        motion_ids_all = atoms["motion_ids"].astype(str)
        segment_ids_all = atoms["segment_ids"].astype(str)
        starts = np.asarray(atoms["start_frames"], dtype=np.int64)
        ends = np.asarray(atoms["end_frames"], dtype=np.int64)

    records: list[tuple[np.ndarray, np.ndarray, str, str, np.ndarray]] = []
    motion_cache: dict[Path, dict[str, np.ndarray]] = {}
    contact_cache: dict[str, tuple[np.ndarray, list[str]]] = {}
    for source_value, contact_source_value, motion_id, segment_id, start, end in zip(
        source_paths,
        contact_source_paths,
        motion_ids_all,
        segment_ids_all,
        starts,
        ends,
        strict=True,
    ):
        item = metadata[segment_id]
        touchdown_names = tuple(str(value) for value in item.get("touchdown_at_end", []))
        # Explicitly marked posture/preparation segments are valid even though
        # their terminal event is a settled pose rather than a touchdown.  Old
        # manifests retain the historical behavior of dropping a final clip
        # fragment without an end touchdown.
        include_for_infiller = item.get("include_for_infiller")
        if include_for_infiller is False or (include_for_infiller is None and not touchdown_names):
            continue
        source = Path(source_value)
        if source not in motion_cache:
            with np.load(source, allow_pickle=False) as data:
                validate_asset(data["robot_asset_json"], context=str(source))
                motion_cache[source] = {
                    "body_names": np.asarray(data["body_names"]),
                    "body_pos_w": np.asarray(data["body_pos_w"], dtype=np.float32),
                    "body_quat_w": np.asarray(data["body_quat_w"], dtype=np.float32),
                }
        motion = motion_cache[source]
        body_names = motion["body_names"].astype(str).tolist()
        indices = [body_names.index(name) for name in BODY_NAMES]
        if end >= len(motion["body_pos_w"]):
            raise ValueError(f"{segment_id}: touchdown frame {end} is outside motion")

        positions_w = motion["body_pos_w"][start : end + 1, indices]
        rotations_w = quat_matrix_wxyz(motion["body_quat_w"][start : end + 1, indices])
        torso_start_position = positions_w[0, 0]
        torso_start_quaternion = motion["body_quat_w"][start, indices[0]]
        world_to_anchor = yaw_matrix(-heading_wxyz(torso_start_quaternion))
        positions = np.einsum(
            "ij,tbj->tbi", world_to_anchor, positions_w - torso_start_position[None, None]
        )
        rotations = np.einsum("ij,tbjk->tbik", world_to_anchor, rotations_w)
        states = np.concatenate(
            (positions.reshape(len(positions), -1), rotation_6d(rotations).reshape(len(positions), -1)),
            axis=-1,
        ).astype(np.float32)

        contact_key = contact_source_value or motion_id
        if contact_key not in contact_cache:
            contact_path = (
                Path(contact_source_value)
                if contact_source_value
                else contact_root / f"{motion_id}_z_scale_1.0.npz"
            )
            with np.load(contact_path, allow_pickle=False) as data:
                if "contact_force_part_mask" in data.files:
                    validate_asset(data["robot_asset_json"], context=str(contact_path))
                    order = np.asarray(data["contact_force_part_order"]).astype(str).tolist()
                    raw = np.asarray(data["contact_force_part_mask"], dtype=np.bool_)
                    masks = np.stack(
                        (
                            raw[:, order.index("LHEE")] | raw[:, order.index("LTOE")],
                            raw[:, order.index("RHEE")] | raw[:, order.index("RTOE")],
                            raw[:, order.index("LH")],
                            raw[:, order.index("RH")],
                            raw[:, order.index("LK")],
                            raw[:, order.index("RK")],
                        ),
                        axis=1,
                    )
                    aligned_order = list(PART_NAMES)
                else:
                    aligned_order = np.asarray(data["part_order"]).astype(str).tolist()
                    masks = np.asarray(data["contact_part_mask"], dtype=np.bool_)
            contact_cache[contact_key] = (masks, aligned_order)
        masks, order = contact_cache[contact_key]
        contact_indices = [order.index(name) for name in PART_NAMES]
        contacts = masks[start : end + 1, contact_indices].astype(np.float32)
        if len(contacts) != len(states):
            raise ValueError(f"{segment_id}: state/contact length mismatch")
        touchdown = np.asarray([name in touchdown_names for name in PART_NAMES], dtype=np.float32)
        records.append((states, contacts, motion_id, segment_id, touchdown))

    maximum = max(len(item[0]) for item in records)
    state_dim = records[0][0].shape[-1]
    states = np.zeros((len(records), maximum, state_dim), dtype=np.float32)
    contacts = np.zeros((len(records), maximum, len(PART_NAMES)), dtype=np.float32)
    valid = np.zeros((len(records), maximum), dtype=np.bool_)
    lengths = np.zeros(len(records), dtype=np.int64)
    motion_ids = []
    segment_ids = []
    touchdowns = []
    for row, (state, contact, motion_id, segment_id, touchdown) in enumerate(records):
        length = len(state)
        states[row, :length] = state
        contacts[row, :length] = contact
        valid[row, :length] = True
        lengths[row] = length
        motion_ids.append(motion_id)
        segment_ids.append(segment_id)
        touchdowns.append(touchdown)
    return TrajectoryDataset(
        states=torch.from_numpy(states),
        contacts=torch.from_numpy(contacts),
        mask=torch.from_numpy(valid),
        lengths=torch.from_numpy(lengths),
        motion_ids=np.asarray(motion_ids),
        segment_ids=np.asarray(segment_ids),
        touchdown=torch.from_numpy(np.asarray(touchdowns, dtype=np.float32)),
        robot_asset_json=robot_asset_json,
    )


def grouped_split(motion_ids: np.ndarray, test_fraction: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    groups = np.unique(motion_ids)
    rng = np.random.default_rng(seed)
    rng.shuffle(groups)
    test_count = max(1, int(round(len(groups) * test_fraction)))
    test_groups = set(groups[:test_count].tolist())
    test = np.asarray([i for i, value in enumerate(motion_ids) if value in test_groups], dtype=np.int64)
    train = np.asarray([i for i, value in enumerate(motion_ids) if value not in test_groups], dtype=np.int64)
    return train, test


class ResidualBlock(nn.Module):
    def __init__(self, width: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.LayerNorm(width),
            nn.Linear(width, 4 * width),
            nn.SiLU(),
            nn.Linear(4 * width, width),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return values + self.layers(values)


class KeyframeInfiller(nn.Module):
    def __init__(self, state_dim: int, contact_dim: int, width: int = 256, layers: int = 4) -> None:
        super().__init__()
        condition_dim = 2 * state_dim + 1 + 3 * contact_dim
        self.condition = nn.Sequential(
            nn.Linear(condition_dim, width),
            nn.SiLU(),
            nn.Linear(width, width),
            nn.SiLU(),
        )
        phase_dim = 1 + 2 * 6
        self.input = nn.Linear(width + phase_dim, width)
        self.blocks = nn.Sequential(*(ResidualBlock(width) for _ in range(layers)))
        self.state_head = nn.Sequential(nn.LayerNorm(width), nn.Linear(width, state_dim))
        self.contact_head = nn.Sequential(nn.LayerNorm(width), nn.Linear(width, contact_dim))

    @staticmethod
    def phase_features(phase: torch.Tensor) -> torch.Tensor:
        frequency = (2.0 ** torch.arange(6, device=phase.device, dtype=phase.dtype)) * math.pi
        angle = phase[..., None] * frequency
        return torch.cat((phase[..., None], torch.sin(angle), torch.cos(angle)), dim=-1)

    def forward(
        self,
        start: torch.Tensor,
        end: torch.Tensor,
        duration: torch.Tensor,
        start_contact: torch.Tensor,
        end_contact: torch.Tensor,
        touchdown: torch.Tensor,
        phase: torch.Tensor,
        valid_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        condition = self.condition(
            torch.cat((start, end, duration[:, None], start_contact, end_contact, touchdown), dim=-1)
        )
        condition = condition[:, None].expand(-1, phase.shape[1], -1)
        hidden = self.input(torch.cat((condition, self.phase_features(phase)), dim=-1))
        hidden = self.blocks(hidden)
        baseline = start[:, None] + phase[..., None] * (end - start)[:, None]
        # Exactly zero at both touchdown boundaries, regardless of network output.
        envelope = (4.0 * phase * (1.0 - phase))[..., None]
        state = baseline + envelope * self.state_head(hidden)
        contact_logits = self.contact_head(hidden)
        boundary_scale = 12.0
        start_logits = boundary_scale * (2.0 * start_contact - 1.0)
        end_logits = boundary_scale * (2.0 * end_contact - 1.0)
        contact_logits = torch.where(
            (phase <= 0.0)[..., None], start_logits[:, None], contact_logits
        )
        contact_logits = torch.where(
            (phase >= 1.0)[..., None], end_logits[:, None], contact_logits
        )
        return state, contact_logits


class AdaLNTransformerBlock(nn.Module):
    def __init__(self, width: int, heads: int, ffn_width: int) -> None:
        super().__init__()
        self.attention_norm = nn.LayerNorm(width, elementwise_affine=False)
        self.ffn_norm = nn.LayerNorm(width, elementwise_affine=False)
        self.attention = nn.MultiheadAttention(width, heads, batch_first=True)
        self.ffn = nn.Sequential(
            nn.Linear(width, ffn_width),
            nn.GELU(),
            nn.Linear(ffn_width, width),
        )
        self.modulation = nn.Sequential(nn.SiLU(), nn.Linear(width, 6 * width))
        nn.init.zeros_(self.modulation[-1].weight)
        nn.init.zeros_(self.modulation[-1].bias)

    @staticmethod
    def modulate(values: torch.Tensor, shift: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
        return values * (1.0 + scale[:, None]) + shift[:, None]

    def forward(
        self,
        values: torch.Tensor,
        condition: torch.Tensor,
        valid_mask: torch.Tensor | None,
    ) -> torch.Tensor:
        shift_attention, scale_attention, gate_attention, shift_ffn, scale_ffn, gate_ffn = (
            self.modulation(condition).chunk(6, dim=-1)
        )
        attention_input = self.modulate(
            self.attention_norm(values), shift_attention, scale_attention
        )
        attention, _ = self.attention(
            attention_input,
            attention_input,
            attention_input,
            key_padding_mask=None if valid_mask is None else ~valid_mask,
            need_weights=False,
        )
        values = values + gate_attention[:, None] * attention
        ffn_input = self.modulate(self.ffn_norm(values), shift_ffn, scale_ffn)
        return values + gate_ffn[:, None] * self.ffn(ffn_input)


class TransformerKeyframeInfiller(nn.Module):
    """Non-causal temporal infiller with endpoint conditions injected at every block."""

    def __init__(
        self,
        state_dim: int,
        contact_dim: int,
        width: int = 128,
        layers: int = 4,
        heads: int = 4,
        ffn_width: int = 512,
    ) -> None:
        super().__init__()
        if width % heads:
            raise ValueError(f"transformer width {width} must be divisible by heads {heads}")
        condition_dim = 2 * state_dim + 1 + 3 * contact_dim
        self.condition = nn.Sequential(
            nn.Linear(condition_dim, width),
            nn.SiLU(),
            nn.Linear(width, width),
        )
        phase_dim = 1 + 2 * 8
        self.phase_input = nn.Sequential(
            nn.Linear(phase_dim, width),
            nn.SiLU(),
            nn.Linear(width, width),
        )
        self.blocks = nn.ModuleList(
            AdaLNTransformerBlock(width, heads, ffn_width) for _ in range(layers)
        )
        self.final_norm = nn.LayerNorm(width)
        self.state_head = nn.Linear(width, state_dim)
        self.contact_head = nn.Linear(width, contact_dim)

    @staticmethod
    def phase_features(phase: torch.Tensor) -> torch.Tensor:
        frequency = (2.0 ** torch.arange(8, device=phase.device, dtype=phase.dtype)) * math.pi
        angle = phase[..., None] * frequency
        return torch.cat((phase[..., None], torch.sin(angle), torch.cos(angle)), dim=-1)

    def forward(
        self,
        start: torch.Tensor,
        end: torch.Tensor,
        duration: torch.Tensor,
        start_contact: torch.Tensor,
        end_contact: torch.Tensor,
        touchdown: torch.Tensor,
        phase: torch.Tensor,
        valid_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        condition = self.condition(
            torch.cat((start, end, duration[:, None], start_contact, end_contact, touchdown), dim=-1)
        )
        values = self.phase_input(self.phase_features(phase)) + condition[:, None]
        for block in self.blocks:
            values = block(values, condition, valid_mask)
        values = self.final_norm(values)
        baseline = start[:, None] + phase[..., None] * (end - start)[:, None]
        envelope = (4.0 * phase * (1.0 - phase))[..., None]
        state = baseline + envelope * self.state_head(values)
        contact_logits = self.contact_head(values)
        boundary_scale = 12.0
        start_logits = boundary_scale * (2.0 * start_contact - 1.0)
        end_logits = boundary_scale * (2.0 * end_contact - 1.0)
        contact_logits = torch.where(
            (phase <= 0.0)[..., None], start_logits[:, None], contact_logits
        )
        contact_logits = torch.where(
            (phase >= 1.0)[..., None], end_logits[:, None], contact_logits
        )
        return state, contact_logits


def gather_endpoint(values: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
    rows = torch.arange(len(values), device=values.device)
    return values[rows, lengths - 1]


def sequence_phase(lengths: torch.Tensor, maximum: int, dtype: torch.dtype) -> torch.Tensor:
    frame = torch.arange(maximum, device=lengths.device, dtype=dtype)[None]
    return frame / (lengths.to(dtype)[:, None] - 1.0).clamp_min(1.0)


def masked_mean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    while mask.ndim < values.ndim:
        mask = mask[..., None]
    return (values * mask).sum() / mask.sum().clamp_min(1.0) / math.prod(values.shape[mask.ndim:])


def predict_batch(
    model: nn.Module,
    states_normalized: torch.Tensor,
    contacts: torch.Tensor,
    lengths: torch.Tensor,
    duration_mean: torch.Tensor,
    duration_std: torch.Tensor,
    touchdown: torch.Tensor,
    valid_mask: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    end = gather_endpoint(states_normalized, lengths)
    end_contact = gather_endpoint(contacts, lengths)
    duration = ((lengths.float() - 1.0).log() - duration_mean) / duration_std
    phase = sequence_phase(lengths, states_normalized.shape[1], states_normalized.dtype)
    prediction, contact_logits = model(
        states_normalized[:, 0],
        end,
        duration,
        contacts[:, 0],
        end_contact,
        touchdown,
        phase,
        valid_mask,
    )
    return prediction, contact_logits, phase


def loss_terms(
    prediction: torch.Tensor,
    contact_logits: torch.Tensor,
    target: torch.Tensor,
    contacts: torch.Tensor,
    mask: torch.Tensor,
) -> dict[str, torch.Tensor]:
    state = masked_mean((prediction - target).square(), mask)
    pair_mask = mask[:, 1:] & mask[:, :-1]
    velocity = masked_mean(
        ((prediction[:, 1:] - prediction[:, :-1]) - (target[:, 1:] - target[:, :-1])).square(),
        pair_mask,
    )
    contact = F.binary_cross_entropy_with_logits(contact_logits, contacts, reduction="none")
    contact = masked_mean(contact, mask)
    return {"state": state, "velocity": velocity, "contact": contact}


def metric_summary(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(values.mean()),
        "p95": float(np.quantile(values, 0.95)),
        "max": float(values.max()),
    }


def evaluate(
    model: nn.Module,
    dataset: TrajectoryDataset,
    indices: np.ndarray,
    mean: torch.Tensor,
    std: torch.Tensor,
    duration_mean: torch.Tensor,
    duration_std: torch.Tensor,
    device: torch.device,
    batch_size: int,
    save_predictions: bool = False,
) -> tuple[dict[str, object], dict[str, np.ndarray] | None]:
    position_errors = []
    rotation_errors = []
    baseline_position_errors = []
    baseline_rotation_errors = []
    middle_contact_correct = []
    all_predictions = []
    all_rows = []
    model.eval()
    with torch.inference_mode():
        for begin in range(0, len(indices), batch_size):
            rows = indices[begin : begin + batch_size]
            states = dataset.states[rows].to(device)
            contacts = dataset.contacts[rows].to(device)
            mask = dataset.mask[rows].to(device)
            lengths = dataset.lengths[rows].to(device)
            touchdown = dataset.touchdown[rows].to(device)
            normalized = (states - mean) / std
            prediction_normalized, contact_logits, phase = predict_batch(
                model,
                normalized,
                contacts,
                lengths,
                duration_mean,
                duration_std,
                touchdown,
                mask,
            )
            prediction = prediction_normalized * std + mean
            start = states[:, 0]
            end = gather_endpoint(states, lengths)
            baseline = start[:, None] + phase[..., None] * (end - start)[:, None]
            body_count = len(BODY_NAMES)
            for candidate, pos_output, rot_output in (
                (prediction, position_errors, rotation_errors),
                (baseline, baseline_position_errors, baseline_rotation_errors),
            ):
                position = candidate[..., : 3 * body_count].reshape(*candidate.shape[:2], body_count, 3)
                target_position = states[..., : 3 * body_count].reshape(*states.shape[:2], body_count, 3)
                distance_cm = torch.linalg.vector_norm(position - target_position, dim=-1) * 100.0
                rotation = rotation_matrix_6d(
                    candidate[..., 3 * body_count :].reshape(*candidate.shape[:2], body_count, 6)
                )
                target_rotation = rotation_matrix_6d(
                    states[..., 3 * body_count :].reshape(*states.shape[:2], body_count, 6)
                )
                relative = rotation.transpose(-1, -2) @ target_rotation
                cosine = ((relative.diagonal(dim1=-2, dim2=-1).sum(-1) - 1.0) * 0.5).clamp(-1.0, 1.0)
                angle_deg = torch.acos(cosine) * (180.0 / math.pi)
                middle_mask = mask.clone()
                middle_mask[:, 0] = False
                row_ids = torch.arange(len(rows), device=device)
                middle_mask[row_ids, lengths - 1] = False
                pos_output.append(distance_cm[middle_mask].cpu().numpy())
                rot_output.append(angle_deg[middle_mask].cpu().numpy())
            predicted_contact = contact_logits.sigmoid() >= 0.5
            middle_mask = mask.clone()
            middle_mask[:, 0] = False
            row_ids = torch.arange(len(rows), device=device)
            middle_mask[row_ids, lengths - 1] = False
            middle_contact_correct.append(
                (predicted_contact == contacts.bool())[middle_mask].float().cpu().numpy()
            )
            if save_predictions:
                all_predictions.append(prediction.cpu().numpy())
                all_rows.append(rows)

    position = np.concatenate(position_errors)
    rotation = np.concatenate(rotation_errors)
    baseline_position = np.concatenate(baseline_position_errors)
    baseline_rotation = np.concatenate(baseline_rotation_errors)
    contact_correct = np.concatenate(middle_contact_correct)
    metrics: dict[str, object] = {
        "samples": int(len(indices)),
        "middle_position_error_cm": metric_summary(position),
        "middle_rotation_error_deg": metric_summary(rotation),
        "middle_contact_bit_accuracy": float(contact_correct.mean()),
        "linear_baseline_middle_position_error_cm": metric_summary(baseline_position),
        "linear_baseline_middle_rotation_error_deg": metric_summary(baseline_rotation),
        "endpoint_constraint": "exact by construction",
    }
    artifact = None
    if save_predictions:
        artifact = {
            "indices": np.concatenate(all_rows),
            "predicted_states": np.concatenate(all_predictions),
        }
    return metrics, artifact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atoms", type=Path, default=DEFAULT_ATOMS)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--contact-root", type=Path, default=DEFAULT_CONTACT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--steps", type=int, default=10_000)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=3.0e-4)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--model", choices=("mlp", "transformer"), default="transformer")
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--ffn-width", type=int, default=512)
    parser.add_argument("--eval-every", type=int, default=1_000)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument(
        "--single-motion-train-all",
        action="store_true",
        help="Use every segment for both training and reconstruction evaluation when only one motion exists.",
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device)
    dataset = load_dataset(args.atoms, args.metadata, args.contact_root)
    if args.single_motion_train_all:
        if len(np.unique(dataset.motion_ids)) != 1:
            raise ValueError("--single-motion-train-all requires exactly one motion")
        train_indices = np.arange(len(dataset.motion_ids), dtype=np.int64)
        test_indices = train_indices.copy()
    else:
        train_indices, test_indices = grouped_split(dataset.motion_ids, args.test_fraction, args.seed)
    train_mask = dataset.mask[train_indices]
    train_values = dataset.states[train_indices][train_mask]
    mean = train_values.mean(dim=0).to(device)[None, None]
    std = train_values.std(dim=0).clamp_min(1.0e-3).to(device)[None, None]
    log_duration = (dataset.lengths[train_indices].float() - 1.0).log()
    duration_mean = log_duration.mean().to(device)
    duration_std = log_duration.std().clamp_min(1.0e-3).to(device)

    if args.model == "mlp":
        model: nn.Module = KeyframeInfiller(
            dataset.states.shape[-1], dataset.contacts.shape[-1], width=args.width, layers=args.layers
        )
    else:
        model = TransformerKeyframeInfiller(
            dataset.states.shape[-1],
            dataset.contacts.shape[-1],
            width=args.width,
            layers=args.layers,
            heads=args.heads,
            ffn_width=args.ffn_width,
        )
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1.0e-4)
    rng = np.random.default_rng(args.seed)
    history = []
    for step in range(1, args.steps + 1):
        rows = rng.choice(train_indices, size=args.batch_size, replace=True)
        states = dataset.states[rows].to(device)
        contacts = dataset.contacts[rows].to(device)
        mask = dataset.mask[rows].to(device)
        lengths = dataset.lengths[rows].to(device)
        touchdown = dataset.touchdown[rows].to(device)
        normalized = (states - mean) / std
        prediction, contact_logits, _ = predict_batch(
            model,
            normalized,
            contacts,
            lengths,
            duration_mean,
            duration_std,
            touchdown,
            mask,
        )
        terms = loss_terms(prediction, contact_logits, normalized, contacts, mask)
        loss = terms["state"] + 0.25 * terms["velocity"] + 0.1 * terms["contact"]
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            probe_rows = test_indices[: min(64, len(test_indices))]
            probe, _ = evaluate(
                model,
                dataset,
                probe_rows,
                mean,
                std,
                duration_mean,
                duration_std,
                device,
                args.batch_size,
            )
            record = {
                "step": step,
                "loss": float(loss.detach()),
                **{f"loss/{name}": float(value.detach()) for name, value in terms.items()},
                "test_middle_position_mean_cm": probe["middle_position_error_cm"]["mean"],
                "test_middle_position_p95_cm": probe["middle_position_error_cm"]["p95"],
                "test_contact_accuracy": probe["middle_contact_bit_accuracy"],
            }
            history.append(record)
            print(json.dumps(record), flush=True)
            model.train()

    train_metrics, _ = evaluate(
        model,
        dataset,
        train_indices,
        mean,
        std,
        duration_mean,
        duration_std,
        device,
        args.batch_size,
    )
    test_metrics, predictions = evaluate(
        model,
        dataset,
        test_indices,
        mean,
        std,
        duration_mean,
        duration_std,
        device,
        args.batch_size,
        save_predictions=True,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "model": model.state_dict(),
        "state_mean": mean.cpu(),
        "state_std": std.cpu(),
        "duration_mean": duration_mean.cpu(),
        "duration_std": duration_std.cpu(),
        "body_names": BODY_NAMES,
        "part_names": PART_NAMES,
        "robot_asset_json": dataset.robot_asset_json,
        "config": vars(args),
    }
    torch.save(checkpoint, args.output / "model.pt")
    assert predictions is not None
    np.savez_compressed(
        args.output / "test_predictions.npz",
        **predictions,
        target_states=dataset.states[predictions["indices"]].numpy(),
        contacts=dataset.contacts[predictions["indices"]].numpy(),
        valid_mask=dataset.mask[predictions["indices"]].numpy(),
        lengths=dataset.lengths[predictions["indices"]].numpy(),
        segment_ids=dataset.segment_ids[predictions["indices"]],
        motion_ids=dataset.motion_ids[predictions["indices"]],
        body_names=np.asarray(BODY_NAMES),
        part_names=np.asarray(PART_NAMES),
        robot_asset_json=np.asarray(dataset.robot_asset_json),
    )
    summary = {
        "schema": "g1_touchdown_keyframe_infiller_v1",
        "definition": "true inclusive touchdown boundary -> next true inclusive touchdown boundary",
        "coordinate_system": "segment-start torso-yaw frame",
        "model": (
            "endpoint-conditioned phase-query residual MLP with exact endpoint envelope"
            if args.model == "mlp"
            else "non-causal temporal AdaLN Transformer with exact endpoint envelope"
        ),
        "samples": len(dataset.states),
        "train_samples": len(train_indices),
        "test_samples": len(test_indices),
        "motion_group_overlap": sorted(
            set(dataset.motion_ids[train_indices]) & set(dataset.motion_ids[test_indices])
        ),
        "length_frames": {
            "min": int(dataset.lengths.min()),
            "median": float(dataset.lengths.float().median()),
            "p95": float(torch.quantile(dataset.lengths.float(), 0.95)),
            "max": int(dataset.lengths.max()),
        },
        "parameters": sum(parameter.numel() for parameter in model.parameters()),
        "body_names": list(BODY_NAMES),
        "part_names": list(PART_NAMES),
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
        "history": history,
        "artifacts": {
            "checkpoint": str(args.output / "model.pt"),
            "test_predictions": str(args.output / "test_predictions.npz"),
        },
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
