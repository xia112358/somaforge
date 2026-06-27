from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from torch import nn
import torch.nn.functional as F


@dataclass
class QuantizerOutput:
    z_q: torch.Tensor
    codes: torch.Tensor
    theta: torch.Tensor
    theta_dec: torch.Tensor
    mu_k: torch.Tensor
    sigma_k: torch.Tensor
    distances: torch.Tensor
    assignment_probs: Optional[torch.Tensor] = None
    posterior_probs: Optional[torch.Tensor] = None
    log_prob_k: Optional[torch.Tensor] = None
    mixture_nll: Optional[torch.Tensor] = None
    q_bar: Optional[torch.Tensor] = None
    log_prior: Optional[torch.Tensor] = None


class GaussianMixtureVectorQuantizer(nn.Module):
    """GMVQ-style diagonal Gaussian component codebook.

    References:
    - VQ-VAE: hard nearest-code assignment and optional straight-through estimator.
    - GM-VQ: each code is a Gaussian-like component with mean and adaptive variance.
    - Gaussian Quant: residual bits and optional STE-compatible quantized latent.
    - GMVAE: categorical component k plus continuous Gaussian residual theta.
    """

    def __init__(
        self,
        num_codes: int = 64,
        latent_dim: int = 32,
        sigma_min: float = 0.05,
        sigma_max: float = 1.0,
        assignment: str = "hard",
        use_ste: bool = True,
        theta_clip: float = 2.0,
        theta_mode: str = "clipped",
        temperature: float = 1.0,
        noise_std: float = 0.0,
        prior_mode: str = "learned",
    ) -> None:
        super().__init__()
        if assignment not in {"hard", "soft"}:
            raise ValueError("assignment must be 'hard' or 'soft'")
        if theta_mode not in {"clipped", "stopgrad", "none", "sample"}:
            raise ValueError("theta_mode must be clipped, stopgrad, none, or sample")
        if prior_mode not in {"learned", "uniform"}:
            raise ValueError("prior_mode must be 'learned' or 'uniform'")

        self.num_codes = num_codes
        self.latent_dim = latent_dim
        self.sigma_min = sigma_min
        self.sigma_max = sigma_max
        self.assignment = assignment
        self.use_ste = use_ste
        self.theta_clip = theta_clip
        self.theta_mode = theta_mode
        self.temperature = temperature
        self.noise_std = noise_std
        self.prior_mode = prior_mode

        self.code_mu = nn.Parameter(torch.empty(num_codes, latent_dim))
        self.code_log_sigma = nn.Parameter(torch.empty(num_codes, latent_dim))
        self.code_log_prior = nn.Parameter(torch.zeros(num_codes))
        nn.init.normal_(self.code_mu, mean=0.0, std=0.5)
        nn.init.constant_(self.code_log_sigma, -0.7)

    def sigma(self) -> torch.Tensor:
        return self.code_log_sigma.exp().clamp(self.sigma_min, self.sigma_max)

    def log_prior(self) -> torch.Tensor:
        if self.prior_mode == "uniform":
            return torch.full_like(self.code_log_prior, -torch.log(torch.tensor(float(self.num_codes), device=self.code_log_prior.device)))
        return F.log_softmax(self.code_log_prior, dim=-1)

    def gaussian_distances(self, z_e: torch.Tensor) -> torch.Tensor:
        # z_e: [B, latent_dim], code_mu/sigma: [K, latent_dim], dist: [B, K]
        sigma = self.sigma()
        diff = z_e[:, None, :] - self.code_mu[None, :, :]
        var = sigma.square().clamp_min(1e-8)
        return (diff.square() / var[None, :, :] + var.log()[None, :, :]).sum(dim=-1)

    def gaussian_log_probs(self, z_e: torch.Tensor) -> torch.Tensor:
        # Constant -0.5 * D * log(2pi) is included for a proper mixture NLL.
        distances = self.gaussian_distances(z_e)
        const = self.latent_dim * torch.log(torch.tensor(2.0 * torch.pi, device=z_e.device, dtype=z_e.dtype))
        return self.log_prior()[None, :] - 0.5 * (distances + const)

    def _theta_for_decode(self, theta: torch.Tensor) -> torch.Tensor:
        if self.theta_mode == "clipped":
            return theta.clamp(-self.theta_clip, self.theta_clip)
        if self.theta_mode == "stopgrad":
            return theta.detach()
        if self.theta_mode == "sample":
            return theta + self.noise_std * torch.randn_like(theta)
        return theta

    def forward(self, z_e: torch.Tensor) -> QuantizerOutput:
        if z_e.ndim != 2:
            raise ValueError(f"z_e must have shape [B, latent_dim], got {tuple(z_e.shape)}")

        distances = self.gaussian_distances(z_e)
        log_prob_k = self.gaussian_log_probs(z_e)
        posterior_probs = F.softmax(log_prob_k / max(self.temperature, 1e-6), dim=-1)
        mixture_nll = -torch.logsumexp(log_prob_k, dim=-1)
        q_bar = posterior_probs.mean(dim=0)
        log_prior = self.log_prior()

        if self.assignment == "soft":
            probs = posterior_probs
            mu_k = probs @ self.code_mu
            sigma_k = probs @ self.sigma()
            codes = probs.argmax(dim=-1)
            assignment_probs: Optional[torch.Tensor] = probs
        else:
            codes = posterior_probs.argmax(dim=-1)
            mu_k = self.code_mu[codes]
            sigma_k = self.sigma()[codes]
            assignment_probs = posterior_probs

        theta = (z_e - mu_k) / sigma_k.clamp_min(1e-8)
        theta_dec = self._theta_for_decode(theta)
        z_q_raw = mu_k + sigma_k * theta_dec

        # VQ-VAE/Gaussian Quant style STE: decoder receives z_q while encoder sees identity gradient.
        z_q = z_e + (z_q_raw - z_e).detach() if self.use_ste else z_q_raw

        return QuantizerOutput(
            z_q=z_q,
            codes=codes,
            theta=theta,
            theta_dec=theta_dec,
            mu_k=mu_k,
            sigma_k=sigma_k,
            distances=distances,
            assignment_probs=assignment_probs,
            posterior_probs=posterior_probs,
            log_prob_k=log_prob_k,
            mixture_nll=mixture_nll,
            q_bar=q_bar,
            log_prior=log_prior,
        )
