#!/usr/bin/env python3
"""Train an offline selector from height/proprio observations to GMVQ code."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from somaforge_core.robot_assets import decode_robot_asset_json


FEATURE_GROUPS = {
    "height": ("height_scan",),
    "root": ("root_pos_w", "root_quat_w", "root_lin_vel_w", "root_ang_vel_w"),
    "joint": ("joint_pos", "joint_vel"),
}


class SelectorMLP(nn.Module):
    def __init__(self, input_dim: int, num_codes: int, hidden_dim: int, depth: int, dropout: float) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        dim = input_dim
        for _ in range(depth):
            layers += [nn.Linear(dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU()]
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            dim = hidden_dim
        layers.append(nn.Linear(dim, num_codes))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def _flatten(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    return arr.reshape(arr.shape[0], -1)


def _build_features(data: np.lib.npyio.NpzFile, groups: list[str]) -> tuple[np.ndarray, list[str]]:
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
    train = np.asarray([x in train_groups for x in group_str])
    val = np.asarray([x in val_groups for x in group_str])
    test = np.asarray([x in test_groups for x in group_str])
    return train, val, test


def _standardize(x: np.ndarray, train_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x[train_mask].mean(axis=0, keepdims=True).astype(np.float32)
    std = x[train_mask].std(axis=0, keepdims=True).astype(np.float32)
    std = np.maximum(std, 1.0e-6)
    return ((x - mean) / std).astype(np.float32), mean.reshape(-1), std.reshape(-1)


def _loader(x: np.ndarray, y: np.ndarray, mask: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    ds = TensorDataset(torch.from_numpy(x[mask]), torch.from_numpy(y[mask]).long())
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle, drop_last=False)


@torch.no_grad()
def _evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, float]:
    model.eval()
    total = 0
    correct = 0
    loss_sum = 0.0
    ce = nn.CrossEntropyLoss(reduction="sum")
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        logits = model(x)
        loss_sum += float(ce(logits, y).item())
        pred = logits.argmax(dim=1)
        correct += int((pred == y).sum().item())
        total += int(y.numel())
    return {
        "loss": loss_sum / max(total, 1),
        "acc": correct / max(total, 1),
        "count": float(total),
    }


@torch.no_grad()
def _confusion(model: nn.Module, x: np.ndarray, y: np.ndarray, mask: np.ndarray, num_codes: int, device: torch.device) -> np.ndarray:
    model.eval()
    conf = np.zeros((num_codes, num_codes), dtype=np.int64)
    xb = torch.from_numpy(x[mask]).to(device)
    yb = torch.from_numpy(y[mask]).long().to(device)
    for start in range(0, xb.shape[0], 4096):
        logits = model(xb[start : start + 4096])
        pred = logits.argmax(dim=1)
        true = yb[start : start + 4096]
        for t, p in zip(true.cpu().numpy(), pred.cpu().numpy()):
            conf[int(t), int(p)] += 1
    return conf


def train(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.out_dir.expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    with np.load(args.dataset.expanduser(), allow_pickle=False) as data:
        value = data["robot_asset_json"] if "robot_asset_json" in data.files else None
        robot_asset = decode_robot_asset_json(value, context=f"selector dataset {args.dataset}")
        x_raw, feature_keys = _build_features(data, args.feature_group)
        y = np.asarray(data["codes"], dtype=np.int64)
        groups = np.asarray(data[args.split_group]).astype(str)

    num_codes = int(args.num_codes or (int(y.max()) + 1))
    train_mask, val_mask, test_mask = _group_split(groups, args.train_frac, args.val_frac, args.seed)
    x, mean, std = _standardize(x_raw, train_mask)

    device = torch.device(args.device)
    model = SelectorMLP(
        input_dim=x.shape[1],
        num_codes=num_codes,
        hidden_dim=args.hidden_dim,
        depth=args.depth,
        dropout=args.dropout,
    ).to(device)

    hist = np.bincount(y[train_mask], minlength=num_codes).astype(np.float32)
    weights = np.zeros_like(hist)
    active = hist > 0
    weights[active] = hist[active].sum() / (active.sum() * hist[active])
    weights = np.clip(weights, 0.0, args.max_class_weight)
    criterion = nn.CrossEntropyLoss(weight=torch.from_numpy(weights).float().to(device))
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    train_loader = _loader(x, y, train_mask, args.batch_size, shuffle=True)
    val_loader = _loader(x, y, val_mask, args.batch_size, shuffle=False)
    test_loader = _loader(x, y, test_mask, args.batch_size, shuffle=False)

    best_val = -1.0
    best_state: dict[str, torch.Tensor] | None = None
    last_metrics: dict[str, float] = {}

    for step in range(1, args.steps + 1):
        model.train()
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            logits = model(xb)
            loss = criterion(logits, yb)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()

        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            train_m = _evaluate(model, train_loader, device)
            val_m = _evaluate(model, val_loader, device)
            last_metrics = {
                "epoch": float(step),
                "train_loss": train_m["loss"],
                "train_acc": train_m["acc"],
                "val_loss": val_m["loss"],
                "val_acc": val_m["acc"],
            }
            print(
                f"epoch={step} train_loss={train_m['loss']:.4f} train_acc={train_m['acc']:.4f} "
                f"val_loss={val_m['loss']:.4f} val_acc={val_m['acc']:.4f}",
                flush=True,
            )
            if val_m["acc"] > best_val:
                best_val = val_m["acc"]
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    train_m = _evaluate(model, train_loader, device)
    val_m = _evaluate(model, val_loader, device)
    test_m = _evaluate(model, test_loader, device)
    conf = _confusion(model, x, y, test_mask, num_codes, device)

    ckpt = {
        "model_state": model.state_dict(),
        "model_config": {
            "input_dim": int(x.shape[1]),
            "num_codes": num_codes,
            "hidden_dim": args.hidden_dim,
            "depth": args.depth,
            "dropout": args.dropout,
        },
        "feature_groups": args.feature_group,
        "feature_keys": feature_keys,
        "norm": {"mean": mean, "std": std},
        "class_weights": weights,
        "dataset": str(args.dataset),
        "split_group": args.split_group,
        "robot_asset": robot_asset,
    }
    torch.save(ckpt, out_dir / "checkpoint.pt")
    np.save(out_dir / "test_confusion.npy", conf)

    summary = {
        "dataset": str(args.dataset),
        "feature_groups": args.feature_group,
        "feature_keys": feature_keys,
        "input_dim": int(x.shape[1]),
        "num_codes": num_codes,
        "train_count": int(train_mask.sum()),
        "val_count": int(val_mask.sum()),
        "test_count": int(test_mask.sum()),
        "train_acc": train_m["acc"],
        "val_acc": val_m["acc"],
        "test_acc": test_m["acc"],
        "train_loss": train_m["loss"],
        "val_loss": val_m["loss"],
        "test_loss": test_m["loss"],
        "best_val_acc": best_val,
        "last_metrics": last_metrics,
        "code_hist": [int(v) for v in np.bincount(y, minlength=num_codes).tolist()],
        "test_confusion": conf.tolist(),
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
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--steps", type=int, default=80, help="Epoch count over the offline dataset.")
    parser.add_argument("--eval-every", type=int, default=5)
    parser.add_argument("--lr", type=float, default=3.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--max-class-weight", type=float, default=8.0)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    if args.feature_group is None:
        args.feature_group = ["height", "root", "joint"]
    return args


def main() -> None:
    train(parse_args())


if __name__ == "__main__":
    main()
