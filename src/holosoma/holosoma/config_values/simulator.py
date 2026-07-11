from holosoma.config_types.simulator import (
    PhysxConfig,
    SceneConfig,
    SimEngineConfig,
    SimulatorConfig,
    SimulatorInitConfig,
    MujocoWarpConfig,
)


isaaclab3_newton = SimulatorConfig(
    _target_="holosoma.simulator.isaaclab3_newton.isaaclab3_newton.IsaacLab3Newton",
    _recursive_=False,
    config=SimulatorInitConfig(
        name="isaaclab3_newton",
        scene=SceneConfig(replicate_physics=True),
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
        mujoco_warp=MujocoWarpConfig(nconmax_per_env=64, njmax_per_env=512),
        contact_sensor_history_length=3,
    ),
)

# Keep the historical selector as a compatibility alias to the only supported backend.
isaacsim = isaaclab3_newton

DEFAULTS = {
    "isaaclab3-newton": isaaclab3_newton,
    "isaacsim": isaaclab3_newton,
}
