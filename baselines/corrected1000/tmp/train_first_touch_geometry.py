"""Independent contact-first height-response pilot; never promotes a baseline.

Both arms start from frozen 1420. Three continuously sampled heights are a
bounded pilot, NOT dense coverage or fresh online geometry each minibatch.
Only authoritative scene queries decide achieved contacts. Shifted anchors
are approach hints, not newly certified expert endpoints.
"""
from dataclasses import dataclass
from pathlib import Path
import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import time


@dataclass
class Config:
    output: Path
    updates: int = 150
    batch_size: int = 16
    seed: int = 20260915
    learning_rate: float = 0.00003
    pose_weight: float = 0.02


def terrain_text(source, scale):
    """Exact vertical scaling of this single box, preserving ground and faces."""
    if not 0.85 <= scale <= 1.15:
        raise ValueError('Outside declared experiment range')
    lines = []
    for line in source.splitlines():
        if line.startswith('v '):
            _, x, y, z = line.split()
            line = f'v {x} {y} {float(z)*scale:.10f}'
        lines.append(line)
    return '\n'.join(lines)+'\n'


class Workers:
    def __init__(self, root, heights, device, *, query_worlds=1, tensor_transport=False):
        self.processes = []; self.logs = []; self.entries = {}
        self.root, self.heights, self.device = root, heights, device
        self.query_worlds = query_worlds
        self.tensor_transport = tensor_transport
        self.tensor_clients = {}

    def __enter__(self):
        from newton_scene_router_audit import CHECKPOINT
        base = json.loads(Path('tmp/newton_contact_sources_v1/1789326506727043514/scene_2/manifest.json').read_text())
        mesh = Path(base['terrains'][0]['terrain_file']).read_text()
        self.root.mkdir(parents=True)
        try:
            for h in self.heights:
                folder = self.root/f'h{h:.8f}'; folder.mkdir()
                terrain = folder/'terrain.obj'; terrain.write_text(terrain_text(mesh,h))
                manifest = copy.deepcopy(base)
                manifest['terrains'][0].update(terrain_file=str(terrain.resolve()), terrain_sha256=hashlib.sha256(terrain.read_bytes()).hexdigest())
                mp = folder/'manifest.json'; mp.write_text(json.dumps(manifest,indent=2))
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
                log = (folder/'worker.log').open('x'); self.logs.append(log)
                args = [sys.executable,'scripts/serve_newton_contact_queries.py','--checkpoint',CHECKPOINT,
                    '--motion-manifest',str(mp),'--binding',str(folder/'binding.json'),'--create-native-binding',
                    '--inspection-output',str(folder/'model.json'),'--query-nconmax','2048','--query-njmax','16384',
                    '--port',str(port),'--device',self.device,'--capture-contact-sources',
                    '--query-worlds',str(self.query_worlds)]
                if self.tensor_transport:
                    key = os.urandom(32)
                    auth_path = folder/'tensor_auth.bin'
                    with os.fdopen(os.open(auth_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
                        stream.write(key)
                    args += ['--tensor-auth', str(auth_path)]
                process = subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
                self.processes.append(process)
                self.entries[h] = dict(folder=folder,endpoint=f'http://127.0.0.1:{port}', port=port)
            deadline = time.monotonic()+240
            while not all('"ready": true' in (e['folder']/'worker.log').read_text() for e in self.entries.values()):
                if any(p.poll() is not None for p in self.processes) or time.monotonic()>deadline:
                    raise RuntimeError(f'Scene startup failed: {self.root}')
                time.sleep(1)
            for h,e in self.entries.items():
                e['model'] = json.loads((e['folder']/'model.json').read_text())
                e['fp'] = e['model']['model_fingerprint']
                levels = [z for b in e['model']['terrain_mesh_bounds'] for z in b['z_levels']]
                # This corpus uses a height SCALE, not a box height in metres.
                # The scene builder adds a 4 cm thick ground slab below z=0.
                reference=json.loads(Path('tmp/newton_contact_sources_v1/1789326506727043514/scene_2/model.json').read_text())
                reference_levels=[z for b in reference['terrain_mesh_bounds'] for z in b['z_levels']]
                if (abs(max(levels)-0.70449438*h)>2e-5 or 0. not in levels
                        or min(levels)!=min(reference_levels)):
                    raise ValueError('Actual Newton terrain differs from requested height')
            # Compare workers produced by the same current Newton build.  A
            # frozen pre-upgrade model.json is not a valid byte-level oracle:
            # current Newton expands capsule/cylinder scale components that
            # older inspection output stored as zeros.  Cross-height equality
            # still catches an accidental robot/config mutation without
            # rejecting that representation-only upgrade.
            current_reference = next(iter(self.entries.values()))['model']
            for h, e in self.entries.items():
                for key in ('shape_body','shape_type','shape_transform','shape_scale','shape_margin','shape_gap'):
                    if e['model'][key] != current_reference[key]:
                        raise ValueError(
                            f'Unexpected asset/config change at height {h}: {key}'
                        )
            from somaforge_core.newton_scene_router import NewtonSceneRouter
            self.router = NewtonSceneRouter({e['fp']:e['endpoint'] for e in self.entries.values()},workers=3)
            if self.tensor_transport:
                from somaforge_core.newton_tensor_transport import TensorSceneClient, TensorSceneRouter
                for index, (height, entry) in enumerate(self.entries.items()):
                    client = TensorSceneClient(entry['port'], (entry['folder']/'tensor_auth.bin').read_bytes())
                    if client.metadata['provenance']['model_fingerprint'] != entry['fp']:
                        raise ValueError('Tensor scene fingerprint differs from actual model inspection')
                    self.tensor_clients[index] = client
                    entry['scene_id'] = index
                self.tensor_router = TensorSceneRouter(self.tensor_clients)
            return self
        except Exception:
            self.__exit__(None,None,None); raise

    def __exit__(self,*unused):
        for client in self.tensor_clients.values():
            try: client.close()
            except (EOFError, BrokenPipeError, OSError): pass
        for p in self.processes:
            if p.poll() is None: p.terminate()
        for p in self.processes: p.wait(timeout=30)
        for log in self.logs: log.close()


def run(cfg, device):
    import numpy as np
    import torch
    import train_next_interaction_v1 as train
    import somaforge_core.newton_scene_router as router
    from climb00_pipeline.next_interaction_joint import JointInteractionPredictor
    from climb00_pipeline.next_interaction_surface import prepare_supervision, objective
    from climb00_pipeline.neural_infiller import _quaternion_matrix_wxyz
    from somaforge_core.robot_assets import encode_robot_asset_json
    import climb00_pipeline.newton_witness_loss as witness
    from somaforge_core.contact_face_selection import select_contact_pairs

    if cfg.updates<1 or cfg.batch_size<1 or not 0<=cfg.pose_weight<=0.2: raise ValueError('Invalid pilot settings')
    root=cfg.output; root.mkdir(parents=True,exist_ok=False)
    def save(name,value): (root/name).write_text(json.dumps(value,indent=2))
    torch.set_num_threads(2); torch.manual_seed(cfg.seed)
    ckpath=Path('tmp/predictor_topology_full_retrain/1789387338727408985/predictor/last.pt')
    ck=torch.load(ckpath,map_location=device,weights_only=False)
    config=dict(ck['config'])
    for k in ('manifest','q_cache','output'): config[k]=Path(config[k])
    basecfg=train.Config(**config)
    model=JointInteractionPredictor(basecfg.width,basecfg.layers).to(device)
    x,t,s,splits,samples,identity=train.prepare(basecfg,model,torch.device(device))
    prepare_supervision(basecfg.manifest,x,t,samples,model)
    first=[]
    for mid in sorted({z.motion_id for z in samples}):
        ids=[i for i,z in enumerate(samples) if z.motion_id==mid and bool((t['role'][i,2:4]==1).any()) and not bool(x['current_contact'][i,2:4].any())]
        if ids: first.append(min(ids,key=lambda i:samples[i].current_frame))
    # Both arms use the same canonical first-touch intent: feet persist, hands touch down.
    train_ids=[i for i in first if abs(samples[i].height-1.)<1e-5 and t['role'][i].tolist()==[2,2,1,1,0,0]]
    if len(train_ids)<10: raise ValueError('Insufficient matched first-touch starts')
    rng=np.random.default_rng(cfg.seed)
    continuous=sorted(float(rng.uniform(a,b)) for a,b in [(.95,.975),(.975,1.025),(1.025,1.05)])
    save('config.json',dict(schema='first_touch_height_response_pilot_v1',initial_checkpoint=str(ckpath),initial_sha256=hashlib.sha256(ckpath.read_bytes()).hexdigest(),
        updates_per_arm=cfg.updates,batch_size=cfg.batch_size,seed=cfg.seed,pose_weight=cfg.pose_weight,
        discrete_heights=[.95,1.,1.05],sampled_heights=continuous,heldout_heights=[.9,1.1],training_samples=train_ids,
        robot_asset_json=encode_robot_asset_json(),scope='1420 adaptation mechanism pilot; not from-scratch reproduction, full-trajectory training, or certified reachability',
        approach_hint='old material anchor shifted with target surface; not expert pose or contact truth',
        model_inputs=list(x),checkpoint_selection='fixed update budget; heldout not used for selection'))
    take=lambda bank,ids:{k:v[ids].clone() for k,v in bank.items()}
    captured={}
    original_query=witness.query_local_distances
    def capture_query(*args,**kwargs):
        result=original_query(*args,**kwargs);captured['observed']=result[1];return result
    witness.query_local_distances=capture_query
    def batch(ids,h,fp,alter):
        xx,tt,ss=take(x,ids),take(t,ids),take(s,ids)
        if alter:
            dz=0.70449438*(h-1.)
            xx['faces'][:,1,2]+=dz
            ss['box_center'][:,2]+=dz/2; ss['box_half_extents'][:,2]+=dz/2
            tt['anchor'][:,:,2]+=dz*(tt['surface']==1)
        tt['observed_faces']=xx['faces']
        tt['newton_model_fingerprint'][:]=torch.tensor(list(bytes.fromhex(fp)),dtype=torch.uint8,device=device)
        return xx,tt,ss
    def loss_at(model,xx,tt,ss):
        pred=model(**xx)
        loss,metrics=objective(model,pred,tt,ss,invalid_witness_policy='detach',witness_audit_path=root/'invalid_witnesses.jsonl')
        q=pred.qpos
        rot=(_quaternion_matrix_wxyz(q[:,3:7])-_quaternion_matrix_wxyz(tt['q'][:,3:7])).square().mean((1,2))
        pose=((q[:,:3]-tt['q'][:,:3])/.1).square().mean(-1)+rot/.3**2+((q[:,7:]-tt['q'][:,7:])/.5).square().mean(-1)
        loss=loss-(.2-cfg.pose_weight)*pose
        observed=captured['observed']
        catalogs=observed.get('surface_catalog_by_sample')
        if catalogs is None:catalogs=[observed['surface_catalog']]*len(q)
        both=[]
        for j,cat in enumerate(catalogs):
            actual=select_contact_pairs([observed['pairs'][j]],cat)
            mask=actual['contact_part_mask'][0];surface=actual['contact_surface'][0]
            both.append(all(bool(mask[k]) and int(surface[k])==int(tt['surface'][j,k]) for k in (2,3)))
        metrics['both_hands_realized']=q.new_tensor(both)
        metrics['optimized_loss']=loss
        return loss,metrics
    checkpoints={'baseline':ck['model']}
    # Identical minibatch indices and scene index schedule in both arms.
    schedule=np.random.default_rng(cfg.seed+1)
    batches=[(int(schedule.integers(3)),schedule.choice(train_ids,cfg.batch_size,replace=True).tolist()) for _ in range(cfg.updates)]
    for arm,heights in [('discrete',[.95,1.,1.05]),('sampled',continuous)]:
        save('status.json',dict(stage='starting_scenes',arm=arm))
        with Workers(root/arm,heights,device) as workers:
            router.configured_router=lambda:workers.router
            model.load_state_dict(ck['model']);model.train()
            # Changing terrain must not silently invalidate current-contact inputs.
            from climb00_pipeline.newton_witness_loss import query_local_distances
            from somaforge_core.contact_face_selection import select_contact_pairs
            audits=[]
            for h in heights:
                xx,tt,ss=batch(train_ids,h,workers.entries[h]['fp'],True)
                _,observed=query_local_distances(model.fk,xx['current_q'],ss,
                    world_frame=(tt['newton_world_origin'],tt['newton_world_basis']),fingerprints=tt['newton_model_fingerprint'])
                catalogs=observed.get('surface_catalog_by_sample')
                if catalogs is None:catalogs=[observed['surface_catalog']]*len(train_ids)
                for j,idx in enumerate(train_ids):
                    actual=select_contact_pairs([observed['pairs'][j]],catalogs[j])
                    mask=torch.as_tensor(actual['contact_part_mask'][0],device=device,dtype=torch.bool)
                    surface=torch.as_tensor(actual['contact_surface'][0],device=device)
                    ok=bool((mask==xx['current_contact'][j]).all() and (surface[mask]==xx['current_surface'][j,mask]).all())
                    audits.append(dict(height=h,sample=idx,current_contacts_valid=ok))
            save(f'{arm}_input_audit.json',audits)
            if not all(z['current_contacts_valid'] for z in audits):
                raise RuntimeError('Changed scene invalidates current-contact inputs; do not train stale labels')
            optimizer=torch.optim.AdamW(model.parameters(),lr=cfg.learning_rate,weight_decay=0.)
            for step,(hi,ids) in enumerate(batches,1):
                h=heights[hi];xx,tt,ss=batch(ids,h,workers.entries[h]['fp'],True)
                optimizer.zero_grad(set_to_none=True);loss,metrics=loss_at(model,xx,tt,ss)
                if not torch.isfinite(loss).all(): raise RuntimeError('Nonfinite training loss')
                loss.mean().backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10.,error_if_nonfinite=True);optimizer.step()
                row=dict(arm=arm,step=step,height=h,loss=float(loss.detach().mean()),metrics={k:float(v.detach().float().mean()) for k,v in metrics.items() if v.ndim==1})
                with (root/'history.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
                if step==1 or step%10==0:
                    save('status.json',dict(stage='training',**row));print(json.dumps(row),flush=True)
            checkpoints[arm]={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            torch.save(dict(model=checkpoints[arm],config=ck['config'],step=cfg.updates,robot_asset_json=encode_robot_asset_json(),experiment=str(root/'config.json')),root/f'{arm}.pt')
            model.eval();train_eval={}
            with torch.no_grad():
                for h in heights:
                    xx,tt,ss=batch(train_ids,h,workers.entries[h]['fp'],True)
                    _,metrics=loss_at(model,xx,tt,ss)
                    train_eval[str(h)]={k:float(v.float().mean()) for k,v in metrics.items() if v.ndim==1}
            save(f'{arm}_train_evaluation.json',train_eval)
    results={}
    save('status.json',dict(stage='heldout_evaluation'))
    with Workers(root/'heldout',[.9,1.1],device) as workers:
        router.configured_router=lambda:workers.router
        for arm,state in checkpoints.items():
            model.load_state_dict(state);model.eval();results[arm]={}
            for h in [.9,1.1]:
                ids=[i for i in first if abs(samples[i].height-h)<1e-5];rows=[]
                with torch.no_grad():
                    for start in range(0,len(ids),cfg.batch_size):
                        chosen=ids[start:start+cfg.batch_size]
                        xx,tt,ss=batch(chosen,h,workers.entries[h]['fp'],False)
                        _,metrics=loss_at(model,xx,tt,ss)
                        rows.extend(dict(sample=i,**{k:float(v[j]) for k,v in metrics.items() if v.ndim==1}) for j,i in enumerate(chosen))
                results[arm][str(h)]=dict(count=len(rows),metrics={k:sum(z[k] for z in rows)/len(rows) for k in rows[0] if k!='sample'},rows=rows)
                save('evaluation.json',results)
    save('status.json',dict(stage='complete',evaluation=str(root/'evaluation.json')))


if __name__=='__main__':
    from holosoma.utils.sim_utils import parse_isaaclab_launcher_args
    official=parse_isaaclab_launcher_args('Contact-first height-response pilot')
    import tyro
    cfg=tyro.cli(Config)
    run(cfg,official.device or 'cuda:0')
