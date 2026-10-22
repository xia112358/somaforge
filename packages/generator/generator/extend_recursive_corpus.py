"""Append complete train/validation endpoint chains without filtering failures."""
from collections import Counter
import math

import torch

from generator.next_interaction_heightmap_v2 import render_root_yaw_box_heightmaps
from generator.role_validity import validity_inputs
from somaforge_core.robot_assets import decode_robot_asset_json
from somaforge_core.newton_contacts import SCHEMA as CONTACT_SCHEMA
from somaforge_core.contact_face_selection import FACE_POLICY


def recursive_seed_records(records):
    seeds=[r for r in records if r['kind']=='demonstration' and
           r['split'] in ('train','validation') and r['current_frame']==0]
    if {r['split'] for r in seeds}!={'train','validation'}:
        raise ValueError('Recursive coverage requires train and validation seeds')
    return seeds


@torch.no_grad()
def extend_corpus(cfg,baseline,predictor,query,device):
    from generator.train_frozen_predictor_infiller import (evidence,dump,cpu_tree,
        audit_prediction,inference_contract,configured_acceptance,SCHEMA,load_published_infiller_input)
    from somaforge_core.published_data import resolve_published_path
    if cfg.source_corpus is not None:
        cfg.source_corpus = resolve_published_path(cfg.source_corpus)
    if cfg.source_corpus is None or cfg.corpus.exists():
        raise ValueError('Extension requires an immutable source and a fresh corpus path')
    source=load_published_infiller_input(cfg.source_corpus)
    decode_robot_asset_json(source['robot_asset_json'],context='recursive parent corpus')
    if source['schema']!=SCHEMA or source['predictor']!=evidence(baseline['checkpoint']['path']):
        raise ValueError('Parent corpus/Predictor mismatch')
    fingerprints={str(e['scene_id']):e['fp'] for e in query.workers.entries.values()}
    if source['scene_fingerprints']!=fingerprints: raise ValueError('Newton scenes changed')
    if source['summary']['label_policy']!=FACE_POLICY: raise ValueError('Stale primary-face semantics')
    seeds=recursive_seed_records(source['records'])
    if cfg.smoke:
        seeds=[next(r for r in seeds if r['split']==split) for split in ('train','validation')]
    frames=round(cfg.rollout_duration*50)+1
    if frames<4 or not math.isfinite(cfg.rollout_duration): raise ValueError('Invalid recursive duration')
    phase=torch.linspace(0,1,frames,device=device)[:,None]
    blend=phase.square()*(3-2*phase)
    limits=configured_acceptance(baseline['configuration_dict'])
    records=list(source['records']); audits=[]
    raw=cfg.report/'recursive_endpoints'; raw.mkdir(exist_ok=False)
    semantics=dict(contact_schema=CONTACT_SCHEMA,face_policy=FACE_POLICY,
        sampling='same-state fixed-q endpoint query; no integration',link_names=query.names,
        scenes={str(i):c.metadata for i,c in query.workers.tensor_clients.items()})
    # Metadata includes tensors; retain it losslessly rather than stringify them.
    torch.save(cpu_tree(semantics),raw/'contact_semantics.pt')
    for seed_number,seed in enumerate(seeds):
        q0=seed['q'][0].to(device)
        sid=int(seed['scene_id']); ids=torch.tensor([sid],device=device)
        sc={k:v[None].to(device) for k,v in seed['scene'].items()}
        for event in range(cfg.rollout_events):
            initial=query.observed(q0[None],ids)
            heightmap=render_root_yaw_box_heightmaps(*(sc[k].cpu().numpy() for k in
                ('box_center','box_rotation','box_half_extents','ground_height')),q0[None].cpu().numpy())
            prediction=predictor(current_q=q0[None],current_contact=initial['contact_part_mask'],
                current_anchor=initial['contact_position_w'],heightmap=torch.as_tensor(heightmap,device=device),
                **validity_inputs(predictor,q0[None],torch.as_tensor(heightmap,device=device),initial,
                    scan_provider=query.workers.scan, scene_ids=ids))
            if not bool(torch.isfinite(prediction.qpos).all()): raise ValueError('Nonfinite recursive endpoint')
            observed,audit=audit_prediction(predictor,query,prediction,q0,initial,sid,limits)
            contract,_=inference_contract(predictor,q0,prediction,initial,observed)
            q1=prediction.qpos[0]; aligned=q1.clone()
            aligned[3:7]=torch.where((q0[3:7]*q1[3:7]).sum()<0,-q1[3:7],q1[3:7])
            q=(1-blend)*q0+blend*aligned
            q[:,3:7]=torch.nn.functional.normalize(q[:,3:7],dim=-1)
            q[0]=q0; q[-1]=q1
            # These arrays store only endpoint/persistent intent. They are not
            # observed interior contacts. The unified objective ignores unknown
            # generated timing and never uses these absent material witnesses.
            active=torch.zeros(frames,6,dtype=torch.bool,device=device)
            active[0]=contract['start_contact']; active[-1]=contract['end_contact']
            surface=torch.full((frames,6),-1,device=device,dtype=torch.long)
            surface[0]=contract['start_surface']; surface[-1]=contract['end_surface']
            record=dict(q=q,active=active,surface=surface,material=q.new_full((frames,6,3),float('nan')),
                material_link=torch.full((frames,6),-1,device=device,dtype=torch.long),
                margin=q.new_full((frames,6),float('nan')),duration=q.new_tensor((frames-1)/50),
                scene=seed['scene'],scene_id=seed['scene_id'],contract=contract,kind='predictor_recursive',
                split=seed['split'],motion_id=seed['motion_id'],sample_id=seed['sample_id'],
                current_frame=event*(frames-1),target_frame=(event+1)*(frames-1),
                chain_id=f"recursive_unfiltered_{seed['motion_id']}",
                intent_timing='boundaries and same-surface keep only; interior timing unknown',
                endpoint_audit=audit,material_evidence='unknown; fresh unified geometry used during training')
            records.append(cpu_tree(record))
            row=dict(split=seed['split'],motion_id=seed['motion_id'],event=event,**audit); audits.append(row)
            torch.save(dict(start_q=q0.cpu(),end_q=q1.cpu(),initial=cpu_tree(initial),observed=cpu_tree(observed),
                contract=cpu_tree(contract),audit=row),raw/f"motion_{seed['motion_id']:03d}_event_{event:03d}.pt")
            q0=q1.detach().clone()  # Every ordinary failure is fed back unchanged.
        progress=dict(stage='recursive_corpus',seeds=seed_number+1,total_seeds=len(seeds),
            events=len(audits),rejected=sum(not a['accepted'] for a in audits))
        dump(cfg.report/'extension_progress.json',progress)
        print(__import__('json').dumps(progress),flush=True)
    corpus=dict(source,records=records,parent_corpus=evidence(cfg.source_corpus),
        extension=dict(schema='unfiltered_train_validation_recursion_v1',events=cfg.rollout_events,
            duration_s=(frames-1)/50,seeds=[dict(split=r['split'],motion_id=r['motion_id']) for r in seeds],
            test_records_added=0,ordinary_failure_behavior='record_and_continue',smoke=cfg.smoke,
            raw_evidence=str(raw.resolve())),summary=dict(source['summary'],
            counts=dict(Counter(f"{r['split']}/{r['kind']}" for r in records))))
    cfg.corpus.parent.mkdir(parents=True,exist_ok=True)
    torch.save(corpus,cfg.corpus)
    dump(cfg.report/'extension_audits.json',audits)
    dump(cfg.report/'corpus_summary.json',dict(corpus['summary'],extension=corpus['extension']))
    return corpus
