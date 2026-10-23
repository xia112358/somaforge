"""Float32 Newton FK and analytic derivatives for the independent Torch IK pilot.

Newton evaluates every link pose. Derivatives use the same model's joint frames,
axes and ancestry; no second URDF FK or alternate robot asset is introduced.
"""
from __future__ import annotations

from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import numpy as np
import torch

from somaforge_core import G1_29DOF_JOINT_ORDER
from somaforge_core.robot_assets import canonical_g1_urdf_path


def quat_multiply(a, b):
    a, b = torch.broadcast_tensors(a, b)
    return torch.cat((a[..., :1]*b[..., :1]-(a[..., 1:]*b[..., 1:]).sum(-1, keepdim=True),
        a[..., :1]*b[..., 1:]+b[..., :1]*a[..., 1:]
        +torch.linalg.cross(a[..., 1:], b[..., 1:])), -1)


def quat_apply(q, v):
    xyz, v = torch.broadcast_tensors(q[..., 1:], v)
    cross = torch.linalg.cross(xyz, v)
    return v+2*(q[..., :1]*cross+torch.linalg.cross(xyz, cross))


class _NewtonFK(torch.autograd.Function):
    @staticmethod
    def forward(ctx, cfg, robot):
        poses, derivative = robot.evaluate(cfg, derivatives=True)
        ctx.save_for_backward(derivative)
        return poses

    @staticmethod
    def backward(ctx, gradient):
        (derivative,) = ctx.saved_tensors
        return (gradient[..., None]*derivative).sum((-3, -2)), None


