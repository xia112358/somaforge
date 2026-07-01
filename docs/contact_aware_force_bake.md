# Contact-aware augmentation force references

This document describes the current force-reference compatibility layer for
contact-aware augmentation. The long-term direction is to make contact dynamics
part of the augmentation representation itself:

```text
contact phase + surface binding + contact strength + force envelope
```

The code in this document is still useful because force-aware tracking policies
expect part-level reference force channels in the generated motion files. The
prescribed MuJoCo backend is a diagnostic/compatibility backend, not the final
force-retargeting model.

## Prescribed backend semantics

The prescribed backend is **not** a rollout. It uses prescribed playback:

```text
for each frame t:
  set qpos/qvel/qacc from the generated reference
  solve contacts with the selected backend
  read contact forces
  aggregate them to parent contact parts
  do not call step / do not integrate / do not feed forces back into the body
```

The generated force is therefore a baked reference signal for inspection or
training experiments, not a claim that the reference motion is a dynamically
closed-loop rollout. On terrain/model mismatches, prescribed contact solve can
produce unphysical spikes; those outputs should be treated as diagnostics.

## Install

MuJoCo is optional and only needed by the prescribed MuJoCo backend:

```bash
uv pip install --python .venv/bin/python -e ".[force]"
```

For UI work, install both extras:

```bash
uv pip install --python .venv/bin/python -e ".[viewer,force]"
```

## Formal WBT ref command

Use this after producing a `ContactEditPlan` from the contact editor. The plan's
`source_motion_path` is the single source reference: it supplies the original
trajectory, contact masks/positions, and contact-force channels. There is no
separate public `--source-force-ref` input in the formal path.

```bash
motion-edit generate-ref \
  --plan data/workbench/climb00_surface_edits.json \
  --output-motion data/motions/generated/climb00_farther_force.policy_ref_v1.npz \
  --output-contact-layer contact/climb00_farther_force \
  --output-segment-layer candidates/climb00_farther_force \
  --output-motion-version-id climb00_farther_force \
  --overwrite
```

This runs:

```text
ContactEditPlan
  -> lte_fullbody / batch_contact_laplacian geometry generation
  -> fullbody IK output with joint_pos
  -> contact-phase force retarget from plan.source_motion_path
  -> WBT policy-ref validation
  -> output npz with WBT force reference channels
```

This mode keeps the augmented kinematic trajectory unchanged after IK. It splits
source and target contact masks into local contact phases, resamples source
force envelopes over each target phase, writes bounded six-part force channels,
and records `force_source = retargeted_contact_force`.

The generated target contact layer is passed back into force retargeting, so the
writer reads anchor `surface_normal` values and rotates the source normal load
into the target contact surface frame. If no target contact layer is available,
it falls back to the default up normal and records that fallback in metadata.

Use `--no-check-policy-ref` only for debugging malformed intermediate files. The
formal command validates the final npz against the 2026-06-08 WBT
contact-force policy reference contract by default.

## Diagnostic backends

The prescribed MuJoCo backend and force-only bake helpers remain available as
Python internals for debugging simulator/contact mismatches. They are not the
formal augmentation path. Use them only when inspecting a generated fullbody
motion against a particular MJCF, and keep their output out of training unless
the metadata and WBT validator agree.

## Body/geom part maps

The MuJoCo backend first tries explicit name maps, then falls back to built-in
name aliases, then falls back to nearest `contact_force_part_position_w` when it
is available. Use maps when the real G1 MJCF has project-specific geom/body
names that do not contain tokens like `left_foot`, `right_hand`, or `left_knee`.

Map files are JSON objects whose keys are MuJoCo names and whose values are
canonical contact parts:

```json
{
  "left_toe_collision": "left_foot",
  "right_palm_collision": "right_hand",
  "left_knee_capsule": "left_knee"
}
```

The formal `generate-ref` path does not need these maps because it retargets the
force from the source full motion instead of querying MuJoCo contacts.

## WBT output fields

Force reference writers should produce canonical parent-part channels:

```text
contact_force_part_order:      [P]
contact_force_part_w:          [T, P, 3]
contact_force_part_mask:       [T, P]
contact_force_part_position_w: [T, P, 3]
contact_force_part_force_w:    [T, P, 3]
motion_edit_force_metadata:    JSON scalar
```

`motion-edit generate-ref` writes WBT policy-compatible force channels for the
contact-force checkpoint trained on 2026-06-08. The same field contract should
be used by future force-retarget/contact-dynamics writers:

```text
contact_force_part_order = LF, RF, LH, RH, LK, RK
contact_force_part_w     = field consumed by holosoma MotionLoader
```

`contact_force_part_force_w` is kept as an explicit motion_edit alias with the
same values. Internal diagnostics can still disable WBT compatibility, but the
formal `generate-ref` command always writes the WBT six-part contract.

If the motion has `contact_force_part_mask`, prescribed solve uses it to gate
solved forces so that inactive intended contacts stay zero. Retargeted force
writers should treat the mask as a contact-phase signal, not just a binary
postprocess gate.

## Metadata contract

For the prescribed backend, `motion_edit_force_metadata` records:

```text
force_source = prescribed_motion_contact_solve
state_policy = prescribed_qpos_qvel_qacc
force_applied_to_body = false
integrated = false
solve_mode = forward | inverse
used_sample_count
unknown_sample_count
missing_intended_contact_frames
force_norm_max
policy_ref_compat = wbt_contact_force_6part | none
```

For the retarget backend, metadata records:

```text
force_source = retargeted_contact_force
state_policy = contact_phase_force_retarget
force_applied_to_body = false
integrated = false
source_force_ref = plan.source_motion_path
source_phase_count
retarget_phase_count
matched_phase_count
unmatched_target_phase_count
force_norm_max
normal_source
```

If `motion_edit_generation_metadata` already exists, the force metadata is also
inserted under `contact_force_bake`.

`motion-edit generate-ref` validates the output against the 2026-06-08 WBT
contact-force policy reference contract by default. The check requires:

```text
joint_pos: [T, 36] for G1 29-DoF refs
joint_vel: [T, 35]
contact_force_part_w: [T, 6, 3]
contact_force_part_order: LF, RF, LH, RH, LK, RK
```

## Failure interpretation

High `missing_intended_contact_frames` means the intended contact mask says a
body part should be in contact but the backend did not return a contact assigned
to that part. Common causes are:

```text
- edited contact point is slightly off the surface
- MuJoCo model geometry does not match the source robot geometry
- body/geom names cannot be mapped to the canonical part order
- contact margin/solver settings are too strict
```

High `unknown_sample_count` means the backend produced contact samples that could
not be assigned to a parent part by body/geom name or nearest `contact_force_part_position_w`.
Add explicit body/geom maps first. Increase `--force-assignment-max-distance`
only after checking the contact overlay.

## Current limitations

- The MuJoCo backend is prescribed-state only; it does not run a stabilizing
  controller and does not integrate state.
- The first retarget backend uses contact masks and part-level forces. If no
  explicit surface normals are provided, it records `normal_source=default_up`;
  pass the target contact layer to use anchor `surface_normal` values.
- The force reference is part-level, not raw pair-level. This is intentional for
  force-aware tracking reward stability.
- Isaac/Newton prescribed backends are not implemented yet. If the training
  reward is very sensitive to simulator-specific force statistics, add the same
  backend interface for the training simulator.
- The generated force is a reference/load signal, not a proof of dynamic
  feasibility. Use metadata and downstream reward gating for low-confidence
  segments.
