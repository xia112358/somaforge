"""Segment any verified canonical motion; touchdown parts are active, not persistent.

Reuses temporal event selection; displacement is diagnostic only.
Newton labels remain unchanged.
"""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from gmvq.g1_fk import CanonicalG1TorchFK
from somaforge_core.newton_contact_data import load_contact_labels
from somaforge_core.contact_events import event_contract, group_endpoint
from segment_original28_interactions import (Config, LINKS, PARTS, EVENT_SELECTION,
    cluster_events, events_for_part, solver_event_geometry)


def optional_source_recording(motion):
    """Provenance is optional metadata, never an algorithmic prerequisite."""
    for key in ('rollout_ref_source_recording', 'source_recording'):
        if key in motion:
            return str(np.asarray(motion[key]).item())
    return None


def contact_roles(mask, surfaces, start, end, group):
    active = np.zeros(len(PARTS), dtype=bool)
    for event in group:
        p = event['part_index']
        if not mask[end, p] or surfaces[end, p] != event['surface']:
            raise ValueError('Touchdown target is not realized at segment endpoint')
        active[p] = True
    maintained = mask[start:end+1].all(axis=0)
    maintained &= (surfaces[start:end+1] == surfaces[start]).all(axis=0)
    persistent = maintained & ~active
    return active, persistent


@dataclass(frozen=True)
class HoldConfig:
    window_seconds: float = .5
    root_range_m: float = .02
    joint_range_rad: float = .08
    root_angle_rad: float = .08
    minimum_hold_seconds: float = .4
    settle_confirm_seconds: float = .24
    minimum_motion_frames: int = 7
    # Whole-hold bounds prevent slowly drifting motion passing local windows.
    total_range_multiplier: float = 2.


def stable_pose(q, mask, surfaces, cfg, multiplier=1.):
    """Pose extent, not accumulated jitter; contact truth is never changed."""
    if not mask[0].any() or not (mask == mask[0]).all():
        return False
    if not (surfaces[:, mask[0]] == surfaces[0, mask[0]]).all():
        return False
    quat = q[:, 3:7].astype(float)
    quat /= np.linalg.norm(quat, axis=1, keepdims=True)
    angle = 2*np.arccos(np.clip(np.abs(quat @ quat[0]), 0, 1))
    return bool(np.linalg.norm(np.ptp(q[:, :3], axis=0)) <= cfg.root_range_m*multiplier
                and np.ptp(q[:, 7:], axis=0).max() <= cfg.joint_range_rad*multiplier
                and angle.max() <= cfg.root_angle_rad*multiplier)


