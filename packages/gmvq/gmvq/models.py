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


class MaskedConv1DEncoder(nn.Module):
    def __init__(self, t: int = 120, d: int = 14, latent_dim: int = 32, hidden_dim: int = 128) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(d, hidden_dim, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=5, padding=2),
            nn.GELU(),
        )
        self.proj = nn.Linear(hidden_dim, latent_dim)

    def forward(self, x: torch.Tensor, valid_mask: torch.Tensor | None = None) -> torch.Tensor:
        # [B, T, D] -> [B, H, T]
        h = self.net(x.transpose(1, 2))
        if valid_mask is None:
            pooled = h.mean(dim=-1)
        else:
            mask = valid_mask.to(device=x.device, dtype=h.dtype).unsqueeze(1)
            pooled = (h * mask).sum(dim=-1) / mask.sum(dim=-1).clamp_min(1.0)
        return self.proj(pooled)


class _TCNBlock(nn.Module):
    def __init__(self, hidden_dim: int, dilation: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=3, padding=dilation, dilation=dilation),
            nn.GELU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=3, padding=dilation, dilation=dilation),
        )
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(x + self.net(x))


class MaskedTCNEncoder(nn.Module):
    def __init__(self, t: int = 120, d: int = 14, latent_dim: int = 32, hidden_dim: int = 128) -> None:
        super().__init__()
        self.input = nn.Sequential(nn.Conv1d(d, hidden_dim, kernel_size=5, padding=2), nn.GELU())
        self.blocks = nn.Sequential(*[_TCNBlock(hidden_dim, dilation) for dilation in (1, 2, 4, 8, 16)])
        self.proj = nn.Sequential(
            nn.Linear(2 * hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, latent_dim),
        )

    def forward(self, x: torch.Tensor, valid_mask: torch.Tensor | None = None) -> torch.Tensor:
        h = self.blocks(self.input(x.transpose(1, 2))).transpose(1, 2)
        if valid_mask is None:
            pooled = torch.cat([h.mean(dim=1), h.amax(dim=1)], dim=-1)
        else:
            mask = valid_mask.to(device=x.device, dtype=h.dtype).unsqueeze(-1)
            mean = (h * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
            max_in = h.masked_fill(~valid_mask.to(device=x.device).unsqueeze(-1), -torch.inf)
            max_pool = max_in.amax(dim=1)
            max_pool = torch.where(torch.isfinite(max_pool), max_pool, torch.zeros_like(max_pool))
            pooled = torch.cat([mean, max_pool], dim=-1)
        return self.proj(pooled)


class MaskedBiGRUEncoder(nn.Module):
    def __init__(self, t: int = 120, d: int = 14, latent_dim: int = 32, hidden_dim: int = 128) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=d,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True,
        )
        self.proj = nn.Sequential(
            nn.Linear(2 * hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, latent_dim),
        )

    def forward(self, x: torch.Tensor, valid_mask: torch.Tensor | None = None) -> torch.Tensor:
        if valid_mask is None:
            lengths = torch.full((x.shape[0],), x.shape[1], dtype=torch.long, device=x.device)
        else:
            lengths = valid_mask.long().sum(dim=1).clamp_min(1)
        packed = nn.utils.rnn.pack_padded_sequence(
            x,
            lengths.detach().cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        _, h_n = self.gru(packed)
        h = torch.cat([h_n[-2], h_n[-1]], dim=-1)
        return self.proj(h)


class MaskedTransformerEncoder(nn.Module):
    def __init__(self, t: int = 120, d: int = 14, latent_dim: int = 32, hidden_dim: int = 128) -> None:
        super().__init__()
        self.input = nn.Linear(d, hidden_dim)
        self.pos = nn.Parameter(torch.zeros(1, t, hidden_dim))
        layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=4,
            dim_feedforward=4 * hidden_dim,
            dropout=0.1,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=2)
        self.proj = nn.Sequential(
            nn.Linear(2 * hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, latent_dim),
        )

    def forward(self, x: torch.Tensor, valid_mask: torch.Tensor | None = None) -> torch.Tensor:
        h = self.input(x) + self.pos[:, : x.shape[1]]
        key_padding_mask = None if valid_mask is None else ~valid_mask.to(device=x.device)
        h = self.encoder(h, src_key_padding_mask=key_padding_mask)
        if valid_mask is None:
            pooled = torch.cat([h.mean(dim=1), h.amax(dim=1)], dim=-1)
        else:
            mask = valid_mask.to(device=x.device, dtype=h.dtype).unsqueeze(-1)
            mean = (h * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
            max_in = h.masked_fill(~valid_mask.to(device=x.device).unsqueeze(-1), -torch.inf)
            max_pool = max_in.amax(dim=1)
            max_pool = torch.where(torch.isfinite(max_pool), max_pool, torch.zeros_like(max_pool))
            pooled = torch.cat([mean, max_pool], dim=-1)
        return self.proj(pooled)


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


class TimeConditionedDecoder(nn.Module):
    """Decode each frame from a global latent and normalized progress u in [0, 1]."""

    def __init__(self, in_dim: int, t: int = 120, d: int = 14, hidden_dim: int = 256) -> None:
        super().__init__()
        self.t = t
        self.d = d
        time_dim = 5
        self.net = nn.Sequential(
            nn.Linear(in_dim + time_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, d),
        )

    def _time_features(self, z: torch.Tensor, lengths: torch.Tensor | None = None) -> torch.Tensor:
        b = z.shape[0]
        idx = torch.arange(self.t, device=z.device, dtype=z.dtype).view(1, self.t)
        if lengths is None:
            denom = torch.full((b, 1), max(self.t - 1, 1), device=z.device, dtype=z.dtype)
        else:
            denom = (lengths.to(device=z.device, dtype=z.dtype).view(b, 1) - 1.0).clamp_min(1.0)
        u = (idx / denom).clamp(0.0, 1.0)
        return torch.stack(
            [
                u,
                torch.sin(torch.pi * u),
                torch.cos(torch.pi * u),
                torch.sin(2.0 * torch.pi * u),
                torch.cos(2.0 * torch.pi * u),
            ],
            dim=-1,
        )

    def forward(self, z: torch.Tensor, lengths: torch.Tensor | None = None) -> torch.Tensor:
        time = self._time_features(z, lengths=lengths)
        z_rep = z[:, None, :].expand(-1, self.t, -1)
        return self.net(torch.cat([z_rep, time], dim=-1))


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
        elif encoder_type == "conv1d_masked":
            self.encoder = MaskedConv1DEncoder(t=t, d=d, latent_dim=latent_dim)
        elif encoder_type == "tcn_masked":
            self.encoder = MaskedTCNEncoder(t=t, d=d, latent_dim=latent_dim)
        elif encoder_type == "bigru_masked":
            self.encoder = MaskedBiGRUEncoder(t=t, d=d, latent_dim=latent_dim)
        elif encoder_type == "transformer_masked":
            self.encoder = MaskedTransformerEncoder(t=t, d=d, latent_dim=latent_dim)
        else:
            raise ValueError(
                "encoder_type must be 'mlp', 'conv1d', 'conv1d_masked', "
                "'tcn_masked', 'bigru_masked', or 'transformer_masked'"
            )

        if decoder_type not in {"latent", "factorized", "time"}:
            raise ValueError("decoder_type must be 'latent', 'factorized', or 'time'")

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
        decoder_in_dim = latent_dim if decoder_type in {"latent", "time"} else 2 * latent_dim
        if decoder_type == "time":
            self.decoder = TimeConditionedDecoder(in_dim=decoder_in_dim, t=t, d=d)
        else:
            self.decoder = SegmentDecoder(in_dim=decoder_in_dim, t=t, d=d)
        self.length_head = nn.Sequential(
            nn.Linear(latent_dim, latent_dim),
            nn.GELU(),
            nn.Linear(latent_dim, 1),
        )

    def forward(
        self,
        x: torch.Tensor,
        valid_mask: torch.Tensor | None = None,
        lengths: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        # x: [B, T, D]
        if self.encoder_type in {"conv1d_masked", "tcn_masked", "bigru_masked", "transformer_masked"}:
            z_e = self.encoder(x, valid_mask=valid_mask)
        else:
            z_e = self.encoder(x)
        q = self.quantizer(z_e)
        dec_in = q.z_q if self.decoder_type in {"latent", "time"} else torch.cat([q.mu_k, q.theta_dec], dim=-1)
        if self.decoder_type == "time":
            x_recon = self.decoder(dec_in, lengths=lengths)
        else:
            x_recon = self.decoder(dec_in)
        out: dict[str, torch.Tensor] = {
            "x_recon": x_recon,
            "log_length_pred": self.length_head(q.z_q).squeeze(-1),
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
