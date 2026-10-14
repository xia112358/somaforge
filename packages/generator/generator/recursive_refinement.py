"""Training-only recursive coverage and sampled trajectory continuity."""
from collections import defaultdict

import torch
from somaforge_core.g1_kinematics import _quaternion_matrix_wxyz


def role_consistency_loss(logits, actual_contact):
    """A keep role requires current actual contact; other roles remain free.

    This is learning from Newton observations, not an inference-time mask or
    a claim that an intended future contact has been realized.
    """
    if logits.shape != (*actual_contact.shape, 4) or actual_contact.dtype != torch.bool:
        raise ValueError('Expected role logits [...,6,4] and actual boolean contact')
    valid = logits.clone()
    valid[..., 2] = valid[..., 2].masked_fill(~actual_contact, -torch.inf)
    return (torch.logsumexp(logits, -1)-torch.logsumexp(valid, -1)).mean(-1)


def adjacent_records(records):
    """Return true successors only, in the same split, chain and scene."""
    starts = defaultdict(list)
    for i, r in enumerate(records):
        if not r['chain_id'].startswith('isolated_'):
            starts[(r['split'], r['kind'], r['chain_id'], int(r['scene_id']), r['current_frame'])].append(i)
    pairs = {}
    for i, r in enumerate(records):
        key = (r['split'], r['kind'], r['chain_id'], int(r['scene_id']), r['target_frame'])
        matches = starts.get(key, [])
        if len(matches)>1:
            raise ValueError('Ambiguous adjacent trajectory records')
        if matches:
            j = matches[0]
            if not torch.equal(r['q'][-1], records[j]['q'][0]):
                raise ValueError('Adjacent records do not share an exact boundary')
            for name in r['scene']:
                a,b=r['scene'][name],records[j]['scene'][name]
                # Source world-frame conversions differ by a few float32 ULPs
                # even within one immutable Newton scene. This is numerical
                # scene identity tolerance, never a contact distance rule.
                tolerance=8*torch.finfo(a.dtype).eps
                if not torch.allclose(a,b,rtol=tolerance,atol=tolerance):
                    raise ValueError('Adjacent records disagree on scene coordinates')
            pairs[i] = j
    return pairs


def sampled_seam_loss(left, right, left_dt, right_dt, scale, *, target_left=None,target_right=None):
    """Match sampled velocity changes, using each segment's actual dt.

    Optional expert sides retain the demonstrated sampled acceleration.
    Without targets this preserves the historical zero-change objective.
    Rotation-matrix differences avoid quaternion sign artifacts and singular
    derivatives of acos at identity. Scales come from the existing decoder.
    """
    if left.shape[1] != 2 or right.shape[1] != 2:
        raise ValueError('Seam loss expects the two samples on either side')
    lv=(left[:,1]-left[:,0])/left_dt[:,None]
    rv=(right[:,1]-right[:,0])/right_dt[:,None]
    delta=lv-rv
    if (target_left is None)!=(target_right is None):
        raise ValueError('Both expert seam sides must be supplied')
    if target_left is not None:
        delta=delta-((target_left[:,1]-target_left[:,0])/left_dt[:,None]
                     -(target_right[:,1]-target_right[:,0])/right_dt[:,None])
    root=delta[:,:3].norm(dim=-1)/scale[0]
    joint=(delta[:,7:]/scale[7:]).abs().amax(-1)
    lr=_quaternion_matrix_wxyz(left[...,3:7])
    rr=_quaternion_matrix_wxyz(right[...,3:7])
    angular_delta=((lr[:,1]-lr[:,0])/left_dt[:,None,None]
                   -(rr[:,1]-rr[:,0])/right_dt[:,None,None])
    if target_left is not None:
        tl=_quaternion_matrix_wxyz(target_left[...,3:7]);tr=_quaternion_matrix_wxyz(target_right[...,3:7])
        angular_delta=angular_delta-((tl[:,1]-tl[:,0])/left_dt[:,None,None]
                                    -(tr[:,1]-tr[:,0])/right_dt[:,None,None])
    angular=angular_delta.flatten(1).norm(dim=-1)
    angular=angular/(2**.5*2*scale[3])
    penalty=torch.log1p(torch.stack((root,joint,angular),-1).square())
    return penalty.mean(-1)+penalty.amax(-1)


