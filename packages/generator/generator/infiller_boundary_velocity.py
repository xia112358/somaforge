"""World-frame boundary velocities and self-generated history for the Infiller.

Velocity ordering is root translation (3), world angular velocity (3), joints
(29). Native finite differences are estimates, not integrated Newton state.
Generated corpus interiors are placeholders and never supply velocity labels.
"""
from __future__ import annotations

import torch
from torch.nn import functional as F
from somaforge_core.g1_kinematics import _quaternion_multiply_wxyz as multiply


def relative_rotation(start, end):
    start, end = F.normalize(start, dim=-1), F.normalize(end, dim=-1)
    conjugate = torch.cat((start[..., :1], -start[..., 1:]), -1)
    relative = multiply(end, conjugate)
    relative = torch.where(relative[..., :1] < 0, -relative, relative)
    vector = relative[..., 1:]
    norm = vector.norm(dim=-1, keepdim=True)
    angle = 2*torch.atan2(norm, relative[..., :1])
    factor = torch.where(norm > 1e-6, angle/norm.clamp_min(1e-6),
                         2+norm.square()/3)
    return vector*factor


def rotation_exp(vector):
    angle = vector.norm(dim=-1, keepdim=True)
    return torch.cat(((angle/2).cos(), .5*torch.sinc(angle/(2*torch.pi))*vector), -1)


def inverse_left_jacobian(rotation, velocity):
    angle = rotation.norm(dim=-1, keepdim=True)
    safe = angle.clamp_min(1e-4)
    coefficient = torch.where(angle > 1e-3,
        (1-.5*safe/torch.tan(.5*safe))/safe.square(),
        1/12+angle.square()/720)
    cross = torch.linalg.cross(rotation, velocity)
    return velocity-.5*cross+coefficient*torch.linalg.cross(rotation, cross)


def finite_difference_velocity(pair, dt):
    if pair.ndim != 3 or pair.shape[1:] != (2, 36):
        raise ValueError('Velocity requires [B,2,36] native poses')
    dt = torch.as_tensor(dt, device=pair.device, dtype=pair.dtype).reshape(-1, 1)
    if not bool(torch.isfinite(dt).all()) or bool((dt <= 0).any()):
        raise ValueError('Velocity requires positive finite elapsed time')
    return torch.cat((pair[:, 1, :3]-pair[:, 0, :3],
        relative_rotation(pair[:, 0, 3:7], pair[:, 1, 3:7]),
        pair[:, 1, 7:]-pair[:, 0, 7:]), -1)/dt


def hermite_pose(start, end, phase, duration, initial, terminal, residual):
    u = phase
    h01 = u.square()*(3-2*u)
    h10 = u*(1-u).square()
    h11 = u.square()*(u-1)
    time = duration[:, None, None]
    positions = torch.cat((start[:, :3], start[:, 7:]), -1)
    targets = torch.cat((end[:, :3], end[:, 7:]), -1)
    iv = torch.cat((initial[:, :3], initial[:, 6:]), -1)
    tv = torch.cat((terminal[:, :3], terminal[:, 6:]), -1)
    linear = ((1-h01)*positions[:, None]+h01*targets[:, None]
              +time*(h10*iv[:, None]+h11*tv[:, None]))
    rotation = relative_rotation(start[:, 3:7], end[:, 3:7])
    tangent = inverse_left_jacobian(rotation, terminal[:, 3:6])
    vector = (h01*rotation[:, None]+time*(h10*initial[:, None, 3:6]+h11*tangent[:, None]))
    gate = 16*u.square()*(1-u).square()
    linear = linear+gate*torch.cat((residual[..., :3], residual[..., 7:]), -1)
    vector = vector+gate*2*residual[..., 4:7]
    quaternion = multiply(rotation_exp(vector), start[:, None, 3:7])
    return torch.cat((linear[..., :3], quaternion, linear[..., 3:]), -1)


