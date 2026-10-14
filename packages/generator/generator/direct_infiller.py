"""Direct endpoint decoder and auditable trajectory metrics.

The 182/256/256/256/36 network is the historical Direct Infiller architecture.
Geometry objectives guide motion; only separate Newton queries establish contact.
"""
from __future__ import annotations

import torch
from torch import nn

from somaforge_core.g1_kinematics import (
    CanonicalG1ForwardKinematics, _quaternion_matrix_wxyz, _rotation_log_vector,
)
from contact_solver.collision_geometry import CanonicalG1CollisionPoints
from contact_solver.contact_surface_interval import finite_face_band_cost
from generator.trajectory_budget import derivative_metrics, densify_qpos

SCHEMA = 'direct_infiller_frozen_predictor_v1'


class DirectInfiller(nn.Module):
    """Historical direct decoder, with explicit canonical boundaries and time."""
    def __init__(self, *, predict_frames=False, frame_training='decoupled', boundary_velocity=False,
                 conditional_boundary=False, residual_extension=False):
        super().__init__()
        if frame_training not in ('joint', 'decoupled'):
            raise ValueError('Unknown frame training mode')
        self.frame_training = frame_training
        self.fk = CanonicalG1ForwardKinematics()
        self.geometry = CanonicalG1CollisionPoints(24)
        self.network = nn.Sequential(nn.Linear(182, 256), nn.Tanh(), nn.Linear(256, 256),
                                     nn.Tanh(), nn.Linear(256, 256), nn.Tanh(), nn.Linear(256, 36))
        nn.init.zeros_(self.network[-1].weight)
        nn.init.zeros_(self.network[-1].bias)
        self.register_buffer('scale', torch.tensor([.3]*3+[.5]*4+[1.]*29))
        self.predicts_frames = predict_frames
        self.conditions_on_velocity = boundary_velocity
        if conditional_boundary and not boundary_velocity:
            raise ValueError('Conditional boundary velocities require velocity architecture')
        self.conditional_boundary = conditional_boundary
        self.has_residual_extension = residual_extension
        if residual_extension:
            self.residual_extension = nn.Linear(256, 36)
            nn.init.zeros_(self.residual_extension.weight)
            nn.init.zeros_(self.residual_extension.bias)
        if boundary_velocity:
            self.register_buffer('velocity_scale', torch.tensor([.3]*3+[1.]*32))
            self.initial_velocity_head = nn.Sequential(nn.Linear(209 if conditional_boundary else 173, 128), nn.Tanh(),
                nn.Linear(128, 128), nn.Tanh(), nn.Linear(128, 35))
            self.terminal_velocity_head = nn.Sequential(nn.Linear(209, 128), nn.Tanh(),
                nn.Linear(128, 128), nn.Tanh(), nn.Linear(128, 35))
            self.velocity_adapter = nn.Linear(70, 182, bias=False)
            nn.init.zeros_(self.velocity_adapter.weight)
            for head in (self.initial_velocity_head, self.terminal_velocity_head):
                nn.init.zeros_(head[-1].weight)
                nn.init.zeros_(head[-1].bias)
        if predict_frames:
            # Count includes both endpoints. No externally supplied duration
            # enters this head; softplus allows extrapolation beyond demos.
            self.frame_head = nn.Sequential(nn.Linear(172, 128), nn.Tanh(),
                nn.Linear(128, 128), nn.Tanh(), nn.Linear(128, 1))
            nn.init.zeros_(self.frame_head[-1].weight)
            nn.init.constant_(self.frame_head[-1].bias, torch.expm1(torch.tensor(47/50)).log().item())

    def boundary_features(self, start, end, contract, scene):
        origin = start[:, :3]
        a, z = start.clone(), end.clone()
        a[:, :3] -= origin
        z[:, :3] -= origin
        z[:, 3:7] = torch.where((a[:, 3:7]*z[:, 3:7]).sum(-1, keepdim=True)<0,
                                -z[:, 3:7], z[:, 3:7])
        na, nz = a.clone(), z.clone()
        for value in (na, nz):
            value[:, 3:7] = torch.where(value[:, 3:4]<0, -value[:, 3:7], value[:, 3:7])
            value[:, 7:] /= torch.pi
        c, s = contract, scene
        static = torch.cat((na, nz, (c['start_anchor']-origin[:, None]).flatten(1),
            (c['end_anchor']-origin[:, None]).flatten(1), c['end_local_offset'].flatten(1),
            c['start_contact'].float(), c['end_contact'].float(), c['keep'].float(),
            c['start_surface'].float(), c['end_surface'].float(), s['box_center']-origin,
            s['box_rotation'].flatten(1), s['box_half_extents'],
            (s['ground_height']-origin[:, 2])[:, None]), -1)
        return static, a, z, origin

    def frame_count(self, start, end, contract, scene):
        if not self.predicts_frames:
            raise ValueError('This Infiller has no learned frame head')
        static, _, _, _ = self.boundary_features(start, end, contract, scene)
        return self.frame_count_from_features(static)

    def frame_count_from_features(self, features):
        return 4 + 50*nn.functional.softplus(self.frame_head(features).squeeze(-1))

    def boundary_velocities(self, start, end, contract, scene, duration,
                            start_velocity=None, velocity_known=None):
        from generator.infiller_boundary_velocity import relative_rotation
        if not self.conditions_on_velocity:
            raise ValueError('This Infiller has no boundary velocity architecture')
        if self.predicts_frames and self.frame_training == 'decoupled':
            duration = duration.detach()
        if not bool(torch.isfinite(duration).all()) or bool((duration <= 0).any()):
            raise ValueError('Trajectory needs positive finite duration')
        static, _, _, _ = self.boundary_features(start, end, contract, scene)
        timed = torch.cat((static, duration[:, None]), -1)
        secant = torch.cat((end[:, :3]-start[:, :3],
            relative_rotation(start[:, 3:7], end[:, 3:7]), end[:, 7:]-start[:, 7:]), -1)/duration[:, None]
        known = torch.zeros(len(start), device=start.device, dtype=torch.bool)
        incoming = torch.zeros_like(secant)
        if start_velocity is None:
            if velocity_known is not None and bool(velocity_known.any()):
                raise ValueError('Known velocity requires a provided history')
        else:
            if start_velocity.shape != (len(start), 35) or not bool(torch.isfinite(start_velocity).all()):
                raise ValueError('Incoming velocity must be finite [B,35]')
            known = (torch.ones(len(start), device=start.device, dtype=torch.bool)
                     if velocity_known is None else velocity_known.bool())
            if known.shape != (len(start),):
                raise ValueError('Velocity known mask must be [B]')
            incoming = torch.where(known[:, None], start_velocity, incoming)
        initial_inputs = (torch.cat((timed, incoming*duration[:, None]/self.velocity_scale,
                          known[:, None].float()), -1) if self.conditional_boundary else timed)
        estimate = secant+self.initial_velocity_head(initial_inputs)*self.velocity_scale/duration[:, None]
        initial = estimate if self.conditional_boundary else torch.where(known[:, None], incoming, estimate)
        inputs = torch.cat((timed, initial*duration[:, None]/self.velocity_scale, known[:, None].float()), -1)
        terminal = secant+self.terminal_velocity_head(inputs)*self.velocity_scale/duration[:, None]
        return initial, terminal, estimate, known

    def forward(self, start, end, phase, contract, scene, duration,
                start_velocity=None, velocity_known=None):
        if phase.ndim != 3 or phase.shape[-1] != 1:
            raise ValueError('phase must be [B,T,1]')
        if self.predicts_frames and self.frame_training == 'decoupled':
            duration = duration.detach()
        static, a, z, origin = self.boundary_features(start, end, contract, scene)
        static = torch.cat((static, duration[:, None]), -1)
        features = torch.cat([phase]+[f(phase*torch.pi*k)
            for k in (1, 2, 4, 8) for f in (torch.sin, torch.cos)], -1)
        inputs = torch.cat((features, static[:, None].expand(-1, phase.shape[1], -1)), -1)
        u = phase
        if self.conditions_on_velocity:
            from generator.infiller_boundary_velocity import hermite_pose
            initial, terminal, _, _ = self.boundary_velocities(start, end, contract, scene,
                duration, start_velocity, velocity_known)
            velocity = torch.cat((initial, terminal), -1)*duration[:, None]/self.velocity_scale.repeat(2)
            inputs = inputs+self.velocity_adapter(velocity)[:, None]
            residual = self.trajectory_residual(inputs)
            q = hermite_pose(a, z, u, duration, initial, terminal, residual)
        else:
            blend = u.square()*(3-2*u)
            q = (1-blend)*a[:, None]+blend*z[:, None]
            q = q+16*u.square()*(1-u).square()*self.trajectory_residual(inputs)
        q = torch.cat((q[..., :3]+origin[:, None], nn.functional.normalize(q[..., 3:7], dim=-1),
            q[..., 7:].clamp(self.fk.joint_lower, self.fk.joint_upper)), -1)
        # Keep the caller's exact quaternion representation at both boundaries.
        return torch.where((u == 0), start[:, None], torch.where((u == 1), end[:, None], q))

    def trajectory_residual(self, inputs):
        if not self.has_residual_extension:
            return self.scale*torch.tanh(self.network(inputs))
        hidden = self.network[:-1](inputs)
        return self.scale*(torch.tanh(self.network[-1](hidden))+self.residual_extension(hidden))


