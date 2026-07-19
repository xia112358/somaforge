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
| `exp:g1-29dof-wbt-baseline-single` | Single-motion diagnosis | `omniretarget_baseline.json` | `hotspot_failure_window` | 22 s |
| `exp:g1-29dof-wbt-baseline-29` | Initial 29-motion policy | `omniretarget_baseline_29.json` | `hotspot_failure_window` | 10 s |
| `exp:g1-29dof-wbt-contact-force` | Newton 8-part force tracking | `newton_contact_force_8part.json` | `hotspot_failure_window` | 20 s |

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
-> Motion Edit ContactEditPlan and generate-ref
-> force-retarget (PyRoki three-cost graph + repeated Newton force rollout)
-> accepted canonical 8-part Newton force reference/manifest
-> GMVQ segment pack and checkpoint
-> WBT training from scratch
```

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

Use the Newton rollout contact manifest as the Motion Edit source. Import it to
register immutable `MotionAsset` records, open one registered asset in the
Contact Editor, validate its `ContactEditPlan`, then write an edited kinematic
reference into `runtime/current/motions/`:

```bash
source scripts/source_somaforge.sh
packages/motion_edit/motion-edit import-asset-manifest \
  --manifest runtime/current/manifests/newton_contact_force_8part.json
packages/motion_edit/motion-edit contact-editor \
  --motion-asset-id climb_01_newton_8part
packages/motion_edit/motion-edit validate-contact-edit-plan --plan /path/to/plan.json
packages/motion_edit/motion-edit generate-ref --plan /path/to/plan.json \
  --output-motion runtime/current/motions/example.policy_ref_v1.npz \
  --output-contact-layer /path/to/contact_layer.json \
  --output-motion-version-id example_v1
```

`generate-ref` does not solve contact forces. Replay the edited reference with
the baseline policy and extract canonical Newton forces:

```bash
python scripts/extract_all_rollout_ref_contact_force_demos.py \
  --base-manifest runtime/current/manifests/example_motion_edit.json \
  --checkpoint runtime/current/models/baseline/model.pt
```

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
