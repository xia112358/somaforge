#!/usr/bin/env python3
"""Train a scan-conditioned deformation operator with immutable full endpoints."""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT / "tmp"))

from climb00_scan_observation import (  # noqa: E402
    SCAN_COLS, SCAN_ROWS, conform_contact_targets_to_scan, local_scan_grid, scans_from_local_box,
)
from climb00_privileged_geometry import (  # noqa: E402
    PrivilegedGeometryEncoder, conform_contact_targets_to_geometry, privileged_geometry_array,
)
from train_climb00_contact_conditioned_infiller import (  # noqa: E402
    BODY_NAMES, PART_BODY_INDEX, AdaLNBlock, build_dataset, contact_aware_sparse_clearance,
    dense_swept_samples, phase_resample, runtime_resample_batch,
)
from train_climb00_contact_event_predictor import PARTS, split_name  # noqa: E402
from train_climb00_scan_contact_selector import (  # noqa: E402
    ScanEncoder, transition_labels, transition_vocabulary,
)
from train_g1_touchdown_keyframe_infiller import quat_matrix_wxyz, rotation_6d, rotation_matrix_6d, yaw_matrix  # noqa: E402
from train_climb00_scan_full_boundary_selector import (  # noqa: E402
    PrivilegedFullBoundarySelector, ScanFullBoundarySelector, decode_boundary, enforce_contact_boundary,
)
from holosoma.utils.rotations import matrix_to_quaternion, quaternion_to_matrix, slerp  # noqa: E402


