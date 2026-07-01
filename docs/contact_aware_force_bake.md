# Contact-aware augmentation with prescribed contact-force baking

This workflow extends contact-anchor motion augmentation with a force-reference
postprocess. It is designed for force-aware tracking policies that expect a
part-level reference contact force channel.

The force stage is **not** a rollout. It uses prescribed playback:

```text
for each frame t:
  set qpos/qvel/qacc from the generated reference
  solve contacts with the selected backend
  read contact forces
  aggregate them to parent contact parts
  do not call step / do not integrate / do not feed forces back into the body
```

The generated force is therefore a baked reference signal for training, not a
claim that the reference motion is a dynamically closed-loop rollout.

## Install

MuJoCo is optional and only needed by the prescribed MuJoCo backend:

```bash
uv pip install --python .venv/bin/python -e ".[force]"
```

For UI work, install both extras:

```bash
uv pip install --python .venv/bin/python -e ".[viewer,force]"
```

## One-step command

Use this after producing a `ContactEditPlan` from the contact editor:

```bash
motion-edit-contact-aware-augment \
  --plan data/workbench/climb00_surface_edits.json \
  --output-motion data/motions/generated/climb00_farther_force.npz \
  --output-contact-layer contact/climb00_farther_force \
  --output-segment-layer candidates/climb00_farther_force \
  --output-motion-version-id climb00_farther_force \
  --force-mujoco-model /path/to/g1_mujoco.xml \
  --force-solve-mode forward \
  --overwrite
```

This runs:

```text
ContactEditPlan
  -> lte_fullbody / batch_contact_laplacian geometry generation
  -> fullbody IK output with joint_pos
  -> prescribed contact-force solve
  -> output npz with force reference channels
```

Use `--force-solve-mode inverse` only when the qpos/qvel/qacc sequence is stable
enough for inverse dynamics contact queries. The default `forward` mode is more
forgiving for early debugging.

## Force-only command

If a generated motion already exists and only needs force channels:

```bash
motion-edit-bake-force \
  --motion data/motions/generated/climb00_farther.npz \
  --output-motion data/motions/generated/climb00_farther_force.npz \
  --mujoco-model /path/to/g1_mujoco.xml \
  --solve-mode forward \
  --overwrite
```

To write back into the same npz, pass `--in-place` instead of `--output-motion`.

## Output fields

The force bake writes canonical parent-part channels:

```text
contact_force_part_order:      [P]
contact_force_part_mask:       [T, P]
contact_force_part_position_w: [T, P, 3]
contact_force_part_force_w:    [T, P, 3]
motion_edit_force_metadata:    JSON scalar
```

The default parent-part order is:

```text
left_foot, right_foot, left_hand, right_hand, left_knee, right_knee
```

If the motion already has `contact_force_part_order`, that order is preserved.
If the motion has `contact_force_part_mask`, it gates the solved forces so that
inactive intended contacts stay zero.

## Metadata contract

`motion_edit_force_metadata` records:

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
```

If `motion_edit_generation_metadata` already exists, the force metadata is also
inserted under `contact_force_bake`.

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
Increase `--force-assignment-max-distance` only after checking the contact overlay.

## Current limitations

- The MuJoCo backend is prescribed-state only; it does not run a stabilizing
  controller and does not integrate state.
- The force reference is part-level, not raw pair-level. This is intentional for
  force-aware tracking reward stability.
- Isaac/Newton prescribed backends are not implemented yet. If the training
  reward is very sensitive to simulator-specific force statistics, add the same
  backend interface for the training simulator.
- The generated force is a reference/load signal, not a proof of dynamic
  feasibility. Use metadata and downstream reward gating for low-confidence
  segments.