def velocity_objective(model, batch):
    """Only real demonstrations provide start/end velocity targets."""
    mask = batch['demo']
    if not bool(mask.any()):
        return batch['q'].sum()*0, dict(boundary_velocity_supervision=None)
    if getattr(model, 'conditional_boundary', False):
        return sampled_velocity_objective(model, batch, mask)
    contract = {k:v[mask] for k,v in batch['contract'].items()}
    scene = {k:v[mask] for k,v in batch['scene'].items()}
    q = batch['q'][mask]
    duration = batch.get('reference_duration', batch['duration'])[mask]
    dt = duration/(q.shape[1]-1)
    target_initial = finite_difference_velocity(q[:, :2], dt)
    target_terminal = finite_difference_velocity(q[:, -2:], dt)
    incoming = batch.get('start_velocity')
    known = batch.get('velocity_known')
    _, terminal, estimate, _ = model.boundary_velocities(q[:, 0], q[:, -1], contract,
        scene, batch['duration'][mask],
        start_velocity=None if incoming is None else incoming[mask],
        velocity_known=None if known is None else known[mask])
    loss = (F.smooth_l1_loss(estimate/model.velocity_scale, target_initial/model.velocity_scale)
            +F.smooth_l1_loss(terminal/model.velocity_scale, target_terminal/model.velocity_scale))
    metrics = dict(boundary_velocity_supervision=loss,
        terminal_joint_velocity_mae=(terminal[:, 6:]-target_terminal[:, 6:]).abs().mean())
    return loss, metrics


def sample_expert_phase(q, phase):
    """Interpolate real expert poses, never contact labels or generated interiors.

    The same normalized path is sampled on the decoder's chosen time grid.
    Thus finite-difference targets use exactly the prediction's elapsed time.
    """
    coordinate=phase.squeeze(-1)*(q.shape[1]-1)
    lower=coordinate.floor().long().clamp(0,q.shape[1]-1)
    upper=(lower+1).clamp_max(q.shape[1]-1)
    index=torch.arange(len(q),device=q.device)[:,None]
    a,z=q[index,lower],q[index,upper]
    u=(coordinate-lower)[...,None]
    linear=(1-u)*a+u*z
    rotation=multiply(rotation_exp(u*relative_rotation(a[...,3:7],z[...,3:7])),a[...,3:7])
    return torch.cat((linear[...,:3],rotation,linear[...,7:]),-1)


def expert_native_pair(record, count, tail, device):
    if record['kind']!='demonstration':
        raise ValueError('Generated interiors cannot supply expert seam targets')
    q=record['q'].to(device)[None]
    count=torch.as_tensor(count,device=device,dtype=q.dtype).reshape(1)
    phase=(torch.stack((1-1/(count-1),torch.ones_like(count)),-1) if tail else
           torch.stack((torch.zeros_like(count),1/(count-1)),-1))[...,None]
    return sample_expert_phase(q,phase)


def sampled_velocity_objective(model, batch, mask):
    q=batch['q'][mask]
    count=(batch['motion_frames'][mask].detach().round() if model.predicts_frames else
           q.new_full((len(q),),q.shape[1]))
    duration=(count-1)/50 if model.predicts_frames else batch['duration'][mask]
    dt=duration/(count-1)
    zero=torch.zeros_like(count);one=torch.ones_like(count)
    phase=torch.stack((zero,1/(count-1),one-1/(count-1),one),-1)[...,None]
    predicted=model(q[:,0],q[:,-1],phase,
        {k:v[mask] for k,v in batch['contract'].items()},
        {k:v[mask] for k,v in batch['scene'].items()},duration,
        start_velocity=None if batch.get('start_velocity') is None else batch['start_velocity'][mask],
        velocity_known=None if batch.get('velocity_known') is None else batch['velocity_known'][mask])
    target=sample_expert_phase(q,phase).detach()
    initial=finite_difference_velocity(predicted[:,:2],dt)
    terminal=finite_difference_velocity(predicted[:,-2:],dt)
    ti=finite_difference_velocity(target[:,:2],dt)
    tt=finite_difference_velocity(target[:,-2:],dt)
    loss=(F.smooth_l1_loss(initial/model.velocity_scale,ti/model.velocity_scale)
          +F.smooth_l1_loss(terminal/model.velocity_scale,tt/model.velocity_scale))
    return loss,dict(boundary_velocity_supervision=loss,
        terminal_joint_velocity_mae=(terminal[:,6:]-tt[:,6:]).abs().mean(),
        initial_joint_velocity_mae=(initial[:,6:]-ti[:,6:]).abs().mean())


