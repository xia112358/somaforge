"""Compatibility import for the packaged canonical G1 Torch FK."""

from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET

import numpy as np
import torch
from torch import nn

from gmvq.g1_fk import CanonicalG1TorchFK
from somaforge_core.robot_assets import canonical_g1_urdf_path, validate_canonical_g1_urdf


def _numbers(value: str | None, default: tuple[float, float, float]):
    if not value:
        return np.asarray(default, dtype=np.float32)
    return np.asarray([float(item) for item in value.split()], dtype=np.float32)


def _rpy_matrix(rpy: np.ndarray) -> np.ndarray:
    roll, pitch, yaw = (float(value) for value in rpy)
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)
    return np.asarray(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ],
        dtype=np.float32,
    )


def _quat_wxyz_matrix(quaternion: torch.Tensor) -> torch.Tensor:
    q = quaternion / quaternion.norm(dim=-1, keepdim=True).clamp_min(1.0e-8)
    w, x, y, z = q.unbind(dim=-1)
    return torch.stack(
        (
            1 - 2 * (y * y + z * z),
            2 * (x * y - z * w),
            2 * (x * z + y * w),
            2 * (x * y + z * w),
            1 - 2 * (x * x + z * z),
            2 * (y * z - x * w),
            2 * (x * z - y * w),
            2 * (y * z + x * w),
            1 - 2 * (x * x + y * y),
        ),
        dim=-1,
    ).reshape(q.shape[:-1] + (3, 3))


def _axis_angle_matrix(axis: torch.Tensor, angle: torch.Tensor) -> torch.Tensor:
    axis = axis / axis.norm().clamp_min(1.0e-8)
    x, y, z = axis.unbind()
    zero = torch.zeros((), dtype=axis.dtype, device=axis.device)
    skew = torch.stack((zero, -z, y, z, zero, -x, -y, x, zero)).reshape(3, 3)
    eye = torch.eye(3, dtype=axis.dtype, device=axis.device)
    outer = axis[:, None] * axis[None, :]
    c = torch.cos(angle)[..., None, None]
    s = torch.sin(angle)[..., None, None]
    return c * eye + (1.0 - c) * outer + s * skew


@dataclass(frozen=True)
class _Joint:
    name: str
    kind: str
    parent: str
    child: str
    xyz: np.ndarray
    rotation: np.ndarray
    axis: np.ndarray


class _LegacyCanonicalG1TorchFK:
    """Evaluate canonical G1 link origins from ``joint_pos[..., 36]``."""

    def __init__(self, *, joint_names: list[str], link_names: list[str]) -> None:
        super().__init__()
        urdf = canonical_g1_urdf_path()
        validate_canonical_g1_urdf(urdf)
        root = ET.parse(urdf).getroot()  # noqa: S314 - validated canonical local asset
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
                    rotation=_rpy_matrix(
                        _numbers(None if origin is None else origin.get("rpy"), (0.0, 0.0, 0.0))
                    ),
                    axis=_numbers(None if axis is None else axis.get("xyz"), (1.0, 0.0, 0.0)),
                )
            )
            children.add(child)
        roots = sorted(links - children)
        if roots != ["pelvis"]:
            raise ValueError(f"canonical G1 URDF must have pelvis root, got {roots}")
        if len(set(joint_names)) != len(joint_names):
            raise ValueError("joint_names contains duplicates")
        joint_index = {name: index for index, name in enumerate(joint_names)}

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
        missing = [name for name in link_names if name not in links]
        if missing:
            raise ValueError(f"requested links are absent from canonical G1 URDF: {missing}")
        actuated = [
            joint.name for joint in ordered if joint.kind in {"revolute", "continuous", "prismatic"}
        ]
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
            self.register_buffer(f"origin_rotation_{index}", torch.from_numpy(joint.rotation))
            self.register_buffer(f"axis_{index}", torch.from_numpy(joint.axis))

    def forward(self, joint_pos: torch.Tensor) -> torch.Tensor:
        if joint_pos.shape[-1] != 36:
            raise ValueError(f"joint_pos must end in 36, got {tuple(joint_pos.shape)}")
        shape = joint_pos.shape[:-1]
        position: dict[str, torch.Tensor] = {"pelvis": joint_pos[..., :3]}
        rotation: dict[str, torch.Tensor] = {"pelvis": _quat_wxyz_matrix(joint_pos[..., 3:7])}
        for index, joint in enumerate(self.joints):
            parent_rotation = rotation[joint.parent]
            xyz = getattr(self, f"origin_xyz_{index}")
            origin_rotation = getattr(self, f"origin_rotation_{index}")
            child_position = position[joint.parent] + torch.matmul(
                parent_rotation, xyz.expand(shape + (3,)).unsqueeze(-1)
            ).squeeze(-1)
            child_rotation = torch.matmul(parent_rotation, origin_rotation)
            if joint.kind in {"revolute", "continuous"}:
                angle = joint_pos[..., 7 + self.joint_index[joint.name]]
                child_rotation = torch.matmul(
                    child_rotation,
                    _axis_angle_matrix(getattr(self, f"axis_{index}"), angle),
                )
            elif joint.kind == "prismatic":
                distance = joint_pos[..., 7 + self.joint_index[joint.name]]
                offset = getattr(self, f"axis_{index}") * distance[..., None]
                child_position = child_position + torch.matmul(
                    child_rotation, offset.unsqueeze(-1)
                ).squeeze(-1)
            position[joint.child] = child_position
            rotation[joint.child] = child_rotation
        return torch.stack([position[name] for name in self.link_names], dim=-2)
