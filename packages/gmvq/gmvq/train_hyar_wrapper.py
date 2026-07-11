from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from .data import load_contact_force_provenance, make_synthetic_segments
from .hyar_wrapper import (
    FrozenGMVQCodec,
    HyARActionVAE,
    HyARLossWeights,
    HyARNestedAutoEncoder,
    compute_hyar_loss,
)
from somaforge_core.robot_assets import decode_robot_asset_json


@dataclass
class HyARDatasetItem:
    x: torch.Tensor
    state: Optional[torch.Tensor] = None
    next_state: Optional[torch.Tensor] = None


class HyARSegmentDataset(Dataset[HyARDatasetItem]):
    def __init__(
        self,
        segments: torch.Tensor,
        states: Optional[torch.Tensor] = None,
        next_states: Optional[torch.Tensor] = None,
    ) -> None:
        if segments.ndim != 3:
            raise ValueError(f"segments must have shape [N, T, D], got {tuple(segments.shape)}")
        n = segments.shape[0]
        if states is not None and states.shape[0] != n:
            raise ValueError("states and segments must have the same leading dimension")
        if next_states is not None and next_states.shape[0] != n:
            raise ValueError("next_states and segments must have the same leading dimension")
        self.segments = segments.float()
        self.states = None if states is None else states.float()
        self.next_states = None if next_states is None else next_states.float()

    def __len__(self) -> int:
        return self.segments.shape[0]

    def __getitem__(self, idx: int) -> HyARDatasetItem:
        state = None if self.states is None else self.states[idx]
        next_state = None if self.next_states is None else self.next_states[idx]
        return HyARDatasetItem(self.segments[idx], state, next_state)


def collate_items(items: list[HyARDatasetItem]) -> dict[str, Optional[torch.Tensor]]:
    batch: dict[str, Optional[torch.Tensor]] = {"x": torch.stack([it.x for it in items], dim=0)}
    if items[0].state is not None:
        batch["state"] = torch.stack([it.state for it in items if it.state is not None], dim=0)
    else:
        batch["state"] = None
    if items[0].next_state is not None:
        batch["next_state"] = torch.stack([it.next_state for it in items if it.next_state is not None], dim=0)
    else:
        batch["next_state"] = None
    return batch


