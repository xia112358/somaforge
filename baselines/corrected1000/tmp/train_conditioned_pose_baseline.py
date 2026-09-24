#!/usr/bin/env python3
"""Stage-A no-binding pose-only baseline with one explicit contact plan."""

from __future__ import annotations

import argparse
import atexit
import copy
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import torch
import tyro
from isaaclab.app import AppLauncher


ROOT = Path.cwd().resolve()
if not (ROOT / "packages/climb00_pipeline/climb00_pipeline").is_dir():
    ROOT = Path(__file__).resolve().parents[1]
for package in (ROOT / "packages/climb00_pipeline", ROOT / "packages/somaforge_core", ROOT / "tmp"):
    sys.path.insert(0, str(package))

from climb00_pipeline.conditioned_pose_predictor import (
    ConditionedHeightmapPosePredictor,
    conditioned_pose_objective,
)
from climb00_pipeline.heightmap_contact_projector import observed_surface_indices
from climb00_pipeline.neural_infiller import _matrix_from_rotation6d
from climb00_pipeline.next_interaction_heightmap_v2 import render_root_yaw_box_heightmaps
from somaforge_core.robot_assets import encode_robot_asset_json
from train_climb00_contact_event_predictor import split_name
from train_climb00_scan_action_q_deformer import box_obbs


DATA_CACHE = ROOT / "tmp/predictor_preprocessing_cache/e68ff83005af2c7858a8472454893239f44db5034a3245ed0f1f07cc58cf9d45.pt"


@dataclass
class Config:
    manifest: Path = ROOT / "tmp/temporal207_training_v2_ready/manifest.json"
    q_cache: Path = ROOT / "tmp/temporal207_training_v2_ready/q_cache.npz"
    data_cache: Path = DATA_CACHE
    output: Path = ROOT / "tmp/conditioned_pose_stage_a"
    mode: str = "overfit"
    steps: int = 500
    width: int = 192
    layers: int = 3
    batch_size: int = 64
    learning_rate: float = 3.0e-4
    evaluation_every: int = 25
    seed: int = 20260917
    encoder_warm_start: Path | None = ROOT / "tmp/predictor_heightmap_v4_bound_warmstart.pt"
    model_warm_start: Path | None = None
    overfit_motion_id: int | None = None
    heightmap_supersample: int = 1


def take(values: dict[str, torch.Tensor], indices: torch.Tensor) -> dict[str, torch.Tensor]:
    return {key: value[indices] for key, value in values.items()}