class SelfGeneratedHistory:
    """Decode native prefix velocities from boundaries only; no teacher history.

    Per-update caching keeps weights consistent. Prefixes are detached for
    training; the current pair still has gradients through the seam objective.
    """
    def __init__(self, model, records, device, boundary_cache=None):
        from generator.recursive_refinement import adjacent_records
        self.model, self.records, self.device = model, records, device
        pairs = adjacent_records(records)
        if len(set(pairs.values())) != len(pairs):
            raise ValueError('Ambiguous trajectory predecessors')
        self.predecessors = {right:left for left,right in pairs.items()}
        self.cache = {}
        self.boundary_cache = boundary_cache

    @torch.no_grad()
    def incoming(self, index):
        from generator.direct_infiller import collate, decode_batch, prepare_frame_prediction
        previous = self.predecessors.get(index)
        if previous is None:
            return None
        if previous in self.cache:
            return self.cache[previous]
        path, visiting = [], set()
        while previous is not None and previous not in self.cache:
            if previous in visiting:
                raise ValueError('Cyclic trajectory history')
            visiting.add(previous); path.append(previous)
            previous = self.predecessors.get(previous)
        velocity = self.cache.get(previous)
        for prior in reversed(path):
            batch = prepare_frame_prediction(self.model, collate([self.records[prior]], self.device))
            batch['start_velocity'] = velocity
            count = (batch['motion_frames'].round() if self.model.predicts_frames else
                     batch['q'].new_tensor([len(self.records[prior]['q'])]))
            # History matches rounded native inference, including elapsed time.
            batch['duration'] = (count-1)/50
            phase = torch.stack((1-1/(count-1), torch.ones_like(count)), -1)[..., None]
            pair = decode_batch(self.model, batch, phase)
            velocity = finite_difference_velocity(pair, 1/50).detach()
            self.cache[prior] = velocity
        return velocity

    def condition(self, batch, indices):
        if self.boundary_cache is not None:
            self.ensure(indices)
        values = [self.incoming(index) for index in indices]
        batch['start_velocity'] = torch.cat([batch['q'].new_zeros(1, 35) if v is None else v
                                            for v in values])
        batch['velocity_known'] = torch.tensor([v is not None for v in values], device=self.device)
        return batch

    @torch.no_grad()
    def ensure(self, indices):
        """Batch independent chains at each prefix depth, preserving recurrence."""
        from generator.direct_infiller import decode_batch
        required = set()
        for index in indices:
            prior = self.predecessors.get(index)
            visiting = set()
            while prior is not None and prior not in self.cache:
                if prior in visiting:raise ValueError('Cyclic trajectory history')
                visiting.add(prior)
                if prior in required:break
                required.add(prior);prior=self.predecessors.get(prior)
        while required:
            ready = sorted(i for i in required if self.predecessors.get(i) not in required)
            if not ready:raise ValueError('Cyclic trajectory history')
            for first in range(0,len(ready),128):
                chosen=ready[first:first+128]
                batch=self.boundary_cache.native_batch(chosen)
                values=[self.cache.get(self.predecessors.get(i)) for i in chosen]
                batch['start_velocity']=torch.cat([batch['q'].new_zeros(1,35) if v is None else v for v in values])
                batch['velocity_known']=torch.tensor([v is not None for v in values],device=self.device)
                count=batch['native_count']
                phase=torch.stack((1-1/(count-1),torch.ones_like(count)),-1)[...,None]
                pair=decode_batch(self.model,batch,phase)
                velocity=finite_difference_velocity(pair,1/50).detach()
                for i,v in zip(chosen,velocity):self.cache[i]=v[None]
            required.difference_update(ready)

    def store(self, index, native_q):
        self.cache[index] = finite_difference_velocity(native_q[None, -2:], 1/50).detach()


