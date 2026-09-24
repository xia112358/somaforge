#!/usr/bin/env python3
"""Four-way endpoint projector oracle on the 18-event climb00 sequence."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import socket
import subprocess
import sys
import time

import numpy as np
import torch


ROOT = Path.cwd().resolve()
if not (ROOT / "packages/climb00_pipeline/climb00_pipeline").is_dir():
    ROOT = Path(__file__).resolve().parents[1]
for package in (ROOT / "packages/climb00_pipeline", ROOT / "packages/somaforge_core", ROOT / "tmp"):
    sys.path.insert(0, str(package))

from climb00_pipeline.contact_constrained_projector import NewtonContactProjector
from climb00_pipeline.fullbody_dataset import _matrix_quaternion_wxyz, _quaternion_matrix_wxyz
from climb00_pipeline.next_interaction_heightmap_v2 import (
    _root_yaw_basis,
    heightmap_supersample_for_architecture,
    render_root_yaw_box_heightmaps,
)
from climb00_pipeline.next_interaction_heightmap_v4 import (
    BoundHeightmapInteractionPredictor,
    JointBoundHeightmapInteractionPredictor,
)
from somaforge_core.contact_face_selection import select_contact_pairs
from somaforge_core.newton_contact_query import query_contacts
from somaforge_core.robot_assets import decode_robot_asset_json
from train_climb00_scan_action_q_deformer import box_obbs


DEFAULT_CHECKPOINT = ROOT / "tmp/predictor_heightmap_v4_singlepoint100/1789626046577313625/predictor/best.pt"
DEFAULT_OUTPUT = ROOT / "tmp/contact_constrained_projector_oracle_v1"
DATA_CACHE = ROOT / "tmp/predictor_preprocessing_cache/e68ff83005af2c7858a8472454893239f44db5034a3245ed0f1f07cc58cf9d45.pt"
Q_CACHE = ROOT / "tmp/temporal207_training_v2_ready/q_cache.npz"
MANIFEST = ROOT / "tmp/temporal207_training_v2_ready/manifest.json"
AUDIT = ROOT / "tmp/newton_contact_sources_v1/1789326506727043514"
POLICY_CHECKPOINT = ROOT / "runtime/current/holosoma/logs/WholeBodyTracking/20260727_085520-g1_29dof_wbt_single_climb00_completionema_horizon50_ncon160_from4k_to10k-locomotion/model_06000.pt"


def yaw_frame(local_q: np.ndarray, world_q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    basis = _quaternion_matrix_wxyz(world_q[3:7]) @ _quaternion_matrix_wxyz(local_q[3:7]).T
    origin = world_q[:3] - basis @ local_q[:3]
    if not np.allclose(basis[2], (0, 0, 1), atol=1.0e-5):
        raise ValueError("dataset frame is not a ground-preserving yaw transform")
    return origin.astype(np.float32), basis.astype(np.float32)


def to_world_q(q: np.ndarray, origin: np.ndarray, basis: np.ndarray) -> np.ndarray:
    result = np.asarray(q, np.float32).copy()
    result[:3] = origin + basis @ result[:3]
    result[3:7] = _matrix_quaternion_wxyz(basis @ _quaternion_matrix_wxyz(result[3:7]))
    return result


def to_world_points(points: np.ndarray, origin: np.ndarray, basis: np.ndarray) -> np.ndarray:
    return np.asarray(points, np.float32) @ basis.T + origin


def to_local_points(points: np.ndarray, origin: np.ndarray, basis: np.ndarray) -> np.ndarray:
    return (np.asarray(points, np.float32) - origin) @ basis


def load_model(checkpoint: dict, device: torch.device):
    architecture = checkpoint["config"]["architecture"]
    width = int(checkpoint["config"]["width"])
    layers = int(checkpoint["config"]["layers"])
    if architecture == "heightmap_v4_bound":
        model = BoundHeightmapInteractionPredictor(width, layers)
    elif architecture == "heightmap_v5_joint_bound":
        model = JointBoundHeightmapInteractionPredictor(width, layers)
    else:
        raise ValueError("oracle requires a bound predictor with a predicted contact region")
    model.load_state_dict(checkpoint["model"])
    return model.to(device).eval(), architecture


def observe(q_world: np.ndarray, endpoint: str) -> dict[str, np.ndarray]:
    raw = query_contacts(q_world[None], None, endpoint=endpoint)
    selected = select_contact_pairs(raw["pairs"], raw["surface_catalog"])
    return {
        "mask": np.asarray(selected["contact_part_mask"][0], dtype=bool),
        "surface": np.asarray(selected["contact_surface"][0], dtype=np.int64),
        "position_w": np.asarray(selected["contact_position_w"][0], dtype=np.float32),
    }


def result_record(result, reference_world: np.ndarray) -> dict:
    selected = select_contact_pairs(
        result.observed["pairs"], result.observed["surface_catalog"]
    )
    return {
        "converged": result.converged,
        "iterations": result.iterations,
        "intended_contact": result.intended_contact.detach().cpu().tolist(),
        "intended_surface": result.intended_surface.detach().cpu().tolist(),
        "actual_contact": result.actual_contact.detach().cpu().tolist(),
        "actual_surface": result.actual_surface.detach().cpu().tolist(),
        "actual_contact_position_w": np.asarray(
            selected["contact_position_w"][0], dtype=np.float32
        ).tolist(),
        "unrealized_contacts": result.unrealized_contacts,
        "extra_contacts": result.extra_contacts,
        "maximum_penetration_cm": 100.0 * result.maximum_penetration_m,
        "attempted_maximum_penetration_cm": (
            100.0 * result.attempted_maximum_penetration_m
        ),
        "safety_fallback_used": result.safety_fallback_used,
        "root_displacement_cm": 100.0 * result.root_displacement_m,
        "maximum_joint_displacement_rad": result.joint_displacement_rad,
        "reference_root_error_cm": 100.0 * float(
            np.linalg.norm(result.qpos[:3].detach().cpu().numpy() - reference_world[:3])
        ),
        "projected_q_world": result.qpos.detach().cpu().tolist(),
        "history": list(result.history),
    }


def evaluate(args: argparse.Namespace, endpoint: str) -> None:
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    args.output.mkdir(parents=True)
    payload = torch.load(DATA_CACHE, map_location="cpu", weights_only=False)
    samples, data = payload["samples"], payload["data"]
    manifest = json.loads(MANIFEST.read_text())
    with np.load(Q_CACHE, allow_pickle=False) as cache:
        q_segments = np.asarray(cache["target_q"], dtype=np.float32)
    checkpoint = torch.load(args.checkpoint, map_location=args.device, weights_only=False)
    decode_robot_asset_json(checkpoint["robot_asset_json"], context="contact projector oracle")
    device = torch.device(args.device)
    model, architecture = load_model(checkpoint, device)
    centers, rotations, half_extents, grounds = box_obbs(data)
    rows = [i for i, sample in enumerate(samples) if int(sample["motion_id"]) == args.motion_id]
    rows.sort(key=lambda row: int(samples[row]["current_frame"]))
    if len(rows) != 18:
        raise ValueError(f"expected the 18-event oracle sequence, found {len(rows)} events")
    entry = manifest["motion_files"][args.motion_id]
    with np.load(entry["motion_file"], allow_pickle=False) as motion:
        decode_robot_asset_json(motion["robot_asset_json"], context="contact projector oracle reference")
        world_motion = np.asarray(motion["joint_pos"], dtype=np.float32)
        joint_names = np.asarray(motion["joint_names"]).astype(str).tolist()

    provider = lambda q, geometry: query_contacts(q, geometry, endpoint=endpoint)
    projector = NewtonContactProjector(
        provider,
        iterations=args.iterations,
        damping=args.damping,
        maximum_step=args.maximum_step,
    ).to(device)
    variant_names = (
        "gt_topology_whole_surface",
        "gt_topology_gt_patch",
        "predicted_topology_whole_surface",
        "predicted_topology_gt_patch",
        "predicted_topology_predicted_patch",
    )
    records = []
    for event_index, row in enumerate(rows):
        current_local = q_segments[row, 0]
        current_world = world_motion[int(samples[row]["current_frame"])]
        reference_world = world_motion[int(samples[row]["target_frame"])]
        origin, frame_basis = yaw_frame(current_local, current_world)
        current_observed = observe(current_world, endpoint)
        anchor_local = to_local_points(current_observed["position_w"], origin, frame_basis)
        heightmap = render_root_yaw_box_heightmaps(
            centers[row : row + 1],
            rotations[row : row + 1],
            half_extents[row : row + 1],
            grounds[row : row + 1],
            current_local[None],
            supersample=heightmap_supersample_for_architecture(architecture),
        )
        inputs = {
            "current_q": torch.as_tensor(current_local[None], device=device),
            "current_contact": torch.as_tensor(current_observed["mask"][None], device=device),
            "current_anchor": torch.as_tensor(anchor_local[None], device=device),
            "current_surface": torch.as_tensor(current_observed["surface"][None], device=device),
            "heightmap": torch.as_tensor(heightmap, device=device),
        }
        with torch.no_grad():
            prediction = model(**inputs)
            nominal_world = to_world_q(prediction.qpos[0].cpu().numpy(), origin, frame_basis)
            local_yaw_basis, _ = _root_yaw_basis(inputs["current_q"])
            predicted_anchor_local = inputs["current_q"][0, :3] + torch.einsum(
                "ij,pj->pi", local_yaw_basis[0], prediction.binding_points_local[0]
            )
        predicted_anchor_world = to_world_points(
            predicted_anchor_local.cpu().numpy(), origin, frame_basis
        )
        gt_anchor_world = to_world_points(data["target_contacts"][row], origin, frame_basis)
        world_center = origin + frame_basis @ centers[row]
        world_rotation = frame_basis @ rotations[row]
        half = half_extents[row]
        top_region = np.concatenate((
            world_center + world_rotation[:, 2] * half[2],
            world_rotation[:, 0],
            world_rotation[:, 1],
            half[:2],
        )).astype(np.float32)
        surface_regions = {1: torch.as_tensor(top_region, device=device)}
        gt_contact = np.asarray(data["end_contact"][row], dtype=bool)
        gt_surface = np.asarray(data["target_surfaces"][row], dtype=np.int64)
        predicted_contact = prediction.contact[0].detach().cpu().numpy().astype(bool)
        predicted_surface = prediction.surface[0].detach().cpu().numpy().astype(np.int64)
        variants = (
            (gt_contact, gt_surface, gt_anchor_world, False),
            (gt_contact, gt_surface, gt_anchor_world, True),
            (predicted_contact, predicted_surface, predicted_anchor_world, False),
            (predicted_contact, predicted_surface, gt_anchor_world, True),
            (predicted_contact, predicted_surface, predicted_anchor_world, True),
        )
        event = {
            "event_index": event_index,
            "row": int(row),
            "frames": [int(samples[row]["current_frame"]), int(samples[row]["target_frame"])],
            "nominal_q_world": nominal_world.tolist(),
            "reference_q_world": reference_world.tolist(),
            "nominal_reference_root_error_cm": 100.0 * float(
                np.linalg.norm(nominal_world[:3] - reference_world[:3])
            ),
            "variants": {},
        }
        for name, (contact, surface, anchor, patch) in zip(variant_names, variants, strict=True):
            result = projector.project(
                torch.as_tensor(nominal_world, device=device),
                torch.as_tensor(contact, device=device),
                torch.as_tensor(surface, device=device),
                torch.as_tensor(anchor, device=device),
                patch=patch,
                surface_regions=surface_regions,
                safe_qpos=torch.as_tensor(current_world, device=device),
            )
            event["variants"][name] = result_record(result, reference_world)
        records.append(event)
        print(json.dumps({
            "event": event_index + 1,
            "rows": row,
            "converged": {
                name: event["variants"][name]["converged"] for name in variant_names
            },
        }), flush=True)

    summary = {}
    for name in variant_names:
        values = [event["variants"][name] for event in records]
        nominal = [value["history"][0] for value in values]
        summary[name] = {
            "converged": sum(bool(value["converged"]) for value in values),
            "events": len(values),
            "nominal_topology_exact": sum(bool(value["topology_exact"]) for value in nominal),
            "nominal_mean_unrealized_contacts": float(np.mean([value["unrealized_contacts"] for value in nominal])),
            "nominal_mean_extra_contacts": float(np.mean([value["extra_contacts"] for value in nominal])),
            "nominal_mean_penetration_cm": 100.0 * float(np.mean([value["maximum_penetration_m"] for value in nominal])),
            "nominal_max_penetration_cm": 100.0 * float(max(value["maximum_penetration_m"] for value in nominal)),
            "mean_unrealized_contacts": float(np.mean([value["unrealized_contacts"] for value in values])),
            "mean_extra_contacts": float(np.mean([value["extra_contacts"] for value in values])),
            "mean_penetration_cm": float(np.mean([value["maximum_penetration_cm"] for value in values])),
            "max_penetration_cm": float(max(value["maximum_penetration_cm"] for value in values)),
            "mean_root_displacement_cm": float(np.mean([value["root_displacement_cm"] for value in values])),
            "mean_reference_root_error_cm": float(np.mean([value["reference_root_error_cm"] for value in values])),
        }
    report = {
        "schema": "next_contact_feasible_projection_oracle_v1",
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_step": int(checkpoint["step"]),
        "architecture": architecture,
        "motion_id": args.motion_id,
        "terrain": next(
            row["terrain_file"]
            for row in manifest["terrains"]
            if row["terrain_id"] == entry["terrain_id"]
        ),
        "joint_names": joint_names,
        "robot_asset_json": checkpoint["robot_asset_json"],
        "contract": {
            "nominal_pose": "one-pass predictor endpoint",
            "projection_coordinates": "35D floating-base tangent (root 6 + canonical 29 joints)",
            "contact_truth": "fresh Newton/MJWarp constraint activation, allocation, and shared primary-face selection",
            "active_constraint": "refreshed Newton witness physical separation -> 0",
            "inactive_constraint": "refreshed pair dist >= that pair's actual includemargin",
            "penetration_constraint": "refreshed Newton closest terrain/self witness held on positive side; interior clearance is a fraction of actual solver includemargin",
            "missing_pair_approach": "canonical collision material point to proposed patch or target plane",
            "training": False,
        },
        "summary": summary,
        "events": records,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


def run(args: argparse.Namespace) -> None:
    manifest = json.loads(MANIFEST.read_text())
    entry = manifest["motion_files"][args.motion_id]
    terrain_ids = [row["terrain_id"] for row in manifest["terrains"]]
    scene_index = terrain_ids.index(entry["terrain_id"])
    source = AUDIT / f"scene_{scene_index}"
    worker_dir = args.output.parent / f"{args.output.name}_worker_{time.time_ns()}"
    worker_dir.mkdir(parents=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    endpoint = f"http://127.0.0.1:{port}"
    log_path = worker_dir / "worker.log"
    with log_path.open("w") as log:
        command = [
            sys.executable,
            "scripts/serve_newton_contact_queries.py",
            "--checkpoint", str(POLICY_CHECKPOINT),
            "--motion-manifest", str(source / "manifest.json"),
            "--binding", str(worker_dir / "binding.json"),
            "--create-native-binding",
            "--inspection-output", str(worker_dir / "model.json"),
            "--query-nconmax", "2048",
            "--query-njmax", "16384",
            "--port", str(port),
            "--device", "cuda:0",
            "--capture-contact-sources",
        ]
        worker = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 180.0
            while not log_path.exists() or '"ready": true' not in log_path.read_text():
                if worker.poll() is not None:
                    raise RuntimeError(f"Newton worker exited; see {log_path}")
                if time.monotonic() > deadline:
                    raise TimeoutError("Newton worker startup timeout")
                time.sleep(2.0)
            evaluate(args, endpoint)
        finally:
            if worker.poll() is None:
                worker.terminate()
            worker.wait(timeout=30)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--motion-id", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=8)
    parser.add_argument("--damping", type=float, default=2.0e-3)
    parser.add_argument("--maximum-step", type=float, default=0.20)
    parser.add_argument("--device", default="cuda:0")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
