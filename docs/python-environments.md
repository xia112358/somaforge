# Python environment profiles

The Miniforge + pip workflow creates independent environments for this checkout.
It does not update an existing training environment, change launcher defaults, or
restart running processes. Select a profile explicitly until a separate switch is
requested. The earlier GA setup remains available in [installation](install.md)
and [runtime compatibility](environments.md).

| Profile | Prefix under the checkout | Purpose |
| --- | --- | --- |
| `main` | `runtime/environments/conda/somaforge` | WBT, Predictor/Infiller, Motion Edit service, native Newton queries and source-motion retargeting |
| `ik` | `runtime/environments/conda/somaforge-ik` | PyRoki/JAX trajectory optimization in a separate process |
| `retarget` | `runtime/environments/conda/somaforge-retarget` | Optional standalone source-motion retargeting; CPU Torch, not the default training environment |

The catalog is [`configs/environments/profiles.json`](../configs/environments/profiles.json).
Each profile declares its Python version, external dependency lock, editable local
packages and any fixed source requirements. Conda supplies Python and pip; pip
installs the locked dependencies. This workflow does not install dependencies
with `uv`, use the root `uv.lock`, or share another environment through `.pth`.
The external Isaac Lab checkout is still pinned and used as a source dependency;
its packages are installed into the new main prefix.

## Plan, create and inspect

Use Linux x86_64 and Miniforge. The main profile builds `evdev` from source; on
Ubuntu install `build-essential` and `linux-libc-dev` for the C compiler and Linux
input/uinput headers. Run commands from the checkout root:

```bash
python3 scripts/bootstrap_runtime.py
python3 scripts/manage_environment.py plan --profile main
python3 scripts/manage_environment.py create --profile main
python3 scripts/manage_environment.py check --profile main
python3 scripts/manage_environment.py run --profile main -- motion-edit --help
```

`plan` displays the proposed locations and installation stages without creating an
environment. `create` creates the declared prefix and installs its lock and local
packages. It can resume a prefix owned by this manager with the same inputs;
foreign or incompatible prefixes are refused rather than overwritten. `check`
reports the environment state and dependency checks. A successful CPU check does
not establish that Kit, CUDA, a policy, or an optimization run has been validated.

To select Miniforge explicitly, add
`--conda /path/to/miniforge3/bin/conda`. Discovery also accepts `CONDA_EXE`,
`MINIFORGE_ROOT`, a `conda` executable on `PATH`, or `~/miniforge3/bin/conda`.
Use `--isaaclab /path/to/pinned/IsaacLab` for the Lab source checkout. These are
machine-local locations; they are not paths embedded into the dependency locks.

`run` resolves `python` from the selected prefix and supplies its runtime markers,
pinned Lab source snapshot, and subprocess routing. Use it as the launch entry
point; a bare `conda activate` does not reproduce that context.

Existing wrappers and `source scripts/source_isaaclab3_newton_setup.sh` still
select the earlier GA runtime. Use the manager's explicit `run --profile main`
form when qualifying the new environment; do not combine both activation methods
in the same shell or assume a legacy wrapper selects the new prefix.

Launch training through the same prefix, for example
`python3 scripts/manage_environment.py run --profile main -- python -m holosoma.train_agent --help`.
Isaac Sim can bootstrap its Kit kernel and request the NVIDIA Omniverse license
even for this help command. The manager does not set `OMNI_KIT_ACCEPT_EULA`
automatically; complete the license prompt when intentionally launching Kit.

## Optional IK and standalone retargeting

```bash
python3 scripts/manage_environment.py plan --profile ik
python3 scripts/manage_environment.py create --profile ik
python3 scripts/manage_environment.py check --profile ik
python3 scripts/manage_environment.py run --profile ik -- python -c 'import pyroki, jaxls, coal, clarabel'

# Main already includes retargeting; create this only for a separate CPU workflow.
python3 scripts/manage_environment.py create --profile retarget
python3 scripts/manage_environment.py check --profile retarget
```

The IK profile uses JAX's CUDA 12 backend for optimization. Torch is the CPU build
required by the installed local package metadata; the IK entrypoint uses JAX for
its optimizer and explicitly requests CPU for its direct Newton collision
queries. This prevents an additional Torch CUDA stack from being installed into
the JAX process. Actual Newton/Kit policy evaluation remains in `main`; the native
contact and canonical robot asset contracts are unchanged.

