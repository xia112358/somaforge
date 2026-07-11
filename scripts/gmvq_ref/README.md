# GMVQ Ref Integration Scripts

This directory contains SomaForge integration scripts for Newton-validated
Motion Edit references and GMVQ.

Generic model code lives in `packages/gmvq`; editor tooling lives in
`packages/motion_edit`. External repository layouts are unsupported.

Use `check_workspace.py` before running training/eval commands to catch the most
common data mixup: using rollout state as the VAE ref source.

The default paths and known data hazards are recorded in:

```text
scripts/gmvq_ref/climb00_data_index.json
```

Environment variables still override the index defaults for local machines.

Standard augmented-ref and selector chain:

```text
motion_edit generate-ref
-> edited kinematic reference
-> Newton validation rollout and canonical 8-part force reference
-> gmvq-vae prepare_motion_edit_segments / local full-ref segment packer
-> gmvq-vae train_gmvq
-> extract_selector_height_dataset.py
-> train_selector_code.py
-> train_selector_theta.py
-> eval_selector_decode.py
-> selector_runtime.GMVQSelectorRuntime
-> decode_selector_ref.py
-> policy runtime / motion-matched manifest
```

See `docs/gmvq-ref-pipeline.md` for the exact smoke commands and the policy-ref
data contract.

The successful Newton rollout is the production boundary between motion
generation and GMVQ. `generate-ref` alone is not training eligible.
`canonicalize_policy_ref.py` remains a diagnostic converter, but it cannot make
legacy data trustworthy without the canonical robot asset fingerprint.

For G1 WBT, the canonical policy ref shape is:

```text
joint_pos: [T, 36] = root xyz + root quat + 29 dof
joint_vel: [T, 35] = root lin vel + root ang vel + 29 dof vel
```

Do not train on either old augmented source:

- `joint_vel: [T, 36]` packs have the wrong policy loader schema.
- only successful Newton rollout force references with canonical provenance are
  valid force-training inputs.

Build augmentation inputs from the official motion manifest first:

```bash
conda run -n env_holosoma_isaaclab3_newton python scripts/gmvq_ref/prepare_clean_source_aug_inputs.py
```

This writes clean `policy_ref_v1` source refs and a cut summary whose
`motion_path` fields point at those refs:

```text
tmp/gmvq_play/clean_source_aug_full/clean32_sources/manifest.json
tmp/gmvq_play/clean_source_aug_full/raw_contact_29_cut_summary_clean32_source.json
```

Then generate contact-surface jitter plans in `motion_edit` from the rebased cut
summary. Validate each plan, use `generate-ref` to create edited kinematics,
then run the result through Newton before rebuilding the segment pack.

```bash
cd /home/xiaz/somaforge/packages/motion_edit
./motion-edit generate-contact-jitter-plans \
  --cut-summary /home/xiaz/somaforge/tmp/gmvq_play/clean_source_aug_full/raw_contact_29_cut_summary_clean32_source.json \
  --output-dir /home/xiaz/somaforge/tmp/gmvq_play/clean_source_aug_full/contact_jitter_plans_raw29_large_mixed_n64_clean32 \
  --samples-per-contact 64 \
  --radius 0.12 \
  --sampler mixed \
  --mode reject \
  --overwrite

./motion-edit generate-ref \
  --plan /path/to/validated.plan.json \
  --output-motion /home/xiaz/somaforge/packages/motion_edit/data/motions/generated/example.policy_ref_v1.npz \
  --output-contact-layer contact/example \
  --output-segment-layer candidates/example \
  --output-motion-version-id example \
  --register-motion-version \
  --overwrite
```

The old fixed35 pack below fixed dimensions only; it is not the final official
training source because it was built from rollout-derived refs:

```text
tmp/gmvq_play/motion_edit_aug_full_ref_relative_t192_raw29_large_mixed_n64_full_fixed35.npz
```

Use smaller contact jitter, for example 5 cm, when the goal is old-policy sanity
tracking. The 12 cm mixed surface jitter is coverage data for GMVQ/selector and
is not expected to be fully trackable by the old policy without retraining.

`build_event_token_plan.py` creates an optional runtime token plan. The current
stable smoke path uses valid-length / padding boundaries. Contact-event switching
needs a target event table generated from the same segmentation used for GMVQ.

The selector path is now the main learned switch/input path:

```text
height/proprio observation
-> code selector
-> theta selector conditioned on selected code
-> GMVQ decoder
-> policy_ref_v1 segment
```

Use `eval_selector_decode.py` to validate this before policy eval. It compares:

- oracle GMVQ code/theta decode
- selector theta with the true code
- selector-predicted code and theta

Important alignment rule: selector labels and the GMVQ segment pack are aligned
by row order. `window_indices` is window-local metadata, not the row index into
the segment pack.

To produce a policy-loadable decoded ref from selector predictions:

```bash
conda run -n env_holosoma_isaaclab3_newton python scripts/gmvq_ref/decode_selector_ref.py
```

This writes a `policy_ref_v1` npz plus a single-motion manifest under
`tmp/gmvq_play/selector_decoded_refs/`.

## Motion-edit force-ref finetune

Do not finetune directly on the full `raw29_large_mixed_n64_force_ref`
manifest. That manifest contains 1856 full trajectories and creates a multi-GB
GPU motion bank, which makes reference gathers dominate rollout collection.

Build shard manifests once:

```bash
python scripts/gmvq_ref/build_motion_manifest_shards.py \
  --manifest runtime/current/manifests/motion_edit_ref_v1.json \
  --groups-per-shard 4 \
  --overwrite
```

The standard force-ref finetune entry is the sharded zero-start wrapper:

```bash
python scripts/train_motion_edit_force_sharded.py \
  --checkpoint runtime/current/checkpoints/wbt_baseline_29/model.pt \
  --shard-index runtime/current/manifests/motion_edit_ref_v1_shards/shard_index.json \
  --num-envs 4096 \
  --total-iterations 2000 \
  --learning-rate 1e-4 \
  --save-interval 100 \
  --name motion_edit_raw29_force_ref_sharded_env4096_ft2000_from19999
```

The sharded wrapper now keeps the successful hotspot settings by default:
`reset_sampler=hotspot_failure_window`, `start_at_timestep_zero_prob=0.2`,
optimizer state loading, random episode length initialization, and group probes
with 8 probe envs per terrain group. This replaces the expensive per-motion
probe20 setup for motion-edit variants while keeping the change scoped to this
force-ref finetune path.

For a speed probe, run one shard for a few iterations:

```bash
python scripts/train_motion_edit_force_sharded.py \
  --checkpoint runtime/current/checkpoints/wbt_baseline_29/model.pt \
  --shard-index runtime/current/manifests/motion_edit_ref_v1_shards/shard_index.json \
  --num-envs 4096 \
  --iterations-per-shard 10 \
  --num-shards 1 \
  --save-interval 10 \
  --name motion_edit_raw29_force_ref_shard_benchmark
```

The zero-start force-ref wrappers enable load-time motion-order canonicalization
by default. This keeps the change scoped to the motion-edit force-ref finetune
experiment and avoids per-step full-bank body/joint reindexing. To benchmark the
full manifest with this experiment path:

```bash
python scripts/train_motion_edit_force_zero_start.py \
  --checkpoint runtime/current/checkpoints/wbt_baseline_29/model.pt \
  --motion-manifest runtime/current/manifests/motion_edit_ref_v1.json \
  --num-envs 4096 \
  --iterations 10 \
  --save-interval 10 \
  --name motion_edit_raw29_force_ref_full_canonicalize_benchmark
```
