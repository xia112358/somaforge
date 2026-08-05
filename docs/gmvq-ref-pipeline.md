# GMVQ Ref Pipeline

> This is the detailed preparation/history document. The accepted production
> artifact set and the only current online GMVQ/WBT run command are maintained
> in [`climb00-pairwise48-production.md`](climb00-pairwise48-production.md).
> Paths under `tmp/gmvq_play` in this document are historical examples, not
> production inputs.

SomaForge is the integration workspace for Motion Edit, GMVQ, and Holosoma
policy/runtime work. Their source packages remain separate Python modules, but
the canonical data protocol, manifests, runtime bundles, and evaluation
commands are versioned together in this repository.

## Repository Roles

- `motion_edit`: contact/anchor editing and cut boundary export.
- `gmvq-vae`: generic VQ/VAE model code and training utilities.
- `holosoma_newton`: IsaacLab/Newton policy environment, motion manifests,
  policy eval, visualization, and glue scripts.

Do not bypass the package interfaces by copying implementation files between
modules. Shared robot identity and motion contracts belong in
`somaforge_core`.

## Current runtime boundary

The accepted production bundle documented in
[`climb00-pairwise48-production.md`](climb00-pairwise48-production.md) uses the
embedded GMVQ codec, code selector, theta selector, duration prior,
transition mask, and start-conditioned decoder. It is the only promoted online
runtime.

The newer `current_frame_future` path is a development path for predicting one
complete absolute future segment from the current scan and robot state. It does
not integrate predicted pose increments. Its whole-segment continuity and
closed-loop terminal recovery are under evaluation, so checkpoints under
`tmp/` must not replace `runtime/current/models/climb00_pairwise48/gmvq.pt`.

## Ref Data Contract

The VAE training target is `policy_ref_v1`: the policy-ready Holosoma reference
itself. See `docs/policy-ref-v1.md`.

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

All generated or augmented motions must pass through:

```bash
python3 scripts/gmvq_ref/canonicalize_policy_ref.py \
  --input generated_raw.npz \
  --output generated.policy_ref_v1.npz
```

before GMVQ segment preparation.

## Clean Source Ref

This document describes the data contract and historical examples. The old
motion-matched manifests referenced below were retired with the wrong-URDF
data. New runs must start from `configs/training_pipeline_manifest.json` and
write derived manifests under `runtime/current/manifests/`.

The clean ref sources come from the canonical Newton motion manifest:

```text
runtime/current/manifests/omniretarget_baseline_29.json
```

For `climb_00`, that clean source is:

```text
runtime/current/motions/climb_00_z_scale_1.0.npz
```

The rollout contact-force file is not a clean ref source:

```text
tmp/rollout_ref_contact_points_29/motions/climb_00_rollout_ref_contact_force.npz
```

It contains actual policy rollout state (`root_pos`, `dof_pos`, `body_pos_w`,
etc.) and therefore includes tracking error. It may be used for contact/force
metadata, but must not overwrite the reference motion fields listed above.

Prepare the clean 32-body policy-ref sources and a rebased cut summary with:

```bash
cd /home/xiaz/somaforge
conda run -n env_somaforge python scripts/gmvq_ref/prepare_clean_source_aug_inputs.py
```

Outputs:

```text
tmp/gmvq_play/clean_source_aug_full/clean32_sources/manifest.json
tmp/gmvq_play/clean_source_aug_full/raw_contact_29_cut_summary_clean32_source.json
```

## Cut Boundaries

`motion_edit` cut summaries provide segment boundaries, but the `motion_path`
inside an old cut summary may point at rollout-derived data. For VAE ref training
and augmentation, always use the clean-source rebased cut summary.

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

The current standard chain is:

```text
official motion-matched manifest
-> prepare_clean_source_aug_inputs.py
-> clean32 policy_ref_v1 sources
-> clean-source rebased motion_edit cut summary
-> motion_edit ContactEditPlan / surface jitter
-> generate-ref
-> edited kinematic references
-> Newton validation rollout / canonical 8-part force references
-> shared segment table / valid-mask segment packer
-> packages/gmvq train_gmvq
-> packages/gmvq decode_motion_edit_ref
-> policy_ref_v1 decoded motion
-> SomaForge motion-matched manifest
-> policy eval / offline reconstruction eval
```

Smoke commands that exercise the full data interface:

