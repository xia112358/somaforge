# Conda Environments

SomaForge uses Conda environments only. Project-local `.venv` environments are
not part of the supported workflow.

| Environment | Responsibility |
| --- | --- |
| `env_somaforge` | SomaForge workspace, Holosoma, Isaac Lab 3/Newton, Motion Edit, evaluation, and TensorBoard |
| `gmvq_vae` | GMVQ and HyAR model preparation and training |
| `hsretargeting` | OmniRetarget and source-motion retargeting |
| `env_pyroki_climb_projection` | Motion Edit PyRoki IK subprocess |

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
override. `force-retarget` continues to use `env_pyroki_climb_projection`.
