"""Root-yaw height-map predictor with explicit part-to-space attention."""
from __future__ import annotations

import math
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

from .next_interaction import NextInteraction
from .next_interaction_heightmap import (
    HEIGHTMAP_CLIP_M, HEIGHTMAP_COLS, HEIGHTMAP_RESOLUTION_M, HEIGHTMAP_ROWS,
    HeightmapEncoder, heightmap_grid,
)
from .neural_infiller import (
    CanonicalG1CollisionPoints, CanonicalG1ForwardKinematics, _matrix_from_rotation6d,
    _quaternion_matrix_wxyz, _quaternion_multiply_wxyz, _rotation6d,
)


def _numpy_root_yaw_basis(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, np.float32)
    w, x, y, z = np.moveaxis(q[:, 3:7], -1, 0)
    norm = np.sqrt(w*w+x*x+y*y+z*z)
    w, x, y, z = (value/norm for value in (w, x, y, z))
    cosine, sine = 1-2*(y*y+z*z), 2*(w*z+x*y)
    planar=np.sqrt(cosine*cosine+sine*sine);cosine,sine=cosine/planar,sine/planar
    basis = np.zeros((len(q), 3, 3), np.float32)
    basis[:,0,0],basis[:,1,0]=cosine,sine
    basis[:,0,1],basis[:,1,1]=-sine,cosine
    basis[:,2,2]=1
    return basis


def render_root_yaw_box_heightmaps(center, rotation, half_extents, ground_height, current_q,
                                   *, supersample: int = 1):
    """Render root-yaw height, optionally area-filtering each output cell."""
    center,rotation,half_extents,current_q=[np.asarray(x,np.float32) for x in
                                           (center,rotation,half_extents,current_q)]
    ground_height=np.asarray(ground_height,np.float32).reshape(-1);batch=len(center)
    if current_q.shape!=(batch,36):raise ValueError('current_q must be [B,36]')
    if center.shape!=(batch,3) or rotation.shape!=(batch,3,3):raise ValueError('invalid box pose')
    if supersample < 1:raise ValueError('supersample must be positive')
    grid=heightmap_grid().reshape(-1,2);basis=_numpy_root_yaw_basis(current_q)
    offsets=(np.arange(supersample,dtype=np.float32)+.5)/supersample-.5
    offsets=np.stack(np.meshgrid(offsets,offsets,indexing='ij'),-1).reshape(-1,2)*HEIGHTMAP_RESOLUTION_M
    top=center[:,2]+rotation[:,2,2]*half_extents[:,2];samples=[]
    for offset in offsets:
        local=np.zeros((batch,len(grid),3),np.float32);local[:,:,:2]=grid[None]+offset
        world=np.einsum('nij,npj->npi',basis,local)+current_q[:,None,:3]
        box_local=np.einsum('npi,nij->npj',world-center[:,None],rotation)
        inside=(np.abs(box_local[...,:2])<=half_extents[:,None,:2]+1e-6).all(-1)
        samples.append(np.where(inside,top[:,None],ground_height[:,None])-current_q[:,2:3])
    height=np.mean(samples,axis=0)
    return np.clip(height,-HEIGHTMAP_CLIP_M,HEIGHTMAP_CLIP_M).reshape(
        batch,HEIGHTMAP_ROWS,HEIGHTMAP_COLS).astype(np.float32)


def heightmap_supersample_for_architecture(architecture: str) -> int:
    """Return the recorded scan contract for each height-map architecture.

    Bound V4/V5 models bind contacts to actual grid samples, so averaging
    multiple terrain heights into one cell is forbidden for them.
    """
    return 2 if architecture == "heightmap_v3_robust" else 1


_DEVICE_HEIGHTMAP_GRIDS = {}


