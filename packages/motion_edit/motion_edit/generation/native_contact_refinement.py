"""Soft trajectory refinement using freshly queried, authoritative Newton witnesses.

Events supply contact intent. Only native activation/allocation and full-body
separation certify the result; absent candidates are failures, never zero error.
"""
from dataclasses import dataclass
import numpy as np
import torch
from contact_solver.newton_witness_loss import (
    query_local_distances, full_body_violation, selected_contact_activation_deficit,
)

PARTS = ('left_foot', 'right_foot', 'left_hand', 'right_hand', 'left_knee', 'right_knee')
ENDPOINTS = ('left_ankle_roll_link', 'right_ankle_roll_link',
             'left_sphere_hand_link', 'right_sphere_hand_link', 'left_knee_link', 'right_knee_link')


def interior_approach_goal(point, geometry, fraction=.01):
    """Move an approach target off a finite face edge, preserving clearance.

    This moves only a soft optimization target, never a robot pose or a contact
    label. The inset is relative to the actual polygon, not a distance gate.
    """
    from .surface_contact_loss import face_edges
    normal,edges,offsets=face_edges(geometry)
    if not len(edges): return np.asarray(point)
    center=np.asarray(geometry['polygon_world']).mean(0)
    point=np.asarray(point)
    projected=point-normal*np.dot(point-center,normal)
    outside=edges@projected-offsets;center_slack=offsets-edges@center
    if np.any(center_slack<=0):raise ValueError('Face has no strict interior')
    enter=float(np.maximum(outside/(outside+center_slack).clip(min=1.e-12),0).max())
    alpha=np.clip(enter,0,1)+(1-np.clip(enter,0,1))*fraction
    return point+alpha*(center-projected)


def demonstrated_approach_tasks(spec, events, fk, q_reference, surface_catalog):
    """Existing material targets guide absent candidates, never label contact.

    Nearest observations are transported only within each intended phase.
    """
    from .support_motion import endpoint
    from somaforge_core.contact_face_selection import upward_face_mask
    wanted, faces = event_contact_intent(events, spec.frame_count)
    links=tuple(sorted(set(ENDPOINTS) | {c.body_label.rstrip('/').split('/')[-1] for c in spec.contacts}))
    with torch.no_grad():
        positions,rotations=fk.link_poses(q_reference,links)
    positions=positions.cpu().numpy();rotations=rotations.cpu().numpy()
    observations = {}
    for contact in spec.contacts:
        name=endpoint(contact.body_label)
        if name not in PARTS:
            raise ValueError(f'Unresolved approach endpoint: {contact.body_label}')
        part=PARTS.index(name)
        link=links.index(contact.body_label.rstrip('/').split('/')[-1]);parent=links.index(ENDPOINTS[part])
        geometry = contact.metadata['target_surface_geometry']
        if not upward_face_mask([geometry['normal']])[0]:
            raise ValueError('Approach target is not an eligible main surface')
        # Event surface IDs come from the native binding. The caller supplies
        # an explicitly verified mapping, not a geometric contact threshold.
        matches=[s['surface'] for s in surface_catalog
                 if np.allclose(s['normal_w'],geometry['normal'],atol=1.e-6,rtol=0)
                 and np.isclose(s['plane_offset'],np.dot(geometry['origin'],geometry['normal']),atol=1.e-6,rtol=0)]
        if len(matches)!=1:raise ValueError('Approach face cannot be uniquely bound to native geometry')
        face=int(matches[0])
        targets = contact.resolved_target_points_w()
        for i, frame in enumerate(contact.frames):
            local = contact.points_local if contact.points_local_by_frame is None else contact.points_local_by_frame[i]
            clearance = (targets[i]-np.asarray(geometry['origin'])) @ np.asarray(geometry['normal'])
            j = int(np.argmin(clearance))
            world=positions[frame,link]+rotations[frame,link]@local[j]
            parent_local=rotations[frame,parent].T@(world-positions[frame,parent])
            record = (float(clearance[j]), parent_local, interior_approach_goal(targets[i,j],geometry), geometry)
            key = (int(frame), part, face)
            if key not in observations or record[0] < observations[key][0]:
                observations[key] = record
    local = np.zeros((*wanted.shape,3)); target = np.zeros_like(local); valid = np.zeros_like(wanted)
    domains=[[None for _ in PARTS] for _ in range(len(wanted))]
    for part in range(len(PARTS)):
        start = 0
        while start < len(wanted):
            if not wanted[start,part]: start += 1; continue
            end = start + 1; face = int(faces[start,part])
            while end < len(wanted) and wanted[end,part] and faces[end,part] == face: end += 1
            observed = [f for f in range(start,end) if (f,part,face) in observations]
            for frame in range(start,end):
                if not observed: continue
                nearest = min(observed,key=lambda f:abs(f-frame))
                _,local[frame,part],target[frame,part],domains[frame][part] = observations[nearest,part,face]
                valid[frame,part] = True
            start = end
    return local, target, valid, domains


