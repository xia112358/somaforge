"""Original loaded sites as editing references, never edited execution loads."""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from scipy.spatial.transform import Rotation

from somaforge_core.loaded_material_motion import (
    MATERIAL_MOTION_SCHEMA, DEFAULT_MATERIAL_RESIDUAL_SCALE_M, DEFAULT_MATERIAL_PATH_BUDGET_M,
    DEFAULT_SOURCE_ADDED_MOTION_WEIGHT, loaded_material_steps, material_path_report,
    phase_added_motion, source_motion_allowances, tangent_material_rms)
from somaforge_core.newton_support import select_support_contacts
from somaforge_core.support_evidence import load_support_observations


def export_sites(motion, observations, original_state, output):
    observed = load_support_observations(motion, observations)
    with np.load(original_state,allow_pickle=False) as z:
        provenance=json.loads(z['rollout_provenance_json'].item())
        source_q=z['joint_pos']
    with np.load(motion,allow_pickle=False) as z:
        if not np.allclose(z['joint_pos'],source_q,atol=1.e-6,rtol=0):
            raise ValueError('Loaded editing references require unchanged physical source poses')
    recording=Path(provenance['recording'])
    if hashlib.sha256(recording.read_bytes()).hexdigest()!=provenance['sha256']:
        raise ValueError('Original recording changed')
    records=[]
    with np.load(recording,allow_pickle=False) as z:
        meta=json.loads(z['_metadata_json'].item())
        fields={k[len('solver_contact_'):]:z[k] for k in z.files
                if k.startswith('solver_contact_') and k!='solver_contact_count'}
        for t,frame in enumerate(provenance['native_frame_indices'][:-1]):
            n=int(z['solver_contact_count'][frame])
            belongs=fields['worldid'][frame,:n]==provenance['env']
            snapshot={k:v[frame,:n][belongs] for k,v in fields.items()};snapshot['count']=int(belongs.sum())
            selected=select_support_contacts(snapshot,meta['newton_scene_binding'],meta['newton_body_labels'])
            forces=np.einsum('ni,ni->n',snapshot['force_on_body1_w'],snapshot['frame_w'][:,0])
            for i in np.flatnonzero(selected['eligible'] & (forces>0)):
                side=int(selected['robot_side'][i])
                records.append((t,int(selected['groups'][i]%6),int(selected['surfaces'][i]),
                    meta['newton_body_labels'][int(snapshot[f'body{side}'][i])].rsplit('/',1)[-1],
                    snapshot[f'application_point{side}_local'][i],snapshot['frame_w'][i,0],forces[i]))
    if not records:raise ValueError('No original loaded sites')
    arrays=dict(frame=np.array([r[0] for r in records]),part=np.array([r[1] for r in records]),
        surface=np.array([r[2] for r in records]),body=np.array([r[3] for r in records]),
        local=np.array([r[4] for r in records]),normal=np.array([r[5] for r in records]),
        weight=np.array([r[6] for r in records]),
        load_known=observed['load_known'][:-1], load_bearing=observed['load_bearing'][:-1],
        metadata_json=np.array(json.dumps(dict(
            schema='source_loaded_material_edit_reference_v1',source_sha256=hashlib.sha256(Path(motion).read_bytes()).hexdigest(),
            recording=provenance,clock='original solve sites evaluated through post-integration pose FK; geometric editing reference only',
            edited_force_truth=False))))
    with Path(output).open('xb') as stream:np.savez_compressed(stream,**arrays)
    return arrays


def material_steps(motion, sites, frame_count):
    with np.load(motion,allow_pickle=False) as z:
        names=z['body_names'].astype(str).tolist();position=z['body_pos_w'];quaternion=z['body_quat_w']
    if len(position)!=frame_count:raise ValueError('Reference and edited pose clocks differ')
    rot=Rotation.from_quat(quaternion[..., [1,2,3,0]].reshape(-1,4)).as_matrix().reshape(*quaternion.shape[:-1],3,3)
    return loaded_material_steps(torch.as_tensor(position, dtype=torch.float64),
        torch.as_tensor(rot, dtype=torch.float64), frames=sites['frame'],
        links=np.array([names.index(s) for s in sites['body']]), parts=sites['part'],
        local=sites['local'], normals=sites['normal'], loads=sites['weight'],
        surfaces=sites['surface']).detach().numpy()