Launch Motion Edit from `run --profile main`. In managed `main` and `ik` profiles,
generation defaults to the selected catalog's absolute IK prefix, including the
batch command's persistent worker. Outside those profiles the legacy
`env_somaforge` default remains unchanged. An explicit `--ik-conda-env` always
takes precedence, whether it names an older environment or supplies a different
absolute prefix.

The subprocess uses `conda run --prefix` for an absolute path; an existing
environment name still uses `conda run -n`. A caller already running the actual IK
prefix reuses its interpreter. Persistent workers disable Conda output capture.
The manager also supplies its chosen Miniforge executable, so it need not be on
`PATH`. Repository-local prefixes are not named environments; use a full path
rather than just `somaforge-ik` when explicitly overriding the default.

The IK subprocess imports only the declared Motion Edit/core/solver source paths
and its own environment's packages. It does not inherit the parent's Lab or old
site-packages through `PYTHONPATH`. Main-profile markers remain available so a
later native Newton worker can route back to the selected main runtime.

## Locks and source provenance

The main lock contains 382 external packages, exported from the pinned official
Isaac Lab lock plus SomaForge's declared additions and compatibility overrides.
The checked-in lock uses exact artifact URLs and SHA-256 hashes, and its
`.provenance.json` records their origins. Installation consumes those artifacts
directly with pip; it does not run `uv` or resolve a new set of simulator versions.
`scripts/build_environment_lock.py` is the maintainer export utility. The catalog
records specific upstream metadata exceptions for the validated Newton overlay
and the ONNX GPU / official OpenCV providers; they remain visible rather than being hidden by a
generic successful `pip check` claim.

Only one distribution may supply each shared ONNX Runtime or OpenCV Python API.
The manager rejects duplicate providers even when all version requirements are
satisfied; ordinary OpenCV wheels overwrite Isaac Sim's `cv2` binary.

The export utility verifies both the Isaac Lab Git commit and the committed
upstream lock, and refuses a project resolution that changes retained upstream
versions. New simulator versions therefore require an explicit lock update.

The IK and standalone retarget locks cover their local packages' required
external dependencies as well as the workflow-specific requirements. Local
packages are installed separately with `--no-deps`; their presence must not be
used as an excuse to omit their required web, geometry or Torch dependencies.
All registry dependencies have exact versions. The CPU Torch wheel is an explicit
Linux x86_64 / CPython 3.12 URL.

PyRoki is fixed at `388e43e1fc0d0ee382968d3dd72970fd62a0450c`, and JAXLS at
`f8f8dbb54b3e0c16e8bf014496462a4e675e9389`. That PyRoki revision declares a
floating JAXLS Git URL, which pip cannot override with an incompatible direct-URL
constraint. The full dependency closure is therefore resolved using PyRoki's
declared requirements and the fixed JAXLS source; PyRoki is installed from its
fixed revision separately with `--no-deps`. The original source metadata is not
rewritten. Check both dependency versions and VCS commit provenance when changing
these locks.

Fixed source builds use `--no-build-isolation`. The IK profile's eight pinned
bootstrap tools are also listed in
[`ik-bootstrap.lock.txt`](../configs/environments/ik-bootstrap.lock.txt): the common
pip/setuptools/wheel/packaging tools plus hatchling and its pathspec, pluggy and
trove-classifiers dependencies. This supplies JAXLS's build backend on a fresh
machine without relying on a cached wheel or tools in an older environment.

On 2026-10-22, new `main` and `ik` prefixes were actually created with Miniforge
and Python 3.12.15. Both passed the manager's complete dependency, source and
isolation checks; main reports its nine exact compatibility/provider exceptions,
while IK also passes ordinary `pip check`. The new main prefix passed the CPU
repository suite: 2,159 tests and three subtests passed, three tests skipped.
The installed Motion Edit and IK CLI help commands passed. In the new IK prefix,
PyRoki/JAXLS/coal imports, JAX CPU execution and canonical Newton CPU model
construction passed with CUDA hidden. The main-to-IK persistent worker also
passed an actual CPU ping/shutdown check through the selected Miniforge and IK
prefix. A fresh temporary build environment built the fixed JAXLS/PyRoki sources
from an empty cache.

Standalone retargeting has resolver/metadata validation only (76 external
packages and 114 active dependency edges); it was not created because main
already supplies retargeting. GPU IK, Kit launch, policy evaluation and training
were not started. Training CLI help reached the first-use Kit license prompt
and was not accepted as a successful smoke test. Dataset downloads, checkpoint
choice, training restarts and migration of an active run remain separate actions.
