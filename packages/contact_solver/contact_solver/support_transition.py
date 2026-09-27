"""Endpoint support retention from actual Newton pairs and material-point FK.

Static environment only. This certifies neither load bearing nor the path
between endpoints. Query witnesses at the destination never replace anchors.
"""
import torch


def _eligible(rows):
    p = rows.pair
    required = ('type', 'dist', 'includemargin', 'efc_address', 'constraint_rows',
                'active', 'constraint_allocated', 'eligible', 'upward', 'task_pair')
    if any(k not in p for k in required):
        raise ValueError('Missing Newton support evidence')
    active = ((p['type'].long() & 1) != 0) & (p['dist'] < p['includemargin'])
    address = p['efc_address'].reshape(len(active), -1) if len(active) else p['efc_address']
    if len(active):
        count = p['constraint_rows']
        if bool(((count < 1) | (count > address.shape[1])).any()):
            raise ValueError('Invalid Newton support constraint row count')
        valid = torch.arange(address.shape[1], device=address.device)[None] < count[:, None]
        allocated = active & ((address >= 0) | ~valid).all(-1)
        if not torch.equal(active, p['active']) or not torch.equal(allocated, p['constraint_allocated']):
            raise ValueError('Newton support activation/allocation mismatch')
        if bool((active & ~allocated).any()):
            raise ValueError('Unallocated active support evidence')
    selected = p['eligible']
    if bool((selected & ~(active & p['constraint_allocated'] & p['upward'] & p['task_pair'])).any()):
        raise ValueError('Invalid primary-face support evidence')
    if bool((selected & ~rows.normal_valid).any()):
        raise ValueError('Unknown support normal')
    if bool((selected & ((p['body_link0'] >= 0) | (p['body_link1'] < 0))).any()):
        raise ValueError('Support transition currently requires static environment pairs')
    return selected


def predicted_support_loss(fk, before, after, predicted_role, *, tolerance_m=.06):
    """Penalize motion of every self-declared persistent endpoint (role 2).

    Only actual initial Newton primary-face contacts enable an endpoint. Final
    contact loss cannot disable it. Material-point choices are frozen, while
    their motion through the predicted pose's FK is differentiable. Taking the
    minimum within a part permits internal contact-region/pivot changes.
    """
    if not __import__('math').isfinite(tolerance_m) or tolerance_m <= 0:
        raise ValueError('Positive finite support tolerance required')
    q = after.q
    if predicted_role.shape != (len(q), 6) or predicted_role.dtype != torch.long:
        raise ValueError('Predicted roles must be long [B,6]')
    if bool(((predicted_role < 0) | (predicted_role > 3)).any()):
        raise ValueError('Unknown predicted support role')
    names = tuple(before.observed['link_names'])
    if len(before.q) != len(q) or names != tuple(after.observed['link_names']):
        raise ValueError('Support query batch/link mismatch')
    if (before.world_frame is None) != (after.world_frame is None):
        raise ValueError('Support query frame mismatch')
    if before.world_frame is not None and not all(torch.equal(a,b) for a,b in zip(before.world_frame,after.world_frame)):
        raise ValueError('Support queries must use the same frame')
    first, last = _eligible(before), _eligible(after)
    initial = torch.zeros((len(q),6),device=q.device,dtype=torch.bool)
    initial[before.pair['sample'][first],before.pair['part'][first]] = True
    declared = predicted_role.detach() == 2
    enabled = declared & initial
    zero = q.sum(-1)*0
    best = q.new_full((len(q)*6,),torch.inf)
    if bool(enabled.any()):
        with torch.no_grad():
            pos0,rot0 = fk.link_poses(before.q.detach(),names)
        pos1,rot1 = fk.link_poses(q,names)
        groups,distances = [],[]
        for rows,selected,pos,rot in ((before,first,pos0,rot0),
                                      (after,last,pos1.detach(),rot1.detach())):
            p=rows.pair
            selected=selected & enabled[p['sample'],p['part'].clamp(0,5)]
            sample,part,link=p['sample'][selected],p['part'][selected],p['body_link1'][selected]
            anchor=rows.points[selected,1].detach()
            if not bool(torch.isfinite(anchor).all()):
                raise ValueError('Nonfinite support witness')
            material=torch.einsum('nji,nj->ni',rot[sample,link],anchor-pos[sample,link]).detach()
            start=pos0[sample,link]+torch.einsum('nij,nj->ni',rot0[sample,link],material)
            finish=pos1[sample,link]+torch.einsum('nij,nj->ni',rot1[sample,link],material)
            groups.append(sample*6+part)
            distances.append((finish-start).norm(dim=-1))
        distance=torch.cat(distances)
        if not bool(torch.isfinite(distance).all()):
            raise ValueError('Nonfinite support displacement')
        best=best.scatter_reduce(0,torch.cat(groups),distance,reduce='amin')
    displacement=torch.where(enabled,best.reshape(len(q),6),zero[:,None])
    penalty=((displacement-tolerance_m).relu()/tolerance_m).square()
    loss=(penalty*enabled).sum(-1)/enabled.sum(-1).clamp_min(1)+zero
    return loss,dict(predicted_support_loss=loss,
        predicted_support_count=enabled.sum(-1).to(q),
        predicted_support_without_initial_contact=(declared & ~initial).sum(-1).to(q),
        predicted_support_max_displacement_m=displacement.amax(-1))


