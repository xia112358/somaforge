"""Own five dedicated fixed-q workers; validate all demonstration endpoints.

No training or integration. Only subprocesses created here are terminated.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import torch
from somaforge_core.newton_scene_router import NewtonSceneRouter
from somaforge_core.newton_contact_query import query_contacts
from somaforge_core.contact_face_selection import select_contact_pairs
from climb00_pipeline.neural_infiller import CanonicalG1ForwardKinematics
from climb00_pipeline.newton_witness_loss import query_local_distances, selected_contact_cost
from somaforge_core.newton_contacts import triangle_distance_squared

ROOT=Path('tmp/newton_scene_router_v1')
CHECKPOINT='runtime/current/holosoma/logs/WholeBodyTracking/20260727_085520-g1_29dof_wbt_single_climb00_completionema_horizon50_ncon160_from4k_to10k-locomotion/model_06000.pt'


def save(path,value):path.write_text(json.dumps(value,indent=2))


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--capture-contact-sources',action='store_true')
    args=parser.parse_args()
    torch.set_num_threads(1)
    root=Path('tmp/newton_contact_sources_v1') if args.capture_contact_sources else ROOT
    output=root/str(time.time_ns());output.mkdir(parents=True)
    manifest=json.loads(Path('tmp/temporal207_training_v2_ready/manifest.json').read_text())
    entries=manifest['motion_files'];fingerprints=[];groups={}
    for i,entry in enumerate(entries):
        with np.load(entry['newton_contact_file'],allow_pickle=False) as z:
            sem=json.loads(z['contact_semantics_json'].item())
        fp=sem['scene']['model_fingerprint'];fingerprints.append(fp)
        groups.setdefault(fp,[]).append(i)
    template=json.loads(Path('tmp/paired_surface_v1/recursive_best150/worker_manifest.json').read_text())
    routes={fp:f'http://127.0.0.1:{8110+i}' for i,fp in enumerate(groups)}
    config=dict(schema='newton_native_scene_routes_v1',routes=routes,workers=3)
    save(output/'routes.json',config)
    os.environ['SOMAFORGE_NEWTON_SCENE_ROUTES']=str((output/'routes.json').resolve())
    os.environ['SOMAFORGE_CONTACT_SOURCE_AUDIT_DIR']=str((output/'source_equivalence_failures').resolve())
    workers=[];streams=[]
    try:
        for i,(fp,indices) in enumerate(groups.items()):
            directory=output/f'scene_{i}';directory.mkdir()
            entry=entries[indices[0]];plan=json.loads(Path(entry['edit_plan_file']).read_text())
            motion=Path(entry['motion_file']);terrain=Path(plan['metadata']['target_terrain_mesh'])
            spec=copy.deepcopy(template);row=spec['motion_files'][0]
            digest=hashlib.sha256(motion.read_bytes()).hexdigest()
            row.update(source_file=str(motion),motion_file=str(motion),source_sha256=digest,motion_sha256=digest)
            spec['bootstrap_motion']=str(motion)
            spec['terrains'][0].update(terrain_file=str(terrain),terrain_sha256=hashlib.sha256(terrain.read_bytes()).hexdigest())
            save(directory/'manifest.json',spec)
            log=(directory/'worker.log').open('w');streams.append(log)
            command=[sys.executable,'scripts/serve_newton_contact_queries.py','--checkpoint',CHECKPOINT,
                '--motion-manifest',str(directory/'manifest.json'),'--binding',str(directory/'binding.json'),
                '--inspection-output',str(directory/'model.json'),'--create-native-binding',
                '--query-nconmax','2048','--query-njmax','16384','--port',str(8110+i),'--device','cuda:0']
            if args.capture_contact_sources:command.append('--capture-contact-sources')
            workers.append(subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT))
        deadline=time.monotonic()+180
        while True:
            if any(p.poll() is not None for p in workers):raise RuntimeError('Query worker exited; see worker logs')
            ready=sum('"ready": true' in (output/f'scene_{i}/worker.log').read_text() for i in range(len(workers)))
            if ready==len(workers):break
            if time.monotonic()>deadline:raise TimeoutError('Query worker startup timeout')
            print(json.dumps(dict(status='starting_workers',ready=ready,total=len(workers),output=str(output))),flush=True)
            time.sleep(5)
        for i,fp in enumerate(groups):
            actual=json.loads((output/f'scene_{i}/model.json').read_text())['model_fingerprint']
            if actual!=fp:raise ValueError('Initialized worker differs from original scene fingerprint')
        corpus=torch.load('tmp/paired_surface_v1/paired_corpus/corpus.pt',map_location='cpu',weights_only=False)
        for sequence,entry in zip(corpus['sequences'],entries):
            if Path(sequence['source']).resolve()!=Path(entry['motion_file']).resolve():
                raise ValueError('Corpus/manifest sequence mismatch')
        records=[r for r in corpus['records'] if r['supervision_kind']=='demonstration']
        fk=CanonicalG1ForwardKinematics();reports=[];started=time.monotonic()
        # Every corpus demonstration endpoint, including the per-motion initial
        # state records. Mixed batches exercise the scatter-back route.
        with torch.no_grad():
            for first in range(0,len(records),64):
                batch=records[first:first+64]
                q=torch.stack([r['base'][-1] for r in batch])
                fp=torch.tensor([list(bytes.fromhex(fingerprints[r['sequence']])) for r in batch],dtype=torch.uint8)
                rows,result=query_local_distances(fk,q,fingerprints=fp)
                active=torch.stack([r['contract']['active_contact'] for r in batch]).bool()
                surface=torch.stack([r['contract']['contact_surface'] for r in batch]).long()
                cost,missing,realized=selected_contact_cost(q,rows,active,surface)
                for j,r in enumerate(batch):
                    selected=select_contact_pairs([result['pairs'][j]],result['surface_catalog_by_sample'][j])
                    observed=np.asarray(selected['contact_part_mask'][0],bool)
                    osurface=np.asarray(selected['contact_surface'][0])
                    desired=active[j].numpy();ds=surface[j].numpy()
                    reports.append(dict(sequence=r['sequence'],event=r['event'],frame=r['last'],
                        intended=int(desired.sum()),realized=int(realized[j].sum()),
                        missing_pairs=int(missing[j].sum()),contact_cost=float(cost[j].sum()),
                        exact_topology=bool(np.array_equal(observed,desired) and np.array_equal(osurface[desired],ds[desired])),
                        extra_parts=np.flatnonzero(observed&~desired).tolist(),
                        missing_parts=np.flatnonzero(desired&~realized[j].numpy()).tolist()))
                    if args.capture_contact_sources:
                        source_pairs=[]
                        for pair in result['pairs'][j]:
                            source=pair['contact_source']
                            if source['status']!='mesh_triangle' or not source['same_pass_source_mapping_verified']:
                                raise ValueError('Unverified or unsupported actual contact source')
                            source_pairs.append(dict(pair,surface=source['primary_surface'],
                                surface_candidates=source['incident_surface_candidates']))
                        selected_source=select_contact_pairs([source_pairs],result['surface_catalog_by_sample'][j])
                        sa=np.asarray(selected_source['contact_part_mask'][0],bool)
                        ss=np.asarray(selected_source['contact_surface'][0])
                        reports[-1].update(source_exact_topology=bool(np.array_equal(sa,desired)
                            and np.array_equal(ss[desired],ds[desired])),same_pass_source_mapping_verified=True,
                            source_missing_parts=np.flatnonzero(desired&(~sa|(ss!=ds))).tolist(),
                            source_extra_parts=np.flatnonzero(sa&~desired).tolist())
                        if not reports[-1]['source_exact_topology']:
                            reports[-1]['source_pairs']=source_pairs
                    if not reports[-1]['exact_topology']:
                        with np.load(entries[r['sequence']]['newton_contact_file'],allow_pickle=False) as z:
                            saved=json.loads(z['task_contact_pairs_json'].item())[r['last']]
                        reports[-1]['saved_pairs']=saved
                        reports[-1]['queried_pairs']=result['pairs'][j]
                        reports[-1]['witness_face_distances']=[]
                        for pair in result['pairs'][j]:
                            if pair['part'] not in reports[-1]['missing_parts']:continue
                            distances=[]
                            for face in result['surface_catalog_by_sample'][j]:
                                distances.append(dict(surface=face['surface'],normal_w=face['normal_w'],
                                    witness_gap_m=float(np.sqrt(triangle_distance_squared(
                                        pair['terrain_position_w'],face['triangles_w']).min()))))
                            reports[-1]['witness_face_distances'].append(dict(robot_shape=pair['robot_shape'],
                                terrain_position_w=pair['terrain_position_w'],
                                nearest=sorted(distances,key=lambda x:x['witness_gap_m'])[:3]))
                save(output/'endpoints_progress.json',dict(done=len(reports),total=len(records),elapsed=time.monotonic()-started))
                if args.capture_contact_sources:save(output/'endpoints_partial.json',reports)
                print(json.dumps(dict(status='endpoints',done=len(reports),total=len(records),elapsed=time.monotonic()-started)),flush=True)
        save(output/'endpoints.json',reports)
        summary=dict(motions=len(entries),scenes=len(groups),endpoints=len(reports),
            intended=sum(r['intended'] for r in reports),realized=sum(r['realized'] for r in reports),
            exact_topology=sum(r['exact_topology'] for r in reports),
            missing_pairs=sum(r['missing_pairs'] for r in reports),max_contact_cost=max(r['contact_cost'] for r in reports),
            elapsed_seconds=time.monotonic()-started,training=False,output=str(output))
        if args.capture_contact_sources:
            summary.update(source_exact_topology=sum(r['source_exact_topology'] for r in reports),
                same_pass_verified_endpoints=sum(r['same_pass_source_mapping_verified'] for r in reports),
                source_missing_contacts=sum(len(r['source_missing_parts']) for r in reports),
                source_extra_contacts=sum(len(r['source_extra_parts']) for r in reports))
        save(output/'summary.json',summary);print(json.dumps(summary),flush=True)
        if args.capture_contact_sources:
            env=dict(os.environ,SOMAFORGE_NEWTON_CONTACT_URL=routes[fingerprints[4]],
                SOMAFORGE_OBJECTIVE_SMOKE_OUTPUT=str((output/'objective_smoke.json').resolve()))
            subprocess.run([sys.executable,'tmp/newton_witness_loss_v3/smoke_objective.py'],env=env,check=True)
        gradient_audit(records,entries,fingerprints,routes,output)
    finally:
        for p in workers:
            if p.poll() is None:p.terminate()
        for p in workers:
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        for stream in streams:stream.close()


def gradient_audit(records,entries,fingerprints,routes,output):
    """Re-query previous outliers, retaining witnesses and repeated-q noise."""
    prior=json.loads(Path('tmp/newton_witness_loss_v3/audit_0.001.json').read_text())
    outliers=[r for r in prior['derivatives'] if r['abs_error']>.01]
    bank={r['event']:r for r in records if r['sequence']==4}
    endpoint=routes[fingerprints[4]];report=[]
    def key(p):return [p[k] for k in ('part','robot_shape','terrain_shape','surface')]
    for event in sorted({r['event'] for r in outliers}):
        q=bank[event]['base'][-1].numpy();queries=[q.copy() for _ in range(4)];labels=[('repeat',0,0)]*4
        for eps in (1e-4,1e-3,1e-2):
            for axis in range(3):
                for sign in (1,-1):
                    value=q.copy();value[axis]+=sign*eps;queries.append(value);labels.append((eps,axis,sign))
        result=query_contacts(np.stack(queries),None,endpoint=endpoint)
        for old in (r for r in outliers if r['event']==event):
            matches=[[p for p in row if key(p)==old['pair']] for row in result['candidate_pairs']]
            chosen=[min(row,key=lambda p:p['dist']) if row else None for row in matches]
            repeated=[p['dist'] for p in chosen[:4] if p is not None]
            item=dict(previous=old,repeat_distance_range_m=max(repeated)-min(repeated) if repeated else None,steps=[])
            for eps in (1e-4,1e-3,1e-2):
                plus=chosen[labels.index((eps,old['axis'],1))];minus=chosen[labels.index((eps,old['axis'],-1))]
                if plus is None or minus is None:item['steps'].append(dict(epsilon=eps,missing_pair=True));continue
                numerical=(plus['dist']-minus['dist'])/(2*eps)
                item['steps'].append(dict(epsilon=eps,numerical=numerical,
                    abs_error=abs(numerical-old['analytic']),plus=plus,minus=minus,
                    normal_change=float(np.linalg.norm(np.array(plus['normal_w'])-minus['normal_w']))))
            report.append(item)
    save(output/'gradient_outliers.json',report)
    print(json.dumps(dict(status='gradient_outliers_complete',cases=len(report))),flush=True)


if __name__=='__main__':main()
