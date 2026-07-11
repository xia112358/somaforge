from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import torch
from torch.utils.data import DataLoader
from somaforge_core import stage_spec

from .data import build_dataset, load_contact_force_provenance, load_robot_asset_metadata
from .losses import compute_loss
from .models import GMVQAutoEncoder


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train a GMVQ-style atom-skill tokenizer.")
    p.add_argument("--data", type=str, default=None)
    p.add_argument("--synthetic", action="store_true")
    p.add_argument("--save_dir", type=str, default="runs/gmvq")
    p.add_argument("--num_codes", type=int, default=64)
    p.add_argument("--latent_dim", type=int, default=32)
    p.add_argument(
        "--encoder_type",
        choices=["mlp", "conv1d", "conv1d_masked", "tcn_masked", "bigru_masked", "transformer_masked"],
        default="mlp",
    )
    p.add_argument("--decoder_type", choices=["latent", "factorized", "time"], default="latent")
    p.add_argument("--assignment", choices=["hard", "soft"], default="hard")
    p.add_argument("--batch_size", type=int, default=128)
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--theta_mode", choices=["clipped", "stopgrad", "none", "sample"], default="clipped")
    p.add_argument("--theta_clip", type=float, default=2.0)
    p.add_argument("--sigma_min", type=float, default=0.05)
    p.add_argument("--sigma_max", type=float, default=1.0)
    p.add_argument("--use_ste", action="store_true", default=True)
    p.add_argument("--no_use_ste", dest="use_ste", action="store_false")
    p.add_argument("--prior_mode", choices=["learned", "uniform"], default="learned")
    p.add_argument("--target_bits", type=float, default=4.0)
    p.add_argument("--t", type=int, default=120)
    p.add_argument("--d", type=int, default=14)
    p.add_argument("--synthetic_n", type=int, default=4096)
    p.add_argument("--log_every", type=int, default=100)

    p.add_argument("--beta_theta", type=float, default=0.01)
    p.add_argument("--beta_rate", type=float, default=0.01)
    p.add_argument("--beta_commit", type=float, default=0.25)
    p.add_argument("--beta_usage", type=float, default=0.01)
    p.add_argument("--beta_sigma", type=float, default=0.001)
    p.add_argument("--beta_vel", type=float, default=0.1)
    p.add_argument("--beta_mix", type=float, default=0.05)
    p.add_argument("--beta_balance", type=float, default=0.01)
    p.add_argument("--beta_sep", type=float, default=0.001)
    p.add_argument("--beta_theta_moments", type=float, default=0.01)
    p.add_argument("--beta_length", type=float, default=0.05)
    p.add_argument("--sep_tau", type=float, default=1.0)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    stage_spec("gmvq")
    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    dataset, stats = build_dataset(
        args.data,
        args.synthetic,
        synthetic_n=args.synthetic_n,
        t=args.t,
        d=args.d,
    )
    robot_asset = None if args.synthetic else load_robot_asset_metadata(args.data)
    contact_force_provenance = None if args.synthetic else load_contact_force_provenance(args.data)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=False)
    iterator = iter(loader)

    model = GMVQAutoEncoder(
        t=dataset.segments.shape[1],
        d=dataset.segments.shape[2],
        latent_dim=args.latent_dim,
        num_codes=args.num_codes,
        encoder_type=args.encoder_type,
        decoder_type=args.decoder_type,
        assignment=args.assignment,
        use_ste=args.use_ste,
        theta_mode=args.theta_mode,
        theta_clip=args.theta_clip,
        sigma_min=args.sigma_min,
        sigma_max=args.sigma_max,
        prior_mode=args.prior_mode,
    ).to(args.device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)

    cfg = SimpleNamespace(**vars(args))
    last_metrics: dict[str, torch.Tensor] = {}
    uses_valid_mask = hasattr(dataset, "valid_mask")
    for step in range(1, args.steps + 1):
        try:
            batch = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            batch = next(iterator)
        if isinstance(batch, dict):
            x = batch["x"]
            valid_mask = batch.get("valid_mask")
            lengths = batch.get("lengths")
        else:
            x = batch
            valid_mask = None
            lengths = None
        x = x.to(args.device)
        valid_mask = None if valid_mask is None else valid_mask.to(args.device)
        lengths = None if lengths is None else lengths.to(args.device)

        output = model(x, valid_mask=valid_mask, lengths=lengths)
        loss, metrics = compute_loss(x, output, model, cfg, valid_mask=valid_mask, lengths=lengths)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        last_metrics = metrics

        if step == 1 or step % args.log_every == 0 or step == args.steps:
            items = " ".join(
                f"{k}={float(v):.4f}"
                for k, v in metrics.items()
                if k not in {"active_codes"}
            )
            print(f"step={step} active_codes={int(metrics['active_codes'])} {items}", flush=True)

    ckpt = {
        "model_state": model.state_dict(),
        "model_config": model.config(),
        "train_args": vars(args),
        "uses_valid_mask": uses_valid_mask,
        "norm_stats": None if stats is None else {"mean": stats.mean.cpu(), "std": stats.std.cpu()},
        "last_metrics": {k: v.cpu() for k, v in last_metrics.items()},
        "robot_asset": robot_asset,
        "contact_force_provenance": contact_force_provenance,
    }
    torch.save(ckpt, save_dir / "checkpoint.pt")
    with (save_dir / "config.json").open("w", encoding="utf-8") as f:
        json.dump(vars(args) | model.config(), f, indent=2)
    if stats is not None:
        torch.save({"mean": stats.mean.cpu(), "std": stats.std.cpu()}, save_dir / "norm_stats.pt")
    print(f"saved checkpoint: {save_dir / 'checkpoint.pt'}")


if __name__ == "__main__":
    main()