def load_infiller(saved, device):
    architecture = saved.get('architecture', {})
    predicts = architecture.get('predicts_frames', False)
    if any(k.startswith('frame_head.') for k in saved['model']) != predicts:
        raise ValueError('Infiller frame-head architecture metadata/state mismatch')
    # Historical checkpoints used joint time gradients. Preserve their recipe.
    model = DirectInfiller(predict_frames=predicts,
        frame_training=architecture.get('frame_training', 'joint'),
        boundary_velocity=architecture.get('boundary_velocity', False),
        conditional_boundary=architecture.get('conditional_boundary', False),
        residual_extension=architecture.get('residual_extension', False)).to(device)
    model.load_state_dict(saved['model'])
    return model


def prepare_frame_prediction(model, batch):
    """Teacher phase grids preserve demo poses, not their externally given time."""
    if getattr(model, 'predicts_frames', False):
        batch['reference_duration'] = batch['duration']
        batch['predicted_frames'] = model.frame_count(batch['q'][:, 0], batch['q'][:, -1],
            batch['contract'], batch['scene'])
        batch['frame_training'] = model.frame_training
        batch['motion_frames'] = (batch['predicted_frames'].detach()
            if model.frame_training == 'decoupled' else batch['predicted_frames'])
        batch['duration'] = (batch['motion_frames']-1)/50
    return batch