def seam_objective(model, records, indices, successors, q, device, history=None,boundary_cache=None,
                   derivative_limits=None,budget_ratio=1.5):
    if derivative_limits is not None:
        supervised,_=seam_objective(model,records,indices,successors,q,device,history=history,boundary_cache=boundary_cache)
        budget,count=seam_budget_objective(model,records,indices,successors,q,device,history,
                                          boundary_cache,derivative_limits,budget_ratio)
        return supervised+budget,count
    selected=[(local,successors[index]) for local,index in enumerate(indices) if index in successors]
    expert_targets=getattr(model,'conditional_boundary',False)
    if expert_targets:
        selected=[(local,neighbor) for local,neighbor in selected
                  if records[indices[local]]['kind']=='demonstration' and records[neighbor]['kind']=='demonstration']
    if not selected:
        return q.sum()*0, 0
    if boundary_cache is not None:
        from generator.direct_infiller import decode_batch
        from generator.infiller_boundary_velocity import finite_difference_velocity
        left_indices=[indices[local] for local,_ in selected]
        right_indices=[neighbor for _,neighbor in selected]
        left_batch=boundary_cache.native_batch(left_indices)
        right_batch=boundary_cache.native_batch(right_indices)
        if history is not None:history.condition(left_batch,left_indices)
        lc,rc=left_batch['native_count'],right_batch['native_count']
        left_phase=torch.stack((1-1/(lc-1),torch.ones_like(lc)),-1)[...,None]
        right_phase=torch.stack((torch.zeros_like(rc),1/(rc-1)),-1)[...,None]
        left=decode_batch(model,left_batch,left_phase)
        dt=q.new_full((len(selected),),1/50)
        if getattr(model,'conditions_on_velocity',False):
            right_batch['start_velocity']=finite_difference_velocity(left,dt)
        right=decode_batch(model,right_batch,right_phase)
        targets={}
        if expert_targets:
            from generator.infiller_boundary_velocity import expert_native_pair
            targets=dict(target_left=torch.cat([expert_native_pair(records[i],n,True,device) for i,n in zip(left_indices,lc)]),
                         target_right=torch.cat([expert_native_pair(records[i],n,False,device) for i,n in zip(right_indices,rc)]))
        return sampled_seam_loss(left,right,dt,dt,model.scale,**targets).mean(),len(selected)
    # Every right neighbor is decoded at its own first two native phases. No
    # padding, duration transplant, or detached fixed-neighbor target is used.
    from generator.direct_infiller import collate, decode_batch, prepare_frame_prediction
    losses=[]
    for local,neighbor in selected:
        r=records[neighbor]
        b=prepare_frame_prediction(model,collate([r],device))
        if model.predicts_frames:
            # Decoupled timing also applies to phase locations, not just dt.
            left_batch=prepare_frame_prediction(model,collate([records[indices[local]]],device))
            if history is not None:
                history.condition(left_batch, [indices[local]])
            if getattr(model, 'conditions_on_velocity', False):
                for native_batch in (left_batch,b):
                    native_batch['motion_frames']=native_batch['motion_frames'].round()
                    native_batch['duration']=(native_batch['motion_frames']-1)/50
            zero=q.new_zeros(1); one=q.new_ones(1)
            lp=torch.stack((one-1/(left_batch['motion_frames']-1),one),-1)[...,None]
            phase=torch.stack((zero,1/(b['motion_frames']-1)),-1)[...,None]
            left=decode_batch(model,left_batch,lp)
            left_dt=right_dt=q.new_tensor([1/50])
        else:
            phase=q.new_tensor([0.,1/(len(r['q'])-1)])[None,:,None]
            left=q[local:local+1,-2:]
            left_dt=q.new_tensor([float(records[indices[local]]['duration'])/(q.shape[1]-1)])
            right_dt=q.new_tensor([float(r['duration'])/(len(r['q'])-1)])
        if getattr(model, 'conditions_on_velocity', False):
            from generator.infiller_boundary_velocity import finite_difference_velocity
            b['start_velocity']=finite_difference_velocity(left,left_dt)
        right=decode_batch(model,b,phase)
        targets={}
        if expert_targets:
            from generator.infiller_boundary_velocity import expert_native_pair
            left_count=left_batch['motion_frames'].round() if model.predicts_frames else len(records[indices[local]]['q'])
            right_count=b['motion_frames'].round() if model.predicts_frames else len(r['q'])
            targets=dict(target_left=expert_native_pair(records[indices[local]],left_count,True,device),
                         target_right=expert_native_pair(r,right_count,False,device))
        losses.append(sampled_seam_loss(left,right,left_dt,right_dt,model.scale,**targets))
    return torch.cat(losses).mean(), len(selected)


