"""Generate edits from the authoritative source and its explicit support phases.

Produces augmentation references, never silently publishes a training dataset.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import argparse
import hashlib
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path


def main():
    from motion_edit.generation.native_contact_refinement import (
        RefinementConfig, REFINEMENT_OBJECTIVE_SCHEMA)
    defaults = RefinementConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=defaults.steps)
    parser.add_argument('--learning-rate', type=float, default=defaults.learning_rate)
    parser.add_argument('--query-worlds', type=int, default=32)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--support-phases', type=Path, required=True)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--reuse-completed', type=Path)
    args = parser.parse_args()
    from somaforge_core.robot_assets import somaforge_root
    from motion_edit.generation.rollout_authority import generate_contact_aware_pyroki_preview
    from contact_solver.contact_regions import CONTACT_INTERVAL_SCHEMA
    from somaforge_core.support_semantics import SUPPORT_ASSESSMENT_SCHEMA
    from compact_edited_stationary import compact
    root = somaforge_root()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = json.loads((args.archive/'versions/temporal207_training_v2_ready/index.json').read_text())['motion_files']
    pilots = [Path(x['plan_path']).stem for x in json.loads((args.dataset/'design_v2/pilot.json').read_text())['plans']][::-1]
    rows.sort(key=lambda r: (pilots.index(r['motion_id']) if r['motion_id'] in pilots else len(pilots), r['motion_id']))
    if args.limit is not None:
        rows = rows[:args.limit]
    accepted = json.loads((args.dataset/'baseline207_repair_v1/h110/audit.json').read_text())['final']
    import numpy as np
    with np.load(args.dataset/'source/motion.npz', allow_pickle=False) as source:
        source_joint_step = float(np.rad2deg(np.abs(np.diff(source['joint_pos'][:, 7:], axis=0))).max())
    items = []
    failures = 0
    lock = threading.RLock()
    preparation_lock = threading.Lock()
    active = {}
    source_signature = {name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in dict(source=args.dataset/'source/motion.npz',
                               labels=args.dataset/'source/effective_contacts.npz',
                               events=args.dataset/'source/keyframe_segments/atoms.jsonl',
                               phases=args.support_phases).items()}

    def write_status(stage, **kw):
        report = dict(stage=stage, total=len(rows), completed=len(items), items=items,
                      updated_at=time.time(), training_ready=False, workers=args.workers, active=dict(active), **kw)
        tmp = args.output/'status.pending.json'
        tmp.write_text(json.dumps(report, indent=2))
        tmp.replace(args.output/'status.json')
        print(json.dumps({k:v for k,v in report.items() if k != 'items'}), flush=True)

    def save_status(stage, **kw):
        with lock:
            write_status(stage, **kw)

    def process_one(row):
        started = time.time()
        name = row['motion_id']
        plan_path = args.dataset/'design_v2/plans'/f'{name}.json'
        signature = dict(**source_signature, plan=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                         steps=args.steps, learning_rate=args.learning_rate,
                         contact_interval_schema=CONTACT_INTERVAL_SCHEMA,
                         objective_schema=REFINEMENT_OBJECTIVE_SCHEMA,
                         support_assessment_schema=SUPPORT_ASSESSMENT_SCHEMA)
        folder = args.output/name
        report_path = folder/'reference_acceptance.json'
        if args.reuse_completed is not None and not (folder/'audit.json').exists():
            candidate = args.reuse_completed/name
            if (candidate/'reference_acceptance.json').exists():
                candidate = Path(json.loads((candidate/'reference_acceptance.json').read_text())['full_motion']).parent
            if (candidate/'audit.json').exists():
                previous = json.loads((candidate/'audit.json').read_text())
                reuse_report = args.reuse_completed/name/'reference_acceptance.json'
                same_inputs = (reuse_report.exists() and
                               json.loads(reuse_report.read_text()).get('input_signature') == signature)
                if (same_inputs and previous.get('contact_interval_schema') == CONTACT_INTERVAL_SCHEMA
                        and previous.get('objective_schema') == REFINEMENT_OBJECTIVE_SCHEMA
                        and previous.get('event_contract_schema') == 'explicit_action_contact_acceptance_v2'
                        and previous.get('source_initializer',{} ) is not None
                        and previous.get('source_initializer',{}).get('schema') == 'authoritative_source_edited_initializer_v1'):
                    folder = candidate
        if report_path.exists():
            existing=json.loads(report_path.read_text())
            if (existing.get('input_signature') != signature
                    or existing.get('generation_contract')!=REFINEMENT_OBJECTIVE_SCHEMA
                    or existing.get('contact_interval_schema')!=CONTACT_INTERVAL_SCHEMA
                    or (existing.get('source_initializer') or {}).get('schema')!='authoritative_source_edited_initializer_v1'):
                raise ValueError('Old augmented candidate cannot be reused as a source-phase result')
            return existing
        if args.reuse_completed is not None and folder != args.output/name:
            previous_report = args.reuse_completed/name/'reference_acceptance.json'
            if previous_report.exists():
                result = json.loads(previous_report.read_text())
                result.update(reused=True, elapsed_seconds=time.time()-started)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(json.dumps(result, indent=2))
                return result
        with lock:
            active[name] = dict(started_at=started)
            save_status('refining', motion_id=name)
        try:
            with preparation_lock:
                plan_path = args.dataset/'design_v2/plans'/f'{name}.json'
                plan = json.loads(plan_path.read_text())
                terrain = Path(plan['metadata']['target_terrain_mesh'])
                key = hashlib.sha256(terrain.read_bytes()).hexdigest()[:16]
                scene = args.dataset/'scenes'/key/f'worlds_{args.query_worlds}'
                scene.mkdir(parents=True, exist_ok=True)
                if not (scene/'manifest.json').exists():
                    manifest = json.loads((root/'runtime/current/manifests/wbt_single_climb_00.json').read_text())
                    source_path = (args.dataset/'source/motion.npz').resolve()
                    manifest['terrains'][0].update(terrain_file=str(terrain.resolve()),
                        terrain_sha256=hashlib.sha256(terrain.read_bytes()).hexdigest())
                    motion_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
                    manifest['motion_files'][0].update(motion_file=str(source_path), motion_sha256=motion_hash,
                        source_file=str(source_path), source_sha256=motion_hash)
                    (scene/'manifest.json').write_text(json.dumps(manifest, indent=2))
                if not (scene/'binding.json').exists():
                    with (scene/'export.log').open('w') as log:
                        subprocess.run([sys.executable, str(root/'scripts/serve_newton_contact_queries.py'),
                            '--checkpoint', str(args.checkpoint), '--motion-manifest', str(scene/'manifest.json'),
                            '--binding', str(scene/'binding.json'), '--inspection-output', str(scene/'model.json'),
                            '--query-nconmax', '2048', '--query-njmax', '16384', '--device', 'cuda:0',
                            '--query-worlds', str(args.query_worlds), '--create-native-binding', '--inspect-only'], cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
                taskspace = args.dataset/'work_v3'/f'{name}.contact_aware_taskspace.npz'
                if not taskspace.exists():
                    taskspace = generate_contact_aware_pyroki_preview(plan_path,
                        output_motion_path=args.output/'compile_only'/f'{name}.npz',
                        intermediate_dir=args.output/'taskspaces', compile_only=True)
            from motion_edit.generation.source_support import initialize_source_edit
            motion = args.output/'source_initializers'/f'{name}.npz'
            if not motion.exists():
                initialize_source_edit(args.dataset/'source/motion.npz',plan_path,motion)
            with np.load(motion, allow_pickle=False) as seed:
                provenance = json.loads(seed['source_initializer_json'].item())
            if (provenance.get('schema') != 'authoritative_source_edited_initializer_v1'
                    or provenance.get('source_sha256') != hashlib.sha256((args.dataset/'source/motion.npz').read_bytes()).hexdigest()
                    or provenance.get('plan_sha256') != hashlib.sha256(plan_path.read_bytes()).hexdigest()):
                raise ValueError('Initializer does not match the current source and edit plan')
            if not (folder/'audit.json').exists():
                if folder.exists():
                    raise RuntimeError('Incomplete candidate retained; use a fresh output directory to retry')
                command = [sys.executable, str(root/'scripts/refine_motion_contacts.py'),
                    '--motion', str(motion), '--events', str(args.dataset/'source/keyframe_segments/atoms.jsonl'),
                    '--support-phases', str(args.support_phases), '--taskspace', str(taskspace), '--checkpoint', str(args.checkpoint),
                    '--manifest', str(scene/'manifest.json'), '--binding', str(scene/'binding.json'),
                    '--output', str(folder), '--continuity-reference', str(args.dataset/'source/motion.npz'),
                    '--event-reference-contacts', str(args.dataset/'source/effective_contacts.npz'),
                    '--cpu-threads', '1', '--steps', str(args.steps), '--learning-rate', str(args.learning_rate), '--query-worlds', str(args.query_worlds), '--source-support']
                with (args.output/f'{name}.log').open('w') as stream:
                    subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT, check=True)
            audit = json.loads((folder/'audit.json').read_text())
            if ((audit.get('source_initializer') or {}).get('schema')!='authoritative_source_edited_initializer_v1'
                    or audit.get('objective_schema') != REFINEMENT_OBJECTIVE_SCHEMA
                    or audit.get('contact_interval_schema') != CONTACT_INTERVAL_SCHEMA):
                raise ValueError('Candidate source or contact objective does not match the current contract')
            before, after = audit['initial'], audit['final']
            # The user-accepted h110 reference supplies the residual-geometry
            # allowance. This is NOT a contact activation threshold.
            depth_limit = accepted['max_penetration_mm']
            joint_limit = max(before['max_joint_step_deg'], accepted['max_joint_step_deg'], source_joint_step)
            a, b = before['source_support'], after['source_support']
            checks = dict(contact_events=after['contact_events_passed'],
                          residual_geometry=after['max_penetration_mm'] <= depth_limit,
                          no_larger_joint_jump=after['max_joint_step_deg'] <= joint_limit,
                          source_relative_contact_motion=after['phase_support']['passed'])
            result = dict(motion_id=name, generation_contract=REFINEMENT_OBJECTIVE_SCHEMA,
                          contact_interval_schema=CONTACT_INTERVAL_SCHEMA,
                          support_assessment_schema=SUPPORT_ASSESSMENT_SCHEMA,
                          actual_support_status='unknown_without_new_execution',
                          input_signature=signature,
                          learning_rate=audit.get('learning_rate'), steps=args.steps,
                          source_initializer=audit['source_initializer'], phase_support=after['phase_support'],
                          reference_usable=all(checks.values()), checks=checks,
                          source_motion=str(motion), full_motion=str(folder/'motion.npz'),
                          support_before=a, support_after=b, training_ready=False,
                          source_max_joint_step_deg=source_joint_step, joint_step_allowance_deg=joint_limit,
                          selected_iteration=after.get('selected_iteration', after['step']),
                          depth_allowance_mm=depth_limit, max_penetration_mm=after['max_penetration_mm'],
                          strict_geometry_passed=after['geometry_passed'],
                          acceptance_scope='augmentation_reference_not_dynamics_certification')
            cropped = folder/'motion_cropped.npz'
            if not cropped.exists():
                contract = compact(folder/'motion.npz', cropped, [(471,699)], args.dataset/'compaction_policy.json')
                (folder/'compaction.json').write_text(json.dumps(contract, indent=2))
            result.update(cropped_motion=str(cropped), cropped_contact_labels='pending_fresh_native_relabel',
                          cross_seam_supervision=False)
            result.update(elapsed_seconds=time.time()-started, reused=folder != args.output/name)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(result, indent=2))
            return result
        except Exception:
            error = traceback.format_exc()
            (args.output/f'{name}.error.txt').write_text(error)
            return dict(motion_id=name, error=error, reference_usable=False,
                        elapsed_seconds=time.time()-started)

    if args.workers < 1:
        raise ValueError('workers must be positive')
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_one, row): row['motion_id'] for row in rows}
        for future in as_completed(futures):
            result = future.result()
            with lock:
                active.pop(result['motion_id'], None)
                items.append(result)
                failures = failures+1 if 'error' in result else 0
                save_status('refining')
            if failures >= 3:
                for pending in futures:
                    pending.cancel()
                save_status('blocked_by_repeated_errors')
                raise RuntimeError('Three consecutive errors; queued work cancelled')
    save_status('generation_complete', usable=sum(x.get('reference_usable', False) for x in items))


if __name__ == '__main__':
    main()
