from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
from torch.utils.data import Dataset


@dataclass
class NormStats:
    mean: torch.Tensor
    std: torch.Tensor


class SegmentDataset(Dataset[torch.Tensor]):
    """Dataset of anchor-to-anchor segments with shape [N, T, D]."""

    def __init__(self, segments: torch.Tensor) -> None:
        if segments.ndim != 3:
            raise ValueError(f"segments must have shape [N, T, D], got {tuple(segments.shape)}")
        self.segments = segments.float()

    def __len__(self) -> int:
        return self.segments.shape[0]

    def __getitem__(self, idx: int) -> torch.Tensor:
        return self.segments[idx]


class MaskedSegmentDataset(Dataset[dict[str, Any]]):
    """Padded variable-length segment dataset with original lengths."""

    def __init__(
        self,
        segments: torch.Tensor,
        valid_mask: torch.Tensor,
        lengths: torch.Tensor,
        metadata: Optional[dict[str, np.ndarray]] = None,
    ) -> None:
        if segments.ndim != 3:
            raise ValueError(f"segments must have shape [N, T, D], got {tuple(segments.shape)}")
        if valid_mask.shape != segments.shape[:2]:
            raise ValueError(
                f"valid_mask must have shape [N, T]={tuple(segments.shape[:2])}, got {tuple(valid_mask.shape)}"
            )
        if lengths.shape != (segments.shape[0],):
            raise ValueError(f"lengths must have shape [N], got {tuple(lengths.shape)}")
        self.segments = segments.float()
        self.valid_mask = valid_mask.bool()
        self.lengths = lengths.long()
        self.metadata = metadata or {}

    def __len__(self) -> int:
        return self.segments.shape[0]

    def __getitem__(self, idx: int) -> dict[str, Any]:
        item: dict[str, Any] = {
            "x": self.segments[idx],
            "valid_mask": self.valid_mask[idx],
            "lengths": self.lengths[idx],
        }
        for key, values in self.metadata.items():
            item[key] = values[idx]
        return item


