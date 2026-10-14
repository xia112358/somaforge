"""Crop certified holds with explicit quintic soft joins and fresh Newton FK.

Run native contact relabeling and event segmentation on this new artifact.
Old labels, events, velocities, and frame-indexed edits are not copied as truth.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from motion_edit.generation.stationary_compaction import compact_timeline, compact_qpos
from somaforge_core.kinematics import angular_velocity_wxyz, body_velocities_from_pose
from somaforge_core.robot_assets import decode_robot_asset_json


def compact(source, output, holds, evidence, *, blend_frames=16):
    with np.load(source, allow_pickle=True) as z:
        decode_robot_asset_json(z['robot_asset_json'].item(), context=str(source))
        q = z['joint_pos']
        if blend_frames:
            compact_pose, frames, _, seams, joins = compact_qpos(q, holds, blend_frames=blend_frames)
        else:
            frames, _, seams = compact_timeline(len(q), holds)
            compact_pose, joins = q[frames].copy(), []
        out = {k: z[k].copy() for k in ('fps', 'joint_names', 'body_names', 'robot_asset_json')}
        for k in ('joint_pos', 'body_pos_w', 'body_quat_w'):
            out[k] = z[k][frames].copy()
        out['joint_pos'] = compact_pose
    fps = float(out['fps'].item())
    if len(frames) < 2:
        raise ValueError('Not enough retained frames')
    # A mixed pose trajectory has one continuous clock. Exact frame selection
    # remains disconnected and must not imply a speed across removed time.
    cuts = np.asarray([0, len(frames)]) if joins else np.r_[0, seams, len(frames)]
    out['joint_vel'] = np.zeros((len(frames), out['joint_pos'].shape[1]-1))
    out['body_lin_vel_w'] = np.zeros_like(out['body_pos_w'])
    out['body_ang_vel_w'] = np.zeros_like(out['body_pos_w'])
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b-a < 2:
            continue
        q = out['joint_pos'][a:b]
        out['joint_vel'][a:b] = np.concatenate((np.gradient(q[:, :3], 1/fps, axis=0),
            angular_velocity_wxyz(q[:, 3:7], 1/fps), np.gradient(q[:, 7:], 1/fps, axis=0)), axis=1)
        linear, angular = body_velocities_from_pose(out['body_pos_w'][a:b], out['body_quat_w'][a:b], fps)
        out['body_lin_vel_w'][a:b], out['body_ang_vel_w'][a:b] = linear, angular
    contract = dict(schema=('edited_stationary_soft_join_v1' if joins else 'edited_stationary_frame_selection_v1'), source=str(source.resolve()),
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    hold_evidence=str(evidence.resolve()),
                    hold_evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
                    inclusive_holds=holds, source_frames=frames.tolist(), seam_frames=seams.tolist(),
                    continuous_clip_ranges=[[int(a), int(b)] for a, b in zip(cuts[:-1], cuts[1:])],
                    pose_interpolation=bool(joins), soft_joins=joins,
                    pose_exact_selection=not bool(joins), cross_seam_supervision_allowed=False,
                    join_status='pending_native_contact_and_continuity_audit' if joins else 'disconnected',
                    native_relabel_required=True, event_rebuild_required=True, training_ready=False)
    out['source_frame_indices'] = frames
    out['stationary_compaction_json'] = np.asarray(json.dumps(contract, sort_keys=True))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    seed = output.with_name(output.stem+'.soft_seed.npz') if joins else output
    if seed.exists():
        with np.load(seed, allow_pickle=False) as previous:
            if (not joins or not np.array_equal(previous['joint_pos'], out['joint_pos'])
                    or previous['stationary_compaction_json'].item() != out['stationary_compaction_json'].item()):
                raise ValueError('Existing compaction seed differs from requested source/window')
    else:
        with seed.open('xb') as stream:
            np.savez_compressed(stream, **out)
    if joins:
        # Body transforms must come from blended q, never interpolated FK or
        # copied contact/force arrays. The seed is retained for provenance.
        from motion_edit.generation.newton_direct_fk import canonicalize_motion_with_direct_newton_fk
        canonicalize_motion_with_direct_newton_fk(seed, output)
    return contract


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--hold-evidence', required=True, type=Path)
    p.add_argument('--hold', nargs=2, type=int, action='append', required=True, metavar=('START', 'END'))
    p.add_argument('--blend-frames', type=int, default=16,
                   help='Quintic soft-join window; 0 exports disconnected exact frame selection')
    args = p.parse_args()
    result = compact(args.source, args.output, args.hold, args.hold_evidence, blend_frames=args.blend_frames)
    print(json.dumps({k: v for k, v in result.items() if k != 'source_frames'}, indent=2))


if __name__ == '__main__':
    main()
