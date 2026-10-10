"""Rebuild a complete edit collection from explicit native source evidence."""
import argparse
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

import numpy as np
from somaforge_core.loaded_material_motion import DEFAULT_MATERIAL_RESIDUAL_SCALE_M
from .newton_collision import COLLISION_WITNESS_SCHEMA
from .stable_contact_material import MATERIAL_SAMPLE_SCHEMA
from .continuous_ik import SOLVER_SCHEMA
from .optimization_geometry import OPTIMIZATION_GEOMETRY_SCHEMA, SPHERE_DISTANCE_SCHEMA

GENERATION_SCHEMA = 'native_observed_source_joint_trajectory_material_budget_edit_v12'
DEFAULT_ENVIRONMENT_DEPTH_RESIDUAL_SCALE_M = .01
DEFAULT_COLLISION_REFINEMENTS = 4
LOADED_MATERIAL_OBJECTIVE = 'loaded_material_phase_budget_source_regularizer_v2'


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def dump(path,value):
    path=Path(path)
    staged=path.with_name(f'.{path.name}.{os.getpid()}.{threading.get_ident()}.writing')
    staged.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    staged.replace(path)


def generation_objective(residual_scale_m, depth_scale_m, collision_refinements):
    if not np.isfinite(depth_scale_m) or depth_scale_m <= 0:
        raise ValueError('Environment depth residual normalization must be positive')
    if not np.isfinite(residual_scale_m) or residual_scale_m <= 0:
        raise ValueError('Material motion residual normalization must be positive')
    if collision_refinements < 1:
        raise ValueError('Positive collision refinement count required')
    return dict(material_motion_residual_scale_m=residual_scale_m,
        environment_depth_residual_scale_m=depth_scale_m,
        collision_refinements=collision_refinements,
        collision_witness_schema=COLLISION_WITNESS_SCHEMA,
        optimization_sample_contract=MATERIAL_SAMPLE_SCHEMA,
        ik_residual_dtype='float64',
        ik_solver_schema=SOLVER_SCHEMA,
        optimization_geometry_schema=OPTIMIZATION_GEOMETRY_SCHEMA,
        sphere_distance_schema=SPHERE_DISTANCE_SCHEMA,
        per_frame_optimization_calls=0,
        loaded_material_objective=LOADED_MATERIAL_OBJECTIVE)


def verify_effective_objective(diagnostics, requested):
    loaded = diagnostics.get('loaded_material_motion', {})
    effective = dict(material_motion_residual_scale_m=loaded.get('residual_scale_m'),
        environment_depth_residual_scale_m=diagnostics.get('environment_depth_residual_scale_m'),
        collision_refinements=diagnostics.get('environment_collision_max_refinements'),
        collision_witness_schema=diagnostics.get('environment_collision_witness_schema'),
        optimization_sample_contract=diagnostics.get('optimization_sample_contract'),
        ik_residual_dtype=diagnostics.get('ik_residual_dtype'),
        ik_solver_schema=diagnostics.get('ik_solver_schema'),
        optimization_geometry_schema=diagnostics.get('optimization_geometry_schema'),
        sphere_distance_schema=diagnostics.get('sphere_distance_schema'),
        per_frame_optimization_calls=diagnostics.get('per_frame_optimization_calls'),
        loaded_material_objective=loaded.get('objective'))
    if effective != requested:
        raise ValueError(f'IK objective configuration was not applied: requested={requested}, effective={effective}')
    return effective


def validate_completed_generation(record, plan, residual_scale_m, *,
        environment_depth_residual_scale_m=DEFAULT_ENVIRONMENT_DEPTH_RESIDUAL_SCALE_M,
        collision_refinements=DEFAULT_COLLISION_REFINEMENTS):
    if record.get('schema') != GENERATION_SCHEMA:
        raise ValueError('Completed edit predates the current contact-only objective; use a fresh output version')
    reference = record['loaded_reference']
    if reference.get('residual_scale_m') != residual_scale_m:
        raise ValueError('Completed edit uses a different material motion loss scale')
    requested = generation_objective(residual_scale_m, environment_depth_residual_scale_m, collision_refinements)
    if record.get('requested_objective') != requested or record.get('effective_objective') != requested:
        raise ValueError('Completed edit uses a different or unverified IK objective configuration')
    for key in ('sites', 'observations', 'phases'):
        if hashlib.sha256(Path(reference[key]).read_bytes()).hexdigest() != reference['sha256'][key]:
            raise ValueError('Completed edit uses changed loaded material reference')
    events = record.get('event_reference')
    if not events:
        raise ValueError('Completed edit lacks observed source event provenance')
    for key in ('motion', 'labels', 'events', 'contract'):
        if hashlib.sha256(Path(events[key]).read_bytes()).hexdigest() != events['sha256'][key]:
            raise ValueError('Completed edit uses changed observed source event reference')
    if record['plan_sha256'] != hashlib.sha256(Path(plan).read_bytes()).hexdigest():
        raise ValueError('Completed edit belongs to an obsolete plan')


