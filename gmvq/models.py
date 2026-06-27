from __future__ import annotations

from typing import Any

import torch
from torch import nn

from .quantizers import GaussianMixtureVectorQuantizer


class MLPEncoder(nn.Module):
    def __init__(self, t: int = 120, d: int = 14, latent_dim: int = 32, hidden_dim: int = 256) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(t * d, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, latent_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Conv1DEncoder(nn.Module):
    def __init__(self, t: int = 120, d: int = 14, latent_dim: int = 32, hidden_dim: int = 128) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(d, hidden_dim, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=5, stride=2, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=5, stride=2, padding=2),
            nn.GELU(),
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(hidden_dim, latent_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # [B, T, D] -> [B, D, T]
        return self.net(x.transpose(1, 2))


class SegmentDecoder(nn.Module):
    def __init__(self, in_dim: int, t: int = 120, d: int = 14, hidden_dim: int = 256) -> None:
        super().__init__()
        self.t = t
        self.d = d
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, t * d),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        return self.net(z).view(z.shape[0], self.t, self.d)


class Conv1DDecoder(nn.Module):
    """Temporal 1D CNN decoder from a global latent to [B, T, D]."""

    def __init__(self, z_dim: int = 32, t: int = 120, d: int = 14, hidden_dim: int = 128) -> None:
        super().__init__()
        self.t = t
        self.d = d
        self.hidden_dim = hidden_dim
        seed_t = max(4, (t + 3) // 4)
        self.seed_t = seed_t
        self.fc = nn.Sequential(
            nn.Linear(z_dim, hidden_dim * seed_t),
            nn.GELU(),
        )
        self.net = nn.Sequential(
            nn.ConvTranspose1d(hidden_dim, hidden_dim, kernel_size=4, stride=2, padding=1),
            nn.GELU(),
            nn.ConvTranspose1d(hidden_dim, hidden_dim, kernel_size=4, stride=2, padding=1),
            nn.GELU(),
            nn.Conv1d(hidden_dim, d, kernel_size=5, padding=2),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        h = self.fc(z).view(z.shape[0], self.hidden_dim, self.seed_t)
        x = self.net(h)
        if x.shape[-1] != self.t:
            x = torch.nn.functional.interpolate(x, size=self.t, mode="linear", align_corners=False)
        return x.transpose(1, 2)


class GMVQAutoEncoder(nn.Module):
    """Autoencoder for segment ~= decoder(k, theta)."""

    def __init__(
        self,
        t: int = 120,
        d: int = 14,
        latent_dim: int = 32,
        num_codes: int = 64,
        encoder_type: str = "mlp",
        decoder_type: str = "latent",
        assignment: str = "hard",
        use_ste: bool = True,
        theta_mode: str = "clipped",
        theta_clip: float = 2.0,
        sigma_min: float = 0.05,
        sigma_max: float = 1.0,
        prior_mode: str = "learned",
    ) -> None:
        super().__init__()
        if encoder_type == "mlp":
            self.encoder = MLPEncoder(t=t, d=d, latent_dim=latent_dim)
        elif encoder_type == "conv1d":
            self.encoder = Conv1DEncoder(t=t, d=d, latent_dim=latent_dim)
        else:
            raise ValueError("encoder_type must be 'mlp' or 'conv1d'")

        if decoder_type not in {"latent", "factorized"}:
            raise ValueError("decoder_type must be 'latent' or 'factorized'")

        self.t = t
        self.d = d
        self.latent_dim = latent_dim
        self.num_codes = num_codes
        self.encoder_type = encoder_type
        self.decoder_type = decoder_type

        self.quantizer = GaussianMixtureVectorQuantizer(
            num_codes=num_codes,
            latent_dim=latent_dim,
            sigma_min=sigma_min,
            sigma_max=sigma_max,
            assignment=assignment,
            use_ste=use_ste,
            theta_mode=theta_mode,
            theta_clip=theta_clip,
            prior_mode=prior_mode,
        )
        decoder_in_dim = latent_dim if decoder_type == "latent" else 2 * latent_dim
        self.decoder = SegmentDecoder(in_dim=decoder_in_dim, t=t, d=d)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        # x: [B, T, D]
        z_e = self.encoder(x)
        q = self.quantizer(z_e)
        dec_in = q.z_q if self.decoder_type == "latent" else torch.cat([q.mu_k, q.theta_dec], dim=-1)
        x_recon = self.decoder(dec_in)
        out: dict[str, torch.Tensor] = {
            "x_recon": x_recon,
            "z_e": z_e,
            "z_q": q.z_q,
            "codes": q.codes,
            "theta": q.theta,
            "theta_dec": q.theta_dec,
            "mu_k": q.mu_k,
            "sigma_k": q.sigma_k,
            "distances": q.distances,
        }
        if q.assignment_probs is not None:
            out["assignment_probs"] = q.assignment_probs
        if q.posterior_probs is not None:
            out["posterior_probs"] = q.posterior_probs
        if q.log_prob_k is not None:
            out["log_prob_k"] = q.log_prob_k
        if q.mixture_nll is not None:
            out["mixture_nll"] = q.mixture_nll
        if q.q_bar is not None:
            out["q_bar"] = q.q_bar
        if q.log_prior is not None:
            out["log_prior"] = q.log_prior
        return out

    def config(self) -> dict[str, Any]:
        q = self.quantizer
        return {
            "t": self.t,
            "d": self.d,
            "latent_dim": self.latent_dim,
            "num_codes": self.num_codes,
            "encoder_type": self.encoder_type,
            "decoder_type": self.decoder_type,
            "assignment": q.assignment,
            "use_ste": q.use_ste,
            "theta_mode": q.theta_mode,
            "theta_clip": q.theta_clip,
            "sigma_min": q.sigma_min,
            "sigma_max": q.sigma_max,
            "prior_mode": q.prior_mode,
        }
