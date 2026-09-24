"""Fresh observation-only next-interaction experiment; AppLauncher before tyro."""
import argparse
import os
from dataclasses import asdict,dataclass
import json
from pathlib import Path
import time
import numpy as np
import torch
import tyro
from isaaclab.app import AppLauncher
from somaforge_core.robot_assets import somaforge_root,encode_robot_asset_json
from climb00_pipeline.next_interaction import NextInteractionPredictor,NextInteraction,objective
from climb00_pipeline.neural_infiller import _matrix_from_rotation6d

ROOT=somaforge_root()


@dataclass
class Config:
    manifest:Path=ROOT/'tmp/dropout207_training_v1/manifest.json'
    q_cache:Path=ROOT/'tmp/dropout207_training_v1/q_cache.npz'
    output:Path=ROOT/'tmp/next_interaction_v1/gate'
    mode:str='gate'
    architecture:str='independent_v1'
    contact_objective:str='legacy_anchor'
    width:int=192
    layers:int=3
    batch_size:int=64
    epochs:int=2000
    gate_steps:int=2000
    learning_rate:float=.0003
    evaluation_every:int=10
    patience:int=200
    early_stopping:bool=True
    resume:Path|None=None
    seed:int=20260913
    profile_first_step:bool=False
    closed_loop_steps:int=1
    closed_loop_batch_fraction:float=.1
    closed_loop_recovery_weight:float=.25
    closed_loop_severe_penetration_m:float=.05
    neighborhood_batch_fraction:float=0.
    neighborhood_xy_m:float=.06
    warm_start:Path|None=None
    binding_pretrain_steps:int=0


def prepare(cfg,model,device):
    from predictor_preprocessing_cache import load_or_build_dataset
    from climb00_pipeline.contact_validity import validate_touchdown_cache
    from train_climb00_scan_action_q_deformer import box_obbs
    from train_climb00_contact_event_predictor import split_name
    data,samples,_,identity=load_or_build_dataset(cfg.manifest,64)
    with np.load(cfg.q_cache) as z:
        validate_touchdown_cache(z,samples,64)
        if str(z['contact_dataset_fingerprint'].item())!=identity['dataset_fingerprint']:
            raise ValueError('q cache does not belong to verified event corpus')
        q=torch.tensor(z['target_q'][:,[0,-1]],device=device)
    tensor=lambda x:torch.as_tensor(x,device=device)
    center_np,rotation_np,half_np,ground_np=box_obbs(data)
    center,rotation,half,ground=[tensor(x) for x in (center_np,rotation_np,half_np,ground_np)]
    normal=rotation[:,:,2]
    top=torch.cat((center+normal*half[:,2:3],normal,rotation[:,:,0],rotation[:,:,1],half[:,:2],torch.zeros_like(ground[:,None])),-1)
    floor=torch.zeros_like(top);floor[:,2]=ground;floor[:,5]=1.;floor[:,6]=1.;floor[:,10]=1.;floor[:,14]=1.
    faces=torch.stack((floor,top),1)
    current_contact=tensor(data['start_contacts']).bool()
    inputs=dict(current_q=q[:,0],current_contact=current_contact,current_anchor=tensor(data['current_contacts']),
                current_surface=tensor(data['current_surfaces']),faces=faces)
    if cfg.architecture=='heightmap_v1':
        from climb00_pipeline.next_interaction_heightmap import render_box_heightmaps
        inputs['heightmap']=tensor(render_box_heightmaps(center_np,rotation_np,half_np,ground_np))
    elif cfg.architecture in ('heightmap_v2','heightmap_v3','heightmap_v3_coupled','heightmap_v3_robust','heightmap_v4_bound','heightmap_v5_joint_bound'):
        from climb00_pipeline.next_interaction_heightmap_v2 import (
            heightmap_supersample_for_architecture, render_root_yaw_box_heightmaps)
        # Bound predictors use one fixed sample at every 2 cm grid location.
        # Averaging four sub-samples fabricates intermediate heights at a hard
        # terrain edge, so it is not a valid point-scan observation or binding
        # location.  Keep supersampling only for the separate legacy robust-v3
        # experiment whose checkpoint contract explicitly includes it.
        inputs['heightmap']=tensor(render_root_yaw_box_heightmaps(
            center_np,rotation_np,half_np,ground_np,q[:,0].detach().cpu().numpy(),
            supersample=heightmap_supersample_for_architecture(cfg.architecture)))
    role=torch.zeros((len(q),6),dtype=torch.long,device=device)
    role[tensor(data['end_contact']).bool()]=3
    role[tensor(data['persistent_contact']).bool()]=2
    role[tensor(data['interaction_touchdown']).bool()]=1
    if not torch.equal(role!=0,tensor(data['end_contact']).bool()):raise ValueError('Role/endpoint mismatch')
    with torch.no_grad():
        pos,rot6=model.fk(q[:,1,None]);pos=pos[:,0];rot=_matrix_from_rotation6d(rot6[:,0])
        material=torch.einsum('bpji,bpj->bpi',rot[:,1:7],tensor(data['target_contacts'])-pos[:,1:7])
    target=dict(q=q[:,1],current_q=q[:,0],role=role,surface=tensor(data['target_surfaces']).long(),anchor=tensor(data['target_contacts']),
                material_local=material,duration=tensor(data['duration']),body_position=pos)
    scene=dict(box_center=center,box_rotation=rotation,box_half_extents=half,ground_height=ground)
    split={name:torch.tensor([i for i,s in enumerate(samples) if split_name(s.height).startswith(name)],device=device)
           for name in ('train','validation','test')}
    for ids in split.values():
        if len(ids)==0:raise ValueError('Empty trajectory split')
    train=split['train']
    with torch.no_grad():model.pose_head.bias[7:].copy_(target['q'][train,7:].mean(0))
    # Algebraic expressivity audit: feed every demonstrated target to the
    # output representation, including the 1,326 examples beyond old +/-1 rad.
    if hasattr(model,'encode_pose'):
        raw=model.encode_pose(target['q'],inputs['current_q'])
    else:
        raw=target['q'].clone();raw[:,:3]-=inputs['current_q'][:,:3]
    decoded=model.decode_pose(raw,inputs['current_q'])
    torch.testing.assert_close(decoded,target['q'],rtol=1e-5,atol=1e-6)
    active=role!=0
    restored=pos[:,1:7]+torch.einsum('bpij,bpj->bpi',rot[:,1:7],material)
    residual=(restored-target['anchor']).norm(dim=-1)[active]
    input_contract=('current q, actual current contacts/surfaces/anchors, 2 cm root-yaw height map only'
                    if cfg.architecture in ('heightmap_v1','heightmap_v2','heightmap_v3','heightmap_v3_coupled','heightmap_v3_robust','heightmap_v4_bound','heightmap_v5_joint_bound') else
                    'current q, actual current contacts/surfaces/anchors, observed face geometry only')
    summary=dict(samples=len(samples),splits={k:len(v) for k,v in split.items()},
        contact_dataset_fingerprint=identity['dataset_fingerprint'],
        event_contract=json.loads(cfg.manifest.read_text())['event_contract'],
        beyond_old_joint_delta=int(((q[:,1,7:]-q[:,0,7:]).abs()>1).any(-1).sum()),
        all_endpoint_poses_expressible=True,material_reconstruction_max_m=float(residual.max()),
        input_contract=input_contract,
        no_phase_no_velocity_no_future_input=True,free_contact_offset_head=False,
        role_names=['no_contact','touchdown','persistent','other_endpoint_contact'],
        scope='supervised single endpoint; sampled geometry diagnostics are not achieved Newton contact')
    return inputs,target,scene,split,samples,summary