def frame_objective(batch):
    """Expert-only time supervision; generated efficiency is legacy joint-only."""
    predicted = batch['predicted_frames']
    demo = batch['demo']
    target = 1+50*batch['reference_duration']
    decoupled = batch.get('frame_training', 'joint') == 'decoupled'
    error = (nn.functional.smooth_l1_loss(predicted, target, reduction='none') if decoupled
        else nn.functional.smooth_l1_loss(predicted.log(), target.log(), reduction='none'))
    supervised = error[demo].mean() if bool(demo.any()) else predicted.sum()*0
    # Positive elapsed-time cost prevents unbounded slowing of unknown events.
    efficiency = (predicted.sum()*0 if decoupled else
        batch['duration'][~demo].mean() if bool((~demo).any()) else predicted.sum()*0)
    mae = (predicted[demo].round()-target[demo]).abs().mean() if bool(demo.any()) else predicted.sum()*0
    return supervised, efficiency, dict(frame_supervision=supervised,
        frame_efficiency_seconds=efficiency, frame_mae=mae if bool(demo.any()) else None,
        predicted_frames_mean=predicted.mean())


def generate_segment(model, start, end, contract, scene, *, duration=None, maximum_frames=4096,
                     use_frame_head=True, start_velocity=None, velocity_known=None):
    """Native 50 Hz output; excessive predictions fail rather than clip time."""
    if len(start) != 1:
        raise ValueError('Variable-length inference expects one segment')
    predicted = None
    if model.predicts_frames and use_frame_head:
        predicted = model.frame_count(start, end, contract, scene)
        if not bool(torch.isfinite(predicted).all()):
            raise ValueError('Nonfinite Infiller frame count')
        count = int(predicted.round().item())
    else:
        if duration is None:
            raise ValueError('Historical Infiller needs an explicit duration')
        count = round(float(duration)*50)+1
    if count < 4 or count > maximum_frames:
        raise ValueError(f'Predicted segment count {count} outside resource range [4,{maximum_frames}]')
    seconds = start.new_tensor([(count-1)/50])
    phase = torch.linspace(0, 1, count, device=start.device, dtype=start.dtype)[None, :, None]
    kwargs = dict(start_velocity=start_velocity, velocity_known=velocity_known) if getattr(model, 'conditions_on_velocity', False) else {}
    q = model(start, end, phase, contract, scene, seconds, **kwargs)[0]
    metadata = dict(frames=count, duration_s=float(seconds[0]),
        predicted_frames_float=None if predicted is None else float(predicted[0].detach()))
    if kwargs:
        initial, terminal, _, known = model.boundary_velocities(start, end, contract, scene, seconds, **kwargs)
        metadata.update(incoming_velocity_source='previous generated native 50Hz finite difference'
            if bool(known[0]) else 'unknown history; model estimated initial velocity',
            initial_velocity=initial[0].detach().cpu().tolist(),
            predicted_terminal_velocity=terminal[0].detach().cpu().tolist())
        metadata['incoming_velocity_usage']='condition; model predicts initial velocity' if model.conditional_boundary else 'hard initial boundary when known'
    return q, metadata