@torch.no_grad()
def support_transition(fk, before, after, *, tolerance_m=.06):
    """Hard endpoint-part retention gate; no loss or gradient modification.

    Group by endpoint part, ignoring internal shape/witness switches. Track
    material witnesses from BOTH endpoint regions through their own link FK;
    minimum displacement allows pivots without comparing different witnesses.
    Endpoint-only: neither uninterrupted contact nor no-slip path is certified.
    Tolerance is not a Newton contact margin.
    """
    if tolerance_m <= 0 or not __import__('math').isfinite(tolerance_m):
        raise ValueError('Positive finite support displacement tolerance required')
    if len(before.q) != len(after.q) or tuple(before.observed['link_names']) != tuple(after.observed['link_names']):
        raise ValueError('Support query batch/link mismatch')
    if (before.world_frame is None) != (after.world_frame is None):
        raise ValueError('Support query frame mismatch')
    if before.world_frame is not None and not all(torch.equal(a, b) for a,b in zip(before.world_frame, after.world_frame)):
        raise ValueError('Support queries must use the same frame')
    first, last = _eligible(before), _eligible(after)
    q = after.q
    if not bool(first.any()):
        return dict(support_displacement_m=q.new_zeros(len(q)),
                    support_transition_valid=torch.zeros(len(q), device=q.device, dtype=torch.bool),
                    support_initial_present=torch.zeros(len(q), device=q.device, dtype=torch.bool))
    names = tuple(before.observed['link_names'])
    pos0, rot0 = fk.link_poses(before.q.detach(), names)
    pos1, rot1 = fk.link_poses(q.detach(), names)
    batches, parts, distances, ends = [], [], [], []
    for end, rows, selected, pos, rot, other_pos, other_rot in (
            (0, before, first, pos0, rot0, pos1, rot1),
            (1, after, last, pos1, rot1, pos0, rot0)):
        p = rows.pair
        sample, part, link = p['sample'][selected], p['part'][selected], p['body_link1'][selected]
        anchor = rows.points[selected, 1].detach()
        if not bool(torch.isfinite(anchor).all()):
            raise ValueError('Nonfinite support witness')
        material = torch.einsum('nji,nj->ni', rot[sample,link], anchor-pos[sample,link])
        moved = other_pos[sample,link]+torch.einsum('nij,nj->ni', other_rot[sample,link], material)
        distance = (moved-anchor).norm(dim=-1)
        if not bool(torch.isfinite(distance).all()):
            raise ValueError('Nonfinite support displacement')
        batches.append(sample); parts.append(part); distances.append(distance)
        ends.append(torch.full_like(sample, end))
    batch, parts, distances, ends = map(torch.cat, (batches, parts, distances, ends))
    best = q.new_full((len(q),), float('inf'))
    initial = torch.zeros(len(q), device=q.device, dtype=torch.bool)
    initial[before.pair['sample'][first]] = True
    if len(batch):
        keys, inverse = torch.unique(torch.stack((batch, parts), -1), dim=0, return_inverse=True)
        motion = q.new_full((len(keys),), float('inf')).scatter_reduce_(0, inverse, distances, reduce='amin')
        begin = torch.zeros(len(keys), device=q.device, dtype=torch.bool)
        finish = begin.clone()
        begin[inverse[ends == 0]] = True
        finish[inverse[ends == 1]] = True
        retained = begin & finish
        best.scatter_reduce_(0, keys[retained,0], motion[retained], reduce='amin')
    return dict(support_displacement_m=torch.where(torch.isfinite(best), best, torch.zeros_like(best)),
                support_transition_valid=best <= tolerance_m, support_initial_present=initial)


