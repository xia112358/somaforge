"""Soft trajectory refinement using freshly queried, authoritative Newton witnesses.

Events supply contact intent. Only native activation/allocation and full-body
separation certify the result; absent candidates are failures, never zero error.
"""
from dataclasses import dataclass
import copy
import numpy as np
import torch
from .regional_contact_refinement import EventContactRegions, regional_terms

PARTS = ('left_foot', 'right_foot', 'left_hand', 'right_hand', 'left_knee', 'right_knee')
REFINEMENT_OBJECTIVE_SCHEMA = 'source_relative_acceleration_loaded_material_budget_v10'
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


def event_contact_roles(events, frame_count):
    """Explicit whole-endpoint release intervals, with an exclusive end.

    Legacy touchdown release_frame can span required support on another
    surface and does not certify a whole-endpoint release interval.
    """
    wanted, face = event_contact_intent(events, frame_count)
    release = np.zeros_like(wanted)
    for event in events:
        for interval in event.get('release_events', []):
            start, stop = int(interval['start_frame']), int(interval['end_frame_exclusive'])
            part = int(interval['part_index'])
            if interval.get('scope') != 'whole_endpoint':
                raise ValueError('Release event must explicitly name whole_endpoint scope')
            if not 0 <= start < stop <= frame_count or not 0 <= part < len(PARTS):
                raise ValueError('Invalid event release interval')
            release[start:stop, part] = True
    if np.any(wanted & release):
        raise ValueError('Required contact and release events conflict')
    return wanted, face, release


def require_material_task_coverage(events, frame_count, approach_tasks):
    """Reject missing authored intent targets before starting native workers.

    This validates an optimization request, not demonstration quality or actual
    contact. No role is removed and no target is invented from a distance rule.
    """
    wanted, _ = event_contact_intent(events, frame_count)
    valid, domains = np.asarray(approach_tasks[2], bool), approach_tasks[3]
    if valid.shape != wanted.shape or len(domains) != frame_count or any(len(row)!=6 for row in domains):
        raise ValueError('Event material task clock dimensions differ')
    present = np.asarray([[geometry is not None for geometry in row] for row in domains])
    missing = np.argwhere(wanted & ~(valid & present))
    if len(missing):
        raise ValueError(f'Event material targets missing for {len(missing)} required part-frames: '
                         f'{missing[:20].tolist()}; require explicit authored surface tasks, no contact fallback')


def joint_continuity_terms(joints, reference):
    """Match aligned source increments; constant joint offsets are allowed."""
    if joints.shape != reference.shape or len(joints) < 3:
        raise ValueError('Continuity reference must align with at least three motion frames')
    delta = joints-reference
    velocity = ((delta[1:]-delta[:-1])/.01).square().mean()
    acceleration = ((delta[2:]-2*delta[1:-1]+delta[:-2])/.01).square().mean()
    return velocity, acceleration


def marker_acceleration_loss(points, scale, reference=None):
    """Preserve demonstrated acceleration when an aligned source is known.

    A source's own acceleration is free. Constant offsets and velocity offsets
    are also free; introduced jumps still have a restoring gradient. Without a
    source this is only an absolute geometric smoothness prior.
    """
    if len(points) < 3 or scale <= 0:
        raise ValueError('Marker acceleration requires three frames and a positive scale')
    if reference is not None:
        if reference.shape != points.shape:
            raise ValueError('Marker continuity reference must align with the trajectory')
        points = points-reference.detach()
    return ((points[2:]-2*points[1:-1]+points[:-2])/scale).square().mean()


def trajectory_support_regularizer(q, output_markers, reference_markers, persistent, scale,
                                   *, phase_motion_loss=None, source_support=None):
    """Use original loaded material sites as the sole support-motion metric.

    Full endpoint markers are only a geometric prior when no original load
    reference exists. They must not add a second stationary-support criterion.
    """
    if phase_motion_loss is not None:
        return phase_motion_loss(q)
    denom = persistent.sum().clamp_min(1)
    if source_support is not None:
        extra_step, accumulated = source_support(q)
        return .1*((extra_step/scale).square().sum()/denom
                   + .01*(accumulated/scale).square().sum()/denom)
    correction = output_markers-reference_markers
    velocity = correction[1:]-correction[:-1]
    return .1*((velocity/scale).square().mean((-1,-2))*persistent).sum()/denom


