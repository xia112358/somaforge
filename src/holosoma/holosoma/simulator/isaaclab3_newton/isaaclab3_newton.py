from __future__ import annotations

from typing import Any

import isaaclab.sim as sim_utils
from isaaclab.sim.spawners.from_files.from_files import spawn_from_usd
from isaaclab.sim.utils import find_matching_prims, get_current_stage
from loguru import logger
from pxr import Usd, UsdPhysics

from holosoma.simulator.isaaclab3_newton.backend import build_newton_physics_cfg, resolve_robot_usd
from holosoma.simulator.isaacsim.isaacsim import IsaacSim


def spawn_newton_usd_with_floating_root(
    prim_path: str,
    cfg: sim_utils.UsdFileCfg,
    translation: tuple[float, float, float] | None = None,
    orientation: tuple[float, float, float, float] | None = None,
    **kwargs,
) -> Usd.Prim:
    prim = spawn_from_usd(prim_path, cfg, translation=translation, orientation=orientation, **kwargs)

    articulation_props = getattr(cfg, "articulation_props", None)
    if articulation_props is None or articulation_props.fix_root_link is not False:
        return prim

    stage = get_current_stage()
    disabled_count = 0
    for robot_prim in find_matching_prims(prim_path, stage=stage):
        root_joint_path = f"{robot_prim.GetPath()}/Physics/root_joint"
        root_joint_prim = stage.GetPrimAtPath(root_joint_path)
        if not root_joint_prim.IsValid():
            continue

        root_joint = UsdPhysics.Joint(root_joint_prim)
        if not root_joint:
            continue

        root_joint.GetJointEnabledAttr().Set(False)
        disabled_count += 1

    if disabled_count:
        logger.info(f"Disabled {disabled_count} Newton root fixed joint(s) for floating-base articulation.")

    return prim


class IsaacLab3Newton(IsaacSim):
    """Isaac Lab 3.0 wrapper using Newton's MJWarp physics backend."""

    def _build_physics_cfg(self):
        return build_newton_physics_cfg(self.simulator_config)

    def _build_robot_spawn_cfg(
        self,
        asset_root: str,
        robot_asset_cfg: Any,
        robot_rigid_props: sim_utils.RigidBodyPropertiesCfg,
        robot_articulation_props: sim_utils.ArticulationRootPropertiesCfg,
    ):
        usd_path = resolve_robot_usd(asset_root, robot_asset_cfg)
        logger.info(f"Using pre-converted Lab3/Newton robot USD: {usd_path}")
        return sim_utils.UsdFileCfg(
            func=spawn_newton_usd_with_floating_root,
            usd_path=str(usd_path),
            activate_contact_sensors=True,
            rigid_props=robot_rigid_props,
            articulation_props=robot_articulation_props,
        )