def render_root_yaw_box_heightmaps_device(center, rotation, half_extents, ground_height, current_q,
                                         *, supersample=1):
    """Same observation raster on device; this does not classify contact."""
    if current_q.ndim != 2 or current_q.shape[1] != 36 or supersample < 1:
        raise ValueError('Expected canonical qpos and positive supersampling')
    key = (current_q.device, current_q.dtype)
    if key not in _DEVICE_HEIGHTMAP_GRIDS:
        # Upload the identical static numpy linspace grid once, so replacing
        # observation arithmetic cannot change the raster cell definition.
        _DEVICE_HEIGHTMAP_GRIDS[key] = torch.as_tensor(heightmap_grid().reshape(-1, 2),
            device=current_q.device, dtype=current_q.dtype)
    grid = _DEVICE_HEIGHTMAP_GRIDS[key]
    basis, _ = _root_yaw_basis(current_q)
    offsets = (torch.arange(supersample, device=current_q.device, dtype=current_q.dtype)+.5)/supersample-.5
    offsets = torch.stack(torch.meshgrid(offsets, offsets, indexing='ij'), -1).reshape(-1, 2)*HEIGHTMAP_RESOLUTION_M
    top = center[:, 2]+rotation[:, 2, 2]*half_extents[:, 2]
    samples = []
    for offset in offsets.unbind():
        local = torch.cat((grid+offset, torch.zeros_like(grid[:, :1])), -1)
        world = torch.einsum('bij,pj->bpi', basis, local)+current_q[:, None, :3]
        box_local = torch.einsum('bpi,bij->bpj', world-center[:, None], rotation)
        inside = (box_local[..., :2].abs() <= half_extents[:, None, :2]+1e-6).all(-1)
        samples.append(torch.where(inside, top[:, None], ground_height[:, None])-current_q[:, 2:3])
    return torch.stack(samples).mean(0).clamp(-HEIGHTMAP_CLIP_M, HEIGHTMAP_CLIP_M).reshape(
        len(current_q), HEIGHTMAP_ROWS, HEIGHTMAP_COLS)