def decode_batch(model, batch, phase=None):
    if phase is None:
        phase = batch['phase']
    kwargs = (dict(start_velocity=batch.get('start_velocity'), velocity_known=batch.get('velocity_known'))
              if getattr(model, 'conditions_on_velocity', False) else {})
    return model(batch['q'][:, 0], batch['q'][:, -1], phase, batch['contract'],
                 batch['scene'], batch['duration'], **kwargs)


def collate(records, device):
    if not records or len({len(r['q']) for r in records}) != 1:
        raise ValueError('Only equal native frame counts may be batched; no padding')
    transfer = lambda v: v.to(device)
    b = {k: transfer(torch.stack([r[k] for r in records])) for k in
         ('q', 'active', 'surface', 'material', 'material_link', 'margin', 'duration', 'scene_id')}
    b['contract'] = {k: transfer(torch.stack([r['contract'][k] for r in records]))
                     for k in records[0]['contract']}
    b['scene'] = {k: transfer(torch.stack([r['scene'][k] for r in records])) for k in records[0]['scene']}
    b['phase'] = torch.linspace(0, 1, b['q'].shape[1], device=device)[None, :, None].expand(len(records), -1, -1)
    b['demo'] = torch.tensor([r['kind']=='demonstration' for r in records], device=device)
    return b


