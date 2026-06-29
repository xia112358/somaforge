from holosoma.config_types.simulator import (
    MujocoBackend,
    MujocoWarpConfig,
    PhysxConfig,
    SceneConfig,
    SimEngineConfig,
    SimulatorConfig,
    SimulatorInitConfig,
)

isaacgym = SimulatorConfig(
    _target_="holosoma.simulator.isaacgym.isaacgym.IsaacGym",
    _recursive_=False,
    config=SimulatorInitConfig(
        name="isaacgym",
        sim=SimEngineConfig(
            fps=200,
            control_decimation=4,
            substeps=1,
            physx=PhysxConfig(
                solver_type=1,
                num_position_iterations=8,
                num_velocity_iterations=4,
                bounce_threshold_velocity=0.5,
            ),
        ),
        contact_sensor_history_length=3,
    ),
)

isaaclab3_newton = SimulatorConfig(
    _target_="holosoma.simulator.isaaclab3_newton.isaaclab3_newton.IsaacLab3Newton",
    _recursive_=False,
    config=SimulatorInitConfig(
        name="isaaclab3_newton",
        scene=SceneConfig(
            replicate_physics=True,
        ),
        sim=SimEngineConfig(
            fps=200,
            control_decimation=4,
            substeps=1,
            physx=PhysxConfig(
                solver_type=1,
                num_position_iterations=8,
                num_velocity_iterations=4,
                bounce_threshold_velocity=0.5,
            ),
            render_mode="human",
            render_interval=4,
        ),
        mujoco_warp=MujocoWarpConfig(
            nconmax_per_env=128,
            njmax_per_env=None,
        ),
        contact_sensor_history_length=3,
    ),
)

# This migration copy is Newton-only. Keep the historical `simulator:isaacsim`
# selector as an alias so old launch scripts do not silently instantiate PhysX.
isaacsim = isaaclab3_newton


mujoco = SimulatorConfig(
    _target_="holosoma.simulator.mujoco.mujoco.MuJoCo",
    _recursive_=False,
    config=SimulatorInitConfig(
        name="mujoco",
        scene=SceneConfig(
            replicate_physics=True,
        ),
        sim=SimEngineConfig(
            fps=200,
            control_decimation=4,
            substeps=1,
            physx=PhysxConfig(
                solver_type=1,
                num_position_iterations=4,
                num_velocity_iterations=0,
                bounce_threshold_velocity=0.5,
            ),
            render_mode="fake",
            render_interval=1,
        ),
        mujoco_backend=MujocoBackend.CLASSIC,  # Explicit for clarity
    ),
)


mjwarp = SimulatorConfig(
    _target_="holosoma.simulator.mujoco.mujoco.MuJoCo",
    _recursive_=False,
    config=SimulatorInitConfig(
        name="mujoco",
        scene=SceneConfig(
            replicate_physics=True,
        ),
        sim=SimEngineConfig(
            fps=200,
            control_decimation=4,
            substeps=1,
            physx=PhysxConfig(
                solver_type=1,
                num_position_iterations=4,
                num_velocity_iterations=0,
                bounce_threshold_velocity=0.5,
            ),
            render_mode="fake",
            render_interval=1,
        ),
        mujoco_backend=MujocoBackend.WARP,  # GPU-accelerated backend
    ),
)


DEFAULTS = {
    "isaacgym": isaacgym,
    "isaacsim": isaaclab3_newton,
    "isaaclab3-newton": isaaclab3_newton,
    "mujoco": mujoco,
    "mjwarp": mjwarp,
}
