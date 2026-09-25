"""Extract six-part contact labels from recorded Newton solver decisions.

No distances recomputed, no force threshold, no inferred margin. Legacy raw
contact-only recordings are rejected because candidates are not active contacts.
"""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from somaforge_core.robot_assets import validate_g1_asset_metadata

PARTS=('left_foot','right_foot','left_hand','right_hand','left_knee','right_knee')


def identify(label):
    match=re.search(r'/env_(\d+)/Robot/',label)
    if not match:return None
    name=label.rsplit('/',1)[-1]
    for p,part in enumerate(PARTS):
        side,kind=part.split('_')
        if name.startswith(side+'_') and ((kind=='foot' and 'ankle' in name)
                or (kind=='hand' and 'sphere_hand' in name) or (kind=='knee' and 'knee' in name)):
            return int(match[1]),p
    return int(match[1]),None


def extract(arrays,metadata,env_id):
    from somaforge_core.newton_contacts import extract_recording_contacts
    result = extract_recording_contacts(arrays, metadata, env_id)
    return result['active'], result['unallocated']


def _legacy_extract_diagnostic(arrays,metadata,env_id):
    required=['count','active','constraint_allocated','body0','body1','worldid']
    missing=[f'solver_contact_{k}' for k in required if f'solver_contact_{k}' not in arrays]
    if missing:raise ValueError('Recording has no verified solver activation; raw candidates/force are not a substitute: '+','.join(missing))
    semantics=metadata.get('solver_contact_semantics',{})
    if semantics.get('schema')!='newton_mjwarp_constraint_snapshot_v1':raise ValueError('Unknown contact snapshot semantics')
    labels=metadata['newton_body_labels'];lookup=[identify(label) for label in labels]
    active=arrays['solver_contact_active'];allocated=arrays['solver_contact_constraint_allocated']
    result=np.zeros((len(active),6),bool);overflow=np.zeros_like(result)
    for f,count in enumerate(arrays['solver_contact_count']):
        if not 0 <= int(count) <= active.shape[1]:
            raise ValueError('Invalid solver contact count')
        for j in np.flatnonzero(active[f,:int(count)]):
            if arrays['solver_contact_worldid'][f,j]!=env_id:continue
            b=[int(arrays[f'solver_contact_body{s}'][f,j]) for s in (0,1)]
            if any(k < -1 or k >= len(lookup) for k in b):
                raise ValueError('Invalid solver body mapping; cannot assume terrain')
            pair=[lookup[k] if 0<=k<len(lookup) else None for k in b]
            # Exclude self collision and robot-to-robot contact. Only a robot
            # body against a non-robot counterpart defines terrain interaction.
            robot=[v for v in pair if v is not None]
            if len(robot)!=1 or robot[0][0]!=env_id or robot[0][1] is None:continue
            p=robot[0][1]
            if allocated[f,j]:result[f,p]=True
            else:overflow[f,p]=True
    return result,overflow


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--recording',type=Path,required=True);parser.add_argument('--env-id',type=int,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    with np.load(args.recording,allow_pickle=False) as z:
        metadata=json.loads(z['_metadata_json'].item());validate_g1_asset_metadata(metadata['robot_asset'],context=str(args.recording))
        if not 0<=args.env_id<int(metadata['num_envs']):raise ValueError('env-id out of range')
        contact,overflow=extract(z,metadata,args.env_id)
        timestep=z['motion_time_step'][:,args.env_id].copy()
        terminated=z['terminated'][:,args.env_id].copy();timeout=z['timeout'][:,args.env_id].copy()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(args.output,contact_part_mask=contact,part_order=np.array(PARTS),
        unallocated_active_contact=overflow,motion_time_step=timestep,terminated=terminated,timeout=timeout,
        recording_path=np.array(str(args.recording.resolve())),env_id=np.array(args.env_id),
        robot_asset_json=np.array(json.dumps(metadata['robot_asset'])),
        contact_semantics_json=np.array(json.dumps(metadata['solver_contact_semantics'])))
    print(json.dumps(dict(frames=len(contact),active_part_frames=int(contact.sum()),
        unallocated_active_part_frames=int(overflow.sum()),output=str(args.output))))


if __name__=='__main__':main()