def seal_clip_velocities(path,contract):
    """Do not derive a fictional velocity across a removed standing interval."""
    from somaforge_core.kinematics import angular_velocity_wxyz,body_velocities_from_pose
    with np.load(path,allow_pickle=True) as z:arrays={k:z[k].copy() for k in z.files}
    fps=float(arrays['fps']);q=arrays['joint_pos']
    arrays['joint_vel']=np.zeros((len(q),q.shape[1]-1),np.float32)
    arrays['body_lin_vel_w']=np.zeros_like(arrays['body_pos_w'])
    arrays['body_ang_vel_w']=np.zeros_like(arrays['body_pos_w'])
    for a,b in contract['continuous_clip_ranges']:
        if b-a<2:continue
        pose=q[a:b]
        arrays['joint_vel'][a:b]=np.concatenate((np.gradient(pose[:,:3],1/fps,axis=0),
            angular_velocity_wxyz(pose[:,3:7],1/fps),np.gradient(pose[:,7:],1/fps,axis=0)),axis=1)
        linear,angular=body_velocities_from_pose(arrays['body_pos_w'][a:b],arrays['body_quat_w'][a:b],fps)
        arrays['body_lin_vel_w'][a:b],arrays['body_ang_vel_w'][a:b]=linear,angular
    arrays['velocity_clip_contract_json']=np.array(json.dumps(dict(
        continuous_clip_ranges=contract['continuous_clip_ranges'],cross_seam_differentiation=False)))
    np.savez_compressed(path,**arrays)


@contextmanager
def generation_cache(folder):
    """Lease an existing official IK worker; only compilation is cached."""
    import fcntl
    config=folder.parent.parent/'ik_workers.json'
    previous=os.environ.get('SOMAFORGE_IK_WORKER_SOCKET')
    lease=None
    cache=folder/'collision_reference.npz'
    if config.exists():
        settings=json.loads(config.read_text())
        if settings.get('active'):
            while lease is None:
                for index,name in enumerate(settings['sockets']):
                    stream=(config.parent/f'ik_lease_{index}.lock').open('a')
                    try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError:stream.close();continue
                    lease=stream;os.environ['SOMAFORGE_IK_WORKER_SOCKET']=name
                    cache=config.parent/'source'/f'collision_reference_{index}.npz'
                    break
                if lease is None:time.sleep(.05)
    try:yield cache
    finally:
        if lease is not None:lease.close()
        if previous is None:os.environ.pop('SOMAFORGE_IK_WORKER_SOCKET',None)
        else:os.environ['SOMAFORGE_IK_WORKER_SOCKET']=previous


def serve_generation_cache(output,workers):
    """Own only dedicated generation workers, and close them after editing."""
    from generate_contact_aware_batch import _start_ik_worker,_worker_request,_batch_environment
    work=output/'generation_cache';work.mkdir(exist_ok=True)
    environment=_batch_environment(work);pool=[]
    try:
        for index in range(workers):
            pool.append(_start_ik_worker(index=index,environment=environment,work_root=work))
        dump(output/'ik_workers.json',dict(active=True,sockets=[p[0] for p in pool]))
        while True:
            try:stage=json.loads((output/'status.json').read_text())['stage']
            except (FileNotFoundError, json.JSONDecodeError):
                time.sleep(.1)
                continue
            if stage!='editing':break
            time.sleep(1)
    finally:
        dump(output/'ik_workers.json',dict(active=False))
        for name,process,log in pool:
            try:_worker_request(name,{'shutdown':True});process.wait(timeout=20)
            except Exception:
                if process.poll() is None:process.terminate();process.wait(timeout=20)
            log.close()


