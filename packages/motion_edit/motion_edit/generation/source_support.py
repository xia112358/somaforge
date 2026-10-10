"""Source-relative material motion, independent of framewise contact witnesses.

These are optimization/slide diagnostics, never a contact classifier.
"""
import numpy as np
import torch
from somaforge_core.loaded_material_motion import (
    DEFAULT_MATERIAL_RESIDUAL_SCALE_M, DEFAULT_MATERIAL_PATH_BUDGET_M,
    DEFAULT_SOURCE_ADDED_MOTION_WEIGHT, phase_material_paths)
from somaforge_core.contact_motion import (
    CONTACT_MOTION_SCHEMA, contact_region_statistics,same_material_tangent_motion)


def build_support_reference(spec, domains, valid):
    from motion_edit.contact.surface_frame import map_points_between_surface_frames
    transforms = spec.metadata['support_surface_transforms']
    rotations = np.broadcast_to(np.eye(3), (*valid.shape, 3, 3)).copy()
    normals = np.zeros((*valid.shape, 3))
    for t, part in zip(*np.nonzero(valid)):
        geometry = domains[t][part]
        normal = np.asarray(geometry['normal'])
        matches = [tr for tr in transforms if
                   np.allclose(tr['target_surface']['normal'], normal, atol=1.e-6) and
                   np.isclose(np.dot(tr['target_surface']['origin'], normal),
                              np.dot(geometry['origin'], normal), atol=1.e-6)]
        if not matches:
            raise ValueError('No authored surface transform for source support')
        matrices = []
        for tr in matches:
            basis = map_points_between_surface_frames(np.vstack((np.zeros(3), np.eye(3))),
                                                     tr['source_surface'], tr['target_surface'])
            matrices.append((basis[1:]-basis[0]).T)
        if not all(np.allclose(matrices[0], r, atol=1.e-7) for r in matrices):
            raise ValueError('Ambiguous support rotation')
        rotations[t, part] = matrices[0]
        normals[t, part] = normal
    return rotations, normals


def support_residuals(positions, rotations, source_positions, source_rotations,
                      local, edit_rotations, normals, persistent):
    # Use the SAME material point on both sides of each time interval. A heel
    # to toe witness change therefore cannot masquerade as sliding.
    def displacement(p, r):
        return p[1:]-p[:-1]+torch.einsum('tpij,tpj->tpi', r[1:]-r[:-1], local[:-1])
    error = displacement(positions, rotations)-torch.einsum(
        'tpij,tpj->tpi', edit_rotations[:-1], displacement(source_positions, source_rotations))
    normal = normals[:-1]
    error = error-(error*normal).sum(-1, keepdim=True)*normal
    error = error*persistent[..., None]
    # Accumulate over an endpoint/surface event; witness changes do not reset.
    cumulative = torch.cumsum(error, dim=0)
    indices = torch.arange(len(error), device=error.device)[:, None].expand_as(persistent)
    resets = torch.where(~persistent, indices, torch.zeros_like(indices)).cummax(0).values
    origin = cumulative.gather(0, resets[..., None].expand_as(cumulative))
    # Index zero is only an origin if interval zero is inactive.
    origin = torch.where((resets == 0)[..., None] & persistent[0][None, :, None],
                         torch.zeros_like(origin), origin)
    return error, cumulative-origin


def support_statistics(step, drift, persistent):
    selected = persistent[..., None].expand_as(step)
    if not bool(persistent.any()):
        return dict(extra_step_max_mm=0., extra_step_rms_mm=0., accumulated_drift_max_mm=0.)
    return dict(extra_step_max_mm=float(step.norm(dim=-1)[persistent].max()*1000),
                extra_step_rms_mm=float(step[selected].square().mean().sqrt()*1000),
                accumulated_drift_max_mm=float(drift.norm(dim=-1)[persistent].max()*1000))


def initialize_source_edit(source_path, plan_path, output_path):
    """Run the authored edit from the source, never an archived augmented pose."""
    import hashlib
    import json
    from pathlib import Path
    from .rollout_authority import generate_contact_aware_pyroki_preview
    source_path, plan_path, output_path = map(Path,(source_path,plan_path,output_path))
    plan=json.loads(plan_path.read_text())
    if Path(plan['source_motion_path']).resolve()!=source_path.resolve():
        raise ValueError('Plan/source authority mismatch')
    generated=output_path.parent/'generated'/output_path.name
    generate_contact_aware_pyroki_preview(plan_path,output_motion_path=generated,
        intermediate_dir=output_path.parent/'taskspaces'/output_path.stem,
        ik_max_nfev=25,ik_q_acceleration_weight=8.)
    # This artifact was produced by the editor immediately above. Its legacy
    # joint-name array uses object dtype; normalize it at this boundary so the
    # refinement input itself never requires pickle loading.
    with np.load(generated,allow_pickle=True) as z:
        data={k:z[k].copy() for k in ('joint_pos','joint_names','fps','robot_asset_json')}
    data['joint_names']=np.asarray(data['joint_names'],dtype=str)
    metadata=dict(schema='authoritative_source_edited_initializer_v1',source=str(source_path.resolve()),
        source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        plan_id=plan['plan_id'],plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        generated_motion=str(generated.resolve()),archived_augmentation_used=False)
    data['source_initializer_json']=np.asarray(json.dumps(metadata))
    output_path.parent.mkdir(parents=True,exist_ok=True)
    with output_path.open('xb') as stream:np.savez_compressed(stream,**data)
    return metadata


