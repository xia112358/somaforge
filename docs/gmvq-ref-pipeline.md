# GMVQ Ref Pipeline

This repo is the integration layer for policy/runtime work. Keep `motion_edit` and
`gmvq-vae` as separate repositories, and use this repo to pin the data protocol,
paths, manifests, and evaluation commands.

## Repository Roles

- `motion_edit`: contact/anchor editing and cut boundary export.
- `gmvq-vae`: generic VQ/VAE model code and training utilities.
- `holosoma_newton`: IsaacLab/Newton policy environment, motion manifests,
  policy eval, visualization, and glue scripts.

Do not copy the source trees into each other. Use local paths, editable installs,
or submodules only after the interfaces are stable.

## Ref Data Contract

The VAE training target is the policy-ready Holosoma reference itself:

- `joint_pos`: root xyz + root quat wxyz + joint positions
- `joint_vel`: root linear velocity + root angular velocity + joint velocities
- `body_pos_w`
- `body_quat_w`: wxyz in npz, converted by the motion loader
- `body_lin_vel_w`
- `body_ang_vel_w`
- `joint_names`
- `body_names`
- `fps`

The decoder should output these same fields. Do not run FK after the decoder.
FK belongs only to offline data preparation if a source motion is missing body
fields.

## Clean Source Ref

For `climb_00`, the clean ref source is:

```text
/home/xiaz/holosoma_isaaclab3_newton/OmniRetarget_Dataset/data/holosoma_motions_50hz/climb_00_z_scale_1.0.npz
```

The rollout contact-force file is not a clean ref source:

```text
tmp/rollout_ref_contact_points_29/motions/climb_00_rollout_ref_contact_force.npz
```

It contains actual policy rollout state (`root_pos`, `dof_pos`, `body_pos_w`,
etc.) and therefore includes tracking error. It may be used for contact/force
metadata, but must not overwrite the reference motion fields listed above.

## Cut Boundaries

`motion_edit` cut summaries can provide segment boundaries, but the `motion_path`
inside a cut summary may point at rollout-derived data. For VAE ref training,
always override the source motion with the clean source ref.

For the current `climb_00` cut summary, the exported cut frames end at frame 919
while the clean source motion has 1005 frames. Decide explicitly whether the tail
`919..1005` is:

- a valid final primitive,
- hold/settle metadata to keep outside VAE training, or
- a policy-eval-only suffix copied from the clean source ref.

Do not silently pad/extend the last decoded frame and treat that as clean data.

## Relative Encoding

Relative encoding is only for world-position stability:

- subtract the segment anchor root xyz from `joint_pos[:, 0:3]`
- subtract the segment anchor root xyz from `body_pos_w`
- leave joint angles, velocities, and quaternions in their policy ref semantics

The original lengths and masks remain part of the segment dataset so padded
frames do not contribute to reconstruction loss.

## Current Validated Result

The chain below has been validated as an initial end-to-end inference path:

```text
clean source ref
-> motion_edit cut segments
-> GMVQ encoder/code/theta
-> GMVQ decoder full ref
-> Holosoma policy eval
```

Using the clean source ref, the decoded full ref ran strict policy eval for 1102
recorded steps. The earlier 16-frame `bad_tracking` failure was caused by using
rollout state as ref.

## Local Setup

Copy `scripts/gmvq_ref/climb00_orig_z1.env.example` to a local ignored env file
if needed, or export the variables in your shell.

Then run:

```bash
python3 scripts/gmvq_ref/check_workspace.py
```

This only checks paths and data consistency; it does not train or launch Isaac.
