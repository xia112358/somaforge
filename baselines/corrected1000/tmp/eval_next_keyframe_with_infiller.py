#!/usr/bin/env python3
"""Evaluate next-contact prediction followed by the existing G1 temporal infiller."""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT / "tmp"))

from train_g1_touchdown_keyframe_infiller import (  # noqa: E402
    BODY_NAMES,
    PART_NAMES,
    TransformerKeyframeInfiller,
    quat_matrix_wxyz,
    rotation_6d,
    rotation_matrix_6d,
    validate_asset,
    yaw_matrix,
)
from train_next_contact_keyframe_predictor import (  # noqa: E402
    Predictor,
    build_samples,
    source_contact_schedule,
)


DEFAULT_MANIFEST = ROOT / "tmp/climb00_continuous_coverage/training_manifest_207.json"
DEFAULT_PREDICTOR = ROOT / "tmp/climb00_next_contact_keyframe_v1/model.pt"
DEFAULT_INFILLER = ROOT / "tmp/g1_merged_touchdown_infiller_v2_3k/model.pt"
DEFAULT_OUTPUT = ROOT / "tmp/climb00_next_contact_infilled_v1"


def collapse_contact(values: np.ndarray) -> np.ndarray:
    if values.shape[-1] == 6:
        return values.astype(np.float32)
    values = np.asarray(values)
    return np.stack(
        (
            values[..., 0] | values[..., 1],
            values[..., 2] | values[..., 3],
            values[..., 4],
            values[..., 5],
            values[..., 6],
            values[..., 7],
        ),
        axis=-1,
    ).astype(np.float32)


@dataclass
class Segment:
    motion_id: int
    height: float
    current_frame: int
    target_frame: int
    states: np.ndarray
    contacts: np.ndarray
    predictor_x: np.ndarray
    target_endpoint: np.ndarray
    touchdown: np.ndarray
    fps: float


def load_segments(manifest_path: Path, heights: set[float]) -> list[Segment]:
    manifest = json.loads(manifest_path.read_text())
    samples, _ = build_samples(manifest_path)
    selected = [sample for sample in samples if round(sample.height, 2) in heights]
    motion_cache: dict[int, tuple[dict[str, np.ndarray], np.ndarray, float, list[int]]] = {}
    segments = []
    for sample in selected:
        if sample.motion_id not in motion_cache:
            entry = manifest["motion_files"][sample.motion_id]
            with np.load(entry["motion_file"], allow_pickle=False) as loaded:
                validate_asset(loaded["robot_asset_json"], context=str(entry["motion_file"]))
                motion = {
                    "body_names": np.asarray(loaded["body_names"]),
                    "body_pos_w": np.asarray(loaded["body_pos_w"], dtype=np.float32),
                    "body_quat_w": np.asarray(loaded["body_quat_w"], dtype=np.float32),
                }
                fps = float(np.asarray(loaded["fps"]).item())
            body_names = motion["body_names"].astype(str).tolist()
            indices = [body_names.index(name) for name in BODY_NAMES]
            contact8 = source_contact_schedule(entry, len(motion["body_pos_w"]))
            motion_cache[sample.motion_id] = (motion, contact8, fps, indices)
        motion, contact8, fps, indices = motion_cache[sample.motion_id]
        start, end = sample.current_frame, sample.target_frame
        position_w = motion["body_pos_w"][start : end + 1, indices]
        rotation_w = quat_matrix_wxyz(motion["body_quat_w"][start : end + 1, indices])
        anchor_position = position_w[0, 0]
        torso_rotation = rotation_w[0, 0]
        heading = math.atan2(float(torso_rotation[1, 0]), float(torso_rotation[0, 0]))
        world_to_anchor = yaw_matrix(-heading)
        position = np.einsum(
            "ij,tbj->tbi", world_to_anchor, position_w - anchor_position[None, None]
        )
        rotation = np.einsum("ij,tbjk->tbik", world_to_anchor, rotation_w)
        states = np.concatenate(
            (position.reshape(len(position), -1), rotation_6d(rotation).reshape(len(rotation), -1)),
            axis=-1,
        ).astype(np.float32)
        contacts = collapse_contact(contact8[start : end + 1])
        target_endpoint = sample.continuous[:-1]
        if not np.allclose(states[-1], target_endpoint, atol=2.0e-5):
            raise RuntimeError(f"endpoint coordinate mismatch for motion {sample.motion_id} frame {end}")
        segments.append(
            Segment(
                motion_id=sample.motion_id,
                height=sample.height,
                current_frame=start,
                target_frame=end,
                states=states,
                contacts=contacts,
                predictor_x=sample.x,
                target_endpoint=target_endpoint,
                touchdown=collapse_contact(sample.touchdown.astype(bool)),
                fps=fps,
            )
        )
    return segments


