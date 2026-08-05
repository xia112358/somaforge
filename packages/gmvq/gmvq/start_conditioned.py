"""Start-state-conditioned residual decoding for absolute GMVQ atoms."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from somaforge_core.robot_assets import validate_g1_asset_metadata
from torch import nn


class StartConditionedDecoder(nn.Module):
    """Generate an absolute future atom conditioned on its actual entry state."""

    def __init__(
        self,
        *,
        feature_dim: int = 71,
        num_codes: int = 13,
        theta_dim: int = 4,
        hidden_dim: int = 256,
        depth: int = 3,
        condition_decay_power: float = 0.0,
        condition_root: bool = True,
        anchor_start: bool = False,
    ) -> None:
        super().__init__()
        self.feature_dim = int(feature_dim)
        self.num_codes = int(num_codes)
        self.theta_dim = int(theta_dim)
        self.hidden_dim = int(hidden_dim)
        self.depth = int(depth)
        self.condition_decay_power = float(condition_decay_power)
        self.condition_root = bool(condition_root)
        self.anchor_start = bool(anchor_start)
        input_dim = 2 * self.feature_dim + self.num_codes + self.theta_dim + 5
        layers: list[nn.Module] = []
        dim = input_dim
        for _ in range(self.depth):
            layers.extend((nn.Linear(dim, self.hidden_dim), nn.GELU()))
            dim = self.hidden_dim
        output = nn.Linear(dim, self.feature_dim)
        nn.init.zeros_(output.weight)
        nn.init.zeros_(output.bias)
        layers.append(output)
        self.net = nn.Sequential(*layers)

    @staticmethod
    def _time_features(base: torch.Tensor, lengths: torch.Tensor | None) -> torch.Tensor:
        batch, frames = base.shape[:2]
        index = torch.arange(frames, dtype=base.dtype, device=base.device).view(1, frames)
        if lengths is None:
            denominator = torch.full((batch, 1), max(frames - 1, 1), dtype=base.dtype, device=base.device)
        else:
            denominator = (lengths.to(device=base.device, dtype=base.dtype).view(batch, 1) - 1.0).clamp_min(1.0)
        u = (index / denominator).clamp(0.0, 1.0)
        return torch.stack(
            (
                u,
                torch.sin(torch.pi * u),
                torch.cos(torch.pi * u),
                torch.sin(2.0 * torch.pi * u),
                torch.cos(2.0 * torch.pi * u),
            ),
            dim=-1,
        )

    def forward(
        self,
        base: torch.Tensor,
        *,
        start_state: torch.Tensor,
        codes: torch.Tensor,
        theta: torch.Tensor,
        lengths: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if base.ndim != 3 or base.shape[-1] != self.feature_dim:
            raise ValueError(f"base must be [B,T,{self.feature_dim}], got {tuple(base.shape)}")
        if start_state.shape != (base.shape[0], self.feature_dim):
            raise ValueError(f"start_state must be {(base.shape[0], self.feature_dim)}, got {tuple(start_state.shape)}")
        if theta.shape != (base.shape[0], self.theta_dim):
            raise ValueError(f"theta must be {(base.shape[0], self.theta_dim)}, got {tuple(theta.shape)}")
        one_hot = F.one_hot(codes.long(), num_classes=self.num_codes).to(dtype=base.dtype)
        context = torch.cat((start_state, one_hot, theta), dim=-1)
        context = context[:, None, :].expand(-1, base.shape[1], -1)
        time = self._time_features(base, lengths)
        correction = self.net(torch.cat((base, context, time), dim=-1))
        if not self.condition_root and self.feature_dim == 71:
            feature_mask = torch.ones(self.feature_dim, dtype=correction.dtype, device=correction.device)
            feature_mask[:7] = 0.0
            feature_mask[36:42] = 0.0
            correction = correction * feature_mask
        if self.condition_decay_power > 0.0:
            correction = correction * (1.0 - time[..., :1]).pow(self.condition_decay_power)
        output = base + correction
        if self.anchor_start:
            # The measured entry state is both a network condition (see
            # ``context`` above) and the exact first output.  Frames 1..T are
            # generated jointly by the decoder from that condition; they are
            # not a runtime blend or an integrated relative trajectory.
            output = torch.cat((start_state[:, None], output[:, 1:]), dim=1)
        return output

    def config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "feature_dim": self.feature_dim,
            "num_codes": self.num_codes,
            "theta_dim": self.theta_dim,
            "hidden_dim": self.hidden_dim,
            "depth": self.depth,
            "condition_decay_power": self.condition_decay_power,
            "condition_root": self.condition_root,
            "anchor_start": self.anchor_start,
        }
        return config


def load_start_conditioned_decoder(
    checkpoint: str | Path | Mapping[str, Any],
    *,
    device: str | torch.device,
) -> StartConditionedDecoder:
    if isinstance(checkpoint, Mapping):
        payload = dict(checkpoint)
        context = "embedded start-conditioned decoder"
    else:
        payload = torch.load(Path(checkpoint).expanduser(), map_location="cpu", weights_only=False)
        context = f"start-conditioned decoder {checkpoint}"
    validate_g1_asset_metadata(payload.get("robot_asset"), context=context)
    model = StartConditionedDecoder(**payload["model_config"])
    model.load_state_dict(payload["model_state"])
    model.to(device)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model


__all__ = ["StartConditionedDecoder", "load_start_conditioned_decoder"]
