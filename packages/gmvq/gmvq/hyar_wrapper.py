from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import torch
from torch import nn
import torch.nn.functional as F

from .data import NormStats
from .models import GMVQAutoEncoder
from somaforge_core.robot_assets import validate_g1_asset_metadata


def _mlp(in_dim: int, out_dim: int, hidden_dim: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Linear(in_dim, hidden_dim),
        nn.GELU(),
        nn.Linear(hidden_dim, hidden_dim),
        nn.GELU(),
        nn.Linear(hidden_dim, out_dim),
    )


class FrozenGMVQCodec(nn.Module):
    """Frozen interface around a trained residual GMVQ segment tokenizer.

    This keeps the GMVQ segment latent (`z_e`, `z_q`) separate from the HyAR
    latent action (`z_h`). By default all GMVQ parameters are frozen.
    """

    def __init__(
        self,
        checkpoint: str | Path,
        device: str | torch.device = "cpu",
        trainable: bool = False,
    ) -> None:
        super().__init__()
        ckpt = torch.load(checkpoint, map_location="cpu", weights_only=False)
        validate_g1_asset_metadata(ckpt.get("robot_asset"), context=f"GMVQ checkpoint {checkpoint}")
        contact_provenance = ckpt.get("contact_force_provenance")
        if not isinstance(contact_provenance, dict) or contact_provenance.get("source_backend") != "isaaclab3_newton_mjwarp":
            raise ValueError(f"GMVQ checkpoint {checkpoint} has no Newton contact-force provenance")
        self.robot_asset = dict(ckpt["robot_asset"])
        self.contact_force_provenance = dict(contact_provenance)
        cfg = ckpt["model_config"]
        self.model = GMVQAutoEncoder(**cfg)
        self.model.load_state_dict(ckpt["model_state"])
        self.model.to(device)
        self.model.train(trainable)
        for param in self.model.parameters():
            param.requires_grad_(trainable)

        self.model_config = cfg
        self.trainable = trainable
        self.device_ref = torch.device(device)
        ns = ckpt.get("norm_stats")
        self.norm_stats: Optional[NormStats] = None
        if ns is not None:
            self.norm_stats = NormStats(mean=ns["mean"], std=ns["std"])

    @property
    def num_codes(self) -> int:
        return int(self.model.num_codes)

    @property
    def theta_dim(self) -> int:
        return int(self.model.latent_dim)

    @property
    def t(self) -> int:
        return int(self.model.t)

    @property
    def d(self) -> int:
        return int(self.model.d)

    def normalize(self, x: torch.Tensor) -> torch.Tensor:
        if self.norm_stats is None:
            return x
        return (x - self.norm_stats.mean.to(x.device)) / self.norm_stats.std.to(x.device)

    def encode_segment(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """Encode normalized segments x: [B, T, D] to GMVQ hybrid code."""
        ctx = torch.enable_grad() if self.trainable else torch.no_grad()
        with ctx:
            out = self.model(x)
        return {
            "k": out["codes"],
            "theta": out["theta"],
            "z_e": out["z_e"],
            "z_q": out["z_q"],
            "x_recon": out["x_recon"],
        }

    def decode_hybrid(self, k: torch.Tensor, theta: torch.Tensor) -> dict[str, torch.Tensor]:
        """Decode GMVQ hybrid code `(k, theta)` back to segment space."""
        q = self.model.quantizer
        sigma = q.sigma().to(theta.device)
        mu_k = q.code_mu.to(theta.device)[k]
        sigma_k = sigma[k]
        theta_dec = q._theta_for_decode(theta)
        z_q = mu_k + sigma_k * theta_dec
        if self.model.decoder_type in {"latent", "time"}:
            dec_in = z_q
        else:
            dec_in = torch.cat([mu_k, theta_dec], dim=-1)
        x_hat = self.model.decoder(dec_in)
        return {"x_hat": x_hat, "z_q": z_q, "theta_dec": theta_dec}


class HyARActionVAE(nn.Module):
    """HyAR-style conditional VAE for the GMVQ hybrid code `(k, theta)`.

    HyAR reference ideas:
    - Learnable discrete action embedding table.
    - Conditional VAE for continuous parameters conditioned on action embedding.
    - Optional state conditioning.
    - Optional classifier from latent action for latent-to-k retrieval.
    """

    def __init__(
        self,
        num_codes: int,
        theta_dim: int,
        action_emb_dim: int = 16,
        hyar_latent_dim: int = 4,
        state_dim: Optional[int] = None,
        hidden_dim: int = 128,
        use_state_conditioning: bool = False,
        use_k_classifier: bool = True,
    ) -> None:
        super().__init__()
        self.num_codes = num_codes
        self.theta_dim = theta_dim
        self.action_emb_dim = action_emb_dim
        self.hyar_latent_dim = hyar_latent_dim
        self.state_dim = state_dim
        self.hidden_dim = hidden_dim
        self.use_state_conditioning = use_state_conditioning
        self.use_k_classifier = use_k_classifier

        cond_dim = action_emb_dim + (state_dim or 0 if use_state_conditioning else 0)
        self.action_embedding = nn.Embedding(num_codes, action_emb_dim)

        enc_in_dim = theta_dim + cond_dim
        self.encoder = _mlp(enc_in_dim, 2 * hyar_latent_dim, hidden_dim)
        dec_in_dim = hyar_latent_dim + cond_dim
        self.decoder = _mlp(dec_in_dim, theta_dim, hidden_dim)

        cls_in_dim = hyar_latent_dim + ((state_dim or 0) if use_state_conditioning else 0)
        self.k_classifier = _mlp(cls_in_dim, num_codes, hidden_dim) if use_k_classifier else None

        dyn_in_dim = hyar_latent_dim + (state_dim or 0)
        self.dynamics_head = _mlp(dyn_in_dim, state_dim, hidden_dim) if state_dim is not None else None

    def _state(self, state: Optional[torch.Tensor]) -> Optional[torch.Tensor]:
        if not self.use_state_conditioning:
            return None
        if state is None:
            raise ValueError("state conditioning is enabled but state is None")
        return state

    def condition(self, k: torch.Tensor, state: Optional[torch.Tensor] = None) -> torch.Tensor:
        e_k = self.action_embedding(k)
        s = self._state(state)
        if s is None:
            return e_k
        return torch.cat([e_k, s], dim=-1)

    def encode(
        self,
        k: torch.Tensor,
        theta: torch.Tensor,
        state: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        cond = self.condition(k, state)
        h = self.encoder(torch.cat([theta, cond], dim=-1))
        z_mu, z_logvar = h.chunk(2, dim=-1)
        return z_mu, z_logvar.clamp(-10.0, 6.0)

    @staticmethod
    def reparameterize(z_mu: torch.Tensor, z_logvar: torch.Tensor) -> torch.Tensor:
        eps = torch.randn_like(z_mu)
        return z_mu + eps * torch.exp(0.5 * z_logvar)

    def decode(
        self,
        k: torch.Tensor,
        z_h: torch.Tensor,
        state: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        cond = self.condition(k, state)
        return self.decoder(torch.cat([z_h, cond], dim=-1))

    def classify_k(self, z_h: torch.Tensor, state: Optional[torch.Tensor] = None) -> Optional[torch.Tensor]:
        if self.k_classifier is None:
            return None
        if self.use_state_conditioning:
            if state is None:
                raise ValueError("state conditioning is enabled but state is None")
            inp = torch.cat([z_h, state], dim=-1)
        else:
            inp = z_h
        return self.k_classifier(inp)

    def predict_next_state(self, z_h: torch.Tensor, state: Optional[torch.Tensor]) -> Optional[torch.Tensor]:
        if self.dynamics_head is None or state is None:
            return None
        return self.dynamics_head(torch.cat([state, z_h], dim=-1))

    def forward(
        self,
        k: torch.Tensor,
        theta: torch.Tensor,
        state: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        z_mu, z_logvar = self.encode(k, theta, state)
        z_h = self.reparameterize(z_mu, z_logvar) if self.training else z_mu
        theta_hat = self.decode(k, z_h, state)
        out: dict[str, torch.Tensor] = {
            "z_h": z_h,
            "z_mu": z_mu,
            "z_logvar": z_logvar,
            "theta_hat": theta_hat,
        }
        k_logits = self.classify_k(z_mu, state)
        if k_logits is not None:
            out["k_logits"] = k_logits
        pred_next_state = self.predict_next_state(z_h, state)
        if pred_next_state is not None:
            out["pred_next_state"] = pred_next_state
        return out

    def config(self) -> dict[str, Any]:
        return {
            "num_codes": self.num_codes,
            "theta_dim": self.theta_dim,
            "action_emb_dim": self.action_emb_dim,
            "hyar_latent_dim": self.hyar_latent_dim,
            "state_dim": self.state_dim,
            "hidden_dim": self.hidden_dim,
            "use_state_conditioning": self.use_state_conditioning,
            "use_k_classifier": self.use_k_classifier,
        }


class HyARNestedAutoEncoder(nn.Module):
    """Full nested path: segment -> GMVQ `(k, theta)` -> HyAR `z_h` -> segment."""

    def __init__(self, gmvq_codec: FrozenGMVQCodec, hyar: HyARActionVAE) -> None:
        super().__init__()
        self.gmvq_codec = gmvq_codec
        self.hyar = hyar

    def forward(
        self,
        x: torch.Tensor,
        state: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        g = self.gmvq_codec.encode_segment(x)
        h = self.hyar(g["k"], g["theta"], state)
        dec = self.gmvq_codec.decode_hybrid(g["k"], h["theta_hat"])
        out = {
            "k": g["k"],
            "theta": g["theta"],
            "z_e": g["z_e"],
            "z_q": g["z_q"],
            "x_gmvq_recon": g["x_recon"],
            "z_h": h["z_h"],
            "z_mu": h["z_mu"],
            "z_logvar": h["z_logvar"],
            "theta_hat": h["theta_hat"],
            "x_hat": dec["x_hat"],
            "z_q_hat": dec["z_q"],
        }
        for key in ("k_logits", "pred_next_state"):
            if key in h:
                out[key] = h[key]
        return out


class HyARPolicyActionDecoder(nn.Module):
    """Policy-facing decoder for later RL use.

    Mode A: policy outputs `(k, z_h)`.
    Mode B: policy outputs only `z_h`; a classifier recovers `k`.
    """

    def __init__(self, gmvq_codec: FrozenGMVQCodec, hyar: HyARActionVAE) -> None:
        super().__init__()
        self.gmvq_codec = gmvq_codec
        self.hyar = hyar

    def decode_with_known_k(
        self,
        k: torch.Tensor,
        z_h: torch.Tensor,
        state: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        theta = self.hyar.decode(k, z_h, state)
        dec = self.gmvq_codec.decode_hybrid(k, theta)
        return {"k": k, "theta": theta, "x_hat": dec["x_hat"], "z_q": dec["z_q"]}

    def decode_from_latent(
        self,
        z_h: torch.Tensor,
        state: Optional[torch.Tensor] = None,
        sample: bool = False,
    ) -> dict[str, torch.Tensor]:
        k_logits = self.hyar.classify_k(z_h, state)
        if k_logits is None:
            raise RuntimeError("HyARActionVAE was created without k_classifier")
        if sample:
            k = torch.distributions.Categorical(logits=k_logits).sample()
        else:
            k = k_logits.argmax(dim=-1)
        out = self.decode_with_known_k(k, z_h, state)
        out["k_logits"] = k_logits
        return out


@dataclass
class HyARLossWeights:
    beta_kl: float = 1e-3
    beta_x: float = 1.0
    beta_vel: float = 0.1
    beta_k: float = 0.1
    beta_dyn: float = 0.1
    beta_latent: float = 0.0


def compute_hyar_loss(
    x: torch.Tensor,
    output: dict[str, torch.Tensor],
    weights: HyARLossWeights,
    next_state: Optional[torch.Tensor] = None,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    theta_mse = F.mse_loss(output["theta_hat"], output["theta"])
    x_recon_mse = F.mse_loss(output["x_hat"], x)
    if x.shape[1] > 1:
        velocity_mse = F.mse_loss(output["x_hat"][:, 1:] - output["x_hat"][:, :-1], x[:, 1:] - x[:, :-1])
    else:
        velocity_mse = torch.zeros((), device=x.device)

    z_mu = output["z_mu"]
    z_logvar = output["z_logvar"]
    kl_loss = -0.5 * (1.0 + z_logvar - z_mu.square() - z_logvar.exp()).sum(dim=-1).mean()
    latent_norm = output["z_h"].square().sum(dim=-1).mean()

    if "k_logits" in output:
        k_cls_loss = F.cross_entropy(output["k_logits"], output["k"])
        k_cls_acc = (output["k_logits"].argmax(dim=-1) == output["k"]).float().mean()
    else:
        k_cls_loss = torch.zeros((), device=x.device)
        k_cls_acc = torch.zeros((), device=x.device)

    if next_state is not None and "pred_next_state" in output:
        dynamics_loss = F.mse_loss(output["pred_next_state"], next_state)
    else:
        dynamics_loss = torch.zeros((), device=x.device)

    total = (
        theta_mse
        + weights.beta_kl * kl_loss
        + weights.beta_x * x_recon_mse
        + weights.beta_vel * velocity_mse
        + weights.beta_k * k_cls_loss
        + weights.beta_dyn * dynamics_loss
        + weights.beta_latent * latent_norm
    )

    codes = output["k"]
    hist = torch.bincount(codes.reshape(-1), minlength=int(codes.max().item()) + 1).float()
    theta_abs = output["theta_hat"].abs()
    metrics = {
        "total_loss": total.detach(),
        "theta_mse": theta_mse.detach(),
        "x_recon_mse": x_recon_mse.detach(),
        "velocity_mse": velocity_mse.detach(),
        "kl_loss": kl_loss.detach(),
        "k_cls_loss": k_cls_loss.detach(),
        "k_cls_acc": k_cls_acc.detach(),
        "dynamics_mse": dynamics_loss.detach(),
        "latent_norm": latent_norm.detach(),
        "z_mu_mean": z_mu.mean().detach(),
        "z_mu_std": z_mu.std(unbiased=False).detach(),
        "z_h_norm": output["z_h"].norm(dim=-1).mean().detach(),
        "theta_hat_abs_max": theta_abs.max().detach(),
        "theta_hat_clip_ratio": (theta_abs >= 0.5).float().mean().detach(),
        "active_codes": (hist > 0).sum().detach(),
    }
    return total, metrics
