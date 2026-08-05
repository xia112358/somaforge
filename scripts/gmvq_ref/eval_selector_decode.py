#!/usr/bin/env python3
"""Evaluate `obs -> code/theta -> GMVQ decode` against source ref segments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch
from somaforge_core.robot_assets import somaforge_root

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gmvq.hyar_wrapper import FrozenGMVQCodec

from scripts.gmvq_ref.selector_runtime import GMVQSelectorRuntime
from scripts.gmvq_ref.train_selector_code import _build_features as build_code_features
from scripts.gmvq_ref.train_selector_code import _group_split


def _load_segments(path: Path, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path.expanduser(), allow_pickle=True) as data:
        segments = np.asarray(data["segments"][indices], dtype=np.float32)
        valid_mask = np.asarray(data["valid_mask"][indices], dtype=np.bool_)
    return segments, valid_mask


def _valid_mse(x_hat: np.ndarray, target: np.ndarray, valid_mask: np.ndarray) -> dict[str, float]:
    mask = valid_mask[..., None].astype(np.float32)
    sq = (x_hat - target) ** 2 * mask
    frame_mse = float(sq.sum() / max(float(mask.sum() * target.shape[-1]), 1.0))
    seq_den = np.maximum(valid_mask.sum(axis=1).astype(np.float32) * target.shape[-1], 1.0)
    seq_mse = np.sum(sq, axis=(1, 2)) / seq_den
    return {
        "valid_frame_mse": frame_mse,
        "mean_segment_mse": float(seq_mse.mean()),
    }


@torch.no_grad()
def _decode_batches(
    codec: FrozenGMVQCodec,
    code: np.ndarray,
    theta: np.ndarray,
    lengths: np.ndarray,
    *,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    outs: list[np.ndarray] = []
    for start in range(0, code.shape[0], batch_size):
        k = torch.from_numpy(code[start : start + batch_size].astype(np.int64)).to(device)
        th = torch.from_numpy(theta[start : start + batch_size].astype(np.float32)).to(device)
        length = torch.from_numpy(lengths[start : start + batch_size].astype(np.int64)).to(device)
        outs.append(codec.decode_hybrid(k, th, lengths=length)["x_hat"].cpu().numpy())
    return np.concatenate(outs, axis=0)


@torch.no_grad()
def _predict_codes(runtime: GMVQSelectorRuntime, obs: np.ndarray, batch_size: int) -> np.ndarray:
    outs: list[np.ndarray] = []
    for start in range(0, obs.shape[0], batch_size):
        xb = torch.from_numpy(obs[start : start + batch_size].astype(np.float32)).to(runtime.device_ref)
        outs.append(runtime.predict_code(xb).cpu().numpy())
    return np.concatenate(outs, axis=0)


@torch.no_grad()
def _predict_theta(
    runtime: GMVQSelectorRuntime,
    obs: np.ndarray,
    code: np.ndarray,
    batch_size: int,
) -> np.ndarray:
    outs: list[np.ndarray] = []
    for start in range(0, obs.shape[0], batch_size):
        xb = torch.from_numpy(obs[start : start + batch_size].astype(np.float32)).to(runtime.device_ref)
        kb = torch.from_numpy(code[start : start + batch_size].astype(np.int64)).to(runtime.device_ref)
        outs.append(runtime.predict_theta(xb, kb).cpu().numpy())
    return np.concatenate(outs, axis=0)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    device = torch.device(args.device)
    out_dir = args.out_dir.expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    runtime = GMVQSelectorRuntime(
        code_checkpoint=args.code_selector,
        theta_checkpoint=args.theta_selector,
        gmvq_checkpoint=args.gmvq_checkpoint,
        device=device,
    )
    codec = runtime.gmvq_codec

    with np.load(args.selector_dataset.expanduser(), allow_pickle=False) as data:
        obs, obs_keys = build_code_features(data, ["height", "root", "joint"])
        codes_true = np.asarray(data["codes"], dtype=np.int64)
        theta_true = np.asarray(data["theta"], dtype=np.float32)
        lengths_all = np.asarray(data["lengths"], dtype=np.int64)
        groups = np.asarray(data[args.split_group]).astype(str)
        train_mask, val_mask, test_mask = _group_split(groups, args.train_frac, args.val_frac, args.seed)

    test_indices = np.flatnonzero(test_mask)
    if args.max_samples is not None:
        test_indices = test_indices[: args.max_samples]

    obs_test = obs[test_indices]
    codes_test = codes_true[test_indices]
    theta_test = theta_true[test_indices]
    lengths_test = lengths_all[test_indices]

    codes_pred = _predict_codes(runtime, obs_test, args.batch_size)
    theta_true_code = _predict_theta(runtime, obs_test, codes_test, args.batch_size)
    theta_pred_code = _predict_theta(runtime, obs_test, codes_pred, args.batch_size)

    segments, valid_mask = _load_segments(args.segment_pack, test_indices)
    if codec.norm_stats is None:
        target = segments
    else:
        mean = codec.norm_stats.mean.cpu().numpy().astype(np.float32)
        std = codec.norm_stats.std.cpu().numpy().astype(np.float32)
        target = (segments - mean) / std

    oracle = _decode_batches(
        codec, codes_test, theta_test, lengths_test, device=device, batch_size=args.batch_size
    )
    selector_true_code = _decode_batches(
        codec, codes_test, theta_true_code, lengths_test, device=device, batch_size=args.batch_size
    )
    selector_pred_code = _decode_batches(
        codec, codes_pred, theta_pred_code, lengths_test, device=device, batch_size=args.batch_size
    )

    summary: dict[str, Any] = {
        "schema": "gmvq_selector_decode_eval_v1",
        "selector_dataset": str(args.selector_dataset.expanduser()),
        "segment_pack": str(args.segment_pack.expanduser()),
        "gmvq_checkpoint": str(args.gmvq_checkpoint.expanduser()),
        "code_selector": str(args.code_selector.expanduser()),
        "theta_selector": str(args.theta_selector.expanduser()),
        "split_group": args.split_group,
        "seed": args.seed,
        "test_count": int(test_indices.shape[0]),
        "obs_keys": obs_keys,
        "runtime": runtime.metadata(),
        "code_accuracy": float(np.mean(codes_pred == codes_test)),
        "theta_mse_true_code": float(np.mean((theta_true_code - theta_test) ** 2)),
        "theta_mse_pred_code": float(np.mean((theta_pred_code - theta_test) ** 2)),
        "oracle_gmvq": _valid_mse(oracle, target, valid_mask),
        "selector_true_code": _valid_mse(selector_true_code, target, valid_mask),
        "selector_pred_code": _valid_mse(selector_pred_code, target, valid_mask),
    }

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    np.save(out_dir / "test_indices.npy", test_indices)
    np.save(out_dir / "codes_pred.npy", codes_pred)
    np.save(out_dir / "codes_true.npy", codes_test)
    np.save(out_dir / "theta_pred_code.npy", theta_pred_code)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    base = somaforge_root() / "tmp/gmvq_play"
    selector_base = base / "selector_dataset_v1/raw29_large_mixed_n64_codes16_height"
    gmvq_base = base / "gmvq_aug_full_ref_t192_raw29_large_mixed_n64_codes16_12k"
    parser.add_argument(
        "--selector-dataset",
        type=Path,
        default=selector_base / "selector_height_code_theta_dataset.npz",
    )
    parser.add_argument(
        "--segment-pack",
        type=Path,
        default=base / "motion_edit_aug_full_ref_relative_t192_raw29_large_mixed_n64_full.npz",
    )
    parser.add_argument("--gmvq-checkpoint", type=Path, default=gmvq_base / "checkpoint.pt")
    parser.add_argument("--code-selector", type=Path, default=selector_base / "code_selector_mlp_hrootjoint_80e/checkpoint.pt")
    parser.add_argument("--theta-selector", type=Path, default=selector_base / "theta_selector_mlp_hrootjoint_code_100e/checkpoint.pt")
    parser.add_argument("--out-dir", type=Path, default=selector_base / "selector_decode_eval")
    parser.add_argument("--split-group", default="raw_clip_paths")
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--val-frac", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def main() -> None:
    evaluate(parse_args())


if __name__ == "__main__":
    main()
