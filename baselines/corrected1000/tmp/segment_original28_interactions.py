"""Select Newton contact events; motion amplitude is diagnostic, not a veto."""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import numpy as np
from somaforge_core.robot_assets import decode_robot_asset_json, encode_robot_asset_json
from somaforge_core.contact_events import bridge_dropouts, event_contract, group_endpoint, MAX_DROPOUT_FRAMES

ROOT=Path(__file__).absolute().parents[1]
PARTS=('left_foot','right_foot','left_hand','right_hand','left_knee','right_knee')
LINKS=('left_ankle_roll_link','right_ankle_roll_link','left_sphere_hand_link','right_sphere_hand_link','left_knee_link','right_knee_link')


@dataclass(frozen=True)
class Config:
    release_seconds: float=.06
    landing_window_seconds: float=.12
    landing_occupancy: float=2/3
    cluster_seconds: float=.12
    minimum_normal_range_includemargin_ratio: float=.5


EVENT_SELECTION = dict(schema='newton_temporal_touchdown_v3', motion_amplitude_veto=True,
                       release_seconds=.06, landing_window_seconds=.12, landing_occupancy=2/3,
                       cluster_seconds=.12, motion_axis='actual_primary_surface_normal',
                       motion_scale='actual_endpoint_pair_includemargin',
                       minimum_normal_range_includemargin_ratio=.5,
                       subthreshold_policy='cluster_companion_only')


def events_for_part(contact,gap,penetration,position,fps,cfg,surface_sequence,
                    surface_normal,includemargin):
    actual_contact = np.asarray(contact, dtype=bool)
    surface_normal = np.asarray(surface_normal, dtype=float)
    includemargin = np.asarray(includemargin, dtype=float)
    if surface_normal.shape != (3,) or includemargin.shape != actual_contact.shape:
        raise ValueError('Invalid event geometry evidence')
    contact = bridge_dropouts(actual_contact, surface_sequence)
    release_n=max(1,round(fps*cfg.release_seconds));window=max(1,round(fps*cfg.landing_window_seconds))
    needed=int(np.ceil(window*cfg.landing_occupancy))
    events=[];rejected=[];away_count=0;armed=False;origin=0;last_contact=0
    for f in range(len(contact)):
        clearly_away=not contact[f]
        away_count=away_count+1 if clearly_away else 0
        if not armed and away_count>=release_n:
            armed=True;origin=last_contact;release=f-release_n+1
        if armed and actual_contact[f] and f+window<=len(contact) and contact[f:f+window].sum()>=needed:
            path=position[origin:f+1]
            excursion=float(np.linalg.norm(path-path[0],axis=-1).max())
            chord=path[-1]-path[0];u=np.linspace(0,1,len(path))[:,None]
            arc=float(np.linalg.norm(path-(path[0]+u*chord),axis=-1).max())
            normal_coordinate=path@surface_normal
            normal_range=float(np.ptp(normal_coordinate))
            endpoint_margin=float(np.nanmin(includemargin[[origin,f]]))
            if not np.isfinite(endpoint_margin) or endpoint_margin <= 0:
                raise ValueError('Missing actual Newton includemargin at event endpoint')
            required=cfg.minimum_normal_range_includemargin_ratio*endpoint_margin
            record=dict(frame=f,release_frame=release,previous_contact_frame=origin,
                excursion_m=excursion,arc_m=arc,normal_range_m=normal_range,
                endpoint_includemargin_m=endpoint_margin,required_normal_range_m=required,
                normal_range_includemargin_ratio=normal_range/endpoint_margin,
                landing_occupancy=float(contact[f:f+window].mean()))
            record['motion_qualified'] = bool(normal_range >= required)
            events.append(record)
            if not record['motion_qualified']:
                rejected.append(dict(**record,reason='insufficient_surface_normal_motion'))
            armed=False;away_count=0
        if contact[f] and not armed:last_contact=f
    return events,rejected


def cluster_events(events,contact,fps,cfg,surfaces=None):
    continuity = np.stack([bridge_dropouts(contact[:, p], None if surfaces is None else surfaces[:, p])
                           for p in range(contact.shape[1])], axis=1)
    groups=[]
    for event in sorted(events,key=lambda e:(e['frame'],e['part_index'])):
        event = dict(event)
        if groups:
            previous=groups[-1];parts=[e['part_index'] for e in previous]
            # Do not merge successive actions of one limb. At the shared end
            # all earlier touchdown parts must actually be in contact too.
            merged = False
            if (event['frame']-previous[0]['frame']<=round(cfg.cluster_seconds*fps)
                    and event['part_index'] not in parts):
                candidate = previous + [event]
                first = max(event['frame'], group_endpoint(previous))
                for end in range(first, min(len(contact), event['frame']+MAX_DROPOUT_FRAMES+1)):
                    realized = all(contact[end,e['part_index']] and
                        (surfaces is None or surfaces[end,e['part_index']]==e['surface']) for e in candidate)
                    continuous = all(continuity[e['frame']:end+1,e['part_index']].all() and
                        (surfaces is None or np.all(surfaces[e['frame']:end+1,e['part_index']][contact[e['frame']:end+1,e['part_index']]]==e['surface'])) for e in candidate)
                    if realized and continuous:
                        for e in candidate: e['cluster_endpoint_frame'] = end
                        previous.append(event);merged = True;break
            if merged: continue
        # Sub-margin threshold chatter may complete the topology of a nearby
        # real event, but must never create an event boundary by itself.
        if event.get('motion_qualified', True):
            groups.append([event])
    return groups