def warmup_velocity_heads(model, training, validation, cfg, device):
    """Independent expert supervision, with unknown/model-estimated history.

    Real demonstration velocities are labels only. No teacher velocity enters
    the terminal head as context; pose/scene/time are the available inputs.
    """
    import json
    from generator.direct_infiller import collate

    @torch.no_grad()
    def features(records):
        experts = [r for r in records if r['kind'] == 'demonstration']
        if not experts:
            raise ValueError('Boundary velocity warmup requires real demonstrations')
        values = []
        for r in experts:
            b = collate([r], device); q = b['q']
            time = (model.frame_count(q[:, 0], q[:, -1], b['contract'], b['scene'])-1)/50 if model.predicts_frames else b['duration']
            static, _, _, _ = model.boundary_features(q[:, 0], q[:, -1], b['contract'], b['scene'])
            secant = finite_difference_velocity(torch.stack((q[:, 0], q[:, -1]), 1), time)
            dt = b['duration']/(q.shape[1]-1)
            values.append((torch.cat((static, time[:, None]), -1), secant, time,
                finite_difference_velocity(q[:, :2], dt), finite_difference_velocity(q[:, -2:], dt)))
        return tuple(torch.cat([v[i] for v in values]) for i in range(5))

    x, secant, time, yi, yz = features(training)
    vx, vs, vt, vi, vz = features(validation)
    untouched = {k:v.detach().clone() for k,v in model.state_dict().items()
                 if not k.startswith(('initial_velocity_head.', 'terminal_velocity_head.'))}
    parameters = list(model.initial_velocity_head.parameters())+list(model.terminal_velocity_head.parameters())
    optimizer = torch.optim.Adam(parameters, lr=.001)
    generator = torch.Generator(device=device).manual_seed(cfg.seed)

    def predict(features, secant, duration):
        initial = secant+model.initial_velocity_head(features)*model.velocity_scale/duration[:, None]
        inputs = torch.cat((features, initial*duration[:, None]/model.velocity_scale,
                            features.new_zeros(len(features), 1)), -1)
        terminal = secant+model.terminal_velocity_head(inputs)*model.velocity_scale/duration[:, None]
        return initial, terminal

    best, best_state, history = float('inf'), None, []
    for step in range(cfg.velocity_warmup_steps+1):
        if step:
            index = torch.randint(len(x), (128,), device=device, generator=generator)
            initial, terminal = predict(x[index], secant[index], time[index])
            loss = (F.smooth_l1_loss(initial/model.velocity_scale, yi[index]/model.velocity_scale)
                    +F.smooth_l1_loss(terminal/model.velocity_scale, yz[index]/model.velocity_scale))
            optimizer.zero_grad(set_to_none=True); loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, 10, error_if_nonfinite=True)
            optimizer.step()
        if step%250 == 0 or step == cfg.velocity_warmup_steps:
            with torch.no_grad():
                initial, terminal = predict(vx, vs, vt)
                score = float(((initial-vi).abs()/model.velocity_scale).mean()
                              +((terminal-vz).abs()/model.velocity_scale).mean())
                record = dict(stage='velocity_warmup', step=step, validation_normalized_mae=score,
                    initial_joint_mae_rad_s=float((initial[:, 6:]-vi[:, 6:]).abs().mean()),
                    terminal_joint_mae_rad_s=float((terminal[:, 6:]-vz[:, 6:]).abs().mean()),
                    train_experts=len(x), validation_experts=len(vx), test_used=False)
            if score < best:
                best, best_step = score, step
                best_state = {k:v.detach().clone() for k,v in model.state_dict().items()
                              if k.startswith(('initial_velocity_head.', 'terminal_velocity_head.'))}
            history.append(record); print(json.dumps(record), flush=True)
            (cfg.report/'velocity_warmup_progress.json').write_text(json.dumps(record, indent=2)+'\n')
    model.load_state_dict(best_state, strict=False)
    if any(not torch.equal(value, model.state_dict()[key]) for key,value in untouched.items()):
        raise AssertionError('Velocity warmup altered timing or trajectory parameters')
    result = dict(best_step=best_step, validation_normalized_mae=best, history=history,
        supervision='real demonstration native 50Hz first/last finite differences only',
        velocity_context='unknown; model estimated initial velocity; no teacher velocity input', test_used=False)
    (cfg.output/'velocity_warmup.json').write_text(json.dumps(result, indent=2)+'\n')
    return result
