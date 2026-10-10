# Repository maintenance

## Maintained code and entrypoints

| Area | Implementation | Entrypoint / tests |
| --- | --- | --- |
| Assets, FK, contact semantics | `packages/somaforge_core` | `scripts/check_asset_manifest.py`, package tests |
| Motion editing and augmentation | `packages/motion_edit` | `motion-edit generate-ref`, Contact Editor, package tests |
| Predictor and Infiller | `packages/generator` | `python -m generator.train_full1000_position`, package tests |
| Contact optimization | `packages/contact_solver` | package API; diagnostics under `research/`; package tests |
| Newton WBT | `src/holosoma` | `train_agent.py`, `eval_agent.py`, `replay.py`, `run_sim.py` |
| Retargeting | `src/holosoma_retargeting` | separate retargeting environment |

`climb00_pipeline` contains historical module aliases only. Current source and
ordinary tests import the owning package directly. The compatibility identity
test is retained for old snapshots and checkpoint reproduction. Historical
experiments are not additional current training entrypoints.

The maintained full1000 trainer no longer imports training scripts from `tmp/`:
dataset preparation lives in `generator.training_data`, owned Newton workers in
`generator.scene_workers`, and the optional isolated-gradient audit in
`generator.research.isolated_gradients`. Dataset splits and training equations
were preserved when extracting these helpers. Query checkpoint, source scene
manifest and model inspection paths are explicit configuration fields.

The maintained trainer defaults match the user-designated
[`predictor.v1_latest.20261010`](../baselines/predictor_v1_latest_20261010/README.md):
v1, loaded-material207_joint_v12 data and keep-patch weight1. Configuration,
dependencies and the fixed step1000 comparison checkpoint are registered there.
New scratch runs do not load that checkpoint; use a fresh output directory.
Historical data variants are not approved merely by repository cleanup.

## Data and historical records

- Formal motion/dataset archives: `runtime/current/motions/`.
- Formal checkpoints: `runtime/current/models/`.
- Asset, data and acceptance indexes: `runtime/current/manifests/` and the
  tracked registries in `configs/`.
- Disposable diagnostics: project `tmp/`.
- Frozen experiment source/configuration: `baselines/`; do not rewrite snapshots
  to look like current code.

Root `data`, `logs` and `tmp` are symlinks into `runtime/current/holosoma`.
`tmp/` still contains referenced historical weights, datasets and scene records.
Its name is not evidence that its contents can be deleted.

The 2026-09-28 inventory checked the previous Predictor snapshot. That pretrained
recipe was moved to the system recycle bin after explicit confirmation on
2026-10-02. That scratch recipe and control500 were archived in place on
2026-10-10 when the user designated `baselines/predictor_v1_latest_20261010/`
as the current training and analysis baseline. The current pointer and archive
index are `baselines/current.json` and `baselines/archives.json`; historical
weights, data, source snapshots and launch records remain intact.
The historical direct-infiller corpus remains intact;
that experiment is documented in `climb00_direct_infiller_baseline.md` and is
not a newly approved training corpus.

The local retention registry is
`runtime/current/manifests/repository_cleanup_20260928.json`.
It records protected reproduction dependencies, not training admission.
Tracked upstream motion/examples remain pending dependency-specific review;
the repository audit lists them instead of silently removing them.

## Verification

Static audit, including modified and untracked source:

```bash
python3 scripts/check_repository.py --output tmp/repository_audit.json
source scripts/source_somaforge.sh
python scripts/check_asset_manifest.py
python scripts/check_training_manifest.py
```

Package and contact-pipeline tests require the project's Newton environment:

```bash
source scripts/source_isaaclab3_newton_setup.sh
OMP_NUM_THREADS=2 python -m pytest -p no:cacheprovider \
  packages tests/test_newton_contact_pipeline.py -q
```

IsaacLab/CUDA tests require the host environment. Passing static/unit checks
does not establish trajectory acceptance or policy execution quality.

## Cleanup record and constraints

35 tests were relocated from the compatibility package to their implementation
owners: 25 Generator, 9 Contact Solver and 1 shared-core test. Existing modified
tests were moved with their changes, not reset to Git versions.

The explicitly approved `.pytest_cache`, `.ruff_cache`, root `__pycache__`, empty
`source/`, and retired `generation/ik_subprocess.py` were moved to the system
recycle bin. Additional removals require an enumerated confirmation. Caches may
be recreated by normal tooling.

Diagnostics, movement records, extracted-source fingerprints and test results
are under `tmp/repository_cleanup_20260928/`. No training process is stopped by
cleanup; no dataset/checkpoint is deleted, silently relabeled, or promoted to a
new baseline. Changes are left reviewable in the working tree until a separate
commit/push request.

Verification for this cleanup: 755 package/contact-pipeline tests and 3 subtests
passed in the host Newton environment. The static audit parsed 870 Python files
with no errors; asset and training manifests passed; the maintained trainer's
`--help` completed without starting training. Full WBT training and physical
rollouts were not run as part of this repository organization.

## Non-predictor entrypoint retirement

The following Motion Edit commands and handlers are now removed, including their
hidden registrations: `workbench`, `workbench-action`, `import-manual-cuts`,
`export-cutter-segments`, `accept`, `reject`, `list-layer`,
`migrate-layer-to-canonical`, `import-lte-catalog`, and `force-retarget`.
`export-manifest` and `export-split-npz` require `--motion-version-id`; the old
layer `--source` path is rejected both by parsing and direct handler calls.
The old workbench server, LTE catalog adapter and adapter test were moved to the
system recycle bin after explicit confirmation.

The Predictor was outside the 2026-09-28 retirement pass. Its pretrained
initialization and previous baseline were subsequently retired on 2026-10-02;
the earlier inventory is historical evidence, not a current executable recipe.
Shared geometry/storage helpers required by the Contact Editor remain in use.

### Unified web visualization (2026-09-28)

The supported browser entry is `motion-edit contact-editor`. `--motion-id` opens
registered editing/playback; `--review` opens canonical NPZ sequences or JSON pose
comparison reports in the same Three.js page. See
[Motion Edit playback documentation](../packages/motion_edit/README.md#unified-playback-and-experiment-review).
Retargeting no longer embeds a Viser process or exposes `retargeter.visualize` /
`retargeter.debug`. Simulation Kit rendering remains controlled by AppLauncher.
Historical contact flags in diagnostic reports are explicitly unverified, and
read-only NPZ playback does not infer contact from distances or force thresholds.
Seven old viewer/configuration files and three superseded web bundles were moved
to the system trash after the user confirmed the itemized list. No standalone
Viser fallback entrypoint remains in maintained source. Predictor code remains frozen.
