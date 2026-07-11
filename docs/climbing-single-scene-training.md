# Climbing Single-Scene Training

This guide trains one policy per climbing scene. Each run uses one retargeted motion file and the matching static obstacle URDF.

Do not use `exp:g1-29dof-wbt-w-object` for this workflow. The climbing obstacle is a fixed collision scene, not a tracked dynamic object. Use `exp:g1-29dof-wbt` and inject the static object through `--robot.object.*`.

## Environment

From the Holosoma repo root:

```bash
cd /home/xiaz/somaforge
source scripts/source_isaaclab3_newton_setup.sh
```

## Scene Inputs

Obstacle URDFs are available for:

```text
src/holosoma_retargeting/holosoma_retargeting/demo_data/climb/mocap_climb_seq_0/multi_boxes_scaled_0.74_0.74_0.74.urdf
src/holosoma_retargeting/holosoma_retargeting/demo_data/climb/mocap_climb_seq_1/multi_boxes_scaled_0.74_0.74_0.74.urdf
src/holosoma_retargeting/holosoma_retargeting/demo_data/climb/mocap_climb_seq_2/multi_boxes_scaled_0.74_0.74_0.74.urdf
src/holosoma_retargeting/holosoma_retargeting/demo_data/climb/mocap_climb_seq_3/multi_boxes_scaled_0.74_0.74_0.74.urdf
src/holosoma_retargeting/holosoma_retargeting/demo_data/climb/mocap_climb_seq_4/multi_boxes_scaled_0.74_0.74_0.74.urdf
```

At the time this doc was written, retargeted G1 climbing motion files found in the repo were for `seq_0`:

```text
src/holosoma_retargeting/holosoma_retargeting/demo_results/g1/climbing/mocap_climb/mocap_climb_seq_0_mj.npz
src/holosoma_retargeting/holosoma_retargeting/demo_results/g1/climbing/mocap_climb/mocap_climb_seq_0_mj_crawlstyle.npz
src/holosoma_retargeting/holosoma_retargeting/demo_results/g1/climbing/mocap_climb/mocap_climb_seq_0_mj_crawlstyle_scale074.npz
```

For `seq_1` to `seq_4`, generate the corresponding `*_mj.npz` first, then use the same command template below with the matching sequence number.

## Refresh Manifest

After retargeting creates new climbing motion files, refresh the manifest:

```bash
python scripts/build_climbing_manifest.py
```

This scans:

```text
src/holosoma_retargeting/holosoma_retargeting/demo_data/climb
src/holosoma_retargeting/holosoma_retargeting/demo_results/g1/climbing
```

and writes:

```text
configs/climbing_scenes.json
```

Only scenes with both a retargeted motion file and the matching obstacle URDF are included.

## Quick Visual Run

Use this first to confirm the robot, motion, and static obstacle align. This keeps the IsaacSim GUI open and runs only 20 iterations.

```bash
python scripts/train_climbing_scene.py \
  --seq 0 \
  --variant mj \
  --num-envs 256 \
  --gui \
  --iterations 20
```

For available alternate `seq_0` motions, change `--variant`:

```bash
--variant mj_crawlstyle
--variant mj_crawlstyle_scale074
```

## Full Training

After the visual run looks correct, remove the iteration limit or set it explicitly to the desired value.

```bash
python scripts/train_climbing_scene.py \
  --seq 0 \
  --variant mj \
  --num-envs 256 \
  --gui
```

To train a policy for another scene, change `SEQ` and ensure the matching motion file exists:

```bash
python scripts/train_climbing_scene.py --seq 1 --variant mj --num-envs 256 --gui
```

The intended mapping is:

```text
mocap_climb_seq_0_mj.npz -> mocap_climb_seq_0/multi_boxes_scaled_0.74_0.74_0.74.urdf
mocap_climb_seq_1_mj.npz -> mocap_climb_seq_1/multi_boxes_scaled_0.74_0.74_0.74.urdf
mocap_climb_seq_2_mj.npz -> mocap_climb_seq_2/multi_boxes_scaled_0.74_0.74_0.74.urdf
mocap_climb_seq_3_mj.npz -> mocap_climb_seq_3/multi_boxes_scaled_0.74_0.74_0.74.urdf
mocap_climb_seq_4_mj.npz -> mocap_climb_seq_4/multi_boxes_scaled_0.74_0.74_0.74.urdf
```

## Notes

- Use `python scripts/train_climbing_scene.py --seq 0 --dry-run` to inspect the resolved raw `train_agent.py` command without launching IsaacSim.
- Keep `--simulator.config.scene.env_spacing=0.0` for these single-scene runs so the motion frame and obstacle frame stay aligned.
- Keep `--robot.object.fix-base=True`; the obstacle is static.
- Keep `--robot.object.init-pos "[0.0,0.0,0.0]"` unless the retargeting output and obstacle URDF use a different shared world origin.
- Use one process per scene. This workflow intentionally does not mix multiple obstacle layouts in the same training run.
- If the robot immediately fails tracking, first verify the selected `MOTION` and `OBSTACLE` use the same sequence and scale.

## Raw Command Equivalent

The wrapper resolves a scene from the manifest and then calls `train_agent.py` with arguments equivalent to:

```bash
python src/holosoma/holosoma/train_agent.py \
  exp:g1-29dof-wbt \
  simulator:isaaclab3-newton \
  --robot.object.object-urdf-path="<manifest obstacle_urdf>" \
  --robot.object.fix-base=True \
  --robot.object.init-pos "[0.0,0.0,0.0]" \
  --command.setup_terms.motion_command.params.motion_config.motion_file="<manifest motion_file>" \
  --simulator.config.scene.env_spacing=0.0 \
  --training.num_envs 256 \
  --training.headless=False \
  --logger.video.enabled=False
```