@torch.no_grad()
def native_material_samples(fk, q, observed, indices, wanted_surfaces=None):
    """Freeze current native material witnesses for one local optimization."""
    p=observed['pairs'];ids=torch.as_tensor(indices,device=q.device)
    if 'normal_w' not in p:raise ValueError('Missing actual contact normals; material tangent motion unknown')
    # Candidates in activation holes cannot certify supporting-region motion.
    selected=p['eligible'] & p['upward'] & p['task_pair'] & (p['body_link0']<0) & (p['body_link1']>=0)
    selected &= ids[p['sample']] < len(q)-1
    if wanted_surfaces is not None:
        wanted=wanted_surfaces[ids[p['sample']],p['part'].clamp(0,5)]
        selected &= (wanted>=0) & (p['surface']==wanted)
    sample=p['sample'][selected];part=p['part'][selected];link=p['body_link1'][selected]
    point=p['geometry_point1_w'][selected]
    pos,rot=fk.link_poses(q,observed['link_names'])
    frame=ids[sample]
    local=torch.einsum('nji,nj->ni',rot[frame,link],point-pos[frame,link])
    return dict(frames=frame, parts=part, links=link, local=local,
                normals=p['normal_w'][selected],
                names=tuple(observed['link_names']))


@torch.no_grad()
def native_material_motion(fk, q, observed, indices, samples=None):
    """Actual-contact region distribution, following each material point."""
    s=native_material_samples(fk,q,observed,indices) if samples is None else samples
    frame,link,local=s['frames'],s['links'],s['local']
    pos,rot=fk.link_poses(q,s['names'])
    delta=same_material_tangent_motion(pos,rot,frame,link,local,s['normals'])
    distance=delta.norm(dim=-1)
    ids=torch.as_tensor(indices,device=q.device)
    group=torch.searchsorted(ids,frame)*6+s['parts'];size=len(indices)*6
    return {key: value.reshape(len(indices),6).cpu().numpy()
            for key,value in contact_region_statistics(distance,group,size).items()}


def native_material_steps(fk, q, observed, indices, samples=None):
    """Actual-contact pivot step; not a whole-region no-slip certificate."""
    return native_material_motion(fk,q,observed,indices,samples)['pivot']


def audit_geometric_phase_motion(contract, steps, mask, surfaces, tolerance_m=None, distribution=None, budgets_m=None):
    """Report absolute stage motion; never allow contact dropout to erase it."""
    rows=[]
    for action in contract['actions']:
        a,b=action['start'],action['end']
        for req in action['requirements']:
            if req['kind']!='keep':continue
            part,face=req['part'],req['surface']
            on=mask[a:b+1,part] & (surfaces[a:b+1,part]==face)
            values=steps[a:b,part]
            valid=np.isfinite(values)
            complete=bool(valid.all())
            path=float(values[valid].sum())
            if budgets_m is not None and len(rows)>=len(budgets_m):raise ValueError('Phase budget count differs')
            budget=(float(budgets_m[len(rows)] if budgets_m is not None else tolerance_m)
                    if budgets_m is not None or tolerance_m is not None else None)
            if budget is not None and (not np.isfinite(budget) or budget<0):raise ValueError('Invalid contact motion budget')
            row=dict(action=action['id'],start=a,end=b,part=part,surface=face,
                actual_off_frames=(np.flatnonzero(~on)+a).tolist(),
                measured_steps=int(valid.sum()),required_steps=b-a,
                material_tangent_path_m=path,measurement_complete=complete,
                geometric_pivot_path_m=path,budget_m=budget,
                force_bearing_slip_status='unknown_without_same_solve_loads',
                passed=None if budget is None else complete and path<=budget)
            if distribution is not None:
                row['region_path_m']={key:float(distribution[key][a:b,part][valid].sum())
                    for key in ('minimum','pivot','lower_quartile','median','upper_quartile','maximum')}
                row['contact_sample_count_min']=int(distribution['count'][a:b,part].min())
            rows.append(row)
    if budgets_m is not None and len(rows)!=len(budgets_m):raise ValueError('Phase budget count differs')
    return dict(schema='explicit_phase_pivot_and_region_motion_v3',motion_metric=CONTACT_MOTION_SCHEMA,
                geometric_metric='actual_contact_pivot_minimum',tolerance_m=tolerance_m,
                budget_source='source_relative_allowance' if budgets_m is not None else 'explicit_diagnostic' if tolerance_m is not None else 'unknown',
                support_location_status='unknown_without_same_solve_per_constraint_force',
                acceptance_scope='geometric_motion_budget_only_not_force_bearing_support',
                passed=None if rows and any(r['passed'] is None for r in rows) else all(r['passed'] for r in rows),phases=rows)


