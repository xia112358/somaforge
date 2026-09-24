from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np

from somaforge_core.robot_assets import decode_robot_asset_json, encode_robot_asset_json


ROOT = Path(__file__).absolute().parents[1]
DEFAULT_MANIFEST = ROOT / "runtime/current/manifests/newton_contact_force_8part.json"
DEFAULT_OUTPUT = ROOT / "tmp/g1_complete_limb_actions_newton_v3"

PART_NAMES = (
    "left_foot",
    "right_foot",
    "left_hand",
    "right_hand",
    "left_knee",
    "right_knee",
)
CHAIN_NAMES = ("left_hand", "right_hand", "left_leg", "right_leg")
CHAIN_PART_INDICES = ((2,), (3,), (0, 4), (1, 5))
CHAIN_BODY_NAMES = (
    "left_wrist_yaw_link",
    "right_wrist_yaw_link",
    "left_ankle_roll_link",
    "right_ankle_roll_link",
)


@dataclass(frozen=True)
class LimbAction:
    chain: int
    start_frame: int
    liftoff_frame: int | None
    touchdown_frame: int
    touchdown_parts: tuple[str, ...]
    start_observed: bool
    start_kind: str
    reach_onset_frame: int | None = None
    contact_interval_start_frame: int | None = None


def debounce_binary_states(states: np.ndarray, minimum_stable_frames: int) -> np.ndarray:
    values = np.asarray(states, dtype=np.bool_)
    if values.ndim != 2:
        raise ValueError("contact states must have shape [frames, channels]")
    if minimum_stable_frames <= 0:
        raise ValueError("minimum stable contact frames must be positive")
    if len(values) < 2 or minimum_stable_frames == 1:
        return values.copy()
    filtered = np.empty_like(values)
    for channel in range(values.shape[1]):
        source = values[:, channel]
        current = bool(source[0])
        filtered[0, channel] = current
        candidate_start: int | None = None
        for frame in range(1, len(source)):
            value = bool(source[frame])
            if value == current:
                if candidate_start is not None:
                    filtered[candidate_start:frame, channel] = current
                    candidate_start = None
                filtered[frame, channel] = current
                continue
            if candidate_start is None:
                candidate_start = frame
            filtered[frame, channel] = current
            if frame - candidate_start + 1 >= minimum_stable_frames:
                filtered[candidate_start : frame + 1, channel] = value
                current = value
                candidate_start = None
        if candidate_start is not None:
            filtered[candidate_start:, channel] = current
    return filtered


def robust_contact_states(
    contacts: np.ndarray, minimum_stable_frames: int
) -> tuple[np.ndarray, np.ndarray]:
    raw_parts = np.asarray(contacts, dtype=np.bool_)
    body_states = debounce_binary_states(raw_parts, minimum_stable_frames)
    # As in PARC: union foot/knee before debouncing the leg chain, so endpoint
    # handover does not create a false leg flight interval.
    raw_chains = np.stack(
        [np.any(raw_parts[:, indices], axis=1) for indices in CHAIN_PART_INDICES], axis=1
    )
    chain_states = debounce_binary_states(raw_chains, minimum_stable_frames)
    return body_states, chain_states


def touchdown_parts(
    raw_contacts: np.ndarray,
    chain: int,
    frame: int,
    *,
    window: int,
) -> tuple[str, ...]:
    indices = CHAIN_PART_INDICES[chain]
    sample = raw_contacts[frame : min(len(raw_contacts), frame + window), indices]
    strength = sample.mean(axis=0) if len(sample) else np.zeros(len(indices))
    active = [indices[index] for index in np.flatnonzero(strength > 0.5)]
    if not active and len(strength) and float(strength.max()) > 0.0:
        active = [indices[int(np.argmax(strength))]]
    return tuple(PART_NAMES[index] for index in active)