def event_contact_intent(events, frame_count):
    """Persist phase identity across noisy frame observations and foot shapes."""
    wanted = np.zeros((frame_count, len(PARTS)), bool)
    face = np.full(wanted.shape, -1, np.int64)

    def assign(start, stop, part, surface):
        if not 0 <= start < stop <= frame_count or surface < 0:
            raise ValueError('Invalid event contact interval/surface')
        old = face[start:stop, part]
        if np.any((old >= 0) & (old != surface)):
            raise ValueError('Conflicting event surface intent')
        wanted[start:stop, part] = True
        face[start:stop, part] = surface

    for event in events:
        a, b = event['start_frame'], event['end_frame']
        for name in event.get('persistent_parts', []):
            part = PARTS.index(name)
            source, target = event['source_surfaces'][part], event['target_surfaces'][part]
            if source != target:
                raise ValueError('Persistent contact cannot change surfaces')
            assign(a, b + 1, part, int(source))
        for touchdown in event.get('touchdown_events', []):
            assign(b, b + 1, int(touchdown['part_index']), int(touchdown['surface']))
    return wanted, face


@dataclass(frozen=True)
class RefinementConfig:
    steps: int = 240
    learning_rate: float = 2.e-4
    uniform_batch: int = 64
    priority_batch: int = 32
    audit_every: int = 32
    distance_scale_m: float = .001  # loss normalization, not a contact threshold


