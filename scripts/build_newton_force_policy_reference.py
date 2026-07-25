#!/usr/bin/env python3
"""Build a WBT policy reference from edited kinematics and calculated force."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from motion_edit.contact_force.frame_boundary_replay import (
    build_force_policy_reference,
)
from somaforge_core.contact_schema import decode_contact_force_provenance
from somaforge_core.motion_schema import decode_kinematics_provenance


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {key: np.asarray(data[key]) for key in data.files}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kinematics", required=True, type=Path)
    parser.add_argument("--replay-force", required=True, type=Path)
    parser.add_argument("--rollout-recording", required=True, type=Path)
    parser.add_argument("--terrain", required=True, type=Path)
    parser.add_argument("--output-motion", required=True, type=Path)
    parser.add_argument("--output-manifest", required=True, type=Path)
    parser.add_argument("--motion-id", default="climb00_height110")
    return parser


def main() -> None:
    args = _parser().parse_args()
    inputs = (
        args.kinematics,
        args.replay_force,
        args.rollout_recording,
        args.terrain,
    )
    for path in inputs:
        if not path.expanduser().is_file():
            raise FileNotFoundError(path)
    if args.output_motion.exists():
        raise FileExistsError(args.output_motion)
    if args.output_manifest.exists():
        raise FileExistsError(args.output_manifest)

    kinematics_path = args.kinematics.expanduser().resolve()
    replay_path = args.replay_force.expanduser().resolve()
    recording_path = args.rollout_recording.expanduser().resolve()
    terrain_path = args.terrain.expanduser().resolve()
    kinematics = _load_npz(kinematics_path)
    replay = _load_npz(replay_path)
    with np.load(recording_path, allow_pickle=False) as recording:
        recording_metadata = json.loads(str(recording["_metadata_json"].item()))

    output = build_force_policy_reference(
        kinematics=kinematics,
        replay=replay,
        recording_metadata=recording_metadata,
        recording_path=recording_path,
        kinematics_path=kinematics_path,
    )
    args.output_motion.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output_motion, **output)

    kinematics_provenance = decode_kinematics_provenance(
        output["kinematics_provenance_json"],
        context=str(args.output_motion),
        require_newton=True,
    )
    contact_provenance = decode_contact_force_provenance(
        output["contact_force_provenance_json"],
        context=str(args.output_motion),
        require_newton=True,
    )
    manifest = {
        "schema_version": 1,
        "description": (
            "Single-motion policy reference with direct Newton kinematics and "
            "frame-boundary Newton replay force."
        ),
        "source_kind": "motion_edit_newton_frame_boundary_dynamic_replay",
        "motion_files": [
            {
                "motion_id": 0,
                "motion_name": str(args.motion_id),
                "motion_file": str(args.output_motion.resolve()),
                "motion_sha256": _sha256(args.output_motion),
                "source_file": str(kinematics_path),
                "source_sha256": _sha256(kinematics_path),
                "terrain_id": 0,
                "weight": 1.0,
                "kinematics_backend": kinematics_provenance["kinematics_backend"],
                "contact_force_source": contact_provenance["source_backend"],
            }
        ],
        "terrains": [
            {
                "terrain_id": 0,
                "terrain_file": str(terrain_path),
                "terrain_sha256": _sha256(terrain_path),
            }
        ],
    }
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    force = np.asarray(output["contact_force_part_w"])
    print(
        json.dumps(
            {
                "motion": str(args.output_motion.resolve()),
                "manifest": str(args.output_manifest.resolve()),
                "frames": int(force.shape[0]),
                "force_shape": list(force.shape),
                "force_norm_max_n": float(
                    np.linalg.norm(force, axis=-1).max(initial=0.0)
                ),
                "kinematics_backend": kinematics_provenance["kinematics_backend"],
                "contact_source_backend": contact_provenance["source_backend"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
