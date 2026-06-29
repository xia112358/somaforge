# Repository data layout

This document describes the data that is visible in the remote GitHub repository
versus data that must stay local or external. It is intentionally about the repo
state, not a full local workstation dump.

## Tracked in git

These are small enough and useful enough to keep in the repository:

- `configs/climbing_scenes.json`: scene-level climbing configuration.
- `configs/motion_matched/*.json`: motion/terrain/contact-force manifests used
  by WBT training and eval commands.
- `configs/motion_matched/terrain_obj_cache/*/*.obj`: small terrain meshes
  referenced by the committed manifests.
- `scripts/*motion_matched*.py`, `scripts/*contact_force*.py`,
  `scripts/*climbing*.py`: reproducible manifest and contact-force helpers.
- `scripts/gmvq_ref/`: GMVQ/ref integration notes and workspace checks.
- `docs/data-policy.md`, `docs/gmvq-ref-pipeline.md`,
  `docs/cleanup-scope.md`: current project scope and data rules.

## Not tracked in git

These must remain local, ignored, or stored externally:

- `OmniRetarget_Dataset/`: clean policy-ready source motions and retargeted
  motion datasets.
- `data/`: generated contact-force demos, motion viewer exports, and rollout
  derived datasets.
- `tmp/`: experiments, GMVQ segments/checkpoints/decoded refs, diagnostics,
  plots, CSVs, and scratch scripts.
- `logs/`, `logs_eval/`, `runs/`, `wandb/`: training/eval outputs and videos.
- `*.npz`, `*.pt`, `*.pth`, `*.ckpt`, `*.onnx`, `*.pdf`: generated arrays,
  checkpoints, model exports, and large copied documents.

## GMVQ climb00 index

The committed machine-readable index is:

```text
scripts/gmvq_ref/climb00_data_index.json
```

It records the expected local paths and known data hazards for the first GMVQ
ref pipeline:

- clean ref source: `OmniRetarget_Dataset/data/holosoma_motions_50hz/...`
- cut source: `motion_edit/data/workbench/raw_contact_29_cut_summary.json`
- rollout contact metadata: `tmp/rollout_ref_contact_points_29/...`
- terrain object: `configs/motion_matched/terrain_obj_cache/climb_00/...`

The index is for validation and documentation. It does not make those external
datasets part of the GitHub repository.

## Known climb00 issue

The current `motion_edit` cut summary for `climb_00_z_scale_1.0` ends at frame
919 while the clean source ref has 1005 frames. The tail `919..1005` must be
handled deliberately as one of:

- a final primitive,
- a policy-eval suffix copied directly from the clean ref, or
- excluded hold/settle metadata.

Do not silently extend the last decoded GMVQ frame and call it clean data.

## Rollout data rule

Rollout-derived files contain actual policy state and tracking error. They may
provide contact/force metadata, but their motion fields must not replace the
clean ref fields for `ref -> code -> ref` training.
