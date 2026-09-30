"""Source-relative material motion, independent of framewise contact witnesses.

These are optimization/slide diagnostics, never a contact classifier.
"""
import numpy as np
import torch
from somaforge_core.contact_motion import (
    CONTACT_MOTION_SCHEMA, contact_region_statistics,same_material_tangent_motion,calibrate_pivot_budgets)


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


def audit_phase_support(contract, steps, mask, surfaces, tolerance_m=None, distribution=None, budgets_m=None):
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
    """Geometric preservation budget for motion ADDED to the original source.

    Samples start from verified source contacts and refresh from current native
    witnesses at each audit. Missing groups retain source guidance; only native
    evidence can certify geometric motion coverage or contact. Keep intent does
    not require freezing the original motion or establish measured support.
    """
    def __init__(self, fk, source_q, labels_path, contract, tolerance_m=None, residual_scale_m=.001):
        import json
        from somaforge_core.contact_face_selection import select_contact_pairs
        with np.load(labels_path,allow_pickle=False) as z:
            semantics=json.loads(z['contact_semantics_json'].item())
            selected=select_contact_pairs(json.loads(z['contact_pairs_json'].item()),semantics['scene']['surface_catalog'])
        self.fk,self.contract,self.tolerance_m=fk,contract,tolerance_m
        self.source_q=source_q.detach().clone()
        self.surfaces=torch.full((len(source_q),6),-1,device=source_q.device,dtype=torch.long)
        for action in contract['actions']:
            for req in action['requirements']:
                if req['kind']!='keep':continue
                current=self.surfaces[action['start']:action['end'],req['part']]
                if bool(((current>=0)&(current!=req['surface'])).any()):raise ValueError('Conflicting phase support surface')
                current[:]=req['surface']
        if residual_scale_m <= 0:
            raise ValueError('Material motion residual scale must be positive')
        self.residual_scale_m=residual_scale_m
        wanted=self.surfaces.cpu().numpy()
        records=[(t,p) for t,pairs in enumerate(selected['contact_pairs'][:-1]) for p in pairs
                 if wanted[t,p['part']]==p['surface']]
        self.names=sorted({p['body_name'] for _,p in records})
        self.frames=torch.tensor([t for t,_ in records],device=source_q.device,dtype=torch.long)
        self.links=torch.tensor([self.names.index(p['body_name']) for _,p in records],device=source_q.device,dtype=torch.long)
        parts=torch.tensor([p['part'] for _,p in records],device=source_q.device,dtype=torch.long)
        points=source_q.new_tensor([p['position_w'] for _,p in records]).reshape(-1,3)
        with torch.no_grad():
            if self.names:
                pos,rot=fk.link_poses(source_q,self.names)
                self.local=torch.einsum('nji,nj->ni',rot[self.frames,self.links],points-pos[self.frames,self.links])
            else:
                self.local=source_q.new_empty((0,3))
        self.groups=self.frames*6+parts
        self.normals=source_q.new_tensor([p['normal_w'] for _,p in records]).reshape(-1,3)
        self.size=(len(source_q)-1)*6
        self._source=(tuple(self.names),self.frames,self.links,self.local,self.groups,self.normals)
        self._index_samples()
        counts=torch.bincount(self.groups,minlength=self.size)
        self.phases=[(a['start'],a['end'],r['part']) for a in contract['actions']
                     for r in a['requirements'] if r['kind']=='keep']
        for a,b,p in self.phases:
            if not bool((counts.reshape(-1,6)[a:b,p]>0).all()):
                raise ValueError('Source phase lacks actual material samples')
        with torch.no_grad():
            steps=self.steps(source_q)
            self.calibration=calibrate_pivot_budgets(steps,self.phases)
        self.tolerance_m=source_q.new_tensor([r['budget_m'] for r in self.calibration]) if tolerance_m is None else tolerance_m

    def _index_samples(self):
        counts=torch.bincount(self.groups,minlength=self.size)
        self.width=max(1,int(counts.max()))
        self.order=self.groups.argsort()
        self.sorted_groups=self.groups[self.order]
        self.slots=torch.arange(len(self.groups),device=self.groups.device)-(counts.cumsum(0)-counts)[self.sorted_groups]

    @torch.no_grad()
    def refresh(self, chunks):
        """Use the same witnesses as acceptance, without redefining contact.

        Missing groups retain source samples for guidance only; acceptance
        independently reports their missing native motion measurements.
        """
        names=chunks[0]['names']
        if any(c['names']!=names for c in chunks):
            raise ValueError('Native body mapping changed during trajectory audit')
        frames,parts,links,local,normals=(torch.cat([c[k] for c in chunks])
                                  for k in ('frames','parts','links','local','normals'))
        groups=frames*6+parts
        source_names,sf,sl,sx,sg,sn=self._source
        missing=torch.bincount(groups,minlength=self.size)[sg]==0
        remap=torch.tensor([names.index(name) for name in source_names],device=links.device,dtype=torch.long)
        self.names=names
        self.frames=torch.cat((frames,sf[missing]))
        self.links=torch.cat((links,remap[sl[missing]]))
        self.local=torch.cat((local,sx[missing]))
        self.groups=torch.cat((groups,sg[missing]))
        self.normals=torch.cat((normals,sn[missing]))
        self._index_samples()

    def steps(self,q):
        if not len(self.frames):
            return q.new_full((len(q)-1,6),float('nan'))
        pos,rot=self.fk.link_poses(q,self.names)
        t,j=self.frames,self.links
        delta=same_material_tangent_motion(pos,rot,t,j,self.local,self.normals)
        return contact_region_statistics(delta.norm(dim=-1),self.groups,self.size,
            width=self.width,validate=False)['pivot'].reshape(-1,6)

    def paths(self,q):
        if not self.phases:
            return q.new_empty(0)
        steps=self.steps(q)
        return torch.stack([steps[a:b,p].sum() for a,b,p in self.phases])

    def source_paths(self):
        """Re-evaluate the original motion at the SAME current material sites."""
        return self.paths(self.source_q).detach()

    def __call__(self,q):
        if not self.phases:
            return q.sum()*0
        paths=self.paths(q)
        # Existing original movement is preserved, not treated as slip to fix.
        extra=paths-self.source_paths()
        return ((extra-self.tolerance_m).relu()/self.residual_scale_m).square().mean()
