# Holosoma Core Package

This package is currently maintained in this repository as part of the
IsaacLab 3 / Newton WBT climbing research workspace.

Use the repository root README for the active project scope. The active setup
entrypoint is:

```bash
source scripts/source_isaaclab3_newton_setup.sh
```

Useful local checks:

```bash
python scripts/gmvq_ref/check_workspace.py
python scripts/gmvq_ref/check_data_layout.py
python -m holosoma.train_agent exp:g1-29dof-wbt simulator:isaaclab3-newton logger:disabled
```

Legacy IsaacGym, MuJoCo, and real-robot inference examples from the upstream
framework are intentionally not documented here because their setup entrypoints
are not active in this cleanup branch.
