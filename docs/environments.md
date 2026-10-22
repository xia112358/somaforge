# SomaForge runtime environments

All Isaac Lab, Isaac Sim, native Newton, contact workers, and Motion Edit service
entry points use the pinned GA environment:

| Component | Version / location |
| --- | --- |
| Isaac Lab | v3.0.0, commit `e3f7d9ff1f5d7f8280de3ece9000b7117f66bcf4`, `~/isaaclab_3.0_ga` |
| Isaac Sim / Torch | 6.2 / 2.11, supplied by the official GA lockfile |
| Newton / Warp | 1.7.0 / 1.18.0, project compatibility overlay |
| MuJoCo / MuJoCo Warp | 3.15.0 / 3.15.0 |
| GA base | `runtime/environments/isaaclab-ga-3.0.0-base` |
| Project Python | `runtime/environments/isaaclab-ga-3.0.0-newton-1.7.0/bin/python` |
| PyRoki GPU optimization | separate `env_somaforge`, selected by `--ik-conda-env` |
| Source-motion retargeting | separate `hsretargeting` |

The supported project setup is the Bash/Linux workflow below, using Python 3.12
and a compatible NVIDIA GPU/driver. The official base selects Torch's CUDA 13
wheels; a locally installed CUDA toolkit or a CUDA 12.8 container tag alone does
not establish driver compatibility. See [fresh-machine installation](install.md)
for prerequisites and the boundary between environment checks and GPU validation.

From the repository root:

```bash
python3 scripts/bootstrap_runtime.py
bash scripts/setup_isaaclab3_newton.sh
source scripts/source_isaaclab3_newton_setup.sh
python scripts/train_php_wbt.py --help
packages/motion_edit/motion-edit --help
```

Setup preserves older environments and uses the unmodified official GA lockfile
plus `configs/isaaclab-ga-overlay-requirements.txt`. The project overlay inherits
only the GA base's packages. `SOMAFORGE_SETUP_PYTHON` can select the Python 3.12
interpreter used during installation; `SOMAFORGE_ISAACLAB_PATH` selects the pinned
GA checkout. New machines do not need this workstation's Conda environment:
select/bootstrap the Python 3.12 interpreter as described in the installation
guide. The activation script rebuilds Python paths and checks the Newton
runtime. `source scripts/source_somaforge.sh` alone only sets workspace paths;
it does not select a simulator environment. Launch Python workers after GA
activation. The `motion-edit` wrapper activates GA automatically.

`bootstrap_runtime.py` creates the ignored local data layout and aliases without
overwriting an existing directory/link. Use `--data-root /path/to/data` for an
external data root. It also installs the bundled, fingerprinted canonical USD at
the path expected by the simulator. Dataset and checkpoint transfer remains
separate; neither bootstrap nor environment setup chooses training inputs.

The setup source of truth is the pinned external Isaac Lab checkout's `uv.lock`
plus the project's `configs/isaaclab-ga-overlay-requirements.txt` and
`configs/newton-main-requirements.txt`. Do not substitute a generic root `uv sync`
for this environment installation.

Motion Edit trajectory optimization has a separate optional environment:

```bash
bash scripts/setup_motion_edit_ik.sh
```

Its dependencies are recorded in `configs/motion-edit-ik-requirements.txt`,
including fixed PyRoki/JAXLS source revisions. Select the resulting optimization
environment using `--ik-conda-env`; see the installation guide for its exact
activation and CPU/GPU options. Retargeting uses its own
`scripts/setup_retargeting.sh` workflow and is not installed by the main WBT setup.

Use `--visualizer kit` for a window. With no visualizer argument the launch is
headless; explicit `--headless` takes precedence. Official AppLauncher arguments
such as `--device` and `--enable_cameras` are parsed before project configuration.

## Checkpoints and rotations

Root/body states, motion tensors and checkpoint observations remain XYZW.
Explicit WXYZ asset configuration is converted only at USD/Lab boundaries.
Canonical serialized motion files use their declared quaternion convention;
do not infer NPZ ordering from the simulator's internal tensor convention.
The historically named depth-camera `offset_rot_wxyz` field was previously passed
directly to an XYZW sensor. Its default `rotation_convention="legacy_xyzw"`
preserves that physical camera frame for existing checkpoints. New camera
configurations can explicitly select `rotation_convention="wxyz"`; do not change
this on resume without intending to change the observation frame.

Normal model, optimizer, normalization, progress and sampler checkpoint formats
are retained. No simulator snapshot is added. Resume into a separate output
folder when validating an existing run. The upgrade does not restart running
processes; new processes use the environment selected at launch.

The new [modular expert/student workflow](wbt-modular-experiments.md) uses the
native `DistillPPO` checkpoint format. Its student networks/layout differ from the
historical PHP adapter under local `tmp/`; those student checkpoints still require
their original entrypoint. Expert checkpoints must match their canonical asset,
action controls and saved observation/network configuration.

The canonical USD bundle is installed from `assets/g1_spherehand_usd/` with its
existing hashes. `scripts/convert_g1_spherehand_usd.py` is a deliberate asset-build
tool, not a fresh-install prerequisite. Re-running an importer may change USD
bytes even with the same URDF; do not relax fingerprint checks or relabel existing
datasets/checkpoints to accept an unverified conversion.

Newton's native collision guard and canonical G1 asset rules remain active.
The overlay adapts renamed Lab/Newton APIs; it does not change collision margins,
contact activation or the robot asset. Historical experiment reports retain
their original environment paths and are not current setup instructions.

## Migration validation (2026-10-20)

The production environment passed old checkpoint `03913` → `03914` → fresh-process
`03915` resume checks with exact model/normalization, optimizer, sampler and gate
restoration. The original training entry then resumed `03915` and saved `03916`.
These checks used 8 environments and short updates; full-size long-running
training and policy-quality equivalence have not been qualified.

The full regression run passed 2035 tests, skipped 3 and retained 6 Generator
failures also reproduced in the old environment (missing mock `workers`,
undefined `cfg`, and a gradient audit treating a boolean as a tensor).
The final focused state/camera/worker regression passed 42 tests; launcher parsing
passed 6 cases. G1 GPU validation checked 29 joints, XYZW round trips and 30 active
contacts with no unallocated constraints. Actual RGB recording and a 50-step
Kit student playback passed. The Docker recipe was updated but not built.

Local machine-readable evidence and logs (not distributed with a Git clone):
[`tmp/isaaclab_ga_20261020/production_status.json`](../tmp/isaaclab_ga_20261020/production_status.json).
