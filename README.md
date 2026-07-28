# SomaForge

SomaForge is the unified workspace for G1 contact-aware motion editing,
residual GM-VQ skill representation, and IsaacLab3/Newton whole-body tracking.

## Layout

```text
src/holosoma/               WBT training, evaluation, and simulator integration
src/holosoma_retargeting/   Retargeting tools (separate environment)
packages/motion_edit/       Contact Editor and force-reference generation
packages/gmvq/              GMVQ and HyAR models
packages/somaforge_core/    Shared robot asset identity contract
OmniRetarget_Dataset/       Imported preprocessing tools
runtime/current/            Outputs made with the canonical robot asset
runtime/legacy_wrong_urdf/  Quarantined old data; never use for training
configs/assets_manifest.json Manifest-first registry for every runtime asset
configs/training_pipeline_manifest.json Shared three-stage training data contract
```

## Canonical assets

Every G1 path uses:

```text
src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.urdf
```

All runtime inputs are selected through `configs/assets_manifest.json` and
`configs/training_pipeline_manifest.json`. Training motions, GMVQ datasets,
selectors, and checkpoints must carry the matching `robot_asset_json` identity.
Missing or mismatched identity is rejected.

```bash
source scripts/source_somaforge.sh
python scripts/check_asset_manifest.py
python scripts/check_training_manifest.py
```

Programs can resolve an asset by manifest ID instead of joining paths:

```python
from somaforge_core import AssetManifest

assets = AssetManifest.load()
terrain_dir = assets.resolve("terrain.climb.cache", "root")
robot_urdf = assets.resolve("robot.g1.spherehand", "urdf")
```

## Training presets

The CLI exposes only the three stages used by the canonical pipeline:

| Preset | Purpose | Default manifest | Reset sampler | Horizon |
| --- | --- | --- | --- | --- |
| `exp:g1-29dof-wbt-baseline-single` | Single-motion diagnosis | `omniretarget_baseline.json` | `completion_ema_failure_window` | 22 s |
| `exp:g1-29dof-wbt-baseline-29` | Initial 29-motion policy | `omniretarget_baseline_29.json` | `completion_ema_failure_window` | 10 s |
| `exp:g1-29dof-wbt-contact-force` | Newton 8-part force tracking | `newton_contact_force_8part.json` | `completion_ema_failure_window` | 20 s |

All three presets use the spherehand robot and Isaac Lab 3/Newton. Baseline
presets train from scratch; old checkpoints and manifests are incompatible.

Before the first Isaac Lab/Newton run, generate the USD cache from the canonical URDF:

```bash
source scripts/source_isaaclab3_newton_setup.sh
python scripts/convert_g1_spherehand_usd.py --headless
python scripts/check_somaforge_assets.py
```

## End-to-end workflow

Old checkpoints and motion manifests are intentionally incompatible. Start
from a fresh canonical source motion and rebuild the pipeline in this order:

```text
OmniRetarget/PyRoki qpos
-> Newton canonical FK conversion
-> initial WBT baseline policy
-> Newton rollout/contact-force manifest
-> validated Motion Edit ContactEditPlan
-> low-jitter rollout pose authority (6 Hz zero-phase cleanup)
-> contact-Laplacian whole-body semantic curves
-> Newton robot-local rigid contact patches
-> PyRoki trajectory IK + Newton soft signed-distance similarity
-> direct Newton FK canonical edited motion
-> frame-boundary Newton force replay
-> accepted canonical 8-part Newton force reference/manifest
-> GMVQ segment pack and checkpoint
-> WBT training from scratch
```

The retained reference implementation is
[`height110_soft_signed_distance_v2`](packages/motion_edit/docs/height110_production_pipeline.md).
It is the authority for edited-motion generation and force extraction. The old
force-retarget/projector loops are not production paths.

### 1. Bootstrap and validate assets

```bash
source scripts/source_somaforge.sh
python3 scripts/check_asset_manifest.py
python3 scripts/check_training_manifest.py
source scripts/source_isaaclab3_newton_setup.sh
python scripts/convert_g1_spherehand_usd.py --headless
python scripts/check_somaforge_assets.py
python scripts/canonicalize_omniretarget_newton.py \
  runtime/current/omniretarget/robot-terrain/climb_*.npz \
  --output-dir runtime/current/motions \
  --output-fps 50 \
  --batch-size 1 \
  --headless
python scripts/build_newton_motion_manifest.py \
  --manifest runtime/current/manifests/omniretarget_baseline_29.json \
  --raw-root runtime/current/omniretarget/robot-terrain
python scripts/check_motion_manifest.py
```

### 2. Train the initial WBT baseline

The first WBT run uses only the Newton-canonicalized source motion and terrain. It
does not depend on Motion Edit, GM-VQ, or HyAR. Save the baseline checkpoint
and rollout/contact manifest under `runtime/current/`.

```bash
source scripts/source_isaaclab3_newton_setup.sh
python src/holosoma/holosoma/train_agent.py \
  exp:g1-29dof-wbt-baseline-29 \
  simulator:isaaclab3-newton \
  --headless \
  --command.setup-terms.motion-command.params.motion-config.motion-manifest \
    runtime/current/manifests/omniretarget_baseline_29.json \
  --terrain.terrain-term.motion-matched-manifest \
    runtime/current/manifests/omniretarget_baseline_29.json \
  --training.num-envs 4096
```