def stats(values: list[np.ndarray]) -> dict[str, float]:
    flat = np.concatenate([np.asarray(value).reshape(-1) for value in values])
    return {
        "mean": float(flat.mean()),
        "p95": float(np.quantile(flat, 0.95)),
        "max": float(flat.max()),
    }


def load_models(
    predictor_path: Path, infiller_path: Path, device: torch.device
) -> tuple[Predictor, dict, TransformerKeyframeInfiller, dict]:
    predictor_ckpt = torch.load(predictor_path, map_location=device, weights_only=False)
    predictor = Predictor(**predictor_ckpt["model"]).to(device)
    predictor.load_state_dict(predictor_ckpt["state_dict"])
    predictor.eval()
    infiller_ckpt = torch.load(infiller_path, map_location=device, weights_only=False)
    if tuple(infiller_ckpt["body_names"]) != BODY_NAMES or tuple(infiller_ckpt["part_names"]) != PART_NAMES:
        raise ValueError("infiller body/contact schema mismatch")
    config = infiller_ckpt["config"]
    infiller = TransformerKeyframeInfiller(
        state_dim=63,
        contact_dim=6,
        width=int(config["width"]),
        layers=int(config["layers"]),
        heads=int(config["heads"]),
        ffn_width=int(config["ffn_width"]),
    ).to(device)
    infiller.load_state_dict(infiller_ckpt["model"])
    infiller.eval()
    return predictor, predictor_ckpt, infiller, infiller_ckpt


