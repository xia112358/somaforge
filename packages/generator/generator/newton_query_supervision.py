"""Loss-only scene identity and local-to-native frame, not predictor features."""
import json
from pathlib import Path
import numpy as np
import torch
from somaforge_core.g1_kinematics import _quaternion_matrix_wxyz
from somaforge_core.robot_assets import decode_robot_asset_json


def prepare_query_metadata(manifest, inputs, target, samples):
    manifest = Path(manifest)
    entries = json.loads(manifest.read_text())['motion_files']
    def resolve(value):
        path = Path(value)
        return path if path.is_absolute() else manifest.parent/path
    grouped = {}
    for i, sample in enumerate(samples):grouped.setdefault(sample.motion_id, []).append(i)
    device = inputs['current_q'].device
    origins = inputs['current_q'].new_empty((len(samples),3))
    bases = inputs['current_q'].new_empty((len(samples),3,3))
    fingerprints = torch.empty((len(samples),32),dtype=torch.uint8,device=device)
    max_error = 0.
    for motion, indices in grouped.items():
        entry = entries[motion]
        with np.load(resolve(entry['newton_contact_file']),allow_pickle=False) as z:
            semantics = json.loads(z['contact_semantics_json'].item())
            fp = semantics['scene']['model_fingerprint']
        with np.load(resolve(entry['motion_file']),allow_pickle=False) as z:
            decode_robot_asset_json(z['robot_asset_json'],context='Newton query training metadata')
            world = torch.as_tensor(z['joint_pos'],device=device,dtype=inputs['current_q'].dtype)
        if world.ndim != 2 or world.shape[1] != 36:
            raise ValueError('Native query metadata requires canonical qpos motion')
        ids = torch.tensor(indices,device=device)
        current = world[[samples[i].current_frame for i in indices]]
        end = world[[samples[i].target_frame for i in indices]]
        local = inputs['current_q'][ids]
        basis = _quaternion_matrix_wxyz(current[:,3:7]) @ _quaternion_matrix_wxyz(local[:,3:7]).transpose(-1,-2)
        origin = current[:,:3]-torch.einsum('bij,bj->bi',basis,local[:,:3])
        tq = target['q'][ids]
        # A scene transform cannot repair different joint data or a mismatched
        # cache. Check both endpoints, not just a constructed start alignment.
        error = max(float((current[:,7:]-local[:,7:]).abs().max()),
            float((end[:,7:]-tq[:,7:]).abs().max()),
            float((torch.einsum('bij,bj->bi',basis,tq[:,:3])+origin-end[:,:3]).abs().max()),
            float((basis@_quaternion_matrix_wxyz(tq[:,3:7])-_quaternion_matrix_wxyz(end[:,3:7])).abs().max()))
        if error > 1e-4:raise ValueError(f'Local/native q cache mismatch for {entry["motion_id"]}: {error}')
        if not torch.allclose(basis[:,2],basis.new_tensor([0.,0.,1.]).expand(len(ids),3),atol=1e-5,rtol=0):
            raise ValueError('Training frame is not ground-preserving yaw')
        origins[ids] = origin; bases[ids] = basis
        fingerprints[ids] = torch.tensor(list(bytes.fromhex(fp)),dtype=torch.uint8,device=device)
        max_error = max(max_error,error)
    target.update(newton_world_origin=origins,newton_world_basis=bases,newton_model_fingerprint=fingerprints)
    return dict(query_metadata='loss_only_native_fingerprint_and_frame_v1',native_frame_max_error=max_error)
