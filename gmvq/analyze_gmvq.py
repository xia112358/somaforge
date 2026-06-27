from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .data import NormStats, SegmentDataset, build_dataset, load_segments, normalize_segments
from .losses import code_usage_stats
from .models import GMVQAutoEncoder


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze a trained GMVQ tokenizer.")
    p.add_argument("--checkpoint", type=str, required=True)
    p.add_argument("--data", type=str, default=None)
    p.add_argument("--synthetic", action="store_true")
    p.add_argument("--out_dir", type=str, default=None)
    p.add_argument("--batch_size", type=int, default=256)
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--synthetic_n", type=int, default=4096)
    return p.parse_args()


def maybe_plot(out_dir: Path, codes: np.ndarray, theta: np.ndarray, num_codes: int) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    hist = np.bincount(codes, minlength=num_codes)
    plt.figure(figsize=(9, 3))
    plt.bar(np.arange(num_codes), hist)
    plt.xlabel("code")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_dir / "code_usage.png", dpi=160)
    plt.close()

    try:
        from sklearn.decomposition import PCA
    except Exception:
        return

    if theta.shape[0] >= 2:
        xy = PCA(n_components=2).fit_transform(theta)
        plt.figure(figsize=(5, 5))
        plt.scatter(xy[:, 0], xy[:, 1], c=codes, s=5, cmap="tab20")
        plt.tight_layout()
        plt.savefig(out_dir / "theta_pca.png", dpi=160)
        plt.close()


def main() -> None:
    args = parse_args()
    ckpt_path = Path(args.checkpoint)
    ckpt = torch.load(ckpt_path, map_location="cpu")
    cfg = ckpt["model_config"]
    out_dir = Path(args.out_dir) if args.out_dir else ckpt_path.parent / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.data:
        segments = load_segments(args.data)
        ns = ckpt.get("norm_stats")
        stats = NormStats(mean=ns["mean"], std=ns["std"]) if ns is not None else None
        segments, _ = normalize_segments(segments, stats=stats)
        dataset = SegmentDataset(segments)
    else:
        dataset, _ = build_dataset(
            data=None,
            synthetic=args.synthetic,
            synthetic_n=args.synthetic_n,
            t=cfg.get("t", 120),
            d=cfg.get("d", 14),
        )

    model = GMVQAutoEncoder(**cfg).to(args.device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    all_codes: list[torch.Tensor] = []
    all_theta: list[torch.Tensor] = []
    all_z_e: list[torch.Tensor] = []
    all_z_q: list[torch.Tensor] = []
    recon_subset: list[torch.Tensor] = []
    mse_sum = 0.0
    count = 0

    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)
    with torch.no_grad():
        for x in loader:
            x = x.to(args.device)
            out = model(x)
            all_codes.append(out["codes"].cpu())
            all_theta.append(out["theta"].cpu())
            all_z_e.append(out["z_e"].cpu())
            all_z_q.append(out["z_q"].cpu())
            if len(recon_subset) < 4:
                recon_subset.append(out["x_recon"][: min(16, x.shape[0])].cpu())
            mse_sum += torch.nn.functional.mse_loss(out["x_recon"], x, reduction="sum").item()
            count += x.numel()

    codes_t = torch.cat(all_codes, dim=0)
    theta_t = torch.cat(all_theta, dim=0)
    z_e_t = torch.cat(all_z_e, dim=0)
    z_q_t = torch.cat(all_z_q, dim=0)
    recon_t = torch.cat(recon_subset, dim=0)[:64]

    np.save(out_dir / "codes.npy", codes_t.numpy())
    np.save(out_dir / "theta.npy", theta_t.numpy())
    np.save(out_dir / "z_e.npy", z_e_t.numpy())
    np.save(out_dir / "z_q.npy", z_q_t.numpy())
    np.save(out_dir / "recon_subset.npy", recon_t.numpy())

    usage = code_usage_stats(codes_t, cfg["num_codes"])
    print("code usage histogram:")
    print(usage["hist"].long().tolist())
    print(f"active code count: {int(usage['active_codes'])}")
    print(f"perplexity: {float(usage['perplexity']):.4f}")
    print(f"reconstruction MSE: {mse_sum / max(count, 1):.6f}")
    for code in range(cfg["num_codes"]):
        mask = codes_t == code
        if bool(mask.any()):
            th = theta_t[mask]
            print(f"code={code} n={int(mask.sum())} theta_mean={th.mean(0).mean():.4f} theta_std={th.std(0).mean():.4f}")

    maybe_plot(out_dir, codes_t.numpy(), theta_t.numpy(), cfg["num_codes"])
    print(f"saved analysis arrays: {out_dir}")


if __name__ == "__main__":
    main()