def predict_endpoints(
    model: Predictor, checkpoint: dict, segments: list[Segment], device: torch.device, batch_size: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x = np.stack([segment.predictor_x for segment in segments])
    outputs, touchdowns, contacts = [], [], []
    mean = checkpoint["x_mean"].cpu().numpy()
    std = checkpoint["x_std"].cpu().numpy()
    y_mean = checkpoint["y_mean"].cpu().numpy()
    y_std = checkpoint["y_std"].cpu().numpy()
    with torch.inference_mode():
        for begin in range(0, len(x), batch_size):
            batch = torch.as_tensor((x[begin : begin + batch_size] - mean) / std, device=device)
            output, touchdown_logits, contact_logits = model(batch)
            outputs.append(output.cpu().numpy() * y_std + y_mean)
            touchdowns.append((touchdown_logits.sigmoid() >= 0.5).cpu().numpy())
            contacts.append((contact_logits.sigmoid() >= 0.5).cpu().numpy())
    output = np.concatenate(outputs)
    return output[:, :-1], output[:, -1], collapse_contact(np.concatenate(touchdowns)), collapse_contact(np.concatenate(contacts))


def evaluate_case(
    name: str,
    infiller: TransformerKeyframeInfiller,
    checkpoint: dict,
    segments: list[Segment],
    endpoint: np.ndarray,
    duration_seconds: np.ndarray,
    end_contact: np.ndarray,
    touchdown: np.ndarray,
    device: torch.device,
    batch_size: int,
) -> tuple[dict, list[np.ndarray]]:
    state_mean = checkpoint["state_mean"].to(device)
    state_std = checkpoint["state_std"].to(device)
    duration_mean = checkpoint["duration_mean"].to(device)
    duration_std = checkpoint["duration_std"].to(device)
    position_errors: list[np.ndarray] = []
    rotation_errors: list[np.ndarray] = []
    final5_errors: list[np.ndarray] = []
    active_final5_errors: list[np.ndarray] = []
    contact_correct: list[np.ndarray] = []
    predictions: list[np.ndarray] = []
    endpoint_input_z = []
    body_count = len(BODY_NAMES)
    for begin in range(0, len(segments), batch_size):
        batch_segments = segments[begin : begin + batch_size]
        maximum = max(len(segment.states) for segment in batch_segments)
        lengths = torch.as_tensor([len(segment.states) for segment in batch_segments], device=device)
        mask = torch.arange(maximum, device=device)[None] < lengths[:, None]
        phase = torch.arange(maximum, device=device, dtype=torch.float32)[None] / (lengths.float()[:, None] - 1.0)
        start = torch.as_tensor(np.stack([segment.states[0] for segment in batch_segments]), device=device)
        end = torch.as_tensor(endpoint[begin : begin + len(batch_segments)], device=device)
        start_contact = torch.as_tensor(np.stack([segment.contacts[0] for segment in batch_segments]), device=device)
        batch_end_contact = torch.as_tensor(end_contact[begin : begin + len(batch_segments)], device=device)
        batch_touchdown = torch.as_tensor(touchdown[begin : begin + len(batch_segments)], device=device)
        gap_frames = torch.as_tensor(
            duration_seconds[begin : begin + len(batch_segments)]
            * np.asarray([segment.fps for segment in batch_segments]),
            dtype=torch.float32,
            device=device,
        ).clamp_min(1.0)
        duration = (gap_frames.log() - duration_mean) / duration_std
        start_n = (start - state_mean[0, 0]) / state_std[0, 0]
        end_n = (end - state_mean[0, 0]) / state_std[0, 0]
        endpoint_input_z.append(end_n.abs().cpu().numpy())
        with torch.inference_mode():
            predicted_n, contact_logits = infiller(
                start_n, end_n, duration, start_contact, batch_end_contact, batch_touchdown, phase, mask
            )
            predicted = predicted_n * state_std + state_mean
        predicted_contact = contact_logits.sigmoid() >= 0.5
        for local, segment in enumerate(batch_segments):
            length = len(segment.states)
            candidate = predicted[local, :length]
            target = torch.as_tensor(segment.states, device=device)
            position = candidate[:, : 3 * body_count].reshape(length, body_count, 3)
            target_position = target[:, : 3 * body_count].reshape(length, body_count, 3)
            pos_error = torch.linalg.vector_norm(position - target_position, dim=-1).cpu().numpy() * 100.0
            rotation = rotation_matrix_6d(candidate[:, 3 * body_count :].reshape(length, body_count, 6))
            target_rotation = rotation_matrix_6d(target[:, 3 * body_count :].reshape(length, body_count, 6))
            relative = rotation.transpose(-1, -2) @ target_rotation
            cosine = ((relative.diagonal(dim1=-2, dim2=-1).sum(-1) - 1.0) * 0.5).clamp(-1.0, 1.0)
            rot_error = (torch.acos(cosine) * (180.0 / math.pi)).cpu().numpy()
            interior = slice(1, max(length - 1, 1))
            position_errors.append(pos_error[interior])
            rotation_errors.append(rot_error[interior])
            last_begin = max(1, length - 6)
            final5_errors.append(pos_error[last_begin : length - 1])
            active = np.flatnonzero(touchdown[begin + local] > 0.5) + 1
            active_final5_errors.append(pos_error[last_begin : length - 1, active])
            true_contact = torch.as_tensor(segment.contacts, device=device).bool()
            contact_correct.append(
                (predicted_contact[local, 1 : length - 1] == true_contact[1 : length - 1]).cpu().numpy()
            )
            predictions.append(candidate.cpu().numpy())
    z = np.concatenate(endpoint_input_z).reshape(-1)
    return {
        "case": name,
        "segments": len(segments),
        "middle_position_error_cm": stats(position_errors),
        "last5_interior_position_error_cm": stats(final5_errors),
        "active_touchdown_last5_position_error_cm": stats(active_final5_errors),
        "middle_rotation_error_deg": stats(rotation_errors),
        "middle_contact_bit_accuracy": float(np.concatenate([v.reshape(-1) for v in contact_correct]).mean()),
        "endpoint_condition_abs_z": {
            "mean": float(z.mean()), "p95": float(np.quantile(z, 0.95)), "max": float(z.max())
        },
        "endpoint_constraint": "exact to the endpoint supplied to the infiller",
    }, predictions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--predictor", type=Path, default=DEFAULT_PREDICTOR)
    parser.add_argument("--infiller", type=Path, default=DEFAULT_INFILLER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--heights", default="0.90,1.10")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    heights = {round(float(value), 2) for value in args.heights.split(",")}
    device = torch.device(args.device)
    segments = load_segments(args.manifest, heights)
    predictor, predictor_ckpt, infiller, infiller_ckpt = load_models(args.predictor, args.infiller, device)
    predicted_endpoint, predicted_duration, predicted_touchdown, predicted_contact = predict_endpoints(
        predictor, predictor_ckpt, segments, device, args.batch_size
    )
    true_endpoint = np.stack([segment.states[-1] for segment in segments])
    true_duration = np.asarray([(len(segment.states) - 1) / segment.fps for segment in segments], dtype=np.float32)
    true_touchdown = np.stack([segment.touchdown for segment in segments])
    true_contact = np.stack([segment.contacts[-1] for segment in segments])
    reports = {}
    for height in sorted(heights):
        indices = np.flatnonzero(np.isclose([segment.height for segment in segments], height))
        subset = [segments[index] for index in indices]
        oracle, oracle_predictions = evaluate_case(
            "true_endpoint_infiller",
            infiller,
            infiller_ckpt,
            subset,
            true_endpoint[indices],
            true_duration[indices],
            true_contact[indices],
            true_touchdown[indices],
            device,
            args.batch_size,
        )
        complete, complete_predictions = evaluate_case(
            "predicted_endpoint_infiller",
            infiller,
            infiller_ckpt,
            subset,
            predicted_endpoint[indices],
            predicted_duration[indices],
            predicted_contact[indices],
            predicted_touchdown[indices],
            device,
            args.batch_size,
        )
        endpoint_error = np.linalg.norm(
            predicted_endpoint[indices, :21].reshape(-1, 7, 3)
            - true_endpoint[indices, :21].reshape(-1, 7, 3), axis=-1
        ) * 100.0
        duration_error = np.abs(predicted_duration[indices] - true_duration[indices]) * 50.0
        reports[f"height_{height:.2f}"] = {
            "segments": len(indices),
            "endpoint_position_error_cm": {
                "mean": float(endpoint_error.mean()),
                "p95": float(np.quantile(endpoint_error, 0.95)),
                "max": float(endpoint_error.max()),
            },
            "duration_error_frames_at_50hz": {
                "mean": float(duration_error.mean()),
                "p95": float(np.quantile(duration_error, 0.95)),
                "max": float(duration_error.max()),
            },
            "oracle": oracle,
            "complete": complete,
        }
    report = {
        "schema": "climb00_next_contact_plus_infiller_eval_v1",
        "definition": "observed current touchdown boundary -> predicted next boundary -> frozen existing AdaLN temporal infiller",
        "predictor": str(args.predictor.resolve()),
        "infiller": str(args.infiller.resolve()),
        "infiller_retrained": False,
        "metrics": reports,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(
        args.output / "predicted_keyframes.npz",
        motion_id=np.asarray([segment.motion_id for segment in segments]),
        height=np.asarray([segment.height for segment in segments]),
        current_frame=np.asarray([segment.current_frame for segment in segments]),
        target_frame=np.asarray([segment.target_frame for segment in segments]),
        predicted_endpoint=predicted_endpoint,
        predicted_duration_seconds=predicted_duration,
        predicted_touchdown=predicted_touchdown,
        predicted_contact=predicted_contact,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