def load_hyar_arrays(
    path: str | Path,
    state_key: str = "states",
    next_state_key: str = "next_states",
) -> tuple[torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
    path = Path(path)
    if path.suffix == ".npz":
        obj = np.load(path)
        value = obj["robot_asset_json"] if "robot_asset_json" in obj.files else None
        decode_robot_asset_json(value, context=f"HyAR dataset {path}")
        seg_key = "segments" if "segments" in obj.files else obj.files[0]
        segments = torch.from_numpy(obj[seg_key]).float()
        states = torch.from_numpy(obj[state_key]).float() if state_key in obj.files else None
        next_states = torch.from_numpy(obj[next_state_key]).float() if next_state_key in obj.files else None
        return segments, states, next_states

    if path.suffix == ".pt":
        obj = torch.load(path, map_location="cpu", weights_only=False)
        if torch.is_tensor(obj):
            return obj.float(), None, None
        if not isinstance(obj, dict):
            raise ValueError(".pt data must be a tensor or dict")
        seg = None
        for key in ("segments", "x", "data"):
            if key in obj:
                seg = obj[key]
                break
        if seg is None:
            raise ValueError(".pt dict must contain one of: segments, x, data")
        states = obj.get(state_key)
        next_states = obj.get(next_state_key)
        return (
            torch.as_tensor(seg).float(),
            None if states is None else torch.as_tensor(states).float(),
            None if next_states is None else torch.as_tensor(next_states).float(),
        )

    raise ValueError(f"unsupported data suffix: {path.suffix}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train a HyAR wrapper on top of a frozen residual GMVQ tokenizer.")
    p.add_argument("--gmvq_checkpoint", type=str, required=True)
    p.add_argument("--data", type=str, default=None)
    p.add_argument("--synthetic", action="store_true")
    p.add_argument("--save_dir", type=str, default="runs/hyar_wrapper")
    p.add_argument("--hyar_latent_dim", type=int, default=4)
    p.add_argument("--action_emb_dim", type=int, default=16)
    p.add_argument("--hidden_dim", type=int, default=128)
    p.add_argument("--batch_size", type=int, default=256)
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--use_state_conditioning", action="store_true")
    p.add_argument("--state_key", type=str, default="states")
    p.add_argument("--next_state_key", type=str, default="next_states")
    p.add_argument("--beta_kl", type=float, default=1e-3)
    p.add_argument("--beta_x", type=float, default=1.0)
    p.add_argument("--beta_vel", type=float, default=0.1)
    p.add_argument("--beta_k", type=float, default=0.1)
    p.add_argument("--beta_dyn", type=float, default=0.1)
    p.add_argument("--beta_latent", type=float, default=0.0)
    p.add_argument("--synthetic_n", type=int, default=4096)
    p.add_argument("--log_every", type=int, default=100)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    codec = FrozenGMVQCodec(args.gmvq_checkpoint, device=args.device, trainable=False)

    if args.data:
        dataset_contact_provenance = load_contact_force_provenance(args.data)
        if dataset_contact_provenance["solver_config_sha256"] != codec.contact_force_provenance["solver_config_sha256"]:
            raise ValueError("HyAR dataset and GMVQ checkpoint use different Newton solver fingerprints")
        segments, states, next_states = load_hyar_arrays(args.data, args.state_key, args.next_state_key)
    elif args.synthetic:
        segments, _ = make_synthetic_segments(n=args.synthetic_n, t=codec.t, d=codec.d)
        states = None
        next_states = None
    else:
        raise ValueError("provide --data or --synthetic; real data is recommended for a frozen GMVQ checkpoint")

    if segments.shape[1:] != (codec.t, codec.d):
        raise ValueError(f"data shape {tuple(segments.shape[1:])} does not match GMVQ shape {(codec.t, codec.d)}")

    segments = codec.normalize(segments)
    state_dim = int(states.shape[-1]) if args.use_state_conditioning and states is not None else None
    if args.use_state_conditioning and states is None:
        raise ValueError("--use_state_conditioning requires states in the dataset")

    dataset = HyARSegmentDataset(segments, states, next_states)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, collate_fn=collate_items)
    iterator = iter(loader)

    hyar = HyARActionVAE(
        num_codes=codec.num_codes,
        theta_dim=codec.theta_dim,
        action_emb_dim=args.action_emb_dim,
        hyar_latent_dim=args.hyar_latent_dim,
        state_dim=state_dim,
        hidden_dim=args.hidden_dim,
        use_state_conditioning=args.use_state_conditioning,
        use_k_classifier=True,
    ).to(args.device)
    nested = HyARNestedAutoEncoder(codec, hyar).to(args.device)
    weights = HyARLossWeights(
        beta_kl=args.beta_kl,
        beta_x=args.beta_x,
        beta_vel=args.beta_vel,
        beta_k=args.beta_k,
        beta_dyn=args.beta_dyn,
        beta_latent=args.beta_latent,
    )
    opt = torch.optim.AdamW(hyar.parameters(), lr=args.lr)
    last_metrics: dict[str, torch.Tensor] = {}

    for step in range(1, args.steps + 1):
        try:
            batch = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            batch = next(iterator)

        x = batch["x"].to(args.device)
        state = None if batch["state"] is None else batch["state"].to(args.device)
        next_state = None if batch["next_state"] is None else batch["next_state"].to(args.device)

        out = nested(x, state)
        loss, metrics = compute_hyar_loss(x, out, weights, next_state=next_state)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(hyar.parameters(), 1.0)
        opt.step()
        last_metrics = metrics

        if step == 1 or step % args.log_every == 0 or step == args.steps:
            items = " ".join(f"{k}={float(v):.4f}" for k, v in metrics.items())
            print(f"step={step} {items}", flush=True)

    ckpt = {
        "hyar_state": hyar.state_dict(),
        "hyar_config": hyar.config(),
        "gmvq_checkpoint": str(Path(args.gmvq_checkpoint)),
        "train_args": vars(args),
        "last_metrics": {k: v.cpu() for k, v in last_metrics.items()},
        "robot_asset": codec.robot_asset,
        "contact_force_provenance": codec.contact_force_provenance,
    }
    torch.save(ckpt, save_dir / "checkpoint.pt")
    with (save_dir / "config.json").open("w", encoding="utf-8") as f:
        json.dump({**vars(args), **hyar.config()}, f, indent=2)
    print(f"saved checkpoint: {save_dir / 'checkpoint.pt'}")


if __name__ == "__main__":
    main()
