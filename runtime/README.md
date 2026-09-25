# Runtime data

`current/` contains outputs created with the canonical G1 sphere-hand asset.
`legacy_wrong_urdf/` contains preserved data and configuration produced before
the asset contract was enforced. Legacy artifacts must not be used for
training, evaluation, Motion Edit generation, or Predictor/Infiller training.

The tracked manifest at `configs/assets_manifest.json` is the source of truth
for robot, terrain, motion, model, and generated-asset locations. New files
must be placed under the corresponding `current/` category and referenced by
an asset manifest or a derived manifest carrying its asset IDs and hashes.
Do not add direct absolute paths to project configs.

Current categories are `current/motions`, `current/terrains`,
`current/models`, `current/manifests`, and `current/generated`.

Canonical identity:

- asset: `g1_29dof_spherehand_v1`
- URDF SHA256: `6d79140d335157ad026d24b79be6fbb161c997c01c3ffc37bcca282dc2240696`
- XML SHA256: `877ad16b5f32fcc971f21d85f0cfbf9ef3c1d5b67667b68fe2fc871aa872bd62`
- URDF/mesh bundle SHA256: `d798925cd916e994a47c70ee30ea5f537f000a825c1c66aa914bbe434f60c199`