def trajectory_objective(model, b, q, limits, link_names, *, dense_factor=10):
    """Historical budgets/weak prior plus actual-margin material face intervals.

    Contact masks are observations for demonstrations and declared intent for
    predicted boundaries. These costs never classify generated contact.
    """
    dense = densify_qpos(q, dense_factor)
    points, _ = model.geometry(model.fk, dense)
    s = b['scene']
    local = torch.einsum('btpi,bij->btpj', points-s['box_center'][:, None, None], s['box_rotation'])
    box = (-(local.abs()-s['box_half_extents'][:, None, None]).amax(-1)).relu()
    ground = (s['ground_height'][:, None, None]-points[..., 2]).relu()
    collision = q.sum()*0
    # Historical 2mm is an optimization allowance, never a solver margin.
    for depth in (box, ground):
        excess = (depth-.002).relu()/.01
        cost = torch.expm1(excess.clamp_max(12))
        frame_cost = cost.amax(-1)
        collision = collision+10*(cost.mean()+.25*frame_cost.mean()+.25*frame_cost.amax()
                                  +.25*(1-torch.exp(-excess.amax(-1))).mean())
    position, rotation = model.fk.link_poses(q, link_names)
    batch = torch.arange(len(q), device=q.device)[:, None, None]
    frames = torch.arange(q.shape[1], device=q.device)[None, :, None]
    link = b['material_link'].clamp_min(0)
    material = position[batch, frames, link]+torch.einsum('btpij,btpj->btpi',
        rotation[batch, frames, link], b['material'])
    top = s['box_center']+s['box_rotation'][:, :, 2]*s['box_half_extents'][:, 2:3]
    ml = torch.einsum('btpi,bij->btpj', material-top[:, None, None], s['box_rotation'])
    floor = b['surface']==0
    gap = torch.where(floor, material[..., 2]-s['ground_height'][:, None, None], ml[..., 2])
    outside = torch.where(floor[..., None], 0, (ml[..., :2].abs()-s['box_half_extents'][:, None, :2][:, :, None]).relu())
    band = finite_face_band_cost(gap, outside, b['margin'])
    known = b['active'] & (b['material_link'] >= 0) & torch.isfinite(b['margin']) & (b['margin'] > 0)
    if bool((b['active'] & ~known).any()):
        raise ValueError('Required contact intent has unknown actual material or margin')
    contact = (band*known).sum()/known.sum().clamp_min(1)/.005**2*12
    # Demonstration materials may roll/pivot. Match their motion, rather than
    # making a link origin or one arbitrary witness into stationary support.
    with torch.no_grad():
        rp, rr = model.fk.link_poses(b['q'], link_names)
        reference_material = rp[batch, frames, link]+torch.einsum('btpij,btpj->btpi',
            rr[batch, frames, link], b['material'])
    demo_active = known & b['demo'][:, None, None]
    material_prior = (((material-reference_material)/.005).square().sum(-1)*demo_active).sum()/demo_active.sum().clamp_min(1)
    current = derivative_metrics(q, b['duration'])
    ratio = torch.stack([current[k]/limits[k] for k in limits], -1)
    excess = (ratio-1).relu().square()
    budget = excess.mean()+excess.amax(-1).mean()
    reference = b['q'].clone()
    reference[..., 3:7] = torch.where((reference[..., 3:7]*q[..., 3:7]).sum(-1, keepdim=True)<0,
                                      -reference[..., 3:7], reference[..., 3:7])
    deviation = ((q-reference)/model.scale).square().mean()
    acceleration = ((q[:, 2:]-2*q[:, 1:-1]+q[:, :-2])/model.scale).square().mean()
    total = collision+contact+material_prior+.01*deviation+.1*acceleration+2000*budget
    return total, dict(proxy_collision=collision, material_interval=contact,
                      demonstration_material_prior=material_prior, budget=budget)