def take(group,ids):return {k:v[ids] for k,v in group.items()}


def remap_newton_fingerprints(target, path):
    """Map archived scene IDs to the exact realized current-Newton scenes."""
    config=json.loads(Path(path).read_text())
    if config.get('schema')!='newton_model_fingerprint_remap_v1':raise ValueError('Unknown Newton fingerprint remap')
    mapping=config['mapping']; encoded=target['newton_model_fingerprint'];changed=0
    for old,new in mapping.items():
        mask=(encoded==torch.tensor(list(bytes.fromhex(old)),dtype=torch.uint8,device=encoded.device)).all(-1)
        encoded[mask]=torch.tensor(list(bytes.fromhex(new)),dtype=torch.uint8,device=encoded.device);changed+=int(mask.sum())
    if changed!=len(encoded):raise ValueError(f'Newton fingerprint remap incomplete: {changed}/{len(encoded)}')
    return dict(schema=config['schema'],rows=changed,mapping=mapping,geometry_equality_verified=config['geometry_equality_verified'])


def main():
    parser=argparse.ArgumentParser(add_help=False);AppLauncher.add_app_launcher_args(parser)
    official,remaining=parser.parse_known_args();cfg=tyro.cli(Config,args=remaining)
    if official.visualizer is not None or official.enable_cameras:raise ValueError('Tensor predictor is headless')
    if cfg.mode not in ('gate','full'):raise ValueError('mode must be gate or full')
    if cfg.output.exists():raise FileExistsError(cfg.output)
    cfg.output.mkdir(parents=True)
    torch.set_num_threads(2);torch.manual_seed(cfg.seed)
    device=torch.device('cpu' if official.cpu else official.device)
    loss_function=objective
    if cfg.architecture=='joint_v2':
        from climb00_pipeline.next_interaction_joint import JointInteractionPredictor,prepare_supervision,objective as joint_objective
        model=JointInteractionPredictor(cfg.width,cfg.layers).to(device)
        loss_function=joint_objective
    elif cfg.architecture=='heightmap_v1':
        from climb00_pipeline.next_interaction_heightmap import HeightmapInteractionPredictor
        model=HeightmapInteractionPredictor(cfg.width,cfg.layers).to(device)
    elif cfg.architecture=='heightmap_v2':
        from climb00_pipeline.next_interaction_heightmap_v2 import RootYawHeightmapInteractionPredictor
        model=RootYawHeightmapInteractionPredictor(cfg.width,cfg.layers).to(device)
    elif cfg.architecture in ('heightmap_v3','heightmap_v3_coupled','heightmap_v3_robust'):
        from climb00_pipeline.next_interaction_heightmap_v3 import DenseHeightmapInteractionPredictor
        model=DenseHeightmapInteractionPredictor(
            cfg.width,cfg.layers,couple_contact_pose=cfg.architecture in ('heightmap_v3_coupled','heightmap_v3_robust')).to(device)
    elif cfg.architecture=='heightmap_v4_bound':
        from climb00_pipeline.next_interaction_heightmap_v4 import BoundHeightmapInteractionPredictor
        model=BoundHeightmapInteractionPredictor(cfg.width,cfg.layers).to(device)
    elif cfg.architecture=='heightmap_v5_joint_bound':
        from climb00_pipeline.next_interaction_heightmap_v4 import JointBoundHeightmapInteractionPredictor
        model=JointBoundHeightmapInteractionPredictor(cfg.width,cfg.layers).to(device)
    elif cfg.architecture=='independent_v1':model=NextInteractionPredictor(cfg.width,cfg.layers).to(device)
    else:raise ValueError('Unknown predictor architecture')
    inputs,target,scene,split,samples,summary=prepare(cfg,model,device)
    if cfg.contact_objective=='surface_region_v1':
        if cfg.architecture not in ('joint_v2','heightmap_v1','heightmap_v2','heightmap_v3','heightmap_v3_coupled','heightmap_v3_robust','heightmap_v4_bound','heightmap_v5_joint_bound'):
            raise ValueError('Surface experiment requires joint_v2 or heightmap_v1')
        from climb00_pipeline.next_interaction_surface import prepare_supervision as prepare_surface, objective as surface_objective
        summary['joint_interaction']=prepare_surface(cfg.manifest,inputs,target,samples,model)
        # Newton may occasionally return a finite separation with coincident
        # witnesses and an undefined (zero) normal.  Preserve that reported
        # penetration in the objective and validity metrics, but do not let an
        # undefined direction abort the complete training run or fabricate a
        # collision gradient.  Every occurrence remains auditable.
        from functools import partial
        if cfg.architecture=='heightmap_v1':
            from climb00_pipeline.next_interaction_heightmap import objective as surface_objective
            summary['heightmap']={
                'schema':'root_yaw_heightmap_v1','resolution_m':.02,'rows':71,'cols':61,
                'forward_range_m':[-.4,1.0],'lateral_range_m':[-.6,.6],
                'terrain_input_excludes_analytic_faces':True,
                'newton_truth_unchanged':True,'learned_pose_refinements':2,
                'penetration_tail_objective':'quartic Newton depth, worst batch quintile x4',
            }
        elif cfg.architecture=='heightmap_v2':
            from climb00_pipeline.next_interaction_heightmap_v2 import objective as surface_objective
            summary['heightmap']={
                'schema':'root_yaw_heightmap_v2','resolution_m':.02,'rows':71,'cols':61,
                'terrain_input_excludes_analytic_faces':True,'actual_root_yaw_frame':True,
                'part_to_spatial_cross_attention':True,'learned_pose_refinements':0,
                'categorical_pose_conditioning_gradient':'detached','penetration_tail_objective':None,
            }
        elif cfg.architecture in ('heightmap_v3','heightmap_v3_coupled','heightmap_v3_robust'):
            from climb00_pipeline.next_interaction_heightmap_v3 import objective as surface_objective
            summary['heightmap']={
                'schema':'root_yaw_heightmap_v3','resolution_m':.02,'rows':71,'cols':61,
                'terrain_input_excludes_analytic_faces':True,'actual_root_yaw_frame':True,
                'latent_memory_rows':36,'latent_memory_cols':31,
                'part_to_spatial_cross_attention_layers':2,
                'pose_to_spatial_cross_attention_layers':1,
                'explicit_surface_intermediate':False,'learned_pose_refinements':0,
                'categorical_pose_conditioning_gradient':(
                    'coupled' if cfg.architecture in ('heightmap_v3_coupled','heightmap_v3_robust') else 'detached'),
                'heightmap_supersample':2 if cfg.architecture=='heightmap_v3_robust' else 1,
                'penetration_tail_objective':None,
            }
        elif cfg.architecture=='heightmap_v4_bound':
            from climb00_pipeline.next_interaction_heightmap_v4 import objective as surface_objective
            summary['heightmap']={
                'schema':'root_yaw_heightmap_v4_bound','resolution_m':.02,'rows':71,'cols':61,
                'terrain_input_excludes_analytic_faces':True,'actual_root_yaw_frame':True,
                'latent_memory_rows':36,'latent_memory_cols':31,'heightmap_supersample':1,
                'heightmap_cell_semantics':'single_center_point_ground_or_top',
                'per_part_hard_spatial_binding_soft_gradient':True,
                'shared_binding_for_contact_and_pose':True,
                'direct_active_part_to_pose_path':True,
                'predicted_intent_newton_consistency':'all_detached_weight_0.25',
                'binding_supervision':'3d_local_gaussian_heatmap_ce_sigma_4cm',
                'binding_pretrain_steps':cfg.binding_pretrain_steps,
                'event_index_input':False,'projection':False,'penetration_tail_objective':None,
            }
        elif cfg.architecture=='heightmap_v5_joint_bound':
            from climb00_pipeline.next_interaction_heightmap_v4 import joint_objective as surface_objective
            summary['heightmap']={
                'schema':'root_yaw_heightmap_v5_joint_bound','resolution_m':.02,'rows':71,'cols':61,
                'terrain_input_excludes_analytic_faces':True,'actual_root_yaw_frame':True,
                'latent_memory_rows':36,'latent_memory_cols':31,'heightmap_supersample':1,
                'heightmap_cell_semantics':'single_center_point_ground_or_top',
                'binding_supervision':'3d_local_gaussian_heatmap_ce_sigma_4cm',
                'binding_pretrain_steps':cfg.binding_pretrain_steps,
                'pose_decoder':'single_global_multi_constraint_transformer',
                'independent_part_pose_delta':False,'binding_point_pull_loss':False,
                'event_index_input':False,'projection':False,'penetration_tail_objective':None,
            }
        loss_function=partial(
            surface_objective,
            invalid_witness_policy='detach',
            witness_audit_path=cfg.output/'invalid_newton_witnesses.jsonl',
        )
        summary['invalid_newton_witness_policy'] = {
            'mode': 'retain_scalar_detach_undefined_gradient',
            'audit': 'invalid_newton_witnesses.jsonl',
            'geometry_valid_required_for_success': True,
        }
    elif cfg.contact_objective=='legacy_anchor':
        if cfg.architecture=='joint_v2':summary['joint_interaction']=prepare_supervision(cfg.manifest,inputs,target,samples)
    else:raise ValueError('Unknown contact objective')
    model_input_keys=(('current_q','current_contact','current_anchor','current_surface','heightmap')
                      if cfg.architecture in ('heightmap_v1','heightmap_v2','heightmap_v3','heightmap_v3_coupled','heightmap_v3_robust','heightmap_v4_bound','heightmap_v5_joint_bound') else tuple(inputs))
    def predict(batch_ids):
        batch=take(inputs,batch_ids)
        return model(**{key:batch[key] for key in model_input_keys})
    remap_path=os.environ.get('SOMAFORGE_NEWTON_FINGERPRINT_REMAP')
    if remap_path:
        summary['newton_fingerprint_remap']=remap_newton_fingerprints(target,remap_path)
    (cfg.output/'dataset.json').write_text(json.dumps(summary,indent=2))
    config={k:str(v) if isinstance(v,Path) else v for k,v in asdict(cfg).items()}
    (cfg.output/'config.json').write_text(json.dumps(config,indent=2))
    print(json.dumps(dict(dataset=summary)),flush=True)
    train=split['train']
    if cfg.mode=='gate':
        # A complete observed training trajectory, not a fabricated phase ID.
        source=samples[int(train[0])].source
        train=torch.tensor([int(i) for i in train if samples[int(i)].source==source],device=device)
        print(json.dumps(dict(gate_samples=len(train),source=source)),flush=True)
    optimizer=torch.optim.AdamW(model.parameters(),lr=cfg.learning_rate,weight_decay=1e-5)
    steps=cfg.gate_steps if cfg.mode=='gate' else cfg.epochs
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,steps,eta_min=cfg.learning_rate*.1)
    best=float('inf');best_joint=-1.;best_step=0;started=time.perf_counter();history=[]
    start_step=0
    if cfg.warm_start is not None:
        checkpoint=torch.load(cfg.warm_start,map_location=device,weights_only=False)
        source_architecture=checkpoint['config'].get('architecture')
        compatible_heightmap=(
            (cfg.architecture=='heightmap_v3_robust'
             and source_architecture in ('heightmap_v3','heightmap_v3_coupled'))
            or (cfg.architecture=='heightmap_v4_bound'
                and source_architecture in ('heightmap_v3','heightmap_v3_coupled','heightmap_v3_robust'))
            or (cfg.architecture=='heightmap_v5_joint_bound'
                and source_architecture in ('heightmap_v4_bound','heightmap_v3_coupled'))
        )
        if source_architecture!=cfg.architecture and not compatible_heightmap:
            raise ValueError('Warm-start architecture mismatch')
        if str(checkpoint['robot_asset_json'])!=str(encode_robot_asset_json()):
            raise ValueError('Warm-start robot asset mismatch')
        incompatible=model.load_state_dict(checkpoint['model'],strict=not compatible_heightmap)
        print(json.dumps(dict(warm_started_from=str(cfg.warm_start),
                              warm_start_step=int(checkpoint['step']),optimizer_reset=True,
                              missing_keys=list(incompatible.missing_keys),
                              unexpected_keys=list(incompatible.unexpected_keys))),flush=True)
    if cfg.resume is not None:
        if cfg.warm_start is not None:raise ValueError('Cannot combine resume and warm start')
        checkpoint=torch.load(cfg.resume,map_location=device,weights_only=False)
        if checkpoint['config'].get('architecture','independent_v1')!=cfg.architecture:
            raise ValueError('Resume architecture mismatch')
        if checkpoint['dataset']!=summary:raise ValueError('Resume dataset/contract mismatch')
        if str(checkpoint['robot_asset_json'])!=str(encode_robot_asset_json()):raise ValueError('Resume robot asset mismatch')
        for key in ('mode','width','layers','batch_size','epochs','gate_steps','learning_rate','seed'):
            if checkpoint['config'][key]!=config[key]:raise ValueError(f'Resume config mismatch: {key}')
        start_step=int(checkpoint['step'])
        if not 0<start_step<steps:raise ValueError('Resume step outside training horizon')
        model.load_state_dict(checkpoint['model'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        scheduler.load_state_dict(checkpoint['scheduler'])
        torch.set_rng_state(checkpoint['rng_state'].cpu())
        if 'cuda_rng_state' in checkpoint and device.type=='cuda':
            torch.cuda.set_rng_state(checkpoint['cuda_rng_state'].cpu(),device)
        print(json.dumps(dict(resumed_from=str(cfg.resume),start_step=start_step,
                              learning_rate=optimizer.param_groups[0]['lr'],early_stopping=cfg.early_stopping,
                              exact_cuda_rng_restored='cuda_rng_state' in checkpoint)),flush=True)

    @torch.no_grad()
    def evaluate(ids):
        model.eval();totals={};count=0;maxima={}
        for batch_ids in ids.split(cfg.batch_size):
            prediction=predict(batch_ids)
            _,m=loss_function(model,prediction,take(target,batch_ids),take(scene,batch_ids))
            for key,value in m.items():
                totals[key]=totals.get(key,0.)+float(value.sum())
                if key in ('contact_max_cm','penetration_cm','joint_violation_rad','intent_margin_excess_cm',
                           'surface_margin_excess_cm','start_material_motion_max_cm','demonstration_anchor_max_cm',
                           'newton_fullbody_penetration_cm','binding_contact_max_cm',
                           'binding_realization_max_cm'):
                    maxima[key]=max(maxima.get(key,0.),float(value.max()))
            count+=len(batch_ids)
        model.train()
        return {**{k:v/count for k,v in totals.items()},'maxima':maxima}

    def save(name,step,metrics):
        torch.save(dict(schema='next_interaction_predictor_v1',model=model.state_dict(),optimizer=optimizer.state_dict(),
            scheduler=scheduler.state_dict(),step=step,metrics=metrics,config=config,dataset=summary,
            robot_asset_json=encode_robot_asset_json(),rng_state=torch.get_rng_state(),
            **({'cuda_rng_state':torch.cuda.get_rng_state(device)} if device.type=='cuda' else {})),cfg.output/name)

    if cfg.closed_loop_steps < 1 or cfg.closed_loop_steps > 4:
        raise ValueError('closed_loop_steps must be in [1,4]')
    if not 0 < cfg.closed_loop_recovery_weight <= 1:
        raise ValueError('closed_loop_recovery_weight must be in (0,1]')
    if not 0 < cfg.closed_loop_batch_fraction <= 1:
        raise ValueError('closed_loop_batch_fraction must be in (0,1]')
    if cfg.closed_loop_severe_penetration_m <= 0:
        raise ValueError('closed_loop_severe_penetration_m must be positive')
    if not 0 <= cfg.neighborhood_batch_fraction <= 1:
        raise ValueError('neighborhood_batch_fraction must be in [0,1]')
    if cfg.neighborhood_xy_m < 0:
        raise ValueError('neighborhood_xy_m must be nonnegative')
    if cfg.binding_pretrain_steps < 0 or cfg.binding_pretrain_steps >= steps:
        raise ValueError('binding_pretrain_steps must be in [0, steps)')
    if cfg.binding_pretrain_steps and cfg.architecture not in ('heightmap_v4_bound','heightmap_v5_joint_bound'):
        raise ValueError('Binding pretraining is restricted to bound heightmap models')
    if cfg.neighborhood_batch_fraction and cfg.architecture != 'heightmap_v3_robust':
        raise ValueError('Neighborhood supervision is restricted to heightmap_v3_robust')
    if cfg.architecture == 'heightmap_v3_robust' and cfg.neighborhood_batch_fraction <= 0:
        raise ValueError('heightmap_v3_robust requires neighborhood_batch_fraction > 0')
    if cfg.closed_loop_steps > 1 and cfg.architecture != 'heightmap_v3':
        raise ValueError('Closed-loop training pilot is restricted to heightmap_v3')
    next_row={}
    for motion in sorted({sample.motion_id for sample in samples}):
        sequence=sorted((i for i,sample in enumerate(samples) if sample.motion_id==motion),
                        key=lambda i:samples[i].current_frame)
        for left,right in zip(sequence,sequence[1:]):
            if samples[left].target_frame==samples[right].current_frame:next_row[left]=right
    if cfg.closed_loop_steps>1:
        allowed=set(int(i) for i in train)
        starts=[]
        for candidate in allowed:
            cursor=candidate
            for _ in range(cfg.closed_loop_steps-1):
                cursor=next_row.get(cursor,-1)
                if cursor not in allowed:break
            else:starts.append(candidate)
        if not starts:raise ValueError('No complete closed-loop training windows')
        unroll_starts=torch.tensor(starts,device=device)
        summary['closed_loop_training']={
            'schema':'actual_newton_teacher_sequence_unroll_v1','steps':cfg.closed_loop_steps,
            'windows':len(starts),'state_gradient':'truncated','event_index_model_input':False,
            'current_contact':'actual Newton/MJWarp plus shared primary-face selection',
            'expert':'next contiguous demonstrated contact event',
            'teacher_progress':'advance only after actual Newton target topology is achieved',
            'recovery_weight':cfg.closed_loop_recovery_weight,
            'rollout_batch_fraction':cfg.closed_loop_batch_fraction,
            'nominal_replay_fraction':1-cfg.closed_loop_batch_fraction,
            'severe_penetration_termination_m':cfg.closed_loop_severe_penetration_m,
            'termination_is_not_contact_label':True,
        }
        (cfg.output/'dataset.json').write_text(json.dumps(summary,indent=2))
    if cfg.neighborhood_batch_fraction:
        summary['neighborhood_supervision']={
            'schema':'expert_event_local_recovery_v1',
            'batch_fraction':cfg.neighborhood_batch_fraction,
            'root_yaw_xy_uniform_m':cfg.neighborhood_xy_m,
            'target':'same demonstrated next interaction in the unchanged scene frame',
            'current_contact':'fresh Newton/MJWarp constraint activation plus shared primary-face selection',
            'role_relabel':'actual perturbed current contact to unchanged target topology',
            'heightmap':'2 cm root-yaw, 2x2 area-filtered',
            'event_index_model_input':False,'closed_loop_rollout':False,
        }
        (cfg.output/'dataset.json').write_text(json.dumps(summary,indent=2))

    def advanced_ids(batch_ids, achieved):
        values=[]
        for row,done in zip(batch_ids.detach().cpu().tolist(),achieved.detach().cpu().tolist()):
            values.append(next_row.get(row,row) if done else row)
        return torch.tensor(values,device=device)

    def q_observation(q, target_batch, scene_batch):
        from climb00_pipeline.newton_witness_loss import query_local_distances
        from somaforge_core.contact_face_selection import select_contact_pairs
        world_frame=(target_batch['newton_world_origin'],target_batch['newton_world_basis'])
        rows,observed=query_local_distances(model.fk,q,scene_batch,
            world_frame=world_frame,fingerprints=target_batch['newton_model_fingerprint'])
        catalogs=observed.get('surface_catalog_by_sample')
        if catalogs is None:catalogs=[observed['surface_catalog']]*len(rows)
        masks=[];surfaces=[];anchors=[]
        for pairs,catalog in zip(rows,catalogs):
            active=[pair for pair,_ in pairs if pair['constraint_active'] and pair['allocated']]
            selected=select_contact_pairs([active],catalog)
            masks.append(selected['contact_part_mask'][0])
            surfaces.append(selected['contact_surface'][0])
            anchors.append(selected['contact_position_w'][0])
        penetration=[]
        for row in observed['full_robot_separation']:
            depth=0.
            for key in ('worst_terrain','worst_self'):
                witness=row.get(key)
                if witness is not None:depth=max(depth,-float(witness['dist']))
            penetration.append(max(0.,depth))
        return (rows,observed),torch.as_tensor(np.asarray(masks),device=device),\
            torch.as_tensor(np.asarray(surfaces),device=device),\
            torch.as_tensor(np.asarray(anchors),device=device),\
            torch.as_tensor(penetration,device=device)

    def rollout_observation(prediction, target_batch, scene_batch):
        return q_observation(prediction.qpos,target_batch,scene_batch)

    def neighborhood_inputs(batch_ids):
        from climb00_pipeline.dagger_supervision import recovery_roles
        from climb00_pipeline.next_interaction_heightmap_v2 import (
            _root_yaw_basis,render_root_yaw_box_heightmaps)
        input_batch=take(inputs,batch_ids);target_batch=take(target,batch_ids);scene_batch=take(scene,batch_ids)
        q=input_batch['current_q'].detach().clone();basis,_=_root_yaw_basis(q)
        offset=(2*torch.rand((len(q),2),device=device)-1)*cfg.neighborhood_xy_m
        q[:,:3]=q[:,:3]+torch.einsum('bij,bj->bi',basis[:,:,:2],offset)
        _,actual_contact,actual_surface,actual_anchor,_=q_observation(q,target_batch,scene_batch)
        active=target_batch['role']!=0;dynamic_target=dict(target_batch)
        dynamic_target['role']=recovery_roles(
            actual_contact,actual_surface,active,target_batch['surface'],target_batch['role'])
        heightmap=render_root_yaw_box_heightmaps(
            scene_batch['box_center'].detach().cpu().numpy(),
            scene_batch['box_rotation'].detach().cpu().numpy(),
            scene_batch['box_half_extents'].detach().cpu().numpy(),
            scene_batch['ground_height'].detach().cpu().numpy(),q.detach().cpu().numpy(),supersample=2)
        dynamic_inputs=dict(input_batch,current_q=q,current_contact=actual_contact,
                            current_anchor=actual_anchor,current_surface=actual_surface,
                            heightmap=torch.as_tensor(heightmap,device=device))
        return dynamic_inputs,dynamic_target,scene_batch

    def next_rollout_inputs(prediction,current_contact,current_surface,current_anchor,scene_batch):
        from climb00_pipeline.next_interaction_heightmap_v2 import render_root_yaw_box_heightmaps
        q=prediction.qpos.detach()
        heightmap=render_root_yaw_box_heightmaps(
            scene_batch['box_center'].detach().cpu().numpy(),
            scene_batch['box_rotation'].detach().cpu().numpy(),
            scene_batch['box_half_extents'].detach().cpu().numpy(),
            scene_batch['ground_height'].detach().cpu().numpy(),q.cpu().numpy())
        return dict(current_q=q,current_contact=current_contact,current_anchor=current_anchor,
                    current_surface=current_surface,heightmap=torch.as_tensor(heightmap,device=device))

    if cfg.architecture in ('heightmap_v4_bound','heightmap_v5_joint_bound') and cfg.binding_pretrain_steps:
        model.set_binding_pretrain(start_step < cfg.binding_pretrain_steps)
    for step in range(start_step+1,steps+1):
        if cfg.architecture in ('heightmap_v4_bound','heightmap_v5_joint_bound') and step==cfg.binding_pretrain_steps+1:
            model.set_binding_pretrain(False)
            if cfg.architecture=='heightmap_v4_bound':model.activate_binding(0.05)
            print(json.dumps(dict(binding_joint_training_started=step,
                                  binding_strength=.05 if cfg.architecture=='heightmap_v4_bound' else 'zero_initialized_global_decoder')),flush=True)
        begin=time.perf_counter();ids=train[torch.randperm(len(train),device=device)];total=0.
        profile = {key: 0.0 for key in ('predict', 'objective', 'backward', 'optimizer')} if cfg.profile_first_step and step == 1 else None
        def mark():
            if device.type == 'cuda': torch.cuda.synchronize(device)
            return time.perf_counter()
        for batch_ids in ids.split(len(ids) if cfg.mode=='gate' else cfg.batch_size):
            optimizer.zero_grad(set_to_none=True)
            stamp=mark() if profile is not None else 0.
            use_closed_loop=(cfg.closed_loop_steps>1
                             and bool(torch.rand((),device=device)<cfg.closed_loop_batch_fraction))
            use_neighborhood=(cfg.neighborhood_batch_fraction>0
                              and bool(torch.rand((),device=device)<cfg.neighborhood_batch_fraction))
            if use_neighborhood:
                neighborhood,target_batch,scene_batch=neighborhood_inputs(batch_ids)
                pred=model(**{key:neighborhood[key] for key in model_input_keys})
                loss,_=loss_function(model,pred,target_batch,scene_batch)
            elif not use_closed_loop:
                pred=predict(batch_ids)
                if profile is not None: profile['predict']+=mark()-stamp;stamp=mark()
                loss,_=loss_function(model,pred,take(target,batch_ids),take(scene,batch_ids))
            else:
                selection=torch.randint(len(unroll_starts),(len(batch_ids),),device=device)
                batch_ids=unroll_starts[selection]
                rollout_inputs=take(inputs,batch_ids);target_ids=batch_ids;losses=[];weights=[]
                alive=torch.ones(len(batch_ids),device=device)
                for depth in range(cfg.closed_loop_steps):
                    pred=model(**{key:rollout_inputs[key] for key in model_input_keys})
                    target_batch=take(target,target_ids);scene_batch=take(scene,target_ids)
                    query_result,actual_contact,actual_surface,actual_anchor,actual_penetration=rollout_observation(
                        pred,target_batch,scene_batch)
                    dynamic_target=dict(target_batch)
                    if depth:
                        from climb00_pipeline.dagger_supervision import recovery_roles
                        active=dynamic_target['role']!=0
                        dynamic_target['role']=recovery_roles(
                            rollout_inputs['current_contact'],rollout_inputs['current_surface'],active,
                            dynamic_target['surface'],dynamic_target['role'])
                    depth_loss,_=loss_function(model,pred,dynamic_target,scene_batch,
                                               query_override=query_result)
                    weight=1. if depth==0 else cfg.closed_loop_recovery_weight
                    losses.append(depth_loss*alive*weight);weights.append(alive*weight)
                    if depth+1<cfg.closed_loop_steps:
                        target_active=target_batch['role']!=0
                        achieved=(actual_contact==target_active).all(-1)
                        achieved=achieved & torch.where(
                            target_active,actual_surface==target_batch['surface'],True).all(-1)
                        target_ids=advanced_ids(target_ids,achieved)
                        alive=alive*(actual_penetration<=cfg.closed_loop_severe_penetration_m)
                        rollout_inputs=next_rollout_inputs(
                            pred,actual_contact,actual_surface,actual_anchor,scene_batch)
                loss=torch.stack(losses).sum(0)/torch.stack(weights).sum(0).clamp_min(1e-6)
            if profile is not None: profile['objective']+=mark()-stamp;stamp=mark()
            if not torch.isfinite(loss).all():raise RuntimeError('Nonfinite predictor objective')
            loss.mean().backward()
            if profile is not None: profile['backward']+=mark()-stamp;stamp=mark()
            nnorm=torch.nn.utils.clip_grad_norm_(model.parameters(),10.,error_if_nonfinite=True)
            optimizer.step();total+=float(loss.detach().sum())
            if profile is not None: profile['optimizer']+=mark()-stamp
        scheduler.step()
        should_eval=step==1 or step%(50 if cfg.mode=='gate' else cfg.evaluation_every)==0 or step==steps
        if should_eval:
            metrics=evaluate(train if cfg.mode=='gate' else split['validation'])
            row=dict(step=step,train_loss=total/len(train),seconds_per_step=time.perf_counter()-begin,
                     elapsed_seconds=time.perf_counter()-started,metrics=metrics)
            if profile is not None: row['training_profile_seconds']=profile
            contact_score=(metrics['surface_margin_excess_cm']
                           +10*(metrics['newton_unrealized_target_contacts']+metrics['newton_unwanted_contact_parts'])/6
                           if cfg.contact_objective=='surface_region_v1' else metrics['contact_cm'])
            score=(contact_score+10*(1-metrics['contact_exact'])+.1*metrics['body_cm']
                   +metrics['penetration_cm']+100*metrics['maxima']['joint_violation_rad'])
            if cfg.architecture in ('heightmap_v1','heightmap_v2') and cfg.contact_objective=='surface_region_v1':
                # Select a balanced feasible checkpoint.  A one-percent gain in
                # valid contact must not hide a multi-centimeter penetration spike.
                joint=metrics['valid_next_contact']
                score=(100*(1-joint)+2*metrics['maxima']['newton_fullbody_penetration_cm']
                       +contact_score+.1*metrics['body_cm'])
                improved=score<best-1e-5
            elif cfg.contact_objective=='surface_region_v1':
                # Primary ranking is the joint next-contact/nonpenetration rate;
                # continuous loss is only a tie-breaker, never task certification.
                joint=metrics['valid_next_contact']
                improved=joint>best_joint or (joint==best_joint and score<best-1e-5)
            else:
                joint=best_joint;improved=score<best-1e-5
            if improved:best=score;best_joint=joint;best_step=step;save('best.pt',step,metrics)
            save('last.pt',step,metrics)
            history.append(row)
            with (cfg.output/'history.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
            (cfg.output/'progress.json').write_text(json.dumps({**row,'status':'running'},indent=2))
            print(json.dumps(row),flush=True)
            if cfg.mode=='full' and cfg.early_stopping and step-best_step>=cfg.patience:break
    selected_name='last.pt' if not cfg.early_stopping else 'best.pt'
    selected=torch.load(cfg.output/selected_name,map_location=device,weights_only=False)
    model.load_state_dict(selected['model'])
    result=dict(status='complete',selected_checkpoint=selected_name,selected_step=selected['step'],last_step=step,
                start_step=start_step,elapsed_seconds=time.perf_counter()-started)
    if cfg.mode=='gate':
        result['fit']=evaluate(train)
        m=result['fit']
        contact_mean=m.get('contact_cm',m.get('surface_margin_excess_cm'))
        contact_max=m['maxima'].get('contact_max_cm',m['maxima'].get('surface_margin_excess_cm'))
        result['gate_checks']=dict(contact_mean=contact_mean<1.,contact_max=contact_max<3.,
                                  contact_topology=m['contact_exact']>.95,touchdown=m['touchdown_exact']>.95,
                                  posture=m['joint_rmse_rad']<.2,
                                  joint_feasibility=m['maxima']['joint_violation_rad']<.01)
        result['passed']=all(result['gate_checks'].values())
        if cfg.contact_objective=='surface_region_v1':
            result['gate_checks']['valid_next_contact']=m['valid_next_contact']==1.
            result['passed']=all(result['gate_checks'].values())
    else:
        result['validation']=evaluate(split['validation']);result['test']=evaluate(split['test'])
    (cfg.output/'result.json').write_text(json.dumps(result,indent=2))
    (cfg.output/'progress.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
    if cfg.mode=='gate' and not result['passed']:raise SystemExit(2)


if __name__=='__main__':main()
