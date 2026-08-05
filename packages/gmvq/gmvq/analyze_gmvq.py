from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .data import NormStats, SegmentDataset, build_dataset, load_segment_arrays, load_segments, normalize_segments
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
        arrays = load_segment_arrays(args.data)
        segments = arrays["segments"]
        code_segments = arrays.get("code_segments")
        theta_segments = arrays.get("theta_segments")
        valid_mask = arrays.get("valid_mask")
        lengths = arrays.get("lengths")
        ns = ckpt.get("norm_stats")
        stats = NormStats(mean=ns["mean"], std=ns["std"]) if ns is not None else None
        segments, _ = normalize_segments(segments, stats=stats)
        code_ns = ckpt.get("code_norm_stats")
        theta_ns = ckpt.get("theta_norm_stats")
        code_stats = (
            None
            if code_ns is None
            else NormStats(mean=code_ns["mean"], std=code_ns["std"])
        )
        theta_stats = (
            None
            if theta_ns is None
            else NormStats(mean=theta_ns["mean"], std=theta_ns["std"])
        )
        if code_segments is not None:
            code_segments, _ = normalize_segments(code_segments, stats=code_stats)
        if theta_segments is not None:
            theta_segments, _ = normalize_segments(theta_segments, stats=theta_stats)
        dataset = SegmentDataset(
            segments,
            code_segments=code_segments,
            theta_segments=theta_segments,
        )
        metadata = arrays.get("metadata", {})
    else:
        valid_mask = None
        lengths = None
        dataset, _ = build_dataset(
            data=None,
            synthetic=args.synthetic,
            synthetic_n=args.synthetic_n,
            t=cfg.get("t", 120),
            d=cfg.get("d", 14),
        )
        metadata = {}

    model = GMVQAutoEncoder(**cfg).to(args.device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    all_codes: list[torch.Tensor] = []
    all_theta: list[torch.Tensor] = []
    all_z_e: list[torch.Tensor] = []
    all_z_q: list[torch.Tensor] = []
    all_recon: list[torch.Tensor] = []
    all_log_length_pred: list[torch.Tensor] = []
    recon_subset: list[torch.Tensor] = []
    mse_sum = 0.0
    count = 0
    valid_mse_sum = 0.0
    valid_count = 0.0
    seq_mse_sum = 0.0
    seq_count = 0

    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)
    offset = 0
    with torch.no_grad():
        for batch in loader:
            if isinstance(batch, dict):
                x = batch["x"]
                code_x = batch.get("code_x")
                theta_x = batch.get("theta_x")
            else:
                x = batch
                code_x = None
                theta_x = None
            batch_size = x.shape[0]
            batch_mask = None
            batch_lengths = None
            if valid_mask is not None:
                batch_mask = valid_mask[offset : offset + batch_size].to(args.device)
            if lengths is not None:
                batch_lengths = lengths[offset : offset + batch_size].to(args.device)
            offset += batch_size
            x = x.to(args.device)
            out = model(
                x,
                valid_mask=batch_mask,
                lengths=batch_lengths,
                code_x=None if code_x is None else code_x.to(args.device),
                theta_x=None if theta_x is None else theta_x.to(args.device),
            )
            all_codes.append(out["codes"].cpu())
            all_theta.append(out["theta"].cpu())
            all_z_e.append(out["z_e"].cpu())
            all_z_q.append(out["z_q"].cpu())
            all_recon.append(out["x_recon"].cpu())
            if "log_length_pred" in out:
                all_log_length_pred.append(out["log_length_pred"].cpu())
            if len(recon_subset) < 4:
                recon_subset.append(out["x_recon"][: min(16, x.shape[0])].cpu())
            mse_sum += torch.nn.functional.mse_loss(out["x_recon"], x, reduction="sum").item()
            count += x.numel()
            if batch_mask is not None:
                frame_mse = (out["x_recon"] - x).square().mean(dim=2)
                valid_mse_sum += (frame_mse * batch_mask.float()).sum().item()
                valid_count += batch_mask.float().sum().item()
                if batch_lengths is not None:
                    seq_mse = (frame_mse * batch_mask.float()).sum(dim=1) / batch_lengths.float().clamp_min(1.0)
                    seq_mse_sum += seq_mse.sum().item()
                    seq_count += int(seq_mse.numel())

    codes_t = torch.cat(all_codes, dim=0)
    theta_t = torch.cat(all_theta, dim=0)
    z_e_t = torch.cat(all_z_e, dim=0)
    z_q_t = torch.cat(all_z_q, dim=0)
    recon_all_t = torch.cat(all_recon, dim=0)
    log_length_pred_t = torch.cat(all_log_length_pred, dim=0) if all_log_length_pred else None
    recon_t = torch.cat(recon_subset, dim=0)[:64]

    np.save(out_dir / "codes.npy", codes_t.numpy())
    np.save(out_dir / "theta.npy", theta_t.numpy())
    np.save(out_dir / "z_e.npy", z_e_t.numpy())
    np.save(out_dir / "z_q.npy", z_q_t.numpy())
    np.save(out_dir / "recon_padded.npy", recon_all_t.numpy())
    np.save(out_dir / "recon_subset.npy", recon_t.numpy())
    if log_length_pred_t is not None:
        np.save(out_dir / "length_pred.npy", log_length_pred_t.exp().numpy())
    if lengths is not None:
        np.save(out_dir / "lengths.npy", lengths.numpy())
    if valid_mask is not None:
        np.save(out_dir / "valid_mask.npy", valid_mask.numpy())
    if args.data:
        latent_payload: dict[str, np.ndarray] = {
            "codes": codes_t.numpy(),
            "theta": theta_t.numpy(),
            "z_e": z_e_t.numpy(),
            "z_q": z_q_t.numpy(),
        }
        if lengths is not None:
            latent_payload["lengths"] = lengths.numpy()
        for key, value in metadata.items():
            latent_payload[key] = np.asarray(value)
        np.savez_compressed(out_dir / "latents.npz", **latent_payload)

    usage = code_usage_stats(codes_t, cfg["num_codes"])
    print("code usage histogram:")
    print(usage["hist"].long().tolist())
    print(f"active code count: {int(usage['active_codes'])}")
    print(f"perplexity: {float(usage['perplexity']):.4f}")
    print(f"reconstruction MSE: {mse_sum / max(count, 1):.6f}")
    if valid_mask is not None:
        print(f"valid-frame reconstruction MSE: {valid_mse_sum / max(valid_count, 1.0):.6f}")
    if seq_count:
        print(f"mean per-segment valid reconstruction MSE: {seq_mse_sum / max(seq_count, 1):.6f}")
    if log_length_pred_t is not None and lengths is not None:
        length_pred = log_length_pred_t.exp()
        length_target = lengths.float()
        mae = (length_pred - length_target).abs().mean()
        rel_mae = ((length_pred - length_target).abs() / length_target.clamp_min(1.0)).mean()
        print(f"length MAE: {float(mae):.4f}")
        print(f"length relative MAE: {float(rel_mae):.4f}")
    for code in range(cfg["num_codes"]):
        mask = codes_t == code
        if bool(mask.any()):
            th = theta_t[mask]
            print(f"code={code} n={int(mask.sum())} theta_mean={th.mean(0).mean():.4f} theta_std={th.std(0).mean():.4f}")

    maybe_plot(out_dir, codes_t.numpy(), theta_t.numpy(), cfg["num_codes"])
    print(f"saved analysis arrays: {out_dir}")


if __name__ == "__main__":
    main()
