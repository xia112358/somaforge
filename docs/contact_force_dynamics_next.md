# Contact force dynamics next steps

This note is the handoff point for continuing the contact-force augmentation
work. It separates the useful compatibility work already in the branch from the
next formal change: making force dynamics part of the contact representation.

## Current branch

```text
feature/transfer-local-contact-laplacian
```

The branch is not `main`. Runtime data under `data/` and generated Holosoma
artifacts are local only and should not be committed.

## Kept changes

These changes are still useful and should stay in the branch:

```text
motion_edit/contact_force/schema.py
motion_edit/contact_force/__init__.py
motion_edit/generation/contact_force_bake.py
motion_edit/contact_force/cli.py
motion_edit/generation/contact_aware.py
motion_edit/generation/contact_aware_cli.py
tests/test_generation_contact_force_bake.py
tests/test_contact_force_cli.py
tests/test_contact_aware_generation.py
tests/test_contact_aware_cli.py
```

They provide the WBT-compatible force reference contract:

```text
contact_force_part_order = LF, RF, LH, RH, LK, RK
contact_force_part_w:          [T, 6, 3]
contact_force_part_mask:       [T, 6]
contact_force_part_position_w: [T, 6, 3]
contact_force_part_force_w:    [T, 6, 3]
```

They also add:

```text
policy-ref validator
geom/body part maps for MuJoCo backend assignment
contact-aware CLI force argument passthrough
metadata contract for force reference writers
```

The following geometry/contact changes should also stay because the target
force representation is six-part, including knees:

```text
motion_edit/contact/jitter.py
motion_edit/contact_laplacian/backend.py
motion_edit/contact_laplacian/solver.py
motion_edit/generation/lte_fullbody.py
motion_edit/generation/pyroki_fullbody_ik.py
```

## Removed cleanup

The experimental parallel batch command was removed from `motion_edit/cli.py`:

```text
batch-generate-lte-augmentations-parallel
```

Reason: it was a batch throughput helper, not part of the contact-force dynamics
design, and it had no focused tests.

## Current limitation

The prescribed MuJoCo force bake is only a diagnostic/compatibility backend.
It is not the final force-generation path.

Do not treat this as the target model:

```text
augmented geometry -> prescribed MuJoCo contact solve -> final force
```

It can produce unphysical spikes when the generated trajectory penetrates or the
MuJoCo model/terrain contact geometry does not match the training simulator. The
observed multi-box spike around `16936N` is an example of this failure mode.

## Target abstraction

The next formal model should treat contact as a dynamic signal, not a binary
label:

```text
contact = geometry consistency + phase/load process + force envelope
```

A useful internal representation is:

```text
ContactPhase:
  part
  start_frame
  end_frame
  surface_id
  position_w[t]
  normal_w[t]
  contact_strength[t]
  force_envelope_w[t]
```

This should be extracted from the existing contact masks, surface bindings,
edited anchors, and source force references.

## Implemented first pass

The first optimization-level hook is now implemented:

```text
source contact force
-> ContactLoadProfile over local contact phase
-> ContactHandleSpec.load_profile
-> contact residual weights sampled inside the solver
```

Important detail:

```text
ContactLoadProfile.phase is local to one contact handle.
Per-frame weights are only a compiled solver-side result.
```

Implemented files:

```text
motion_edit/contact/dynamics.py
motion_edit/contact_laplacian/schema.py
motion_edit/contact_laplacian/residuals.py
motion_edit/contact_laplacian/backend.py
motion_edit/contact_laplacian/solver.py
motion_edit/contact_laplacian/transfer_solver.py
motion_edit/generation/lte_fullbody.py
```

Current behavior:

```text
source motion contact_force_part_w/contact_force_part_force_w
  + contact_force_part_order
  + optional contact_force_part_mask
  + anchor surface normal
-> normal-load envelope per contact phase
-> mean-one solver contact residual multiplier s(phi)
```

If no force channel is present, generation behaves as before. If force exists
but the load is numerically zero over a contact phase, the profile falls back to
uniform strength for that handle rather than dropping the contact constraint.
The normal case preserves the handle's average stiffness:

