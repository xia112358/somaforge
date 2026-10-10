# SomaForge

SomaForge is the unified workspace for G1 contact-aware motion editing,
next-contact prediction, endpoint-conditioned trajectory infilling, and
IsaacLab3/Newton whole-body tracking.

## Layout

```text
src/holosoma/               WBT training, evaluation, and simulator integration
src/holosoma_retargeting/   Retargeting tools (separate environment)
packages/motion_edit/       Contact editing and validated kinematic candidates
packages/generator/         Predictor, Infiller, datasets and generation training
packages/contact_solver/    Contact objectives, collision gradients and projection
packages/climb00_pipeline/  Legacy import and module CLI compatibility
packages/somaforge_core/    Shared assets, FK, contracts and Newton contact semantics
OmniRetarget_Dataset/       Imported preprocessing tools
runtime/current/            Outputs made with the canonical robot asset
configs/assets_manifest.json Manifest-first registry for every runtime asset
configs/training_pipeline_manifest.json Shared training data contract
```

See [repository maintenance](docs/repository-maintenance.md) for active entrypoints,
historical compatibility, data retention and validation commands.

## Canonical assets

Every G1 path uses:

```text
src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.urdf
```

All runtime inputs are selected through `configs/assets_manifest.json` and
`configs/training_pipeline_manifest.json`. Training motions, Predictor/Infiller datasets,
and checkpoints must carry the matching `robot_asset_json` identity.
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
original force-free motion
-> direct Newton FK canonicalization
-> self-collision-enabled WBT policy
-> parallel Newton policy rollouts with measured force/raw contacts
-> one fused rollout source
-> surface-aware contact layer and validated ContactEditPlan
-> contact-Laplacian semantic curves
-> Newton robot-local rigid patches
-> PyRoki trajectory IK with Newton penetration/self-collision costs
-> direct Newton FK canonical edited motion
-> fine-tune the same self-collision policy on the augmented motion
-> Newton policy execution produces the augmented motion's real force
```

The retained reference implementation is documented in
[`height110_production_pipeline.md`](packages/motion_edit/docs/height110_production_pipeline.md).
Self-collision is enabled from the initial policy onward. The old clean6hz,
frame-boundary replay, force-retarget, and projector branches are not
production paths.

The current generation architecture is:

```text
current robot state + actual contact observation + terrain
-> Predictor: next contact plan and endpoint pose
-> Infiller: continuous motion between endpoints
-> Newton validation and WBT tracking
```

Predictor and Infiller replace the retired GMVQ/HyAR module. Their code lives in
`packages/generator/`. The current Predictor baseline is
[`predictor.v1_latest.20261010`](baselines/predictor_v1_latest_20261010/baseline.json):
the v1 shared-observation architecture, coherent shape/target interval loss,
loaded-material207_joint_v12 data, and keep-patch weight 1. Its frozen reference
is the 2026-10-09 scratch run's step1000 checkpoint, selected as the latest saved
result rather than by a single validation peak. The recipe uses 100 demonstration
warmup intervals plus 1000 feedback intervals with continuous demonstration
training and autonomous post-demonstration feedback. The observed run reached
1002 intervals and has no completion report; it did not complete all 1100.
Configuration, checkpoint and dependency hashes, stage-wide validation statistics
and reproduction commands are registered in the baseline directory and
`configs/assets_manifest.json`. Static endpoints and a training-case recursion
do not establish held-out recursive generalization or executed support/load/slip.
The previous pretrained Predictor recipe and its entrypoints have been retired.
Its raw recursive evaluation uses Predictor outputs alone; it is not an
acceptance result for an integrated Predictor + Infiller + WBT deployment.
The older [pairwise48 report](docs/climb00-pairwise48-production.md) is historical.

Previous Predictor recipes and comparison checkpoints are
[archived in place](baselines/README.md), including scratch_recipe.20261002,
source550 and control500. Historical weights, data and source snapshots remain
available for explicit comparisons; current defaults use the latest baseline.
The overall structured v2 architecture replacement is recorded as
[failed and not adopted](baselines/predictor_control500_20261009/architecture_decision.json).
The latest baseline designation does not claim an independently measured gain
from the coherent-query refactor or continuous physical execution acceptance.

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

The first WBT run uses only the Newton-canonicalized source motion and terrain.
It does not depend on Motion Edit, Predictor, or Infiller. Self-collision must already
be enabled here and remains enabled for rollout collection and every later
fine-tune. Save the accepted checkpoint and rollout recording under
`runtime/current/`.

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

The production generator consumes one fused rollout source for pose, measured
force evidence, contact timing, and raw Newton patch geometry. It writes
canonical edited kinematics only; stale source-force and `raw_contact_*` fields
are not copied:

```bash
conda run --no-capture-output -n env_somaforge python \
  scripts/generate_contact_aware_edited_motion.py \
  --plan /path/to/validated_plan.json \
  --output "$PWD/tmp/motion_edit_run/final_motion.npz" \
  --intermediate-dir "$PWD/tmp/motion_edit_run/work" \
  --ik-collision-reference-cache \
    "$PWD/tmp/motion_edit_run/source_collision_reference.npz" \
  --ik-conda-env env_somaforge \
  --newton-device cpu
```

Reuse the same collision-reference cache for every variant derived from one
source rollout. Its terrain, source qpos, and canonical robot-asset hashes are
validated before use; a mismatch is recomputed rather than accepted.

The generated motion must contain `joint_pos [T,36]`, `joint_vel [T,35]`,
complete body pose/velocity arrays, canonical joint/body names,
`robot_asset_json`, and direct-Newton kinematics provenance. Body poses are
exactly direct Newton FK of `joint_pos`.

The edited motion and the accepted self-collision policy checkpoint are the
two inputs to fine-tuning. Force is not copied or replay-baked into the edited
NPZ. The fine-tuned policy produces the augmented motion's real contact force
when it executes in Newton.
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

### 4. Train Predictor and Infiller

Use actual Newton contact labels and event boundaries. Predictor learns the
next contact plan and endpoint pose; Infiller learns the trajectory between
endpoints. Generated trajectories require independent contact, collision and
WBT acceptance before use as validated references.

See [the latest v1 baseline](baselines/predictor_v1_latest_20261010/baseline.json) for the
saved Predictor configuration and entrypoints. Model weights and training data
remain local. See `packages/generator/` for the Infiller implementations;
this replacement does not assert a newly validated combined runtime.

### 5. Train the refined Holosoma WBT policy

Use the canonical Newton USD and the Newton-validated force manifest produced
from Motion Edit or a Predictor/Infiller-generated reference. Do not resume the baseline
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

Browser playback, contact editing, and saved experiment comparisons share
`./motion-edit contact-editor`. Use `--motion-id <registered-id>` for registered
motions or `--review <canonical.npz|diagnostic.json>` for read-only review;
`--terrain <terrain.obj>` supplies the scene for an NPZ sequence. See
[the unified playback guide](packages/motion_edit/README.md#unified-playback-and-experiment-review).

接触保持意图、实际载荷与支撑滑移的全链路约定见 [支撑证据](docs/support-semantics.md)。
