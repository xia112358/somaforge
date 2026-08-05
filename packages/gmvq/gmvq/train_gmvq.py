from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from somaforge_core import stage_spec

from .data import build_dataset, load_contact_force_provenance, load_robot_asset_metadata
from .losses import compute_loss
from .models import GMVQAutoEncoder


def _trajectory_embeddings(
    segments: torch.Tensor,
    valid_mask: torch.Tensor,
    *,
    phase_steps: int,
    pca_dim: int,
) -> np.ndarray:
    values = segments.detach().cpu().numpy().astype(np.float64, copy=False)
    masks = valid_mask.detach().cpu().numpy().astype(np.bool_, copy=False)
    if values.ndim != 3 or masks.shape != values.shape[:2]:
        raise ValueError("trajectory bootstrap expects [N,T,D] segments and [N,T] masks")
    if phase_steps < 2:
        raise ValueError("trajectory bootstrap phase_steps must be at least 2")

    valid_values = values[masks]
    active = valid_values.var(axis=0) > 1.0e-12
    if not np.any(active):
        raise ValueError("trajectory bootstrap has no nonconstant code features")
    target_phase = np.linspace(0.0, 1.0, phase_steps)
    flattened: list[np.ndarray] = []
    for segment, mask in zip(values, masks):
        real = segment[mask][:, active]
        if len(real) < 2:
            raise ValueError("trajectory bootstrap requires at least two valid frames per segment")
        source_phase = np.linspace(0.0, 1.0, len(real))
        resampled = np.stack(
            [
                np.interp(target_phase, source_phase, real[:, feature])
                for feature in range(real.shape[1])
            ],
            axis=1,
        )
        flattened.append(resampled.reshape(-1))
    matrix = np.stack(flattened)
    matrix -= matrix.mean(axis=0, keepdims=True)

    rank = min(int(pca_dim), matrix.shape[0] - 1, matrix.shape[1])
    if rank <= 0 or rank >= matrix.shape[1]:
        return matrix
    gram = matrix @ matrix.T
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1][:rank]
    return eigenvectors[:, order] * np.sqrt(
        np.maximum(eigenvalues[order], 0.0)
    )[None, :]


