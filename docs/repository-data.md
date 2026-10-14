# Repository data layout

This document describes the data that is visible in the remote GitHub repository
versus data that must stay local or external. It is intentionally about the repo
state, not a full local workstation dump.

## Physical separation

The code checkout is `/home/xiaz/somaforge`; local runtime data is stored in the
sibling `/home/xiaz/somaforge-data/current`. The checkout's `runtime/current`
is a relative directory symlink to `../../somaforge-data/current`. Existing
manifests, launch recipes, and root `data`, `logs`, `tmp` aliases keep their
logical paths, without copying or relabeling their inputs. Motion Edit's
`packages/motion_edit/data` link uses the same external tree.
The asset manifest explicitly declares `external_roots: ["runtime/current"]`.
Resolution verifies the declared directory's real target and preserves asset hash
checks. Motion Edit mounts that physical directory under its logical resource URL
while retaining each static mount's normal path and symlink boundary checks.

Code, configs, baseline recipes and the authoritative robot assets remain
versioned in the checkout. Python environments remain under
`runtime/environments` because installed scripts and packages contain absolute
paths. Data backup and code backup are separate operations; code-only Git clones
need the external data restored and the directory link created before use.

Migration and runtime checks are recorded in
`runtime/current/archives/data_code_separation_20261010/`.

## Tracked in git

These are small enough and useful enough to keep in the repository:

- `configs/assets_manifest.json`: canonical robot and terrain asset registry.
- `configs/training_pipeline_manifest.json`: stage-level training data contract.
- `configs/motion_matched/README.md`: local runtime manifest layout.
- `configs/motion_matched/terrain_obj_cache/*/*.obj`: small terrain meshes
  referenced by the committed manifests.
- `scripts/*motion_matched*.py`, `scripts/*contact_force*.py`: reproducible
  manifest and contact-force helpers.
- `packages/generator/`: Predictor and Infiller implementations.
- `packages/contact_solver/`: contact optimization and research.
- `packages/climb00_pipeline/`: import/CLI aliases for historical reproduction only.
- `baselines/current.json`: current Predictor baseline pointer.
- `baselines/predictor_v1_latest_20261010/`: current recipe and recorded results.
- `baselines/archives.json`: historical recipe and comparison records, retained for reproduction.
- `docs/data-policy.md`,
  `docs/cleanup-scope.md`: current project scope and data rules.

## Not tracked in git

These must remain local, ignored, or stored externally:

- `OmniRetarget_Dataset/`: clean policy-ready source motions and retargeted
  motion datasets.
- `data/`: generated contact-force demos, motion viewer exports, and rollout
  derived datasets.
- `tmp/`: temporary diagnostics and disposable outputs only. Required inputs,
  persistent build caches and frozen launch records live under formal runtime
  categories. The 2026-10-10 migration ledger is
  `runtime/current/archives/preserved_inputs_20261010/migration.json`.
- `runtime/current/{motions,models,manifests,generated}/`: formal data and models.
- `logs/`, `logs_eval/`, `runs/`, `wandb/`: training/eval outputs and videos.
- `*.npz`, `*.pt`, `*.pth`, `*.ckpt`, `*.onnx`, `*.pdf`: generated arrays,
  checkpoints, model exports, and large copied documents.

## Predictor/Infiller input manifests

The canonical 29-motion source manifest is generated locally at:

```text
runtime/current/manifests/omniretarget_baseline_29.json
```

Each motion entry binds the source trajectory, Newton-canonicalized trajectory,
terrain ID, source hash, motion hash, and kinematics provenance. Predictor/Infiller and Motion
Edit derive their own manifests from this source rather than maintaining a
second machine-specific data index.

- raw retarget source: `runtime/current/omniretarget/robot-terrain/`
- canonical no-force motion: `runtime/current/motions/`
- derived Motion Edit and Predictor/Infiller data: paths declared by their stage manifests
- terrain assets: entries resolved through `configs/assets_manifest.json`

## Historical climb00 data issue

The historical `motion_edit` cut summary for `climb_00_z_scale_1.0` ends at frame
919 while the clean source ref has 1005 frames. The tail `919..1005` must be
handled deliberately as one of:

- a final primitive,
- a policy-eval suffix copied directly from the clean ref, or
- excluded hold/settle metadata.

Do not silently extend the last generated frame and call it clean data.

## Rollout data rule

Rollout-derived files contain actual policy state and tracking error. They may
provide contact/force metadata, but their motion fields must not replace the
clean ref fields for clean-reference reconstruction training.