def transfer_constraints(batch):
    """Expert native observations; generated inputs have no expert timing.

    A generated transition only specifies its boundaries and persistent contact.
    Its historical 20/80 percent pseudo-timing is deliberately not consumed.
    """
    contact=batch['contract']; frames=batch['q'].shape[1]
    persistent=(contact['keep'].bool() & contact['start_contact'].bool()
                & contact['end_contact'].bool() & (contact['start_surface']==contact['end_surface']))
    active=persistent[:,None].expand(-1,frames,-1).clone()
    surface=contact['start_surface'][:,None].expand(-1,frames,-1).clone()
    release=torch.zeros_like(active)
    active[:,0]=contact['start_contact'].bool(); active[:,-1]=contact['end_contact'].bool()
    surface[:,-1]=contact['end_surface']
    release[:,0]=~active[:,0]; release[:,-1]=~active[:,-1]
    demo=batch['demo'][:,None,None]
    active=torch.where(demo,batch['active'].bool(),active)
    surface=torch.where(demo,batch['surface'],surface)
    release=torch.where(demo,~batch['active'].bool(),release)
    return active,torch.where(active,surface,-1),release


def regularized_motion_objective(model,b,q,limits,*,budget_ratio=1.5,witnessed_budgets=False):
    """Full expert trajectories and reference-feasible soft smoothness.

    Expert paths or endpoint cubics provide a kinematic derivative-budget
    floor, without claiming collision or contact feasibility. Historical
    limits remain a floor and are reported independently by evaluation.
    """
    if budget_ratio<1: raise ValueError('Reference-feasible budget ratio must be at least one')
    reference=b['q'].clone()
    if witnessed_budgets:
        from generator.trajectory_budget import boundary_cubic_reference
        with torch.no_grad():
            generated=boundary_cubic_reference(b['q'][:,0],b['q'][:,-1],b['phase'])
            reference=torch.where(b['demo'][:,None,None],reference,generated)
    reference[...,3:7]=torch.where((reference[...,3:7]*q[...,3:7]).sum(-1,keepdim=True)<0,
                                  -reference[...,3:7],reference[...,3:7])
    deviation=((q-reference)/model.scale).square().mean((1,2))
    demo=b['demo'].to(q)
    pose=(deviation*demo).sum()/demo.sum().clamp_min(1)
    current=derivative_metrics(q,b['duration'])
    with torch.no_grad():
        nominal=derivative_metrics(reference,b['duration'] if witnessed_budgets else b.get('reference_duration', b['duration']))
        effective={k:torch.maximum(limits[k].to(q),nominal[k]*budget_ratio).clamp_min(1e-8)
                   for k in limits}
        if 'predicted_frames' in b and not witnessed_budgets:
            # Generated cubic duration is not a timing/feasibility witness.
            effective={k:torch.where(b['demo'], value, limits[k].to(q))
                       for k,value in effective.items()}
    ratios=torch.stack([current[k]/effective[k] for k in limits],-1)
    penalty=torch.log1p((ratios-1).relu().square())
    smooth=penalty.mean()+penalty.amax(-1).mean()
    return pose,smooth,dict(supervised_pose=pose,feasible_smoothness=smooth)


