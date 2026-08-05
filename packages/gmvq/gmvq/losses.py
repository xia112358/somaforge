from __future__ import annotations

from typing import Any, Callable, Optional

import torch
import torch.nn.functional as F


contact_loss_fn: Optional[Callable[..., torch.Tensor]] = None
outcome_loss_fn: Optional[Callable[..., torch.Tensor]] = None


def code_usage_stats(codes: torch.Tensor, num_codes: int) -> dict[str, torch.Tensor]:
    hist = torch.bincount(codes.reshape(-1), minlength=num_codes).float()
    probs = hist / hist.sum().clamp_min(1.0)
    entropy = -(probs * (probs + 1e-10).log()).sum()
    perplexity = entropy.exp()
    active_codes = (hist > 0).sum()
    uniform = torch.full_like(probs, 1.0 / num_codes)
    usage_kl = (probs * ((probs + 1e-10).log() - uniform.log())).sum()
    return {
        "hist": hist,
        "probs": probs,
        "entropy": entropy,
        "perplexity": perplexity,
        "active_codes": active_codes,
        "usage_kl": usage_kl,
    }


def compute_loss(
    x: torch.Tensor,
    output: dict[str, torch.Tensor],
    model: torch.nn.Module,
    cfg: Any,
    valid_mask: torch.Tensor | None = None,
    lengths: torch.Tensor | None = None,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Aggregate prototype losses.

    References:
    - VQ-VAE: reconstruction, commitment, code usage, perplexity.
    - Gaussian Quant: KL in bits and target bitrate regularization.
    - GM-VQ: sigma regularization for learned Gaussian code components.
    - QueST: velocity/skill-token analysis friendly terms for trajectory chunks.
    """

    beta_theta = float(getattr(cfg, "beta_theta", 0.01))
    beta_rate = float(getattr(cfg, "beta_rate", 0.01))
    beta_commit = float(getattr(cfg, "beta_commit", 0.25))
    beta_usage = float(getattr(cfg, "beta_usage", 0.01))
    beta_sigma = float(getattr(cfg, "beta_sigma", 0.001))
    beta_vel = float(getattr(cfg, "beta_vel", 0.1))
    beta_mix = float(getattr(cfg, "beta_mix", 0.05))
    beta_balance = float(getattr(cfg, "beta_balance", 0.01))
    beta_sep = float(getattr(cfg, "beta_sep", 0.001))
    beta_theta_moments = float(getattr(cfg, "beta_theta_moments", 0.01))
    beta_local_basis = float(getattr(cfg, "beta_local_basis", 0.001))
    beta_length = float(getattr(cfg, "beta_length", 0.05))
    target_bits = float(getattr(cfg, "target_bits", 4.0))
    codebook_loss_weight = float(getattr(cfg, "codebook_loss_weight", 1.0))
    sep_tau = float(getattr(cfg, "sep_tau", 1.0))

    x_recon = output["x_recon"]
    z_e = output["z_e"]
    mu_k = output["mu_k"]
    theta = output["theta"]

    if valid_mask is not None:
        frame_mask = valid_mask.to(device=x.device, dtype=x.dtype)
        if frame_mask.shape != x.shape[:2]:
            raise ValueError(f"valid_mask must have shape {tuple(x.shape[:2])}, got {tuple(frame_mask.shape)}")
        mask = frame_mask.unsqueeze(-1)
        recon_sse = ((x_recon - x).square() * mask).sum(dim=(1, 2))
        recon_count = (frame_mask.sum(dim=1) * x.shape[-1]).clamp_min(1.0)
        recon_loss = (recon_sse / recon_count).mean()
    else:
        frame_mask = None
        recon_loss = F.mse_loss(x_recon, x)
    theta_l2 = theta.square().mean()
    theta_kl_bits_per_sample = (0.5 * theta.square() / torch.log(torch.tensor(2.0, device=x.device))).sum(dim=-1)
    theta_rate = (theta_kl_bits_per_sample.mean() - target_bits).abs()

    # VQ-VAE commitment/codebook terms, with Gaussian component mean as the code vector.
    commit_encoder = F.mse_loss(z_e, mu_k.detach())
    commit_codebook = F.mse_loss(z_e.detach(), mu_k)
    commit_loss = commit_encoder + codebook_loss_weight * commit_codebook

    usage = code_usage_stats(output["codes"], model.quantizer.num_codes)
    usage_loss = usage["usage_kl"]

    mixture_nll = output.get("mixture_nll")
    mix_loss = mixture_nll.mean() if mixture_nll is not None else torch.zeros((), device=x.device)

    q_bar = output.get("q_bar")
    if q_bar is not None:
        uniform = torch.full_like(q_bar, 1.0 / q_bar.numel())
        balance_loss = (q_bar * ((q_bar + 1e-10).log() - uniform.log())).sum()
        q_bar_entropy = -(q_bar * (q_bar + 1e-10).log()).sum()
    else:
        balance_loss = usage_loss
        q_bar_entropy = usage["entropy"]

    probs = output.get("posterior_probs")
    if probs is not None:
        entropy_per_sample = -(probs * (probs + 1e-10).log()).sum(dim=-1).mean()
    else:
        entropy_per_sample = torch.zeros((), device=x.device)

    sigma = model.quantizer.sigma()
    near_min = F.relu(model.quantizer.sigma_min * 1.2 - sigma).square().mean()
    near_max = F.relu(sigma - model.quantizer.sigma_max * 0.8).square().mean()
    log_sigma_l2 = model.quantizer.code_log_sigma.square().mean()
    sigma_reg = near_min + near_max + 0.01 * log_sigma_l2

    mu = model.quantizer.code_mu
    if mu.shape[0] > 1:
        sq_dist = torch.cdist(mu, mu).square()
        mask = ~torch.eye(mu.shape[0], dtype=torch.bool, device=mu.device)
        sep_loss = torch.exp(-sq_dist[mask] / max(sep_tau, 1e-6)).mean()
    else:
        sep_loss = torch.zeros((), device=x.device)

    theta_moments = torch.zeros((), device=x.device)
    active_moment_codes = torch.zeros((), device=x.device)
    for code in range(model.quantizer.num_codes):
        mask = output["codes"] == code
        if int(mask.sum()) >= 2:
            th = theta[mask]
            mean_loss = th.mean(dim=0).square().mean()
            var_loss = (th.var(dim=0, unbiased=False) - 1.0).square().mean()
            theta_moments = theta_moments + mean_loss + var_loss
            active_moment_codes = active_moment_codes + 1.0
    theta_moments = theta_moments / active_moment_codes.clamp_min(1.0)
    local_theta_basis = getattr(model, "local_theta_basis", None)
    local_basis_loss = (
        local_theta_basis.square().mean()
        if local_theta_basis is not None
        else torch.zeros((), device=x.device)
    )

    if x.shape[1] > 1:
        recon_vel = x_recon[:, 1:] - x_recon[:, :-1]
        target_vel = x[:, 1:] - x[:, :-1]
        if frame_mask is not None:
            vel_mask = (frame_mask[:, 1:] * frame_mask[:, :-1]).unsqueeze(-1)
            vel_sse = ((recon_vel - target_vel).square() * vel_mask).sum(dim=(1, 2))
            vel_count = (vel_mask.squeeze(-1).sum(dim=1) * x.shape[-1]).clamp_min(1.0)
            vel_loss = (vel_sse / vel_count).mean()
        else:
            vel_loss = F.mse_loss(recon_vel, target_vel)
    else:
        vel_loss = torch.zeros((), device=x.device)

    length_loss = torch.zeros((), device=x.device)
    log_length_pred = output.get("log_length_pred")
    if log_length_pred is not None and lengths is not None:
        target_log_length = lengths.to(device=x.device, dtype=x.dtype).clamp_min(1.0).log()
        length_loss = F.mse_loss(log_length_pred, target_log_length)

    task_loss = torch.zeros((), device=x.device)
    if contact_loss_fn is not None:
        task_loss = task_loss + contact_loss_fn(x, output)
    if outcome_loss_fn is not None:
        task_loss = task_loss + outcome_loss_fn(x, output)

    total = (
        recon_loss
        + beta_theta * theta_l2
        + beta_rate * theta_rate
        + beta_commit * commit_loss
        + beta_usage * usage_loss
        + beta_mix * mix_loss
        + beta_balance * balance_loss
        + beta_sep * sep_loss
        + beta_theta_moments * theta_moments
        + beta_local_basis * local_basis_loss
        + beta_sigma * sigma_reg
        + beta_vel * vel_loss
        + beta_length * length_loss
        + task_loss
    )

    metrics = {
        "total_loss": total.detach(),
        "recon_loss": recon_loss.detach(),
        "vel_loss": vel_loss.detach(),
        "length_loss": length_loss.detach(),
        "theta_l2": theta_l2.detach(),
        "theta_rate": theta_rate.detach(),
        "theta_bits": theta_kl_bits_per_sample.mean().detach(),
        "commit_loss": commit_loss.detach(),
        "usage_loss": usage_loss.detach(),
        "mix_loss": mix_loss.detach(),
        "balance_loss": balance_loss.detach(),
        "sep_loss": sep_loss.detach(),
        "theta_moments": theta_moments.detach(),
        "local_basis_loss": local_basis_loss.detach(),
        "sigma_reg": sigma_reg.detach(),
        "active_codes": usage["active_codes"].detach(),
        "perplexity": usage["perplexity"].detach(),
        "q_bar_entropy": q_bar_entropy.detach(),
        "entropy_per_sample": entropy_per_sample.detach(),
        "mean_sigma": sigma.mean().detach(),
        "min_sigma": sigma.min().detach(),
        "max_sigma": sigma.max().detach(),
    }
    return total, metrics
