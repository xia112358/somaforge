"""Differentiable FK for the authoritative floating-base G1 URDF."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import numpy as np
import torch
from somaforge_core.robot_assets import canonical_g1_urdf_path, validate_canonical_g1_urdf
from torch import nn


def _numbers(value: str | None, default: tuple[float, float, float]) -> np.ndarray:
    if not value:
        return np.asarray(default, dtype=np.float32)
    return np.asarray([float(item) for item in value.split()], dtype=np.float32)


def _rpy_quat_wxyz(rpy: np.ndarray) -> np.ndarray:
    roll, pitch, yaw = (float(value) for value in rpy)
    cr, sr = np.cos(roll / 2.0), np.sin(roll / 2.0)
    cp, sp = np.cos(pitch / 2.0), np.sin(pitch / 2.0)
    cy, sy = np.cos(yaw / 2.0), np.sin(yaw / 2.0)
    return np.asarray(
        (
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        ),
        dtype=np.float32,
    )


def quat_mul_wxyz(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    aw, ax, ay, az = a.unbind(dim=-1)
    bw, bx, by, bz = b.unbind(dim=-1)
    return torch.stack(
        (
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ),
        dim=-1,
    )


def quat_rotate_wxyz(quaternion: torch.Tensor, vector: torch.Tensor) -> torch.Tensor:
    q = quaternion / quaternion.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
    qv = q[..., 1:]
    uv = torch.cross(qv, vector, dim=-1)
    uuv = torch.cross(qv, uv, dim=-1)
    return vector + 2.0 * (q[..., :1] * uv + uuv)


def _axis_angle_quat_wxyz(axis: torch.Tensor, angle: torch.Tensor) -> torch.Tensor:
    axis = axis / axis.norm().clamp_min(1.0e-8)
    half = 0.5 * angle
    return torch.cat((torch.cos(half)[..., None], torch.sin(half)[..., None] * axis), dim=-1)


@dataclass(frozen=True)
class _Joint:
    name: str
    kind: str
    parent: str
    child: str
    xyz: np.ndarray
    quaternion: np.ndarray
    axis: np.ndarray


class CanonicalG1TorchFK(nn.Module):
    """Evaluate requested canonical G1 link origins and WXYZ orientations."""

    def __init__(self, *, joint_names: list[str], link_names: list[str]) -> None:
        super().__init__()
        urdf = canonical_g1_urdf_path()
        validate_canonical_g1_urdf(urdf)
        root = ET.parse(urdf).getroot()  # noqa: S314 - validated authoritative local asset
        links = {str(link.get("name")) for link in root.findall("link")}
        parsed: list[_Joint] = []
        children: set[str] = set()
        for element in root.findall("joint"):
            parent = str(element.find("parent").get("link"))
            child = str(element.find("child").get("link"))
            origin = element.find("origin")
            axis = element.find("axis")
            parsed.append(
                _Joint(
                    name=str(element.get("name")),
                    kind=str(element.get("type")),
                    parent=parent,
                    child=child,
                    xyz=_numbers(None if origin is None else origin.get("xyz"), (0.0, 0.0, 0.0)),
                    quaternion=_rpy_quat_wxyz(_numbers(None if origin is None else origin.get("rpy"), (0.0, 0.0, 0.0))),
                    axis=_numbers(None if axis is None else axis.get("xyz"), (1.0, 0.0, 0.0)),
                )
            )
            children.add(child)
        roots = sorted(links - children)
        if roots != ["pelvis"]:
            raise ValueError(f"canonical G1 URDF must have pelvis root, got {roots}")

        joint_index = {name: index for index, name in enumerate(joint_names)}
        if len(joint_index) != len(joint_names):
            raise ValueError("joint_names contains duplicates")
        pending = parsed.copy()
        available = {"pelvis"}
        ordered: list[_Joint] = []
        while pending:
            ready = [joint for joint in pending if joint.parent in available]
            if not ready:
                raise ValueError("canonical G1 URDF joint tree is disconnected")
            for joint in ready:
                ordered.append(joint)
                available.add(joint.child)
                pending.remove(joint)

        missing_links = [name for name in link_names if name not in links]
        if missing_links:
            raise ValueError(f"requested links are absent from canonical G1 URDF: {missing_links}")
        actuated = [joint.name for joint in ordered if joint.kind in {"revolute", "continuous", "prismatic"}]
        missing_joints = [name for name in actuated if name not in joint_index]
        extra_joints = [name for name in joint_names if name not in set(actuated)]
        if missing_joints or extra_joints:
            raise ValueError(
                f"joint order does not match canonical G1 URDF; missing={missing_joints}, extra={extra_joints}"
            )

        self.joints = ordered
        self.joint_index = joint_index
        self.link_names = tuple(link_names)
        for index, joint in enumerate(ordered):
            self.register_buffer(f"origin_xyz_{index}", torch.from_numpy(joint.xyz))
            self.register_buffer(f"origin_quat_{index}", torch.from_numpy(joint.quaternion))
            self.register_buffer(f"axis_{index}", torch.from_numpy(joint.axis))

    def forward_pose(self, joint_pos: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if joint_pos.shape[-1] != 36:
            raise ValueError(f"joint_pos must end in 36, got {tuple(joint_pos.shape)}")
        shape = joint_pos.shape[:-1]
        root_quat = joint_pos[..., 3:7]
        root_quat = root_quat / root_quat.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
        position: dict[str, torch.Tensor] = {"pelvis": joint_pos[..., :3]}
        quaternion: dict[str, torch.Tensor] = {"pelvis": root_quat}
        for index, joint in enumerate(self.joints):
            parent_quat = quaternion[joint.parent]
            xyz = getattr(self, f"origin_xyz_{index}").expand(shape + (3,))
            child_position = position[joint.parent] + quat_rotate_wxyz(parent_quat, xyz)
            origin_quat = getattr(self, f"origin_quat_{index}").expand(shape + (4,))
            child_quat = quat_mul_wxyz(parent_quat, origin_quat)
            if joint.kind in {"revolute", "continuous"}:
                angle = joint_pos[..., 7 + self.joint_index[joint.name]]
                rotation = _axis_angle_quat_wxyz(getattr(self, f"axis_{index}"), angle)
                child_quat = quat_mul_wxyz(child_quat, rotation)
            elif joint.kind == "prismatic":
                distance = joint_pos[..., 7 + self.joint_index[joint.name]]
                offset = getattr(self, f"axis_{index}") * distance[..., None]
                child_position = child_position + quat_rotate_wxyz(child_quat, offset)
            child_quat = child_quat / child_quat.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
            position[joint.child] = child_position
            quaternion[joint.child] = child_quat
        return (
            torch.stack([position[name] for name in self.link_names], dim=-2),
            torch.stack([quaternion[name] for name in self.link_names], dim=-2),
        )

    def forward(self, joint_pos: torch.Tensor) -> torch.Tensor:
        return self.forward_pose(joint_pos)[0]


__all__ = ["CanonicalG1TorchFK", "quat_mul_wxyz", "quat_rotate_wxyz"]