def extract_limb_actions(
    raw_contacts: np.ndarray,
    chain_states: np.ndarray,
    *,
    endpoint_window_frames: int,
) -> list[LimbAction]:
    open_liftoff: list[int | None] = [None] * len(CHAIN_NAMES)
    censored_open = [not bool(chain_states[0, chain]) for chain in range(len(CHAIN_NAMES))]
    actions: list[LimbAction] = []
    for frame in range(1, len(chain_states)):
        lifted = chain_states[frame - 1] & (~chain_states[frame])
        for chain_value in np.flatnonzero(lifted):
            chain = int(chain_value)
            open_liftoff[chain] = frame
            censored_open[chain] = False
        landed = (~chain_states[frame - 1]) & chain_states[frame]
        for chain_value in np.flatnonzero(landed):
            chain = int(chain_value)
            liftoff = open_liftoff[chain]
            censored = liftoff is None and censored_open[chain]
            if liftoff is None and not censored:
                continue
            start = 0 if censored else max(0, int(liftoff) - 1)
            actions.append(
                LimbAction(
                    chain=chain,
                    start_frame=start,
                    liftoff_frame=None if censored else int(liftoff),
                    touchdown_frame=frame,
                    touchdown_parts=touchdown_parts(
                        raw_contacts, chain, frame, window=endpoint_window_frames
                    ),
                    start_observed=not censored,
                    start_kind="clip_censored" if censored else "contact_liftoff",
                    contact_interval_start_frame=start,
                )
            )
            open_liftoff[chain] = None
            censored_open[chain] = False
    return actions


def refine_hand_reach(
    action: LimbAction,
    body_positions: np.ndarray,
    body_names: list[str],
    chain_states: np.ndarray,
    *,
    capture_radius_m: float,
    support_event_snap_frames: int,
) -> LimbAction:
    if action.chain not in (0, 1):
        return action
    body_index = body_names.index(CHAIN_BODY_NAMES[action.chain])
    old_start, end = action.start_frame, action.touchdown_frame
    target = body_positions[end, body_index]
    distance = np.linalg.norm(body_positions[old_start : end + 1, body_index] - target, axis=1)
    outside = np.flatnonzero(distance[:-1] > capture_radius_m)
    if not len(outside):
        return replace(
            action,
            start_observed=False,
            start_kind="reach_entry_censored",
            reach_onset_frame=None,
            contact_interval_start_frame=old_start,
        )
    onset = old_start + int(outside[-1]) + 1
    other_support = np.delete(chain_states, action.chain, axis=1)
    changes = np.flatnonzero(np.any(other_support[1:] != other_support[:-1], axis=1)) + 1
    nearby = changes[
        (changes <= onset)
        & (changes >= max(old_start, onset - support_event_snap_frames))
    ]
    snapped = int(nearby[-1]) if len(nearby) else onset
    return replace(
        action,
        start_frame=snapped,
        start_observed=True,
        start_kind=(
            "goal_capture_entry"
            if snapped == onset
            else "goal_capture_entry_snapped_to_support_event"
        ),
        reach_onset_frame=onset,
        contact_interval_start_frame=old_start,
    )


def group_actions(actions: list[LimbAction], merge_gap_frames: int) -> list[list[LimbAction]]:
    groups: list[list[LimbAction]] = []
    for action in sorted(actions, key=lambda item: (item.touchdown_frame, item.start_frame, item.chain)):
        previous = groups[-1] if groups else []
        previous_chains = {item.chain for item in previous}
        intervals_overlap = bool(previous) and max(
            min(item.start_frame for item in previous), action.start_frame
        ) < min(
            max(item.touchdown_frame for item in previous), action.touchdown_frame
        )
        if (
            previous
            and action.touchdown_frame - previous[-1].touchdown_frame < merge_gap_frames
            and action.chain not in previous_chains
            and intervals_overlap
        ):
            previous.append(action)
        else:
            groups.append([action])
    return groups


def support_names(body_states: np.ndarray, frame: int) -> list[str]:
    return [PART_NAMES[index] for index in np.flatnonzero(body_states[frame]).tolist()]


