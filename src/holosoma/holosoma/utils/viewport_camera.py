from __future__ import annotations

from loguru import logger


def prime_overview_viewport(env, *, label: str = "Viewport") -> None:
    """Force the Kit viewport to show the full environment layout."""
    if getattr(env, "headless", True):
        return

    simulator = _get_simulator(env)
    sim = getattr(simulator, "sim", None)
    if sim is None:
        return

    target, eye = get_overview_camera(env)
    sync_visualizer_camera_pose(sim, eye, target)
    activate_perspective_viewport_camera()
    if hasattr(sim, "set_camera_view"):
        try:
            sim.set_camera_view(eye, target)
        except Exception as exc:
            logger.debug(f"{label} SimulationContext camera setup skipped: {exc}")

    for _ in range(12):
        try:
            sim.render()
        except Exception as exc:
            logger.debug(f"{label} viewport sim.render() warmup skipped: {exc}")
            break

    sync_visualizer_camera_pose(sim, eye, target)
    if hasattr(sim, "set_camera_view"):
        try:
            sim.set_camera_view(eye, target)
        except Exception as exc:
            logger.debug(f"{label} final camera setup skipped: {exc}")
    logger.info(f"{label} viewport overview primed: eye={eye}, target={target}")


def get_overview_camera(env) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    try:
        simulator = _get_simulator(env)
        origins = simulator.env_origins
        origins_cpu = origins.detach().cpu()
        min_xyz = origins_cpu.min(dim=0).values.tolist()
        max_xyz = origins_cpu.max(dim=0).values.tolist()
        center = [(float(min_xyz[i]) + float(max_xyz[i])) * 0.5 for i in range(3)]
        span_x = max(float(max_xyz[0]) - float(min_xyz[0]), 1.0)
        span_y = max(float(max_xyz[1]) - float(min_xyz[1]), 1.0)
        span = max(span_x, span_y, 20.0)

        target = (center[0], center[1], center[2] + 0.5)
        eye = (center[0] + 0.35 * span, center[1] - 0.75 * span, center[2] + 0.85 * span)
        return target, eye
    except Exception:
        target = (0.0, 0.0, 0.5)
        eye = (12.0, -28.0, 24.0)
        return target, eye


def _get_simulator(env):
    return getattr(env, "simulator", None) or getattr(env, "sim", None)


def sync_visualizer_camera_pose(
    sim,
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
) -> None:
    visualizers = getattr(sim, "visualizers", None) or []
    for visualizer in visualizers:
        cfg = getattr(visualizer, "cfg", None)
        if cfg is not None:
            try:
                cfg.eye = eye
                cfg.lookat = target
            except Exception as exc:
                logger.debug(f"Visualizer camera cfg sync skipped for {type(visualizer).__name__}: {exc}")
        set_camera_view = getattr(visualizer, "set_camera_view", None)
        if callable(set_camera_view):
            try:
                set_camera_view(eye, target)
            except Exception as exc:
                logger.debug(f"Visualizer camera view sync skipped for {type(visualizer).__name__}: {exc}")


def activate_perspective_viewport_camera() -> None:
    try:
        import omni.kit.viewport.utility as viewport_utils
    except Exception:
        return

    viewport_api = viewport_utils.get_active_viewport()
    if viewport_api is None:
        return
    set_active_camera = getattr(viewport_api, "set_active_camera", None)
    if set_active_camera is not None:
        try:
            set_active_camera("/OmniverseKit_Persp")
        except Exception:
            return
