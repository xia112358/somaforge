from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .data import NormStats, denormalize_segments, load_segment_arrays, normalize_segments_masked
from .models import GMVQAutoEncoder
from somaforge_core.robot_assets import encode_robot_asset_json, validate_g1_asset_metadata


def _load_npz(path: str | Path) -> dict[str, Any]:
    with np.load(Path(path).expanduser(), allow_pickle=True) as data:
        return {key: data[key] for key in data.files}


def _feature_keys(path: str | Path) -> list[str]:
    with np.load(Path(path).expanduser(), allow_pickle=True) as data:
        if "feature_keys" not in data.files:
            raise ValueError("prepared dataset is missing feature_keys")
        return [str(item) for item in np.asarray(data["feature_keys"]).reshape(-1).tolist()]


def _split_feature_frame(row: np.ndarray, *, source_motion: dict[str, Any], feature_keys: list[str]) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    offset = 0
    for key in feature_keys:
        if key not in source_motion:
            raise KeyError(f"source motion missing feature key {key!r}")
        shape = tuple(np.asarray(source_motion[key]).shape[1:])
        width = int(np.prod(shape, dtype=np.int64))
        values = row[offset : offset + width]
        if values.shape[0] != width:
            raise ValueError(f"decoded row ended while reading feature {key!r}")
        out[key] = values.reshape(shape)
        offset += width
    if offset != row.shape[0]:
        raise ValueError(f"decoded row has {row.shape[0]} dims but feature split consumed {offset}")
    return out


def _copy_source_motion(source_motion: dict[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = {}
    for key, value in source_motion.items():
        arr = np.asarray(value)
        copied[key] = arr.copy() if arr.flags.writeable else np.array(arr)
    return copied


def decode_segments(
    *,
    checkpoint: str | Path,
    data: str | Path,
    output: str | Path,
    device: str = "cpu",
    source_motion: str | Path | None = None,
    latents_output: str | Path | None = None,
) -> Path:
    ckpt = torch.load(Path(checkpoint).expanduser(), map_location="cpu")
    validate_g1_asset_metadata(ckpt.get("robot_asset"), context=f"GMVQ checkpoint {checkpoint}")
    cfg = ckpt["model_config"]
    arrays = load_segment_arrays(data)
    segments = arrays["segments"]
    valid_mask = arrays.get("valid_mask")
    lengths = arrays.get("lengths")
    metadata = arrays.get("metadata") or {}
    feature_keys = _feature_keys(data)

    ns = ckpt.get("norm_stats")
    stats = NormStats(mean=ns["mean"], std=ns["std"]) if ns is not None else None
    x, _ = normalize_segments_masked(segments, valid_mask, stats=stats)

    model = GMVQAutoEncoder(**cfg).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    with torch.no_grad():
        out = model(
            x.to(device),
            valid_mask=None if valid_mask is None else valid_mask.to(device),
            lengths=None if lengths is None else lengths.to(device),
        )
    recon = out["x_recon"].cpu()
    if stats is not None:
        recon = denormalize_segments(recon, stats)
    recon_np = recon.numpy()

    source_paths = np.asarray(metadata.get("source_paths"), dtype=object).reshape(-1)
    if source_motion is None:
        if source_paths.size == 0:
            raise ValueError("provide --source-motion when prepared dataset has no source_paths metadata")
        source_motion_path = Path(str(source_paths[0])).expanduser()
    else:
        source_motion_path = Path(source_motion).expanduser()
    source = _load_npz(source_motion_path)
    decoded = _copy_source_motion(source)

    start_frames = np.asarray(metadata.get("start_frames"), dtype=np.int64).reshape(-1)
    end_frames = np.asarray(metadata.get("end_frames"), dtype=np.int64).reshape(-1)
    if lengths is None:
        lengths_np = end_frames - start_frames
    else:
        lengths_np = lengths.numpy().astype(np.int64)

    for i, (start, end, length) in enumerate(zip(start_frames, end_frames, lengths_np)):
        count = min(int(length), int(end) - int(start), recon_np.shape[1])
        for local in range(count):
            split = _split_feature_frame(recon_np[i, local], source_motion=source, feature_keys=feature_keys)
            frame = int(start) + local
            for key, value in split.items():
                decoded[key][frame] = value.astype(decoded[key].dtype, copy=False)

    decoded["gmvq_decode_metadata"] = np.asarray(
        json.dumps(
            {
                "checkpoint": str(Path(checkpoint).expanduser()),
                "prepared_data": str(Path(data).expanduser()),
                "source_motion": str(source_motion_path),
                "feature_keys": feature_keys,
                "segment_count": int(recon_np.shape[0]),
            },
            sort_keys=True,
        ),
        dtype=object,
    )
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output_path, **decoded)

    if latents_output is not None:
        lat_path = Path(latents_output).expanduser().resolve()
        lat_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            lat_path,
            codes=out["codes"].cpu().numpy(),
            theta=out["theta"].cpu().numpy(),
            z_e=out["z_e"].cpu().numpy(),
            z_q=out["z_q"].cpu().numpy(),
            lengths=None if lengths is None else lengths.numpy(),
            segment_ids=np.asarray(metadata.get("segment_ids"), dtype=object),
            start_frames=start_frames,
            end_frames=end_frames,
            source_paths=source_paths,
            robot_asset_json=np.asarray(encode_robot_asset_json(ckpt["robot_asset"])),
        )
    return output_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Decode a GMVQ motion_edit segment dataset back to a full ref npz.")
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--source-motion", default=None)
    p.add_argument("--latents-output", default=None)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out = decode_segments(
        checkpoint=args.checkpoint,
        data=args.data,
        output=args.output,
        device=args.device,
        source_motion=args.source_motion,
        latents_output=args.latents_output,
    )
    print(f"wrote decoded ref {out}")


if __name__ == "__main__":
    main()