def quantiles(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "p05": None,
            "median": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    array = np.asarray(values, dtype=np.int64)
    return {
        "count": len(values),
        "min": int(array.min()),
        "p05": float(np.quantile(array, 0.05)),
        "median": float(np.median(array)),
        "p95": float(np.quantile(array, 0.95)),
        "p99": float(np.quantile(array, 0.99)),
        "max": int(array.max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--contact-min-stable-frames", type=int, default=5)
    parser.add_argument("--touchdown-merge-gap-frames", type=int, default=5)
    parser.add_argument("--endpoint-window-frames", type=int, default=5)
    parser.add_argument("--hand-capture-radius-m", type=float, default=0.2)
    parser.add_argument("--hand-support-event-snap-frames", type=int, default=10)
    parser.add_argument("--maximum-observed-frames", type=int, default=120)
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    motion_reports = []
    observed_lengths: list[int] = []
    eligible_lengths: list[int] = []
    censored_lengths: list[int] = []
    excluded_long_actions: list[dict[str, object]] = []
    robot_asset_json: str | None = None
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest_root = args.manifest.parent
    entries = sorted(
        (item for item in manifest["motion_files"] if int(item["motion_id"]) < 28),
        key=lambda item: int(item["motion_id"]),
    )
    fps_values = []
    for entry in entries:
        motion_index = int(entry["motion_id"])
        motion_id = f"climb_{motion_index:02d}"
        contact_path = (manifest_root / str(entry["motion_file"])).resolve()
        motion_path = (manifest_root / str(entry["reference_motion_file"])).resolve()
        with np.load(contact_path, allow_pickle=False) as data:
            order = np.asarray(data["contact_force_part_order"]).astype(str).tolist()
            raw_force = np.asarray(data["contact_force_part_mask"], dtype=np.bool_)
            raw_contacts = np.stack(
                (
                    raw_force[:, order.index("LHEE")] | raw_force[:, order.index("LTOE")],
                    raw_force[:, order.index("RHEE")] | raw_force[:, order.index("RTOE")],
                    raw_force[:, order.index("LH")],
                    raw_force[:, order.index("RH")],
                    raw_force[:, order.index("LK")],
                    raw_force[:, order.index("RK")],
                ),
                axis=1,
            )
        with np.load(motion_path, allow_pickle=False) as data:
            decoded = decode_robot_asset_json(data["robot_asset_json"], context=str(motion_path))
            if not str(decoded["urdf_path"]).endswith(
                "src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.urdf"
            ):
                raise ValueError(f"{motion_path}: non-canonical G1 asset")
            current_asset = str(np.asarray(data["robot_asset_json"]).item())
            if robot_asset_json is None:
                robot_asset_json = current_asset
            elif json.loads(robot_asset_json)["asset_bundle_sha256"] != json.loads(current_asset)[
                "asset_bundle_sha256"
            ]:
                raise ValueError(f"{motion_path}: robot asset bundle mismatch")
            body_positions = np.asarray(data["body_pos_w"], dtype=np.float32)
            body_names = np.asarray(data["body_names"]).astype(str).tolist()
            fps_values.append(float(np.asarray(data["fps"]).item()))
        if len(raw_contacts) != len(body_positions):
            raise ValueError(f"{motion_id}: contact/motion frame mismatch")

        body_states, chain_states = robust_contact_states(
            raw_contacts, args.contact_min_stable_frames
        )
        actions = extract_limb_actions(
            raw_contacts,
            chain_states,
            endpoint_window_frames=args.endpoint_window_frames,
        )
        actions = [
            refine_hand_reach(
                action,
                body_positions,
                body_names,
                chain_states,
                capture_radius_m=args.hand_capture_radius_m,
                support_event_snap_frames=args.hand_support_event_snap_frames,
            )
            for action in actions
        ]
        groups = group_actions(actions, args.touchdown_merge_gap_frames)
        local_records = []
        for local_index, group in enumerate(groups):
            start = min(action.start_frame for action in group)
            end = max(action.touchdown_frame for action in group)
            observed = all(action.start_observed for action in group)
            length = end - start + 1
            (observed_lengths if observed else censored_lengths).append(length)
            record = {
                "segment_id": f"{motion_id}_complete_limb_action_{local_index:04d}",
                "motion_id": motion_id,
                "source_path": str(motion_path),
                "contact_source_path": str(contact_path),
                "track": "complete_limb_action",
                "start_frame": int(start),
                "end_frame": int(end),
                "duration_frames": int(end - start),
                "source_support": support_names(body_states, start),
                "target_support": support_names(body_states, end),
                "touchdown_at_start": [],
                "touchdown_at_end": sorted(
                    {part for action in group for part in action.touchdown_parts}
                ),
                "active_chains": [CHAIN_NAMES[action.chain] for action in group],
                "start_observed": bool(observed),
                "start_kinds": [action.start_kind for action in group],
                "liftoff_frames": [action.liftoff_frame for action in group],
                "touchdown_frames": [action.touchdown_frame for action in group],
                "reach_onset_frames": [action.reach_onset_frame for action in group],
                "contact_interval_start_frames": [
                    action.contact_interval_start_frame for action in group
                ],
                "actions": [asdict(action) for action in group],
            }
            local_records.append(record)
            if observed:
                if args.maximum_observed_frames <= 0 or length <= args.maximum_observed_frames:
                    records.append(record)
                    eligible_lengths.append(length)
                else:
                    excluded_long_actions.append(record)
        motion_reports.append(
            {
                "motion_id": motion_id,
                "detected_action_groups": len(groups),
                "observed_action_groups": sum(bool(item["start_observed"]) for item in local_records),
                "censored_action_groups": sum(not bool(item["start_observed"]) for item in local_records),
                "records": local_records,
            }
        )

    if not records or robot_asset_json is None:
        raise RuntimeError("no observed complete limb actions extracted")
    args.output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output / "manifest.npz",
        source_paths=np.asarray([item["source_path"] for item in records]),
        contact_source_paths=np.asarray([item["contact_source_path"] for item in records]),
        motion_ids=np.asarray([item["motion_id"] for item in records]),
        segment_ids=np.asarray([item["segment_id"] for item in records]),
        start_frames=np.asarray([item["start_frame"] for item in records], dtype=np.int64),
        end_frames=np.asarray([item["end_frame"] for item in records], dtype=np.int64),
        robot_asset_json=np.asarray(robot_asset_json),
    )
    with (args.output / "atoms.jsonl").open("w", encoding="utf-8") as stream:
        for item in records:
            stream.write(json.dumps(item, sort_keys=True) + "\n")
    summary = {
        "schema": "g1_complete_limb_actions_newton_v3",
        "definition": {
            "primitive": "active limb onset/liftoff through its touchdown",
            "leg_chain": "foot OR knee, union before debounce",
            "hand_reach": "last entry into touchdown-centered capture sphere",
            "other_support_changes": "retained inside primitive, not segmentation boundaries",
            "near_simultaneous_touchdowns": "merged only for distinct overlapping action intervals",
            "contact_min_stable_frames": args.contact_min_stable_frames,
            "touchdown_merge_gap_frames": args.touchdown_merge_gap_frames,
            "hand_capture_radius_m": args.hand_capture_radius_m,
            "hand_support_event_snap_frames": args.hand_support_event_snap_frames,
            "maximum_observed_frames": args.maximum_observed_frames,
            "maximum_observed_frames_basis": (
                "physical-rate equivalent of PARC complete-action max: 68 frames at 30Hz "
                "is about 113 frames at 50Hz; rounded to 120"
            ),
        },
        "fps": float(np.median(fps_values)),
        "contact_source": str(args.manifest),
        "contact_semantics": "Newton 8-part force mask; heel/toe unioned before leg-chain debounce",
        "motion_count": len(motion_reports),
        "observed_actions": len(records),
        "raw_observed_length_frames": quantiles(observed_lengths),
        "eligible_length_frames": quantiles(eligible_lengths),
        "excluded_long_action_count": len(excluded_long_actions),
        "excluded_long_actions": excluded_long_actions,
        "censored_length_frames": quantiles(censored_lengths),
        "motions": motion_reports,
        "artifacts": {
            "manifest": str(args.output / "manifest.npz"),
            "metadata": str(args.output / "atoms.jsonl"),
        },
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "observed_actions": len(records),
                "raw_observed_length_frames": summary["raw_observed_length_frames"],
                "eligible_length_frames": summary["eligible_length_frames"],
                "excluded_long_action_count": summary["excluded_long_action_count"],
                "censored_length_frames": summary["censored_length_frames"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