### 3. Create the Motion Edit reference

Use the Newton rollout contact manifest as the Motion Edit source. Import it,
open a registered asset in the unified Contact Editor, and validate its
surface-constrained `ContactEditPlan`:

```bash
source scripts/source_somaforge.sh
packages/motion_edit/motion-edit import-asset-manifest \
  --manifest runtime/current/manifests/newton_contact_force_8part.json
packages/motion_edit/motion-edit contact-editor \
  --motion-asset-id climb_01_newton_8part
packages/motion_edit/motion-edit validate-contact-edit-plan --plan /path/to/plan.json
```

The production generator consumes one pose authority and one force rollout
authority. It writes canonical kinematics only; stale source-force and
`raw_contact_*` fields are not copied:

```bash
conda run --no-capture-output -n env_somaforge python \
  scripts/generate_contact_aware_edited_motion.py \
  --plan /path/to/validated_plan.json \
  --output "$PWD/tmp/motion_edit_run/final_motion.npz" \
  --intermediate-dir "$PWD/tmp/motion_edit_run/work" \
  --ik-conda-env env_somaforge \
  --newton-device cpu
```

The generated motion must contain `joint_pos [T,36]`, `joint_vel [T,35]`,
complete body pose/velocity arrays, canonical joint/body names,
`robot_asset_json`, and direct-Newton kinematics provenance. Body poses are
exactly direct Newton FK of `joint_pos`.

Contact force is calculated afterward with frame-boundary Newton replay. At
each 20 ms control boundary the edited state is authoritative, Newton advances
four continuous 5 ms substeps, and the fourth substep supplies the force
sample. Source forces are references only and are never migrated into the
edited file. See the retained height110 pipeline for the replay, policy
reference build, fine-tune, and acceptance commands.

The resulting force files carry `contact_force_provenance_json` with the
Newton solver configuration. MuJoCo diagnostic forces are rejected by WBT.
`contact_force_part_w` is the unfiltered Newton force from the latest physics
step and is time-aligned with `contact_force_part_position_w` and the raw
contact channels. `contact_force_part_history_w` preserves the real physics
substeps in latest-first order. Contact-state hysteresis only affects
`contact_force_part_mask`; the direct threshold result remains available as
`contact_force_part_mask_raw` and no mask processing changes either force
channel.

### Evaluate a checkpoint

Evaluation loads the experiment configuration stored in the checkpoint, then
applies the dedicated evaluation settings and any advanced experiment
overrides. Interactive visualization uses only Isaac Lab's
`--visualizer kit` flag:

```bash
# Interactive Isaac Sim / Kit window.
python -m holosoma.eval_agent \
  --checkpoint /path/to/model.pt \
  --visualizer kit \
  --num-envs 1 \
  --max-steps 2000

# Headless evaluation. Omit --visualizer for the same default, or make it explicit.
python -m holosoma.eval_agent \
  --checkpoint /path/to/model.pt \
  --headless \
  --num-envs 29 \
  --max-steps 2000
```

Evaluation does not write persistent TensorBoard or W&B logs by default.
`--video.enabled True`, `--recording.config.enabled True`,
`--acceptance.config.enabled True`, and `--export-onnx True` each enable one
explicit output type.

### 4. Prepare and train GM-VQ / HyAR

Prepare segments from the Newton rollout force manifest, then train from the
resulting pack. Keep the pack and checkpoints under `runtime/current/`:

```bash
source scripts/source_somaforge.sh
conda run -n env_somaforge python -m gmvq.prepare_motion_edit_segments \
  --motion-edit-manifest runtime/current/manifests/newton_contact_force_8part.json \
  --motion-root runtime/current/motions \
  --output runtime/current/models/example_segment_pack.npz
conda run -n env_somaforge python -m gmvq.train_gmvq \
  --data runtime/current/models/example_segment_pack.npz \
  --save_dir runtime/current/models/example_gmvq
```

The packer and trainer reject missing or incompatible robot fingerprints.

### 5. Train the refined Holosoma WBT policy

Use the canonical Newton USD and the Newton-validated force manifest produced
from Motion Edit or a GM-VQ/HyAR-decoded reference. Do not resume the baseline
checkpoint:

```bash
source scripts/source_isaaclab3_newton_setup.sh
python src/holosoma/holosoma/train_agent.py \
  exp:g1-29dof-wbt-contact-force \
  simulator:isaaclab3-newton \
  --headless \
  --command.setup-terms.motion-command.params.motion-config.motion-manifest \
    runtime/current/manifests/newton_contact_force_8part.json \
  --terrain.terrain-term.motion-matched-manifest \
    runtime/current/manifests/newton_contact_force_8part.json \
  --training.num-envs 4096
```

Before a long run, use the corresponding scene wrapper with `--dry-run` and
verify that its motion and terrain IDs resolve through the manifests.

`src/holosoma_retargeting` remains in the same repository but uses a separate
environment because its NumPy constraint conflicts with the main workspace.
The supported Conda environments and their responsibilities are listed in
[`docs/environments.md`](docs/environments.md).
