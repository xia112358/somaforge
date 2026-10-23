# SomaForge

SomaForge is a workspace for G1 whole-body tracking (WBT), expert-to-student
distillation, contact-aware motion editing, and next-contact prediction.
Simulation uses the pinned Isaac Lab
3.0.0 / Isaac Sim 6.2 / Newton 1.7.0 environment.

Git `main` is the maintained integration branch. Its environment catalog declares
one runtime profile, also named `main`, at `runtime/environments/conda/somaforge`.
WBT, distillation, Motion Edit and Predictor all use this profile. The separate IK environment and the standalone Retargeting package have been retired.
Motion Edit uses Torch float32 and native Newton FK, with its existing UI
interfaces preserved. See [component validation](docs/environments.md#main-consolidation-validation-2026-10-2223)
for the completed runtime checks and their scope.

## Start here

- [Fresh-machine installation](docs/install.md) and [runtime compatibility](docs/environments.md)
- [Unified main Python environment](docs/python-environments.md) for every maintained component
- [Modular WBT experts, contact-reference recording and distillation](docs/wbt-modular-experiments.md)
- [ACP single-task reproduction: contact tracking and attention-based planning](docs/acp-reproduction.md)
- [Download training inputs, reference models and extracted demonstrations](docs/data-downloads.md)
- [Motion Edit and browser playback](packages/motion_edit/README.md)
- [Predictor baseline and reproduction records](baselines/README.md)
- [Current main-environment Predictor inputs](docs/environments.md#generator-inputs-for-main)
- [Local data layout](docs/repository-data.md), [data policy](docs/data-policy.md),
  and [repository maintenance](docs/repository-maintenance.md)

From a fresh checkout on a supported Linux NVIDIA workstation:

```bash
python3 scripts/bootstrap_runtime.py
python3 scripts/manage_environment.py create --profile main
source scripts/source_isaaclab3_newton_setup.sh
python3 scripts/manage_environment.py check --profile main
python scripts/check_training_manifest.py
python -m holosoma.train_agent --help
```

Bootstrap creates local runtime directories and aliases; setup installs the
pinned environment. Training inputs, fixed reference checkpoints and extracted
demonstrations are available separately through the
[component downloader](docs/data-downloads.md); cloning Git does not download them.
Follow the [installation guide](docs/install.md) before launching simulation.

## Layout

```text
src/holosoma/               WBT training, evaluation, and simulator integration
packages/motion_edit/       Contact editing and validated kinematic candidates
packages/generator/         Predictor, datasets and prediction training
packages/contact_solver/    Contact objectives, collision gradients and projection
packages/climb00_pipeline/  Optional historical import/CLI compatibility
packages/somaforge_core/    Shared assets, FK, contracts and Newton contact semantics
OmniRetarget_Dataset/       Imported preprocessing tools
runtime/current/            Outputs made with the canonical robot asset
configs/assets_manifest.json Manifest-first registry for every runtime asset
configs/training_pipeline_manifest.json Shared training data contract
```

See [repository maintenance](docs/repository-maintenance.md) for active entrypoints,
historical compatibility, data retention and validation commands.
Past experiment reports are separated under [docs/history](docs/history/README.md).

## Canonical assets

Every G1 path uses:

```text
src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.urdf
```

All runtime inputs are selected through `configs/assets_manifest.json` and
`configs/training_pipeline_manifest.json`. Training motions, Predictor datasets,
and checkpoints must carry the matching `robot_asset_json` identity.
Missing or mismatched identity is rejected.

```bash
source scripts/source_somaforge.sh
python scripts/check_asset_manifest.py --allow-missing
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

The recommended composable defaults use the existing `ExperimentConfig` and
observation, reward, command, termination, curriculum and algorithm managers:

| Preset | Purpose |
| --- | --- |
| `exp:wbt-expert-dense` | Dense-reference expert |
| `exp:wbt-expert-sparse` | Sparse-reference expert with native contact labels |
| `exp:wbt-expert-force` | Expert with reference and measured contact force |
| `exp:wbt-student` | Native PPO/DAgger distillation from explicitly supplied experts |

Each command is independent: manually select manifests and checkpoints, train
experts, record contact-reference data when needed, combine manifests, and distill.
The [modular workflow guide](docs/wbt-modular-experiments.md) lists the commands,
replaceable configuration blocks and resume rules. Student actor inputs contain
measured observations and a high-level task command; reference poses, joint
targets, desired contact/force and teacher routing remain privileged.

The CLI also retains named baseline, future-reference, sparse-climbing and PHP
experiment presets. `exp:g1-29dof-wbt-contact-force` is the older eight-part
force-data experiment; its threshold/hysteresis masks do not establish native
contact truth. New sparse/force experiments require the six-part native-contact
reference contract described in the modular guide.

Compatible checkpoints retain the normal model, optimizer, normalization,
progress and sampler/curriculum state. Compatibility depends on the canonical
robot identity, algorithm and observation/network layout. The native student
cannot load the historical `tmp/` PHP adapter's different checkpoint schema.
No simulator snapshot is saved.

The canonical USD bundle is distributed with its existing fingerprints. Do not
regenerate it as a routine installation step: a new conversion can change bytes
and invalidate the recorded bundle identity. See the environment guide for asset
checks and deliberate conversion.

## Motion editing and generation

The motion-editing branch starts with a canonical source motion and a
self-collision-enabled WBT policy, collects actual executed contact/force evidence,
and edits a validated surface-constrained `ContactEditPlan`. Semantic curves and
Newton rigid patches feed Torch float32 trajectory IK; direct Newton FK produces the
edited kinematic candidate. The policy must execute that candidate to produce its
own actual contact force. Do not copy source force labels into an edited motion.

See [Motion Edit](packages/motion_edit/README.md) and the retained
[height110 reference pipeline](packages/motion_edit/docs/height110_production_pipeline.md)
for the detailed implementation. Historical eight-part recordings, threshold masks
and their acceptance records keep their original meaning; the new six-part WBT
contact-reference contract does not automatically convert or recertify them.
The old clean6hz, frame-boundary replay, force-retarget and projector branches
are not production entrypoints.

Predictor lives in `packages/generator/` and produces next-contact plans and endpoint
poses from robot state, actual contact observations and terrain. Candidates use
independent Newton validation; WBT executes explicitly supplied motion references.
The Infiller module has been retired. Its historical datasets, checkpoints and
published release records remain archived.

The current Predictor pointer is [baselines/current.json](baselines/current.json):
[v1 latest](baselines/predictor_v1_latest_20261010/README.md), using
loaded-material207_joint_v12 data, coherent interval loss and keep-patch weight 1.
Its retained step1000 checkpoint is the latest saved result of the 2026-10-09
scratch run, not a selection by a single validation peak. The run reached
1002 of 1100 planned intervals and has no completion report. Static endpoints and
training-case recursion do not establish held-out recursive generalization or
executed support/load/slip, and no combined Predictor + WBT deployment acceptance is asserted.

[Archived baselines](baselines/README.md) retain scratch_recipe.20261002,
source550 and control500 recipes and comparisons. The structured v2 replacement
was [not adopted](baselines/predictor_control500_20261009/architecture_decision.json).
Historical reports live under [docs/history](docs/history/README.md); they are
not current installation instructions.

## Evaluation and visualization

The evaluator reconstructs a compatible experiment from its checkpoint:

```bash
source scripts/source_isaaclab3_newton_setup.sh
python -m holosoma.eval_agent \
  --checkpoint /path/to/model.pt \
  --num-envs 1 --max-steps 2000 --visualizer kit
```

Omit `--visualizer` for headless operation; explicit `--headless` takes precedence.
Evaluation does not write persistent TensorBoard or W&B logs by default. Video,
recording, acceptance output and ONNX export are explicit options. Remote Kit
uses livestreaming; TensorBoard independently reads the selected training run.
See [evaluation and remote playback](docs/wbt-modular-experiments.md#evaluate-or-replay-separately).

Browser playback and contact editing share
`packages/motion_edit/motion-edit contact-editor`.
Use `--motion-id <registered-id>` for registered motions or
`--review <canonical.npz|diagnostic.json>` for review, with
`--terrain <terrain.obj>` when needed. See the
[unified playback guide](packages/motion_edit/README.md#unified-playback-and-experiment-review).
Browser review does not run the tracking policy or certify actual contact.

Contact intent, realized load and support slip are distinguished in
[the support semantics guide](docs/support-semantics.md).
