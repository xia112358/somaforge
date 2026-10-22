# Data policy

This repository integrates Newton whole-body tracking, expert/student
distillation, contact-aware motion editing, Predictor/Infiller generation and
retargeting. Keep the Git tree small enough for practical review and checkout.

## Allowed in git

- Source code, tests, and small scripts.
- Small JSON/YAML/TOML configuration files.
- Small motion/scene/contact manifests that are needed to reproduce a training command.
- Small terrain or robot example assets when they are required by an active test or documented example.
- The canonical G1 URDF/meshes and fingerprinted USD bundle needed to configure
  the simulator consistently on another machine.
- Documentation and experiment notes.

## Not allowed in git

- Raw or generated rollout `.npz` / `.npy` motion arrays.
- Checkpoints: `.pt`, `.pth`, `.ckpt`, ONNX exports, policy snapshots.
- WandB directories, training logs, videos, plots, CSV dumps, and temporary analysis outputs.
- Large copied HTML/vendor documentation dumps.
- Full external datasets or generated retargeting result directories.

Formal datasets, references, checkpoints and manifests belong in
`runtime/current/{motions,models,manifests,generated}/`; persistent caches and
retained input/launch records use `runtime/current/cache/` and
`runtime/current/archives/`. Use `tmp/` for diagnostics
and disposable experiments only. Existing referenced artifacts in `tmp/` are
protected historical dependencies, not permission to delete them.

Other ignored local paths include:

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

If a manifest depends on large files outside git, document the expected layout in `docs/repository-maintenance.md` or a nearby README.

Do not commit one workstation's absolute dataset/checkpoint paths as current
defaults. Explicit local teacher specifications and launch records may use them;
shared examples should show portable paths or clearly marked placeholders. See
[installation](install.md) and [repository data](repository-data.md) for runtime
bootstrap and independent data transfer.

## Contact-reference identity

New sparse/force WBT references require the canonical robot identity and actual
Newton/MJWarp constraint activation/allocation, with shared primary-surface
selection and recorded sample timing. Preserve raw contacts for audit. Force
thresholds, geometric proximity and predicted contact intent are not substitute
contact truth. A recorded executed trajectory must remain identified as execution
data; do not silently replace clean reference kinematics with rollout tracking
error. See the [modular recording guide](wbt-modular-experiments.md#prepare-contact-reference-data-independently).

## Retargeting exception

`src/holosoma_retargeting/` uses an independent environment and has separate data
requirements. WBT maintenance does not authorize moving or deleting retargeting
data/scripts. Any cleanup requires an itemized confirmation and the system
recycle bin, as required by `AGENTS.md`; runtime bootstrap must preserve existing
directories and links.
