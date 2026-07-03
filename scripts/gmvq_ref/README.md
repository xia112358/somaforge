# GMVQ Ref Integration Scripts

This directory is for glue scripts owned by `holosoma_newton`.

Keep generic model code in `gmvq-vae` and editor/cut tooling in `motion_edit`.
Scripts here may call those repos, but should not duplicate their source code.

Expected local layout:

```text
/home/xiaz/
  motion_edit/
  gmvq-vae/
  holosoma_isaaclab3_newton/
```

Use `check_workspace.py` before running training/eval commands to catch the most
common data mixup: using rollout state as the VAE ref source.

The default paths and known data hazards are recorded in:

```text
scripts/gmvq_ref/climb00_data_index.json
```

Environment variables still override the index defaults for local machines.

Standard augmented-ref and selector chain:

```text
motion_edit generated raw npz
-> canonicalize_policy_ref.py
-> policy_ref_v1 npz
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

`canonicalize_policy_ref.py` is the boundary between motion generation and GMVQ.
GMVQ inputs and decoded outputs should be `policy_ref_v1`, not solver-specific
or contact-specific intermediate NPZ files.

For G1 WBT, the canonical policy ref shape is:

```text
joint_pos: [T, 36] = root xyz + root quat + 29 dof
joint_vel: [T, 35] = root lin vel + root ang vel + 29 dof vel
```

Do not train on either old augmented source:

- `joint_vel: [T, 36]` packs have the wrong policy loader schema.
- rollout-ref contact-force sources contain policy tracking error and are not
  clean reference motions.

Build augmentation inputs from the official motion manifest first:

```bash
conda run -n env_isaaclab python scripts/gmvq_ref/prepare_clean_source_aug_inputs.py
```

This writes clean `policy_ref_v1` source refs and a cut summary whose
`motion_path` fields point at those refs:

```text
tmp/gmvq_play/clean_source_aug_full/clean32_sources/manifest.json
tmp/gmvq_play/clean_source_aug_full/raw_contact_29_cut_summary_clean32_source.json
```

Then generate contact-surface jitter plans in `motion_edit` from the rebased cut
summary, generate motions, canonicalize them back to `policy_ref_v1`, and rebuild
the segment pack:

```bash
cd /home/xiaz/motion_edit
./motion-edit generate-contact-jitter-plans \
  --cut-summary /home/xiaz/holosoma_isaaclab3_newton/tmp/gmvq_play/clean_source_aug_full/raw_contact_29_cut_summary_clean32_source.json \
  --output-dir /home/xiaz/holosoma_isaaclab3_newton/tmp/gmvq_play/clean_source_aug_full/contact_jitter_plans_raw29_large_mixed_n64_clean32 \
  --samples-per-contact 64 \
  --radius 0.12 \
  --sampler mixed \
  --mode reject \
  --overwrite

./motion-edit batch-generate-lte-augmentations-parallel \
  --plan-manifest /home/xiaz/holosoma_isaaclab3_newton/tmp/gmvq_play/clean_source_aug_full/contact_jitter_plans_raw29_large_mixed_n64_clean32/manifest.json \
  --output-motion-dir /home/xiaz/holosoma_isaaclab3_newton/tmp/gmvq_play/clean_source_aug_full/generated_raw29_large_mixed_n64_clean32 \
  --fullbody-solver batch_contact_laplacian \
  --workers 8 \
  --overwrite \
  --allow-draft \
  --allow-free \
  --continue-on-error
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
conda run -n env_isaaclab python scripts/gmvq_ref/decode_selector_ref.py
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
  --manifest configs/motion_matched/motion_edit_raw29_large_mixed_n64_force_ref_manifest.json \
  --groups-per-shard 4 \
  --overwrite
```

The standard force-ref finetune entry is the sharded zero-start wrapper:

```bash
python scripts/train_motion_edit_force_sharded.py \
  --checkpoint logs/WholeBodyTracking/20260608_150410-g1_29dof_wbt_contact_force_6part_hotspot_multimotion_probe20_fixed_probe-locomotion/model_19999.pt \
  --shard-index configs/motion_matched/motion_edit_raw29_large_mixed_n64_force_ref_manifest_shards/shard_index.json \
  --num-envs 4096 \
  --total-iterations 2000 \
  --learning-rate 1e-4 \
  --save-interval 100 \
  --name motion_edit_raw29_force_ref_sharded_env4096_ft2000_from19999
```

For a speed probe, run one shard for a few iterations:

```bash
python scripts/train_motion_edit_force_sharded.py \
  --checkpoint logs/WholeBodyTracking/20260608_150410-g1_29dof_wbt_contact_force_6part_hotspot_multimotion_probe20_fixed_probe-locomotion/model_19999.pt \
  --shard-index configs/motion_matched/motion_edit_raw29_large_mixed_n64_force_ref_manifest_shards/shard_index.json \
  --num-envs 4096 \
  --iterations-per-shard 10 \
  --num-shards 1 \
  --save-interval 10 \
  --name motion_edit_raw29_force_ref_shard_benchmark
```