class NewtonRobot:
    """Canonical G1 model with a base-local, WXYZ/XYZ FK interface.

    FK buffers stay on the selected Torch/Warp device. Collision/SQP queries
    consume explicit host copies and never move through a JAX runtime.
    """

    def __init__(self, robot_path=None, *, device='cpu'):
        import newton
        import warp as wp

        path = canonical_g1_urdf_path().resolve()
        if robot_path is not None and Path(robot_path).resolve() != path:
            raise ValueError('Torch/Newton IK requires the canonical G1 asset')
        self.wp = wp
        self.device = torch.device(device)
        with wp.ScopedDevice(str(self.device)):
            builder = newton.ModelBuilder(up_axis=newton.Axis.Z)
            builder.add_urdf(str(path), floating=True, hide_visuals=True,
                collapse_fixed_joints=False, joint_ordering=None, bodies_follow_joint_ordering=False)
            self.model = builder.finalize(device=str(self.device))
        model = self.model
        if model.articulation_count != 1:
            raise ValueError('Expected one canonical G1 articulation')
        labels = tuple(str(x).rsplit('/', 1)[-1] for x in model.body_label)
        # Stable URDF order also keeps diagnostic arrays comparable to PyRoki.
        names = tuple(node.attrib['name'] for node in ET.parse(path).getroot().findall('link'))
        if len(set(labels)) != len(labels) or set(names) != set(labels):
            raise ValueError('Canonical Newton/URDF link mapping is incomplete')
        self.links = SimpleNamespace(names=names)
        self.body_indices = torch.tensor([labels.index(name) for name in names])
        joint_labels = tuple(str(x).rsplit('/', 1)[-1] for x in model.joint_label)
        actuated = tuple(G1_29DOF_JOINT_ORDER)
        joint_indices = [joint_labels.index(name) for name in actuated]
        q_start = model.joint_q_start.numpy()
        qd_start = model.joint_qd_start.numpy()
        self.q_indices = torch.tensor([q_start[i] for i in joint_indices], dtype=torch.long)
        self.dof_indices = np.asarray([qd_start[i] for i in joint_indices], dtype=np.int64)
        if model.joint_coord_count != 36 or model.joint_dof_count != 35:
            raise ValueError('Unexpected canonical floating-base coordinate layout')
        kinds = model.joint_type.numpy()
        if any(int(kinds[i]) != int(newton.JointType.REVOLUTE) for i in joint_indices):
            raise ValueError('Analytic pilot derivatives require canonical revolute joints')
        self.joints = SimpleNamespace(actuated_names=actuated, num_actuated_joints=len(actuated),
            lower_limits=model.joint_limit_lower.numpy()[self.dof_indices],
            upper_limits=model.joint_limit_upper.numpy()[self.dof_indices])
        parent = model.joint_parent.numpy()
        child = model.joint_child.numpy()
        body_joint = {int(body): i for i, body in enumerate(child) if body >= 0}
        ancestors = np.zeros((len(names), len(actuated)), dtype=bool)
        column = {joint: i for i, joint in enumerate(joint_indices)}
        for link, body in enumerate(self.body_indices.tolist()):
            while body >= 0:
                joint = body_joint[body]
                if joint in column:
                    ancestors[link, column[joint]] = True
                body = int(parent[joint])
        self.ancestors = torch.from_numpy(ancestors)
        self.parents = torch.tensor(parent[joint_indices], dtype=torch.long)
        self.origin = torch.from_numpy(model.joint_X_p.numpy()[joint_indices].copy())
        self.axes = torch.from_numpy(model.joint_axis.numpy()[self.dof_indices].copy())
        for name in ('body_indices', 'q_indices', 'ancestors', 'parents', 'origin', 'axes'):
            setattr(self, name, getattr(self, name).to(self.device))
        self._buffers = {}

    def evaluate(self, cfg, *, derivatives=False):
        from newton._src.sim.ik.ik_common import eval_fk_batched

        cfg = torch.as_tensor(cfg, dtype=torch.float32, device=self.device).detach()
        if cfg.shape[-1] != 29:
            raise ValueError('Expected 29 canonical G1 joint coordinates')
        batch_shape = cfg.shape[:-1]
        flat = cfg.reshape(-1, 29)
        n, model, wp = len(flat), self.model, self.wp
        coordinates = torch.zeros((n, model.joint_coord_count), dtype=torch.float32, device=self.device)
        coordinates[:, 6] = 1.  # Newton root quaternion is XYZW.
        coordinates[:, self.q_indices] = flat
        if n not in self._buffers:
            self._buffers[n] = (
                wp.zeros((n, model.joint_dof_count), dtype=float, device=str(self.device)),
                wp.zeros((n, model.body_count), dtype=wp.transform, device=str(self.device)),
                wp.zeros((n, model.body_count), dtype=wp.spatial_vector, device=str(self.device)))
        velocity, body, body_velocity = self._buffers[n]
        stream = (wp.ScopedStream(wp.stream_from_torch(torch.cuda.current_stream(self.device)))
                  if self.device.type == 'cuda' else nullcontext())
        with stream:
            eval_fk_batched(model, wp.from_torch(coordinates), velocity, body, body_velocity)
        transforms = wp.to_torch(body).clone()
        selected = transforms[:, self.body_indices]
        poses = torch.cat((selected[..., [6, 3, 4, 5]], selected[..., :3]), -1)
        poses = poses.reshape(*batch_shape, len(self.links.names), 7)
        if not derivatives:
            return poses

        parents = transforms[:, self.parents]
        parent_q = parents[..., [6, 3, 4, 5]]
        joint_q = quat_multiply(parent_q, self.origin[None, :, [6, 3, 4, 5]])
        joint_position = parents[..., :3]+quat_apply(parent_q, self.origin[None, :, :3])
        axes = quat_apply(joint_q, self.axes[None])
        position = selected[..., :3]
        quaternion = selected[..., [6, 3, 4, 5]]
        dp = torch.linalg.cross(axes[:, None].expand(-1, len(self.links.names), -1, -1),
            position[:, :, None]-joint_position[:, None])
        omega = torch.cat((torch.zeros_like(axes[..., :1]), axes), -1)
        dq = .5*quat_multiply(omega[:, None], quaternion[:, :, None])
        derivative = torch.cat((dq, dp), -1)*self.ancestors[None, :, :, None]
        derivative = derivative.transpose(-1, -2).reshape(*batch_shape, len(self.links.names), 7, 29)
        return poses, derivative

    def forward_kinematics(self, cfg):
        cfg = torch.as_tensor(cfg, dtype=torch.float32, device=self.device)
        if cfg.requires_grad:
            return _NewtonFK.apply(cfg, self)
        return self.evaluate(cfg)

    def numpy_fk(self, cfg):
        return self.evaluate(cfg).detach().cpu().numpy()