def make_synthetic_segments(
    n: int = 4096,
    t: int = 120,
    d: int = 14,
    num_modes: int = 8,
    seed: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Create multimodal skill segments.

    Each mode has a distinct temporal pattern; amplitude, phase, duration warp,
    and endpoint offsets create continuous intra-mode variation.
    """

    gen = torch.Generator().manual_seed(seed)
    time = torch.linspace(0.0, 1.0, t)
    mode_ids = torch.randint(0, num_modes, (n,), generator=gen)
    segments = torch.empty(n, t, d)

    feature_phase = torch.linspace(0.0, torch.pi, d)
    feature_scale = torch.linspace(0.65, 1.35, d)

    for i in range(n):
        mode = int(mode_ids[i])
        amp = 0.65 + 0.8 * torch.rand((), generator=gen)
        phase = 2.0 * torch.pi * torch.rand((), generator=gen)
        warp = 0.75 + 0.5 * torch.rand((), generator=gen)
        endpoint = 0.35 * torch.randn(d, generator=gen)
        bias = 0.15 * torch.randn(d, generator=gen)

        tau = torch.clamp(time.pow(warp), 0.0, 1.0)
        freq = 1.0 + (mode % 4)
        sign = -1.0 if mode >= num_modes // 2 else 1.0

        if mode % 4 == 0:
            base = torch.sin(2.0 * torch.pi * freq * tau[:, None] + feature_phase[None, :] + phase)
        elif mode % 4 == 1:
            base = torch.cos(2.0 * torch.pi * freq * tau[:, None] + 0.5 * feature_phase[None, :] + phase)
        elif mode % 4 == 2:
            pulse = torch.exp(-((tau - 0.25 - 0.08 * (mode % 3)) ** 2) / 0.018)
            base = pulse[:, None] * torch.sin(torch.pi * tau[:, None] * feature_scale[None, :] + phase)
        else:
            saw = 2.0 * ((freq * tau + phase / (2.0 * torch.pi)) % 1.0) - 1.0
            base = saw[:, None] * torch.cos(feature_phase[None, :] + 0.3 * mode)

        ramp = tau[:, None] * endpoint[None, :]
        segments[i] = sign * amp * base * feature_scale[None, :] + ramp + bias[None, :]

    segments += 0.03 * torch.randn(segments.shape, generator=gen)
    return segments, mode_ids


def load_segments(path: str | Path) -> torch.Tensor:
    path = Path(path)
    if path.suffix == ".pt":
        obj = torch.load(path, map_location="cpu")
        if isinstance(obj, dict):
            for key in ("segments", "x", "data"):
                if key in obj:
                    obj = obj[key]
                    break
        segments = torch.as_tensor(obj)
    elif path.suffix == ".npz":
        obj = np.load(path)
        key = "segments" if "segments" in obj.files else obj.files[0]
        segments = torch.from_numpy(obj[key])
    else:
        raise ValueError(f"unsupported data file suffix: {path.suffix}")

    if segments.ndim != 3:
        raise ValueError(f"loaded data must have shape [N, T, D], got {tuple(segments.shape)}")
    return segments.float()


def load_segment_arrays(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    segments = load_segments(path)
    out: dict[str, Any] = {"segments": segments}
    if path.suffix != ".npz":
        return out

    obj = np.load(path, allow_pickle=True)
    if "valid_mask" in obj.files:
        out["valid_mask"] = torch.from_numpy(np.asarray(obj["valid_mask"], dtype=np.bool_))
    if "lengths" in obj.files:
        out["lengths"] = torch.from_numpy(np.asarray(obj["lengths"], dtype=np.int64))
    elif "valid_mask" in out:
        out["lengths"] = out["valid_mask"].long().sum(dim=1)
    metadata_keys = [
        "segment_ids",
        "motion_ids",
        "source_paths",
        "start_frames",
        "end_frames",
        "active_bodies",
        "feature_keys",
    ]
    metadata = {
        key: obj[key]
        for key in metadata_keys
        if key in obj.files and np.asarray(obj[key]).shape[:1] == (segments.shape[0],)
    }
    if metadata:
        out["metadata"] = metadata
    return out


def normalize_segments(
    segments: torch.Tensor,
    stats: Optional[NormStats] = None,
    eps: float = 1e-6,
) -> tuple[torch.Tensor, NormStats]:
    if stats is None:
        mean = segments.mean(dim=(0, 1), keepdim=True)
        std = segments.std(dim=(0, 1), keepdim=True).clamp_min(eps)
        stats = NormStats(mean=mean, std=std)
    return (segments - stats.mean) / stats.std, stats


def normalize_segments_masked(
    segments: torch.Tensor,
    valid_mask: Optional[torch.Tensor] = None,
    stats: Optional[NormStats] = None,
    eps: float = 1e-6,
) -> tuple[torch.Tensor, NormStats]:
    if stats is not None or valid_mask is None:
        return normalize_segments(segments, stats=stats, eps=eps)
    if valid_mask.shape != segments.shape[:2]:
        raise ValueError(
            f"valid_mask must have shape [N, T]={tuple(segments.shape[:2])}, got {tuple(valid_mask.shape)}"
        )
    mask = valid_mask.to(dtype=segments.dtype, device=segments.device).unsqueeze(-1)
    denom = mask.sum(dim=(0, 1), keepdim=True).clamp_min(1.0)
    mean = (segments * mask).sum(dim=(0, 1), keepdim=True) / denom
    var = ((segments - mean).square() * mask).sum(dim=(0, 1), keepdim=True) / denom
    stats = NormStats(mean=mean, std=var.sqrt().clamp_min(eps))
    normalized = (segments - stats.mean) / stats.std
    return normalized * mask, stats


def denormalize_segments(segments: torch.Tensor, stats: NormStats) -> torch.Tensor:
    return segments * stats.std.to(segments.device) + stats.mean.to(segments.device)


def build_dataset(
    data: Optional[str],
    synthetic: bool,
    normalize: bool = True,
    synthetic_n: int = 4096,
    t: int = 120,
    d: int = 14,
) -> tuple[SegmentDataset | MaskedSegmentDataset, Optional[NormStats]]:
    if data:
        arrays = load_segment_arrays(data)
        segments = arrays["segments"]
        valid_mask = arrays.get("valid_mask")
        lengths = arrays.get("lengths")
        metadata = arrays.get("metadata")
    elif synthetic:
        segments, _ = make_synthetic_segments(n=synthetic_n, t=t, d=d)
        valid_mask = None
        lengths = None
        metadata = None
    else:
        raise ValueError("provide --data or --synthetic")

    stats: Optional[NormStats] = None
    if normalize:
        segments, stats = normalize_segments_masked(segments, valid_mask)
    if valid_mask is not None and lengths is not None:
        return MaskedSegmentDataset(segments, valid_mask, lengths, metadata=metadata), stats
    return SegmentDataset(segments), stats
