# Runtime data

Runtime data is physically separate from the code checkout:

```text
/home/xiaz/somaforge/                 code, configs, documentation and robot assets
/home/xiaz/somaforge-data/current/    motions, models, logs, caches and archives
runtime/current                     -> ../../somaforge-data/current
runtime/environments/               Python environments; not relocated
```

Keep the sibling data directory when moving or backing up this workstation's
checkout. A code-only Git clone does not contain the local datasets or models;
restore the data directory and create the `runtime/current` link before running
data-dependent commands. Do not create a second populated `runtime/current`
directory. Configurations retain their existing logical paths through the link.
`configs/assets_manifest.json` explicitly declares `runtime/current` in
`external_roots`. Asset resolution and Motion Edit browser resource mounts share
this declaration; undeclared external directories remain outside the allowed
roots. Browser URLs retain the `/repo/runtime/current/...` prefix.
The 2026-10-10 relocation preserves all file identities and protected input
hashes; its ledger is `current/archives/data_code_separation_20261010/`.

`current/` holds formal runtime assets and experiments. Directory location alone
is not certification: every training input still requires the canonical asset,
current contact semantics and its own acceptance record. Historical wrong-asset
artifacts remain ineligible even if located here.

The tracked manifest at `configs/assets_manifest.json` is the source of truth
for robot, terrain, motion, model, and generated-asset locations. New files
must be placed under the corresponding `current/` category and referenced by
an asset manifest or a derived manifest carrying its asset IDs and hashes.
Do not add direct absolute paths to project configs.

Current categories are `current/motions`, `current/terrains`,
`current/models`, `current/manifests`, `current/generated`, persistent
`current/cache`, and historical `current/archives`. Required inputs and caches
are never kept in `tmp/`; that directory is for temporary outputs only.

Canonical identity is resolved by `somaforge_core.robot_assets` and recorded in
`configs/assets_manifest.json`. Do not copy fingerprints into documentation;
they become stale when the authoritative robot/mesh bundle changes.

`data`, `logs` and `tmp` at the repository root are symlinks into
`current/holosoma/`. Cleaning their contents changes the actual runtime files.