def _kmeans_labels(
    embeddings: np.ndarray,
    *,
    num_codes: int,
    restarts: int,
    seed: int = 0,
) -> np.ndarray:
    values = np.asarray(embeddings, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError(f"kmeans embeddings must be 2D, got {values.shape}")
    if not 1 <= num_codes <= len(values):
        raise ValueError(f"num_codes must be in [1,{len(values)}], got {num_codes}")
    rng = np.random.default_rng(seed)
    best: tuple[float, np.ndarray] | None = None
    for _ in range(max(1, int(restarts))):
        indices = [int(rng.integers(len(values)))]
        while len(indices) < num_codes:
            distances = (
                (values[:, None, :] - values[np.asarray(indices)][None, :, :]) ** 2
            ).sum(axis=2).min(axis=1)
            total = float(distances.sum())
            if total <= 1.0e-12:
                remaining = np.setdiff1d(np.arange(len(values)), np.asarray(indices))
                indices.append(int(rng.choice(remaining)))
            else:
                indices.append(int(rng.choice(len(values), p=distances / total)))
        centers = values[np.asarray(indices)].copy()
        labels = np.full(len(values), -1, dtype=np.int64)
        for _ in range(100):
            distances = ((values[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
            next_labels = distances.argmin(axis=1)
            if np.array_equal(next_labels, labels):
                break
            labels = next_labels
            for code in range(num_codes):
                members = values[labels == code]
                if len(members):
                    centers[code] = members.mean(axis=0)
        inertia = float(((values - centers[labels]) ** 2).sum())
        if best is None or inertia < best[0]:
            best = (inertia, labels.copy())
    assert best is not None
    return best[1]


def _bootstrap_code_encoder(
    model: GMVQAutoEncoder,
    dataset: object,
    *,
    device: torch.device,
    steps: int,
    lr: float,
    phase_steps: int,
    pca_dim: int,
    restarts: int,
    batch_size: int,
) -> dict[str, object]:
    code_segments = getattr(dataset, "code_segments", None)
    valid_mask = getattr(dataset, "valid_mask", None)
    if code_segments is None or valid_mask is None:
        raise ValueError("trajectory bootstrap requires a masked dual-view dataset")
    embeddings = _trajectory_embeddings(
        code_segments,
        valid_mask,
        phase_steps=phase_steps,
        pca_dim=pca_dim,
    )
    labels_np = _kmeans_labels(
        embeddings,
        num_codes=model.num_codes,
        restarts=restarts,
    )
    labels = torch.from_numpy(labels_np).long()
    parameters = list(model.encoder.parameters()) + [model.quantizer.code_mu]
    optimizer = torch.optim.AdamW(parameters, lr=lr)
    generator = torch.Generator().manual_seed(0)
    model.train()
    final_accuracy = 0.0
    for step in range(1, steps + 1):
        indices = torch.randint(
            len(code_segments),
            (min(batch_size, len(code_segments)),),
            generator=generator,
        )
        x = code_segments[indices].to(device)
        mask = valid_mask[indices].to(device)
        target = labels[indices].to(device)
        z_e = model._encode(model.encoder, x, mask)
        squared_distance = torch.cdist(z_e, model.quantizer.code_mu).square()
        logits = -squared_distance
        center = model.quantizer.code_mu[target]
        loss = F.cross_entropy(logits, target) + 0.1 * F.mse_loss(z_e, center)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(parameters, 1.0)
        optimizer.step()
        if step == steps or step % max(1, steps // 5) == 0:
            with torch.no_grad():
                final_accuracy = float((logits.argmax(dim=-1) == target).float().mean())
            print(
                f"bootstrap_step={step} loss={float(loss.detach()):.4f} "
                f"batch_accuracy={final_accuracy:.4f}",
                flush=True,
            )

    with torch.no_grad():
        model.quantizer.code_log_sigma.fill_(-0.7)
        predictions: list[torch.Tensor] = []
        for start in range(0, len(code_segments), batch_size):
            x = code_segments[start : start + batch_size].to(device)
            mask = valid_mask[start : start + batch_size].to(device)
            z_e = model._encode(model.encoder, x, mask)
            predictions.append(model.quantizer(z_e).codes.cpu())
        predicted = torch.cat(predictions)
        accuracy = float((predicted == labels).float().mean())
    counts = np.bincount(labels_np, minlength=model.num_codes)
    report: dict[str, object] = {
        "schema": "trajectory_kmeans_bootstrap_v1",
        "sample_count": int(len(labels_np)),
        "num_codes": int(model.num_codes),
        "phase_steps": int(phase_steps),
        "pca_dim": int(pca_dim),
        "cluster_counts": counts.tolist(),
        "encoder_assignment_accuracy": accuracy,
        "uses_segment_metadata": False,
    }
    print(json.dumps(report, sort_keys=True), flush=True)
    return report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train a GMVQ-style atom-skill tokenizer.")
    p.add_argument("--data", type=str, default=None)
    p.add_argument("--synthetic", action="store_true")
    p.add_argument("--save_dir", type=str, default="runs/gmvq")
    p.add_argument("--num_codes", type=int, default=64)
    p.add_argument("--latent_dim", type=int, default=32)
    p.add_argument("--theta_dim", type=int, default=None)
    p.add_argument(
        "--encoder_type",
        choices=["mlp", "conv1d", "conv1d_masked", "tcn_masked", "bigru_masked", "transformer_masked"],
        default="mlp",
    )
    p.add_argument("--decoder_type", choices=["latent", "factorized", "time"], default="latent")
    p.add_argument("--assignment", choices=["hard", "soft"], default="hard")
    p.add_argument("--batch_size", type=int, default=128)
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--training_stage", choices=["joint", "code", "theta"], default="joint")
    p.add_argument("--init_checkpoint", type=str, default=None)
    p.add_argument("--soft_warmup_steps", type=int, default=0)
    p.add_argument(
        "--local_output_theta",
        action="store_true",
        help="decode theta as a code-local low-rank trajectory residual",
    )
    p.add_argument("--trajectory_kmeans_bootstrap_steps", type=int, default=0)
    p.add_argument("--trajectory_kmeans_phase_steps", type=int, default=64)
    p.add_argument("--trajectory_kmeans_pca_dim", type=int, default=32)
    p.add_argument("--trajectory_kmeans_restarts", type=int, default=32)
    p.add_argument("--freeze_bootstrapped_codes", action="store_true")
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
    p.add_argument("--beta_local_basis", type=float, default=0.001)
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
    code_stats = getattr(dataset, "code_norm_stats", None)
    theta_stats = getattr(dataset, "theta_norm_stats", None)
    has_code_view = getattr(dataset, "code_segments", None) is not None
    has_theta_view = getattr(dataset, "theta_segments", None) is not None
    robot_asset = None if args.synthetic else load_robot_asset_metadata(args.data)
    contact_force_provenance = None
    if not args.synthetic:
        with np.load(Path(args.data).expanduser(), allow_pickle=False) as data:
            has_force_provenance = "contact_force_provenance_json" in data.files
        if has_force_provenance:
            contact_force_provenance = load_contact_force_provenance(args.data)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=False)
    iterator = iter(loader)

    init_checkpoint = None
    if args.init_checkpoint:
        init_checkpoint = torch.load(args.init_checkpoint, map_location="cpu", weights_only=False)
        model_config = dict(init_checkpoint["model_config"])
        model_config["theta_enabled"] = args.training_stage != "code"
        model = GMVQAutoEncoder(**model_config)
        model.load_state_dict(init_checkpoint["model_state"])
        if model.dual_view != has_code_view:
            raise ValueError(
                "init checkpoint/data dual-view mismatch: "
                f"model.dual_view={model.dual_view} data_has_code_segments={has_code_view}"
            )
        if model.t != dataset.segments.shape[1] or model.d != dataset.segments.shape[2]:
            raise ValueError(
                "init checkpoint shape does not match dataset: "
                f"model={(model.t, model.d)} data={tuple(dataset.segments.shape[1:])}"
            )
        expected_code_d = (
            dataset.segments.shape[2]
            if not has_code_view
            else dataset.code_segments.shape[2]
        )
        expected_theta_d = (
            dataset.segments.shape[2]
            if not has_theta_view
            else dataset.theta_segments.shape[2]
        )
        if model.code_d != expected_code_d or model.theta_d != expected_theta_d:
            raise ValueError(
                "init checkpoint view dimensions do not match dataset: "
                f"model code/theta={(model.code_d, model.theta_d)} "
                f"data={(expected_code_d, expected_theta_d)}"
            )
        checkpoint_asset = init_checkpoint.get("robot_asset")
        if checkpoint_asset is not None and robot_asset is not None:
            if checkpoint_asset.get("asset_bundle_sha256") != robot_asset.get("asset_bundle_sha256"):
                raise ValueError("init checkpoint robot asset does not match training data")
    else:
        model = GMVQAutoEncoder(
            t=dataset.segments.shape[1],
            d=dataset.segments.shape[2],
            latent_dim=args.latent_dim,
            theta_dim=args.theta_dim,
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
            theta_enabled=args.training_stage != "code",
            dual_view=has_code_view,
            local_output_theta=args.local_output_theta,
            code_d=(
                dataset.segments.shape[2]
                if not has_code_view
                else dataset.code_segments.shape[2]
            ),
            theta_d=(
                dataset.segments.shape[2]
                if not has_theta_view
                else dataset.theta_segments.shape[2]
            ),
        )
    model = model.to(args.device)
    bootstrap_report: dict[str, object] | None = None

    if args.training_stage == "code":
        model.set_theta_enabled(False)
        for param in model.theta_encoder.parameters():
            param.requires_grad_(False)
        for param in model.theta_decoder.parameters():
            param.requires_grad_(False)
        if model.theta_source_encoder is not None:
            for param in model.theta_source_encoder.parameters():
                param.requires_grad_(False)
    elif args.training_stage == "theta":
        if init_checkpoint is None:
            raise ValueError("--training_stage theta requires --init_checkpoint from a code stage")
        model.set_theta_enabled(True)
        for param in model.encoder.parameters():
            param.requires_grad_(False)
        for param in model.quantizer.parameters():
            param.requires_grad_(False)
        if model.theta_source_encoder is not None and init_checkpoint.get("training_stage") == "code":
            source_state = model.encoder.state_dict()
            target_state = model.theta_source_encoder.state_dict()
            if source_state.keys() == target_state.keys() and all(
                source_state[key].shape == target_state[key].shape for key in source_state
            ):
                model.theta_source_encoder.load_state_dict(source_state)

    if args.trajectory_kmeans_bootstrap_steps > 0:
        if args.training_stage != "joint":
            raise ValueError("trajectory KMeans bootstrap currently requires --training_stage joint")
        if init_checkpoint is not None:
            raise ValueError("trajectory KMeans bootstrap starts from a fresh model")
        bootstrap_report = _bootstrap_code_encoder(
            model,
            dataset,
            device=torch.device(args.device),
            steps=args.trajectory_kmeans_bootstrap_steps,
            lr=args.lr,
            phase_steps=args.trajectory_kmeans_phase_steps,
            pca_dim=args.trajectory_kmeans_pca_dim,
            restarts=args.trajectory_kmeans_restarts,
            batch_size=args.batch_size,
        )
        if model.theta_source_encoder is not None:
            source_state = model.encoder.state_dict()
            target_state = model.theta_source_encoder.state_dict()
            if source_state.keys() == target_state.keys() and all(
                source_state[key].shape == target_state[key].shape for key in source_state
            ):
                model.theta_source_encoder.load_state_dict(source_state)
        if args.freeze_bootstrapped_codes:
            for param in model.encoder.parameters():
                param.requires_grad_(False)
            for param in model.quantizer.parameters():
                param.requires_grad_(False)

    trainable = [param for param in model.parameters() if param.requires_grad]
    if not trainable:
        raise ValueError(f"training stage {args.training_stage!r} has no trainable parameters")
    opt = torch.optim.AdamW(trainable, lr=args.lr)

    cfg = SimpleNamespace(**vars(args))
    last_metrics: dict[str, torch.Tensor] = {}
    uses_valid_mask = hasattr(dataset, "valid_mask")
    for step in range(1, args.steps + 1):
        if args.training_stage == "code" and args.soft_warmup_steps > 0:
            model.quantizer.assignment = "soft" if step <= args.soft_warmup_steps else "hard"
        try:
            batch = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            batch = next(iterator)
        if isinstance(batch, dict):
            x = batch["x"]
            code_x = batch.get("code_x")
            theta_x = batch.get("theta_x")
            valid_mask = batch.get("valid_mask")
            lengths = batch.get("lengths")
        else:
            x = batch
            code_x = None
            theta_x = None
            valid_mask = None
            lengths = None
        x = x.to(args.device)
        code_x = None if code_x is None else code_x.to(args.device)
        theta_x = None if theta_x is None else theta_x.to(args.device)
        valid_mask = None if valid_mask is None else valid_mask.to(args.device)
        lengths = None if lengths is None else lengths.to(args.device)

        output = model(
            x,
            valid_mask=valid_mask,
            lengths=lengths,
            code_x=code_x,
            theta_x=theta_x,
        )
        loss_target = (
            code_x
            if args.training_stage == "code" and code_x is not None and code_x.shape == x.shape
            else x
        )
        loss, metrics = compute_loss(
            loss_target,
            output,
            model,
            cfg,
            valid_mask=valid_mask,
            lengths=lengths,
        )
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

    if args.training_stage == "code":
        model.quantizer.assignment = "hard"
    ckpt = {
        "model_state": model.state_dict(),
        "model_config": model.config(),
        "train_args": vars(args),
        "uses_valid_mask": uses_valid_mask,
        "norm_stats": None if stats is None else {"mean": stats.mean.cpu(), "std": stats.std.cpu()},
        "code_norm_stats": (
            None if code_stats is None else {"mean": code_stats.mean.cpu(), "std": code_stats.std.cpu()}
        ),
        "theta_norm_stats": (
            None if theta_stats is None else {"mean": theta_stats.mean.cpu(), "std": theta_stats.std.cpu()}
        ),
        "last_metrics": {k: v.cpu() for k, v in last_metrics.items()},
        "robot_asset": robot_asset,
        "contact_force_provenance": contact_force_provenance,
        "training_stage": args.training_stage,
        "init_checkpoint": args.init_checkpoint,
        "trajectory_kmeans_bootstrap": bootstrap_report,
    }
    torch.save(ckpt, save_dir / "checkpoint.pt")
    with (save_dir / "config.json").open("w", encoding="utf-8") as f:
        json.dump(vars(args) | model.config(), f, indent=2)
    if stats is not None:
        torch.save({"mean": stats.mean.cpu(), "std": stats.std.cpu()}, save_dir / "norm_stats.pt")
    print(f"saved checkpoint: {save_dir / 'checkpoint.pt'}")


if __name__ == "__main__":
    main()