def _root_yaw_basis(q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    qn=F.normalize(q[:,3:7],dim=-1);w,x,y,z=qn.unbind(-1)
    cosine,sine=1-2*(y*y+z*z),2*(w*z+x*y)
    planar=torch.sqrt(cosine.square()+sine.square()).clamp_min(1e-8);cosine,sine=cosine/planar,sine/planar
    zero=torch.zeros_like(cosine);one=torch.ones_like(cosine)
    basis=torch.stack((cosine,-sine,zero,sine,cosine,zero,zero,zero,one),-1).reshape(-1,3,3)
    yaw=torch.atan2(sine,cosine)
    yaw_quaternion=torch.stack((torch.cos(yaw/2),zero,zero,torch.sin(yaw/2)),-1)
    return basis,yaw_quaternion


class RootYawHeightmapInteractionPredictor(nn.Module):
    """One-pass joint contact/pose predictor using observed spatial queries."""
    def __init__(self,width: int=192,layers: int=3):
        super().__init__();self.fk=CanonicalG1ForwardKinematics();self.geometry=CanonicalG1CollisionPoints(64)
        self.height=HeightmapEncoder(width);self.global_encoder=nn.Linear(38,width);self.part_encoder=nn.Linear(13,width)
        self.part_identity=nn.Embedding(6,width);self.surface_embedding=nn.Embedding(3,width)
        self.part_to_terrain=nn.MultiheadAttention(width,6,batch_first=True)
        layer=nn.TransformerEncoderLayer(width,6,2*width,dropout=0.,activation='gelu',batch_first=True,norm_first=True)
        self.shared=nn.TransformerEncoder(layer,layers,enable_nested_tensor=False);self.norm=nn.LayerNorm(width)
        self.role_head=nn.Linear(width,4);self.surface_head=nn.Linear(width,2)
        self.role_embedding=nn.Linear(4,width,bias=False);self.predicted_surface_embedding=nn.Linear(2,width,bias=False)
        interaction=nn.TransformerEncoderLayer(width,6,2*width,dropout=0.,activation='gelu',batch_first=True,norm_first=True)
        self.interaction_decoder=nn.TransformerEncoder(interaction,1,enable_nested_tensor=False)
        self.pose_head=nn.Linear(width,36);self.duration_head=nn.Linear(width,1)
        nn.init.normal_(self.pose_head.weight,std=.001);nn.init.zeros_(self.pose_head.bias)
        with torch.no_grad():self.pose_head.bias[3]=1.

    @staticmethod
    def _to_local(points,q,basis):
        return torch.einsum('bij,bpj->bpi',basis.transpose(1,2),points-q[:,None,:3])

    @staticmethod
    def _local_state(q,basis):
        local_rotation=basis.transpose(1,2)@_quaternion_matrix_wxyz(q[:,3:7])
        return torch.cat((torch.zeros_like(q[:,:3]),_rotation6d(local_rotation),q[:,7:]/math.pi),-1)

    @staticmethod
    def _decode_pose(raw,current_q,basis,yaw_quaternion):
        world_delta=torch.einsum('bij,bj->bi',basis,raw[:,:3])
        world_quaternion=_quaternion_multiply_wxyz(yaw_quaternion,F.normalize(raw[:,3:7],dim=-1))
        return torch.cat((current_q[:,:3]+world_delta,world_quaternion,raw[:,7:]),-1)

    def encode_pose(self,target_q,current_q):
        basis,yaw_quaternion=_root_yaw_basis(current_q)
        local_delta=torch.einsum('bij,bj->bi',basis.transpose(1,2),target_q[:,:3]-current_q[:,:3])
        inverse_yaw=yaw_quaternion.clone();inverse_yaw[:,1:]*=-1
        local_quaternion=_quaternion_multiply_wxyz(inverse_yaw,target_q[:,3:7])
        return torch.cat((local_delta,local_quaternion,target_q[:,7:]),-1)

    def decode_pose(self,raw,current_q):
        basis,yaw_quaternion=_root_yaw_basis(current_q)
        return self._decode_pose(raw,current_q,basis,yaw_quaternion)

    def forward(self,current_q,current_contact,current_anchor,current_surface,heightmap):
        terrain,_=self.height(heightmap);basis,yaw_quaternion=_root_yaw_basis(current_q)
        positions,rotations6d=self.fk(current_q[:,None]);positions=positions[:,0,1:7]
        rotations=_matrix_from_rotation6d(rotations6d[:,0,1:7])
        local_position=self._to_local(positions,current_q,basis)
        local_rotation=basis[:,None].transpose(-1,-2)@rotations
        local_anchor=self._to_local(current_anchor,current_q,basis)
        surface_index=torch.where(current_contact,current_surface.clamp(0,1),2)
        part=self.part_encoder(torch.cat((local_position,_rotation6d(local_rotation),
            local_anchor*current_contact[...,None],current_contact[...,None].float()),-1))
        part=part+self.part_identity.weight[None]+self.surface_embedding(surface_index)
        spatial,_=self.part_to_terrain(part,terrain,terrain,need_weights=False);part=self.norm(part+spatial)
        state=self.global_encoder(self._local_state(current_q,basis))[:,None]
        tokens=self.shared(torch.cat((state,part),1));body=self.norm(tokens[:,0]+tokens[:,1:].mean(1));part=self.norm(tokens[:,1:])
        role_logits,surface_logits=self.role_head(part),self.surface_head(part)
        contact=part+self.role_embedding(role_logits.softmax(-1).detach())
        contact=contact+self.predicted_surface_embedding(surface_logits.softmax(-1).detach())
        interaction=self.interaction_decoder(torch.cat((body[:,None],contact),1))
        shared=self.norm(interaction[:,0]+interaction[:,1:].mean(1))
        q=self._decode_pose(self.pose_head(shared),current_q,basis,yaw_quaternion)
        return NextInteraction(q,role_logits,surface_logits,F.softplus(self.duration_head(shared)[:,0]))


def objective(model,prediction,target,scene,**kwargs):
    from .next_interaction_surface import objective as newton_objective
    return newton_objective(model,prediction,target,scene,**kwargs)
