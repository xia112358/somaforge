"""Online GMVQ reference runtime for direct WBT policy execution."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from somaforge_core.asset_registry import sha256_file
from somaforge_core.robot_assets import validate_g1_asset_metadata
from torch import nn

from .hyar_wrapper import FrozenGMVQCodec
from .current_frame_future import (
    CausalSegmentFutureModel,
    canonical_boundary_state,
    load_causal_segment_future_model,
)
from .start_conditioned import load_start_conditioned_decoder

POLICY_REFERENCE_BUNDLE_SCHEMA = "gmvq_policy_reference_bundle_v1"
FEATURE_KEYS = (
    "height_scan",
    "root_pos_w",
    "root_quat_w",
    "root_lin_vel_w",
    "root_ang_vel_w",
    "joint_pos",
    "joint_vel",
)


class SelectorMLP(nn.Module):
    def __init__(self, input_dim: int, num_codes: int, hidden_dim: int, depth: int, dropout: float) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        dim = int(input_dim)
        for _ in range(int(depth)):
            layers.extend((nn.Linear(dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU()))
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            dim = int(hidden_dim)
        layers.append(nn.Linear(dim, int(num_codes)))
        self.net = nn.Sequential(*layers)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.net(value)


class ThetaMLP(nn.Module):
    def __init__(self, input_dim: int, theta_dim: int, hidden_dim: int, depth: int, dropout: float) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        dim = int(input_dim)
        for _ in range(int(depth)):
            layers.extend((nn.Linear(dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU()))
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            dim = int(hidden_dim)
        layers.append(nn.Linear(dim, int(theta_dim)))
        self.net = nn.Sequential(*layers)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.net(value)


class SharedNextAtomSelector(nn.Module):
    """Shared terrain/proprio encoder with internal code and theta heads.

    Code and theta remain explicit latent variables for diagnostics and GMVQ
    decoding, but callers receive one next-atom result from a single forward.
    The previous code is an observation feature, not a hard transition rule.
    ``transition_mask`` remains in the call contract for bundle compatibility
    but does not constrain the learned code logits.
    """

    def __init__(
        self,
        *,
        height_dim: int,
        state_dim: int,
        num_codes: int,
        theta_dim: int,
        branch_dim: int = 128,
        context_dim: int = 256,
        code_embed_dim: int = 32,
    ) -> None:
        super().__init__()
        self.height_dim = int(height_dim)
        self.state_dim = int(state_dim)
        self.num_codes = int(num_codes)
        self.theta_dim = int(theta_dim)
        self.branch_dim = int(branch_dim)
        self.context_dim = int(context_dim)
        self.code_embed_dim = int(code_embed_dim)
        self.height_encoder = nn.Sequential(
            nn.Linear(self.height_dim, self.branch_dim),
            nn.LayerNorm(self.branch_dim),
            nn.GELU(),
            nn.Linear(self.branch_dim, self.branch_dim),
            nn.GELU(),
        )
        self.state_encoder = nn.Sequential(
            nn.Linear(self.state_dim, self.branch_dim),
            nn.LayerNorm(self.branch_dim),
            nn.GELU(),
            nn.Linear(self.branch_dim, self.branch_dim),
            nn.GELU(),
        )
        # The final embedding row represents the initial previous_code=-1.
        self.code_embedding = nn.Embedding(self.num_codes + 1, self.code_embed_dim)
        self.context = nn.Sequential(
            nn.Linear(2 * self.branch_dim + self.code_embed_dim, self.context_dim),
            nn.LayerNorm(self.context_dim),
            nn.GELU(),
            nn.Linear(self.context_dim, self.context_dim),
            nn.GELU(),
        )
        self.code_head = nn.Linear(self.context_dim, self.num_codes)
        self.theta_head = nn.Sequential(
            nn.Linear(self.context_dim + self.code_embed_dim, self.branch_dim),
            nn.GELU(),
            nn.Linear(self.branch_dim, self.theta_dim),
        )

    def forward(
        self,
        observation: torch.Tensor,
        previous_code: torch.Tensor,
        transition_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        del transition_mask
        expected = self.height_dim + self.state_dim
        if observation.ndim != 2 or observation.shape[1] != expected:
            raise ValueError(f"observation must be [B,{expected}], got {tuple(observation.shape)}")
        previous_code = previous_code.to(device=observation.device, dtype=torch.long)
        previous_index = torch.where(previous_code >= 0, previous_code, self.num_codes)
        height = self.height_encoder(observation[:, : self.height_dim])
        state = self.state_encoder(observation[:, self.height_dim :])
        context = self.context(torch.cat((height, state, self.code_embedding(previous_index)), dim=-1))
        logits = self.code_head(context)
        codes = logits.argmax(dim=1)
        theta = self.theta_head(torch.cat((context, self.code_embedding(codes)), dim=-1))
        return logits, codes, theta

    def config(self) -> dict[str, int]:
        return {
            "height_dim": self.height_dim,
            "state_dim": self.state_dim,
            "num_codes": self.num_codes,
            "theta_dim": self.theta_dim,
            "branch_dim": self.branch_dim,
            "context_dim": self.context_dim,
            "code_embed_dim": self.code_embed_dim,
        }


def _load_checkpoint(path: str | Path) -> dict[str, Any]:
    return torch.load(Path(path).expanduser(), map_location="cpu", weights_only=False)


def build_policy_reference_bundle(
    *,
    gmvq_checkpoint: str | Path,
    code_selector: str | Path,
    theta_selector: str | Path,
    start_decoder: str | Path,
    selector_dataset: str | Path,
    current_frame_future: str | Path | None = None,
) -> dict[str, Any]:
    """Build one self-contained runtime bundle from the accepted checkpoints."""
    paths = {
        "gmvq_checkpoint": Path(gmvq_checkpoint).expanduser(),
        "code_selector": Path(code_selector).expanduser(),
        "theta_selector": Path(theta_selector).expanduser(),
        "start_decoder": Path(start_decoder).expanduser(),
        "selector_dataset": Path(selector_dataset).expanduser(),
    }
    payloads = {key: _load_checkpoint(path) for key, path in paths.items() if key != "selector_dataset"}
    future_path = None if current_frame_future is None else Path(current_frame_future).expanduser()
    if future_path is not None:
        payloads["current_frame_future"] = _load_checkpoint(future_path)
    assets = []
    for key, payload in payloads.items():
        validate_g1_asset_metadata(payload.get("robot_asset"), context=key)
        assets.append(dict(payload["robot_asset"]))
    fingerprints = {str(asset["asset_bundle_sha256"]) for asset in assets}
    if len(fingerprints) != 1:
        raise ValueError("GMVQ runtime checkpoints do not share one canonical robot asset")

    gmvq_codes = int(payloads["gmvq_checkpoint"]["model_config"]["num_codes"])
    code_count = int(payloads["code_selector"]["model_config"]["num_codes"])
    if code_count != gmvq_codes + 1:
        raise ValueError(f"code selector must contain {gmvq_codes} motion codes plus STOP, got {code_count}")
    if int(payloads["start_decoder"]["model_config"]["num_codes"]) != gmvq_codes:
        raise ValueError("start-conditioned decoder code count disagrees with GMVQ")

    with np.load(paths["selector_dataset"], allow_pickle=False) as data:
        required = {"local_grid", "codes", "lengths", "motion_ids", "start_frames"}
        missing = required - set(data.files)
        if missing:
            raise ValueError(f"selector dataset is missing runtime fields: {sorted(missing)}")
        local_grid = np.asarray(data["local_grid"], dtype=np.float32)
        codes = np.asarray(data["codes"], dtype=np.int64)
        lengths = np.asarray(data["lengths"], dtype=np.int64)
        motion_ids = np.asarray(data["motion_ids"]).astype(str)
        start_frames = np.asarray(data["start_frames"], dtype=np.int64)
    if local_grid.ndim != 2 or local_grid.shape[1] != 3:
        raise ValueError(f"local_grid must be [P,3], got {local_grid.shape}")

    length_prior = np.zeros(gmvq_codes, dtype=np.int64)
    for code in range(gmvq_codes):
        selected = lengths[codes == code]
        if selected.size == 0:
            raise ValueError(f"selector dataset has no duration prior for code {code}")
        length_prior[code] = int(np.rint(np.median(selected)))

    transition_mask = np.zeros((code_count, code_count), dtype=np.bool_)
    for motion_id in sorted(set(motion_ids)):
        rows = np.flatnonzero((motion_ids == motion_id) & (codes < gmvq_codes))
        rows = rows[np.argsort(start_frames[rows])]
        sequence = codes[rows].astype(int).tolist()
        if sequence:
            sequence.append(gmvq_codes)
        for source, target in pairwise(sequence):
            transition_mask[source, target] = True

    bundle = {
        "schema": POLICY_REFERENCE_BUNDLE_SCHEMA,
        "robot_asset": assets[0],
        "feature_keys": list(FEATURE_KEYS),
        "gmvq_checkpoint": payloads["gmvq_checkpoint"],
        "code_selector": payloads["code_selector"],
        "theta_selector": payloads["theta_selector"],
        "start_decoder": payloads["start_decoder"],
        "local_grid": torch.from_numpy(local_grid),
        "length_prior": torch.from_numpy(length_prior),
        "transition_mask": torch.from_numpy(transition_mask),
        "stop_code": gmvq_codes,
        "source_sha256": {key: sha256_file(path) for key, path in paths.items()},
        "source_paths": {key: str(path) for key, path in paths.items()},
    }
    if future_path is not None:
        future = payloads["current_frame_future"]
        if future.get("schema") != "gmvq_causal_segment_future_v1":
            raise ValueError("current-frame future must use the causal segment checkpoint schema")
        if int(future["stop_code"]) != gmvq_codes:
            raise ValueError("current-frame future STOP code disagrees with GMVQ")
        if int(future["model_config"]["height_dim"]) != int(local_grid.shape[0]):
            raise ValueError("current-frame future scan dimension disagrees with selector dataset")
        bundle["current_frame_future"] = future
        bundle["source_sha256"]["current_frame_future"] = sha256_file(future_path)
        bundle["source_paths"]["current_frame_future"] = str(future_path)
    return bundle


def save_policy_reference_bundle(bundle: Mapping[str, Any], output: str | Path) -> Path:
    output_path = Path(output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(dict(bundle), output_path)
    return output_path


def _quat_mul_wxyz(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    aw, ax, ay, az = a.unbind(dim=-1)
    bw, bx, by, bz = b.unbind(dim=-1)
    return torch.stack(
        (
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ),
        dim=-1,
    )


def _quat_conjugate_wxyz(value: torch.Tensor) -> torch.Tensor:
    return torch.cat((value[..., :1], -value[..., 1:]), dim=-1)


def _finite_difference(value: torch.Tensor, fps: float) -> torch.Tensor:
    velocity = torch.empty_like(value)
    velocity[:, 0] = (value[:, 1] - value[:, 0]) * fps
    velocity[:, -1] = (value[:, -1] - value[:, -2]) * fps
    if value.shape[1] > 2:
        velocity[:, 1:-1] = (value[:, 2:] - value[:, :-2]) * (0.5 * fps)
    return velocity


def _angular_velocity_wxyz(quaternion: torch.Tensor, fps: float) -> torch.Tensor:
    q = quaternion / quaternion.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
    relative = _quat_mul_wxyz(q[:, 1:], _quat_conjugate_wxyz(q[:, :-1]))
    relative = torch.where(relative[..., :1] < 0.0, -relative, relative)
    vector = relative[..., 1:]
    norm = vector.norm(dim=-1, keepdim=True)
    angle = 2.0 * torch.atan2(norm, relative[..., :1].clamp_min(1.0e-8))
    interval = vector / norm.clamp_min(1.0e-8) * angle * fps
    velocity = torch.empty_like(q[..., 1:])
    velocity[:, 0] = interval[:, 0]
    velocity[:, -1] = interval[:, -1]
    if q.shape[1] > 2:
        velocity[:, 1:-1] = 0.5 * (interval[:, :-1] + interval[:, 1:])
    return velocity


def query_local_height_scan(
    *,
    local_grid: torch.Tensor,
    root_pos_w: torch.Tensor,
    root_quat_wxyz: torch.Tensor,
    query_terrain_heights: Any,
) -> torch.Tensor:
    """Sample the training-time local grid around each current robot root."""
    if local_grid.ndim != 2 or local_grid.shape[1] != 3:
        raise ValueError(f"local_grid must be [P,3], got {tuple(local_grid.shape)}")
    if root_pos_w.ndim != 2 or root_pos_w.shape[1] != 3:
        raise ValueError(f"root_pos_w must be [B,3], got {tuple(root_pos_w.shape)}")
    if root_quat_wxyz.shape != (root_pos_w.shape[0], 4):
        raise ValueError(f"root_quat_wxyz must be [B,4], got {tuple(root_quat_wxyz.shape)}")
    quaternion = root_quat_wxyz / root_quat_wxyz.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
    w, x, y, z = quaternion.unbind(dim=-1)
    yaw = torch.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y.square() + z.square()))
    cosine = torch.cos(yaw)[:, None]
    sine = torch.sin(yaw)[:, None]
    grid = local_grid.to(device=root_pos_w.device, dtype=root_pos_w.dtype)
    point_x = cosine * grid[None, :, 0] - sine * grid[None, :, 1]
    point_y = sine * grid[None, :, 0] + cosine * grid[None, :, 1]
    xy = torch.stack((point_x, point_y), dim=-1) + root_pos_w[:, None, :2]
    heights = query_terrain_heights(xy.reshape(-1, 2)).reshape(root_pos_w.shape[0], -1)
    return heights.to(root_pos_w) - root_pos_w[:, 2:3]


class GMVQPolicyReferenceRuntime(nn.Module):
    """Batched observation-to-absolute-reference inference from one bundle."""

    def __init__(self, bundle: str | Path | Mapping[str, Any], *, device: str | torch.device) -> None:
        super().__init__()
        if isinstance(bundle, Mapping):
            payload = dict(bundle)
        else:
            payload = torch.load(Path(bundle).expanduser(), map_location="cpu", weights_only=False)
        if payload.get("schema") != POLICY_REFERENCE_BUNDLE_SCHEMA:
            raise ValueError(f"unsupported GMVQ policy reference bundle: {payload.get('schema')!r}")
        validate_g1_asset_metadata(payload.get("robot_asset"), context="GMVQ policy reference bundle")
        self.device_ref = torch.device(device)

        future_payload = payload.get("current_frame_future")
        self.current_frame_future: CausalSegmentFutureModel | None = None
        self.future_uses_terrain_top_height = False
        self.future_uses_canonical_boundary_state = False
        if isinstance(future_payload, Mapping):
            self.current_frame_future, loaded_future = load_causal_segment_future_model(
                future_payload,
                device=self.device_ref,
            )
            self.register_buffer(
                "future_observation_mean",
                torch.as_tensor(loaded_future["observation_norm"]["mean"], dtype=torch.float32),
            )
            self.register_buffer(
                "future_observation_std",
                torch.as_tensor(loaded_future["observation_norm"]["std"], dtype=torch.float32),
            )
            self.register_buffer(
                "future_target_mean",
                torch.as_tensor(loaded_future["target_norm"]["mean"], dtype=torch.float32),
            )
            self.register_buffer(
                "future_target_std",
                torch.as_tensor(loaded_future["target_norm"]["std"], dtype=torch.float32),
            )
            self.register_buffer(
                "future_theta_mean",
                torch.as_tensor(loaded_future["theta_norm"]["mean"], dtype=torch.float32),
            )
            self.register_buffer(
                "future_theta_std",
                torch.as_tensor(loaded_future["theta_norm"]["std"], dtype=torch.float32),
            )
            self.future_uses_terrain_top_height = "terrain_top_height_w" in loaded_future.get(
                "feature_keys", ()
            )
            self.future_uses_canonical_boundary_state = "canonical_boundary_state" in loaded_future.get(
                "feature_keys", ()
            )

        shared_payload = payload.get("next_atom_model")
        self.next_atom_model: SharedNextAtomSelector | None = None
        if isinstance(shared_payload, Mapping):
            self.next_atom_model = SharedNextAtomSelector(**shared_payload["model_config"])
            self.next_atom_model.load_state_dict(shared_payload["model_state"])
        code_payload = payload.get("code_selector")
        theta_payload = payload.get("theta_selector")
        self.code_model: SelectorMLP | None = None
        self.theta_model: ThetaMLP | None = None
        if isinstance(code_payload, Mapping) and isinstance(theta_payload, Mapping):
            self.code_model = SelectorMLP(**code_payload["model_config"])
            self.code_model.load_state_dict(code_payload["model_state"])
            theta_config = theta_payload["model_config"]
            self.theta_model = ThetaMLP(
                input_dim=theta_config["input_dim"],
                theta_dim=theta_config["theta_dim"],
                hidden_dim=theta_config["hidden_dim"],
                depth=theta_config["depth"],
                dropout=theta_config["dropout"],
            )
            self.theta_model.load_state_dict(theta_payload["model_state"])
        elif self.next_atom_model is None:
            raise ValueError("legacy GMVQ bundle requires code_selector and theta_selector")
        self.codec = FrozenGMVQCodec(payload["gmvq_checkpoint"], device=self.device_ref, trainable=False)
        self.start_decoder = load_start_conditioned_decoder(payload["start_decoder"], device=self.device_ref)
        self.stop_code = int(payload["stop_code"])
        if isinstance(code_payload, Mapping) and isinstance(theta_payload, Mapping):
            self.register_buffer("code_mean", torch.as_tensor(code_payload["norm"]["mean"], dtype=torch.float32))
            self.register_buffer("code_std", torch.as_tensor(code_payload["norm"]["std"], dtype=torch.float32))
            self.register_buffer("theta_x_mean", torch.as_tensor(theta_payload["x_norm"]["mean"], dtype=torch.float32))
            self.register_buffer("theta_x_std", torch.as_tensor(theta_payload["x_norm"]["std"], dtype=torch.float32))
            self.register_buffer("theta_mean", torch.as_tensor(theta_payload["theta_norm"]["mean"], dtype=torch.float32))
            self.register_buffer("theta_std", torch.as_tensor(theta_payload["theta_norm"]["std"], dtype=torch.float32))
        if isinstance(shared_payload, Mapping):
            self.register_buffer(
                "next_atom_obs_mean", torch.as_tensor(shared_payload["observation_norm"]["mean"], dtype=torch.float32)
            )
            self.register_buffer(
                "next_atom_obs_std", torch.as_tensor(shared_payload["observation_norm"]["std"], dtype=torch.float32)
            )
            self.register_buffer(
                "next_atom_theta_mean", torch.as_tensor(shared_payload["theta_norm"]["mean"], dtype=torch.float32)
            )
            self.register_buffer(
                "next_atom_theta_std", torch.as_tensor(shared_payload["theta_norm"]["std"], dtype=torch.float32)
            )
        self.register_buffer("local_grid", torch.as_tensor(payload["local_grid"], dtype=torch.float32))
        self.register_buffer("length_prior", torch.as_tensor(payload["length_prior"], dtype=torch.long))
        self.register_buffer("transition_mask", torch.as_tensor(payload["transition_mask"], dtype=torch.bool))
        self.bundle_metadata = {
            "schema": payload["schema"],
            "robot_asset": payload["robot_asset"],
            "source_sha256": dict(payload.get("source_sha256", {})),
        }
        self.to(self.device_ref)
        self.eval()
        for parameter in self.parameters():
            parameter.requires_grad_(False)

    @property
    def max_frames(self) -> int:
        return int(self.codec.t)

    def build_observation(
        self, height_scan: torch.Tensor, joint_pos: torch.Tensor, joint_vel: torch.Tensor
    ) -> torch.Tensor:
        if height_scan.ndim != 2 or height_scan.shape[1] != self.local_grid.shape[0]:
            raise ValueError(f"height_scan must be [B,{self.local_grid.shape[0]}], got {tuple(height_scan.shape)}")
        if joint_pos.shape != (height_scan.shape[0], 36):
            raise ValueError(f"joint_pos must be [B,36], got {tuple(joint_pos.shape)}")
        if joint_vel.shape != (height_scan.shape[0], 35):
            raise ValueError(f"joint_vel must be [B,35], got {tuple(joint_vel.shape)}")
        terrain_features = (
            (height_scan.max(dim=1, keepdim=True).values + joint_pos[:, 2:3],)
            if getattr(self, "future_uses_terrain_top_height", False)
            else ()
        )
        if getattr(self, "future_uses_canonical_boundary_state", False):
            return torch.cat((height_scan, canonical_boundary_state(joint_pos, joint_vel)), dim=-1)
        return torch.cat(
            (
                height_scan,
                *terrain_features,
                joint_pos[:, :3],
                joint_pos[:, 3:7],
                joint_vel[:, :3],
                joint_vel[:, 3:6],
                joint_pos,
                joint_vel,
            ),
            dim=-1,
        )

    @torch.no_grad()
    def decode_next(
        self,
        *,
        height_scan: torch.Tensor,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
        previous_code: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        height_scan = height_scan.to(self.device_ref, dtype=torch.float32)
        joint_pos = joint_pos.to(self.device_ref, dtype=torch.float32)
        joint_vel = joint_vel.to(self.device_ref, dtype=torch.float32)
        previous_code = previous_code.to(self.device_ref, dtype=torch.long)
        observation = self.build_observation(height_scan, joint_pos, joint_vel)
        if getattr(self, "current_frame_future", None) is not None:
            normalized_observation = (
                observation - self.future_observation_mean
            ) / self.future_observation_std
            local_q = joint_pos.clone()
            local_q[:, :3] = 0.0
            start_raw = torch.cat((local_q, joint_vel), dim=-1)
            start_state = (start_raw - self.future_target_mean) / self.future_target_std
            logits, codes, theta_normalized, _ = self.current_frame_future._latent(
                normalized_observation, previous_code
            )
            del logits
            lengths = self.current_frame_future.length_prior[codes]
            guide = start_state[:, None].expand(-1, self.max_frames, -1).clone()
            active = torch.where(codes < self.stop_code)[0]
            theta = theta_normalized * self.future_theta_std + self.future_theta_mean
            if active.numel() > 0:
                guide[active] = self.codec.decode_hybrid(
                    codes[active],
                    theta[active],
                    lengths=lengths[active],
                )["x_hat"]
            output = self.current_frame_future(
                normalized_observation,
                start_state=start_state,
                lengths=lengths,
                guide_trajectory=guide,
                previous_code=previous_code,
            )
            physical = output["trajectory"] * self.future_target_std + self.future_target_mean
            q = physical[..., :36].clone()
            qd = physical[..., 36:].clone()
            decoded_quat = q[..., 3:7]
            decoded_quat = decoded_quat / decoded_quat.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
            start_quat = joint_pos[:, 3:7]
            start_quat = start_quat / start_quat.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
            alignment = _quat_mul_wxyz(start_quat, _quat_conjugate_wxyz(decoded_quat[:, 0]))
            q[..., :3] = joint_pos[:, None, :3] + (q[..., :3] - q[:, :1, :3])
            q[..., 3:7] = _quat_mul_wxyz(alignment[:, None], decoded_quat)
            stopped = codes == self.stop_code
            if torch.any(stopped):
                q[stopped] = joint_pos[stopped, None]
                qd[stopped] = joint_vel[stopped, None]
                lengths = torch.where(stopped, torch.ones_like(lengths), lengths)
                theta = torch.where(stopped[:, None], torch.zeros_like(theta), theta)
            return {
                "joint_pos": q,
                "joint_vel": qd,
                "codes": codes,
                "theta": theta,
                "lengths": lengths,
                "stopped": stopped,
            }
        shared_theta_norm: torch.Tensor | None = None
        if self.next_atom_model is None:
            assert self.code_model is not None
            logits = self.code_model((observation - self.code_mean) / self.code_std)
            codes = logits.argmax(dim=1)
        else:
            logits, codes, shared_theta_norm = self.next_atom_model(
                (observation - self.next_atom_obs_mean) / self.next_atom_obs_std,
                previous_code,
                self.transition_mask,
            )
        stopped = codes == self.stop_code

        batch = joint_pos.shape[0]
        q = joint_pos[:, None, :].expand(-1, self.max_frames, -1).clone()
        qd = joint_vel[:, None, :].expand(-1, self.max_frames, -1).clone()
        theta = torch.zeros(batch, self.codec.theta_dim, device=self.device_ref)
        lengths = torch.ones(batch, dtype=torch.long, device=self.device_ref)
        active = torch.where(~stopped)[0]
        if active.numel() > 0:
            active_codes = codes[active]
            if shared_theta_norm is None:
                assert self.theta_model is not None
                one_hot = F.one_hot(active_codes, num_classes=self.stop_code + 1).to(observation.dtype)
                theta_input = torch.cat((observation[active], one_hot), dim=-1)
                theta_norm = self.theta_model((theta_input - self.theta_x_mean) / self.theta_x_std)
                active_theta = theta_norm * self.theta_std + self.theta_mean
            else:
                active_theta = (
                    shared_theta_norm[active] * self.next_atom_theta_std + self.next_atom_theta_mean
                )
            active_lengths = self.length_prior[active_codes]
            decoded = self.codec.decode_hybrid(active_codes, active_theta, lengths=active_lengths)["x_hat"]
            start_q = joint_pos[active].clone()
            start_q[:, :3] = 0.0
            start_state = torch.cat((start_q, joint_vel[active]), dim=-1)
            if self.codec.norm_stats is not None:
                mean = self.codec.norm_stats.mean.to(self.device_ref).reshape(-1)
                std = self.codec.norm_stats.std.to(self.device_ref).reshape(-1)
                start_state = (start_state - mean) / std
            decoded = self.start_decoder(
                decoded,
                start_state=start_state,
                codes=active_codes,
                theta=active_theta,
                lengths=active_lengths,
            )
            decoded = self.codec.denormalize(decoded)
            active_q = decoded[..., :36].clone()
            active_qd = decoded[..., 36:].clone()
            decoded_quat = active_q[..., 3:7]
            decoded_quat = decoded_quat / decoded_quat.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
            start_quat = joint_pos[active, 3:7]
            start_quat = start_quat / start_quat.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
            alignment = _quat_mul_wxyz(start_quat, _quat_conjugate_wxyz(decoded_quat[:, 0]))
            active_q[..., :3] = joint_pos[active, None, :3] + (active_q[..., :3] - active_q[:, :1, :3])
            active_q[..., 3:7] = _quat_mul_wxyz(alignment[:, None, :], decoded_quat)
            q[active] = active_q
            qd[active] = active_qd
            theta[active] = active_theta
            lengths[active] = active_lengths
        return {
            "joint_pos": q,
            "joint_vel": qd,
            "codes": codes,
            "theta": theta,
            "lengths": lengths,
            "stopped": stopped,
        }


class GMVQOnlineReference:
    """Per-environment atom buffers; neural decoding runs only at boundaries."""

    def __init__(
        self,
        runtime: GMVQPolicyReferenceRuntime,
        *,
        num_envs: int,
        fps: float = 50.0,
    ) -> None:
        self.runtime = runtime
        self.device = runtime.device_ref
        self.num_envs = int(num_envs)
        self.fps = float(fps)
        self.joint_pos_buffer = torch.zeros(self.num_envs, runtime.max_frames, 36, device=self.device)
        self.joint_vel_buffer = torch.zeros(self.num_envs, runtime.max_frames, 35, device=self.device)
        self.lengths = torch.ones(self.num_envs, dtype=torch.long, device=self.device)
        self.cursors = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)
        self.codes = torch.full((self.num_envs,), -1, dtype=torch.long, device=self.device)
        self.theta = torch.zeros(self.num_envs, runtime.codec.theta_dim, device=self.device)
        self.stopped = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.atom_counts = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)

    @torch.no_grad()
    def refresh(
        self,
        env_ids: torch.Tensor,
        *,
        height_scan: torch.Tensor,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
    ) -> None:
        env_ids = env_ids.to(self.device, dtype=torch.long)
        if env_ids.numel() == 0:
            return
        result = self.runtime.decode_next(
            height_scan=height_scan[env_ids],
            joint_pos=joint_pos[env_ids],
            joint_vel=joint_vel[env_ids],
            previous_code=self.codes[env_ids],
        )
        self.joint_pos_buffer[env_ids] = result["joint_pos"]
        self.joint_vel_buffer[env_ids] = result["joint_vel"]
        self.lengths[env_ids] = result["lengths"]
        self.cursors[env_ids] = 0
        self.codes[env_ids] = result["codes"]
        self.theta[env_ids] = result["theta"]
        self.stopped[env_ids] = result["stopped"]
        self.atom_counts[env_ids] += (~result["stopped"]).long()

    @torch.no_grad()
    def reset(
        self,
        env_ids: torch.Tensor,
        *,
        height_scan: torch.Tensor,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
    ) -> None:
        env_ids = env_ids.to(self.device, dtype=torch.long)
        self.codes[env_ids] = -1
        self.stopped[env_ids] = False
        self.atom_counts[env_ids] = 0
        self.refresh(env_ids, height_scan=height_scan, joint_pos=joint_pos, joint_vel=joint_vel)

    @torch.no_grad()
    def advance(
        self,
        *,
        height_scan: torch.Tensor,
        joint_pos: torch.Tensor,
        joint_vel: torch.Tensor,
        advance_ready: torch.Tensor | None = None,
        boundary_ready: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if advance_ready is None:
            advance_ready = torch.ones(self.num_envs, dtype=torch.bool, device=self.device)
        else:
            advance_ready = advance_ready.to(self.device, dtype=torch.bool)
        if boundary_ready is None:
            boundary_ready = torch.ones(self.num_envs, dtype=torch.bool, device=self.device)
        else:
            boundary_ready = boundary_ready.to(self.device, dtype=torch.bool)
        at_tail = self.cursors >= (self.lengths - 1)
        refresh_ids = torch.where(at_tail & advance_ready & boundary_ready & ~self.stopped)[0]
        advance = ~at_tail & advance_ready & ~self.stopped
        self.cursors[advance] += 1
        self.refresh(refresh_ids, height_scan=height_scan, joint_pos=joint_pos, joint_vel=joint_vel)
        return refresh_ids

    def current(self) -> tuple[torch.Tensor, torch.Tensor]:
        env_ids = torch.arange(self.num_envs, device=self.device)
        return (
            self.joint_pos_buffer[env_ids, self.cursors],
            self.joint_vel_buffer[env_ids, self.cursors],
        )

    def future(self, offsets: tuple[int, ...]) -> tuple[torch.Tensor, torch.Tensor]:
        offset = torch.as_tensor(offsets, dtype=torch.long, device=self.device)
        steps = self.cursors[:, None] + offset[None, :]
        steps = torch.minimum(steps, (self.lengths - 1)[:, None])
        env_ids = torch.arange(self.num_envs, device=self.device)[:, None]
        return self.joint_pos_buffer[env_ids, steps], self.joint_vel_buffer[env_ids, steps]


__all__ = [
    "FEATURE_KEYS",
    "POLICY_REFERENCE_BUNDLE_SCHEMA",
    "GMVQOnlineReference",
    "GMVQPolicyReferenceRuntime",
    "SelectorMLP",
    "SharedNextAtomSelector",
    "ThetaMLP",
    "build_policy_reference_bundle",
    "query_local_height_scan",
    "save_policy_reference_bundle",
]
