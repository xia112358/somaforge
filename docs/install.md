# Install SomaForge on another machine

For the new independent Miniforge + pip workflow, see
[Python environment profiles](python-environments.md). It creates separate
prefixes and requires explicit profile selection; existing launch defaults and
running training remain unchanged. The earlier GA installation below remains
available for reproducing the current runtime.

The supported simulator profile is Linux x86_64, Ubuntu 22.04 or newer, Python
3.12, an NVIDIA GPU and a driver compatible with the official Isaac Lab 3.0.0 /
Isaac Sim 6.2 runtime. Its PyTorch wheels include CUDA 13; the Docker base image's
CUDA version does not establish the minimum driver requirement. Windows users
can use remote Kit/WebRTC and TensorBoard clients; native Windows installation
of this workspace has not been qualified.

## Clone and initialize

Run all examples from the checkout root. Git, Python 3 with `venv`/`pip`, and a C++
build toolchain are prerequisites. Ubuntu may also need `python3-venv`,
`build-essential`, `cmake`, `libgl1`, `libglib2.0-0` and `libegl1`.

```bash
git clone https://github.com/xia112358/somaforge.git
cd somaforge
python3 scripts/bootstrap_runtime.py
bash scripts/setup_isaaclab3_newton.sh
source scripts/source_isaaclab3_newton_setup.sh
python scripts/check_somaforge_assets.py --allow-missing
python -m holosoma.train_agent --help
python -m holosoma.eval_agent --help
```

Bootstrap creates the ignored runtime directories and logical data/log/tmp links.
For external data storage, use `--data-root /absolute/path/to/somaforge-data`
on the first invocation. Existing directories and links are preserved; conflicts
are reported instead of replaced. Setup installs `uv` locally if needed, selects
or downloads Python 3.12, verifies the pinned Lab checkout, and installs the
official frozen base plus the project overlay and the five maintained workspace
packages. It does not install optional retargeting or historical compatibility
packages into the main environment.

`SOMAFORGE_SETUP_PYTHON` may select an existing Python 3.12 executable.
`SOMAFORGE_ISAACLAB_PATH` may select the Lab checkout; its commit must match the
pin in the setup script. Network access to GitHub, PyPI and NVIDIA package
services is required. Isaac Sim use is subject to NVIDIA's license terms.

The root `uv.lock` describes the Python workspace, not the simulator profile.
Use the setup script for simulation: a root-level `uv sync` does not install the
official Isaac Lab runtime. Activation is required in each new shell.

## Robot assets and data

The canonical G1 URDF and its meshes are tracked. The small fixed USD bundle is
distributed under `assets/g1_spherehand_usd/`; bootstrap verifies and restores it
to the standard converted-asset path. All original fingerprints are retained.
Export metadata inside the fixed USD may mention the original workstation; its
actual layer references are relative. Re-running the URDF converter is an asset
development operation and does not guarantee the same byte fingerprint.

The Git source checkout does not contain training datasets or checkpoint arrays.
Optional training inputs, fixed reference models and extracted demonstrations are
published separately; see [data downloads](data-downloads.md):

```bash
python3 scripts/download_data.py list
python3 scripts/download_data.py fetch wbt_baseline29
python3 scripts/download_data.py verify wbt_baseline29
```

Choose components for the intended experiment. `fetch all` is available but not
required for installation; logs and unrelated checkpoint histories are excluded.
The downloader verifies original hashes and installs local path aliases. It does
not start training or choose a different checkpoint.

Bootstrap prepares their directories without manufacturing data or certifying old
labels. Supply your own canonical motion/terrain manifests, or restore the data
used by a particular registered baseline. See [data layout](repository-data.md)
and [data policy](data-policy.md). Baseline records retain hashes of external
inputs; their presence in Git does not mean those inputs were downloaded.

Motion and terrain paths in new manifests should be relative to the manifest.
Published workstation exports retain their original bytes: the downloader writes
`runtime/current/manifests/published_data_paths.json` so readers relocate declared
paths without modifying old manifests, evidence or checkpoints.
Teacher-spec paths can be relative to
their JSON file. Both motion command and terrain configuration must receive the
same chosen manifest. Missing required inputs fail explicitly.

For the independent expert, contact recording and student commands, see
[modular WBT experiments](wbt-modular-experiments.md). The old PHP adapter and the
new native DistillPPO student use different checkpoint/network schemas; installing
the runtime does not convert between them.

## Optional Motion Edit IK and retargeting

PyRoki optimization uses a separate Conda environment. After the main setup,
install Conda if needed, then:

```bash
bash scripts/setup_motion_edit_ik.sh
# Override the environment name by passing it as the sole argument.
conda run -n env_somaforge python -c 'import pyroki, jaxls, coal, clarabel'
```

The requirements pin PyRoki and its JAXLS Git source and install JAX's CUDA 12
backend. Generation commands select this environment with
`--ik-conda-env env_somaforge`; a different name must be passed explicitly.
This environment is not required for WBT training or browser playback.
Source-motion retargeting has its own `scripts/setup_retargeting.sh` and
`scripts/source_retargeting_setup.sh`; inspect that separate workflow before use.

## Verification and remote access

```bash
python scripts/check_repository.py
python scripts/check_asset_manifest.py --allow-missing
python scripts/check_training_manifest.py
packages/motion_edit/motion-edit --help
```

`--allow-missing` is appropriate for auditing a new checkout without external
datasets; it does not waive a training command's required inputs. Static/CPU
checks do not certify GPU initialization or successful policy execution.

Use `--visualizer kit` for Kit and omit it for headless operation; explicit
`--headless` takes precedence. See [environments](environments.md) for rotation
and resume compatibility, and [modular WBT](wbt-modular-experiments.md) for remote
Kit playback. TensorBoard can be reached through an SSH tunnel:

```bash
# On the training host, in the activated environment:
python -m tensorboard.main --logdir /path/to/run --host 127.0.0.1 --port 6006
# On your client:
ssh -N -L 6006:127.0.0.1:6006 user@training-host
```

Then open `http://127.0.0.1:6006` in the client's browser. Dataset restoration,
NVIDIA driver installation, and Docker/GPU compatibility remain machine-specific
requirements; the checks reported for this change state exactly what was run.

The 2026-10-22 portability check used a clean Git clone, a separately cloned pinned
Lab checkout, and new base/project environments on the same Linux host. Asset
identity and imports outside the checkout passed. After copying one explicit
motion/terrain input set into that clone, an eight-environment force expert
completed one update and saved a native checkpoint. This is a bounded installation
and execution check, not an independent-machine benchmark or a convergence test.
Optional IK dependency resolution passed; its full environment and Docker images
were not rebuilt in this check.