class SourcePhaseMotion:
    """Frozen original loaded-site reference for whole-trajectory refinement.

    Fresh static witnesses only certify contact and geometry. They never replace
    original load sites or weights. The cumulative phase budget is the motion
    constraint; source-relative positive excess is only a soft regularizer.
    """
    def __init__(self, fk, source_q, reference, contract, residual_scale_m=DEFAULT_MATERIAL_RESIDUAL_SCALE_M):
        from somaforge_core.loaded_material_motion import source_motion_allowances
        if not isinstance(reference, dict) or 'sites' not in reference:
            raise ValueError('Source phase motion requires original loaded execution reference, not static labels')
        self.fk, self.contract = fk, contract
        self.source_q = source_q.detach().clone()
        self.reference = reference
        self.phase_records = reference['phases']
        expected = {(a['id'], a['start'], a['end'], r['part'], r['surface'])
            for a in contract['actions'] for r in a['requirements'] if r['kind'] == 'keep'}
        actual = {(p['event_id'], p['start'], p['end'], p['part'], p['surface']) for p in self.phase_records}
        if actual != expected or len(actual) != len(self.phase_records):
            raise ValueError('Loaded material phases differ from event contract')
        self.residual_scale_m = float(residual_scale_m)
        if not np.isfinite(self.residual_scale_m) or self.residual_scale_m <= 0:
            raise ValueError('Material motion residual scale must be positive')
        sites = reference['sites']
        self.names = sorted(set(sites['body'].astype(str)))
        self.arguments = dict(frames=sites['frame'], links=[self.names.index(str(n)) for n in sites['body']],
            parts=sites['part'], local=sites['local'], normals=sites['normal'], loads=sites['weight'], surfaces=sites['surface'])
        with torch.no_grad():
            self.original_steps = self.steps(self.source_q).detach()
        # Verify the differentiable FK uses the exact original motion convention.
        np.testing.assert_allclose(self.original_steps.cpu().numpy(), reference['source_steps'], atol=2.e-6, rtol=1.e-4)
        self.calibration = source_motion_allowances(reference['source_steps'], self.phase_records,
            load_known=reference['load_known'], load_bearing=reference['load_bearing'])
        if any(not p['measurement_complete'] for p in self.calibration):
            raise ValueError('Source loaded material allowance unknown')
        self.tolerance_m = source_q.new_tensor([0. if p['allowance_m'] is None else p['allowance_m'] for p in self.calibration])

    def steps(self, q):
        from somaforge_core.loaded_material_motion import loaded_material_steps
        if not self.names:
            return q.new_full((len(q)-1,6),float('nan'))+q.sum()*0
        pos, rot = self.fk.link_poses(q, self.names)
        return loaded_material_steps(pos, rot, **self.arguments)

    def paths(self, q):
        paths, complete = phase_material_paths(self.steps(q), self.phase_records,
            load_known=self.reference['load_known'], load_bearing=self.reference['load_bearing'])
        if not bool(complete.all()):
            raise ValueError('Incomplete loaded material evidence in refinement')
        return paths

    def source_paths(self):
        return self.paths(self.source_q).detach()

    def __call__(self, q):
        from somaforge_core.loaded_material_motion import phase_added_motion
        values = self.steps(q)
        extra, complete = phase_added_motion(values, self.original_steps, self.phase_records,
            load_known=self.reference['load_known'], load_bearing=self.reference['load_bearing'])
        paths, path_complete = phase_material_paths(values, self.phase_records,
            load_known=self.reference['load_known'], load_bearing=self.reference['load_bearing'])
        if not bool((complete & path_complete).all()):
            raise ValueError('Incomplete loaded material evidence in refinement')
        if not len(extra):
            return q.sum()*0
        budget = ((paths-DEFAULT_MATERIAL_PATH_BUDGET_M).relu()/self.residual_scale_m).square().mean()
        preservation = ((extra-self.tolerance_m).relu()/self.residual_scale_m).square().mean()
        return budget+DEFAULT_SOURCE_ADDED_MOTION_WEIGHT*preservation

    @torch.no_grad()
    def audit(self, q):
        from .loaded_material_reference import compare_paths
        from somaforge_core.loaded_material_motion import MATERIAL_MOTION_SCHEMA
        phases = compare_paths(self.reference['source_steps'], self.steps(q).cpu().numpy(), self.phase_records,
            load_known=self.reference['load_known'], load_bearing=self.reference['load_bearing'])
        for row in phases:
            row['passed'] = row['motion_budget_passed']
        return dict(schema=MATERIAL_MOTION_SCHEMA, phases=phases,
            budget_m=DEFAULT_MATERIAL_PATH_BUDGET_M,
            acceptance_rule='complete_loaded_material_phase_path_within_budget',
            source_added_motion_role='soft_regularizer_and_diagnostic_only',
            passed=None if any(p['passed'] is None for p in phases) else all(p['passed'] for p in phases),
            acceptance_scope='original_loaded_site_geometry_reference_not_execution_truth')
