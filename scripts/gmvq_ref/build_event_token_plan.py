#!/usr/bin/env python3
"""Build an event-triggered GMVQ token plan from motion_edit segments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


BODY_TO_PART = {
    "left_foot": "LF",
    "right_foot": "RF",
    "left_hand": "LH",
    "right_hand": "RH",
    "left_knee": "LK",
    "right_knee": "RK",
    "left_hip": "LHIP",
    "right_hip": "RHIP",
}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _load_latents(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        required = {"codes", "theta", "lengths", "start_frames", "end_frames"}
        missing = required - set(data.files)
        if missing:
            raise KeyError(f"{path} missing latent keys: {sorted(missing)}")
        return {key: np.asarray(data[key]) for key in required}


def _support_bodies(segment: dict[str, Any]) -> list[str]:
    raw = segment.get("support_bodies")
    if isinstance(raw, list):
        return [str(item) for item in raw]
    raw = segment.get("support", "")
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    return []


def _part_for_body(body: str | None) -> str:
    if not body:
        return ""
    return BODY_TO_PART.get(body, str(body).upper())


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.motion_edit_manifest.expanduser().resolve()
    latents_path = args.latents.expanduser().resolve()
    manifest = _read_json(manifest_path)
    latents = _load_latents(latents_path)

    motions = manifest.get("motions")
    if not isinstance(motions, list) or len(motions) != 1:
        raise ValueError("event token smoke path expects exactly one motion in motion_edit manifest")
    motion = motions[0]
    segments = motion.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError(f"manifest has no segments: {manifest_path}")

    count = len(segments)
    for key, values in latents.items():
        if values.shape[0] != count:
            raise ValueError(f"latent {key} count={values.shape[0]} does not match segments={count}")

    tokens: list[dict[str, Any]] = []
    for i, segment in enumerate(segments):
        start = int(segment["start_frame"])
        end = int(segment["end_frame"])
        latent_start = int(latents["start_frames"][i])
        latent_end = int(latents["end_frames"][i])
        if (start, end) != (latent_start, latent_end):
            raise ValueError(
                f"segment {i} frame mismatch: manifest=({start},{end}) latent=({latent_start},{latent_end})"
            )

        active_body = str(segment.get("active_body") or segment.get("active") or "")
        observed_length = int(latents["lengths"][i])
        timeout = max(end, start + observed_length)
        tokens.append(
            {
                "index": i,
                "segment_id": str(segment.get("segment_id", f"segment_{i:04d}")),
                "code": int(latents["codes"][i]),
                "theta": latents["theta"][i].astype(float).tolist(),
                "start_frame": start,
                "end_frame": end,
                "observed_length": observed_length,
                "timeout_frame": timeout,
                "active_body": active_body,
                "target_part": _part_for_body(active_body),
                "support_bodies": _support_bodies(segment),
                "support_parts": [_part_for_body(body) for body in _support_bodies(segment)],
                "transition_type": segment.get("transition_type"),
                "source_anchor_id": segment.get("source_anchor_id"),
                "target_anchor_id": segment.get("target_anchor_id"),
                "trigger": {
                    "type": "contact_rising_edge",
                    "part": _part_for_body(active_body),
                },
            }
        )

    return {
        "schema_version": 1,
        "kind": "gmvq_event_token_plan",
        "mode": "contact_rising_edge",
        "source_manifest": str(manifest_path),
        "latents": str(latents_path),
        "motion_id": str(motion.get("motion_id", "")),
        "motion_file": str(motion.get("motion_file", "")),
        "token_count": len(tokens),
        "tokens": tokens,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--motion-edit-manifest", required=True, type=Path)
    parser.add_argument("--latents", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--timeout-margin-frames",
        type=int,
        default=10,
        help="Deprecated; timeout margin is applied by MotionConfig.event_token_timeout_margin_frames.",
    )
    args = parser.parse_args()

    plan = build_plan(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    starts = [token["start_frame"] for token in plan["tokens"]]
    ends = [token["end_frame"] for token in plan["tokens"]]
    parts = [token["target_part"] for token in plan["tokens"]]
    print(f"Wrote {args.output} tokens={len(starts)} frames={starts[0]}..{ends[-1]} parts={parts}")


if __name__ == "__main__":
    main()
