#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def env_path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser()


def require_path(label: str, path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    print(f"[ok] {label}: {path}")


def load_cut_entry(cut_summary: Path, motion_id: str) -> dict:
    with cut_summary.open("r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data if isinstance(data, list) else list(data.values())
    for entry in entries:
        if entry.get("motion_id") == motion_id:
            return entry
    raise KeyError(f"motion_id not found in cut summary: {motion_id}")


def npz_names(arr: np.lib.npyio.NpzFile, key: str) -> list[str]:
    return [str(x) for x in arr[key].tolist()]


def main() -> None:
    motion_edit = env_path("MOTION_EDIT_REPO", "/home/xiaz/motion_edit")
    gmvq_vae = env_path("GMVQ_VAE_REPO", "/home/xiaz/gmvq-vae")
    holosoma = env_path("HOLOSOMA_NEWTON_REPO", str(ROOT))
    clean_ref = env_path(
        "CLIMB00_CLEAN_REF",
        str(ROOT / "OmniRetarget_Dataset/data/holosoma_motions_50hz/climb_00_z_scale_1.0.npz"),
    )
    cut_summary = env_path(
        "MOTION_EDIT_CUT_SUMMARY",
        "/home/xiaz/motion_edit/data/workbench/raw_contact_29_cut_summary.json",
    )
    rollout_contact = env_path(
        "CLIMB00_ROLLOUT_CONTACT",
        str(ROOT / "tmp/rollout_ref_contact_points_29/motions/climb_00_rollout_ref_contact_force.npz"),
    )
    motion_id = os.environ.get("MOTION_ID", "climb_00_z_scale_1.0")

    require_path("motion_edit repo", motion_edit / ".git")
    require_path("gmvq-vae repo", gmvq_vae / ".git")
    require_path("holosoma_newton repo", holosoma / ".git")
    require_path("clean ref", clean_ref)
    require_path("cut summary", cut_summary)
    if rollout_contact.exists():
        print(f"[ok] optional rollout contact metadata: {rollout_contact}")
    else:
        print(f"[warn] optional rollout contact metadata missing: {rollout_contact}")

    cut = load_cut_entry(cut_summary, motion_id)
    cut_frames = [int(x) for x in cut["cut_frames"]]
    print(f"[cut] motion_id={motion_id} frames={cut_frames}")
    print(f"[cut] source motion_path in summary={cut.get('motion_path')}")

    with np.load(clean_ref, allow_pickle=True) as ref:
        required = {
            "fps",
            "joint_names",
            "body_names",
            "joint_pos",
            "joint_vel",
            "body_pos_w",
            "body_quat_w",
            "body_lin_vel_w",
            "body_ang_vel_w",
        }
        missing = sorted(required - set(ref.files))
        if missing:
            raise KeyError(f"clean ref missing required keys: {missing}")
        n_frames = int(ref["joint_pos"].shape[0])
        print(
            "[ref] "
            f"frames={n_frames} joints={len(npz_names(ref, 'joint_names'))} "
            f"bodies={len(npz_names(ref, 'body_names'))}"
        )
        if cut_frames[-1] < n_frames:
            print(f"[warn] cut summary stops at {cut_frames[-1]}, clean ref has {n_frames} frames")
        elif cut_frames[-1] > n_frames:
            raise ValueError(f"cut summary ends past clean ref: {cut_frames[-1]} > {n_frames}")

    if rollout_contact.exists():
        with np.load(clean_ref, allow_pickle=True) as ref, np.load(rollout_contact, allow_pickle=True) as roll:
            ref_bodies = len(npz_names(ref, "body_names"))
            roll_bodies = len(npz_names(roll, "body_names"))
            if roll_bodies != ref_bodies:
                print(
                    "[warn] rollout body count differs from clean ref "
                    f"({roll_bodies} vs {ref_bodies}); use rollout only for metadata"
                )
            diff = np.abs(np.asarray(ref["joint_pos"], dtype=np.float32) - np.asarray(roll["joint_pos"], dtype=np.float32))
            print(
                "[rollout-vs-ref] "
                f"joint_pos mae={float(diff.mean()):.6f} maxabs={float(diff.max()):.6f}"
            )

    print("[done] workspace checks completed")


if __name__ == "__main__":
    main()