def support_transition_http(fk, q0, q1, observed0, observed1, *, tolerance_m=.06):
    """Adapt current HTTP Newton evidence; selection stays in the shared selector."""
    from types import SimpleNamespace
    from somaforge_core.contact_face_selection import select_contact_pairs
    selected = []
    for observation in (observed0, observed1):
        raw = observation['raw_pairs']
        for pair in raw:
            if pair['constraint_active'] and not pair['allocated']:
                raise ValueError('Unallocated active Newton support evidence')
        result = select_contact_pairs([raw], observation['surface_catalog'])
        selected.append(result['contact_pairs'][0])
    names = tuple(sorted({p['body_name'] for group in selected for p in group}))
    def rows(q, pairs):
        n=len(pairs);device=q.device
        def tensor(values,dtype):return torch.as_tensor(values,device=device,dtype=dtype)
        counts=[len(p['efc_address']) for p in pairs];width=max(counts,default=1)
        p=dict(sample=torch.zeros(n,device=device,dtype=torch.long),
            part=tensor([x['part'] for x in pairs],torch.long),
            primary_surface=tensor([x['surface'] for x in pairs],torch.long),
            body_link0=torch.full((n,),-1,device=device,dtype=torch.long),
            body_link1=tensor([names.index(x['body_name']) for x in pairs],torch.long),
            type=tensor([x['constraint_type'] for x in pairs],torch.long),
            dist=tensor([x['dist'] for x in pairs],q.dtype),
            includemargin=tensor([x['includemargin'] for x in pairs],q.dtype),
            active=tensor([x['constraint_active'] for x in pairs],torch.bool),
            constraint_allocated=tensor([x['allocated'] for x in pairs],torch.bool),
            efc_address=tensor([list(x['efc_address'])+[-1]*(width-len(x['efc_address'])) for x in pairs],torch.long).reshape(n,width),
            constraint_rows=tensor(counts,torch.long))
        # These three flags are certified by the shared primary-face selection.
        for key in ('eligible','upward','task_pair'):p[key]=torch.ones(n,device=device,dtype=torch.bool)
        points=tensor([[x['terrain_position_w'],x['position_w']] for x in pairs],q.dtype).reshape(n,2,3)
        normals=tensor([x['normal_w'] for x in pairs],q.dtype).reshape(n,3)
        valid=torch.isfinite(normals).all(-1)&torch.isclose(normals.norm(dim=-1),torch.ones(n,device=device,dtype=q.dtype),atol=1e-4,rtol=0)
        return SimpleNamespace(q=q, pair=p,points=points,normal_valid=valid,world_frame=None,observed={'link_names':names})
    return support_transition(fk,rows(q0,selected[0]),rows(q1,selected[1]),tolerance_m=tolerance_m)