```bash
cd /home/xiaz/somaforge/packages/motion_edit
./motion-edit export-manifest \
  --source candidates/probe_chain_current \
  --output data/exports/manifests/probe_chain_current.json

cd /home/xiaz/somaforge/packages/gmvq
conda run -n env_somaforge python -m gmvq.prepare_motion_edit_segments \
  --motion-edit-manifest /home/xiaz/somaforge/packages/motion_edit/data/exports/manifests/probe_chain_current.json \
  --motion-root /home/xiaz/somaforge/packages/motion_edit \
  --output data/motion_edit/probe_chain_current_ref_t512.npz \
  --feature-key joint_pos \
  --feature-key joint_vel \
  --feature-key body_pos_w \
  --feature-key body_quat_w \
  --feature-key body_lin_vel_w \
  --target-len 512 \
  --min-len 16 \
  --max-len 512

conda run -n env_somaforge python -m gmvq.train_gmvq \
  --data data/motion_edit/probe_chain_current_ref_t512.npz \
  --save_dir runs/gmvq_motion_edit_probe_chain_smoke \
  --encoder_type bigru_masked \
  --decoder_type time \
  --num_codes 8 \
  --latent_dim 16 \
  --batch_size 4 \
  --steps 2 \
  --device cpu

conda run -n env_somaforge python -m gmvq.decode_motion_edit_ref \
  --checkpoint runs/gmvq_motion_edit_probe_chain_smoke/checkpoint.pt \
  --data data/motion_edit/probe_chain_current_ref_t512.npz \
  --output /home/xiaz/somaforge/tmp/gmvq_play/probe_chain_current_gmvq_smoke_ref.npz \
  --latents-output /home/xiaz/somaforge/tmp/gmvq_play/probe_chain_current_gmvq_smoke_latents.npz \
  --device cpu

cd /home/xiaz/somaforge
python3 scripts/gmvq_ref/build_event_token_plan.py \
  --motion-edit-manifest /home/xiaz/somaforge/packages/motion_edit/data/exports/manifests/probe_chain_current.json \
  --latents tmp/gmvq_play/probe_chain_current_gmvq_smoke_latents.npz \
  --output tmp/gmvq_play/probe_chain_current_event_token_plan.json

python3 scripts/gmvq_ref/check_data_layout.py \
  --manifest tmp/gmvq_play/probe_chain_current_gmvq_smoke_manifest.json
```

`event_token_plan` stores the fixed `code/theta` table plus segment metadata.
The currently validated smoke path switches on valid length / padding boundary.
Contact-event switching should only be enabled when the target event table comes
from the same segmentation used to train GMVQ.

The 2-step smoke model is only a chain check; its reconstruction quality is not
meaningful. Use a real training run before policy evaluation.

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

## Selector Decode Evaluation

After large `motion_edit` contact-surface jitter augmentation, the current
learned selector path is:

```text
policy_ref_v1 augmented motions
-> full-ref relative T=192 segment pack
-> GMVQ 16-code checkpoint
-> offline height/proprio selector dataset
-> code selector
-> theta selector
-> GMVQ decoder
-> policy_ref_v1 segment
-> decoded policy_ref_v1 motion npz
-> single-motion manifest
```

The selector dataset is causal at the segment start: height scan plus root and
joint state at the switch frame. It does not include future ref frames. The
current code selector and theta selector checkpoints are evaluated with:

```bash
cd /home/xiaz/somaforge
conda run -n env_somaforge python scripts/gmvq_ref/eval_selector_decode.py
```

The old fixed35 large augmented segment pack fixed the `joint_vel` dimension but
was built from rollout-derived refs:

```text
tmp/gmvq_play/motion_edit_aug_full_ref_relative_t192_raw29_large_mixed_n64_full_fixed35.npz
```

It uses the policy loader contract:

```text
joint_pos: [T, 36]
joint_vel: [T, 35]
feature_dim: 487
```

Do not use it as the final GMVQ training source. Rebuild the large pack from:

```text
tmp/gmvq_play/clean_source_aug_full/generated_raw29_large_mixed_n64_clean32
```

after those generated motions have been canonicalized to `policy_ref_v1`.

Rebuild it with:

```bash
conda run -n env_somaforge python scripts/gmvq_ref/rebuild_augmented_ref_pack.py
```

Historical result on the old `raw29_large_mixed_n64` augmented dataset used a
wrong `joint_vel: [T, 36]` pack (`feature_dim: 488`) and should not be reused as
a valid policy-ref checkpoint:

```text
test_count: 1833
code accuracy: 0.9836
theta MSE with true code: 0.00283
theta MSE with predicted code: 0.00929

oracle GMVQ valid-frame MSE: 0.03037
selector predicted-code valid-frame MSE: 0.03284
```

These values are normalized GMVQ-space MSE over valid frames only. The selector
adds little error beyond the GMVQ decoder itself. When evaluating this path,
align selector samples to the segment pack by row index; `window_indices` is not
a segment-pack row id.

To generate a policy-loadable selector-decoded ref:

```bash
cd /home/xiaz/somaforge
conda run -n env_somaforge python scripts/gmvq_ref/decode_selector_ref.py
python3 scripts/gmvq_ref/check_data_layout.py \
  --manifest tmp/gmvq_play/selector_decoded_refs/climb00_surface_jitter_0000_selector_manifest.json
```

## Local Validation

Validate the source manifest before building any derived GMVQ pack:

```bash
python scripts/gmvq_ref/check_data_layout.py \
  --manifest runtime/current/manifests/omniretarget_baseline_29.json
```

This checks manifest paths only; the motion schema and asset fingerprints are
validated again by the stage loaders.
