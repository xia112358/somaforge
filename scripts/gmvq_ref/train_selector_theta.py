#!/usr/bin/env python3
"""Train an offline selector head from observations and GMVQ code to theta."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


FEATURE_GROUPS = {
    "height": ("height_scan",),
    "root": ("root_pos_w", "root_quat_w", "root_lin_vel_w", "root_ang_vel_w"),
    "joint": ("joint_pos", "joint_vel"),
}


class ThetaMLP(nn.Module):
    def __init__(self, input_dim: int, theta_dim: int, hidden_dim: int, depth: int, dropout: float) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        dim = input_dim
        for _ in range(depth):
            layers += [nn.Linear(dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU()]
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            dim = hidden_dim
        layers.append(nn.Linear(dim, theta_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def _flatten(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    return arr.reshape(arr.shape[0], -1)


def _build_features(data: np.lib.npyio.NpzFile, groups: list[str], num_codes: int) -> tuple[np.ndarray, list[str]]:
    parts: list[np.ndarray] = []
    names: list[str] = []
    for group in groups:
        if group not in FEATURE_GROUPS:
            raise ValueError(f"unknown feature group {group!r}; choices={sorted(FEATURE_GROUPS)}")
        for key in FEATURE_GROUPS[group]:
            if key not in data.files:
                raise KeyError(f"dataset missing feature key {key}")
            parts.append(_flatten(data[key]))
            names.append(key)
    codes = np.asarray(data["codes"], dtype=np.int64)
    onehot = np.zeros((codes.shape[0], num_codes), dtype=np.float32)
    onehot[np.arange(codes.shape[0]), codes] = 1.0
    parts.append(onehot)
    names.append("code_onehot")
    return np.concatenate(parts, axis=1).astype(np.float32), names


def _group_split(groups: np.ndarray, train_frac: float, val_frac: float, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    unique = np.asarray(sorted(set(str(x) for x in groups)))
    rng = np.random.default_rng(seed)
    rng.shuffle(unique)
    n_train = int(round(len(unique) * train_frac))
    n_val = int(round(len(unique) * val_frac))
    train_groups = set(unique[:n_train])
    val_groups = set(unique[n_train : n_train + n_val])
    test_groups = set(unique[n_train + n_val :])
    group_str = np.asarray([str(x) for x in groups])
    return (
        np.asarray([x in train_groups for x in group_str]),
        np.asarray([x in val_groups for x in group_str]),
        np.asarray([x in test_groups for x in group_str]),
    )


def _standardize(x: np.ndarray, train_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x[train_mask].mean(axis=0, keepdims=True).astype(np.float32)
    std = x[train_mask].std(axis=0, keepdims=True).astype(np.float32)
    std = np.maximum(std, 1.0e-6)
    return ((x - mean) / std).astype(np.float32), mean.reshape(-1), std.reshape(-1)


def _loader(x: np.ndarray, y: np.ndarray, mask: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    ds = TensorDataset(torch.from_numpy(x[mask]), torch.from_numpy(y[mask]))
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle, drop_last=False)


@torch.no_grad()
def _evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    loss_sum = 0.0
    elem_count = 0
    sample_mse_sum = 0.0
    sample_count = 0
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        pred = model(x)
        sq = (pred - y).square()
        loss_sum += float(sq.sum().item())
        elem_count += int(sq.numel())
        sample_mse_sum += float(sq.mean(dim=1).sum().item())
        sample_count += int(y.shape[0])
    return {
        "mse": loss_sum / max(elem_count, 1),
        "sample_mse": sample_mse_sum / max(sample_count, 1),
        "count": float(sample_count),
    }


@torch.no_grad()
def _predict(model: nn.Module, x: np.ndarray, mask: np.ndarray, device: torch.device) -> np.ndarray:
    model.eval()
    xb = torch.from_numpy(x[mask]).to(device)
    outs: list[np.ndarray] = []
    for start in range(0, xb.shape[0], 4096):
        outs.append(model(xb[start : start + 4096]).cpu().numpy())
    return np.concatenate(outs, axis=0)


def train(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.out_dir.expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    with np.load(args.dataset.expanduser(), allow_pickle=False) as data:
        codes = np.asarray(data["codes"], dtype=np.int64)
        num_codes = int(args.num_codes or (int(codes.max()) + 1))
        x_raw, feature_keys = _build_features(data, args.feature_group, num_codes)
        theta_raw = np.asarray(data["theta"], dtype=np.float32)
        groups = np.asarray(data[args.split_group]).astype(str)

    train_mask, val_mask, test_mask = _group_split(groups, args.train_frac, args.val_frac, args.seed)
    x, x_mean, x_std = _standardize(x_raw, train_mask)
    theta, theta_mean, theta_std = _standardize(theta_raw, train_mask)

    device = torch.device(args.device)
    model = ThetaMLP(x.shape[1], theta.shape[1], args.hidden_dim, args.depth, args.dropout).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    criterion = nn.SmoothL1Loss(beta=args.huber_beta)

    train_loader = _loader(x, theta, train_mask, args.batch_size, shuffle=True)
    val_loader = _loader(x, theta, val_mask, args.batch_size, shuffle=False)
    test_loader = _loader(x, theta, test_mask, args.batch_size, shuffle=False)

    # Baseline predicts train-set per-code theta mean.
    code_mean = np.zeros((num_codes, theta_raw.shape[1]), dtype=np.float32)
    global_mean = theta_raw[train_mask].mean(axis=0).astype(np.float32)
    for code in range(num_codes):
        mask = train_mask & (codes == code)
        code_mean[code] = theta_raw[mask].mean(axis=0) if np.any(mask) else global_mean

    best_val = float("inf")
    best_state: dict[str, torch.Tensor] | None = None
    last_metrics: dict[str, float] = {}

    for epoch in range(1, args.steps + 1):
        model.train()
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            pred = model(xb)
            loss = criterion(pred, yb)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        if epoch == 1 or epoch % args.eval_every == 0 or epoch == args.steps:
            train_m = _evaluate(model, train_loader, device)
            val_m = _evaluate(model, val_loader, device)
            last_metrics = {
                "epoch": float(epoch),
                "train_mse_norm": train_m["mse"],
                "val_mse_norm": val_m["mse"],
            }
            print(
                f"epoch={epoch} train_mse_norm={train_m['mse']:.5f} val_mse_norm={val_m['mse']:.5f}",
                flush=True,
            )
            if val_m["mse"] < best_val:
                best_val = val_m["mse"]
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    train_m = _evaluate(model, train_loader, device)
    val_m = _evaluate(model, val_loader, device)
    test_m = _evaluate(model, test_loader, device)

    pred_test_norm = _predict(model, x, test_mask, device)
    pred_test = pred_test_norm * theta_std[None, :] + theta_mean[None, :]
    true_test = theta_raw[test_mask]
    test_codes = codes[test_mask]
    baseline = code_mean[test_codes]
    test_theta_mse = float(np.mean((pred_test - true_test) ** 2))
    baseline_theta_mse = float(np.mean((baseline - true_test) ** 2))

    per_code: dict[str, dict[str, float]] = {}
    for code in np.flatnonzero(np.bincount(test_codes, minlength=num_codes)):
        mask = test_codes == code
        per_code[str(int(code))] = {
            "count": int(mask.sum()),
            "theta_mse": float(np.mean((pred_test[mask] - true_test[mask]) ** 2)),
            "baseline_theta_mse": float(np.mean((baseline[mask] - true_test[mask]) ** 2)),
        }

    torch.save(
        {
            "model_state": model.state_dict(),
            "model_config": {
                "input_dim": int(x.shape[1]),
                "theta_dim": int(theta.shape[1]),
                "hidden_dim": args.hidden_dim,
                "depth": args.depth,
                "dropout": args.dropout,
                "num_codes": num_codes,
            },
            "feature_groups": args.feature_group,
            "feature_keys": feature_keys,
            "x_norm": {"mean": x_mean, "std": x_std},
            "theta_norm": {"mean": theta_mean, "std": theta_std},
            "code_theta_mean": code_mean,
            "dataset": str(args.dataset),
            "split_group": args.split_group,
        },
        out_dir / "checkpoint.pt",
    )
    np.save(out_dir / "test_theta_pred.npy", pred_test)
    np.save(out_dir / "test_theta_true.npy", true_test)
    np.save(out_dir / "test_codes.npy", test_codes)

    summary = {
        "dataset": str(args.dataset),
        "feature_groups": args.feature_group,
        "feature_keys": feature_keys,
        "input_dim": int(x.shape[1]),
        "theta_dim": int(theta.shape[1]),
        "num_codes": num_codes,
        "train_count": int(train_mask.sum()),
        "val_count": int(val_mask.sum()),
        "test_count": int(test_mask.sum()),
        "train_mse_norm": train_m["mse"],
        "val_mse_norm": val_m["mse"],
        "test_mse_norm": test_m["mse"],
        "best_val_mse_norm": best_val,
        "test_theta_mse": test_theta_mse,
        "baseline_theta_mse": baseline_theta_mse,
        "theta_mse_improvement": baseline_theta_mse / max(test_theta_mse, 1.0e-12),
        "per_code": per_code,
        "last_metrics": last_metrics,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--feature-group", action="append", default=None, choices=sorted(FEATURE_GROUPS))
    parser.add_argument("--split-group", default="raw_clip_paths")
    parser.add_argument("--num-codes", type=int, default=16)
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--val-frac", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--hidden-dim", type=int, default=512)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--eval-every", type=int, default=5)
    parser.add_argument("--lr", type=float, default=3.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--huber-beta", type=float, default=0.5)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    if args.feature_group is None:
        args.feature_group = ["height", "root", "joint"]
    return args


def main() -> None:
    train(parse_args())


if __name__ == "__main__":
    main()