def sampled_seam_budget_loss(left,right,left_dt,right_dt,reference_left,reference_right,limits,ratio):
    """Soft normalized acceleration budgets across the shared boundary.

    The reference supplies magnitudes only, never velocity direction targets.
    Units match derivative_metrics: second differences normalized to 50 Hz.
    """
    if ratio<1:raise ValueError('Witnessed seam ratio must be at least one')
    if bool((left_dt<=0).any()|(right_dt<=0).any()):raise ValueError('Positive seam sample intervals required')
    def magnitudes(a,b):
        signals={'root_d2_peak':(a[...,:3],b[...,:3]),
                 'joint_d2_peak':(a[...,7:],b[...,7:]),
                 'rotation_matrix_d2_peak':(_quaternion_matrix_wxyz(a[...,3:7]).flatten(-2),
                                           _quaternion_matrix_wxyz(b[...,3:7]).flatten(-2))}
        denominator=2500*(left_dt+right_dt)/2
        result={}
        for key,(l,r) in signals.items():
            acceleration=((r[:,1]-r[:,0])/right_dt[:,None]
                          -(l[:,1]-l[:,0])/left_dt[:,None])/denominator[:,None]
            result[key]=acceleration.abs().amax(-1) if key=='joint_d2_peak' else acceleration.norm(dim=-1)
        return result
    actual=magnitudes(left,right)
    with torch.no_grad():
        witness=magnitudes(reference_left,reference_right)
        budgets={k:torch.maximum(limits[k].to(v),v*ratio).clamp_min(1e-8) for k,v in witness.items()}
    ratios=torch.stack([actual[k]/budgets[k] for k in actual],-1)
    penalty=torch.log1p((ratios-1).relu().square())
    return (penalty.mean(-1)+penalty.amax(-1)).mean()


def seam_budget_objective(model,records,indices,successors,q,device,history,cache,limits,ratio):
    selected=[(indices[local],successors[index]) for local,index in enumerate(indices) if index in successors]
    if not selected:return q.sum()*0,0
    from generator.infiller_efficiency import BoundaryRecordCache
    from generator.infiller_boundary_velocity import finite_difference_velocity,expert_native_pair
    from generator.direct_infiller import decode_batch
    from generator.trajectory_budget import boundary_cubic_reference
    if cache is None:cache=BoundaryRecordCache(model,records,device)
    left_ids,right_ids=map(list,zip(*selected))
    lb,rb=cache.native_batch(left_ids),cache.native_batch(right_ids)
    if history is not None:history.condition(lb,left_ids)
    lc,rc=lb['native_count'],rb['native_count']
    lp=torch.stack((1-1/(lc-1),torch.ones_like(lc)),-1)[...,None]
    rp=torch.stack((torch.zeros_like(rc),1/(rc-1)),-1)[...,None]
    left=decode_batch(model,lb,lp);dt=q.new_full((len(selected),),1/50)
    if getattr(model,'conditions_on_velocity',False):rb['start_velocity']=finite_difference_velocity(left,dt)
    right=decode_batch(model,rb,rp)
    with torch.no_grad():
        def reference(ids,batch,phase,count,tail):
            cubic=boundary_cubic_reference(batch['q'][:,0],batch['q'][:,-1],phase)
            return torch.cat([expert_native_pair(records[i],n,tail,device) if records[i]['kind']=='demonstration'
                              else cubic[j:j+1] for j,(i,n) in enumerate(zip(ids,count))])
        lref=reference(left_ids,lb,lp,lc,True);rref=reference(right_ids,rb,rp,rc,False)
    return sampled_seam_budget_loss(left,right,dt,dt,lref,rref,limits,ratio),len(selected)
