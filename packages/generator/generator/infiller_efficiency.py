"""Synchronized component profiling and immutable boundary batches."""
from contextlib import contextmanager
from collections import defaultdict
import time
import torch


class ComponentTimer:
    def __init__(self, device):
        self.device = device
        self.seconds = defaultdict(float)
        self.calls = defaultdict(int)
        self.synchronize_components = True

    @contextmanager
    def stage(self, name):
        if not self.synchronize_components:
            yield
            return
        if str(self.device).startswith('cuda'):
            torch.cuda.synchronize(self.device)
        begun = time.perf_counter()
        try:
            yield
        finally:
            if str(self.device).startswith('cuda'):
                torch.cuda.synchronize(self.device)
            self.seconds[name] += time.perf_counter()-begun
            self.calls[name] += 1


class BoundaryRecordCache:
    """Only immutable endpoints/scene/contract; no generated interior poses.

    All returned pose grids contain two boundaries. This cache is for prefix
    and seam decoding, never pose/contact/velocity teacher supervision.
    """
    def __init__(self, model, records, device):
        self.q = torch.stack([torch.stack((r['q'][0],r['q'][-1])) for r in records]).to(device)
        self.duration = torch.stack([r['duration'] for r in records]).to(device)
        self.count = self.duration.new_tensor([len(r['q']) for r in records])
        self.contract = {k:torch.stack([r['contract'][k] for r in records]).to(device)
                         for k in records[0]['contract']}
        self.scene = {k:torch.stack([r['scene'][k] for r in records]).to(device)
                      for k in records[0]['scene']}
        self.predicts = model.predicts_frames
        if self.predicts:
            if model.frame_training!='decoupled' or any(p.requires_grad for p in model.frame_head.parameters()):
                raise ValueError('Cached durations require a frozen independent frame head')
            with torch.no_grad():
                # Preserve the legacy scalar prefix/seam head computation,
                # including rounding close to half a frame. Pay this once.
                self.predicted = torch.cat([model.frame_count(self.q[i:i+1,0],self.q[i:i+1,-1],
                    {k:v[i:i+1] for k,v in self.contract.items()},
                    {k:v[i:i+1] for k,v in self.scene.items()}) for i in range(len(records))])
        self.device = device

    def batch(self, indices):
        index = torch.as_tensor(indices,device=self.q.device,dtype=torch.long)
        reference = self.duration[index]
        batch = dict(q=self.q[index],duration=reference,
            contract={k:v[index] for k,v in self.contract.items()},scene={k:v[index] for k,v in self.scene.items()})
        if self.predicts:
            predicted = self.predicted[index]
            batch.update(reference_duration=reference,predicted_frames=predicted,
                motion_frames=predicted,duration=(predicted-1)/50,frame_training='decoupled')
        return batch

    def native_batch(self, indices):
        batch = self.batch(indices)
        count = batch['motion_frames'].round() if self.predicts else self.count[indices]
        batch['duration']=(count-1)/50
        batch['native_count']=count
        return batch