def remap_reference_sites(sites, source_frames, *, load_known, load_bearing):
    """Bind source reference sites to a cropped pose clock, never new loads.

    A removed span has no adjacent source solve. Its seam is unknown, even
    when a soft geometric connection passes static Newton contact checks.
    """
    frames = np.asarray(source_frames, dtype=int)
    known, bearing = np.asarray(load_known, bool), np.asarray(load_bearing, bool)
    if (frames.ndim != 1 or len(frames) < 2 or np.any(np.diff(frames) <= 0)
            or known.shape != bearing.shape or known.ndim != 2 or known.shape[1] != 6
            or frames[0] < 0 or frames[-1] > len(known)):
        raise ValueError('Invalid source-reference crop clock')
    adjacent = np.diff(frames) == 1
    lookup = np.full(len(known), -1, dtype=int)
    lookup[frames[:-1][adjacent]] = np.flatnonzero(adjacent)
    source_site_frames = np.asarray(sites['frame'], int)
    if np.any((source_site_frames < 0) | (source_site_frames >= len(known))):
        raise ValueError('Source sites outside load clock')
    mapped = lookup[source_site_frames]
    keep = mapped >= 0
    result = {key: np.asarray(sites[key])[keep] for key in
              ('part', 'surface', 'body', 'local', 'normal', 'weight')}
    result['frame'] = mapped[keep]
    new_known, new_bearing = known[frames[:-1]].copy(), bearing[frames[:-1]].copy()
    new_known[~adjacent] = False
    new_bearing[~adjacent] = False
    return result, new_known, new_bearing


def compare_paths(source_steps, edited_steps, phases, *, load_known, load_bearing):
    source_budget = material_path_report(source_steps, phases, load_known=load_known,
                                        load_bearing=load_bearing)
    edited_budget = material_path_report(edited_steps, phases, load_known=load_known,
                                        load_bearing=load_bearing)
    calibration = source_motion_allowances(source_steps, phases, load_known=load_known, load_bearing=load_bearing)
    added, complete = phase_added_motion(torch.as_tensor(edited_steps), source_steps, phases,
        load_known=load_known, load_bearing=load_bearing)
    result=[]
    for i, phase in enumerate(phases):
        a,b,p=(phase[k] for k in ('start','end','part'))
        reference=source_steps[a:b,p];candidate=edited_steps[a:b,p]
        known=np.asarray(load_known)[a:b,p] & np.asarray(load_bearing)[a:b,p] & np.isfinite(reference)
        if np.any(known & ~np.isfinite(candidate)):raise ValueError('Edited source-site motion missing')
        # Missing/unloaded source locations never become artificial fixed sites.
        allowance=calibration[i]['allowance_m']
        extra=float(added[i])
        budget_passed=(True if bool(complete[i]) and calibration[i]['loaded_intervals']==0
                       else edited_budget['phases'][i]['within_budget'])
        result.append(dict(**phase,source_path_cm=source_budget['phases'][i]['material_tangent_path_m']*100,
            edited_path_cm=edited_budget['phases'][i]['material_tangent_path_m']*100,added_motion_cm=extra*100,
            source_loaded_steps=int(known.sum()),source_without_loaded_site_frames=(np.flatnonzero(~known)+a).tolist(),
            allowance_cm=None if allowance is None else allowance*100,
            reference_motion_passed=None if allowance is None or not bool(complete[i]) else extra<=allowance,
            reference_motion_check_role='diagnostic_only_not_acceptance',
            motion_budget_passed=budget_passed,
            reference_motion_status=('unknown_reference' if not bool(complete[i]) else
                'known_unloaded_not_constrained' if calibration[i]['loaded_intervals']==0 else 'measured_loaded_reference'),
            metric='original_load_weighted_RMS_same_material_point_displacement',
            material_motion_schema=edited_budget['schema'],
            source_budget=source_budget['phases'][i], edited_budget=edited_budget['phases'][i],
            actual_edited_support='unknown_without_new_execution'))
    return result


def read_loaded_reference(motion, sites_path, observations, phases_path):
    """Require independent source execution evidence, never static witnesses."""
    motion = Path(motion)
    observed = load_support_observations(motion, observations)
    with np.load(sites_path, allow_pickle=False) as z:
        sites = {key: z[key].copy() for key in z.files}
    metadata = json.loads(sites['metadata_json'].item())
    if (metadata.get('schema') != 'source_loaded_material_edit_reference_v1'
            or metadata.get('source_sha256') != hashlib.sha256(motion.read_bytes()).hexdigest()
            or metadata.get('edited_force_truth') is not False
            or metadata.get('recording', {}).get('sha256') != observed['provenance']['recording']['sha256']):
        raise ValueError('Loaded material reference is not bound to original execution')
    known, bearing = observed['load_known'][:-1], observed['load_bearing'][:-1]
    for key, expected in (('load_known', known), ('load_bearing', bearing)):
        if key in sites and not np.array_equal(sites[key], expected):
            raise ValueError('Loaded material reference/load observations differ')
    phases = json.loads(Path(phases_path).read_text())
    source_steps = material_steps(motion, sites, len(known)+1)
    calibration = source_motion_allowances(source_steps, phases, load_known=known, load_bearing=bearing)
    if any(not row['measurement_complete'] for row in calibration):
        raise ValueError('Source phase has unknown material evidence')
    # A finite loaded-site value must agree with the independently observed load mask.
    if not np.array_equal(np.isfinite(source_steps), known & bearing):
        raise ValueError('Original loaded site coverage differs from support observations')
    return dict(sites=sites, phases=phases, source_steps=source_steps,
                load_known=known, load_bearing=bearing, calibration=calibration)


