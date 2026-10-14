"""Freeze the latest Predictor, train the historical direct endpoint decoder.

All contact observations are same-state Newton queries with the shared primary
face selection. Predicted contact windows are intentions, never task labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import nullcontext
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import time

import numpy as np
import torch

from generator.direct_infiller import (SCHEMA, DirectInfiller, collate, decode_batch,
    trajectory_objective, contact_timing_metrics, continuity_metrics, seam_metrics,
    transfer_constraints,regularized_motion_objective, load_infiller, prepare_frame_prediction,
    frame_objective, generate_segment)
from generator.predictor_architecture import load_position_predictor
from generator.depth_observation import predictor_observation
from generator.training_data import prepare, split_name
from generator.scene_workers import Workers
from generator.planned_contact_predictor import plan_points_in_pose_frame, audit_intended_surfaces
from contact_solver.device_contact_objective import DeviceWitnessRows, acceptance, first_minimum
from contact_solver.native_contact_position import native_position_statistics
from contact_solver.interaction_acceptance import configured_acceptance, acceptance_contract
from generator.trajectory_budget import densify_qpos
from somaforge_core.robot_assets import encode_robot_asset_json, decode_robot_asset_json
from somaforge_core.contact_face_selection import select_contact_pairs, FACE_POLICY
from somaforge_core.newton_contact_data import load_raw_contact_labels, require_current_newton_manifest
from somaforge_core.g1_kinematics import G1_29DOF_JOINT_ORDER
from somaforge_core.motion_contracts import BODY_NAMES, CONTACT_PARTS
from somaforge_core.newton_contacts import constraint_decision, SCHEMA as NEWTON_CONTACT_SCHEMA
from somaforge_core.newton_contact_tensors import validate_observed
from somaforge_core.contact_schema import CONTACT_BODY_NAMES_BY_PART


@dataclass
class Config:
    baseline: Path = Path('baselines/predictor_v1_latest_20261010/baseline.json')
    corpus: Path = Path('runtime/current/motions/infiller_latest_predictor_20261010/corpus.pt')
    output: Path = Path('runtime/current/models/generator/direct_infiller_latest_predictor_20261010')
    report: Path = Path('tmp/direct_infiller_latest_predictor_20261010')
    mode: str = 'all'  # all, build, train, evaluate, rollout
    checkpoint: Path | None = None
    steps: int = 5000
    batch_size: int = 32
    frame_budget: int = 1024
    learning_rate: float = .001
    evaluation_every: int = 250
    query_worlds: int = 16
    query_batch_size: int = 128
    seed: int = 20260908
    dense_factor: int = 10
    solid_training_frames: int = 4
    demo_fraction: float = .5
    training_source: str = 'mixed'  # mixed, demonstration_only
    evaluation_splits: tuple[str, ...] = ('train', 'validation', 'test')
    maximum_samples: int | None = None  # Explicit smoke-only cap per split.
    recursive_events: int = 15
    rollout_events: int = 30
    rollout_duration: float = 1.
    rollout_motion_id: int = 0
    objective: str = 'historical'  # historical, unified
    initialization_checkpoint: Path | None = None
    pose_weight: float = 10.
    physics_weight: float = 1.
    smoothness_weight: float = 1.
    feasible_budget_ratio: float = 1.5
    smoke: bool = False
    source_corpus: Path | None = None
    seam_weight: float = 0.
    rollout_predictor_checkpoint: Path | None = None
    predict_frames: bool = False
    frame_training: str = 'decoupled'  # decoupled expert-only timing, joint legacy recipe
    frame_weight: float = 10.
    frame_efficiency_weight: float = .02
    frame_warmup_steps: int = 3000
    maximum_segment_frames: int = 4096  # Resource guard: fail, never clip a prediction.
    rollout_timing: str = 'model'  # model, fixed (explicit counterfactual only)
    boundary_velocity: bool = False
    conditional_boundary: bool = False
    residual_extension: bool = False
    witnessed_budgets: bool = False
    velocity_warmup_steps: int = 3000
    velocity_weight: float = 1.
    efficient_training: bool = False
    profile_repeats: int = 3


def evidence(path):
    path = Path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path.resolve()), sha256=digest)


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def cpu_tree(value):
    if isinstance(value, torch.Tensor): return value.detach().cpu()
    if isinstance(value, dict): return {k:cpu_tree(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)): return [cpu_tree(v) for v in value]
    return value


def checkpoint_corpus_matches(saved,corpus,path):
    if saved['corpus']==evidence(path):return True
    parent=corpus.get('parent_corpus')
    return parent==saved['corpus'] and evidence(parent['path'])==parent


class NativeQueries:
    def __init__(self, workers, fk, batch_size):
        self.workers, self.fk, self.batch_size = workers, fk, batch_size
        self.names = tuple(workers.tensor_router.link_names)

    def observed(self, q, scene_ids):
        observed = self.workers.tensor_router(q.detach(), scene_ids)
        validate_observed(observed)
        return observed

    def depths(self, q, scene_ids, observed=None):
        if observed is None: observed = self.observed(q,scene_ids)
        rows = DeviceWitnessRows(self.fk, q, observed)
        p = observed['pairs']
        native = q.new_zeros(len(q),2)
        valid = p['full_kind'] >= 0
        group = p['sample'][valid]*2+p['full_kind'][valid]
        native.flatten().scatter_reduce_(0,group,(-p['dist'][valid]).relu(),reduce='amax',include_self=True)
        solid = self.workers.solid_router(self.fk,q,scene_ids)
        _, invalid = rows.full_body()
        return torch.maximum(native,solid.depths()), invalid, solid

    @torch.no_grad()
    def timeline(self, q, scene_id, audit_dir=None):
        masks, surfaces, depth, invalid = [], [], [], []
        for first in range(0,len(q),self.batch_size):
            chunk=q[first:first+self.batch_size]
            ids=torch.full((len(chunk),),scene_id,device=q.device,dtype=torch.long)
            observed=self.observed(chunk,ids)
            depths,bad,solid=self.depths(chunk,ids,observed)
            masks.append(observed['contact_part_mask'].cpu())
            surfaces.append(observed['contact_surface'].cpu())
            depth.append(depths.cpu()); invalid.append(bad.cpu())
            if audit_dir is not None:
                audit_dir.mkdir(parents=True,exist_ok=True)
                torch.save(dict(first=first,q=chunk.cpu(),observed=cpu_tree(observed),
                    solid_pairs=cpu_tree(solid.pair)),audit_dir/f'query_{first:06d}.pt')
        return dict(mask=torch.cat(masks),surface=torch.cat(surfaces),depth=torch.cat(depth),invalid=torch.cat(invalid))


def bind_materials(fk,q,observed,names,active=None,surface=None):
    p=observed['pairs']; part=p['part'].clamp(0,5)
    eligible=p['eligible']
    if active is not None:
        eligible=eligible & active[p['sample'],part] & (surface[p['sample'],part]==p['primary_surface'])
    chosen,present=first_minimum(p['dist'],p['sample']*6+part,eligible,len(q)*6)
    link=torch.cat((p['body_link1'],p['body_link1'].new_full((1,),-1)))[chosen].reshape(len(q),6)
    point=torch.cat((p['geometry_point1_w'].to(q),q.new_zeros(1,3)))[chosen].reshape(len(q),6,3)
    margin=torch.cat((p['includemargin'].to(q),q.new_full((1,),float('nan'))))[chosen].reshape(len(q),6)
    position,rotation=fk.link_poses(q,names)
    batch=torch.arange(len(q),device=q.device)[:,None]
    local=torch.einsum('bpji,bpj->bpi',rotation[batch,link.clamp_min(0)],point-position[batch,link.clamp_min(0)])
    local=torch.where(present.reshape(len(q),6,1),local,0)
    return local,link,margin


def record_contract(fk,q0,q1,start_active,end_active,start_surface,end_surface,start_anchor,end_anchor,role):
    with torch.no_grad():
        pos,rot=fk.link_poses(q1[None],BODY_NAMES[1:7])
        local=torch.einsum('bpji,bpj->bpi',rot,end_anchor[None]-pos)[0]
    return dict(start_contact=start_active,end_contact=end_active,start_surface=start_surface,
        end_surface=end_surface,start_anchor=start_anchor,end_anchor=end_anchor,
        end_local_offset=local,keep=role==2,role=role)


def predicted_record(model,query,q0,prediction,initial,end,scene,scene_id,duration,template,chain_id):
    q1=prediction.qpos[0]
    c=prediction.conditioned_contact[0]
    points=plan_points_in_pose_frame(q0[None],prediction.conditioned_points_local)[0]
    surface=audit_intended_surfaces(points[None],c[None],end)[0]
    role=prediction.conditioned_role[0]
    count=max(4,round(duration*50)+1)
    phase=torch.linspace(0,1,count,device=q0.device)[:,None]
    blend=phase.square()*(3-2*phase)
    aligned=q1.clone()
    aligned[3:7]=torch.where((q0[3:7]*aligned[3:7]).sum()<0,-aligned[3:7],aligned[3:7])
    base=(1-blend)*q0+blend*aligned
    base[:,3:7]=torch.nn.functional.normalize(base[:,3:7],dim=-1)
    base[0]=q0; base[-1]=q1
    active_start=initial['contact_part_mask'][0]
    ss=initial['contact_surface'][0]
    anchors=initial['contact_position_w'][0]
    ea=end['contact_position_w'][0]
    contract=record_contract(model.fk,q0,q1,active_start,c,ss,surface,anchors,ea,role)
    start_mat,start_link,start_margin=bind_materials(model.fk,q0[None],initial,query.names)
    end_mat,end_link,end_margin=bind_materials(model.fk,q1[None],end,query.names,c[None],surface[None])
    persistent=(role==2) & active_start & c
    leaving=active_start & ~persistent
    arriving=c & ~persistent
    early=phase[:,0]<=.2; late=phase[:,0]>=.8
    active=persistent[None] | (early[:,None]&leaving[None]) | (late[:,None]&arriving[None])
    use_end=late[:,None]&arriving[None]
    surf=torch.where(use_end,surface[None],ss[None]).expand(count,-1)
    mat=torch.where(use_end[...,None],end_mat[0],start_mat[0]).expand(count,-1,-1)
    link=torch.where(use_end,end_link[0],start_link[0]).expand(count,-1)
    margin=torch.where(use_end,end_margin[0],start_margin[0]).expand(count,-1)
    if bool((active & ((link<0)|~torch.isfinite(margin)|(margin<=0))).any()):
        raise ValueError('Accepted predicted boundary lacks required material/margin')
    record=dict(q=base,active=active,surface=surf,material=mat,material_link=link,margin=margin,
        duration=q0.new_tensor((count-1)/50),scene=scene,scene_id=torch.tensor(scene_id,device=q0.device),
        contract=contract,kind='predictor_accepted',split=template['split'],motion_id=template['motion_id'],
        sample_id=template['sample_id'],current_frame=template['current_frame'],target_frame=template['target_frame'],
        chain_id=chain_id,intent_timing='historical declared leaving<=20%, arriving>=80%; not expert timing',
        original_duration_s=duration)
    return cpu_tree(record)


@torch.no_grad()
def audit_prediction(model,query,prediction,q0,initial,scene_id,limits):
    q=prediction.qpos
    ids=torch.tensor([scene_id],device=q.device)
    observed=query.observed(q,ids)
    points=plan_points_in_pose_frame(q0[None],prediction.conditioned_points_local)
    active=prediction.conditioned_contact
    surface=(prediction.conditioned_surface if prediction.conditioned_surface is not None
        else audit_intended_surfaces(points,active,observed))
    audit=acceptance(observed,active,surface)
    depth,invalid,_=query.depths(q,ids,observed)
    error,complete,count=native_position_statistics(model,query.workers.position_router,q,ids,
        points,active,surface,observed,regions=prediction.planned_regions)
    reasons=[]
    if not bool(audit['contact_accepted'][0]): reasons.append('actual_contact_plan')
    if not bool(active.any()): reasons.append('empty_intent')
    rms=float(error[0].sqrt())
    if not bool(complete[0]) or not math.isfinite(rms) or rms>.04: reasons.append('actual_region_position')
    if not bool(torch.isfinite(depth).all()) or float(depth.max())>limits.shallow_penetration_m:
        reasons.append('terrain_or_self_penetration')
    if bool(invalid.any()): reasons.append('invalid_native_normal')
    keep=prediction.conditioned_role==2
    same_relation = acceptance(initial, keep, surface)['realized']
    if bool((keep & ~same_relation).any()):
        reasons.append('keep_without_current_same_surface_contact')
    if bool(((q[:,7:]<model.fk.joint_lower-1e-6)|(q[:,7:]>model.fk.joint_upper+1e-6)).any()): reasons.append('joint_limits')
    return observed,dict(accepted=not reasons,reasons=reasons,depth_m=depth[0].tolist(),
        position_rms_m=rms if math.isfinite(rms) else None,position_complete=bool(complete[0]),
        contact_accepted=bool(audit['contact_accepted'][0]),observed_parts=int(count[0]))


def make_corpus(cfg,baseline,predictor,query,device):
    deps=baseline['dependencies']
    prep_cfg=argparse.Namespace(manifest=Path(deps['manifest']['path']),data_cache=Path(deps['data_cache']['path']),
        q_cache=Path(deps['q_cache']['path']),heightmap_supersample=1,mode='full')
    inputs,target,scenes,splits,samples,summary=prepare(predictor,prep_cfg,torch.device('cpu'))
    manifest=json.loads(prep_cfg.manifest.read_text())
    require_current_newton_manifest(manifest,context='Infiller source')
    names=query.names
    records=[]; by_sample={}; source_audit=[]
    sample_ids=set()
    for split,indices in splits.items():
        selected=indices.tolist()
        if cfg.maximum_samples is not None: selected=selected[:cfg.maximum_samples]
        sample_ids.update(selected)
    for motion_id,entry in enumerate(manifest['motion_files']):
        ids=[i for i,sample in enumerate(samples) if sample['motion_id']==motion_id and i in sample_ids]
        if not ids: continue
        with np.load(entry['motion_file'],allow_pickle=False) as z:
            decode_robot_asset_json(z['robot_asset_json'],context=entry['motion_file'])
            world=torch.tensor(z['joint_pos'],dtype=torch.float32)
            fps=float(z['fps'].reshape(-1)[0])
        if fps!=50: raise ValueError('Historical native-frame training requires actual 50Hz data')
        load_raw_contact_labels(entry['motion_file'],entry['newton_contact_file'],frame_count=len(world))
        with np.load(entry['newton_contact_file'],allow_pickle=False) as z:
            semantics=json.loads(z['contact_semantics_json'].item())
            raw=json.loads(z['contact_pairs_json'].item())
        # Explicitly rematerialize the current spatial selector, preserving the
        # raw source point pairs by immutable path/hash, with no old task cache.
        selected=select_contact_pairs(raw,semantics['scene']['surface_catalog'])
        mask=torch.tensor(selected['contact_part_mask'])
        surface=torch.tensor(selected['contact_surface'])
        anchors=torch.tensor(selected['contact_position_w'])
        pair_rows=selected['contact_pairs']
        materials=torch.zeros(len(world),6,3); links=torch.full((len(world),6),-1,dtype=torch.long)
        margins=torch.full((len(world),6),float('nan'))
        positions,rotations=predictor.fk.cpu().link_poses(world,names)
        for frame,pairs in enumerate(pair_rows):
            for part in range(6):
                match=[p for p in pairs if p['part']==part and p['surface']==int(surface[frame,part])]
                if not match: continue
                pair=min(match,key=lambda p:p['dist']-p['includemargin'])
                link=names.index(pair['body_name'])
                point=torch.tensor(pair['position_w'],dtype=torch.float32)
                materials[frame,part]=rotations[frame,link].T@(point-positions[frame,link])
                links[frame,part]=link; margins[frame,part]=pair['includemargin']
        for i in ids:
            sample=samples[i]; first,last=sample['current_frame'],sample['target_frame']
            q=world[first:last+1].clone(); ac=mask[first:last+1].clone(); sf=surface[first:last+1].clone()
            role=torch.where(ac[-1],3,0)
            keep=ac.all(0)&(sf==sf[-1]).all(0)&ac[-1]
            role[keep]=2
            starts=ac[1:] & ((~ac[:-1])|(sf[1:]!=sf[:-1]))
            role[starts.any(0)&ac[-1]&~keep]=1
            sc={k:v[i] for k,v in scenes.items()}
            origin,basis=target['newton_world_origin'][i],target['newton_world_basis'][i]
            sc=dict(box_center=origin+basis@sc['box_center'],box_rotation=basis@sc['box_rotation'],
                    box_half_extents=sc['box_half_extents'],ground_height=origin[2]+sc['ground_height'])
            height=round(float(sample['height']),8)
            scene_id=query.workers.entries[height]['scene_id']
            record=dict(q=q,active=ac,surface=sf,material=materials[first:last+1].clone(),
                material_link=links[first:last+1].clone(),margin=margins[first:last+1].clone(),
                duration=torch.tensor((last-first)/fps),scene=sc,scene_id=torch.tensor(scene_id),
                contract=record_contract(predictor.fk,q[0],q[-1],ac[0],ac[-1],sf[0],sf[-1],
                    anchors[first],anchors[last],role),kind='demonstration',split=split_name(height).split('_height')[0],
                motion_id=motion_id,sample_id=i,current_frame=first,target_frame=last,
                chain_id=f'demonstration_{motion_id}',intent_timing='own raw Newton 50Hz observations')
            if bool((ac & ((record['material_link']<0)|~torch.isfinite(record['margin'])|(record['margin']<=0))).any()):
                raise ValueError('Demonstration requires complete actual material/margin evidence')
            records.append(record); by_sample[i]=record
        source_audit.append(dict(motion=evidence(entry['motion_file']),labels=evidence(entry['newton_contact_file']),
            events=evidence(entry['event_segments_file']),selected_pairs=sum(map(len,pair_rows)),
            abnormal_pairs=sum(map(len,selected['abnormal_contact_pairs'])),sampling=semantics['sampling']))
        print(json.dumps(dict(stage='demonstration_build',motion=motion_id,segments=len(records))),flush=True)
    predictor.to(device)
    query.fk=predictor.fk
    audits=[]
    endpoint_raw=cfg.report/'endpoint_raw_newton'; endpoint_raw.mkdir(exist_ok=False)
    for i,record in sorted(by_sample.items()):
        q0=record['q'][0].to(device)
        sc={k:v[None].to(device) for k,v in record['scene'].items()}
        ids=record['scene_id'].reshape(1).to(device)
        with torch.no_grad():
            initial=query.observed(q0[None],ids)
            prediction=predictor(**predictor_observation(predictor,q0[None],initial,sc,ids,query.workers))
            observed,audit=audit_prediction(predictor,query,prediction,q0,initial,int(ids[0]),
                                            configured_acceptance(baseline['configuration_dict']))
            audits.append(dict(sample_id=i,split=record['split'],**audit))
            torch.save(dict(sample_id=i,q=prediction.qpos.detach().cpu(),observed=cpu_tree(observed)),
                       endpoint_raw/f'isolated_{i:05d}.pt')
            if audit['accepted']:
                records.append(predicted_record(predictor,query,q0,prediction,initial,observed,
                    record['scene'],int(ids[0]),float(record['duration']),record,f'isolated_{i}'))
        if len(audits)%100==0: print(json.dumps(dict(stage='endpoint_build',attempts=len(audits),accepted=sum(a['accepted'] for a in audits))),flush=True)
    # True generated chains supply shared endpoints for seam assessment. A
    # failed endpoint terminates its chain; it is never projected or retried.
    by_motion=defaultdict(list)
    for r in by_sample.values(): by_motion[r['motion_id']].append(r)
    chain_audits=[]
    for motion_id,templates in sorted(by_motion.items()):
        templates.sort(key=lambda r:r['current_frame'])
        q0=templates[0]['q'][0].to(device)
        for index,template in enumerate(templates[:cfg.recursive_events]):
            scene_id=int(template['scene_id']); sc={k:v[None].to(device) for k,v in template['scene'].items()}
            with torch.no_grad():
                initial=query.observed(q0[None],torch.tensor([scene_id],device=device))
                prediction=predictor(**predictor_observation(predictor,q0[None],initial,sc,
                    torch.tensor([scene_id],device=device),query.workers))
                observed,audit=audit_prediction(predictor,query,prediction,q0,initial,scene_id,
                    configured_acceptance(baseline['configuration_dict']))
                chain_audits.append(dict(motion_id=motion_id,event=index,split=template['split'],**audit))
                torch.save(dict(motion_id=motion_id,event=index,q=prediction.qpos.detach().cpu(),observed=cpu_tree(observed)),
                           endpoint_raw/f'chain_{motion_id:03d}_{index:02d}.pt')
                if not audit['accepted']: break
                records.append(predicted_record(predictor,query,q0,prediction,initial,observed,template['scene'],
                    scene_id,float(template['duration']),template,f'predictor_chain_{motion_id}'))
                q0=prediction.qpos[0].detach()
    for r in records:
        for key in ('material','margin'):
            # Unknown inactive rows remain explicitly masked; finite storage
            # prevents inactive NaNs poisoning arithmetic in a masked loss.
            if key=='margin': r[key]=torch.where(r['active'],r[key],torch.ones_like(r[key]))
    summary=dict(schema=SCHEMA,counts=dict(Counter(f"{r['split']}/{r['kind']}" for r in records)),
        endpoint_attempts=len(audits),endpoint_accepted=sum(a['accepted'] for a in audits),
        rejection_reasons=dict(Counter(reason for a in audits for reason in a['reasons'])),
        chain_attempts=len(chain_audits),chain_accepted=sum(a['accepted'] for a in chain_audits),
        label_policy=FACE_POLICY,sampling='fixed_q_forward_no_integration',
        dynamic_support='unknown; no executed loads',demonstration_quality_filtering=False,
        predicted_intents_are_labels=False,scope='same original source height holdout; no independent-source claim',
        smoke=cfg.smoke,source_integrity_summary=summary)
    corpus=dict(schema=SCHEMA,robot_asset_json=encode_robot_asset_json(),records=records,summary=summary,
        source_audit=source_audit,endpoint_audits=audits,chain_audits=chain_audits,
        predictor=evidence(baseline['checkpoint']['path']),baseline=evidence(cfg.baseline),
        scene_fingerprints={str(e['scene_id']):e['fp'] for e in query.workers.entries.values()},
        link_names=names)
    cfg.corpus.parent.mkdir(parents=True,exist_ok=True)
    if cfg.corpus.exists(): raise FileExistsError(cfg.corpus)
    torch.save(corpus,cfg.corpus)
    dump(cfg.report/'corpus_summary.json',summary)
    dump(cfg.report/'endpoint_audits.json',dict(isolated=audits,chains=chain_audits))
    return corpus


def batches(records,cfg,rng=None):
    buckets=defaultdict(list)
    for i,r in enumerate(records): buckets[(len(r['q']),r['kind'])].append(i)
    result=[]
    for (length,_),indices in buckets.items():
        if rng is not None: rng.shuffle(indices)
        size=min(cfg.batch_size,max(1,cfg.frame_budget//length))
        result.extend([indices[i:i+size] for i in range(0,len(indices),size)])
    if rng is not None: rng.shuffle(result)
    return result


def unified_objective(model,b,q,limits,query,cfg):
    """Shared Predictor physics on every native frame and inter-frame midpoint.

    Midpoint constraints are intentions inherited only when neighboring labels
    agree. Contact truth always comes from fresh same-state Newton queries.
    """
    from contact_solver.contact_regions import unified_region_objective
    active,surface,release=transfer_constraints(b)
    mid_active=active[:,:-1] & active[:,1:] & (surface[:,:-1]==surface[:,1:])
    mid_surface=torch.where(mid_active,surface[:,:-1],-1)
    mid_release=release[:,:-1] & release[:,1:]
    def interleave(native,mid):
        return torch.cat((torch.stack((native[:,:-1],mid),2).flatten(1,2),native[:,-1:]),1)
    active=interleave(active,mid_active).flatten(0,1)
    surface=interleave(surface,mid_surface).flatten(0,1)
    release=interleave(release,mid_release).flatten(0,1)
    physical_q=densify_qpos(q,2)
    ids=b['scene_id'][:,None].expand(-1,physical_q.shape[1]).flatten()
    scene={k:v[:,None].expand(-1,physical_q.shape[1],*v.shape[1:]).flatten(0,1)
           for k,v in b['scene'].items()}
    flat=physical_q.flatten(0,1); physics_parts=[]
    peak_terrain=0.; peak_self=0.; samples=0
    for first in range(0,len(flat),query.batch_size):
        stop=min(len(flat),first+query.batch_size); chunk=flat[first:stop]; sid=ids[first:stop]
        timer=getattr(query,'timer',None)
        timed=lambda name:timer.stage(name) if timer is not None else nullcontext()
        if cfg.efficient_training: model.fk.begin_link_pose_cache(chunk)
        try:
            with timed('newton_query'):
                observed=query.observed(chunk,sid)
            with timed('witness_fk'):
                rows=DeviceWitnessRows(model.fk,chunk,observed)
            with timed('complete_solids'):
                rows.solid=query.workers.solid_router(model.fk,chunk,sid)
            selected_scene={k:v[first:stop] for k,v in scene.items()}
            with timed('target_interval'):
                interval=query.workers.target_interval(model,rows,active[first:stop],surface[first:stop],selected_scene,sid)
            with timed('region_objective'):
                loss,metrics=unified_region_objective(model,rows,active[first:stop],surface[first:stop],selected_scene,
                    release_mask=release[first:stop],surface_interval=interval,
                    audit_path=cfg.report/'unknown_normals_unified.jsonl')
        finally:
            if cfg.efficient_training:model.fk.end_link_pose_cache()
        physics_parts.append(loss); samples+=len(chunk)
        peak_terrain=max(peak_terrain,float(metrics['solid_terrain_penetration_cm'].detach().max()/100))
        peak_self=max(peak_self,float(metrics['solid_self_penetration_cm'].detach().max()/100))
    frame_loss=torch.cat(physics_parts).reshape(physical_q.shape[:2])
    # Immutable boundary defects cannot be repaired by an endpoint-preserving
    # decoder. Audit them, but do not let their constant maxima hide interior
    # gradients or dominate model selection.
    interior=frame_loss[:,1:-1]
    physics=interior.mean()+interior.amax(-1).mean()
    timer=getattr(query,'timer',None)
    with timer.stage('pose_smoothness') if timer is not None else nullcontext():
        pose,smooth,metrics=regularized_motion_objective(model,b,q,limits,budget_ratio=cfg.feasible_budget_ratio,
            witnessed_budgets=cfg.witnessed_budgets)
    total=cfg.physics_weight*physics+cfg.pose_weight*pose+cfg.smoothness_weight*smooth
    if model.conditions_on_velocity:
        from generator.infiller_boundary_velocity import velocity_objective
        velocity_loss,velocity_metrics=velocity_objective(model,b)
        total=total+cfg.velocity_weight*velocity_loss
        metrics.update(velocity_metrics)
    if model.predicts_frames:
        count_loss,efficiency,frame_metrics=frame_objective(b)
        if model.frame_training == 'joint':
            total=total+cfg.frame_weight*count_loss+cfg.frame_efficiency_weight*efficiency
        metrics.update(frame_metrics)
    return total,dict(metrics,unified_physics=physics,complete_terrain_max_m=peak_terrain,
        complete_self_max_m=peak_self,physical_samples=samples,
        immutable_boundary_physics=float(frame_loss[:,(0,-1)].detach().max()))


@torch.no_grad()
def validation_loss(model,records,limits,names,cfg,device,query=None):
    totals=defaultdict(float); counts=Counter()
    from generator.recursive_refinement import adjacent_records, seam_objective
    successors=adjacent_records(records) if cfg.seam_weight else {}
    from generator.infiller_boundary_velocity import SelfGeneratedHistory
    from generator.infiller_efficiency import BoundaryRecordCache
    boundary_cache=BoundaryRecordCache(model,records,device) if cfg.efficient_training else None
    history=SelfGeneratedHistory(model,records,device,boundary_cache=boundary_cache) if getattr(model,'conditions_on_velocity',False) else None
    schedule=batches(records,cfg)
    for number,indices in enumerate(schedule,1):
        selected=[records[i] for i in indices]; b=prepare_frame_prediction(model,collate(selected,device))
        if history is not None: history.condition(b,indices)
        q=decode_batch(model,b)
        if cfg.objective=='unified':
            if query is None: raise ValueError('Unified model selection requires actual Newton queries')
            loss,metrics=unified_objective(model,b,q,limits,query,cfg)
        else:
            loss,metrics=trajectory_objective(model,b,q,limits,names,dense_factor=cfg.dense_factor)
        if cfg.seam_weight:
            seam,_=seam_objective(model,records,indices,successors,q,device,history=history,boundary_cache=boundary_cache,
                derivative_limits=limits if cfg.witnessed_budgets else None,budget_ratio=cfg.feasible_budget_ratio)
            loss=loss+cfg.seam_weight*seam
        key=selected[0]['kind']; totals[key]+=float(loss)*len(indices); counts[key]+=len(indices)
        if cfg.objective=='unified' and number%25==0:
            progress=dict(stage='unified_validation',batches=number,total_batches=len(schedule),
                evaluated=sum(counts.values()),total=len(records))
            dump(cfg.report/'validation_progress.json',progress)
            print(json.dumps(progress),flush=True)
    metrics={kind:totals[kind]/counts[kind] for kind in counts}
    expected={'demonstration'} if cfg.training_source=='demonstration_only' else {'demonstration','predictor_accepted'}
    if set(metrics) not in (expected,expected|{'predictor_recursive'} if cfg.training_source=='mixed' else expected):
        raise ValueError('Validation boundary kinds do not match training source')
    generated=[value for kind,value in metrics.items() if kind!='demonstration']
    score=metrics['demonstration'] if not generated else .5*(metrics['demonstration']+sum(generated)/len(generated))
    return score,metrics


def supervision_records(records,split,training_source):
    """Keep generated trajectories out of both optimization and model selection."""
    if training_source not in ('mixed','demonstration_only'):
        raise ValueError('Unknown training source')
    return [r for r in records if r['split']==split and
            (training_source=='mixed' or r['kind']=='demonstration')]


def smoke_records(records,cfg):
    if cfg.maximum_samples is None: return records
    if not cfg.smoke: raise ValueError('Training sample cap requires explicit smoke mode')
    by_kind={kind:[r for r in records if r['kind']==kind] for kind in sorted({r['kind'] for r in records})}
    if cfg.maximum_samples<len(by_kind): raise ValueError('Smoke cap must retain every supervised kind')
    selected=[]
    for index in range(max(map(len,by_kind.values()))):
        for group in by_kind.values():
            if index<len(group): selected.append(group[index])
            if len(selected)==cfg.maximum_samples: return selected
    return selected


def attach_shared_materials(model,corpus,cfg,query):
    from contact_solver.contact_regions import ContactRegions
    from contact_solver.contact_material_skin import ContactMaterialSkin
    model.region_geometry=ContactRegions(model.fk)
    reference=json.loads(cfg.baseline.read_text())['training_geometry_materials']['contact_material_skin.pt']
    if evidence(reference['path'])['sha256']!=reference['sha256']: raise ValueError('Stale training contact materials')
    bank=torch.load(reference['path'],map_location='cpu',weights_only=False)
    decode_robot_asset_json(bank['robot_asset_json'],context='Shared Predictor training materials')
    meta=bank['metadata']
    if meta['contact_semantics']!=NEWTON_CONTACT_SCHEMA or meta['face_selection']!=FACE_POLICY:
        raise ValueError('Training materials require current Newton/primary-face rematerialization')
    if tuple(meta['link_names'])!=query.names: raise ValueError('Shared contact material link mapping changed')
    training_ids={r['sample_id'] for r in corpus['records'] if r['split']=='train'}
    material_source=corpus.get('material_source_corpus')
    if material_source is not None:
        if evidence(material_source['path'])!=material_source:
            raise ValueError('Stale inherited material training corpus')
        source=torch.load(material_source['path'],map_location='cpu',weights_only=False)
        if source['robot_asset_json']!=corpus['robot_asset_json'] or source['predictor']!=corpus['predictor']:
            raise ValueError('Inherited materials require the same asset and Predictor')
        source_train={r['sample_id'] for r in source['records'] if r['split']=='train'}
        source_heldout={r['sample_id'] for r in source['records'] if r['split']!='train'}
        if not training_ids<=source_train or set(meta['source_ids']) & source_heldout:
            raise ValueError('Inherited material evidence contains held-out data')
        training_ids=source_train
    if set(meta['source_ids'])-training_ids: raise ValueError('Held-out material entered shared training geometry')
    skin=ContactMaterialSkin(model.region_geometry,query.names)
    for name,value in bank['buffers'].items():
        if name=='known': skin.known.copy_(value)
        else: skin.register_buffer(name,value,persistent=False)
    skin.source_ids=set(meta['source_ids']); skin.source_contact_count=meta['source_contact_count']; skin.finalized=True
    model.region_geometry.material_skin=skin
    return dict(evidence=reference,metadata=meta,inherited_training_corpus=material_source)


def train(cfg,corpus,query,predictor,device):
    model=DirectInfiller(predict_frames=cfg.predict_frames,frame_training=cfg.frame_training,
                         boundary_velocity=cfg.boundary_velocity,conditional_boundary=cfg.conditional_boundary,
                         residual_extension=cfg.residual_extension)
    initialization=None; initial=None
    if cfg.initialization_checkpoint is not None:
        initial=torch.load(cfg.initialization_checkpoint,map_location='cpu',weights_only=False)
        decode_robot_asset_json(initial['robot_asset_json'],context='Infiller initialization')
        compatible=checkpoint_corpus_matches(initial,corpus,cfg.corpus)
        if initial['schema']!=SCHEMA or not compatible or initial['predictor']!=corpus['predictor']:
            raise ValueError('Infiller initialization/corpus/Predictor mismatch')
        state=dict(initial['model'])
        key='initial_velocity_head.0.weight'
        if cfg.conditional_boundary and not initial.get('architecture',{}).get('conditional_boundary',False) and key in state:
            weight=torch.zeros_like(model.initial_velocity_head[0].weight)
            if state[key].shape!=(weight.shape[0],173):
                raise ValueError('Unsupported initial-velocity conditioning migration')
            weight[:,:173]=state[key];state[key]=weight
        incompatible=model.load_state_dict(state,strict=False)
        migration=('frame_head.',)+(('velocity_scale','initial_velocity_head.',
            'terminal_velocity_head.','velocity_adapter.') if cfg.boundary_velocity else ())
        if cfg.residual_extension:migration=migration+('residual_extension.',)
        if incompatible.unexpected_keys or any(not k.startswith(migration) for k in incompatible.missing_keys):
            raise ValueError(f'Unsupported Infiller migration: {incompatible}')
        initialization=evidence(cfg.initialization_checkpoint)
    if cfg.objective=='unified':
        dump(cfg.output/'shared_contact_materials.json',attach_shared_materials(model,corpus,cfg,query))
    model=model.to(device)
    reference=json.loads(Path('configs/climb00/direct_infiller_v1.json').read_text())
    limits={k:torch.tensor(v,device=device) for k,v in reference['smoothness_limits'].items()}
    records=corpus['records']
    train_records=smoke_records(supervision_records(records,'train',cfg.training_source),cfg)
    validation=smoke_records(supervision_records(records,'validation',cfg.training_source),cfg)
    kinds=tuple(sorted({r['kind'] for r in train_records}))
    if set(kinds)!={r['kind'] for r in validation}: raise ValueError('Train/validation kinds differ')
    frame_warmup=None
    if cfg.predict_frames and cfg.frame_warmup_steps:
        from generator.infiller_frame_training import warmup_frame_head
        frame_warmup=warmup_frame_head(model,train_records,validation,cfg,device)
    elif cfg.predict_frames and cfg.frame_training=='decoupled' and initial is not None:
        architecture=initial.get('architecture',{})
        if architecture.get('predicts_frames') and architecture.get('frame_training')=='decoupled':
            frame_warmup=initial.get('frame_warmup')
    frozen_frames = None
    if cfg.predict_frames and cfg.frame_training == 'decoupled':
        if not frame_warmup:
            raise ValueError('Decoupled timing requires an independently supervised frame warmup')
        for parameter in model.frame_head.parameters():
            parameter.requires_grad_(False)
        frozen_frames={k:v.detach().clone() for k,v in model.frame_head.state_dict().items()}
        dump(cfg.output/'independent_frame_training.json',dict(
            supervision='training demonstrations only',selection='validation demonstrations only',
            loss='SmoothL1 in absolute frame counts',trajectory_time='detached predicted duration',
            frame_parameters_frozen_during_trajectory_training=True,
            reused_from_initialization=initialization if cfg.frame_warmup_steps==0 else None,test_used=False))
        torch.save(dict(schema='independent_infiller_frame_head_v2',
            robot_asset_json=encode_robot_asset_json(),model=cpu_tree(model.frame_head.state_dict()),
            boundary_features=172,predictor=corpus['predictor'],corpus=evidence(cfg.corpus),
            frame_warmup=frame_warmup,sampling_hz=50,count_includes_endpoints=True),
            cfg.output/'timing_head_selected.pt')
    velocity_warmup=None
    if model.conditions_on_velocity and cfg.velocity_warmup_steps:
        from generator.infiller_boundary_velocity import warmup_velocity_heads
        velocity_warmup=warmup_velocity_heads(model,train_records,validation,cfg,device)
    from generator.recursive_refinement import adjacent_records, seam_objective
    successors=adjacent_records(train_records) if cfg.seam_weight else {}
    from generator.infiller_boundary_velocity import SelfGeneratedHistory
    from generator.infiller_efficiency import BoundaryRecordCache
    boundary_cache=BoundaryRecordCache(model,train_records,device) if cfg.efficient_training else None
    train_history=SelfGeneratedHistory(model,train_records,device,boundary_cache=boundary_cache) if model.conditions_on_velocity else None
    generated_kinds=[k for k in kinds if k!='demonstration']
    pools={kind:[indices for indices in batches(train_records,cfg) if train_records[indices[0]]['kind']==kind]
           for kind in kinds}
    if any(not pool for pool in pools.values()): raise ValueError('Missing requested training boundary kind')
    rng=random.Random(cfg.seed)
    for pool in pools.values(): rng.shuffle(pool)
    cursors=Counter(); exposures=Counter(demonstration=0,predictor_accepted=0); best=math.inf; started=time.monotonic()
    optimizer=torch.optim.Adam([p for p in model.parameters() if p.requires_grad],lr=cfg.learning_rate)
    baseline_before=evidence(corpus['predictor']['path'])
    def snapshot(step,score,vmetrics):
        return dict(schema=SCHEMA,model=cpu_tree(model.state_dict()),robot_asset_json=encode_robot_asset_json(),
            architecture=dict(predicts_frames=model.predicts_frames,
                frame_training=model.frame_training,
                boundary_velocity=model.conditions_on_velocity,
                conditional_boundary=model.conditional_boundary,
                residual_extension=model.has_residual_extension,
                velocity_supervision='native sampled expert path on predicted time' if model.conditional_boundary else 'analytic heads',
                seam_supervision='expert sampled velocity changes only' if model.conditional_boundary else 'zero sampled velocity change',
                witnessed_segment_and_seam_budgets=cfg.witnessed_budgets,
                velocity_order='world root linear 3, world angular 3, joint 29',
                velocity_history='self-generated native 50Hz finite differences; unknown first segment',
                schema='direct_infiller_conditional_boundary_v2' if model.conditional_boundary else 'direct_infiller_boundary_velocity_v1' if model.conditions_on_velocity else ('direct_infiller_frames_decoupled_v2' if model.frame_training=='decoupled'
                    else 'direct_infiller_frames_v1') if model.predicts_frames else 'direct_infiller_fixed_duration_v1',
                frame_sampling_hz=50,count_includes_endpoints=True),frame_warmup=frame_warmup,
            velocity_warmup=velocity_warmup,
            step=step,config=asdict(cfg),corpus=evidence(cfg.corpus),predictor=baseline_before,
            validation=dict(balanced_loss=score,by_kind=vmetrics),optimizer=cpu_tree(optimizer.state_dict()),
            geometry=query.workers.solid_router.contract(),contact_truth=corpus['summary']['label_policy'],
            sampling=('expert/reference phase grids + midpoint complete Newton/solid queries; learned duration; native 50Hz inference'
                      if model.predicts_frames else 'native 50Hz + 100Hz midpoint complete Newton/solid queries' if cfg.objective=='unified' else
                      'native 50Hz; dense terrain proxy 500Hz; random complete-solid training checks'),
            initialization=initialization,
            training_cohort=dict(training=dict(Counter(r['kind'] for r in train_records)),
                validation=dict(Counter(r['kind'] for r in validation)),smoke=cfg.smoke,
                adjacent_training_pairs=len(successors)),
            target_interval=(query.workers.target_interval_provider().contract() if cfg.objective=='unified' else None),
            frozen_predictor_parameters=sum(p.numel() for p in predictor.parameters()),
            predictor_gradients_present=any(p.grad is not None for p in predictor.parameters()))
    if initialization is not None:
        model.eval(); best,initial_metrics=validation_loss(model,validation,limits,corpus['link_names'],cfg,device,query)
        torch.save(snapshot(0,best,initial_metrics),cfg.output/'best.pt')
        dump(cfg.output/'initial_validation.json',dict(balanced_loss=best,by_kind=initial_metrics,initialization=initialization))
        print(json.dumps(dict(validation_step=0,balanced_loss=best,by_kind=initial_metrics,best_loss=best)),flush=True)
    for step in range(1,cfg.steps+1):
        is_demo=cfg.training_source=='demonstration_only' or ((step-1)*cfg.demo_fraction)%1 < cfg.demo_fraction
        kind='demonstration' if is_demo else generated_kinds[sum(cursors[k] for k in generated_kinds)%len(generated_kinds)]
        pool=pools[kind]; index=cursors[kind]%len(pool)
        if index==0: rng.shuffle(pool)
        cursors[kind]+=1
        batch_indices=pool[index]; batch_records=[train_records[i] for i in batch_indices]
        model.train(); b=prepare_frame_prediction(model,collate(batch_records,device))
        history=train_history
        if history is not None: history.cache.clear()
        if history is not None: history.condition(b,batch_indices)
        q=decode_batch(model,b)
        if cfg.objective=='unified':
            loss,metrics=unified_objective(model,b,q,limits,query,cfg)
            solid_loss=q.sum()*0
        else:
            loss,metrics=trajectory_objective(model,b,q,limits,corpus['link_names'],dense_factor=cfg.dense_factor)
        # Complete initialized solids supplement historical dense terrain
        # sampling, including actual self-collision filters and containment.
        if cfg.objective=='historical':
            chosen=torch.randperm(q.shape[1]-2,device=device)[:cfg.solid_training_frames]+1
            sq=q[:,chosen].flatten(0,1)
            ids=b['scene_id'][:,None].expand(-1,len(chosen)).flatten()
            solid=query.workers.solid_router(model.fk,sq,ids)
            penalties=torch.log1p(((-solid.distances-.002).relu()/.01).square())
            # No overlapping broad-phase candidates means zero collision cost.
            solid_loss=penalties.sum()/max(1,penalties.numel())*10+q.sum()*0
            loss=loss+solid_loss
        if cfg.seam_weight:
            seam,pairs=seam_objective(model,train_records,batch_indices,successors,q,device,history=history,boundary_cache=boundary_cache,
                derivative_limits=limits if cfg.witnessed_budgets else None,budget_ratio=cfg.feasible_budget_ratio)
            loss=loss+cfg.seam_weight*seam
            metrics.update(sampled_seam_loss=seam,sampled_seam_pairs=pairs)
        if not bool(torch.isfinite(loss)):
            raise ValueError(f'Nonfinite Infiller objective: {metrics}, solid={solid_loss}')
        optimizer.zero_grad(set_to_none=True); loss.backward()
        grad=torch.nn.utils.clip_grad_norm_(model.parameters(),10,error_if_nonfinite=True)
        optimizer.step()
        if frozen_frames is not None and any(not torch.equal(v,model.frame_head.state_dict()[k])
                                             for k,v in frozen_frames.items()):
            raise AssertionError('Trajectory training altered independently selected frame parameters')
        lr=1e-5+(cfg.learning_rate-1e-5)*.5*(1+math.cos(math.pi*step/cfg.steps))
        for group in optimizer.param_groups: group['lr']=lr
        exposures[kind]+=len(batch_indices)
        record=dict(step=step,kind=kind,loss=float(loss.detach()),solid_loss=float(solid_loss.detach()),gradient_norm=float(grad),
            learning_rate=lr,elapsed_seconds=time.monotonic()-started,exposures=dict(exposures),
            objective=cfg.objective,metrics={k:float(v.detach()) if isinstance(v,torch.Tensor) else v for k,v in metrics.items()})
        if step==1 or step%25==0:
            with (cfg.output/'history.jsonl').open('a') as stream: stream.write(json.dumps(record)+'\n')
            dump(cfg.output/'progress.json',dict(status='running',**record,target_steps=cfg.steps))
            print(json.dumps(record),flush=True)
        if step==1 or step%cfg.evaluation_every==0 or step==cfg.steps:
            model.eval(); score,vmetrics=validation_loss(model,validation,limits,corpus['link_names'],cfg,device,query)
            if evidence(corpus['predictor']['path']) != baseline_before: raise ValueError('Frozen Predictor changed')
            checkpoint=snapshot(step,score,vmetrics)
            torch.save(checkpoint,cfg.output/'last.pt')
            if score<best:
                best=score; torch.save(checkpoint,cfg.output/'best.pt')
            print(json.dumps(dict(validation_step=step,balanced_loss=score,by_kind=vmetrics,best_loss=best)),flush=True)
    dump(cfg.output/'progress.json',dict(status='complete',steps=cfg.steps,exposures=dict(exposures),
        elapsed_seconds=time.monotonic()-started,predictor_unchanged=True,
        independently_selected_frame_parameters_unchanged=frozen_frames is not None))
    return cfg.output/'best.pt'


def aggregate(rows):
    result={}
    for key in sorted({k for row in rows for k,v in row.items() if isinstance(v,(float,int)) and not isinstance(v,bool)}):
        values=np.asarray([row[key] for row in rows if isinstance(row.get(key),(float,int))],float)
        if len(values): result[key]=dict(mean=float(values.mean()),p95=float(np.quantile(values,.95)),max=float(values.max()))
    result['count']=len(rows)
    return result


@torch.no_grad()
def evaluate(cfg,corpus,checkpoint_path,query,device):
    saved=torch.load(checkpoint_path,map_location='cpu',weights_only=False)
    decode_robot_asset_json(saved['robot_asset_json'],context='Direct Infiller checkpoint')
    if saved['schema']!=SCHEMA or not checkpoint_corpus_matches(saved,corpus,cfg.corpus): raise ValueError('Infiller/corpus mismatch')
    model=load_infiller(saved,device).eval()
    directory=cfg.report/f"evaluation_{checkpoint_path.stem}_step{saved['step']:05d}"
    directory.mkdir(exist_ok=False)
    trajectories=directory/'trajectories'; trajectories.mkdir()
    groups=defaultdict(list); timing_groups=defaultdict(list); seam_groups=defaultdict(list)
    chains=defaultdict(list); rows=[]
    selected=[(index,record) for index,record in enumerate(corpus['records']) if record['split'] in cfg.evaluation_splits]
    if not selected: raise ValueError('No records in requested evaluation splits')
    from generator.infiller_boundary_velocity import SelfGeneratedHistory
    history_records=[r for _,r in selected]
    history=SelfGeneratedHistory(model,history_records,device) if model.conditions_on_velocity else None
    for evaluated,(index,record) in enumerate(selected,1):
        b=collate([record],device)
        if history is not None: history.condition(b,[evaluated-1])
        if model.predicts_frames:
            q,frame_prediction=generate_segment(model,b['q'][:,0],b['q'][:,-1],b['contract'],b['scene'],
                maximum_frames=cfg.maximum_segment_frames,
                start_velocity=b.get('start_velocity'),velocity_known=b.get('velocity_known'))
            b['duration']=q.new_tensor([frame_prediction['duration_s']])
        else:
            q=decode_batch(model,b)[0]
            frame_prediction=dict(frames=len(q),duration_s=float(record['duration']),predicted_frames_float=None)
        if history is not None: history.store(evaluated-1,q)
        if not torch.equal(q[0].cpu(),record['q'][0]) or not torch.equal(q[-1].cpu(),record['q'][-1]):
            raise AssertionError('Infiller moved a fixed boundary')
        frame=query.timeline(q,int(record['scene_id']))
        dense=densify_qpos(q[None],cfg.dense_factor)[0]
        # Preserve complete raw native solver evidence in audit shards. These
        # are geometry/contact observations, not integrated execution loads.
        dense_result=query.timeline(dense,int(record['scene_id']),directory/'raw_newton'/f'segment_{index:05d}')
        middle=dense_result['depth'][1:-1]
        row=dict(index=index,kind=record['kind'],split=record['split'],motion_id=record['motion_id'],
            sample_id=record['sample_id'],**frame_prediction,
            reference_frames=len(record['q']),reference_duration_s=float(record['duration']),
            interior_terrain_max_m=float(middle[:,0].max()),interior_self_max_m=float(middle[:,1].max()),
            interior_penetration_mean_m=float(middle.amax(-1).mean()),
            interior_penetration_fraction=float((middle.amax(-1)>0).float().mean()),
            interior_above_5mm_fraction=float((middle.amax(-1)>.005).float().mean()),
            start_penetration_m=float(dense_result['depth'][0].max()),
            end_penetration_m=float(dense_result['depth'][-1].max()),
            invalid_native_witness_frames=int((dense_result['invalid']>0).sum()),
            continuity=continuity_metrics(q.cpu(),50),support='unknown_without_dynamic_execution')
        c=record['contract']
        if record['kind']=='demonstration':
            aligned=decode_batch(model,b)[0]  # Expert phase grid, predicted elapsed time.
            row.update(frame_absolute_error=abs(len(q)-len(record['q'])),
                phase_aligned_root_rmse_m=float((aligned[:,:3]-b['q'][0,:,:3]).square().sum(-1).mean().sqrt()),
                phase_aligned_joint_rmse_rad=float((aligned[:,7:]-b['q'][0,:,7:]).square().mean().sqrt()))
        timing=contact_timing_metrics(frame['mask'],frame['surface'],c['role'],c['start_surface'],c['end_surface'],50,
            record['active'] if record['kind']=='demonstration' else None,
            record['surface'] if record['kind']=='demonstration' else None)
        row['contact_timing']=timing
        key=f"{record['split']}/{record['kind']}"
        groups[key].append(row); timing_groups[key].extend(timing); rows.append(row)
        np.savez_compressed(trajectories/f'segment_{index:05d}.npz',joint_pos=q.cpu().numpy(),
            robot_asset_json=np.asarray(encode_robot_asset_json()),fps=np.asarray(50),
            actual_contact=frame['mask'].numpy(),actual_surface=frame['surface'].numpy(),
            native_solid_depth_m=frame['depth'].numpy(),dense_depth_m=dense_result['depth'].numpy(),
            sampling=np.asarray('fixed_q_forward_no_integration'),source_kind=np.asarray(record['kind']),
            predicted_frames=np.asarray(len(q)),reference_frames=np.asarray(len(record['q'])),
            duration_s=np.asarray(frame_prediction['duration_s']))
        if not record['chain_id'].startswith('isolated_'):
            chains[(key,record['chain_id'])].append((record,q.cpu()))
        if evaluated==1 or evaluated%25==0:
            dump(directory/'progress.json',dict(status='running',evaluated=evaluated,total=len(selected)))
            print(json.dumps(dict(stage='evaluation',evaluated=evaluated,total=len(selected))),flush=True)
    for (key,chain_id),segments in chains.items():
        segments.sort(key=lambda pair:pair[0]['current_frame'])
        for (left,lq),(right,rq) in zip(segments,segments[1:]):
            if left['target_frame']!=right['current_frame']: continue
            metrics=seam_metrics(lq,rq,50)
            seam_groups[key].append(dict(chain=chain_id,left_sample=left['sample_id'],right_sample=right['sample_id'],**metrics))
    report=dict(schema=SCHEMA,checkpoint=evidence(checkpoint_path),predictor=corpus['predictor'],
        checkpoint_step=saved['step'],scope='requested corpus splits; separately split and boundary source',
        evaluation_splits=list(cfg.evaluation_splits),training_source=saved['config'].get('training_source','mixed'),
        checkpoint_selection_source=saved['config'].get('training_source','mixed'),
        contact_truth=corpus['summary']['label_policy'],sampling='fixed_q_forward_no_integration',
        frame_source='Infiller predicted total frames' if model.predicts_frames else 'reference segment length',
        frame_targets='demonstration only; generated reference length has no timing truth',
        collision_sampling_hz=50*cfg.dense_factor,contact_sampling_hz=50,
        dense_geometry='nlerp between native output samples; actual Newton plus initialized complete solids',
        support='unknown_without_dynamic_execution',groups={})
    for key,group in groups.items():
        times=timing_groups[key]; establishment=[x for x in times if x['role'] in (1,3)]
        keeps=[x for x in times if x['role']==2]
        report['groups'][key]=dict(segments=len(group),penetration=aggregate(group),
            continuity=aggregate([r['continuity'] for r in group]),
            establishment=dict(count=len(establishment),failed=sum(not r['established'] for r in establishment),
                already_active=sum(r['initially_on_target_surface'] for r in establishment),metrics=aggregate(establishment)),
            keep=dict(count=len(keeps),metrics=aggregate(keeps)),seams=aggregate(seam_groups[key]))
    dump(directory/'report.json',report); dump(directory/'segments.json',rows); dump(directory/'seams.json',seam_groups)
    dump(directory/'progress.json',dict(status='complete',evaluated=len(rows),total=len(rows)))
    return report,directory


def inference_contract(predictor,q0,prediction,initial,observed):
    """Unrealized targets stay declared intentions, with no fake contact labels."""
    active=prediction.conditioned_contact[0]
    points=plan_points_in_pose_frame(q0[None],prediction.conditioned_points_local)
    surface=(prediction.conditioned_surface if prediction.conditioned_surface is not None
        else audit_intended_surfaces(points,prediction.conditioned_contact,observed))[0]
    realized=active & observed['contact_part_mask'][0] & (surface==observed['contact_surface'][0])
    anchors=torch.where(realized[:,None],observed['contact_position_w'][0],points[0])
    anchors=torch.where(active[:,None],anchors,0)
    contract=record_contract(predictor.fk,q0,prediction.qpos[0],initial['contact_part_mask'][0],
        active,initial['contact_surface'][0],surface,initial['contact_position_w'][0],anchors,
        prediction.conditioned_role[0])
    return contract,realized


def recursive_segments(predictor,infiller,query,initial_q,scene,scene_id,limits,*,events,duration,
                       dense_factor=10,audit_root=None,maximum_frames=4096,use_frame_head=True):
    """Self-fed endpoint/trajectory recursion; ordinary rejection never resets it."""
    if events<1 or not math.isfinite(duration) or duration<=0:
        raise ValueError('Invalid recursive rollout schedule')
    current=initial_q.clone(); device=current.device; current_velocity=None
    batched_scene={k:v[None].to(device) for k,v in scene.items()}
    for event in range(events):
        with torch.no_grad():
            initial=query.observed(current[None],torch.tensor([scene_id],device=device))
            prediction=predictor(**predictor_observation(predictor,current[None],initial,batched_scene,
                torch.tensor([scene_id],device=device),query.workers))
            if not bool(torch.isfinite(prediction.qpos).all()):
                raise ValueError(f'Nonfinite predicted endpoint at event {event}')
            observed,audit=audit_prediction(predictor,query,prediction,current,initial,scene_id,limits)
            contract,realized=inference_contract(predictor,current,prediction,initial,observed)
            q,frame_prediction=generate_segment(infiller,current[None],prediction.qpos,
                {k:v[None] for k,v in contract.items()},batched_scene,duration=duration,
                maximum_frames=maximum_frames,use_frame_head=use_frame_head,start_velocity=current_velocity)
            if not bool(torch.isfinite(q).all()): raise ValueError(f'Nonfinite Infiller trajectory at event {event}')
            if not torch.equal(q[0],current) or not torch.equal(q[-1],prediction.qpos[0]):
                raise AssertionError('Infiller moved a recursive boundary')
            if getattr(infiller,'conditions_on_velocity',False):
                from generator.infiller_boundary_velocity import finite_difference_velocity
                current_velocity=finite_difference_velocity(q[None,-2:],1/50)
            directory=None if audit_root is None else audit_root/f'event_{event:03d}'
            native=query.timeline(q,scene_id)
            dense=query.timeline(densify_qpos(q[None],dense_factor)[0],scene_id,directory)
            timing=contact_timing_metrics(native['mask'],native['surface'],contract['role'],
                contract['start_surface'],contract['end_surface'],50)
            record=dict(event=event,accepted=audit['accepted'],endpoint_audit=audit,
                **frame_prediction,start_q=current.cpu().tolist(),end_q=q[-1].cpu().tolist(),
                initial_actual_contact=initial['contact_part_mask'][0].cpu().tolist(),
                endpoint_actual_contact=observed['contact_part_mask'][0].cpu().tolist(),
                endpoint_intended_contact=contract['end_contact'].cpu().tolist(),
                intended_surface=contract['end_surface'].cpu().tolist(),
                end_anchor_source=['inactive' if not bool(contract['end_contact'][i]) else
                    'observed_actual' if bool(realized[i]) else 'declared_unrealized_intent' for i in range(6)],
                interior_terrain_max_m=float(dense['depth'][1:-1,0].max()),
                interior_self_max_m=float(dense['depth'][1:-1,1].max()),
                invalid_witness_frames=int((dense['invalid']>0).sum()),
                contact_timing=timing,continuity=continuity_metrics(q.cpu(),50))
            endpoints=dict(start_q=current.cpu(),end_q=q[-1].cpu(),initial=cpu_tree(initial),
                observed=cpu_tree(observed),contract=cpu_tree(contract))
            current=q[-1].detach().clone()
        yield q.cpu(),native,dense,record,endpoints


def rollout(cfg,corpus,checkpoint_path,query,predictor,device,limits):
    saved=torch.load(checkpoint_path,map_location='cpu',weights_only=False)
    decode_robot_asset_json(saved['robot_asset_json'],context='recursive Infiller checkpoint')
    if saved['schema']!=SCHEMA or not checkpoint_corpus_matches(saved,corpus,cfg.corpus) or saved['predictor']!=corpus['predictor']:
        raise ValueError('Recursive Infiller/Predictor/corpus mismatch')
    model=load_infiller(saved,device).eval()
    for parameter in model.parameters(): parameter.requires_grad_(False)
    seed=next((r for r in corpus['records'] if r['kind']=='demonstration' and
               r['motion_id']==cfg.rollout_motion_id and r['current_frame']==0),None)
    if seed is None: raise ValueError('Missing requested initial demonstration state')
    directory=cfg.report/'rollout'; directory.mkdir(exist_ok=False)
    endpoint_dir=directory/'raw_endpoints'; endpoint_dir.mkdir()
    scene={k:v.to(device) for k,v in seed['scene'].items()}
    worker=next(e for e in query.workers.entries.values() if e['scene_id']==int(seed['scene_id']))
    metadata=query.workers.tensor_clients[int(seed['scene_id'])].metadata
    semantics=dict(schema=NEWTON_CONTACT_SCHEMA,face_policy=FACE_POLICY,part_order=CONTACT_PARTS,
        contact_body_names_by_part=CONTACT_BODY_NAMES_BY_PART,contact_reference_links=BODY_NAMES[1:],
        sampling='same-state fixed-q queries; no integration',contact_sampling_hz=50,
        dense_sampling_hz=50*cfg.dense_factor,scene_id=int(seed['scene_id']),
        worker_root=str(query.workers.root.resolve()),model=evidence(worker['folder']/'model.json'),
        surface_catalog=metadata['surface_catalog'],link_names=metadata['link_names'],
        provenance=metadata['provenance'],surface_attribution_schema=metadata['surface_attribution_schema'],
        dense_audit_indexing='event directory, query shard first index; segment native index * dense_factor')
    dump(directory/'contact_semantics.json',semantics)
    center=scene['box_center'].cpu().numpy(); rotation=scene['box_rotation'].cpu().numpy()
    half=scene['box_half_extents'].cpu().numpy()
    vertices=np.asarray([[x,y,z] for x in (-1,1) for y in (-1,1) for z in (-1,1)])*half
    vertices=vertices@rotation.T+center
    faces=((1,2,4,3),(5,7,8,6),(1,5,6,2),(3,4,8,7),(1,3,7,5),(2,6,8,4))
    terrain=directory/'terrain.obj'
    terrain.write_text('o scene_box\n'+''.join('v %.9f %.9f %.9f\n'%tuple(v) for v in vertices)+
                       ''.join('f '+' '.join(map(str,f))+'\n' for f in faces))
    qs=[]; masks=[]; surfaces=[]; depths=[]; dense_depths=[]; records=[]; seams=[]; previous=None
    runtime_predictor=cfg.rollout_predictor_checkpoint or Path(corpus['predictor']['path'])
    before=evidence(runtime_predictor); infiller_before=evidence(checkpoint_path)
    try:
        for q,native,dense,record,endpoints in recursive_segments(predictor,model,query,
            seed['q'][0].to(device),scene,int(seed['scene_id']),limits,
            events=cfg.rollout_events,duration=cfg.rollout_duration,dense_factor=cfg.dense_factor,
            audit_root=directory/'raw_newton',maximum_frames=cfg.maximum_segment_frames,
            use_frame_head=cfg.rollout_timing=='model'):
            event=record['event']; start=0 if event==0 else 1
            if previous is not None: seams.append(dict(event=event,**seam_metrics(previous,q,50)))
            previous=q
            record['first_frame']=0 if not records else records[-1]['last_frame']
            record['last_frame']=record['first_frame']+len(q)-1
            records.append(record); qs.append(q[start:]); masks.append(native['mask'][start:])
            surfaces.append(native['surface'][start:]); depths.append(native['depth'][start:])
            dense_depths.append(dense['depth'][start:])
            torch.save(endpoints,endpoint_dir/f'event_{event:03d}.pt')
            torch.save(dict(q=q,native=native,dense_depth_m=dense['depth'],record=record),directory/f'event_{event:03d}.pt')
            dump(directory/'segments.json',records)
            dump(directory/'progress.json',dict(status='running',generated=len(records),total=cfg.rollout_events,
                rejected=sum(not r['accepted'] for r in records)))
            print(json.dumps(dict(stage='recursive_rollout',generated=len(records),total=cfg.rollout_events,
                endpoint_accepted=record['accepted'],reasons=record['endpoint_audit']['reasons'])),flush=True)
    except Exception as exc:
        dump(directory/'progress.json',dict(status='failed',generated=len(records),total=cfg.rollout_events,
            error=f'{type(exc).__name__}: {exc}'))
        raise
    motion=directory/f'predictor_infiller_recursive{cfg.rollout_events}.npz'
    np.savez_compressed(motion,joint_pos=torch.cat(qs).numpy(),joint_names=np.asarray(G1_29DOF_JOINT_ORDER),
        fps=np.asarray(50),robot_asset_json=np.asarray(saved['robot_asset_json']),
        actual_contact=torch.cat(masks).numpy(),actual_surface=torch.cat(surfaces).numpy(),
        native_solid_depth_m=torch.cat(depths).numpy(),dense_depth_m=torch.cat(dense_depths).numpy(),
        sampling=np.asarray('fixed_q_forward_no_integration'),teacher_forced=np.asarray(False),
        segment_duration_s=np.asarray([r['duration_s'] for r in records]),
        segment_frames=np.asarray([r['frames'] for r in records]),
        segment_first_frame=np.asarray([r['first_frame'] for r in records]),
        segment_last_frame=np.asarray([r['last_frame'] for r in records]),events=np.asarray(len(records)),
        contact_semantics_json=np.asarray(json.dumps(semantics)))
    if before!=evidence(runtime_predictor) or infiller_before!=evidence(checkpoint_path):
        raise ValueError('Frozen rollout checkpoint changed')
    report=dict(schema='predictor_infiller_recursive_rollout_v1',events=len(records),frames=len(torch.cat(qs)),
        duration_s=(len(torch.cat(qs))-1)/50,seed_motion_id=cfg.rollout_motion_id,seed_split=seed['split'],
        teacher_forced=False,future_demonstration_read=False,ordinary_failure_behavior='record_and_continue',
        duration_source='Infiller predicted total frames at 50 Hz' if model.predicts_frames and cfg.rollout_timing=='model' else
                        'fixed configured duration; Predictor has no duration head',
        timing_counterfactual=cfg.rollout_timing=='fixed',
        infiller_checkpoint_step=saved['step'],infiller_training_source=saved.get('config',{}).get('training_source','mixed'),
        predictor=before,infiller=infiller_before,infiller_training_predictor=corpus['predictor'],
        predictor_gradients_present=any(p.grad is not None for p in predictor.parameters()),
        infiller_gradients_present=any(p.grad is not None for p in model.parameters()),
        motion=str(motion.resolve()),terrain=str(terrain.resolve()),sampling='fixed_q_forward_no_integration',
        support='unknown_without_dynamic_execution',contact_truth=FACE_POLICY,
        accepted_endpoints=sum(r['accepted'] for r in records),rejected_endpoints=sum(not r['accepted'] for r in records),
        first_rejected_event=next((r['event'] for r in records if not r['accepted']),None),
        penetration=aggregate(records),seams=aggregate(seams))
    dump(directory/'seams.json',seams); dump(directory/'report.json',report)
    dump(directory/'progress.json',dict(status='complete',generated=len(records),total=cfg.rollout_events))
    dump(cfg.report/'result.json',dict(status='complete',**report))
    return report


def run(cfg,device):
    if cfg.witnessed_budgets and not cfg.conditional_boundary:
        raise ValueError('Witnessed segment/seam pilot requires the conditional boundary architecture')
    if cfg.conditional_boundary and (not cfg.boundary_velocity or cfg.velocity_warmup_steps):
        raise ValueError('Conditional boundary training needs boundary_velocity and velocity_warmup_steps=0; sampled trajectory supervision replaces head-only warmup')
    if cfg.profile_repeats<1:raise ValueError('Profiling requires positive measured repeats')
    if cfg.velocity_warmup_steps<0 or not math.isfinite(cfg.velocity_weight) or cfg.velocity_weight<=0:
        raise ValueError('Invalid boundary velocity training configuration')
    if cfg.boundary_velocity and cfg.objective!='unified' and cfg.mode in ('train','all'):
        raise ValueError('Boundary velocity training requires the unified trajectory objective')
    if cfg.mode not in ('all','build','train','evaluate','rollout','extend','profile'): raise ValueError('Unknown mode')
    if cfg.efficient_training and (not cfg.predict_frames or cfg.frame_training!='decoupled') and cfg.mode in ('all','train'):
        raise ValueError('Efficient timing cache requires independent frozen frame training')
    if not math.isfinite(cfg.seam_weight) or cfg.seam_weight<0: raise ValueError('Invalid seam weight')
    if cfg.seam_weight and cfg.objective!='unified': raise ValueError('Recursive seam training requires unified physics')
    if cfg.predict_frames and cfg.objective!='unified': raise ValueError('Frame training requires unified physics')
    if cfg.frame_training not in ('joint','decoupled'): raise ValueError('Unknown frame training mode')
    if cfg.rollout_timing not in ('model','fixed') or (cfg.rollout_timing=='fixed' and cfg.mode!='rollout'):
        raise ValueError('Fixed timing override is an explicit rollout-only counterfactual')
    if cfg.frame_warmup_steps<0 or cfg.maximum_segment_frames<4 or any(not math.isfinite(v) or v<=0 for v in
        (cfg.frame_weight,cfg.frame_efficiency_weight)):
        raise ValueError('Invalid frame training weights or resource limit')
    if cfg.rollout_predictor_checkpoint is not None and cfg.mode!='rollout':
        raise ValueError('Alternative Predictor is an explicit rollout-only comparison')
    if cfg.maximum_samples is not None and not cfg.smoke: raise ValueError('Sample cap only permitted with --smoke')
    if cfg.training_source not in ('mixed','demonstration_only'): raise ValueError('Unknown training source')
    if cfg.objective not in ('historical','unified'): raise ValueError('Unknown trajectory objective')
    if cfg.feasible_budget_ratio<1 or any(not math.isfinite(v) or v<=0 for v in
        (cfg.pose_weight,cfg.physics_weight,cfg.smoothness_weight,cfg.feasible_budget_ratio)):
        raise ValueError('Invalid unified objective weights or reference-feasible budget ratio')
    if not cfg.evaluation_splits or set(cfg.evaluation_splits)-{'train','validation','test'}:
        raise ValueError('Unknown or empty evaluation splits')
    if cfg.steps<1 or cfg.dense_factor<1 or cfg.recursive_events<0 or not 0<cfg.demo_fraction<1:
        raise ValueError('Invalid training schedule')
    if cfg.rollout_events<1 or not math.isfinite(cfg.rollout_duration) or round(cfg.rollout_duration*50)<3:
        raise ValueError('Invalid recursive rollout schedule')
    if device=='cpu': raise ValueError('Current Newton tensor queries require CUDA; no alternate contact backend')
    torch.set_num_threads(2); torch.manual_seed(cfg.seed); np.random.seed(cfg.seed)
    baseline=json.loads(cfg.baseline.read_text())
    for name,reference in dict(predictor=baseline['checkpoint'],**baseline['dependencies']).items():
        if evidence(reference['path'])['sha256']!=reference['sha256']: raise ValueError(f'Stale {name}')
    predictor_ckpt=torch.load(baseline['checkpoint']['path'],map_location='cpu',weights_only=False)
    predictor=load_position_predictor(predictor_ckpt,device=device).eval()
    for parameter in predictor.parameters(): parameter.requires_grad_(False)
    baseline['configuration_dict']=predictor_ckpt['config']
    deps=baseline['dependencies']
    payload=torch.load(deps['data_cache']['path'],map_location='cpu',weights_only=False)
    heights=sorted({round(float(s['height']),8) for s in payload['samples']})
    del payload
    cfg.report.mkdir(parents=True,exist_ok=True)
    if cfg.mode in ('all','train'):
        if cfg.output.exists(): raise FileExistsError(f'Refusing existing training output: {cfg.output}')
        cfg.output.mkdir(parents=True)
        dump(cfg.output/'config.json',{k:str(v) if isinstance(v,Path) else v for k,v in asdict(cfg).items()})
    worker_root=cfg.report/f'newton_{cfg.mode}_{time.time_ns()}'
    with Workers(worker_root,heights,device,query_worlds=cfg.query_worlds,tensor_transport=True,solid_geometry=True,
        packed_transport=cfg.efficient_training,
        checkpoint=deps['query_checkpoint']['path'],source_manifest=deps['query_source_manifest']['path'],
        source_model=deps['query_source_model']['path'],depth_scan_profile=predictor.depth_scan_profile) as workers:
        query=NativeQueries(workers,predictor.fk,cfg.query_batch_size)
        if cfg.mode in ('all','build'):
            corpus=make_corpus(cfg,baseline,predictor,query,device)
        elif cfg.mode=='extend':
            from generator.extend_recursive_corpus import extend_corpus
            corpus=extend_corpus(cfg,baseline,predictor,query,device)
        else:
            corpus=torch.load(cfg.corpus,map_location='cpu',weights_only=False)
            decode_robot_asset_json(corpus['robot_asset_json'],context='Infiller corpus')
            if corpus['predictor']!=evidence(baseline['checkpoint']['path']): raise ValueError('Predictor/corpus mismatch')
            if corpus['scene_fingerprints']!={str(e['scene_id']):e['fp'] for e in workers.entries.values()}:
                raise ValueError('Actual Newton scenes changed; explicitly rebuild corpus')
            if corpus.get('parent_corpus') and cfg.mode=='train' and cfg.objective!='unified':
                raise ValueError('Rejected recursive boundaries require unified unknown-timing supervision')
            if cfg.mode=='train' and not cfg.smoke and corpus.get('extension',{}).get('smoke'):
                raise ValueError('Smoke recursive coverage cannot become a formal training corpus')
        checkpoint_path=cfg.checkpoint
        if cfg.mode=='profile':
            if checkpoint_path is None: raise ValueError('Profiling requires an Infiller checkpoint')
            from generator.infiller_efficiency import profile_training
            profile_training(cfg,corpus,query,device)
            return
        if cfg.mode in ('all','train'):
            checkpoint_path=train(cfg,corpus,query,predictor,device)
        if cfg.mode=='rollout':
            if checkpoint_path is None: raise ValueError('Rollout requires an Infiller checkpoint')
            if cfg.rollout_predictor_checkpoint is not None:
                alternative=torch.load(cfg.rollout_predictor_checkpoint,map_location='cpu',weights_only=False)
                if alternative.get('refinement',{}).get('parent_predictor')!=corpus['predictor']:
                    raise ValueError('Alternative Predictor must record the same frozen parent')
                predictor=load_position_predictor(alternative,device=device).eval()
                if predictor.depth_scan_profile != workers.depth_scan_profile:
                    raise ValueError('Alternative Predictor camera differs from the frozen corpus observation')
                for parameter in predictor.parameters(): parameter.requires_grad_(False)
            rollout(cfg,corpus,checkpoint_path,query,predictor,device,configured_acceptance(predictor_ckpt['config']))
        if cfg.mode in ('all','evaluate'):
            if checkpoint_path is None: raise ValueError('Evaluation requires checkpoint')
            report,directory=evaluate(cfg,corpus,checkpoint_path,query,device)
            dump(cfg.report/'result.json',dict(status='complete',report=str((directory/'report.json').resolve()),
                predictor_unchanged=evidence(baseline['checkpoint']['path'])['sha256']==baseline['checkpoint']['sha256'],
                evaluated_checkpoint_step=report['checkpoint_step'],
                training_progress=json.loads((cfg.output/'progress.json').read_text()) if (cfg.output/'progress.json').exists() else None,
                smoke=cfg.smoke))


def main():
    from isaaclab.app import AppLauncher
    import tyro
    parser=argparse.ArgumentParser(add_help=False)
    AppLauncher.add_app_launcher_args(parser)
    official,remaining=parser.parse_known_args()
    cfg=tyro.cli(Config,args=remaining)
    device='cpu' if getattr(official,'cpu',False) else official.device
    run(cfg,device)


if __name__=='__main__': main()
