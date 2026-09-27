# Runtime data

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
`current/models`, `current/manifests`, and `current/generated`.

Canonical identity is resolved by `somaforge_core.robot_assets` and recorded in
`configs/assets_manifest.json`. Do not copy fingerprints into documentation;
they become stale when the authoritative robot/mesh bundle changes.

`data`, `logs` and `tmp` at the repository root are symlinks into
`current/holosoma/`. Cleaning their contents changes the actual runtime files.
