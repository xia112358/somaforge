# Cleanup scope

This cleanup narrows `holosoma_newton` from a broad upstream Holosoma fork into a Newton WBT climbing workspace.

## Keep

```text
apps/holosoma.isaaclab3_newton*.kit
configs/climbing_scenes.json
configs/motion_matched/
scripts/*climbing*
scripts/*motion_matched*
scripts/*contact_force*
scripts/setup_isaaclab3_newton.sh
scripts/source_isaaclab3_newton_setup.sh
src/holosoma/holosoma/agents/
src/holosoma/holosoma/config_types/
src/holosoma/holosoma/config_values/wbt/
src/holosoma/holosoma/envs/base_task/
src/holosoma/holosoma/envs/wbt/
src/holosoma/holosoma/managers/*/terms/wbt.py
src/holosoma/holosoma/train_agent.py
src/holosoma/holosoma/eval_agent.py
src/holosoma/holosoma/replay.py
src/holosoma/holosoma/run_sim.py
src/holosoma/holosoma/simulator/isaaclab3_newton/
```

## Do not touch in this pass

```text
src/holosoma_retargeting/
```

Retargeting remains available as a local/upstream reference until a separate decision is made.

## Remove or archive

Remove old upstream surfaces that are not part of the current WBT climbing workflow:

```text
demo_scripts/                         # OMOMO/LAFAN/ROS2 demos from the broad upstream workflow
scripts/setup_isaacgym.sh              # legacy simulator setup
scripts/source_isaacgym_setup.sh
scripts/setup_isaacsim.sh              # legacy non-Newton IsaacSim setup
scripts/source_isaacsim_setup.sh
scripts/setup_mujoco.sh                # legacy MuJoCo setup
scripts/setup_mujoco_via_uv.sh
scripts/source_mujoco_setup.sh
scripts/source_mujoco_uv_setup.sh
scripts/setup_inference.sh             # legacy deployment/inference setup
scripts/source_inference_setup.sh
docker/isaacgym.Dockerfile
docker/mujoco.Dockerfile
docs/vendor/isaaclab3_newton_refs/     # copied vendor HTML; replace with short notes/links when needed
src/holosoma_inference/                # real-robot/inference package, not used by current training workflow
```

## Cleanup order

1. Change README/docs so the repository scope is explicit.
2. Remove demo/setup/docker/vendor files that are clearly outside the current workflow.
3. Remove or quarantine `src/holosoma_inference/` after checking imports.
4. Only then consider deeper pruning of locomotion or simulator code inside `src/holosoma/`.

## Minimal checks after cleanup

```bash
python -m compileall src/holosoma/holosoma
python -m pytest src/holosoma/holosoma/managers/command/tests -q
python -m pytest src/holosoma/holosoma/managers/reward/tests -q
```

If IsaacLab/CUDA import errors occur in a sandbox, treat them as environment limitations and re-run on the local training machine.
