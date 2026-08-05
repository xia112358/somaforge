"""Current-frame-conditioned generation of one complete future motion atom."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from somaforge_core.robot_assets import validate_g1_asset_metadata
from torch import nn


def canonical_boundary_state(joint_pos: torch.Tensor, joint_vel: torch.Tensor) -> torch.Tensor:
    """Remove global XY/yaw while retaining tilt, local root velocity, and joints."""
    if joint_pos.ndim != 2 or joint_pos.shape[1] != 36:
        raise ValueError(f"joint_pos must be [B,36], got {tuple(joint_pos.shape)}")
    if joint_vel.shape != (joint_pos.shape[0], 35):
        raise ValueError(f"joint_vel must be [B,35], got {tuple(joint_vel.shape)}")
    quaternion = joint_pos[:, 3:7]
    quaternion = quaternion / quaternion.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
    w, x, y, z = quaternion.unbind(dim=-1)
    yaw = torch.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y.square() + z.square()))
    half = -0.5 * yaw
    yaw_inverse = torch.stack(
        (torch.cos(half), torch.zeros_like(half), torch.zeros_like(half), torch.sin(half)),
        dim=-1,
    )
    aw, ax, ay, az = yaw_inverse.unbind(dim=-1)
    tilt = torch.stack(
        (
            aw * w - ax * x - ay * y - az * z,
            aw * x + ax * w + ay * z - az * y,
            aw * y - ax * z + ay * w + az * x,
            aw * z + ax * y - ay * x + az * w,
        ),
        dim=-1,
    )
    tilt = torch.where(tilt[:, :1] < 0.0, -tilt, tilt)

    cosine = torch.cos(yaw)
    sine = torch.sin(yaw)

    def yaw_local(vector: torch.Tensor) -> torch.Tensor:
        return torch.stack(
            (
                cosine * vector[:, 0] + sine * vector[:, 1],
                -sine * vector[:, 0] + cosine * vector[:, 1],
                vector[:, 2],
            ),
            dim=-1,
        )

    return torch.cat(
        (
            tilt,
            yaw_local(joint_vel[:, :3]),
            yaw_local(joint_vel[:, 3:6]),
            joint_pos[:, 7:],
            joint_vel[:, 6:],
        ),
        dim=-1,
    )


class SpatialHeightEncoder(nn.Module):
    """Encode flattened height samples using their original 2-D grid layout."""

    def __init__(
        self,
        grid_shapes: tuple[tuple[int, int], ...],
        output_dim: int,
        *,
        antialias: bool = False,
    ) -> None:
        super().__init__()
        if not grid_shapes or any(rows < 2 or cols < 2 for rows, cols in grid_shapes):
            raise ValueError(f"scan_grid_shapes must contain 2-D grids, got {grid_shapes}")
        self.grid_shapes = tuple((int(rows), int(cols)) for rows, cols in grid_shapes)
        self.point_count = sum(rows * cols for rows, cols in self.grid_shapes)
        self.antialias = bool(antialias)
        self.branches = nn.ModuleList(
            nn.Sequential(
                nn.Conv2d(1, 16, kernel_size=3, padding=1),
                nn.GELU(),
                nn.Conv2d(16, 32, kernel_size=3, padding=1),
                nn.GELU(),
                nn.AdaptiveAvgPool2d((2, 2)),
                nn.Flatten(),
            )
            for _ in self.grid_shapes
        )
        self.projection = nn.Sequential(
            nn.Linear(128 * len(self.grid_shapes), output_dim),
            nn.LayerNorm(output_dim),
            nn.GELU(),
        )

    def forward(self, height: torch.Tensor) -> torch.Tensor:
        if height.ndim != 2 or height.shape[1] != self.point_count:
            raise ValueError(f"height must be [B,{self.point_count}], got {tuple(height.shape)}")
        features: list[torch.Tensor] = []
        offset = 0
        for (rows, cols), branch in zip(self.grid_shapes, self.branches, strict=True):
            count = rows * cols
            grid = height[:, offset : offset + count].reshape(-1, 1, rows, cols)
            if self.antialias:
                kernel = grid.new_tensor((1.0, 2.0, 1.0, 2.0, 4.0, 2.0, 1.0, 2.0, 1.0)).reshape(1, 1, 3, 3)
                grid = F.conv2d(F.pad(grid, (1, 1, 1, 1), mode="replicate"), kernel / 16.0)
            features.append(branch(grid))
            offset += count
        return self.projection(torch.cat(features, dim=-1))


class CurrentFrameFutureModel(nn.Module):
    """Jointly infer code, theta, and an absolute future from one current frame."""

    def __init__(
        self,
        *,
        height_dim: int,
        state_dim: int,
        feature_dim: int = 71,
        num_codes: int = 14,
        theta_dim: int = 4,
        max_frames: int = 127,
        branch_dim: int = 128,
        context_dim: int = 256,
        code_embed_dim: int = 32,
        decoder_dim: int = 256,
        decoder_layers: int = 2,
        time_harmonics: int = 8,
        scan_grid_shapes: tuple[tuple[int, int], ...] | None = None,
        previous_code_embed_dim: int = 16,
        previous_code_logit_scale: float = 1.0,
        previous_code_dropout: float = 0.25,
        terrain_scalar_dim: int = 0,
        scan_antialias: bool = False,
    ) -> None:
        super().__init__()
        self.height_dim = int(height_dim)
        self.state_dim = int(state_dim)
        self.feature_dim = int(feature_dim)
        self.num_codes = int(num_codes)
        self.theta_dim = int(theta_dim)
        self.max_frames = int(max_frames)
        self.branch_dim = int(branch_dim)
        self.context_dim = int(context_dim)
        self.code_embed_dim = int(code_embed_dim)
        self.decoder_dim = int(decoder_dim)
        self.decoder_layers = int(decoder_layers)
        self.time_harmonics = int(time_harmonics)
        self.scan_grid_shapes = None if scan_grid_shapes is None else tuple(tuple(x) for x in scan_grid_shapes)
        self.previous_code_embed_dim = int(previous_code_embed_dim)
        self.previous_code_logit_scale = float(previous_code_logit_scale)
        self.previous_code_dropout = float(previous_code_dropout)
        self.terrain_scalar_dim = int(terrain_scalar_dim)
        self.scan_antialias = bool(scan_antialias)
        self.height_encoder = (
            SpatialHeightEncoder(
                self.scan_grid_shapes,
                self.branch_dim,
                antialias=self.scan_antialias,
            )
            if self.scan_grid_shapes is not None
            else nn.Sequential(
                nn.Linear(self.height_dim, self.branch_dim),
                nn.LayerNorm(self.branch_dim),
                nn.GELU(),
                nn.Linear(self.branch_dim, self.branch_dim),
                nn.GELU(),
            )
        )
        self.state_encoder = nn.Sequential(
            nn.Linear(self.state_dim, self.branch_dim),
            nn.LayerNorm(self.branch_dim),
            nn.GELU(),
            nn.Linear(self.branch_dim, self.branch_dim),
            nn.GELU(),
        )
        self.context_encoder = nn.Sequential(
            nn.Linear(2 * self.branch_dim, self.context_dim),
            nn.LayerNorm(self.context_dim),
            nn.GELU(),
            nn.Linear(self.context_dim, self.context_dim),
            nn.GELU(),
        )
        self.code_head = nn.Linear(self.context_dim, self.num_codes)
        self.previous_code_embedding = nn.Embedding(self.num_codes + 1, self.previous_code_embed_dim)
        self.previous_code_head = nn.Linear(self.previous_code_embed_dim, self.num_codes, bias=False)
        self.code_embedding = nn.Parameter(torch.empty(self.num_codes, self.code_embed_dim))
        nn.init.normal_(self.code_embedding, std=0.02)
        latent_dim = self.context_dim + self.code_embed_dim
        self.theta_head = nn.Sequential(
            nn.Linear(latent_dim + self.terrain_scalar_dim, self.branch_dim),
            nn.GELU(),
            nn.Linear(self.branch_dim, self.theta_dim),
        )
        time_dim = 1 + 2 * self.time_harmonics
        self.decoder_input = nn.Linear(latent_dim + self.theta_dim + time_dim, self.decoder_dim)
        self.decoder = nn.GRU(
            input_size=self.decoder_dim,
            hidden_size=self.decoder_dim,
            num_layers=self.decoder_layers,
            batch_first=True,
        )
        self.decoder_initial = nn.Linear(latent_dim + self.theta_dim, self.decoder_layers * self.decoder_dim)
        self.trajectory_head = nn.Linear(self.decoder_dim, self.feature_dim)

    def _time_features(self, batch: int, dtype: torch.dtype, device: torch.device) -> torch.Tensor:
        u = torch.linspace(0.0, 1.0, self.max_frames, dtype=dtype, device=device)
        features = [u]
        for harmonic in range(1, self.time_harmonics + 1):
            angle = torch.pi * float(harmonic) * u
            features.extend((torch.sin(angle), torch.cos(angle)))
        return torch.stack(features, dim=-1)[None].expand(batch, -1, -1)

    def forward(
        self,
        observation: torch.Tensor,
        *,
        start_state: torch.Tensor,
        previous_code: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        expected = self.height_dim + self.terrain_scalar_dim + self.state_dim
        if observation.ndim != 2 or observation.shape[1] != expected:
            raise ValueError(f"observation must be [B,{expected}], got {tuple(observation.shape)}")
        if start_state.shape != (observation.shape[0], self.feature_dim):
            raise ValueError(
                f"start_state must be {(observation.shape[0], self.feature_dim)}, got {tuple(start_state.shape)}"
            )
        height = self.height_encoder(observation[:, : self.height_dim])
        terrain_scalar = observation[:, self.height_dim : self.height_dim + self.terrain_scalar_dim]
        state = self.state_encoder(observation[:, self.height_dim + self.terrain_scalar_dim :])
        context = self.context_encoder(torch.cat((height, state), dim=-1))
        logits = self._code_logits(context, previous_code)
        probabilities = logits.softmax(dim=-1)
        codes = logits.argmax(dim=-1)
        hard = F.one_hot(codes, num_classes=self.num_codes).to(probabilities)
        code_weights = hard + probabilities - probabilities.detach()
        code_context = code_weights @ self.code_embedding
        latent = torch.cat((context, code_context), dim=-1)
        theta = self.theta_head(torch.cat((latent, terrain_scalar), dim=-1))
        decoder_context = torch.cat((latent, theta), dim=-1)
        time = self._time_features(observation.shape[0], observation.dtype, observation.device)
        repeated = decoder_context[:, None].expand(-1, self.max_frames, -1)
        decoder_input = self.decoder_input(torch.cat((repeated, time), dim=-1))
        hidden = self.decoder_initial(decoder_context)
        hidden = hidden.reshape(observation.shape[0], self.decoder_layers, self.decoder_dim).transpose(0, 1).contiguous()
        decoded, _ = self.decoder(decoder_input, hidden)
        trajectory = self.trajectory_head(decoded)
        trajectory = torch.cat((start_state[:, None], trajectory[:, 1:]), dim=1)
        return {
            "code_logits": logits,
            "codes": codes,
            "theta": theta,
            "trajectory": trajectory,
        }

    def _code_logits(self, context: torch.Tensor, previous_code: torch.Tensor | None) -> torch.Tensor:
        logits = self.code_head(context)
        residual = self.previous_code_logits(previous_code, batch_size=context.shape[0], device=context.device)
        return logits + self.previous_code_logit_scale * residual

    def previous_code_logits(
        self,
        previous_code: torch.Tensor | None,
        *,
        batch_size: int,
        device: torch.device,
        apply_dropout: bool = True,
    ) -> torch.Tensor:
        if previous_code is None:
            previous_index = torch.full(
                (batch_size,), self.num_codes, dtype=torch.long, device=device
            )
        else:
            previous_index = previous_code.to(device=device, dtype=torch.long)
            previous_index = torch.where(
                (previous_index >= 0) & (previous_index < self.num_codes),
                previous_index,
                self.num_codes,
            )
        if apply_dropout and self.training and self.previous_code_dropout > 0.0:
            dropped = torch.rand(previous_index.shape, device=device) < self.previous_code_dropout
            previous_index = torch.where(dropped, self.num_codes, previous_index)
        return self.previous_code_head(self.previous_code_embedding(previous_index))

    def config(self) -> dict[str, int]:
        return {
            "height_dim": self.height_dim,
            "state_dim": self.state_dim,
            "feature_dim": self.feature_dim,
            "num_codes": self.num_codes,
            "theta_dim": self.theta_dim,
            "max_frames": self.max_frames,
            "branch_dim": self.branch_dim,
            "context_dim": self.context_dim,
            "code_embed_dim": self.code_embed_dim,
            "decoder_dim": self.decoder_dim,
            "decoder_layers": self.decoder_layers,
            "time_harmonics": self.time_harmonics,
            "scan_grid_shapes": self.scan_grid_shapes,
            "previous_code_embed_dim": self.previous_code_embed_dim,
            "previous_code_logit_scale": self.previous_code_logit_scale,
            "previous_code_dropout": self.previous_code_dropout,
            "terrain_scalar_dim": self.terrain_scalar_dim,
            "scan_antialias": self.scan_antialias,
        }


class CausalSegmentFutureModel(nn.Module):
    """Generate every future state recurrently from the segment's measured start."""

    def __init__(
        self,
        *,
        height_dim: int,
        state_dim: int,
        feature_dim: int = 71,
        num_codes: int = 14,
        theta_dim: int = 4,
        max_frames: int = 127,
        branch_dim: int = 128,
        context_dim: int = 256,
        code_embed_dim: int = 32,
        dynamics_dim: int = 256,
        dynamics_layers: int = 2,
        time_harmonics: int = 8,
        use_guide: bool = False,
        guide_residual_output: bool = False,
        joint_trajectory_output: bool = False,
        start_residual_conditioning: bool = False,
        scan_grid_shapes: tuple[tuple[int, int], ...] | None = None,
        previous_code_embed_dim: int = 16,
        previous_code_logit_scale: float = 1.0,
        previous_code_dropout: float = 0.25,
        terrain_scalar_dim: int = 0,
        scan_antialias: bool = False,
    ) -> None:
        super().__init__()
        self.height_dim = int(height_dim)
        self.state_dim = int(state_dim)
        self.feature_dim = int(feature_dim)
        self.num_codes = int(num_codes)
        self.theta_dim = int(theta_dim)
        self.max_frames = int(max_frames)
        self.branch_dim = int(branch_dim)
        self.context_dim = int(context_dim)
        self.code_embed_dim = int(code_embed_dim)
        self.dynamics_dim = int(dynamics_dim)
        self.dynamics_layers = int(dynamics_layers)
        self.time_harmonics = int(time_harmonics)
        self.use_guide = bool(use_guide)
        self.guide_residual_output = bool(guide_residual_output)
        self.joint_trajectory_output = bool(joint_trajectory_output)
        self.start_residual_conditioning = bool(start_residual_conditioning)
        self.scan_grid_shapes = None if scan_grid_shapes is None else tuple(tuple(x) for x in scan_grid_shapes)
        self.previous_code_embed_dim = int(previous_code_embed_dim)
        self.previous_code_logit_scale = float(previous_code_logit_scale)
        self.previous_code_dropout = float(previous_code_dropout)
        self.terrain_scalar_dim = int(terrain_scalar_dim)
        self.scan_antialias = bool(scan_antialias)
        if self.guide_residual_output and not self.use_guide:
            raise ValueError("guide_residual_output requires use_guide=True")
        if self.joint_trajectory_output and not self.use_guide:
            raise ValueError("joint_trajectory_output requires use_guide=True")
        if self.joint_trajectory_output and self.guide_residual_output:
            raise ValueError("joint_trajectory_output and guide_residual_output are mutually exclusive")
        if self.start_residual_conditioning and not self.joint_trajectory_output:
            raise ValueError("start_residual_conditioning requires joint_trajectory_output=True")
        self.height_encoder = (
            SpatialHeightEncoder(
                self.scan_grid_shapes,
                self.branch_dim,
                antialias=self.scan_antialias,
            )
            if self.scan_grid_shapes is not None
            else nn.Sequential(
                nn.Linear(self.height_dim, self.branch_dim),
                nn.LayerNorm(self.branch_dim),
                nn.GELU(),
                nn.Linear(self.branch_dim, self.branch_dim),
                nn.GELU(),
            )
        )
        self.state_encoder = nn.Sequential(
            nn.Linear(self.state_dim, self.branch_dim),
            nn.LayerNorm(self.branch_dim),
            nn.GELU(),
            nn.Linear(self.branch_dim, self.branch_dim),
            nn.GELU(),
        )
        self.context_encoder = nn.Sequential(
            nn.Linear(2 * self.branch_dim, self.context_dim),
            nn.LayerNorm(self.context_dim),
            nn.GELU(),
            nn.Linear(self.context_dim, self.context_dim),
            nn.GELU(),
        )
        self.code_head = nn.Linear(self.context_dim, self.num_codes)
        self.previous_code_embedding = nn.Embedding(self.num_codes + 1, self.previous_code_embed_dim)
        self.previous_code_head = nn.Linear(self.previous_code_embed_dim, self.num_codes, bias=False)
        self.code_embedding = nn.Parameter(torch.empty(self.num_codes, self.code_embed_dim))
        nn.init.normal_(self.code_embedding, std=0.02)
        latent_dim = self.context_dim + self.code_embed_dim
        self.theta_head = nn.Sequential(
            nn.Linear(latent_dim + self.terrain_scalar_dim, self.branch_dim),
            nn.GELU(),
            nn.Linear(self.branch_dim, self.theta_dim),
        )
        time_dim = 1 + 2 * self.time_harmonics
        dynamics_input = self.feature_dim + latent_dim + self.theta_dim + time_dim
        if self.use_guide:
            dynamics_input += self.feature_dim
        self.dynamics_input = nn.Linear(dynamics_input, self.dynamics_dim)
        self.start_residual_input = (
            nn.Linear(self.feature_dim, self.dynamics_dim, bias=False)
            if self.start_residual_conditioning
            else None
        )
        if self.start_residual_input is not None:
            nn.init.zeros_(self.start_residual_input.weight)
        self.dynamics = nn.GRU(
            input_size=self.dynamics_dim,
            hidden_size=self.dynamics_dim,
            num_layers=self.dynamics_layers,
            batch_first=True,
        )
        self.initial_hidden = nn.Linear(latent_dim + self.theta_dim, self.dynamics_layers * self.dynamics_dim)
        self.delta_head = nn.Linear(self.dynamics_dim, self.feature_dim)
        nn.init.zeros_(self.delta_head.weight)
        nn.init.zeros_(self.delta_head.bias)
        self.register_buffer("target_mean", torch.zeros(self.feature_dim))
        self.register_buffer("target_std", torch.ones(self.feature_dim))
        self.register_buffer("length_prior", torch.full((self.num_codes,), self.max_frames, dtype=torch.long))

    def set_target_normalization(self, mean: torch.Tensor, std: torch.Tensor) -> None:
        self.target_mean.copy_(mean.reshape(-1).to(self.target_mean))
        self.target_std.copy_(std.reshape(-1).to(self.target_std))

    def set_length_prior(self, length_prior: torch.Tensor) -> None:
        if length_prior.shape != self.length_prior.shape:
            raise ValueError(f"length_prior must be {tuple(self.length_prior.shape)}, got {tuple(length_prior.shape)}")
        self.length_prior.copy_(length_prior.to(self.length_prior))

    def _time_features(self, lengths: torch.Tensor, steps: int, dtype: torch.dtype) -> torch.Tensor:
        index = torch.arange(steps, dtype=dtype, device=lengths.device)[None]
        denominator = (lengths.to(dtype=dtype)[:, None] - 1.0).clamp_min(1.0)
        u = (index / denominator).clamp(0.0, 1.0)
        features = [u]
        for harmonic in range(1, self.time_harmonics + 1):
            angle = torch.pi * float(harmonic) * u
            features.extend((torch.sin(angle), torch.cos(angle)))
        return torch.stack(features, dim=-1)

    def _normalized_quaternion(self, state: torch.Tensor) -> torch.Tensor:
        physical = state * self.target_std + self.target_mean
        quaternion = physical[..., 3:7]
        quaternion = quaternion / quaternion.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
        physical = torch.cat((physical[..., :3], quaternion, physical[..., 7:]), dim=-1)
        return (physical - self.target_mean) / self.target_std

    def _latent(
        self, observation: torch.Tensor, previous_code: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        height = self.height_encoder(observation[:, : self.height_dim])
        terrain_scalar = observation[:, self.height_dim : self.height_dim + self.terrain_scalar_dim]
        state = self.state_encoder(observation[:, self.height_dim + self.terrain_scalar_dim :])
        context = self.context_encoder(torch.cat((height, state), dim=-1))
        logits = self.code_head(context)
        history_logits = self.previous_code_logits(
            previous_code, batch_size=observation.shape[0], device=observation.device
        )
        logits = logits + self.previous_code_logit_scale * history_logits
        probabilities = logits.softmax(dim=-1)
        codes = logits.argmax(dim=-1)
        hard = F.one_hot(codes, num_classes=self.num_codes).to(probabilities)
        code_weights = hard + probabilities - probabilities.detach()
        code_context = code_weights @ self.code_embedding
        latent = torch.cat((context, code_context), dim=-1)
        theta = self.theta_head(torch.cat((latent, terrain_scalar), dim=-1))
        return logits, codes, theta, latent

    def previous_code_logits(
        self,
        previous_code: torch.Tensor | None,
        *,
        batch_size: int,
        device: torch.device,
        apply_dropout: bool = True,
    ) -> torch.Tensor:
        if previous_code is None:
            previous_index = torch.full(
                (batch_size,), self.num_codes, dtype=torch.long, device=device
            )
        else:
            previous_index = previous_code.to(device=device, dtype=torch.long)
            previous_index = torch.where(
                (previous_index >= 0) & (previous_index < self.num_codes),
                previous_index,
                self.num_codes,
            )
        if apply_dropout and self.training and self.previous_code_dropout > 0.0:
            dropped = torch.rand(previous_index.shape, device=device) < self.previous_code_dropout
            previous_index = torch.where(dropped, self.num_codes, previous_index)
        return self.previous_code_head(self.previous_code_embedding(previous_index))

    def forward(
        self,
        observation: torch.Tensor,
        *,
        start_state: torch.Tensor,
        lengths: torch.Tensor | None = None,
        teacher_trajectory: torch.Tensor | None = None,
        guide_trajectory: torch.Tensor | None = None,
        previous_code: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        expected = self.height_dim + self.terrain_scalar_dim + self.state_dim
        if observation.ndim != 2 or observation.shape[1] != expected:
            raise ValueError(f"observation must be [B,{expected}], got {tuple(observation.shape)}")
        if start_state.shape != (observation.shape[0], self.feature_dim):
            raise ValueError(
                f"start_state must be {(observation.shape[0], self.feature_dim)}, got {tuple(start_state.shape)}"
            )
        logits, codes, theta, latent = self._latent(observation, previous_code)
        if lengths is None:
            lengths = self.length_prior[codes]
        lengths = lengths.to(device=observation.device, dtype=torch.long)
        decoder_context = torch.cat((latent, theta), dim=-1)
        hidden = self.initial_hidden(decoder_context)
        hidden = hidden.reshape(observation.shape[0], self.dynamics_layers, self.dynamics_dim)
        hidden = hidden.transpose(0, 1).contiguous()
        time = self._time_features(lengths, self.max_frames - 1, observation.dtype)
        repeated = decoder_context[:, None].expand(-1, self.max_frames - 1, -1)
        if self.use_guide:
            if guide_trajectory is None or guide_trajectory.shape != (
                observation.shape[0],
                self.max_frames,
                self.feature_dim,
            ):
                raise ValueError(
                    "guide_trajectory must match "
                    f"{(observation.shape[0], self.max_frames, self.feature_dim)} when use_guide=True"
                )
            guide = guide_trajectory[:, 1:]
            guide_start_residual = start_state - guide_trajectory[:, 0]
            future_index = torch.arange(
                1,
                self.max_frames,
                dtype=observation.dtype,
                device=observation.device,
            )[None]
            duration = (lengths.to(observation.dtype)[:, None] - 1.0).clamp_min(1.0)
            guide_start_weight = (1.0 - (future_index / duration).clamp(0.0, 1.0)).square()[..., None]
        else:
            guide = None
            guide_start_residual = None
            guide_start_weight = None
        if self.joint_trajectory_output:
            current = start_state[:, None].expand(-1, self.max_frames - 1, -1)
            dynamics_input = self.dynamics_input(
                torch.cat((current, guide, repeated, time), dim=-1)
            )
            if self.start_residual_input is not None:
                dynamics_input = dynamics_input + self.start_residual_input(
                    guide_start_residual
                )[:, None]
            decoded, _ = self.dynamics(dynamics_input, hidden)
            following = self._normalized_quaternion(guide + self.delta_head(decoded))
            trajectory = torch.cat((start_state[:, None], following), dim=1)
        elif teacher_trajectory is not None:
            if teacher_trajectory.shape != (observation.shape[0], self.max_frames, self.feature_dim):
                raise ValueError(
                    "teacher_trajectory must be "
                    f"{(observation.shape[0], self.max_frames, self.feature_dim)}, got {tuple(teacher_trajectory.shape)}"
                )
            current = teacher_trajectory[:, :-1]
            parts = (current, repeated, time) if guide is None else (current, guide, repeated, time)
            dynamics_input = self.dynamics_input(torch.cat(parts, dim=-1))
            decoded, _ = self.dynamics(dynamics_input, hidden)
            residual = self.delta_head(decoded)
            following = self._normalized_quaternion(
                guide + guide_start_weight * guide_start_residual[:, None] + residual
                if self.guide_residual_output
                else current + residual
            )
            trajectory = torch.cat((start_state[:, None], following), dim=1)
        else:
            values = [start_state]
            current = start_state
            for step in range(self.max_frames - 1):
                parts = (
                    (current, decoder_context, time[:, step])
                    if guide is None
                    else (current, guide[:, step], decoder_context, time[:, step])
                )
                dynamics_input = self.dynamics_input(torch.cat(parts, dim=-1))[:, None]
                decoded, hidden = self.dynamics(dynamics_input, hidden)
                residual = self.delta_head(decoded[:, 0])
                current = self._normalized_quaternion(
                    guide[:, step]
                    + guide_start_weight[:, step] * guide_start_residual
                    + residual
                    if self.guide_residual_output
                    else current + residual
                )
                values.append(current)
            trajectory = torch.stack(values, dim=1)
        return {
            "code_logits": logits,
            "codes": codes,
            "theta": theta,
            "trajectory": trajectory,
            "lengths": lengths,
        }

    def config(self) -> dict[str, int]:
        return {
            "height_dim": self.height_dim,
            "state_dim": self.state_dim,
            "feature_dim": self.feature_dim,
            "num_codes": self.num_codes,
            "theta_dim": self.theta_dim,
            "max_frames": self.max_frames,
            "branch_dim": self.branch_dim,
            "context_dim": self.context_dim,
            "code_embed_dim": self.code_embed_dim,
            "dynamics_dim": self.dynamics_dim,
            "dynamics_layers": self.dynamics_layers,
            "time_harmonics": self.time_harmonics,
            "use_guide": self.use_guide,
            "guide_residual_output": self.guide_residual_output,
            "joint_trajectory_output": self.joint_trajectory_output,
            "start_residual_conditioning": self.start_residual_conditioning,
            "scan_grid_shapes": self.scan_grid_shapes,
            "previous_code_embed_dim": self.previous_code_embed_dim,
            "previous_code_logit_scale": self.previous_code_logit_scale,
            "previous_code_dropout": self.previous_code_dropout,
            "terrain_scalar_dim": self.terrain_scalar_dim,
            "scan_antialias": self.scan_antialias,
        }

def load_current_frame_future_model(
    checkpoint: str | Path | Mapping[str, Any],
    *,
    device: str | torch.device,
) -> tuple[CurrentFrameFutureModel, dict[str, Any]]:
    if isinstance(checkpoint, Mapping):
        payload = dict(checkpoint)
        context = "embedded current-frame future model"
    else:
        path = Path(checkpoint).expanduser()
        payload = torch.load(path, map_location="cpu", weights_only=False)
        context = f"current-frame future model {path}"
    if payload.get("schema") != "gmvq_current_frame_future_v1":
        raise ValueError(f"unsupported current-frame future checkpoint: {payload.get('schema')!r}")
    validate_g1_asset_metadata(payload.get("robot_asset"), context=context)
    config = dict(payload["model_config"])
    legacy_previous_code = "previous_code_embed_dim" not in config
    if legacy_previous_code:
        config["previous_code_logit_scale"] = 0.0
    model = CurrentFrameFutureModel(**config)
    incompatible = model.load_state_dict(payload["model_state"], strict=not legacy_previous_code)
    if legacy_previous_code and set(incompatible.missing_keys) != {
        "previous_code_embedding.weight",
        "previous_code_head.weight",
    }:
        raise RuntimeError(f"unexpected missing legacy model weights: {incompatible.missing_keys}")
    model.to(device)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model, payload


def load_causal_segment_future_model(
    checkpoint: str | Path | Mapping[str, Any],
    *,
    device: str | torch.device,
) -> tuple[CausalSegmentFutureModel, dict[str, Any]]:
    if isinstance(checkpoint, Mapping):
        payload = dict(checkpoint)
        context = "embedded causal segment future model"
    else:
        path = Path(checkpoint).expanduser()
        payload = torch.load(path, map_location="cpu", weights_only=False)
        context = f"causal segment future model {path}"
    if payload.get("schema") != "gmvq_causal_segment_future_v1":
        raise ValueError(f"unsupported causal segment future checkpoint: {payload.get('schema')!r}")
    validate_g1_asset_metadata(payload.get("robot_asset"), context=context)
    config = dict(payload["model_config"])
    legacy_previous_code = "previous_code_embed_dim" not in config
    if legacy_previous_code:
        config["previous_code_logit_scale"] = 0.0
    model = CausalSegmentFutureModel(**config)
    incompatible = model.load_state_dict(payload["model_state"], strict=not legacy_previous_code)
    if legacy_previous_code and set(incompatible.missing_keys) != {
        "previous_code_embedding.weight",
        "previous_code_head.weight",
    }:
        raise RuntimeError(f"unexpected missing legacy model weights: {incompatible.missing_keys}")
    model.to(device)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model, payload


__all__ = [
    "CausalSegmentFutureModel",
    "CurrentFrameFutureModel",
    "canonical_boundary_state",
    "load_causal_segment_future_model",
    "load_current_frame_future_model",
]