class SequentialLoadedMotion:
    """Original loaded-site RMS task for the production sequential IK.

    Each candidate interval uses the same material sites on its two poses.
    Positive excess accumulates over an authored phase without cancellations.
    This is soft editing guidance, never edited execution support evidence.
    """
    def __init__(self, reference, link_names, *, residual_scale_m=DEFAULT_MATERIAL_RESIDUAL_SCALE_M):
        self.reference = reference
        self.scale = float(residual_scale_m)
        if not np.isfinite(self.scale) or self.scale <= 0:
            raise ValueError('Positive material motion residual scale required')
        sites = reference['sites']
        count = len(reference['source_steps'])
        groups = sites['frame']*6+sites['part']
        width = max(1, int(np.bincount(groups, minlength=count*6).max()))
        shape = (count, 6, width)
        self.links = np.zeros(shape, np.int32)
        self.local = np.zeros((*shape, 3))
        self.normals = np.zeros_like(self.local)
        self.loads = np.zeros(shape)
        slot = np.zeros((count, 6), int)
        for i, (t, p) in enumerate(zip(sites['frame'], sites['part'])):
            j = slot[t, p]; slot[t, p] += 1
            self.links[t, p, j] = link_names.index(str(sites['body'][i]))
            self.local[t, p, j] = sites['local'][i]
            self.normals[t, p, j] = sites['normal'][i]
            self.loads[t, p, j] = sites['weight'][i]
        self.phase_index = np.full((count, 6), -1, int)
        for i, phase in enumerate(reference['phases']):
            a, b, p, face = (int(phase[k]) for k in ('start', 'end', 'part', 'surface'))
            if np.any(self.phase_index[a:b, p] >= 0):
                raise ValueError('Overlapping loaded material phases')
            selected = (sites['frame'] >= a) & (sites['frame'] < b) & (sites['part'] == p)
            if np.any(sites['surface'][selected] != face):
                raise ValueError('Source phase and loaded material surface differ')
            self.phase_index[a:b, p] = i
        self.spent = np.zeros(len(reference['phases']))
        self.path_spent = np.zeros(len(reference['phases']))
        self.edited_steps = np.full_like(reference['source_steps'], np.nan)

    def frame_args(self, frame, previous_positions, previous_rotations, root, root_rotation):
        width = self.links.shape[-1]
        if frame == 0:
            return (np.zeros((6, width), np.int32), np.zeros((6, width, 3)),
                    np.zeros((6, width, 3)), np.zeros((6, width, 3)),
                    np.zeros((6, width)), np.zeros(6), np.zeros((2,6)), np.zeros((2,6)))
        t = frame-1
        links, local = self.links[t], self.local[t]
        points = previous_positions[links]+np.einsum('...ij,...j->...i', previous_rotations[links], local)
        active = (self.phase_index[t] >= 0) & self.reference['load_known'][t] & self.reference['load_bearing'][t]
        remaining = np.zeros((2,6))
        for p in np.flatnonzero(active):
            i = self.phase_index[t, p]
            remaining[0,p] = self.reference['calibration'][i]['allowance_m']-self.spent[i]
            remaining[1,p] = DEFAULT_MATERIAL_PATH_BUDGET_M-self.path_spent[i]
        base_points = (points-root) @ root_rotation
        normals = self.normals[t] @ root_rotation
        source = np.nan_to_num(self.reference['source_steps'][t])
        scale = active.astype(float)/self.scale
        return links, local, base_points, normals, self.loads[t], source, remaining, np.stack((scale*DEFAULT_SOURCE_ADDED_MOTION_WEIGHT**.5, scale))

    def commit(self, frame, previous_positions, previous_rotations, positions, rotations):
        if frame == 0:
            return
        t = frame-1; links, local = self.links[t], self.local[t]
        delta = positions[links]-previous_positions[links]+np.einsum(
            '...ij,...j->...i', rotations[links]-previous_rotations[links], local)
        value = tangent_material_rms(delta, self.normals[t], self.loads[t], xp=np)
        present = self.loads[t].sum(-1) > 0
        self.edited_steps[t] = np.where(present, value, np.nan)
        for p in np.flatnonzero(present & (self.phase_index[t] >= 0)):
            i = self.phase_index[t, p]
            self.spent[i] += max(0., value[p]-self.reference['source_steps'][t, p])
            self.path_spent[i] += value[p]

    def report(self):
        return dict(schema=MATERIAL_MOTION_SCHEMA, objective='loaded_material_phase_budget_source_regularizer_v2',
            budget_m=DEFAULT_MATERIAL_PATH_BUDGET_M, source_added_motion_weight=DEFAULT_SOURCE_ADDED_MOTION_WEIGHT,
            reference_only=True, residual_scale_m=self.scale,
            phases=compare_paths(self.reference['source_steps'], self.edited_steps, self.reference['phases'],
                load_known=self.reference['load_known'], load_bearing=self.reference['load_bearing']),
            actual_edited_support='unknown_without_new_execution')
