# Conda Environments

SomaForge uses Conda environments only. Project-local `.venv` environments are
not part of the supported workflow.

| Environment | Responsibility |
| --- | --- |
| `env_somaforge` | SomaForge workspace, Holosoma, Isaac Lab 3/Newton, Motion Edit/PyRoki, Predictor/Infiller, evaluation, and TensorBoard |
| `hsretargeting` | OmniRetarget and source-motion retargeting |

Use the repository setup scripts rather than activating environments manually:

```bash
./scripts/setup_isaaclab3_newton.sh
source scripts/source_isaaclab3_newton_setup.sh
source scripts/source_retargeting_setup.sh
source scripts/source_somaforge.sh
```

`env_somaforge` is the default runtime environment for the repository. The
setup/source scripts accept `SOMAFORGE_CONDA_ENV` when an intentional
compatibility environment is required. The `motion-edit` launcher follows that
default and additionally accepts `MOTION_EDIT_CONDA_ENV` as a command-specific
override. PyRoki/JAXLS and Predictor/Infiller use the same `env_somaforge` runtime and CUDA 12
stack as Isaac Lab; only source-motion retargeting remains isolated in
`hsretargeting`.
