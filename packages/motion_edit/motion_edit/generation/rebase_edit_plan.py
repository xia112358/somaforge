"""Rebind authored edits to a verified source without warping source poses."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np

from .free_surface_reference import reference_offsets


def event_clock(old_events, new_events, frame_count):
    old = {e['segment_id']: e for e in old_events}
    pairs = []
    for e in new_events:
        reference = old[e['segment_id']]
        for key in ('start_frame', 'end_frame'):
            pairs.append((int(e[key]), int(reference[key])))
    clocks = {}
    for new, previous in pairs:
        if new in clocks and clocks[new] != previous:
            raise ValueError('Ambiguous authored event clock')
        clocks[new] = previous
    x, y = map(np.asarray, zip(*sorted(clocks.items())))
    if x[0] != 0 or x[-1] != frame_count - 1 or np.any(np.diff(y) <= 0):
        raise ValueError('Event clock must cover the complete source monotonically')
    # Maps edit metadata only. The physical source remains on its native clock.
    return np.rint(np.interp(np.arange(frame_count), x, y)).astype(int)


def rebase_plan(plan, old_anchors, new_anchors, old_events, new_events, *,
                source, layer, labels, events, initial_q, surfaces=None):
    result = deepcopy(plan)
    if result['pose_edits'] or any(e.get('source') != 'task_variant_surface_follow' for e in result['edits']):
        raise ValueError('Rebinding requires explicit surface-follow authoring; unsupported edits cannot be dropped')
    clock = event_clock(old_events, new_events, max(e['end_frame'] for e in new_events)+1)
    new_to_old={}
    if surfaces is not None:
        for transform in result['surface_transforms']:
            face=transform['source_surface'];normal=np.asarray(face['normal'])
            matches=[s for s in surfaces if np.allclose(s['normal'],normal,atol=1.e-7,rtol=0)
                     and np.allclose(s['origin'],face['origin'],atol=1.e-7,rtol=0)]
            if len(matches)!=1:raise ValueError('Authored source surface has no unique native layer face')
            native=matches[0];new_to_old[native['surface_id']]=face['surface_id']
            face.update(surface_id=native['surface_id'],object_id=native['object_id'])
    old_offsets = plan['metadata']['free_surface_reference_offsets']
    tables = {}
    for anchor in old_anchors:
        key = (anchor['body'], anchor['surface_id'])
        values, known = tables.setdefault(key, (np.zeros((int(clock[-1])+1,3)),
                                               np.zeros(int(clock[-1])+1, bool)))
        frames = np.arange(anchor['start_frame'], anchor['end_frame'])
        offset = reference_offsets(frames, old_offsets[anchor['anchor_id']])
        if np.any(known[frames] & (np.abs(values[frames]-offset).max(-1)>1.e-8)):
            raise ValueError('Conflicting authored offsets for one contact region')
        values[frames], known[frames] = offset, True
    offsets = {}
    for anchor in new_anchors:
        frames = np.arange(anchor['start_frame'], anchor['end_frame'])
        key = (anchor['body'], new_to_old.get(anchor['surface_id'],anchor['surface_id']))
        if key not in tables:
            raise ValueError(f'New contact region lacks authored edit mapping: {key}')
        values, known = tables[key]
        available = np.flatnonzero(known)
        old_frames = clock[frames]
        if not len(available): raise ValueError('No authored offset samples')
        # Extend the authored reference over a newly observed shape fragment;
        # this does not extend actual contact or invent a support role.
        right = np.searchsorted(available, old_frames).clip(0,len(available)-1)
        left = (right-1).clip(0,len(available)-1)
        chosen = np.where(abs(available[left]-old_frames)<=abs(available[right]-old_frames),left,right)
        motion = values[available[chosen]]
        boundaries = np.r_[0,np.flatnonzero(np.any(np.diff(motion,axis=0)!=0,axis=1))+1,len(frames)]
        windows = [dict(frames=[int(frames[a]),int(frames[b-1])+1],delta=motion[a].tolist())
                   for a,b in zip(boundaries[:-1],boundaries[1:]) if np.any(motion[a])]
        offsets[anchor['anchor_id']] = dict(base=[0.,0.,0.],windows=windows)
    result.update(source_motion_path=str(Path(source).resolve()),source_contact_layer=str(Path(layer).resolve()),
                  source_segment_layer=None,edits=[])
    metadata = result['metadata']
    metadata.update(newton_contact_file=str(Path(labels).resolve()),event_phase_file=str(Path(events).resolve()),
        source_motion_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        free_surface_reference_offsets=offsets,regeneration_source='unchanged_native_execution',
        support_rotation_policy='authored_surface',
        authoring_clock_contract='event_mapped_edit_metadata_only_no_source_pose_resampling')
    for key in ('approach_frames', 'support_approach_seconds', 'support_approach_orientation'):
        metadata.pop(key, None)
    if 'root_yaw_condition' in metadata:
        metadata['root_yaw_condition']['initial_qpos']=np.asarray(initial_q).tolist()
    metadata['rebase_provenance']=dict(schema='native_source_edit_rebase_v1',
        old_source=plan['source_motion_path'],old_plan_id=plan['plan_id'],
        source_pose_warped=False,shape_fragment_count=len(new_anchors))
    return result


def crop_events(events, source_frames):
    from .stationary_compaction import remap_retained_interval
    retained=[]
    for event in events:
        interval=remap_retained_interval(event['start_frame'],event['end_frame'],source_frames)
        if interval is None: raise ValueError('An authored event crosses a removed interval')
        row=deepcopy(event)
        row['source_start_frame'],row['source_end_frame']=event['start_frame'],event['end_frame']
        row['start_frame'],row['end_frame']=interval
        # All event-owned timing must share the new clock, including touchdown.
        for collection in ('touchdown_events','release_events'):
            for item in row.get(collection,[]):
                for key in ('frame','start_frame','end_frame_exclusive','release_frame','previous_contact_frame'):
                    if key in item:
                        value=int(item[key]); index=int(np.searchsorted(source_frames,value))
                        item.setdefault('source_timing',{})[key]=value
                        if key!='end_frame_exclusive' and (index>=len(source_frames) or source_frames[index]!=value):
                            if key in ('release_frame','previous_contact_frame'):
                                item[key]=None
                                continue
                            raise ValueError('Contact event timing was removed by compaction')
                        item[key]=index
        row['cross_seam_supervision_allowed']=False
        retained.append(row)
    return retained