def profile_training(cfg, corpus, query, device):
    """Same batches/weights, no optimizer updates and no test examples."""
    import json
    from somaforge_core.published_data import load_published_json
    from generator import train_frozen_predictor_infiller as trainer
    from generator.direct_infiller import load_infiller,collate,prepare_frame_prediction,decode_batch
    from generator.recursive_refinement import adjacent_records,seam_objective
    from generator.infiller_boundary_velocity import SelfGeneratedHistory
    from somaforge_core.robot_assets import decode_robot_asset_json
    saved=trainer.load_published_infiller_input(cfg.checkpoint)
    decode_robot_asset_json(saved['robot_asset_json'],context='Infiller profile checkpoint')
    if saved['corpus']!=trainer.evidence(cfg.corpus) or saved['predictor']!=corpus['predictor']:
        raise ValueError('Profiling checkpoint/corpus/Predictor mismatch')
    model=load_infiller(saved,'cpu').train()
    for p in model.frame_head.parameters(): p.requires_grad_(False)
    trainer.attach_shared_materials(model,corpus,cfg,query)
    model=model.to(device)
    records=trainer.supervision_records(corpus['records'],'train',cfg.training_source)
    schedule=trainer.batches(records,cfg)
    chosen=[]
    for kind in sorted({r['kind'] for r in records}):
        subset=[indices for indices in schedule if records[indices[0]]['kind']==kind]
        subset.sort(key=lambda indices:(len(records[indices[0]]['q']),-len(indices)))
        chosen.extend([subset[0],subset[len(subset)//2],subset[-1]])
    reference=load_published_json('configs/climb00/direct_infiller_v1.json')
    limits={k:torch.tensor(v,device=device) for k,v in reference['smoothness_limits'].items()}
    successors=adjacent_records(records)
    results=[];reference_batches={};equivalence=[]
    for efficient in (False,True):
        cfg.efficient_training=efficient
        for client in query.workers.tensor_clients.values():client.packed_response=efficient
        cache=BoundaryRecordCache(model,records,device) if efficient else None
        history=SelfGeneratedHistory(model,records,device,boundary_cache=cache) if model.conditions_on_velocity else None
        timer=ComponentTimer(device); query.timer=timer
        for repeat in range(cfg.profile_repeats+3):
            timer.synchronize_components=repeat<=cfg.profile_repeats
            timer.seconds.clear();timer.calls.clear()
            torch.cuda.synchronize(device);begun=time.perf_counter()
            audit_seconds=0.
            for indices in chosen:
                model.zero_grad(set_to_none=True)
                if history is not None:history.cache.clear()
                with timer.stage('batch_and_time'):
                    b=prepare_frame_prediction(model,collate([records[i] for i in indices],device))
                with timer.stage('generated_history'):
                    if history is not None:history.condition(b,indices)
                with timer.stage('trajectory_decode'):
                    q=decode_batch(model,b)
                loss,metrics=trainer.unified_objective(model,b,q,limits,query,cfg)
                with timer.stage('seam'):
                    seam,_=seam_objective(model,records,indices,successors,q,device,history=history,boundary_cache=cache,
                        derivative_limits=limits if cfg.witnessed_budgets else None,budget_ratio=cfg.feasible_budget_ratio)
                    loss=loss+cfg.seam_weight*seam
                with timer.stage('backward'):
                    loss.backward()
                if repeat==0:
                    audit_begun=time.perf_counter()
                    key=tuple(indices)
                    gradient=torch.cat([p.grad.detach().flatten() for p in model.parameters() if p.grad is not None]).cpu()
                    if not efficient:
                        reference_batches[key]=(float(loss.detach()),q.detach().cpu(),gradient)
                    else:
                        reference_loss,reference_q,reference_gradient=reference_batches[key]
                        torch.testing.assert_close(q.detach().cpu(),reference_q,atol=2e-5,rtol=1e-5)
                        torch.testing.assert_close(loss.detach().cpu(),torch.tensor(reference_loss),atol=2e-4,rtol=2e-4)
                        torch.testing.assert_close(gradient,reference_gradient,atol=2e-3,rtol=2e-3)
                        equivalence.append(dict(indices=indices,loss_delta=abs(float(loss.detach())-reference_loss),
                            maximum_pose_delta=float((q.detach().cpu()-reference_q).abs().max()),
                            maximum_gradient_delta=float((gradient-reference_gradient).abs().max())))
                    audit_seconds+=time.perf_counter()-audit_begun
            torch.cuda.synchronize(device);total=time.perf_counter()-begun-audit_seconds
            if repeat:
                row=dict(efficient=efficient,repeat=repeat,seconds=dict(timer.seconds),calls=dict(timer.calls),
                    measurement='synchronized_components' if timer.synchronize_components else 'unprofiled_wall',
                    total_seconds=total,
                    measured_batches=len(chosen),segments=sum(map(len,chosen)),
                    query_worlds=cfg.query_worlds,query_batch_size=cfg.query_batch_size)
                results.append(row); print(json.dumps(row),flush=True)
                trainer.dump(cfg.report/'profile_progress.json',dict(status='running',results=results))
        del cache,history
    query.timer=None
    trainer.dump(cfg.report/'profile.json',dict(status='complete',checkpoint=trainer.evidence(cfg.checkpoint),
        corpus=trainer.evidence(cfg.corpus),same_weights_no_optimizer_updates=True,test_used=False,
        batch_indices=chosen,results=results,equivalence=equivalence))
