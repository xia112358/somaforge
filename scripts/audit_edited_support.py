"""Audit edited material-point motion and actual Newton endpoint contacts.

Reads fixed-q native labels; never infers contact from geometric thresholds.
The output is a diagnostic report, not an automatic training approval.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from somaforge_core.contact_face_selection import select_contact_pairs
from somaforge_core.newton_contact_data import load_contact_labels
from somaforge_core.robot_assets import decode_robot_asset_json


def load_motion(path):
    with np.load(path, allow_pickle=True) as z:
        decode_robot_asset_json(z['robot_asset_json'].item(), context=str(path))
        names = [str(n).rsplit('/', 1)[-1] for n in z['body_names']]
        pos = z['body_pos_w'].astype(float)
        quat = z['body_quat_w'].astype(float)
        rotation = Rotation.from_quat(quat[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(*quat.shape[:-1], 3, 3)
        return names, pos, rotation, z['joint_pos'].copy()


def load_contacts(motion, labels):
    load_contact_labels(motion, labels)
    with np.load(labels, allow_pickle=False) as z:
        sem = json.loads(z['contact_semantics_json'].item())
        pairs = json.loads(z['contact_pairs_json'].item())
        selected = select_contact_pairs(pairs, sem['scene']['surface_catalog'])
        return selected, sem, z['part_order'].tolist(), int(z['unallocated_active_contact'].sum()), pairs


def continuity_report(source, motion):
    """Scan all transitions, including flight and contact activation boundaries."""
    sn, sp, _, sq = load_motion(source)
    gn, gp, _, gq = load_motion(motion)
    if sq.shape != gq.shape or len(sq) < 3:
        raise ValueError('Continuity audit requires aligned full trajectories')
    with np.load(source, allow_pickle=True) as a, np.load(motion, allow_pickle=True) as b:
        if not np.array_equal(a['joint_names'], b['joint_names']):
            raise ValueError('Joint ordering mismatch')
        names = a['joint_names'].astype(str).tolist()
    result = {}
    for tag, q, p, body_names in [('source',sq,sp,sn), ('edited',gq,gp,gn)]:
        dq = np.diff(q[:,7:],axis=0)
        ddq = np.diff(q[:,7:],n=2,axis=0)
        worst = np.unravel_index(np.argmax(np.abs(dq)),dq.shape)
        row = dict(max_joint_step_degrees=float(np.rad2deg(abs(dq[worst]))),
                   max_joint_step_frame=int(worst[0]+1), max_joint_step_name=names[worst[1]],
                   max_joint_second_difference_degrees=float(np.rad2deg(abs(ddq).max())),
                   endpoints={})
        for body in ('left_ankle_roll_link','right_ankle_roll_link','left_knee_link',
                     'right_knee_link','left_sphere_hand_link','right_sphere_hand_link'):
            i=body_names.index(body)
            steps=np.linalg.norm(np.diff(p[:,i],axis=0),axis=-1)
            top=np.argsort(steps)[-10:][::-1]
            row['endpoints'][body]=dict(max_step_m=float(steps.max()),
                worst_transitions=[dict(frame=int(t+1),step_m=float(steps[t])) for t in top])
        result[tag]=row
    return result


def audit(source, source_labels, motion, labels, yaw_degrees, plan=None):
    sn, sp, sr, sq = load_motion(source)
    gn, gp, gr, gq = load_motion(motion)
    if len(sq) != len(gq):
        raise ValueError('Audit untrimmed aligned motions before compaction')
    a, sem, parts, sa, _ = load_contacts(source, source_labels)
    b, _, other_parts, ga, raw = load_contacts(motion, labels)
    if parts != other_parts:
        raise ValueError('Part order mismatch')
    yaw = Rotation.from_euler('z', yaw_degrees, degrees=True).as_matrix()
    surface_rotations = {}
    if plan is not None:
        from motion_edit.contact.surface_frame import map_points_between_surface_frames
        transforms = json.loads(plan.read_text())['surface_transforms']
        for surface in sem['scene']['surface_catalog']:
            matches = [t for t in transforms
                       if np.allclose(t['source_surface']['normal'], surface['normal_w'], atol=1.e-6)
                       and abs(np.dot(t['source_surface']['origin'], surface['normal_w']) - surface['plane_offset']) < 1.e-6]
            if len(matches) > 1:
                raise ValueError('Ambiguous authored source surface')
            rotation = np.eye(3)
            if matches:
                transform = matches[0]
                basis = map_points_between_surface_frames(np.vstack((np.zeros(3), np.eye(3))),
                    transform['source_surface'], transform['target_surface'])
                rotation = (basis[1:]-basis[0]).T
            surface_rotations[surface['surface']] = rotation
    source_mask = a['contact_part_mask']
    target_mask = b['contact_part_mask']
    missing = source_mask & ~target_mask
    added = ~source_mask & target_mask
    rows = {}
    for part, name in enumerate(parts):
        steps = []
        for t in np.flatnonzero(source_mask[:-1, part] & source_mask[1:, part]):
            errors, source_steps, output_steps = [], [], []
            for pair in a['contact_pairs'][t]:
                if pair['part'] != part:
                    continue
                body = sem['provenance']['body_labels'][pair['body']].rsplit('/', 1)[-1]
                i, j = sn.index(body), gn.index(body)
                local = sr[t, i].T @ (np.asarray(pair['position_w']) - sp[t, i])
                sd = sp[t + 1, i] + sr[t + 1, i] @ local - sp[t, i] - sr[t, i] @ local
                gd = gp[t + 1, j] + gr[t + 1, j] @ local - gp[t, j] - gr[t, j] @ local
                # Selected primary faces are horizontal. Tangential motion is
                # diagnostic; no distance here changes the native contact mask.
                rotation = surface_rotations[pair['surface']] if plan is not None else yaw
                errors.append(float(np.linalg.norm((gd - rotation @ sd)[:2])))
                source_steps.append(float(np.linalg.norm(sd[:2])))
                output_steps.append(float(np.linalg.norm(gd[:2])))
            if errors:
                steps.append(dict(frame=int(t + 1), extra_m=float(np.median(errors)),
                                  source_m=float(np.median(source_steps)), output_m=float(np.median(output_steps))))
        rows[name] = dict(missing_frames=np.flatnonzero(missing[:, part]).tolist(),
                          added_frames=np.flatnonzero(added[:, part]).tolist(),
                          material_steps=steps,
                          max_extra_step_m=max((x['extra_m'] for x in steps), default=None))
    return dict(schema='edited_support_native_audit_v1', source=str(source.resolve()),
                motion=str(motion.resolve()), source_labels=str(source_labels.resolve()),
                labels=str(labels.resolve()), yaw_degrees=yaw_degrees, parts=rows,
                authored_plan=str(plan.resolve()) if plan is not None else None,
                frames=len(gq), source_unallocated=sa, output_unallocated=ga,
                exact_source_endpoint_activation_preserved=not bool(missing.any() or added.any() or sa or ga),
                missing_part_frames=int(missing.sum()), added_part_frames=int(added.sum()),
                no_effective_contact_frames=np.flatnonzero(~target_mask.any(-1)).tolist(),
                max_raw_negative_dist_m=max((max(0., -p['dist']) for row in raw for p in row), default=0.),
                source_root_first_step_m=float(np.linalg.norm(sq[1, :3]-sq[0, :3])),
                output_root_first_step_m=float(np.linalg.norm(gq[1, :3]-gq[0, :3])),
                training_ready=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'source-labels', 'motion', 'labels', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--yaw-degrees', type=float, default=0.)
    p.add_argument('--plan', type=Path)
    args = p.parse_args()
    report = audit(args.source, args.source_labels, args.motion, args.labels, args.yaw_degrees, args.plan)
    report['whole_trajectory_continuity'] = continuity_report(args.source,args.motion)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != 'parts'}, indent=2))


if __name__ == '__main__':
    main()
