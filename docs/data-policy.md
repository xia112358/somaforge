# Data policy

This repository is the training/integration workspace for Newton WBT climbing. Keep the git tree small enough that code review, checkout, and Codex-assisted edits remain practical.

## Allowed in git

- Source code, tests, and small scripts.
- Small JSON/YAML/TOML configuration files.
- Small motion/scene/contact manifests that are needed to reproduce a training command.
- Small terrain or robot example assets when they are required by an active test or documented example.
- Documentation and experiment notes.

## Not allowed in git

- Raw or generated rollout `.npz` / `.npy` motion arrays.
- Checkpoints: `.pt`, `.pth`, `.ckpt`, ONNX exports, policy snapshots.
- WandB directories, training logs, videos, plots, CSV dumps, and temporary analysis outputs.
- Large copied HTML/vendor documentation dumps.
- Full external datasets or generated retargeting result directories.

Use ignored local paths such as:

```text
tmp/
logs/
logs_eval/
runs/
wandb/
data/
OmniRetarget_Dataset/
```

## Manifest convention

Manifests may point to local absolute paths during active experimentation, but committed examples should prefer one of these forms:

```text
${REPO_ROOT}/relative/path
${DATA_ROOT}/relative/path
/path/to/local/data   # only in clearly documented local examples
```

If a manifest depends on large files outside git, document the expected layout in `docs/training-recipes.md` or a nearby README.

## Retargeting exception

`src/holosoma_retargeting/` is intentionally not cleaned in this pass. Do not move or delete retargeting data/scripts as part of WBT-only cleanup unless that cleanup is explicitly requested later.