def trim_holds(start, end, q, mask, surfaces, fps, cfg):
    window = max(2, round(cfg.window_seconds*fps))
    confirm = max(1, round(cfg.settle_confirm_seconds*fps))
    minimum = max(1, round(cfg.minimum_hold_seconds*fps))
    candidates = []
    for a in range(start, end-window+2):
        b = a+window
        if stable_pose(q[a:b], mask[a:b], surfaces[a:b], cfg):
            candidates.append(a)
    runs = []
    for a in candidates:
        if runs and a == runs[-1][1]+1:
            runs[-1][1] = a
        else:
            runs.append([a, a])
    pieces, holds, cursor = [], [], start
    for first, last in runs:
        a, b = first+confirm, last+window-1
        if (b-a < minimum or a-cursor < cfg.minimum_motion_frames
                or end-b < cfg.minimum_motion_frames):
            continue
        if not stable_pose(q[a:b+1], mask[a:b+1], surfaces[a:b+1],
                           cfg, cfg.total_range_multiplier):
            continue
        pieces.append((cursor, a, 'settled_pose'))
        holds.append((a, b))
        cursor = b
    pieces.append((cursor, end, 'original_endpoint'))
    return pieces, holds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion', type=Path, required=True)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--trim-holds', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    labels = load_contact_labels(args.motion, args.labels)
    mask, surfaces = labels['contact_part_mask'], labels['contact_surface']
    with np.load(args.motion, allow_pickle=False) as z:
        q = z['joint_pos'].copy()
        fps = float(z['fps'].item())
        asset = str(z['robot_asset_json'].item())
        names = z['joint_names'].astype(str).tolist()
        source_recording = optional_source_recording(z)
    # Rollout stores a subset of links; recover exact requested link origins
    # from unchanged q and the authoritative URDF, not wrist proxies.
    with torch.no_grad():
        pos = CanonicalG1TorchFK(joint_names=names, link_names=list(LINKS))(
            torch.as_tensor(q, dtype=torch.float32)).numpy()
    normals, margins = solver_event_geometry(args.labels, len(mask))
    cfg = Config()
    events, rejected = [], []
    zeros = np.zeros(len(mask))
    for p, part in enumerate(PARTS):
        for surface in np.unique(surfaces[mask[:, p], p]):
            pair = mask[:, p] & (surfaces[:, p] == surface)
            accepted, skipped = events_for_part(pair, zeros, zeros, pos[:, p], fps, cfg,
                surfaces[:, p], normals[int(surface)], margins[(p, int(surface))])
            events.extend(dict(**e, part=part, part_index=p, surface=int(surface)) for e in accepted)
            rejected.extend(dict(**e, part=part, surface=int(surface)) for e in skipped)
    groups = cluster_events(events, mask, fps, cfg, surfaces)
    grouped_events = [event for group in groups for event in group]
    by_end = {group_endpoint(group): group for group in groups}
    if len(by_end) != len(groups):
        raise ValueError('Event groups share a boundary; refusing silent overwrite')
    boundaries = sorted({0, len(mask)-1, *by_end})
    rows, holds, intervals = [], [], []
    hold_cfg = HoldConfig()
    for parent, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        pieces, local_holds = (trim_holds(start, end, q, mask, surfaces, fps, hold_cfg)
                               if args.trim_holds else ([(start, end, 'original_endpoint')], []))
        intervals.extend((a, b, terminal, parent) for a, b, terminal in pieces)
        for a, b in local_holds:
            _, persistent = contact_roles(mask, surfaces, a, b, [])
            holds.append(dict(start_frame=a, end_frame=b, duration_s=(b-a)/fps,
                              parent_interval=parent, terminal_event='stable_hold',
                              include_for_infiller=False, active_parts=[],
                              persistent_parts=[PARTS[p] for p in np.flatnonzero(persistent)]))
    for j, (start, end, terminal, parent) in enumerate(intervals):
        group = by_end.get(end, []) if terminal == 'original_endpoint' else []
        terminal = ('touchdown' if group else 'terminal_tail') if terminal == 'original_endpoint' else terminal
        active, persistent = contact_roles(mask, surfaces, start, end, group)
        rows.append(dict(
            segment_id=f'rollout_interaction_{j:04d}',
            event_contract=event_contract(fps),
            event_selection=EVENT_SELECTION,
            parent_interval=parent, terminal_event=terminal,
            source_path=str(args.motion.resolve()), contact_source_path=str(args.labels.resolve()),
            start_frame=start, end_frame=end, inclusive_end=True,
            duration_frames=end-start, duration_s=(end-start)/fps,
            touchdown_events=group, touchdown_at_end=[e['part'] for e in group],
            active_parts=[PARTS[p] for p in np.flatnonzero(active)],
            persistent_parts=[PARTS[p] for p in np.flatnonzero(persistent)],
            unconstrained_parts=[PARTS[p] for p in np.flatnonzero(~active & ~persistent)],
            source_contact_parts=[PARTS[p] for p in np.flatnonzero(mask[start])],
            target_contact_parts=[PARTS[p] for p in np.flatnonzero(mask[end])],
            source_surfaces=surfaces[start].tolist(), target_surfaces=surfaces[end].tolist(),
            include_for_infiller=bool(group) or terminal == 'settled_pose', short_segment=end-start < 7,
        ))
    summary = dict(
        schema='newton_rollout_touchdown_active_segments_v2', config=asdict(cfg),
        contact_label_contract=labels['contact_label_contract'],
        event_contract=event_contract(fps),
        event_selection=EVENT_SELECTION,
        hold_config=asdict(hold_cfg) if args.trim_holds else None,
        hold_count=len(holds), removed_hold_seconds=sum(h['duration_s'] for h in holds),
        max_segment_seconds=max(r['duration_s'] for r in rows),
        robot_asset_json=asset, source_recording=source_recording,
        motion_sha256=hashlib.sha256(args.motion.read_bytes()).hexdigest(),
        labels_sha256=hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        contact_sampling='fixed_q_forward_no_integration',
        active_semantics='touchdown parts at the event endpoint; no full-segment contact constraint',
        persistent_semantics='non-active parts continuously contacting the same representative surface',
        unconstrained_semantics='neither role; does not imply stationary or non-contact',
        frames=len(mask), segments=len(rows), event_segments=sum(bool(r['touchdown_events']) for r in rows),
        touchdown_events=len(grouped_events), touchdown_candidates=len(events),
        short_segments=sum(r['short_segment'] for r in rows),
        events_by_part={p: sum(e['part'] == p for e in grouped_events) for p in PARTS},
        rejected_events=rejected, training_ready=False,
        limitations='Uses the shared effective contact contract; no support-force, dynamics or penetration acceptance implied.',
    )
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output/'atoms.jsonl').open('x') as f:
        for row in rows:
            f.write(json.dumps(row)+'\n')
    with (args.output/'summary.json').open('x') as f:
        json.dump(summary, f, indent=2)
    with (args.output/'holds.jsonl').open('x') as f:
        for hold in holds:
            f.write(json.dumps(hold)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('rejected_events', 'robot_asset_json')}, indent=2))


if __name__ == '__main__':
    main()
