from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from .hyar_wrapper import FrozenGMVQCodec, HyARActionVAE, HyARNestedAutoEncoder
from .train_hyar_wrapper import HyARSegmentDataset, collate_items, load_hyar_arrays


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze a trained HyAR wrapper over residual GMVQ codes.")
    p.add_argument("--gmvq_checkpoint", type=str, default=None)
    p.add_argument("--hyar_checkpoint", type=str, required=True)
    p.add_argument("--data", type=str, required=True)
    p.add_argument("--out_dir", type=str, default=None)
    p.add_argument("--batch_size", type=int, default=256)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--state_key", type=str, default="states")
    p.add_argument("--next_state_key", type=str, default="next_states")
    return p.parse_args()


def maybe_plot(out_dir: Path, z_h: np.ndarray, k: np.ndarray, theta: np.ndarray, theta_hat: np.ndarray) -> None:
    try:
        import matplotlib.pyplot as plt
        from sklearn.decomposition import PCA
    except Exception:
        return

    if z_h.shape[0] >= 2:
        xy = PCA(n_components=2).fit_transform(z_h)
        plt.figure(figsize=(5, 5))
        plt.scatter(xy[:, 0], xy[:, 1], c=k, s=6, cmap="tab10")
        plt.tight_layout()
        plt.savefig(out_dir / "z_h_pca_by_k.png", dpi=160)
        plt.close()

    if theta.size and theta_hat.size:
        plt.figure(figsize=(5, 5))
        plt.scatter(theta.reshape(-1), theta_hat.reshape(-1), s=3, alpha=0.25)
        lo = min(float(theta.min()), float(theta_hat.min()))
        hi = max(float(theta.max()), float(theta_hat.max()))
        plt.plot([lo, hi], [lo, hi], color="black", linewidth=1)
        plt.tight_layout()
        plt.savefig(out_dir / "theta_vs_theta_hat.png", dpi=160)
        plt.close()

    err = ((theta_hat - theta) ** 2).mean(axis=1)
    plt.figure(figsize=(8, 3))
    for code in np.unique(k):
        plt.hist(err[k == code], bins=40, alpha=0.45, label=f"k={int(code)}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "per_code_theta_error_hist.png", dpi=160)
    plt.close()


def main() -> None:
    args = parse_args()
    hyar_ckpt_path = Path(args.hyar_checkpoint)
    hyar_ckpt = torch.load(hyar_ckpt_path, map_location="cpu", weights_only=False)
    gmvq_checkpoint = args.gmvq_checkpoint or hyar_ckpt["gmvq_checkpoint"]
    out_dir = Path(args.out_dir) if args.out_dir else hyar_ckpt_path.parent / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    codec = FrozenGMVQCodec(gmvq_checkpoint, device=args.device, trainable=False)
    cfg = hyar_ckpt["hyar_config"]
    hyar = HyARActionVAE(**cfg).to(args.device)
    hyar.load_state_dict(hyar_ckpt["hyar_state"])
    hyar.eval()
    nested = HyARNestedAutoEncoder(codec, hyar).to(args.device)
    nested.eval()

    segments, states, next_states = load_hyar_arrays(args.data, args.state_key, args.next_state_key)
    segments = codec.normalize(segments)
    dataset = HyARSegmentDataset(segments, states, next_states)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, collate_fn=collate_items)

    all_k: list[torch.Tensor] = []
    all_theta: list[torch.Tensor] = []
    all_z_h: list[torch.Tensor] = []
    all_theta_hat: list[torch.Tensor] = []
    all_k_logits: list[torch.Tensor] = []
    x_hat_subset: list[torch.Tensor] = []
    theta_sse = 0.0
    theta_count = 0
    x_sse = 0.0
    x_count = 0
    vel_sse = 0.0
    vel_count = 0
    kl_sum = 0.0
    n = 0
    correct_k = 0

    with torch.no_grad():
        for batch in loader:
            x = batch["x"].to(args.device)
            state = None if batch["state"] is None else batch["state"].to(args.device)
            out = nested(x, state)

            all_k.append(out["k"].cpu())
            all_theta.append(out["theta"].cpu())
            all_z_h.append(out["z_h"].cpu())
            all_theta_hat.append(out["theta_hat"].cpu())
            if "k_logits" in out:
                all_k_logits.append(out["k_logits"].cpu())
                correct_k += int((out["k_logits"].argmax(dim=-1) == out["k"]).sum().item())
            if len(x_hat_subset) < 4:
                x_hat_subset.append(out["x_hat"][: min(16, x.shape[0])].cpu())

            theta_sse += F.mse_loss(out["theta_hat"], out["theta"], reduction="sum").item()
            theta_count += out["theta"].numel()
            x_sse += F.mse_loss(out["x_hat"], x, reduction="sum").item()
            x_count += x.numel()
            if x.shape[1] > 1:
                v_hat = out["x_hat"][:, 1:] - out["x_hat"][:, :-1]
                v = x[:, 1:] - x[:, :-1]
                vel_sse += F.mse_loss(v_hat, v, reduction="sum").item()
                vel_count += v.numel()
            kl = -0.5 * (1.0 + out["z_logvar"] - out["z_mu"].square() - out["z_logvar"].exp()).sum(dim=-1)
            kl_sum += float(kl.sum().item())
            n += x.shape[0]

    k_t = torch.cat(all_k, dim=0)
    theta_t = torch.cat(all_theta, dim=0)
    z_h_t = torch.cat(all_z_h, dim=0)
    theta_hat_t = torch.cat(all_theta_hat, dim=0)
    x_hat_t = torch.cat(x_hat_subset, dim=0)[:64]

    np.save(out_dir / "k.npy", k_t.numpy())
    np.save(out_dir / "theta.npy", theta_t.numpy())
    np.save(out_dir / "z_h.npy", z_h_t.numpy())
    np.save(out_dir / "theta_hat.npy", theta_hat_t.numpy())
    np.save(out_dir / "x_hat_subset.npy", x_hat_t.numpy())
    if all_k_logits:
        np.save(out_dir / "k_logits.npy", torch.cat(all_k_logits, dim=0).numpy())

    print(f"theta reconstruction MSE: {theta_sse / max(theta_count, 1):.6f}")
    print(f"full segment reconstruction MSE: {x_sse / max(x_count, 1):.6f}")
    print(f"velocity MSE: {vel_sse / max(vel_count, 1):.6f}")
    print(f"KL: {kl_sum / max(n, 1):.6f}")
    if all_k_logits:
        print(f"k classifier accuracy: {correct_k / max(n, 1):.4f}")

    k_np = k_t.numpy()
    theta_np = theta_t.numpy()
    theta_hat_np = theta_hat_t.numpy()
    for code in range(codec.num_codes):
        mask = k_np == code
        if not mask.any():
            continue
        theta_mse = float(((theta_hat_np[mask] - theta_np[mask]) ** 2).mean())
        print(f"code={code} n={int(mask.sum())} theta_mse={theta_mse:.6f}")

    maybe_plot(out_dir, z_h_t.numpy(), k_np, theta_np, theta_hat_np)
    print(f"saved HyAR analysis arrays: {out_dir}")


if __name__ == "__main__":
    main()