def contact_timing_metrics(mask, surface, role, start_surface, end_surface, fps, reference_mask=None,
                           reference_surface=None):
    """Actual same-surface episodes; no debounce, distances or force surrogate."""
    mask, surface = torch.as_tensor(mask).bool(), torch.as_tensor(surface).long()
    result = []
    for part in range(6):
        if int(role[part]) not in (1, 2, 3):
            continue
        wanted = int(end_surface[part])
        timeline = mask[:, part] & (surface[:, part] == wanted)
        onset = timeline & ~torch.cat((timeline.new_zeros(1), timeline[:-1]))
        onsets = onset.nonzero().flatten().tolist()
        continuous_end_start = None
        if bool(timeline[-1]):
            continuous_end_start = next((i for i in reversed(onsets)), None)
        observed_establishment = [i for i in onsets if i>0]
        item = dict(part=part, role=int(role[part]), target_surface=wanted,
            activation_frames=onsets, activation_times_s=[i/fps for i in onsets],
            ending_episode_start_s=None if continuous_end_start is None else continuous_end_start/fps,
            established=bool(observed_establishment and timeline[-1]),
            endpoint_active=bool(timeline[-1]), initially_on_target_surface=bool(timeline[0]),
            establishment_time_error_s=None)
        if reference_mask is not None:
            ref = torch.as_tensor(reference_mask)[:, part].bool() & (torch.as_tensor(reference_surface)[:, part]==wanted)
            ref_onset = ref & ~torch.cat((ref.new_zeros(1), ref[:-1]))
            ref_starts = [i for i in ref_onset.nonzero().flatten().tolist() if i>0]
            expected = ref_starts[-1] if ref_starts and bool(ref[-1]) else None
            item['reference_ending_episode_start_s'] = None if expected is None else expected/fps
            if expected is not None and continuous_end_start is not None and continuous_end_start>0:
                item['establishment_time_error_s'] = (continuous_end_start-expected)/fps
        if int(role[part])==2:
            valid = mask[:, part] & (surface[:, part]==int(start_surface[part]))
            off = ~valid
            starts = off & ~torch.cat((off.new_zeros(1), off[:-1]))
            lengths, length = [], 0
            for absent in off.tolist():
                if absent: length += 1
                elif length: lengths.append(length); length = 0
            if length: lengths.append(length)
            item.update(keep_coverage=float(valid.float().mean()), keep_disconnects=int(starts.sum()),
                keep_missing_sample_seconds=int(off.sum())/fps,
                keep_longest_missing_sample_seconds=max(lengths, default=0)/fps,
                keep_same_surface=bool(int(start_surface[part])==wanted))
        result.append(item)
    return result


def continuity_metrics(q, fps):
    q = torch.as_tensor(q, dtype=torch.float64)
    metrics = derivative_metrics(q[None], q.new_tensor([(len(q)-1)/fps]))
    result = {k:float(v[0]) for k,v in metrics.items()}
    for name, values in (('root',q[:, :3]), ('joint',q[:, 7:])):
        for order, label in ((1, 'velocity'), (2, 'acceleration'), (3, 'jerk')):
            delta = torch.diff(values, n=order, dim=0)*fps**order
            result[f'{name}_{label}_peak'] = float(delta.abs().max())
            result[f'{name}_{label}_rms'] = float(delta.square().mean().sqrt())
    rotation = _quaternion_matrix_wxyz(q[:, 3:7])
    omega = _rotation_log_vector(rotation[1:]@rotation[:-1].transpose(-1, -2))*fps
    result['root_angular_velocity_peak_rad_s'] = float(omega.norm(dim=-1).max())
    return result


def seam_metrics(left, right, fps):
    """Compare real shared boundaries in one world frame, without alignment."""
    a, b = torch.as_tensor(left, dtype=torch.float64), torch.as_tensor(right, dtype=torch.float64)
    ra, rb = _quaternion_matrix_wxyz(a[:,3:7]), _quaternion_matrix_wxyz(b[:,3:7])
    return dict(root_position_jump_m=float((a[-1,:3]-b[0,:3]).norm()),
        joint_jump_rad=float((a[-1,7:]-b[0,7:]).abs().max()),
        root_rotation_jump_rad=float(_rotation_log_vector(rb[0]@ra[-1].T).norm()),
        root_velocity_jump_m_s=float(((a[-1,:3]-a[-2,:3])-(b[1,:3]-b[0,:3])).norm()*fps),
        joint_velocity_jump_rad_s=float(((a[-1,7:]-a[-2,7:])-(b[1,7:]-b[0,7:])).abs().max()*fps),
        root_angular_velocity_jump_rad_s=float((_rotation_log_vector(ra[-1]@ra[-2].T)
            -_rotation_log_vector(rb[1]@rb[0].T)).norm()*fps))