def refine_trajectory(q_initial, fk, events, query, fingerprint, *,
                      config=RefinementConfig(), progress=None, approach_tasks=None):
    """Optimize all frames, preserving reference-relative support and smoothness.

    q_initial uses the canonical FK joint order. query must be a dedicated
    initialized native scene; a fingerprint mismatch fails closed.
    """
    reference = q_initial.detach().clone()
    n = len(reference)
    wanted_np, face_np = event_contact_intent(events, n)
    wanted = torch.as_tensor(wanted_np, device=reference.device)
    faces = torch.as_tensor(face_np, device=reference.device)
    lo, hi = fk.joint_lower, fk.joint_upper
    mid, rad = (lo + hi) / 2, (hi - lo) / 2
    initial = reference.clone()
    initial[:, 7:] = torch.atanh(((initial[:, 7:] - mid) / rad).clamp(-.999999, .999999))
    state = torch.nn.Parameter(initial)
    optimizer = torch.optim.Adam([state], lr=config.learning_rate)
    scale = config.distance_scale_m
    if scale <= 0 or config.steps < 1:
        raise ValueError('Invalid refinement configuration')
    offsets = reference.new_tensor([[0, 0, 0], [.1, 0, 0], [0, .1, 0], [0, 0, .1]])

    def markers(q):
        p, r = fk.link_poses(q, ENDPOINTS)
        return p[..., None, :] + torch.einsum('...ij,kj->...ki', r, offsets)

    reference_markers = markers(reference).detach()
    if approach_tasks is not None:
        approach_local, approach_target, approach_valid = [torch.as_tensor(x,device=reference.device) for x in approach_tasks[:3]]
        approach_domains=approach_tasks[3]
        approach_local=approach_local.to(reference);approach_target=approach_target.to(reference)
    persistent = wanted[1:] & wanted[:-1] & (faces[1:] == faces[:-1])
    severity = np.zeros(n)
    history = []

    def pose():
        return torch.cat((state[:, :3], torch.nn.functional.normalize(state[:, 3:7], dim=-1),
                          mid + rad * torch.tanh(state[:, 7:])), -1)

    def residual(q, indices):
        rows, native = query_local_distances(fk, q, query=query)
        if native.get('provenance', {}).get('model_fingerprint') != fingerprint:
            raise ValueError('Refinement query scene fingerprint mismatch')
        violation = full_body_violation(fk, q, native['full_robot_separation'])
        activation, missing, realized = selected_contact_activation_deficit(
            q, rows, wanted[indices], faces[indices])
        return violation, activation, missing, wanted[indices] & ~realized, rows

    @torch.no_grad()
    def audit(q, step):
        depths, deficits, absent, off = [], [], [], []
        for start in range(0, n, 128):
            ids = np.arange(start, min(n, start + 128))
            v, a, m, o, _ = residual(q[ids], ids)
            depths.extend(v.cpu().tolist()); deficits.extend(a.amax(-1).cpu().tolist())
            absent.extend(m.cpu().numpy()); off.extend(o.cpu().numpy())
        severity[:] = np.array(depths) / scale + np.array(deficits) + np.array(off).sum(-1)
        record = dict(step=step, max_penetration_mm=max(depths)*1000,
                      penetrating_frames=int(np.count_nonzero(depths)),
                      missing_candidates=int(np.sum(absent)), missing_contacts=int(np.sum(off)),
                      missing_part_frames=np.argwhere(off).tolist())
        record['passed'] = not (record['penetrating_frames'] or record['missing_candidates'] or record['missing_contacts'])
        history.append(record)
        if progress: progress(record)
        return record['passed']

    if audit(pose(), 0):
        return pose().detach(), history
    for step in range(config.steps):
        optimizer.zero_grad()
        q = pose()
        uniform = (np.arange(config.uniform_batch) + step*config.uniform_batch) % n
        priority = np.argsort(-severity)[:config.priority_batch]
        ids = np.unique(np.r_[uniform, priority[severity[priority] > 0]])
        v, a, missing, off, rows = residual(q[ids], ids)
        approach_loss = q.sum()*0
        if missing.any():
            if approach_tasks is None or (missing & ~approach_valid[ids]).any():
                raise ValueError('A required contact has no native candidate or demonstrated approach task')
            p,r=fk.link_poses(q[ids],ENDPOINTS)
            points=p+torch.einsum('tpij,tpj->tpi',r,approach_local[ids])
            errors=[]
            for sample,part in missing.nonzero().cpu().tolist():
                frame=int(ids[sample]);geometry=approach_domains[frame][part]
                candidates=[pair for pair,_ in rows[sample] if int(pair['part'])==part]
                if not candidates:
                    errors.append(((points[sample,part]-approach_target[frame,part])/scale).square().mean())
                    continue
                # A side witness is not promoted to a top contact. Its current
                # material point instead supplies a fresh tangent derivative
                # toward the intended face, followed by a new native query.
                normal=np.asarray(geometry['normal']);goal_reference=approach_target[frame,part].detach().cpu().numpy()
                goals=[]
                for pair in candidates:
                    point=np.asarray(pair['position_w'])
                    desired=point+normal*np.dot(goal_reference-point,normal)
                    goal=interior_approach_goal(desired,geometry)
                    goals.append((float(np.linalg.norm(goal-point)),pair,goal))
                _,pair,goal=min(goals,key=lambda item:item[0])
                position,rotation=fk.link_poses(q[frame:frame+1],(pair['body_name'],))
                position=position[0,0];rotation=rotation[0,0]
                local=rotation.detach().T@(q.new_tensor(pair['position_w'])-position.detach())
                moved=position+rotation@local
                errors.append(((moved-q.new_tensor(goal))/scale).square().mean())
            approach_loss=torch.stack(errors).mean()
        severity[ids] = v.detach().cpu().numpy()/scale + a.detach().amax(-1).cpu().numpy() + off.sum(-1).cpu().numpy()
        normalized = v / scale
        safety = normalized.square() + normalized
        correction = markers(q) - reference_markers
        velocity = correction[1:] - correction[:-1]
        support = ((velocity/scale).square().mean((-1, -2))*persistent).sum()/persistent.sum().clamp_min(1)
        smooth = ((correction[2:] - 2*correction[1:-1] + correction[:-2])/scale).square().mean()
        joint_delta = q[:, 7:] - reference[:, 7:]
        joint_smooth = ((joint_delta[2:] - 2*joint_delta[1:-1] + joint_delta[:-2])/.01).square().mean()
        prior = (joint_delta/.1).square().mean() + ((q[:, :3]-reference[:, :3])/.01).square().mean()
        loss = safety.mean() + safety.amax() + 10*(a.mean()+a.amax()) + approach_loss + .1*support + .05*smooth + .2*joint_smooth + .02*prior
        if not torch.isfinite(loss):
            raise ValueError('Nonfinite native trajectory objective')
        loss.backward(); optimizer.step()
        if (step+1) % config.audit_every == 0 or step+1 == config.steps:
            if audit(pose(), step+1): break
    return pose().detach(), history