def prepare(model: ConditionedHeightmapPosePredictor, cfg: Config, device: torch.device):
    payload = torch.load(cfg.data_cache, map_location="cpu", weights_only=False)
    data, samples = payload["data"], payload["samples"]
    with np.load(cfg.q_cache, allow_pickle=False) as cache:
        q = np.asarray(cache["target_q"][:, (0, -1)], dtype=np.float32)
    center, rotation, half, ground = box_obbs(data)
    heightmap = render_root_yaw_box_heightmaps(
        center, rotation, half, ground, q[:, 0],
        supersample=cfg.heightmap_supersample,
    )
    tensor = lambda value, **kwargs: torch.as_tensor(value, device=device, **kwargs)
    current_contact = tensor(data["start_contacts"]).bool()
    current_surface = observed_surface_indices(
        heightmap,
        q[:, 0],
        np.asarray(data["start_contacts"], dtype=bool),
        np.asarray(data["current_contacts"], dtype=np.float32),
    )
    planned_contact = tensor(data["end_contact"]).bool()
    planned_surface = tensor(data["target_surfaces"], dtype=torch.long)
    inputs = {
        "current_q": tensor(q[:, 0]),
        "current_contact": current_contact,
        "current_anchor": tensor(data["current_contacts"]),
        "current_surface": tensor(current_surface, dtype=torch.long),
        "heightmap": tensor(heightmap),
        "planned_contact": planned_contact,
        "planned_surface": planned_surface,
    }
    target_q = tensor(q[:, 1])
    with torch.no_grad():
        body_position, body_rotation6d = model.fk(target_q[:, None])
        body_position = body_position[:, 0]
        body_rotation = _matrix_from_rotation6d(body_rotation6d[:, 0])
        material_local = torch.einsum(
            "bpji,bpj->bpi",
            body_rotation[:, 1:7],
            tensor(data["target_contacts"]) - body_position[:, 1:7],
        )
    target = {
        "current_q": inputs["current_q"],
        "q": target_q,
        "body_position": body_position,
        "material_local": material_local,
        "anchor": tensor(data["target_contacts"]),
        "planned_contact": planned_contact,
        "planned_surface": planned_surface,
        "current_contact": current_contact,
        "current_anchor": tensor(data["current_contacts"]),
        "current_surface": tensor(current_surface, dtype=torch.long),
    }
    from types import SimpleNamespace
    from climb00_pipeline.newton_query_supervision import prepare_query_metadata
    prepare_query_metadata(
        cfg.manifest,
        inputs,
        target,
        [SimpleNamespace(**sample) for sample in samples],
    )
    scene = {
        "box_center": tensor(center),
        "box_rotation": tensor(rotation),
        "box_half_extents": tensor(half),
        "ground_height": tensor(ground),
    }
    split = {
        name: torch.tensor([
            index for index, sample in enumerate(samples)
            if split_name(float(sample["height"])).startswith(name)
        ], device=device)
        for name in ("train", "validation", "test")
    }
    if any(len(indices) == 0 for indices in split.values()):
        raise ValueError("empty train/validation/test split")
    if cfg.mode == "overfit":
        motion_id = cfg.overfit_motion_id
        if motion_id is None:
            motion_id = int(samples[int(split["train"][0])]["motion_id"])
        overfit = [
            int(index) for index in split["train"].cpu().tolist()
            if int(samples[index]["motion_id"]) == motion_id
        ]
        if not overfit:
            raise ValueError(f"overfit motion {motion_id} is not in the training split")
        split["overfit"] = torch.tensor(overfit, device=device)
    summary = {
        "schema": "conditioned_pose_stage_a_dataset_v1",
        "samples": len(samples),
        "splits": {key: len(value) for key, value in split.items()},
        "condition_contract": "decoder consumes one explicit topology+surface plan",
        "pose_input": "current q + actual contact/anchor + heightmap-derived surface index + 2cm root-yaw heightmap + explicit plan",
        "excluded": ["binding", "predicted topology features", "event index", "future pose"],
        "training": "pose-only; no topology classification objective",
        "failure_states_used_for_training": False,
        "realization_contract": (
            "every supplied limb+surface plan is optimized against fresh Newton "
            "activation/allocation/margin witnesses"
        ),
        "geometric_distance_fallback": False,
        "projector_required_for_hard_guarantee": True,
    }
    return inputs, target, scene, split, samples, summary


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    AppLauncher.add_app_launcher_args(parser)
    official, remaining = parser.parse_known_args()
    cfg = tyro.cli(Config, args=remaining)
    if official.visualizer is not None or official.enable_cameras:
        raise ValueError("conditioned pose training is headless")
    if cfg.mode not in {"overfit", "full"}:
        raise ValueError("mode must be overfit or full")
    if cfg.output.exists():
        raise FileExistsError(f"refusing to overwrite {cfg.output}")
    cfg.output.mkdir(parents=True)
    torch.set_num_threads(2)
    torch.manual_seed(cfg.seed)
    device = torch.device("cpu" if official.cpu else official.device)
    model = ConditionedHeightmapPosePredictor(cfg.width, cfg.layers).to(device)
    warm_start_report = None
    if cfg.encoder_warm_start is not None:
        checkpoint = torch.load(cfg.encoder_warm_start, map_location=device, weights_only=False)
        if checkpoint["config"].get("architecture") not in {
            "heightmap_v3", "heightmap_v3_coupled", "heightmap_v3_robust"
        }:
            raise ValueError("encoder warm start must be a dense V3 checkpoint")
        if str(checkpoint["robot_asset_json"]) != str(encode_robot_asset_json()):
            raise ValueError("encoder warm-start robot asset mismatch")
        loaded, missing = model.load_observation_encoder(checkpoint["model"])
        warm_start_report = {
            "checkpoint": str(cfg.encoder_warm_start.resolve()),
            "source_architecture": checkpoint["config"]["architecture"],
            "source_step": int(checkpoint["step"]),
            "loaded_keys": loaded,
            "fresh_keys": missing,
            "fusion_decoder_reinitialized": True,
        }
    if cfg.model_warm_start is not None:
        checkpoint = torch.load(cfg.model_warm_start, map_location=device, weights_only=False)
        if str(checkpoint["robot_asset_json"]) != str(encode_robot_asset_json()):
            raise ValueError("model warm-start robot asset mismatch")
        model.load_state_dict(checkpoint["model"], strict=True)
        warm_start_report = {
            "checkpoint": str(cfg.model_warm_start.resolve()),
            "source_schema": checkpoint.get("schema"),
            "source_step": int(checkpoint["step"]),
            "loaded": "complete conditioned pose model",
            "objective_changed": "fresh Newton own-plan realization",
        }
    inputs, target, scene, split, samples, dataset_summary = prepare(model, cfg, device)
    train = split["overfit"] if cfg.mode == "overfit" else split["train"]
    validation = train if cfg.mode == "overfit" else split["validation"]
    from train_first_touch_geometry import Workers
    import somaforge_core.newton_scene_router as router
    queried = torch.unique(torch.cat((train, validation))).cpu().tolist()
    heights = sorted({round(float(samples[index]["height"]), 8) for index in queried})
    workers = Workers(cfg.output / "newton_workers", heights, str(device)).__enter__()
    atexit.register(workers.__exit__, None, None, None)
    router.configured_router = lambda: workers.router
    for index in queried:
        height = min(heights, key=lambda value: abs(value - float(samples[index]["height"])))
        target["newton_model_fingerprint"][index] = torch.tensor(
            list(bytes.fromhex(workers.entries[height]["fp"])),
            dtype=torch.uint8,
            device=device,
        )
    with torch.no_grad():
        model.pose_head.bias[7:].copy_(target["q"][train, 7:].mean(0))
        encoded = model.encode_pose(target["q"], inputs["current_q"])
        decoded = model.decode_pose(encoded, inputs["current_q"])
        torch.testing.assert_close(decoded, target["q"], rtol=1.0e-5, atol=1.0e-6)
    config = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in asdict(cfg).items()
    }
    (cfg.output / "config.json").write_text(json.dumps(config, indent=2))
    (cfg.output / "dataset.json").write_text(json.dumps(dataset_summary, indent=2))
    if warm_start_report is not None:
        (cfg.output / "warm_start.json").write_text(json.dumps(warm_start_report, indent=2))

    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.learning_rate, weight_decay=1.0e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, cfg.steps, eta_min=cfg.learning_rate * 0.1
    )

    def predict(indices: torch.Tensor):
        batch = take(inputs, indices)
        return model(**batch)

    @torch.no_grad()
    def evaluate(indices: torch.Tensor) -> dict:
        model.eval()
        totals: dict[str, float] = {}
        maxima: dict[str, float] = {}
        count = 0
        for batch_indices in indices.split(cfg.batch_size):
            _, metrics = conditioned_pose_objective(
                model, predict(batch_indices), take(target, batch_indices), take(scene, batch_indices)
            )
            for key, value in metrics.items():
                totals[key] = totals.get(key, 0.0) + float(value.sum())
                maxima[key] = max(maxima.get(key, -math.inf), float(value.max()))
            count += len(batch_indices)
        model.train()
        return {**{key: value / count for key, value in totals.items()}, "maxima": maxima}

    best_score = math.inf
    best_step = 0
    best_state = None
    history = []
    started = time.perf_counter()
    for step in range(1, cfg.steps + 1):
        shuffled = train[torch.randperm(len(train), device=device)]
        total = 0.0
        model.train()
        for batch_indices in shuffled.split(
            len(shuffled) if cfg.mode == "overfit" else cfg.batch_size
        ):
            optimizer.zero_grad(set_to_none=True)
            prediction = predict(batch_indices)
            loss, _ = conditioned_pose_objective(
                model, prediction, take(target, batch_indices), take(scene, batch_indices)
            )
            loss.mean().backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0, error_if_nonfinite=True)
            optimizer.step()
            total += float(loss.detach().sum())
        scheduler.step()
        if step == 1 or step % cfg.evaluation_every == 0 or step == cfg.steps:
            metrics = evaluate(validation)
            score = (
                40.0 * (1.0 - metrics["newton_generation_valid"])
                + 5.0 * metrics["newton_unrealized_intended_contacts"]
                + metrics["root_cm"] + metrics["body_cm"]
                + 10.0 * metrics["joint_rmse_rad"]
                + metrics["penetration_cm"]
                + metrics["maxima"]["penetration_cm"]
            )
            row = {
                "step": step,
                "train_loss": total / len(train),
                "validation_score": score,
                "metrics": metrics,
                "elapsed_seconds": time.perf_counter() - started,
            }
            history.append(row)
            print(json.dumps(row), flush=True)
            if score < best_score:
                best_score, best_step = score, step
                best_state = copy.deepcopy(model.state_dict())
    if best_state is None:
        raise RuntimeError("training produced no checkpoint")
    model.load_state_dict(best_state)
    final_metrics = evaluate(validation)
    first_metrics = history[0]["metrics"]
    overfit_gate = None
    if cfg.mode == "overfit":
        overfit_gate = {
            "best_after_step_1": best_step > 1,
            "root_improved_4x": final_metrics["root_cm"] <= first_metrics["root_cm"] / 4.0,
            "body_improved_4x": final_metrics["body_cm"] <= first_metrics["body_cm"] / 4.0,
            "joint_improved_4x": final_metrics["joint_rmse_rad"] <= first_metrics["joint_rmse_rad"] / 4.0,
            "realization_improved_4x": (
                final_metrics["own_plan_realization_loss"]
                <= first_metrics["own_plan_realization_loss"] / 4.0
            ),
            "newton_generation_valid_95pct": final_metrics["newton_generation_valid"] >= 0.95,
        }
        overfit_gate["passed"] = all(overfit_gate.values())
    checkpoint = {
        "schema": "conditioned_pose_stage_a_v1",
        "model": best_state,
        "step": best_step,
        "metrics": final_metrics,
        "config": config,
        "dataset": dataset_summary,
        "condition_contract": {
            "planned_contact": "explicit bool [B,6]",
            "planned_surface": "explicit ground/top IDs [B,6]",
            "own_plan_realization": "unconditional fresh Newton activation/allocation constraint",
            "projector_required_for_hard_guarantee": True,
            "binding": False,
            "topology_head": False,
        },
        "robot_asset_json": encode_robot_asset_json(),
    }
    torch.save(checkpoint, cfg.output / "best.pt")
    report = {
        "schema": "conditioned_pose_stage_a_training_report_v1",
        "mode": cfg.mode,
        "best_step": best_step,
        "best_score": best_score,
        "metrics": final_metrics,
        "overfit_gate": overfit_gate,
        "history": history,
        "warm_start": warm_start_report,
    }
    (cfg.output / "report.json").write_text(json.dumps(report, indent=2))
    completion = {**report, "complete": True, "history": f"{len(history)} records"}
    print(json.dumps(completion, default=str), flush=True)


if __name__ == "__main__":
    main()