def generate(plan,folder,holds,crop_evidence,iterations, *, material_motion_residual_scale_m=DEFAULT_MATERIAL_RESIDUAL_SCALE_M,
             collision_refinements=DEFAULT_COLLISION_REFINEMENTS,
             environment_depth_residual_scale_m=DEFAULT_ENVIRONMENT_DEPTH_RESIDUAL_SCALE_M):
    from .rollout_authority import generate_contact_aware_pyroki_preview
    from .newton_direct_fk import canonicalize_motion_with_direct_newton_fk
    from .rebase_edit_plan import crop_events
    from compact_edited_stationary import compact
    from motion_edit.contact.plans import ContactEditPlan
    source_folder = Path(plan).parent.parent/'source'
    from somaforge_core.demonstration_events import observations
    from .event_acceptance import observed_source_contract, materialize_contract
    events=rows(source_folder/'events.jsonl')
    observed,_=observed_source_contract(observations(source_folder/'motion.npz', source_folder/'contacts.npz'),events)
    if events != observed:
        raise ValueError('Source events are not materialized from their own Newton observations; prepare a fresh source bundle')
    materialize_contract(source_folder/'motion.npz', source_folder/'contacts.npz',
        source_folder/'events.jsonl', source_folder/'keep_phases.json')
    event_reference={key:str(source_folder/name) for key,name in
        (('motion','motion.npz'),('labels','contacts.npz'),('events','events.jsonl'),('contract','event_contract.json'))}
    event_reference['sha256']={key:hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for key,path in event_reference.items()}
    authored = json.loads(Path(plan).read_text())
    evidence = {key: str(source_folder/name) for key, name in
        (('sites', 'loaded_sites.npz'), ('observations', 'observations.npz'), ('phases', 'keep_phases.json'))}
    evidence['sha256'] = {key: hashlib.sha256(Path(path).read_bytes()).hexdigest() for key, path in evidence.items()}
    evidence['residual_scale_m'] = material_motion_residual_scale_m
    authored.setdefault('metadata', {})['source_loaded_material_reference'] = evidence
    requested_objective = generation_objective(material_motion_residual_scale_m,
        environment_depth_residual_scale_m, collision_refinements)
    authored['metadata']['environment_depth_residual_scale_m'] = environment_depth_residual_scale_m
    loaded_plan = ContactEditPlan(**authored)
    folder.mkdir(parents=True,exist_ok=False)
    generated=folder/'generated.npz';motion=folder/'motion.npz'
    with generation_cache(folder) as cache:
        preview = generate_contact_aware_pyroki_preview(loaded_plan,output_motion_path=generated,
            intermediate_dir=folder/'work',ik_max_nfev=iterations,ik_q_acceleration_weight=8.,
            ik_collision_max_refinements=collision_refinements,
            ik_collision_reference_cache=cache)
        effective_objective = verify_effective_objective(preview.diagnostics, requested_objective)
        canonicalize_motion_with_direct_newton_fk(generated,motion)
    contract=compact(motion,folder/'cropped_seed.npz',holds,crop_evidence)
    cropped=folder/'motion_cropped.npz'
    canonicalize_motion_with_direct_newton_fk(folder/'cropped_seed.npz',cropped)
    seal_clip_velocities(cropped,contract)
    dump(folder/'compaction.json',contract)
    remapped=crop_events(events,np.asarray(contract['source_frames']))
    (folder/'events_cropped.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in remapped))
    result=dict(motion=str(motion),cropped_motion=str(cropped),events=str(folder/'events_cropped.jsonl'))
    dump(folder/'generation_complete.json',dict(**result, schema=GENERATION_SCHEMA,
        collision_refinements=collision_refinements,
        environment_depth_residual_scale_m=environment_depth_residual_scale_m,
        requested_objective=requested_objective, effective_objective=effective_objective,
        loaded_reference=evidence, event_reference=event_reference,
        plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest()))
    return result


def relabel_collection_group(root,out,checkpoint,item):
    """Use one exact native scene per terrain and reuse only completed labels."""
    key,(terrain,group)=item;scene=out/'scenes'/key[:16];scene.mkdir(exist_ok=True)
    manifest=json.loads((root/'runtime/current/manifests/wbt_single_climb_00.json').read_text())
    source=out/'source/motion.npz';digest=hashlib.sha256(source.read_bytes()).hexdigest()
    manifest['motion_files'][0].update(motion_file=str(source),motion_sha256=digest,source_file=str(source),source_sha256=digest)
    manifest['terrains'][0].update(terrain_file=str(terrain),terrain_sha256=key)
    dump(scene/'manifest.json',manifest)
    jobs=[dict(motion=str(out/'motions'/p.stem/(name+'.npz')),
               labels_output=str(out/'motions'/p.stem/(name+'_contacts.npz')))
          for p in group for name in ('motion','motion_cropped')]
    command=[sys.executable,str(root/'scripts/serve_newton_contact_queries.py'),
        '--checkpoint',str(checkpoint),'--motion-manifest',str(scene/'manifest.json'),
        '--binding',str(scene/'binding.json'),'--inspection-output',str(scene/'model.json'),
        '--query-nconmax','2048','--query-njmax','16384','--query-worlds','1','--device','cuda:0']
    if not (scene/'binding.json').exists():
        with (scene/'export.log').open('w') as log:
            subprocess.run(command+['--create-native-binding','--inspect-only'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    binding=json.loads((scene/'binding.json').read_text())
    pending=[]
    from somaforge_core.newton_contact_data import load_raw_contact_labels
    for job in jobs:
        label=Path(job['labels_output'])
        if not label.exists():pending.append(job);continue
        load_raw_contact_labels(Path(job['motion']),label)
        with np.load(label,allow_pickle=False) as z:
            semantics=json.loads(z['contact_semantics_json'].item())
        if semantics['provenance']['model_fingerprint']!=binding['model_fingerprint']:
            raise ValueError('Existing labels belong to another native terrain model')
    jobs=pending
    if jobs:
        dump(scene/'jobs.json',dict(model_fingerprint=binding['model_fingerprint'],jobs=jobs))
        with (scene/'relabel.log').open('w') as log:
            subprocess.run(command+['--relabel-jobs',str(scene/'jobs.json')],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    return key


def cropped_event_contract(data,events,fps,clips,*,source_policy):
    """Stable completion evidence cannot be borrowed across a removed interval."""
    from .event_acceptance import build_contract
    contract=build_contract(data['contact_part_mask'],data['contact_surface'],events,fps)
    # Candidate dropouts cannot relax the demonstrated event acceptance policy.
    contract['policy']=dict(source_policy)
    contract['policy_reference_clock']='full_native_source_motion'
    if (not clips or clips[0][0]!=0 or clips[-1][1]!=contract['frame_count']
        or any(a>=b for a,b in clips) or any(left[1]!=right[0] for left,right in zip(clips[:-1],clips[1:]))):
        raise ValueError('Continuous clips must partition the complete cropped timeline')
    blocks=[]
    for left,right in contract['retained_blocks']:
        for start,stop in clips:
            a,b=max(left,start),min(right,stop)
            if a<b:blocks.append([a,b])
    for action in contract['actions']:
        if not any(a<=action['start']<=action['end']<b for a,b in blocks):
            raise ValueError('Cropped action crosses a removed-interval seam')
    contract.update(retained_blocks=blocks,continuous_clip_ranges=clips,cross_seam_supervision_allowed=False)
    return contract


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate-plan',type=Path)
    parser.add_argument('--generate-folder',type=Path)
    parser.add_argument('--source-motion',type=Path)
    parser.add_argument('--source-labels',type=Path)
    parser.add_argument('--source-observations',type=Path)
    parser.add_argument('--original-state',type=Path)
    parser.add_argument('--events',type=Path)
    parser.add_argument('--old-events',type=Path)
    parser.add_argument('--plans',type=Path)
    parser.add_argument('--checkpoint',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--hold',nargs=2,type=int,action='append',required=True)
    parser.add_argument('--crop-evidence',type=Path)
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--label-workers',type=int,default=5)
    parser.add_argument('--iterations',type=int,default=25)
    parser.add_argument('--material-motion-residual-scale-m',type=float,default=DEFAULT_MATERIAL_RESIDUAL_SCALE_M,
        help='Soft loss normalization in meters; does not change any contact or slip budget')
    parser.add_argument('--environment-depth-residual-scale-m',type=float,default=DEFAULT_ENVIRONMENT_DEPTH_RESIDUAL_SCALE_M,
        help='Penetration loss normalization in meters; does not change solver contact margins')
    parser.add_argument('--collision-refinements',type=int,default=DEFAULT_COLLISION_REFINEMENTS)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--serve-generation-cache',action='store_true')
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    objective = generation_objective(args.material_motion_residual_scale_m,
        args.environment_depth_residual_scale_m, args.collision_refinements)
    if args.serve_generation_cache:
        serve_generation_cache(args.output,args.workers)
        return
    if args.generate_plan:
        generate(args.generate_plan,args.generate_folder,args.hold,args.crop_evidence,args.iterations,
            material_motion_residual_scale_m=args.material_motion_residual_scale_m,
            environment_depth_residual_scale_m=args.environment_depth_residual_scale_m,
            collision_refinements=args.collision_refinements)
        return
    for key in ('source_motion','source_labels','source_observations','original_state','events','old_events','plans','checkpoint','output'):
        if getattr(args,key) is None:parser.error('--'+key.replace('_','-')+' is required')
    if args.workers<1:raise ValueError('Positive worker count required')
    if args.label_workers<1:raise ValueError('Positive label worker count required')
    from somaforge_core.robot_assets import somaforge_root
    from somaforge_core.support_evidence import load_support_observations
    from somaforge_core.newton_contact_data import load_contact_labels
    from .event_acceptance import observed_source_contract,audit_events
    from .loaded_material_reference import export_sites,material_steps,compare_paths,remap_reference_sites,read_loaded_reference
    from .rebase_edit_plan import rebase_plan
    from .stationary_compaction import compact_timeline
    root=somaforge_root();out=args.output.resolve()
    script=root/'scripts/expand_source_preserving_augmentations.py'
    signature={key:hashlib.sha256(getattr(args,key).read_bytes()).hexdigest() for key in
               ('source_motion','source_labels','source_observations','original_state','events','old_events')}
    signature.update(holds=args.hold,iterations=args.iterations,material_motion_residual_scale_m=args.material_motion_residual_scale_m,
        objective=objective,
        plans={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.plans.glob('*.json'))},
        schema=GENERATION_SCHEMA)
    if not args.resume:
        out.mkdir(parents=True,exist_ok=False)
        (out/'source').mkdir();(out/'plans').mkdir();(out/'motions').mkdir();(out/'scenes').mkdir()
        dump(out/'inputs.json',signature)
        for path,name in ((args.source_motion,'motion.npz'),(args.source_labels,'contacts.npz'),
                          (args.source_observations,'observations.npz'),(args.events,'action_clock_input.jsonl')):
            shutil.copy2(path,out/'source'/name)
        source=out/'source/motion.npz';labels=out/'source/contacts.npz'
        from somaforge_core.demonstration_events import observations
        load_support_observations(source,out/'source/observations.npz');data=observations(source,labels)
        with np.load(source,allow_pickle=False) as z:q=z['joint_pos'];fps=float(z['fps'])
        events,contract=observed_source_contract(data,rows(args.events))
        (out/'source/events.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in events))
        frames,_,seams=compact_timeline(len(q),args.hold)
        from .rebase_edit_plan import crop_events
        crop_events(events,frames)  # A removed interval must never intersect an authored action.
        dump(out/'source/crop_policy.json',dict(holds=args.hold,source_frames=frames.tolist(),
            seam_frames=seams.tolist(),cross_seam_supervision_allowed=False))
        contract['provenance']={key:dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            for key,path in (('motion',source),('labels',labels),('action_clock',args.events))}
        with np.load(labels,allow_pickle=False) as z:
            contract['source_contact_semantics']=json.loads(z['contact_semantics_json'].item())
        dump(out/'source/event_contract.json',contract)
        phases=[dict(event_id=a['id'],start=a['start'],end=a['end'],part=r['part'],surface=r['surface'])
                for a in contract['actions'] for r in a['requirements'] if r['kind']=='keep']
        dump(out/'source/keep_phases.json',phases)
        sites=export_sites(source,out/'source/observations.npz',args.original_state,out/'source/loaded_sites.npz')
        source_steps=material_steps(source,sites,len(q));np.save(out/'source/loaded_steps.npy',source_steps)
        sample=json.loads(next(args.plans.glob('*.json')).read_text())
        terrain=sample['metadata']['source_terrain_mesh']
        with (out/'source/layer.log').open('w') as log:
            subprocess.run([sys.executable,str(root/'scripts/rebuild_newton_contact_layer.py'),
                '--motion',str(source),'--labels',str(labels),'--terrain',terrain,
                '--output',str(out/'source/contact_layer')],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    elif json.loads((out/'inputs.json').read_text())!=signature:
        raise ValueError('Resume inputs differ; choose a fresh output version')
    source=out/'source/motion.npz'
    with np.load(source,allow_pickle=False) as z:q=z['joint_pos']
    events=rows(out/'source/events.jsonl');previous=rows(args.old_events)
    new_anchors=rows(out/'source/contact_layer/anchors/climb_00.jsonl')
    surfaces=rows(out/'source/contact_layer/surfaces/climb_00.jsonl')
    for path in sorted(args.plans.glob('*.json')):
        if (out/'plans'/path.name).exists():continue
        old=json.loads(path.read_text());old_anchors=rows(Path(old['source_contact_layer'])/'anchors/climb_00.jsonl')
        plan=rebase_plan(old,old_anchors,new_anchors,previous,events,source=source,
            layer=out/'source/contact_layer',labels=out/'source/contact_layer/contact_labels/climb_00.npz',
            events=out/'source/events.jsonl',initial_q=q[0],surfaces=surfaces)
        from motion_edit.contact.plans import ContactEditPlan
        ContactEditPlan(**plan).validate(allow_free=True)
        dump(out/'plans'/path.name,plan)
    if args.prepare_only:return
    read_loaded_reference(source, out/'source/loaded_sites.npz', out/'source/observations.npz',
        out/'source/keep_phases.json')
    plans=sorted((out/'plans').glob('*.json'))
    lock=threading.Lock();completed=[];active={}
    def status(stage):
        dump(out/'status.json',dict(stage=stage,total=len(plans),completed=len(completed),
            active=active,items=completed,updated_at=time.time(),training_ready=False))
    def one(path):
        folder=out/'motions'/path.stem
        with lock:active[path.stem]=time.time();status('editing')
        started=time.time()
        if not (folder/'generation_complete.json').exists():
            if folder.exists():raise ValueError('Incomplete generation retained; inspect it before retrying')
            command=[sys.executable,str(script),'--generate-plan',str(path),'--generate-folder',str(folder),
                '--crop-evidence',str(out/'source/crop_policy.json'),'--iterations',str(args.iterations),
                '--material-motion-residual-scale-m',str(args.material_motion_residual_scale_m),
                '--environment-depth-residual-scale-m',str(args.environment_depth_residual_scale_m),
                '--collision-refinements',str(args.collision_refinements)]
            for hold in args.hold:command.extend(['--hold',*map(str,hold)])
            with (out/(path.stem+'.log')).open('w') as log:
                subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
        completed_generation=json.loads((folder/'generation_complete.json').read_text())
        validate_completed_generation(completed_generation, path, args.material_motion_residual_scale_m,
            environment_depth_residual_scale_m=args.environment_depth_residual_scale_m,
            collision_refinements=args.collision_refinements)
        with lock:
            completed.append(dict(motion_id=path.stem,seconds=time.time()-started));active.pop(path.stem);status('editing')
        return folder
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(one,path) for path in plans]
        for future in as_completed(futures):
            try:future.result()
            except Exception:
                for pending in futures:pending.cancel()
                status('generation_error')
                raise
    status('native_relabel')
    terrain_groups={}
    for plan in plans:
        terrain=Path(json.loads(plan.read_text())['metadata']['target_terrain_mesh']).resolve()
        key=hashlib.sha256(terrain.read_bytes()).hexdigest()
        terrain_groups.setdefault(key,(terrain,[]))[1].append(plan)
    def relabel_group(item):
        return relabel_collection_group(root,out,args.checkpoint,item)
    with ThreadPoolExecutor(max_workers=min(args.label_workers,len(terrain_groups))) as pool:
        for future in as_completed([pool.submit(relabel_group,item) for item in terrain_groups.items()]):future.result()
    status('acceptance')
    contract=json.loads((out/'source/event_contract.json').read_text())
    phases=json.loads((out/'source/keep_phases.json').read_text())
    with np.load(out/'source/loaded_sites.npz',allow_pickle=False) as z:sites={k:z[k] for k in z.files}
    source_steps=np.load(out/'source/loaded_steps.npy');results=[]
    source_loads=load_support_observations(out/'source/motion.npz',out/'source/observations.npz')
    for plan in plans:
        folder=out/'motions'/plan.stem;motion=folder/'motion.npz';contact=folder/'motion_contacts.npz'
        data=load_contact_labels(motion,contact);events,_=audit_events(contract,data['contact_part_mask'],data['contact_surface'])
        cropped=folder/'motion_cropped.npz';cropped_labels=folder/'motion_cropped_contacts.npz'
        cropped_data=load_contact_labels(cropped,cropped_labels)
        compaction=json.loads((folder/'compaction.json').read_text())
        crop_contract=cropped_event_contract(cropped_data,rows(folder/'events_cropped.jsonl'),
            contract['fps'],compaction['continuous_clip_ranges'],source_policy=contract['policy'])
        cropped_events,_=audit_events(crop_contract,cropped_data['contact_part_mask'],cropped_data['contact_surface'])
        comparisons=compare_paths(source_steps,material_steps(motion,sites,contract['frame_count']),phases,
            load_known=source_loads['load_known'][:-1],load_bearing=source_loads['load_bearing'][:-1])
        cropped_sites, cropped_known, cropped_bearing = remap_reference_sites(sites,
            compaction['source_frames'], load_known=source_loads['load_known'][:-1],
            load_bearing=source_loads['load_bearing'][:-1])
        source_frames = np.asarray(compaction['source_frames'])
        cropped_source_steps = source_steps[source_frames[:-1]].copy()
        cropped_source_steps[np.diff(source_frames) != 1] = np.nan
        cropped_phases = [dict(event_id=a['id'], start=a['start'], end=a['end'], part=r['part'], surface=r['surface'])
            for a in crop_contract['actions'] for r in a['requirements'] if r['kind']=='keep']
        cropped_comparisons = compare_paths(cropped_source_steps,
            material_steps(cropped, cropped_sites, len(source_frames)), cropped_phases,
            load_known=cropped_known, load_bearing=cropped_bearing)
        with np.load(contact,allow_pickle=False) as z:separation=json.loads(z['full_robot_separation_json'].item())
        summary=dict(terrain_penetration_mm=max(r['terrain_penetration_m'] for r in separation)*1000,
            self_penetration_mm=max(r['self_penetration_m'] for r in separation)*1000,
            invalid_penetrating_witnesses=sum(len(r['invalid_penetrating_witnesses']) for r in separation))
        report=dict(schema=GENERATION_SCHEMA,motion_id=plan.stem,
            motion=str(motion),contacts=str(contact),plan=str(plan),event_acceptance=events,
            cropped_event_acceptance=cropped_events,source_loaded_site_reference=comparisons,full_robot_separation=summary,
            cropped_source_loaded_site_reference=cropped_comparisons,
            material_motion_budget_passed=(None if any(r['motion_budget_passed'] is None for r in comparisons)
                                          else all(r['motion_budget_passed'] for r in comparisons)),
            source_added_motion_role='soft_regularizer_and_diagnostic_only',
            actual_edited_support='unknown_without_new_execution',training_ready=False,
            cropped_motion=str(folder/'motion_cropped.npz'),cropped_contacts=str(folder/'motion_cropped_contacts.npz'),
            cropped_events=str(folder/'events_cropped.jsonl'),compaction=str(folder/'compaction.json'))
        dump(folder/'acceptance.json',report);results.append(report)
    dump(out/'index.json',dict(schema='native_execution_edit_collection_v1',source=str(out/'source/motion.npz'),
        total=len(results),motion_files=results,cross_seam_supervision_allowed=False,training_ready=False))
    completed[:]=[dict(motion_id=r['motion_id'],event_checks_passed=r['event_acceptance']['passed']) for r in results]
    status('generation_complete')


if __name__=='__main__':main()