def loaded_material_candidate_rank(record):
    """Select by the authoritative phase metric, never an arbitrary marker.

    Missing reference evidence cannot rank as measured zero motion. The old
    single-point diagnostic is deliberately absent from the selection order.
    """
    from somaforge_core.loaded_material_motion import MATERIAL_MOTION_SCHEMA
    report = record.get('phase_support', {})
    if report.get('schema') != MATERIAL_MOTION_SCHEMA or not report.get('phases'):
        return None
    phases = report['phases']
    unknown = sum(p['passed'] is None for p in phases)
    failed = sum(p['passed'] is False for p in phases)
    paths = [p['edited_budget']['material_tangent_path_m'] for p in phases]
    return (record['event_acceptance']['failed_checks'], unknown, failed,
            record['max_penetration_mm'], sum(paths))


def missing_material_guidance(fk, q, local, target, valid, missing, margin):
    """Authored material targets guide recovery, never certify contact."""
    if bool((missing & ~valid).any()):
        raise ValueError('Missing contact has no event material target')
    if bool((margin <= 0).any()):
        raise ValueError('Material guidance requires actual positive configured margin')
    position, rotation = fk.link_poses(q, ENDPOINTS)
    point = position+torch.einsum('bpij,bpj->bpi', rotation, local)
    cost = ((point-target)/(.25*margin[:, None, None])).square().sum(-1)
    cost = torch.where(cost <= 1, cost, 2*cost.clamp_min(1).sqrt()-1)
    cost = torch.where(missing, cost, 0)
    return cost.mean(-1)+cost.amax(-1)


@dataclass(frozen=True)
class RefinementConfig:
    steps: int = 1200
    learning_rate: float = 2.e-5
    uniform_batch: int = 64
    priority_batch: int = 32
    audit_every: int = 32
    distance_scale_m: float = .001  # loss normalization, not a contact threshold


