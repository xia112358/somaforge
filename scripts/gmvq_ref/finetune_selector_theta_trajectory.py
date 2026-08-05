#!/usr/bin/env python3
"""Fine-tune a theta selector through the frozen GMVQ trajectory decoder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from gmvq.hyar_wrapper import FrozenGMVQCodec
from train_selector_theta import ThetaMLP, _build_features
from torch_g1_fk import CanonicalG1TorchFK


def _group_masks(groups: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    unique = np.asarray(sorted(set(str(item) for item in groups)))
    rng = np.random.default_rng(seed)
    rng.shuffle(unique)
    train_groups = set(unique[: int(round(0.8 * len(unique)))])
    group_strings = np.asarray([str(item) for item in groups])
    train = np.asarray([item in train_groups for item in group_strings])
    return train, ~train


def _keypoint_mse(
    predicted: torch.Tensor,
    target: torch.Tensor,
    frame_mask: torch.Tensor,
    body_weight: torch.Tensor,
) -> torch.Tensor:
    weighted = (
        (predicted - target).square()
        * frame_mask.unsqueeze(-1)
        * body_weight.unsqueeze(1).unsqueeze(-1)
    )
    count = (
        frame_mask.sum() * body_weight.sum(dim=-1).mean() * predicted.shape[-1]
    ).clamp_min(1.0)
    return weighted.sum() / count


@torch.no_grad()
def _evaluate(
    model: nn.Module,
    codec: FrozenGMVQCodec,
    fk: CanonicalG1TorchFK,
    x: torch.Tensor,
    codes: torch.Tensor,
    theta_mean: torch.Tensor,
    theta_std: torch.Tensor,
    segments: torch.Tensor,
    lengths: torch.Tensor,
    mask: torch.Tensor,
    row_mask: torch.Tensor,
    feature_weight: torch.Tensor,
    target_keypoints: torch.Tensor,
    keypoint_body_weight: torch.Tensor,
    keypoint_loss_weight: float,
    oracle_theta_norm: torch.Tensor | None = None,
) -> dict[str, float]:
    model.eval()
    indices = torch.nonzero(row_mask, as_tuple=False).flatten()
    trajectory_total = 0.0
    keypoint_total = 0.0
    sample_count = 0
    for chunk in indices.split(128):
        theta_norm = model(x[chunk]) if oracle_theta_norm is None else oracle_theta_norm[chunk]
        theta = theta_norm * theta_std + theta_mean
        decoded = codec.decode_hybrid(codes[chunk], theta, lengths=lengths[chunk])["x_hat"]
        valid = mask[chunk].unsqueeze(-1)
        sq = (decoded - segments[chunk]).square() * valid * feature_weight
        trajectory = sq.sum() / (valid.sum() * feature_weight.sum()).clamp_min(1.0)
        keypoint = _keypoint_mse(
            fk(codec.denormalize(decoded)[..., :36]),
            target_keypoints[chunk],
            valid,
            keypoint_body_weight[chunk],
        )
        count = int(chunk.numel())
        trajectory_total += float(trajectory.item()) * count
        keypoint_total += float(keypoint.item()) * count
        sample_count += count
    trajectory_mse = trajectory_total / max(sample_count, 1)
    keypoint_mse = keypoint_total / max(sample_count, 1)
    return {
        "trajectory_mse_norm": trajectory_mse,
        "keypoint_mse_m2": keypoint_mse,
        "objective": trajectory_mse + keypoint_loss_weight * keypoint_mse,
    }


def train(args: argparse.Namespace) -> dict[str, float | int | str]:
    device = torch.device(args.device)
    selector_ckpt = torch.load(args.selector_checkpoint, map_location="cpu", weights_only=False)
    cfg = selector_ckpt["model_config"]
    model = ThetaMLP(
        input_dim=cfg["input_dim"],
        theta_dim=cfg["theta_dim"],
        hidden_dim=cfg["hidden_dim"],
        depth=cfg["depth"],
        dropout=cfg["dropout"],
    ).to(device)
    model.load_state_dict(selector_ckpt["model_state"])

    with np.load(args.selector_dataset, allow_pickle=False) as selector_data:
        x_raw, _ = _build_features(
            selector_data,
            list(selector_ckpt["feature_groups"]),
            int(cfg["num_codes"]),
        )
        all_codes = np.asarray(selector_data["codes"], dtype=np.int64)
        non_stop_mask = all_codes < args.stop_code
        codes_np = all_codes[non_stop_mask]
        theta_np = np.asarray(selector_data["theta"], dtype=np.float32)[non_stop_mask]
        groups = np.asarray(selector_data["motion_ids"]).astype(str)[non_stop_mask]
        x_raw = x_raw[non_stop_mask]
        joint_names = (
            np.asarray(selector_data["joint_names"]).astype(str).tolist()
            if "joint_names" in selector_data.files
            else None
        )
    non_stop_count = int(len(codes_np))

    with np.load(args.segment_pack, allow_pickle=False) as pack:
        segments_np = np.asarray(pack["segments"], dtype=np.float32)
        lengths_np = np.asarray(pack["lengths"], dtype=np.int64)
        valid_np = np.asarray(pack["valid_mask"], dtype=bool)
        theta_segments_np = np.asarray(pack["theta_segments"], dtype=np.float32)
        semantic_names = np.asarray(pack["semantic_names"]).astype(str).tolist()
        active_bodies = np.asarray(pack["active_bodies"]).astype(str)
        pack_motion_ids = np.asarray(pack["motion_ids"]).astype(str)
        first_source_path = str(np.asarray(pack["source_paths"]).astype(str)[0])
    if joint_names is None:
        with np.load(first_source_path, allow_pickle=False) as source:
            joint_names = np.asarray(source["joint_names"]).astype(str).tolist()
    target_lookup: dict[tuple[str, int], int] = {}
    for motion_id in dict.fromkeys(pack_motion_ids.tolist()):
        pack_rows = np.flatnonzero(pack_motion_ids == motion_id)
        selector_rows = np.flatnonzero(groups == motion_id)
        if len(selector_rows) < len(pack_rows):
            raise ValueError(f"selector dataset has too few rows for {motion_id}")
        first_codes = codes_np[selector_rows[: len(pack_rows)]]
        if len(set(first_codes.tolist())) != len(pack_rows):
            raise ValueError(f"first selector pass has duplicate codes for {motion_id}")
        for pack_row, code in zip(pack_rows, first_codes, strict=True):
            target_lookup[(motion_id, int(code))] = int(pack_row)
    try:
        target_indices = np.asarray(
            [target_lookup[(motion_id, int(code))] for motion_id, code in zip(groups, codes_np)],
            dtype=np.int64,
        )
    except KeyError as exc:
        raise ValueError(f"selector row has no matching real augmented target: {exc.args[0]}") from exc
    segments_np = segments_np[target_indices]
    lengths_np = lengths_np[target_indices]
    valid_np = valid_np[target_indices]
    theta_segments_np = theta_segments_np[target_indices]
    active_bodies = active_bodies[target_indices]

    x_mean = np.asarray(selector_ckpt["x_norm"]["mean"], dtype=np.float32)
    x_std = np.asarray(selector_ckpt["x_norm"]["std"], dtype=np.float32)
    theta_mean_np = np.asarray(selector_ckpt["theta_norm"]["mean"], dtype=np.float32)
    theta_std_np = np.asarray(selector_ckpt["theta_norm"]["std"], dtype=np.float32)
    x_np = ((x_raw - x_mean) / x_std).astype(np.float32)
    theta_norm_np = ((theta_np - theta_mean_np) / theta_std_np).astype(np.float32)

    codec = FrozenGMVQCodec(
        args.gmvq_checkpoint,
        device=device,
        trainable=args.train_decoder,
    )
    for parameter in codec.model.parameters():
        parameter.requires_grad_(False)
    decoder_parameters: list[torch.nn.Parameter] = []
    if args.train_decoder:
        for parameter in codec.model.decoder.parameters():
            parameter.requires_grad_(True)
            decoder_parameters.append(parameter)
        if codec.model.local_theta_basis is not None:
            codec.model.local_theta_basis.requires_grad_(True)
            decoder_parameters.append(codec.model.local_theta_basis)
    if args.oracle_theta and not decoder_parameters:
        raise ValueError("--oracle-theta requires --train-decoder")
    segments = codec.normalize(torch.from_numpy(segments_np).to(device))
    if theta_segments_np.shape[:2] != segments_np.shape[:2]:
        raise ValueError("theta_segments must share [N,T] with segments")
    position_dim = 3 * len(semantic_names)
    target_keypoints = torch.from_numpy(
        theta_segments_np[..., :position_dim].reshape(
            theta_segments_np.shape[0],
            theta_segments_np.shape[1],
            len(semantic_names),
            3,
        )
    ).to(device)
    fk = CanonicalG1TorchFK(joint_names=joint_names, link_names=semantic_names).to(device)
    keypoint_body_weight_np = np.ones(
        (len(active_bodies), len(semantic_names)), dtype=np.float32
    )
    active_aliases = {
        "left_foot": "left_ankle_roll_link",
        "right_foot": "right_ankle_roll_link",
        "left_hand": "left_wrist_yaw_link",
        "right_hand": "right_wrist_yaw_link",
        "left_knee": "left_knee_link",
        "right_knee": "right_knee_link",
    }
    semantic_index = {name: index for index, name in enumerate(semantic_names)}
    for row, raw in enumerate(active_bodies):
        for active in json.loads(str(raw)):
            semantic = active_aliases.get(str(active))
            if semantic in semantic_index:
                keypoint_body_weight_np[row, semantic_index[semantic]] = (
                    args.active_keypoint_multiplier
                )
    keypoint_body_weight = torch.from_numpy(keypoint_body_weight_np).to(device)
    x = torch.from_numpy(x_np).to(device)
    codes = torch.from_numpy(codes_np).to(device)
    theta_target = torch.from_numpy(theta_norm_np).to(device)
    lengths = torch.from_numpy(lengths_np).to(device)
    valid = torch.from_numpy(valid_np).to(device)
    theta_mean = torch.from_numpy(theta_mean_np).to(device)
    theta_std = torch.from_numpy(theta_std_np).to(device)
    train_mask_np, eval_mask_np = _group_masks(groups, args.seed)
    train_indices = torch.from_numpy(np.flatnonzero(train_mask_np)).to(device)
    train_mask = torch.from_numpy(train_mask_np).to(device)
    eval_mask = torch.from_numpy(eval_mask_np).to(device)
    feature_weight = torch.ones(segments.shape[-1], dtype=torch.float32, device=device)
    feature_weight[: min(36, segments.shape[-1])] = args.qpos_loss_weight

    before_train = _evaluate(
        model, codec, fk, x, codes, theta_mean, theta_std, segments, lengths, valid, train_mask,
        feature_weight, target_keypoints, keypoint_body_weight, args.keypoint_loss_weight,
        theta_target if args.oracle_theta else None,
    )
    before_eval = _evaluate(
        model, codec, fk, x, codes, theta_mean, theta_std, segments, lengths, valid, eval_mask,
        feature_weight, target_keypoints, keypoint_body_weight, args.keypoint_loss_weight,
        theta_target if args.oracle_theta else None,
    )

    selector_parameters = [] if args.oracle_theta else list(model.parameters())
    optimizer = torch.optim.AdamW(
        selector_parameters + decoder_parameters,
        lr=args.lr,
        weight_decay=args.weight_decay,
    )
    theta_loss_fn = nn.SmoothL1Loss(beta=0.5)
    best_eval = before_eval["objective"]
    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    best_codec_state = {
        key: value.detach().cpu().clone() for key, value in codec.model.state_dict().items()
    }
    rng = torch.Generator(device=device).manual_seed(args.seed)

    for step in range(1, args.steps + 1):
        permutation = train_indices[torch.randperm(train_indices.numel(), generator=rng, device=device)]
        model.train(not args.oracle_theta)
        for batch in permutation.split(args.batch_size):
            theta_norm = theta_target[batch] if args.oracle_theta else model(x[batch])
            theta = theta_norm * theta_std + theta_mean
            decoded = codec.decode_hybrid(codes[batch], theta, lengths=lengths[batch])["x_hat"]
            frame_mask = valid[batch].unsqueeze(-1)
            trajectory_loss = (
                (decoded - segments[batch]).square()
                * frame_mask
                * feature_weight
            ).sum()
            trajectory_loss = trajectory_loss / (
                frame_mask.sum() * feature_weight.sum()
            ).clamp_min(1)
            keypoint_loss = _keypoint_mse(
                fk(codec.denormalize(decoded)[..., :36]),
                target_keypoints[batch],
                frame_mask,
                keypoint_body_weight[batch],
            )
            theta_loss = (
                torch.zeros((), device=device)
                if args.oracle_theta
                else theta_loss_fn(theta_norm, theta_target[batch])
            )
            loss = (
                trajectory_loss
                + args.keypoint_loss_weight * keypoint_loss
                + args.theta_loss_weight * theta_loss
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(selector_parameters + decoder_parameters, 1.0)
            optimizer.step()

        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            eval_metrics = _evaluate(
                model, codec, fk, x, codes, theta_mean, theta_std, segments, lengths, valid,
                eval_mask, feature_weight, target_keypoints, keypoint_body_weight,
                args.keypoint_loss_weight,
                theta_target if args.oracle_theta else None,
            )
            print(
                f"step={step} trajectory_eval_mse_norm="
                f"{eval_metrics['trajectory_mse_norm']:.7f} "
                f"keypoint_eval_rmse_m={eval_metrics['keypoint_mse_m2'] ** 0.5:.6f}",
                flush=True,
            )
            if eval_metrics["objective"] < best_eval:
                best_eval = eval_metrics["objective"]
                best_state = {
                    key: value.detach().cpu().clone() for key, value in model.state_dict().items()
                }
                best_codec_state = {
                    key: value.detach().cpu().clone()
                    for key, value in codec.model.state_dict().items()
                }

    model.load_state_dict(best_state)
    codec.model.load_state_dict(best_codec_state)
    after_train = _evaluate(
        model, codec, fk, x, codes, theta_mean, theta_std, segments, lengths, valid, train_mask,
        feature_weight, target_keypoints, keypoint_body_weight, args.keypoint_loss_weight,
        theta_target if args.oracle_theta else None,
    )
    after_eval = _evaluate(
        model, codec, fk, x, codes, theta_mean, theta_std, segments, lengths, valid, eval_mask,
        feature_weight, target_keypoints, keypoint_body_weight, args.keypoint_loss_weight,
        theta_target if args.oracle_theta else None,
    )

    output = args.output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    selector_ckpt["model_state"] = model.state_dict()
    selector_ckpt["trajectory_finetune"] = {
        "schema": "gmvq_theta_selector_trajectory_finetune_v1",
        "gmvq_checkpoint": str(args.gmvq_checkpoint),
        "segment_pack": str(args.segment_pack),
        "steps": args.steps,
        "theta_loss_weight": args.theta_loss_weight,
        "keypoint_loss_weight": args.keypoint_loss_weight,
        "active_keypoint_multiplier": args.active_keypoint_multiplier,
        "oracle_theta": args.oracle_theta,
        "before_train": before_train,
        "before_eval": before_eval,
        "after_train": after_train,
        "after_eval": after_eval,
    }
    torch.save(selector_ckpt, output)
    if args.output_gmvq is not None:
        gmvq_payload = torch.load(args.gmvq_checkpoint, map_location="cpu", weights_only=False)
        gmvq_payload["model_state"] = codec.model.state_dict()
        gmvq_payload["observation_conditioned_finetune"] = {
            "selector_checkpoint": str(output),
            "qpos_loss_weight": args.qpos_loss_weight,
            "keypoint_loss_weight": args.keypoint_loss_weight,
            "trajectory_eval_mse_norm": after_eval["trajectory_mse_norm"],
            "keypoint_eval_mse_m2": after_eval["keypoint_mse_m2"],
        }
        args.output_gmvq.parent.mkdir(parents=True, exist_ok=True)
        torch.save(gmvq_payload, args.output_gmvq)
    summary = {
        "output": str(output),
        "steps": args.steps,
        "train_count": int(train_mask_np.sum()),
        "eval_count": int(eval_mask_np.sum()),
        "before_train": before_train,
        "before_eval": before_eval,
        "after_train": after_train,
        "after_eval": after_eval,
        "output_gmvq": "" if args.output_gmvq is None else str(args.output_gmvq),
    }
    output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-checkpoint", type=Path, required=True)
    parser.add_argument("--selector-dataset", type=Path, required=True)
    parser.add_argument("--segment-pack", type=Path, required=True)
    parser.add_argument("--gmvq-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-gmvq", type=Path)
    parser.add_argument("--stop-code", type=int, default=13)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1.0e-4)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--theta-loss-weight", type=float, default=0.05)
    parser.add_argument("--qpos-loss-weight", type=float, default=4.0)
    parser.add_argument("--keypoint-loss-weight", type=float, default=20.0)
    parser.add_argument("--active-keypoint-multiplier", type=float, default=4.0)
    parser.add_argument("--train-decoder", action="store_true")
    parser.add_argument(
        "--oracle-theta",
        action="store_true",
        help="Freeze the selector and train the decoder from dataset code/theta labels.",
    )
    parser.add_argument("--eval-every", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260731)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
