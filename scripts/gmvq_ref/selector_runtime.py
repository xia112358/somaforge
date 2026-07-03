#!/usr/bin/env python3
"""Runtime helpers for GMVQ code/theta selector inference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from gmvq.hyar_wrapper import FrozenGMVQCodec
except ModuleNotFoundError:
    gmvq_repo = Path("/home/xiaz/gmvq-vae")
    if gmvq_repo.exists():
        sys.path.insert(0, str(gmvq_repo))
    from gmvq.hyar_wrapper import FrozenGMVQCodec

from scripts.gmvq_ref.train_selector_code import SelectorMLP
from scripts.gmvq_ref.train_selector_theta import ThetaMLP


FEATURE_KEYS = (
    "height_scan",
    "root_pos_w",
    "root_quat_w",
    "root_lin_vel_w",
    "root_ang_vel_w",
    "joint_pos",
    "joint_vel",
)


@dataclass
class SelectorOutput:
    code: torch.Tensor
    theta: torch.Tensor
    x_hat: torch.Tensor
    z_q: torch.Tensor


def _as_2d_float(array: np.ndarray | torch.Tensor, *, device: torch.device) -> torch.Tensor:
    tensor = torch.as_tensor(array, dtype=torch.float32, device=device)
    return tensor.reshape(tensor.shape[0], -1) if tensor.ndim > 1 else tensor.reshape(1, -1)


def build_observation(
    *,
    height_scan: np.ndarray | torch.Tensor,
    root_pos_w: np.ndarray | torch.Tensor,
    root_quat_w: np.ndarray | torch.Tensor,
    root_lin_vel_w: np.ndarray | torch.Tensor,
    root_ang_vel_w: np.ndarray | torch.Tensor,
    joint_pos: np.ndarray | torch.Tensor,
    joint_vel: np.ndarray | torch.Tensor,
    device: str | torch.device = "cpu",
) -> torch.Tensor:
    """Build the selector observation in the policy-ref selector feature order."""
    dev = torch.device(device)
    parts = [
        _as_2d_float(height_scan, device=dev),
        _as_2d_float(root_pos_w, device=dev),
        _as_2d_float(root_quat_w, device=dev),
        _as_2d_float(root_lin_vel_w, device=dev),
        _as_2d_float(root_ang_vel_w, device=dev),
        _as_2d_float(joint_pos, device=dev),
        _as_2d_float(joint_vel, device=dev),
    ]
    batch = parts[0].shape[0]
    for part in parts:
        if part.shape[0] != batch:
            raise ValueError(f"all observation parts must share batch size {batch}, got {part.shape[0]}")
    return torch.cat(parts, dim=1)


class GMVQSelectorRuntime(torch.nn.Module):
    """Frozen `obs -> code/theta -> decoded ref segment` runtime wrapper."""

    def __init__(
        self,
        *,
        code_checkpoint: str | Path,
        theta_checkpoint: str | Path,
        gmvq_checkpoint: str | Path,
        device: str | torch.device = "cpu",
    ) -> None:
        super().__init__()
        self.device_ref = torch.device(device)

        code_ckpt = torch.load(Path(code_checkpoint).expanduser(), map_location="cpu", weights_only=False)
        code_cfg = code_ckpt["model_config"]
        self.code_model = SelectorMLP(
            input_dim=code_cfg["input_dim"],
            num_codes=code_cfg["num_codes"],
            hidden_dim=code_cfg["hidden_dim"],
            depth=code_cfg["depth"],
            dropout=code_cfg["dropout"],
        )
        self.code_model.load_state_dict(code_ckpt["model_state"])

        theta_ckpt = torch.load(Path(theta_checkpoint).expanduser(), map_location="cpu", weights_only=False)
        theta_cfg = theta_ckpt["model_config"]
        self.theta_model = ThetaMLP(
            input_dim=theta_cfg["input_dim"],
            theta_dim=theta_cfg["theta_dim"],
            hidden_dim=theta_cfg["hidden_dim"],
            depth=theta_cfg["depth"],
            dropout=theta_cfg["dropout"],
        )
        self.theta_model.load_state_dict(theta_ckpt["model_state"])

        self.gmvq_codec = FrozenGMVQCodec(gmvq_checkpoint, device=self.device_ref, trainable=False)
        self.num_codes = int(code_cfg["num_codes"])

        self.register_buffer("code_mean", torch.as_tensor(code_ckpt["norm"]["mean"], dtype=torch.float32))
        self.register_buffer("code_std", torch.as_tensor(code_ckpt["norm"]["std"], dtype=torch.float32))
        self.register_buffer("theta_x_mean", torch.as_tensor(theta_ckpt["x_norm"]["mean"], dtype=torch.float32))
        self.register_buffer("theta_x_std", torch.as_tensor(theta_ckpt["x_norm"]["std"], dtype=torch.float32))
        self.register_buffer("theta_mean", torch.as_tensor(theta_ckpt["theta_norm"]["mean"], dtype=torch.float32))
        self.register_buffer("theta_std", torch.as_tensor(theta_ckpt["theta_norm"]["std"], dtype=torch.float32))

        self.feature_keys = tuple(code_ckpt.get("feature_keys", FEATURE_KEYS))
        self.code_checkpoint = str(Path(code_checkpoint).expanduser())
        self.theta_checkpoint = str(Path(theta_checkpoint).expanduser())
        self.gmvq_checkpoint = str(Path(gmvq_checkpoint).expanduser())

        self.to(self.device_ref)
        self.eval()
        for param in self.parameters():
            param.requires_grad_(False)

    @property
    def ref_shape(self) -> tuple[int, int]:
        return (int(self.gmvq_codec.t), int(self.gmvq_codec.d))

    def predict_code(self, obs: torch.Tensor) -> torch.Tensor:
        obs = obs.to(self.device_ref, dtype=torch.float32)
        x = (obs - self.code_mean) / self.code_std
        return self.code_model(x).argmax(dim=1)

    def predict_theta(self, obs: torch.Tensor, code: torch.Tensor) -> torch.Tensor:
        obs = obs.to(self.device_ref, dtype=torch.float32)
        code = code.to(self.device_ref, dtype=torch.long)
        one_hot = torch.nn.functional.one_hot(code, num_classes=self.num_codes).to(dtype=obs.dtype)
        x_raw = torch.cat([obs, one_hot], dim=1)
        x = (x_raw - self.theta_x_mean) / self.theta_x_std
        theta_norm = self.theta_model(x)
        return theta_norm * self.theta_std + self.theta_mean

    def decode(self, code: torch.Tensor, theta: torch.Tensor) -> dict[str, torch.Tensor]:
        return self.gmvq_codec.decode_hybrid(code.to(self.device_ref), theta.to(self.device_ref))

    @torch.no_grad()
    def forward(self, obs: torch.Tensor, code: torch.Tensor | None = None) -> SelectorOutput:
        obs = obs.to(self.device_ref, dtype=torch.float32)
        k = self.predict_code(obs) if code is None else code.to(self.device_ref, dtype=torch.long)
        theta = self.predict_theta(obs, k)
        dec = self.decode(k, theta)
        return SelectorOutput(code=k, theta=theta, x_hat=dec["x_hat"], z_q=dec["z_q"])

    def metadata(self) -> dict[str, Any]:
        return {
            "schema": "gmvq_selector_runtime_v1",
            "feature_keys": list(self.feature_keys),
            "num_codes": self.num_codes,
            "ref_shape": list(self.ref_shape),
            "code_checkpoint": self.code_checkpoint,
            "theta_checkpoint": self.theta_checkpoint,
            "gmvq_checkpoint": self.gmvq_checkpoint,
        }