```text
mean(s(phi)) = 1
```

This means force changes where a contact is strongest inside its local phase,
not the total amount of contact constraint applied to that handle.

## Retarget writer status

The first retarget writer is now implemented:

```text
motion_edit/contact_force/retarget.py
motion_edit/generation/contact_force_bake.py::bake_retargeted_contact_forces_for_motion
```

It performs:

```text
source force ref
-> split source contact masks into phases
-> split target/augmented contact masks into phases
-> match phases per LF/RF/LH/RH/LK/RK part
-> resample source force over target local phase
-> write CanonicalContactForceField / WBT six-part fields
```

The compatibility entry point also dispatches retarget mode:

```text
bake_prescribed_contact_forces_for_motion(..., solve_mode="retarget")
```

The writer accepts target contact-layer normals:

```text
--target-contact-layer data/layers/contact/...
--target-motion-id <motion_id>
```

When provided, anchor `surface_normal` values are compiled to per-frame,
per-part target normals and used during force retargeting. If no target contact
layer is provided, the writer uses `default_up` and records that fallback in
metadata. Source normals are still `default_up` unless explicitly provided by a
future source-contact-dynamics layer.

## Proposed module layout

Add the contact dynamics layer here:

```text
motion_edit/contact/dynamics.py
```

Responsibilities:

```text
ContactPhase / ContactDynamics dataclasses
mask -> touchdown/liftoff phases
phase strength/envelope helpers
metadata serialization for npz/json
```

Force retargeting lives here:

```text
motion_edit/contact_force/retarget.py
```

Responsibilities:

```text
source force ref -> source ContactDynamics
augmented motion + edited anchors -> augmented ContactDynamics
source force envelope -> augmented local contact frame
output CanonicalContactForceField
```

Keep file writing and WBT compatibility in:

```text
motion_edit/generation/contact_force_bake.py
```

The retarget writer entry point is separate from prescribed solve:

```text
bake_retargeted_contact_forces_for_motion(...)
```

## Retargeting rules

The retarget path must not copy source force directly.

Minimum acceptable behavior:

```text
1. Match parts by LF/RF/LH/RH/LK/RK.
2. Split source contact masks into phases.
3. Extract source force envelope per phase.
4. Use augmented contact anchors/body positions for force positions.
5. Use augmented surface normals for normal direction. [implemented for target contact layer]
6. Project tangential force into the augmented contact tangent plane.
7. Preserve/load-normalize the source envelope shape.
8. Clamp and smooth forces to avoid prescribed-solve spikes.
9. Write metadata that says this is retargeted force, not rollout force.
```

Metadata should distinguish:

```text
force_source = retargeted_contact_force
force_applied_to_body = false
integrated = false
source_force_ref = plan.source_motion_path
source_phase_count = ...
retarget_phase_count = ...
force_norm_max = ...
```

## CLI direction

The formal path is one command. It uses `ContactEditPlan.source_motion_path` as
the full source reference and retargets force from that same source motion:

```bash
motion-edit generate-ref \
  --plan data/workbench/climb00_surface_edits.json \
  --output-motion data/motions/generated/climb00_force_retarget.policy_ref_v1.npz \
  --output-contact-layer contact/climb00_force_retarget \
  --overwrite
```

## First smoke target

Use one local fullbody generated motion first:

```text
data/motions/generated/raw29_radius005_n8_full/climb_00_z_scale_1.0_surface_jitter_0000.npz
```

Expected output properties:

```text
joint/body trajectory remains from the augmented motion
force is retargeted, not copied and not policy-rollout-derived
contact_force_part_w shape is [1005, 6, 3]
force max is finite and bounded
WBT validator passes
metadata identifies retargeted_contact_force
```

## Tests to keep running

Fast focused test set:

```bash
.venv/bin/python -m unittest \
  tests.test_contact_force_cli \
  tests.test_generation_contact_force_bake \
  tests.test_contact_aware_cli \
  tests.test_contact_aware_generation
```

Before merging:

```bash
.venv/bin/python -m unittest discover -s tests
```
