# Conda Environments

SomaForge uses Conda environments only. Project-local `.venv` environments are
not part of the supported workflow.

| Environment | Responsibility |
| --- | --- |
| `env_holosoma_isaaclab3_newton` | Holosoma, Isaac Lab 3/Newton, Motion Edit, evaluation, and TensorBoard |
| `gmvq_vae` | GMVQ and HyAR model preparation and training |
| `hsretargeting` | OmniRetarget and source-motion retargeting |
| `env_pyroki_climb_projection` | Motion Edit PyRoki IK subprocess |

Use the repository setup scripts rather than activating environments manually:

```bash
source scripts/source_isaaclab3_newton_setup.sh
source scripts/source_retargeting_setup.sh
source scripts/source_somaforge.sh
```

The `motion-edit` launcher uses `env_holosoma_isaaclab3_newton` by default.
`MOTION_EDIT_CONDA_ENV` may override it for an intentional compatibility test.
