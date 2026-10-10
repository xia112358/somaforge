"""Apply audited soft hold joins to an existing canonical edit collection.

The original motions and physical recordings stay immutable. Mixed poses get
new FK, Newton labels, event evidence and provenance; no forces are inherited.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import hashlib
from pathlib import Path
import subprocess
import sys

import numpy as np

from compact_edited_stationary import compact
from motion_edit.generation.regenerate_edits import dump, rows, cropped_event_contract
from motion_edit.generation.rebase_edit_plan import crop_events
from motion_edit.generation.event_acceptance import audit_events, PARTS
from somaforge_core.newton_contact_data import load_contact_labels
from somaforge_core.support_evidence import load_support_observations
from somaforge_core.loaded_material_motion import material_path_report
from motion_edit.generation.loaded_material_reference import material_steps, remap_reference_sites


def require_source_event_preservation(index):
    """A production edit must preserve its declared source contact events.

    This rejects the complete unfinished generation stage, without deleting or
    filtering demonstrations. Self-observed diagnostic cohorts have no such
    generation certificate and cannot claim source-event preservation.
    """
    if index.get('schema') != 'native_execution_edit_collection_v1':
        return
    failed = [r['motion_id'] for r in index['motion_files']
              if r.get('event_acceptance', {}).get('passed') is not True]
    if failed:
        raise ValueError('Repair source-bound augmentation events before soft joining '
                         'the complete collection; no demonstrations are filtered: ' + ', '.join(failed))


def remap_events(source_events, contract):
    events = crop_events(source_events, np.asarray(contract['source_frames']))
    # One shared boundary after an explicitly synthesized soft connection,
    # rather than a synthetic stationary action or an unobserved bridge.
    for join in contract['soft_joins']:
        seam = join['seam_frame']
        previous = next(e for e in events if e['end_frame'] == seam-1)
        following = next(e for e in events if e['start_frame'] == seam)
        following['pre_soft_join_start_frame'] = seam
        following['start_frame'] = previous['end_frame']
        following['duration_frames'] = following['end_frame']-following['start_frame']
        following['duration_s'] = following['duration_frames']/contract['fps']
        following['soft_join_boundary'] = dict(seam_frame=seam, source_exit_frame=contract['source_frames'][seam]-1,
            status='pending_native_contact_and_continuity_audit')
    return events


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--blend-frames', type=int, default=16)
    p.add_argument('--label-workers', type=int, default=5)
    p.add_argument('--limit', type=int)
    p.add_argument('--resume', action='store_true')
    args = p.parse_args()
    base, out = args.collection.absolute(), args.output.absolute()
    index = json.loads((base/'index.json').read_text())
    require_source_event_preservation(index)
    entries = index['motion_files'][:args.limit]
    policy_path = base/'source/crop_policy.json'
    policy = json.loads(policy_path.read_text())
    source_events = rows(base/'source/events.jsonl')
    source_policy = json.loads((base/'source/event_contract.json').read_text())['policy']
    reference_loads=load_support_observations(base/'source/motion.npz',base/'source/observations.npz')
    with np.load(base/'source/loaded_sites.npz',allow_pickle=False) as z:
        reference_sites={k:z[k] for k in z.files}
    out.mkdir(parents=True, exist_ok=args.resume)
    (out/'source').mkdir(exist_ok=True)
    (out/'motions').mkdir(exist_ok=True)
    dump(out/'status.json', dict(stage='soft_cropping', completed=0, total=len(entries)))
    def verified_contract(path, source):
        contract=json.loads(path.read_text())
        if (contract['source_sha256'] != hashlib.sha256(source.read_bytes()).hexdigest()
                or contract['inclusive_holds'] != policy['holds']
                or any(len(j['right_weights']) != args.blend_frames for j in contract['soft_joins'])):
            raise ValueError('Existing soft crop belongs to different source or blend parameters')
        return contract
    jobs = []; results = []
    source_crop = out/'source/motion_cropped.npz'
    source_contract_path = out/'source/compaction.json'
    if not source_crop.exists():
        c = compact(base/'source/motion.npz', source_crop, policy['holds'], policy_path,
                    blend_frames=args.blend_frames)
        c['fps'] = 50.
        dump(source_contract_path, c)
    else:
        c = verified_contract(source_contract_path,base/'source/motion.npz')
    source_cropped_events = remap_events(source_events, c)
    dump(out/'source/crop_policy.json', dict(source_policy=policy, blend_frames=args.blend_frames,
         source_pose_status='soft_edited_reference_not_original_execution'))
    source_event_path = out/'source/events_cropped.jsonl'
    source_event_path.write_text(''.join(json.dumps(e)+'\n' for e in source_cropped_events))
    for i, entry in enumerate(entries):
        folder = out/'motions'/entry['motion_id']; folder.mkdir(exist_ok=True)
        motion = folder/'motion_cropped.npz'
        if not motion.exists():
            contract = compact(Path(entry['motion']), motion, policy['holds'], policy_path,
                               blend_frames=args.blend_frames)
            with np.load(motion, allow_pickle=False) as z: contract['fps'] = float(z['fps'])
            dump(folder/'compaction.json', contract)
        else: contract = verified_contract(folder/'compaction.json',Path(entry['motion']))
        events = remap_events(source_events, contract)
        ep = folder/'events_cropped.jsonl'
        ep.write_text(''.join(json.dumps(e)+'\n' for e in events))
        result = dict(entry, cropped_motion=str(motion), cropped_contacts=str(folder/'motion_cropped_contacts.npz'),
                      cropped_events=str(ep), compaction=str(folder/'compaction.json'))
        if 'source_loaded_site_reference' in result:
            result['full_source_loaded_site_reference']=result.pop('source_loaded_site_reference')
        results.append(result)
        plan = json.loads(Path(entry['plan']).read_text())
        key = plan['metadata']['terrain_sha256'] if 'terrain_sha256' in plan['metadata'] else None
        if key is None:
            # Exact native scene identity comes from the verified old labels.
            with np.load(entry['contacts'], allow_pickle=False) as z:
                fp = json.loads(z['contact_semantics_json'].item())['scene']['model_fingerprint']
            matches = [s for s in (base/'scenes').iterdir()
                       if s.is_dir() and json.loads((s/'model.json').read_text())['model_fingerprint'] == fp]
            if len(matches) != 1: raise ValueError('No unique native terrain binding')
            key = matches[0].name
        jobs.append((key, dict(motion=str(motion), labels_output=result['cropped_contacts'])))
        dump(out/'status.json', dict(stage='soft_cropping', completed=i+1, total=len(entries)))
    # Source is the unmodified native source scene (height scale 1).
    with np.load(base/'source/contacts.npz', allow_pickle=False) as z:
        fp = json.loads(z['contact_semantics_json'].item())['scene']['model_fingerprint']
    source_scene = next(s for s in (base/'scenes').iterdir()
                        if s.is_dir() and json.loads((s/'model.json').read_text())['model_fingerprint'] == fp)
    source_labels = out/'source/contacts_cropped.npz'
    jobs.append((source_scene.name, dict(motion=str(source_crop), labels_output=str(source_labels))))
    grouped = {}
    for key, job in jobs: grouped.setdefault(key, []).append(job)
    dump(out/'status.json', dict(stage='native_relabel', total=len(jobs)))

    def label(item):
        key, tasks = item; scene = base/'scenes'/key; folder = out/'queries'/key
        folder.mkdir(parents=True, exist_ok=True)
        pending = []
        for task in tasks:
            if Path(task['labels_output']).exists():
                load_contact_labels(task['motion'], task['labels_output'])
            else: pending.append(task)
        if not pending: return
        job_path = folder/'jobs.json'
        dump(job_path, dict(model_fingerprint=json.loads((scene/'model.json').read_text())['model_fingerprint'], jobs=pending))
        command = [sys.executable, 'scripts/serve_newton_contact_queries.py', '--checkpoint', str(args.checkpoint),
            '--motion-manifest', str(scene/'manifest.json'), '--binding', str(scene/'binding.json'),
            '--inspection-output', str(scene/'model.json'), '--query-worlds', '1', '--query-nconmax', '2048',
            '--query-njmax', '16384', '--device', 'cuda:0', '--relabel-jobs', str(job_path)]
        with (folder/'relabel.log').open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    with ThreadPoolExecutor(max_workers=args.label_workers) as pool:
        for future in as_completed([pool.submit(label, item) for item in grouped.items()]): future.result()
    dump(out/'status.json', dict(stage='join_audit', total=len(results)))
    for result in results:
        motion = Path(result['cropped_motion']); data = load_contact_labels(motion, result['cropped_contacts'])
        contract = json.loads(Path(result['compaction']).read_text())
        events = rows(result['cropped_events'])
        event_contract = cropped_event_contract(data, events, contract['fps'], [[0,len(data['contact_part_mask'])]],
                                                source_policy=source_policy)
        sites, known, bearing=remap_reference_sites(reference_sites,contract['source_frames'],
            load_known=reference_loads['load_known'][:-1],load_bearing=reference_loads['load_bearing'][:-1])
        phases=[dict(event_id=a['id'],start=a['start'],end=a['end'],part=r['part'],surface=r['surface'])
            for a in event_contract['actions'] for r in a['requirements'] if r['kind']=='keep']
        cropped_material_motion=material_path_report(material_steps(motion,sites,len(contract['source_frames'])),
            phases,load_known=known,load_bearing=bearing)
        report, _ = audit_events(event_contract, data['contact_part_mask'], data['contact_surface'])
        with np.load(motion, allow_pickle=False) as z: q=z['joint_pos']; positions=z['body_pos_w']
        with np.load(result['motion'], allow_pickle=False) as z: full_q=z['joint_pos']
        with np.load(result['contacts'], allow_pickle=False) as z:
            source_separation=json.loads(z['full_robot_separation_json'].item())
        with np.load(result['cropped_contacts'], allow_pickle=False) as z:
            separation=json.loads(z['full_robot_separation_json'].item())
        audits = []
        for join in contract['soft_joins']:
            a,b = join['output_window']; seam=join['seam_frame']
            source_indices = join['left_source_frames']+join['right_source_frames']
            source_steps = np.concatenate([np.diff(full_q[window,7:], axis=0)
                for window in (join['left_source_frames'], join['right_source_frames'])])
            # Source-wide step maximum provides a documented kinematic scale;
            # no contact-distance threshold is introduced by this audit.
            step = float(np.abs(np.diff(q[max(0,a-1):min(len(q),b+2),7:],axis=0)).max())
            cap = float(np.abs(np.diff(full_q[:,7:],axis=0)).max())
            following = next(e for e in events if e.get('pre_soft_join_start_frame') == seam)
            previous = next(e for e in events if e['end_frame'] == seam-1)
            keep_parts = set(previous['persistent_parts']) | set(following['persistent_parts'])
            required = [(PARTS.index(name), int(following['source_surfaces'][PARTS.index(name)]))
                        for name in sorted(keep_parts)]
            contact_ok = all((data['contact_part_mask'][a:seam+1,p]
                             & (data['contact_surface'][a:seam+1,p]==s)).all() for p,s in required)
            geometry = {}
            for kind in ('terrain','self'):
                field=kind+'_penetration_m'
                baseline=max(source_separation[t][field] for t in source_indices)
                candidate=max(separation[t][field] for t in range(a,seam+1))
                geometry[kind]=dict(source_max_m=baseline,joined_max_m=candidate,
                                    not_worse_than_source=candidate<=baseline+1.e-6)
            invalid=sum(len(separation[t]['invalid_penetrating_witnesses']) for t in range(a,seam+1))
            passed = bool(contact_ok and step <= cap+1.e-7 and invalid==0
                          and all(g['not_worse_than_source'] for g in geometry.values()))
            audits.append(dict(seam_frame=seam, passed=passed, required_keep=required,
                contact_passed=bool(contact_ok), max_join_joint_step_deg=float(np.degrees(step)),
                separation=geometry, invalid_penetrating_witnesses=invalid,
                source_max_joint_step_deg=float(np.degrees(cap)),
                seam_root_cm=float(np.linalg.norm(q[seam,:3]-q[seam-1,:3])*100),
                seam_max_body_cm=float(np.linalg.norm(positions[seam]-positions[seam-1],axis=-1).max()*100)))
            following['soft_join_boundary']['status'] = 'native_contact_and_continuity_audit_passed' if passed else 'rejected'
        passed = all(a['passed'] for a in audits)
        contract.update(join_status='audited_reference_contact_connection' if passed else 'rejected',
                        cross_seam_supervision_allowed=passed, join_audit=audits)
        for event in events: event['cross_seam_supervision_allowed']=passed
        Path(result['cropped_events']).write_text(''.join(json.dumps(e)+'\n' for e in events))
        dump(result['compaction'], contract)
        with np.load(result['cropped_contacts'], allow_pickle=False) as z:
            separation=json.loads(z['full_robot_separation_json'].item())
        separation_summary = dict(frames=len(separation),
            terrain_penetration_m=max(r['terrain_penetration_m'] for r in separation),
            self_penetration_m=max(r['self_penetration_m'] for r in separation),
            invalid_witnesses=sum(len(r['invalid_penetrating_witnesses']) for r in separation),
            join_terrain_penetration_m=max(separation[t]['terrain_penetration_m']
                for join in contract['soft_joins'] for t in range(join['output_window'][0],join['seam_frame']+1)),
            join_self_penetration_m=max(separation[t]['self_penetration_m']
                for join in contract['soft_joins'] for t in range(join['output_window'][0],join['seam_frame']+1)))
        result.update(cropped_event_acceptance=report, join_audit=audits, full_robot_separation=separation_summary,
                      cropped_source_loaded_site_reference=cropped_material_motion,
                      join_passed=passed)
        dump(motion.parent/'acceptance.json',result)
    dump(out/'index.json', dict(schema='soft_joined_native_edit_collection_v1', source_collection=str(base),
         motion_files=results, total=len(results), training_ready=False,
         force_bearing_slip_status='unknown_without_new_execution'))
    summary = dict(total=len(results), joins_passed=sum(r['join_passed'] for r in results),
        native_labels=len(jobs), frame_count=len(c['source_frames']), training_ready=False)
    dump(out/'summary.json', summary); dump(out/'status.json',dict(stage='complete',**summary))
    print(json.dumps(summary),flush=True)


if __name__=='__main__': main()