class ScanTrajectoryDeformer(nn.Module):
    """Deform an existing trajectory; the network has no endpoint authority."""

    def __init__(self, condition_dim: int, width: int = 192, layers: int = 4, heads: int = 6, ffn: int = 768, endpoint_envelope: str = "linear", rotation_residual_limit: float | None = None, rotation_alignment: str = "linear6d"):
        super().__init__()
        if endpoint_envelope not in ("linear","smooth"):
            raise ValueError(f"unknown endpoint envelope: {endpoint_envelope}")
        self.endpoint_envelope=endpoint_envelope
        self.rotation_residual_limit=rotation_residual_limit
        if rotation_alignment not in ("linear6d","so3"):
            raise ValueError(f"unknown rotation alignment: {rotation_alignment}")
        self.rotation_alignment=rotation_alignment
        self.condition = nn.Sequential(nn.Linear(condition_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.scan = ScanEncoder(width, SCAN_ROWS, SCAN_COLS)
        self.fuse = nn.Sequential(nn.Linear(2 * width, width), nn.SiLU(), nn.Linear(width, width))
        self.base = nn.Sequential(nn.Linear(63, width), nn.SiLU(), nn.Linear(width, width))
        self.phase = nn.Sequential(nn.Linear(9, width), nn.SiLU(), nn.Linear(width, width))
        self.blocks = nn.ModuleList([AdaLNBlock(width, heads, ffn) for _ in range(layers)])
        self.out = nn.Sequential(nn.LayerNorm(width), nn.Linear(width, width), nn.GELU(), nn.Linear(width, 63))

    @staticmethod
    def phase_features(phase: torch.Tensor) -> torch.Tensor:
        values = [phase]
        for frequency in (1.0, 2.0, 4.0, 8.0):
            values.extend((torch.sin(math.pi * frequency * phase), torch.cos(math.pi * frequency * phase)))
        return torch.stack(values, dim=-1)

    def align_base(
        self,
        base_position: torch.Tensor, base_rotation: torch.Tensor,
        start_position: torch.Tensor, start_rotation: torch.Tensor,
        end_position: torch.Tensor, end_rotation: torch.Tensor, phase: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        u = phase[..., None, None]
        position = base_position + (1.0 - u) * (start_position - base_position[:, 0])[:, None]
        position = position + u * (end_position - base_position[:, -1])[:, None]
        if self.rotation_alignment == "so3":
            base_matrix=rotation_matrix_6d(base_rotation)
            start_matrix=rotation_matrix_6d(start_rotation); end_matrix=rotation_matrix_6d(end_rotation)
            correction_start=start_matrix@base_matrix[:,0].transpose(-1,-2)
            correction_end=end_matrix@base_matrix[:,-1].transpose(-1,-2)
            q0=matrix_to_quaternion(correction_start)[:,None].expand(-1,base_rotation.shape[1],-1,-1)
            q1=matrix_to_quaternion(correction_end)[:,None].expand_as(q0)
            correction=quaternion_to_matrix(slerp(q0,q1,phase[...,None,None]))
            aligned_matrix=correction@base_matrix
            rotation=aligned_matrix[...,:,:2].reshape_as(base_rotation)
        else:
            rotation = base_rotation + (1.0 - u) * (start_rotation - base_rotation[:, 0])[:, None]
            rotation = rotation + u * (end_rotation - base_rotation[:, -1])[:, None]
        return position, rotation


    def forward(
        self, condition_input: torch.Tensor, height_scan: torch.Tensor, phase: torch.Tensor,
        base_position: torch.Tensor, base_rotation: torch.Tensor,
        start_position: torch.Tensor, start_rotation: torch.Tensor,
        end_position: torch.Tensor, end_rotation: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        aligned_p, aligned_r = self.align_base(
            base_position, base_rotation, start_position, start_rotation,
            end_position, end_rotation, phase,
        )
        base_token = torch.cat((aligned_p.reshape(*aligned_p.shape[:2], 21), aligned_r.reshape(*aligned_r.shape[:2], 42)), -1)
        condition = self.fuse(torch.cat((self.condition(condition_input), self.scan(height_scan)), -1))
        hidden = self.base(base_token) + self.phase(self.phase_features(phase)) + condition[:, None]
        for block in self.blocks:
            hidden = block(hidden, condition)
        residual = self.out(hidden)
        if self.endpoint_envelope == "smooth":
            envelope=(16.0*phase.square()*(1.0-phase).square())[...,None,None]
        else:
            envelope=(4.0*phase*(1.0-phase))[...,None,None]
        position = aligned_p + envelope * residual[..., :21].reshape_as(aligned_p)
        rotation_residual=residual[...,21:].reshape_as(aligned_r)
        if self.rotation_residual_limit is not None:
            rotation_residual=float(self.rotation_residual_limit)*torch.tanh(rotation_residual)
        rotation=aligned_r+envelope*rotation_residual
        return position, rotation


class PrivilegedTrajectoryDeformer(ScanTrajectoryDeformer):
    """Trajectory deformer conditioned on exact offline terrain geometry."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        width = self.condition[-1].out_features
        self.scan = PrivilegedGeometryEncoder(width)


def source_bases(manifest_path: Path, samples, phase_frames: int) -> tuple[np.ndarray, np.ndarray]:
    manifest = json.loads(manifest_path.read_text())
    positions = np.zeros((len(samples), phase_frames, len(BODY_NAMES), 3), np.float32)
    rotations = np.zeros((len(samples), phase_frames, len(BODY_NAMES), 6), np.float32)
    cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for row, sample in enumerate(samples):
        plan = json.loads(Path(manifest["motion_files"][sample.motion_id]["edit_plan_file"]).read_text())
        source = str(plan["source_motion_path"])
        if source not in cache:
            with np.load(source, allow_pickle=False) as loaded:
                names = loaded["body_names"].astype(str).tolist()
                indices = [names.index(name) for name in BODY_NAMES]
                cache[source] = (
                    np.asarray(loaded["body_pos_w"][:, indices], np.float32),
                    quat_matrix_wxyz(np.asarray(loaded["body_quat_w"][:, indices], np.float32)),
                )
        world_p, world_r = cache[source]
        segment_p = world_p[sample.current_frame : sample.target_frame + 1]
        segment_r = world_r[sample.current_frame : sample.target_frame + 1]
        origin = segment_p[0, 0]
        heading = math.atan2(float(segment_r[0, 0, 1, 0]), float(segment_r[0, 0, 0, 0]))
        inverse = yaw_matrix(-heading)
        positions[row] = phase_resample(np.einsum("ij,tbj->tbi", inverse, segment_p - origin), phase_frames)
        local_r = np.einsum("ij,tbjk->tbik", inverse, segment_r)
        rotations[row] = phase_resample(rotation_6d(local_r), phase_frames)
    return positions, rotations


def condition_array(data: dict[str, np.ndarray], indices: np.ndarray) -> np.ndarray:
    start = np.concatenate((data["positions"][indices, 0].reshape(len(indices), -1), data["rotations"][indices, 0].reshape(len(indices), -1)), -1)
    end = np.concatenate((data["positions"][indices, -1].reshape(len(indices), -1), data["rotations"][indices, -1].reshape(len(indices), -1)), -1)
    return np.concatenate((start, end, data["start_contacts"][indices], data["end_contact"][indices], data["touchdown"][indices], data["duration"][indices, None]), -1).astype(np.float32)


def action_medoid_bases(data, samples, base_position, base_rotation, train, *, return_indices=False):
    """Choose one real source trajectory per observed contact-transition action."""
    touchdown_masks, end_masks = transition_vocabulary(data["touchdown"][train], data["end_contact"][train])
    labels = transition_labels(data["touchdown"], data["end_contact"], touchdown_masks, end_masks)
    template_p=np.zeros((len(touchdown_masks),)+base_position.shape[1:],np.float32)
    template_r=np.zeros((len(touchdown_masks),)+base_rotation.shape[1:],np.float32)
    template_c=np.zeros((len(touchdown_masks),)+data["contacts"].shape[1:],np.float32)
    counts={}; medoid_indices=[]; phase=np.linspace(0,1,base_position.shape[1],dtype=np.float32)[None,:,None,None]
    for action in range(len(touchdown_masks)):
        members=train[labels[train]==action]
        flat=np.concatenate((base_position[members].reshape(len(members),-1),base_rotation[members].reshape(len(members),-1)),-1)
        _,unique=np.unique(np.round(flat,6),axis=0,return_index=True)
        candidates=members[np.sort(unique)]
        target_p,target_r=data["positions"][members],data["rotations"][members]
        best_score,best=math.inf,None
        for candidate in candidates:
            bp,br=base_position[candidate][None],base_rotation[candidate][None]
            aligned_p=bp+(1-phase)*(target_p[:,0]-bp[:,0])[:,None]+phase*(target_p[:,-1]-bp[:,-1])[:,None]
            aligned_r=br+(1-phase)*(target_r[:,0]-br[:,0])[:,None]+phase*(target_r[:,-1]-br[:,-1])[:,None]
            score=float(np.square((aligned_p-target_p)/.05).mean()+.5*np.square(aligned_r-target_r).mean())
            if score<best_score: best_score,best=score,int(candidate)
        template_p[action],template_r[action]=base_position[best],base_rotation[best]
        template_c[action]=data["contacts"][best]
        medoid_indices.append(best)
        counts[str(action)]=int(len(candidates))
    output=(template_p,template_r,template_c,labels,touchdown_masks,end_masks,counts)
    return output+(np.asarray(medoid_indices,dtype=np.int64),) if return_indices else output


@torch.no_grad()
def predicted_boundaries(selector_path: Path, data, scans: np.ndarray, device: torch.device):
    checkpoint=torch.load(selector_path,map_location="cpu",weights_only=False); config=checkpoint["config"]
    selector_class=PrivilegedFullBoundarySelector if checkpoint.get("schema","").startswith("climb00_privileged_") else ScanFullBoundarySelector
    model=selector_class(
        int(checkpoint["condition_dim"]),len(checkpoint["action_touchdown_masks"]),
        boundary_dim=len(checkpoint["boundary_mean"]),contact_offset_dim=(len(PARTS)*3 if "contact_offset_mean" in checkpoint else 0),width=int(config["width"]),blocks=int(config["blocks"]),
        action_embedding_dim=int(config["action_embedding_dim"]),
        transition_end_contact_masks=checkpoint["action_end_contact_masks"],
    ).to(device); model.load_state_dict(checkpoint["model"]); model.eval()
    pose=np.concatenate((data["positions"][:,0].reshape(len(scans),-1),data["rotations"][:,0].reshape(len(scans),-1)),-1)
    state=np.concatenate((data["start_contacts"],pose),-1).astype(np.float32)
    end_p=[]; end_r=[]; actions=[]; durations=[]
    for begin in range(0,len(scans),256):
        batch=slice(begin,min(begin+256,len(scans)))
        state_t=torch.from_numpy(state[batch]).to(device); scan_t=torch.from_numpy(scans[batch]).to(device)
        output=model((state_t-checkpoint["state_mean"].to(device))/checkpoint["state_std"].to(device),(scan_t-checkpoint["scan_mean"].to(device))/checkpoint["scan_std"].to(device))
        action=output[0].argmax(-1)
        p,r=decode_boundary(output[4],torch.from_numpy(data["positions"][batch,0]).to(device),torch.from_numpy(data["rotations"][batch,0]).to(device),checkpoint["boundary_mean"].to(device),checkpoint["boundary_std"].to(device))
        if "contact_offset_mean" in checkpoint:
            touchdown=checkpoint["action_touchdown_masks"].to(device)[action].float(); end_contact=checkpoint["action_end_contact_masks"].to(device)[action].float()
            raw_contact=output[2].cpu().numpy()*checkpoint["contact_std"].numpy()[None]+checkpoint["contact_mean"].numpy()[None]
            if checkpoint.get("schema","").startswith("climb00_privileged_"):
                contact=conform_contact_targets_to_geometry(
                    raw_contact,touchdown.cpu().numpy(),data["box_origin"][batch],data["box_basis"][batch],
                    data["box_edge_start"][batch],data["box_height"][batch],
                )
            else:
                contact=conform_contact_targets_to_scan(raw_contact,touchdown.cpu().numpy(),scans[batch])
            offsets=output[5].reshape(-1,len(PARTS),3)*checkpoint["contact_offset_std"].to(device)+checkpoint["contact_offset_mean"].to(device)
            p=enforce_contact_boundary(
                p,r,torch.from_numpy(data["positions"][batch,0]).to(device),
                torch.from_numpy(data["rotations"][batch,0]).to(device),
                torch.from_numpy(contact).to(device),touchdown,end_contact,offsets=offsets,
                persistent_offsets=checkpoint.get("contact_offsets", checkpoint["contact_offset_mean"]).to(device),
            )
        end_p.append(p.cpu().numpy()); end_r.append(r.cpu().numpy()); actions.append(action.cpu().numpy())
        durations.append(torch.exp(output[3]*float(checkpoint["duration_std"])+float(checkpoint["duration_mean"])).cpu().numpy())
    actions=np.concatenate(actions)
    return (np.concatenate(end_p),np.concatenate(end_r),actions,np.concatenate(durations),
            checkpoint["action_touchdown_masks"].numpy()[actions].astype(np.float32),
            checkpoint["action_end_contact_masks"].numpy()[actions].astype(np.float32))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "tmp/climb00_continuous_coverage/training_manifest_207.json")
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/climb00_scan_trajectory_deformer_v1")
    parser.add_argument("--phase-frames", type=int, default=64)
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--width", type=int, default=192)
    parser.add_argument("--layers", type=int, default=4)
    parser.add_argument("--heads", type=int, default=6)
    parser.add_argument("--ffn", type=int, default=768)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--collision-weight", type=float, default=8.0)
    parser.add_argument("--support-weight", type=float, default=0.2)
    parser.add_argument("--smooth-weight", type=float, default=0.05)
    parser.add_argument("--style-weight", type=float, default=0.02)
    parser.add_argument("--safety-margin-m", type=float, default=0.01)
    parser.add_argument("--endpoint-envelope", choices=("linear","smooth"), default="linear")
    parser.add_argument("--rotation-residual-limit", type=float, default=0.25)
    parser.add_argument("--rotation-alignment", choices=("linear6d","so3"), default="so3")
    parser.add_argument("--base-selection", choices=("paired","action_medoid"), default="action_medoid")
    parser.add_argument("--selector-checkpoint", type=Path)
    parser.add_argument("--terrain-conditioning", choices=("scan", "privileged"), default="scan")
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    device = torch.device(args.device)
    data, samples, summary = build_dataset(args.manifest, args.phase_frames)
    base_p, base_r = source_bases(args.manifest, samples, args.phase_frames)
    scans = scans_from_local_box(data["box_origin"], data["box_basis"], data["box_edge_start"], data["box_edge_inward"], data["box_height"])
    if args.terrain_conditioning == "privileged":
        scans = privileged_geometry_array(data)
    train = np.asarray([i for i, s in enumerate(samples) if split_name(s.height) == "train_height_095_100_105"], np.int64)
    validation = np.asarray([i for i, s in enumerate(samples) if split_name(s.height) == "validation_height_090"], np.int64)
    action_base_p=action_base_r=action_base_c=action_touchdown_masks=action_end_masks=None; action_base_counts=None
    if args.base_selection == "action_medoid":
        action_base_p,action_base_r,action_base_c,labels,action_touchdown_masks,action_end_masks,action_base_counts = action_medoid_bases(
            data,samples,base_p,base_r,train,
        )
        base_p,base_r=action_base_p[labels],action_base_r[labels]
    training_p=data["positions"].copy(); training_r=data["rotations"].copy()
    condition = condition_array(data, np.arange(len(samples)))
    selector_boundary_contract=None
    if args.selector_checkpoint:
        predicted_p,predicted_r,predicted_action,predicted_duration,predicted_touchdown,predicted_end_contact=predicted_boundaries(
            args.selector_checkpoint,data,scans,device,
        )
        phase_np=np.linspace(0,1,args.phase_frames,dtype=np.float32)[None,:,None,None]
        training_p=training_p+phase_np*(predicted_p-data["positions"][:,-1])[:,None]
        training_r=training_r+phase_np*(predicted_r-data["rotations"][:,-1])[:,None]
        if args.base_selection=="action_medoid": base_p,base_r=action_base_p[predicted_action],action_base_r[predicted_action]
        start=np.concatenate((data["positions"][:,0].reshape(len(samples),-1),data["rotations"][:,0].reshape(len(samples),-1)),-1)
        end=np.concatenate((predicted_p.reshape(len(samples),-1),predicted_r.reshape(len(samples),-1)),-1)
        condition=np.concatenate((start,end,data["start_contacts"],predicted_end_contact,predicted_touchdown,predicted_duration[:,None]),-1).astype(np.float32)
        selector_boundary_contract={"checkpoint":str(args.selector_checkpoint.resolve()),"action_disagreement_fraction":float((predicted_action!=labels).mean())}
    cm, cs = condition[train].mean(0).astype(np.float32), np.maximum(condition[train].std(0), 1e-5).astype(np.float32)
    sm, ss = scans[train].mean(0).astype(np.float32), np.maximum(scans[train].std(0), 1e-3).astype(np.float32)
    dataset_arrays=((condition-cm)/cs,(scans-sm)/ss,base_p,base_r,training_p,training_r,data["contacts"],data["runtime_lengths"],data["target_surfaces"],data["box_origin"],data["box_basis"],data["box_edge_start"],data["box_edge_inward"],data["box_height"])
    def make_dataset(indices: np.ndarray) -> TensorDataset:
        return TensorDataset(*[torch.from_numpy(x[indices]) for x in dataset_arrays])
    dataset=make_dataset(train); validation_dataset=make_dataset(validation)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=True); iterator = iter(loader)
    validation_loader=DataLoader(validation_dataset,batch_size=128,shuffle=False,drop_last=False)
    model_class = PrivilegedTrajectoryDeformer if args.terrain_conditioning == "privileged" else ScanTrajectoryDeformer
    model = model_class(condition.shape[1], args.width, args.layers, args.heads, args.ffn,args.endpoint_envelope,args.rotation_residual_limit,args.rotation_alignment).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    phase = torch.linspace(0, 1, args.phase_frames, device=device)[None]
    def feasibility_terms(p, r, contacts, lengths, surfaces, bo, bb, es, ei, bh):
        runtime_p=runtime_resample_batch(p,lengths); runtime_c=runtime_resample_batch(contacts,lengths)
        dense_p=dense_swept_samples(runtime_p); dense_c=dense_swept_samples(runtime_c)
        clearance=contact_aware_sparse_clearance(dense_p,dense_c,surfaces,bo,bb,es,ei,bh)
        safety_mask=torch.ones_like(clearance)
        for part,body in enumerate(PART_BODY_INDEX):
            safety_mask[:,:,body]=1.0-dense_c[:,:,part].clamp(0.0,1.0)
        margin_violation=clearance+args.safety_margin_m*safety_mask
        positive=F.relu(margin_violation)/.02
        collision=positive.square().mean()+positive.amax((1,2)).square().mean()
        position_acceleration=(p[:,2:]-2*p[:,1:-1]+p[:,:-2])/.025
        rotation_acceleration=(r[:,2:]-2*r[:,1:-1]+r[:,:-2])/.10
        runtime_r=runtime_resample_batch(r,lengths); matrix=rotation_matrix_6d(runtime_r)
        relative=matrix[:,:-1].transpose(-1,-2)@matrix[:,1:]
        cosine=((relative.diagonal(dim1=-2,dim2=-1).sum(-1)-1.0)*.5).clamp(-1.0,1.0)
        cosine_limit=math.cos(math.radians(15.0))
        rotation_continuity=(F.relu(cosine_limit-cosine)/(1.0-cosine_limit)).square().mean()
        rotation_step=torch.acos(cosine.detach().clamp(-1.0+1e-7,1.0-1e-7))
        smooth=position_acceleration.square().mean()+.25*rotation_acceleration.square().mean()+rotation_continuity
        return collision,smooth,clearance,margin_violation,rotation_step

    def guidance_terms(p, r, target_p, target_r, contacts):
        support_sum=torch.zeros((),dtype=p.dtype,device=p.device); support_count=torch.zeros((),dtype=p.dtype,device=p.device)
        for part,body in enumerate(PART_BODY_INDEX):
            mask=contacts[:,:,part,None]
            support_sum=support_sum+(((p[:,:,body]-target_p[:,:,body])/.02).square()*mask).sum()
            support_count=support_count+mask.sum()*3.0
        support=support_sum/support_count.clamp_min(1.0)
        velocity=((p[:,1:]-p[:,:-1])-(target_p[:,1:]-target_p[:,:-1]))/.05
        curvature=((p[:,2:]-2*p[:,1:-1]+p[:,:-2])-
                   (target_p[:,2:]-2*target_p[:,1:-1]+target_p[:,:-2]))/.025
        rotation_velocity=((r[:,1:]-r[:,:-1])-(target_r[:,1:]-target_r[:,:-1]))/.10
        style=velocity.square().mean()+.25*curvature.square().mean()+.25*rotation_velocity.square().mean()
        return support,style

    @torch.no_grad()
    def evaluate_feasibility():
        model.eval(); actual_free=[]; margin_free=[]; penetration=[]; smooth_values=[]; support_values=[]; style_values=[]; rotation_max=0.0
        for batch in validation_loader:
            c,scan,bp,br,target_p,target_r,contacts,lengths,surfaces,bo,bb,es,ei,bh=[x.to(device) for x in batch]
            ph=phase.expand(len(c),-1)
            p,r=model(c,scan,ph,bp,br,target_p[:,0],target_r[:,0],target_p[:,-1],target_r[:,-1])
            _,smooth,clearance,margin_violation,rotation_step=feasibility_terms(p,r,contacts,lengths,surfaces,bo,bb,es,ei,bh)
            support,style=guidance_terms(p,r,target_p,target_r,contacts)
            actual=F.relu(clearance); margin=F.relu(margin_violation)
            actual_free.append((actual<=0).all((1,2)).cpu().numpy())
            margin_free.append((margin<=0).all((1,2)).cpu().numpy())
            penetration.append(actual.amax((1,2)).cpu().numpy()*100.0)
            smooth_values.append(float(smooth)); support_values.append(float(support)); style_values.append(float(style))
            rotation_max=max(rotation_max,float(torch.rad2deg(rotation_step).max()))
        penetration=np.concatenate(penetration)
        return {"collision_free_fraction":float(np.concatenate(actual_free).mean()),
                "margin_collision_free_fraction":float(np.concatenate(margin_free).mean()),
                "penetration_cm_mean":float(penetration.mean()),"penetration_cm_max":float(penetration.max()),
                "smooth":float(np.mean(smooth_values)),"support":float(np.mean(support_values)),
                "style":float(np.mean(style_values)),"maximum_rotation_step_deg":rotation_max}

    best,best_key,history=None,None,[]
    for step in range(1, args.steps + 1):
        try: batch = next(iterator)
        except StopIteration: iterator = iter(loader); batch = next(iterator)
        c, scan, bp, br, target_p, target_r, contacts, lengths, surfaces, bo, bb, es, ei, bh = [x.to(device) for x in batch]
        ph = phase.expand(len(c), -1)
        p, r = model(c, scan, ph, bp, br, target_p[:, 0], target_r[:, 0], target_p[:, -1], target_r[:, -1])
        collision,smooth,_,_,_=feasibility_terms(p,r,contacts,lengths,surfaces,bo,bb,es,ei,bh)
        support,style=guidance_terms(p,r,target_p,target_r,contacts)
        loss=(args.collision_weight*collision+args.support_weight*support+
              args.smooth_weight*smooth+args.style_weight*style)
        optimizer.zero_grad(set_to_none=True); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 2.0); optimizer.step()
        if step == 1 or step % 500 == 0 or step == args.steps:
            endpoint = max(float((p[:,0]-target_p[:,0]).abs().max()), float((p[:,-1]-target_p[:,-1]).abs().max()), float((r[:,0]-target_r[:,0]).abs().max()), float((r[:,-1]-target_r[:,-1]).abs().max()))
            validation_metric=evaluate_feasibility(); model.train()
            record = {"step": step, "loss": float(loss.detach()), "collision": float(collision.detach()),
                      "support":float(support.detach()),"smooth":float(smooth.detach()),"style":float(style.detach()),"validation":validation_metric,
                      "maximum_endpoint_absolute_error": endpoint}
            history.append(record); print(json.dumps(record))
            key=(validation_metric["collision_free_fraction"],validation_metric["margin_collision_free_fraction"],
                 -validation_metric["penetration_cm_mean"],
                 -(args.support_weight*validation_metric["support"]+args.smooth_weight*validation_metric["smooth"]+
                   args.style_weight*validation_metric["style"]))
            if best_key is None or key>best_key: best_key=key; best=copy.deepcopy(model.state_dict())
    assert best is not None
    checkpoint = {"schema":("climb00_privileged_trajectory_deformer_v1" if args.terrain_conditioning == "privileged" else "climb00_scan_trajectory_deformer_v1"),"model":best,"condition_dim":condition.shape[1],"condition_mean":torch.from_numpy(cm),"condition_std":torch.from_numpy(cs),"scan_mean":torch.from_numpy(sm),"scan_std":torch.from_numpy(ss),"scan_grid":torch.from_numpy(local_scan_grid()),"scan_shape":(SCAN_ROWS,SCAN_COLS),"phase_frames":args.phase_frames,"body_names":BODY_NAMES,"config":vars(args),"action_base_position":None if action_base_p is None else torch.from_numpy(action_base_p),"action_base_rotation":None if action_base_r is None else torch.from_numpy(action_base_r),"action_base_contact":None if action_base_c is None else torch.from_numpy(action_base_c),"action_touchdown_masks":None if action_touchdown_masks is None else torch.from_numpy(action_touchdown_masks),"action_end_contact_masks":None if action_end_masks is None else torch.from_numpy(action_end_masks)}
    torch.save(checkpoint, args.output/"model.pt")
    (args.output/"report.json").write_text(json.dumps({"schema":("climb00_privileged_trajectory_deformer_report_v1" if args.terrain_conditioning == "privileged" else "climb00_scan_trajectory_deformer_report_v1"),"event_dataset":summary,"train_samples":len(train),"validation_samples":len(validation),"base_selection":args.base_selection,"terrain_conditioning":args.terrain_conditioning,"selector_boundary_contract":selector_boundary_contract,"unique_training_base_candidates_per_action":action_base_counts,"objective":"hard endpoints + safety-margin collision + contact support + smoothness + weak differential trajectory style; no absolute full-trajectory reconstruction target","best_key":best_key,"history":history}, indent=2))


if __name__ == "__main__": main()
