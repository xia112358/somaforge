from __future__ import annotations

import argparse

import tyro

from holosoma.config_types.env import get_tyro_env_config
from holosoma.config_types.experiment import ExperimentConfig
from holosoma.config_values.experiment import AnnotatedExperimentConfig
from holosoma.utils.eval_utils import (
    init_sim_imports,
)
from holosoma.utils.helpers import get_class
from holosoma.utils.motion_matched_config import normalize_motion_matched_config
from holosoma.utils.sim_utils import close_simulation_app, parse_isaaclab_launcher_args, sync_launcher_headless_config
from holosoma.utils.tyro_utils import TYRO_CONIFG


def replay(tyro_config: ExperimentConfig, launcher_args: argparse.Namespace | None = None):
    tyro_config = normalize_motion_matched_config(tyro_config)
    simulation_app = init_sim_imports(tyro_config, launcher_args=launcher_args)

    import torch

    from holosoma.utils.common import seeding

    seeding(42, torch_deterministic=False)

    env_target = tyro_config.env_class
    tyro_env_config = get_tyro_env_config(tyro_config)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    env = get_class(env_target)(tyro_env_config, device=device)
    _set_replay_camera(env)

    try:
        done = False
        camera_reapplied = False
        while not done:
            env.simulator.sim.step()
            done = env.step_visualize_motion(None)  # type: ignore[attr-defined]
            if not camera_reapplied:
                _set_replay_camera(env)
                camera_reapplied = True
    finally:
        close_simulation_app(simulation_app)


def _set_replay_camera(env) -> None:
    target = _get_replay_camera_target(env)
    eye = (target[0] + 3.2, target[1] + 3.8, target[2] + 3.6)
    simulator = getattr(env, "simulator", None)
    if simulator is None:
        return

    sim = getattr(simulator, "sim", None)
    if sim is not None and hasattr(sim, "set_camera_view"):
        sim.set_camera_view(eye, target)
        _set_active_viewport_camera_z_up(sim, eye, target)


def _set_active_viewport_camera_z_up(sim, eye: tuple[float, float, float], target: tuple[float, float, float]) -> None:
    try:
        import omni.kit.viewport.utility as viewport_utils
        from pxr import Gf, Sdf, UsdGeom
    except Exception:
        return

    viewport_api = viewport_utils.get_active_viewport()
    if viewport_api is None:
        return

    stage = getattr(sim, "stage", None)
    if stage is None:
        return

    camera_path = Sdf.Path("/World/ReplayCamera")
    camera_prim = stage.GetPrimAtPath(camera_path)
    if not camera_prim.IsValid():
        camera_prim = UsdGeom.Camera.Define(stage, camera_path).GetPrim()

    camera = UsdGeom.Camera(camera_prim)
    camera.CreateFocalLengthAttr(20.0)
    camera.CreateClippingRangeAttr((0.01, 10000.0))

    transform = Gf.Matrix4d(1).SetLookAt(
        Gf.Vec3d(*eye),
        Gf.Vec3d(*target),
        Gf.Vec3d(0.0, 0.0, 1.0),
    ).GetInverse()
    xformable = UsdGeom.Xformable(camera_prim)
    xformable.ClearXformOpOrder()
    xformable.AddTransformOp().Set(transform)

    camera_prim.CreateAttribute("omni:kit:centerOfInterest", Sdf.ValueTypeNames.Vector3d, True).Set(Gf.Vec3d(*target))
    try:
        viewport_api.camera_path = camera_path
    except Exception:
        set_active_camera = getattr(viewport_api, "set_active_camera", None)
        if set_active_camera is not None:
            set_active_camera(str(camera_path))


def _get_replay_camera_target(env) -> tuple[float, float, float]:
    try:
        motion_command = env.command_manager.get_state("motion_command")
        root_pos = motion_command.root_pos_w[0].detach().cpu().tolist()
        return (float(root_pos[0]), float(root_pos[1]), float(root_pos[2]) + 0.15)
    except Exception:
        return (0.3, -0.3, 0.45)


def main() -> None:
    launcher_args = parse_isaaclab_launcher_args("Replay a Holosoma motion.")
    tyro_cfg = tyro.cli(AnnotatedExperimentConfig, config=TYRO_CONIFG)
    tyro_cfg = sync_launcher_headless_config(tyro_cfg, launcher_args)
    replay(tyro_cfg, launcher_args=launcher_args)


if __name__ == "__main__":
    main()