def solver_event_geometry(contact_path, frame_count):
    """Read normals/margins from the same Newton records that define labels."""
    with np.load(contact_path, allow_pickle=False) as archive:
        pairs = json.loads(archive['contact_pairs_json'].item())
        semantics = json.loads(archive['contact_semantics_json'].item())
    if len(pairs) != frame_count:
        raise ValueError('Contact-pair timeline length mismatch')
    normals = {int(row['surface']): np.asarray(row['normal_w'], dtype=float)
               for row in semantics['scene']['surface_catalog']}
    margins = {}
    for frame, frame_pairs in enumerate(pairs):
        for pair in frame_pairs:
            if not pair.get('constraint_active') or not pair.get('allocated'):
                continue
            key = (int(pair['part']), int(pair['surface']))
            values = margins.setdefault(key, np.full(frame_count, np.nan, dtype=float))
            margin = float(pair['includemargin'])
            values[frame] = margin if not np.isfinite(values[frame]) else min(values[frame], margin)
    return normals, margins


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'tmp/original28_newton_interaction_segments_v1')
    parser.add_argument('--mask-directory', type=Path, required=True)
    args=parser.parse_args();cfg=Config();args.output.mkdir(exist_ok=False)
    allrows=[];reports=[]
    for i in range(28):
        mid=f'climb_{i:02d}';maskpath=args.mask_directory/f'{mid}_z_scale_1.0.npz'
        with np.load(maskpath,allow_pickle=False) as z:
            decode_robot_asset_json(z['robot_asset_json'],context=str(maskpath))
            source=Path(z['source_path'].item());fps=float(z['fps'].reshape(-1)[0])
            from somaforge_core.newton_contact_data import load_contact_labels
            verified=load_contact_labels(source,maskpath)
            contact=verified['contact_part_mask'];surfaces=verified['contact_surface']
            gap=pen=np.zeros_like(contact,dtype=float)
            assert hashlib.sha256(source.read_bytes()).hexdigest()==z['source_sha256'].item()
        with np.load(source,allow_pickle=False) as z:
            decode_robot_asset_json(z['robot_asset_json'],context=str(source))
            names=z['body_names'].astype(str).tolist();pos=z['body_pos_w'][:,[names.index(n) for n in LINKS]].copy()
        normals,margins=solver_event_geometry(maskpath,len(contact))
        events=[];rejected=[]
        for p in range(6):
            for surface in np.unique(surfaces[contact[:,p],p]):
                active_pair=contact[:,p] & (surfaces[:,p]==surface)
                accepted,skipped=events_for_part(active_pair,gap[:,p],pen[:,p],pos[:,p],fps,cfg,
                    surfaces[:,p],normals[int(surface)],margins[(p,int(surface))])
                events.extend(dict(**e,part=PARTS[p],part_index=p,surface=int(surface)) for e in accepted)
                rejected.extend(dict(**e,part=PARTS[p],surface=int(surface)) for e in skipped)
        groups=cluster_events(events,contact,fps,cfg,surfaces)
        by_end={group_endpoint(group):group for group in groups}
        boundaries=sorted(set([0,len(contact)-1,*by_end]))
        rows=[]
        for j,(start,end) in enumerate(zip(boundaries[:-1],boundaries[1:])):
            group=by_end.get(end,[])
            rows.append(dict(motion_id=mid,segment_id=f'{mid}_interaction_{j:04d}',source_path=str(source),contact_source_path=str(maskpath),
                event_selection=EVENT_SELECTION,
                start_frame=start,end_frame=end,duration_frames=end-start,duration_s=(end-start)/fps,inclusive_end=True,
                source_support=[PARTS[p] for p in np.flatnonzero(contact[start])],
                target_support=[PARTS[p] for p in np.flatnonzero(contact[end])],
                source_surfaces=surfaces[start].tolist(),target_surfaces=surfaces[end].tolist(),
                touchdown_at_end=[e['part'] for e in group],touchdown_events=group,
                include_for_infiller=bool(group),short_segment=end-start<7,
                endpoint_penetration_cm=None,
                max_segment_penetration_cm=None))
        allrows.extend(rows)
        grouped_events=[event for group in groups for event in group]
        report=dict(motion=mid,contact_label_contract=verified['contact_label_contract'],event_contract=event_contract(fps),event_selection=EVENT_SELECTION,
            segments=len(rows),event_count=len(grouped_events),event_candidates=len(events),event_groups=len(groups),
            by_part={p:sum(e['part']==p for e in grouped_events) for p in PARTS},
            short_segments=sum(r['short_segment'] for r in rows),rejected=rejected,events=events,
            terminal_tail_frames=len(contact)-1-max(by_end,default=0))
        reports.append(report);print(mid,'segments',len(rows),'parts',report['by_part'],flush=True)
    (args.output/'atoms.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in allrows))
    (args.output/'summary.json').write_text(json.dumps(dict(schema='newton_motion_interactions_v1',config=asdict(cfg),parts=PARTS,event_selection=EVENT_SELECTION,
        input='Newton fixed-q contact masks and original body poses; raw masks unchanged',robot_asset_json=encode_robot_asset_json(),
        segments=len(allrows),motions=reports,training_ready=False,
        limitations='Geometric interaction events, not measured support; inspect missed landings, penetration and clustering before training'),indent=2))


if __name__=='__main__':main()