def refine_trajectory(q_initial, fk, events, query, fingerprint, *,
                      config=RefinementConfig(), progress=None, approach_tasks=None,
                      continuity_reference=None, event_contract=None, support_reference=None, phase_motion_loss=None,
                      solid_query=None):
    """Optimize all frames, preserving reference-relative support and smoothness.

    q_initial uses the canonical FK joint order. query(q.detach()) must return
    a complete newton_device_witness_batch_v1 from a dedicated initialized
    native scene, plus provenance. No reduced HTTP-witness fallback is used;
    a fingerprint mismatch fails closed.
    """
    reference = q_initial.detach().clone()
    if solid_query is None:
        raise ValueError('Refinement requires complete realized solid geometry')
    temporal = reference if continuity_reference is None else continuity_reference.detach().to(reference)
    if temporal.shape != reference.shape or not bool(torch.isfinite(temporal).all()):
        raise ValueError('Invalid aligned continuity reference')
    geometry = EventContactRegions(copy.deepcopy(fk).cpu()).to(reference)
    if approach_tasks is None:
        raise ValueError("Unified regional refinement requires event-bound surface tasks")
    n = len(reference)
    wanted_np, face_np, release_np = event_contact_roles(events, n)
    wanted = torch.as_tensor(wanted_np, device=reference.device)
    faces = torch.as_tensor(face_np, device=reference.device)
    release = torch.as_tensor(release_np, device=reference.device)
    tolerated = torch.zeros_like(wanted)
    lo, hi = fk.joint_lower, fk.joint_upper
    mid, rad = (lo + hi) / 2, (hi - lo) / 2
    initial = reference.clone()
    initial[:, 7:] = torch.atanh(((initial[:, 7:] - mid) / rad).clamp(-.999999, .999999))
    state = torch.nn.Parameter(initial)
    optimizer = torch.optim.Adam([state], lr=config.learning_rate)
    scale = config.distance_scale_m
    if scale <= 0 or config.steps < 0:
        raise ValueError('Invalid refinement configuration')
    offsets = reference.new_tensor([[0, 0, 0], [.1, 0, 0], [0, .1, 0], [0, 0, .1]])

    def markers(q):
        p, r = fk.link_poses(q, ENDPOINTS)
        return p[..., None, :] + torch.einsum('...ij,kj->...ki', r, offsets)

    reference_markers = markers(reference).detach()
    temporal_markers = markers(temporal).detach() if continuity_reference is not None else None
    approach_local = torch.as_tensor(approach_tasks[0], device=reference.device, dtype=reference.dtype)
    approach_target = torch.as_tensor(approach_tasks[1], device=reference.device, dtype=reference.dtype)
    approach_valid = torch.as_tensor(approach_tasks[2], device=reference.device, dtype=torch.bool)
    approach_domains = approach_tasks[3]
    persistent = wanted[1:] & wanted[:-1] & (faces[1:] == faces[:-1])
    if support_reference is not None:
        from .source_support import support_residuals, support_statistics
        edit_rotations, support_normals = [torch.as_tensor(x, device=reference.device, dtype=reference.dtype)
                                           for x in support_reference]
        source_positions, source_rotations = [x.detach() for x in fk.link_poses(temporal, ENDPOINTS)]
        persistent = persistent & approach_valid[1:] & approach_valid[:-1]

    def source_support(q):
        positions, rotations = fk.link_poses(q, ENDPOINTS)
        return support_residuals(positions, rotations, source_positions, source_rotations,
                                 approach_local, edit_rotations, support_normals, persistent)

    severity = np.zeros(n)
    history = []
    best_support_candidate = None
    best_support_rank = None

    def pose():
        return torch.cat((state[:, :3], torch.nn.functional.normalize(state[:, 3:7], dim=-1),
                          mid + rad * torch.tanh(state[:, 7:])), -1)

    def residual(q, indices):
        observed = query(q.detach())
        if observed.get('provenance', {}).get('model_fingerprint') != fingerprint:
            raise ValueError('Refinement query scene fingerprint mismatch')
        domains = [approach_domains[int(i)] for i in indices]
        intent = wanted[indices] & ~tolerated[indices]
        value, depth, missing, off, metrics = regional_terms(
            fk, geometry, q, observed, torch.zeros_like(intent) if config.steps == 0 else intent,
            faces[indices], domains, release[indices] & ~tolerated[indices], solid=solid_query(fk, q))
        if event_contract is not None:
            metrics['support_observed'] = observed
            metrics['event_mask'] = observed['contact_part_mask']
            metrics['event_surface'] = observed['contact_surface']
        if config.steps == 0:
            missing = wanted[indices] & ~metrics['matched_candidate_exists']
            off = wanted[indices] & ~metrics['matched_contact_realized']
            guidance = torch.zeros_like(value)
        else:
            guidance = missing_material_guidance(fk, q, approach_local[indices], approach_target[indices],
                approach_valid[indices], missing, observed['configured_margin'])
        metrics['missing_material_guidance'] = guidance
        return value+guidance, depth, missing, off, metrics

    @torch.no_grad()
    def audit(q, step):
        nonlocal best_support_candidate, best_support_rank
        # Preserve raw diagnostics even when event checks tolerate bounded holes.
        tolerated.zero_()
        depths, deficits, absent, off, released = [], [], [], [], []
        event_mask, event_surface = [], []
        material_samples = []
        absolute_steps = np.full((n,6), np.nan)
        region_distribution = {key:np.full((n,6), np.nan) for key in
                               ('minimum','pivot','lower_quartile','median','upper_quartile','maximum','count')}
        for start in range(0, n, 128):
            ids = np.arange(start, min(n, start + 128))
            value, v, m, o, metrics = residual(q[ids], ids)
            depths.extend(v.cpu().tolist()); deficits.extend(value.cpu().tolist())
            absent.extend(m.cpu().numpy()); off.extend(o.cpu().numpy())
            released.extend(metrics['release_violations'].cpu().numpy())
            if event_contract is not None:
                from .source_support import native_material_motion, native_material_samples
                samples = native_material_samples(fk, q, metrics['support_observed'], ids,
                    wanted_surfaces=None)
                material_samples.append(samples)
                distribution = native_material_motion(fk, q, metrics['support_observed'], ids, samples)
                for key,value in distribution.items(): region_distribution[key][ids] = value
                absolute_steps[ids] = distribution['pivot']
                event_mask.extend(metrics['event_mask'].cpu().numpy())
                event_surface.extend(metrics['event_surface'].cpu().numpy())
        severity[:] = np.array(depths) / scale + np.array(deficits) + np.array(off).sum(-1) + np.array(released).sum(-1)
        jv, ja = joint_continuity_terms(q[:, 7:], temporal[:, 7:])
        record = dict(step=step, objective_schema=(REFINEMENT_OBJECTIVE_SCHEMA if phase_motion_loss is not None
                                                 else 'event_material_recovery_output_smoothness_v1'),
                      joint_velocity_residual=float(jv), joint_acceleration_residual=float(ja),
                      marker_acceleration_residual=float(marker_acceleration_loss(markers(q), scale, temporal_markers)),
                      marker_acceleration_reference=('aligned_source' if temporal_markers is not None else 'none_absolute_prior'),
                      support_motion_objective=('original_loaded_material_only'
                          if phase_motion_loss is not None else 'geometric_marker_prior_only'),
                      legacy_marker_support_active=phase_motion_loss is None,
                      max_joint_step_deg=float(torch.rad2deg(torch.diff(q[:, 7:], dim=0)).abs().max()),
                      release_violations=int(np.sum(released)), release_part_frames=np.argwhere(released).tolist(),
                      unified_loss_mean=float(np.mean(deficits)), unified_loss_max=float(np.max(deficits)),
                      max_penetration_mm=max(depths)*1000,
                      penetrating_frames=int(np.count_nonzero(depths)),
                      missing_candidates=int(np.sum(absent)), missing_contacts=int(np.sum(off)),
                      missing_part_frames=np.argwhere(off).tolist())
        if support_reference is not None:
            record['geometric_authored_material_reference'] = dict(
                **support_statistics(*source_support(q), persistent),
                scope='single_authored_material_point_geometry_diagnostic_only',
                used_for_motion_acceptance_or_selection=False)
        if phase_motion_loss is not None:
            record['previous_material_phase_paths_m'] = phase_motion_loss.paths(q).cpu().tolist()
            record['optimization_material_phase_paths_m'] = phase_motion_loss.paths(q).cpu().tolist()
            record['material_phase_loss'] = float(phase_motion_loss(q))
        record['passed'] = not (record['penetrating_frames'] or record['missing_candidates'] or record['missing_contacts'] or record['release_violations'])
        record['legacy_frame_passed'] = record['passed']
        if event_contract is not None:
            from .event_acceptance import audit_events
            event_report, holes = audit_events(event_contract, np.asarray(event_mask), np.asarray(event_surface))
            tolerated.copy_(torch.as_tensor(holes, device=reference.device))
            from .source_support import audit_geometric_phase_motion
            record['geometric_region_motion'] = audit_geometric_phase_motion(event_contract, absolute_steps,
                np.asarray(event_mask), np.asarray(event_surface), distribution=region_distribution)
            record['phase_support'] = (phase_motion_loss.audit(q) if phase_motion_loss is not None else
                dict(passed=None, phases=[], reason='missing_original_loaded_execution_reference'))
            record['event_acceptance'] = event_report
            record['contact_events_passed'] = event_report['passed']
            record['geometry_passed'] = record['penetrating_frames'] == 0
            record['passed'] = (record['contact_events_passed'] and record['geometry_passed']
                                and record['phase_support']['passed'] is True)
            record['trajectory_acceptance'] = 'events_loaded_material_reference_geometry_only_edited_support_unknown'
        if phase_motion_loss is not None and event_contract is not None:
            rank = loaded_material_candidate_rank(record)
            record['candidate_selection_schema'] = 'events_loaded_material_budget_separation_v1'
            if rank is None:
                raise ValueError('Missing loaded material phase evidence for candidate selection')
            if best_support_rank is None or rank < best_support_rank:
                best_support_rank = rank
                best_support_candidate = (q.detach().clone(), step)
        history.append(record)
        if progress: progress(record)
        return record['passed']

    if config.steps == 0:
        audit(reference, 0)
        return reference, history
    if audit(pose(), 0) and continuity_reference is None:
        return pose().detach(), history
    for step in range(config.steps):
        optimizer.zero_grad()
        q = pose()
        uniform = (np.arange(config.uniform_batch) + step*config.uniform_batch) % n
        priority = np.argsort(-severity)[:config.priority_batch]
        ids = np.unique(np.r_[uniform, priority[severity[priority] > 0]])
        interval, v, missing, off, metrics = residual(q[ids], ids)
        severity[ids] = interval.detach().cpu().numpy() + off.sum(-1).cpu().numpy()
        output_markers = markers(q)
        support = trajectory_support_regularizer(q, output_markers, reference_markers, persistent, scale,
            phase_motion_loss=phase_motion_loss,
            source_support=source_support if support_reference is not None else None)
        smooth = marker_acceleration_loss(output_markers, scale, temporal_markers)
        joint_delta = q[:, 7:] - reference[:, 7:]
        joint_velocity, joint_smooth = joint_continuity_terms(q[:, 7:], temporal[:, 7:])
        prior = (joint_delta/.1).square().mean() + ((q[:, :3]-reference[:, :3])/.01).square().mean()
        loss = interval.mean() + support + .05*smooth + .2*joint_smooth + .02*prior
        if continuity_reference is not None:
            loss = loss + .05*joint_velocity
        if not torch.isfinite(loss):
            raise ValueError('Nonfinite native trajectory objective')
        loss.backward(); optimizer.step()
        if (step+1) % config.audit_every == 0 or step+1 == config.steps:
            if audit(pose(), step+1) and continuity_reference is None: break
    if best_support_candidate is not None:
        selected, selected_step = best_support_candidate
        if selected_step != history[-1]['step']:
            audit(selected, selected_step)
        history[-1]['selected_iteration'] = selected_step
        history[-1]['completed_iterations'] = config.steps
        return selected, history
    return pose().detach(), history
