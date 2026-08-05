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
        theta_dim: int | None = None,
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
        theta_enabled: bool = True,
        dual_view: bool = False,
        local_output_theta: bool = False,
        code_d: int | None = None,
        theta_d: int | None = None,
    ) -> None:
        super().__init__()
        if decoder_type not in {"latent", "factorized", "time"}:
            raise ValueError("decoder_type must be 'latent', 'factorized', or 'time'")
        if local_output_theta and decoder_type == "factorized":
            raise ValueError("local_output_theta is not supported with decoder_type='factorized'")

        self.t = t
        self.d = d
        self.latent_dim = latent_dim
        self.theta_dim = latent_dim if theta_dim is None else int(theta_dim)
        if self.theta_dim <= 0 or self.theta_dim > latent_dim:
            raise ValueError(f"theta_dim must be in [1, {latent_dim}], got {self.theta_dim}")
        self.num_codes = num_codes
        self.encoder_type = encoder_type
        self.decoder_type = decoder_type
        self.theta_enabled = bool(theta_enabled)
        self.dual_view = bool(dual_view)
        self.local_output_theta = bool(local_output_theta)
        self.code_d = int(d if code_d is None else code_d)
        self.theta_d = int(d if theta_d is None else theta_d)
        self.encoder = self._make_encoder(t=t, d=self.code_d, latent_dim=latent_dim)
        self.theta_source_encoder = (
            self._make_encoder(t=t, d=self.theta_d, latent_dim=latent_dim)
            if self.dual_view
            else None
        )

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
        if self.theta_dim == latent_dim:
            self.theta_encoder: nn.Module = nn.Identity()
            self.theta_decoder: nn.Module = nn.Identity()
        else:
            self.theta_encoder = nn.Linear(latent_dim, self.theta_dim, bias=False)
            self.theta_decoder = nn.Linear(self.theta_dim, latent_dim, bias=False)
        decoder_in_dim = (
            latent_dim
            if decoder_type in {"latent", "time"}
            else latent_dim + self.theta_dim
        )
        if decoder_type == "time":
            self.decoder = TimeConditionedDecoder(in_dim=decoder_in_dim, t=t, d=d)
        else:
            self.decoder = SegmentDecoder(in_dim=decoder_in_dim, t=t, d=d)
        if self.local_output_theta:
            self.local_theta_basis = nn.Parameter(
                torch.empty(num_codes, self.theta_dim, t, d)
            )
            nn.init.normal_(self.local_theta_basis, mean=0.0, std=0.01)
        else:
            self.register_parameter("local_theta_basis", None)
        self.length_head = nn.Sequential(
            nn.Linear(latent_dim, latent_dim),
            nn.GELU(),
            nn.Linear(latent_dim, 1),
        )

    def _make_encoder(self, *, t: int, d: int, latent_dim: int) -> nn.Module:
        if self.encoder_type == "mlp":
            return MLPEncoder(t=t, d=d, latent_dim=latent_dim)
        if self.encoder_type == "conv1d":
            return Conv1DEncoder(t=t, d=d, latent_dim=latent_dim)
        if self.encoder_type == "conv1d_masked":
            return MaskedConv1DEncoder(t=t, d=d, latent_dim=latent_dim)
        if self.encoder_type == "tcn_masked":
            return MaskedTCNEncoder(t=t, d=d, latent_dim=latent_dim)
        if self.encoder_type == "bigru_masked":
            return MaskedBiGRUEncoder(t=t, d=d, latent_dim=latent_dim)
        if self.encoder_type == "transformer_masked":
            return MaskedTransformerEncoder(t=t, d=d, latent_dim=latent_dim)
        raise ValueError(
            "encoder_type must be 'mlp', 'conv1d', 'conv1d_masked', "
            "'tcn_masked', 'bigru_masked', or 'transformer_masked'"
        )

    def set_theta_enabled(self, enabled: bool) -> None:
        self.theta_enabled = bool(enabled)

    def _encode(
        self,
        encoder: nn.Module,
        x: torch.Tensor,
        valid_mask: torch.Tensor | None,
    ) -> torch.Tensor:
        if self.encoder_type in {"conv1d_masked", "tcn_masked", "bigru_masked", "transformer_masked"}:
            return encoder(x, valid_mask=valid_mask)
        return encoder(x)

    def _reduced_theta(
        self,
        full_theta: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        theta = self.theta_encoder(full_theta)
        theta_dec = self.quantizer._theta_for_decode(theta)
        residual = self.theta_decoder(theta_dec)
        if not self.theta_enabled:
            residual = torch.zeros_like(residual)
        return theta, theta_dec, residual

    def _latent_from_hybrid(
        self,
        *,
        mu_k: torch.Tensor,
        sigma_k: torch.Tensor,
        theta: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        theta_dec = self.quantizer._theta_for_decode(theta)
        residual = self.theta_decoder(theta_dec)
        if not self.theta_enabled:
            residual = torch.zeros_like(residual)
        return mu_k + sigma_k * residual, theta_dec

    def _decode(
        self,
        *,
        codes: torch.Tensor,
        mu_k: torch.Tensor,
        z_q: torch.Tensor,
        theta_dec: torch.Tensor,
        lengths: torch.Tensor | None,
    ) -> torch.Tensor:
        if self.local_output_theta:
            if self.decoder_type == "time":
                template = self.decoder(mu_k, lengths=lengths)
            else:
                template = self.decoder(mu_k)
            local_theta = theta_dec if self.theta_enabled else torch.zeros_like(theta_dec)
            basis = self.local_theta_basis[codes]
            return template + torch.einsum("bi,bitd->btd", local_theta, basis)

        dec_in = (
            z_q
            if self.decoder_type in {"latent", "time"}
            else torch.cat([mu_k, theta_dec], dim=-1)
        )
        if self.decoder_type == "time":
            return self.decoder(dec_in, lengths=lengths)
        return self.decoder(dec_in)

    def decode_hybrid(
        self,
        codes: torch.Tensor,
        theta: torch.Tensor,
        lengths: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        if theta.shape[-1] != self.theta_dim:
            raise ValueError(
                f"theta must have trailing dimension {self.theta_dim}, got {tuple(theta.shape)}"
            )
        sigma = self.quantizer.sigma().to(theta.device)
        mu_k = self.quantizer.code_mu.to(theta.device)[codes]
        sigma_k = sigma[codes]
        z_q, theta_dec = self._latent_from_hybrid(
            mu_k=mu_k,
            sigma_k=sigma_k,
            theta=theta,
        )
        x_hat = self._decode(
            codes=codes,
            mu_k=mu_k,
            z_q=z_q,
            theta_dec=theta_dec,
            lengths=lengths,
        )
        return {
            "x_hat": x_hat,
            "z_q": z_q,
            "theta_dec": theta_dec,
            "log_length_pred": self.length_head(z_q).squeeze(-1),
        }

    def forward(
        self,
        x: torch.Tensor,
        valid_mask: torch.Tensor | None = None,
        lengths: torch.Tensor | None = None,
        code_x: torch.Tensor | None = None,
        theta_x: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        # x: [B, T, D]
        if x.shape[-1] != self.d:
            raise ValueError(f"x must have trailing dimension {self.d}, got {tuple(x.shape)}")
        if code_x is not None and code_x.shape[:2] != x.shape[:2]:
            raise ValueError(f"code_x must match x [B,T], got {tuple(code_x.shape[:2])} != {tuple(x.shape[:2])}")
        if code_x is not None and code_x.shape[-1] != self.code_d:
            raise ValueError(f"code_x must have trailing dimension {self.code_d}, got {tuple(code_x.shape)}")
        if theta_x is not None and theta_x.shape[:2] != x.shape[:2]:
            raise ValueError(
                f"theta_x must match x [B,T], got {tuple(theta_x.shape[:2])} != {tuple(x.shape[:2])}"
            )
        if theta_x is not None and theta_x.shape[-1] != self.theta_d:
            raise ValueError(f"theta_x must have trailing dimension {self.theta_d}, got {tuple(theta_x.shape)}")
        if self.dual_view and code_x is None:
            raise ValueError("dual-view GMVQ requires code_x")
        z_e = self._encode(self.encoder, x if code_x is None else code_x, valid_mask)
        q = self.quantizer(z_e)
        theta_source = z_e
        full_theta = q.theta
        if self.dual_view and self.theta_enabled:
            assert self.theta_source_encoder is not None
            theta_input = x if theta_x is None else theta_x
            theta_source = self._encode(self.theta_source_encoder, theta_input, valid_mask)
            full_theta = (theta_source - q.mu_k) / q.sigma_k
        theta, theta_dec, residual = self._reduced_theta(full_theta)
        z_q_raw = q.mu_k + q.sigma_k * residual
        z_q = (
            z_e + (z_q_raw - z_e).detach()
            if self.quantizer.use_ste and not self.theta_enabled
            else z_q_raw
        )
        x_recon = self._decode(
            codes=q.codes,
            mu_k=q.mu_k,
            z_q=z_q,
            theta_dec=theta_dec,
            lengths=lengths,
        )
        out: dict[str, torch.Tensor] = {
            "x_recon": x_recon,
            "log_length_pred": self.length_head(z_q).squeeze(-1),
            "z_e": z_e,
            "z_theta_source": theta_source,
            "z_q": z_q,
            "codes": q.codes,
            "theta": theta,
            "theta_dec": theta_dec,
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
            "theta_dim": self.theta_dim,
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
            "theta_enabled": self.theta_enabled,
            "dual_view": self.dual_view,
            "local_output_theta": self.local_output_theta,
            "code_d": self.code_d,
            "theta_d": self.theta_d,
        }
