# GMVQ Atom-Skill Tokenizer

This package trains the current `k + theta` residual GM-VQ tokenizer for
humanoid anchor-to-anchor segments.

Default target shape:

```text
x: [B, T, D]
T = 120
D = 14
```

The current CRAM true-baseline proto dataset uses:

```text
x: [B, 25, 3]
```

## Current Architecture

The only retained architecture is:

```text
x -> encoder -> z_e
  -> Gaussian mixture posterior p(k | z_e)
  -> hard code k
  -> theta = (z_e - mu_k) / sigma_k
  -> z_q = mu_k + sigma_k * clamp(theta)
  -> decoder -> x_recon
```

`k` is the discrete atom-skill token. `theta` is the continuous residual
coordinate inside the selected Gaussian component.

The Gaussian codebook has:

```text
mu_k:          [K, latent_dim]
sigma_k:      [K, latent_dim]
log_prior_k:  [K]
```

Token selection uses the full diagonal Gaussian posterior:

```text
log p_k(z_e) =
  log pi_k
  - 0.5 * sum_d [
      (z_e_d - mu_k_d)^2 / sigma_k_d^2
      + log sigma_k_d^2
      + log(2pi)
    ]

p(k | z_e) = softmax(log p_k(z_e))
k = argmax p(k | z_e)
```

This is not RVQ, not plain VQ-VAE, and not pure Gaussian Quant. The codebase is
intentionally focused on residual GM-VQ with explicit `k, theta`.

## References Used

- **VQ-VAE, "Neural Discrete Representation Learning"**: encoder, quantizer,
  decoder structure; straight-through estimator; commitment loss; code usage
  and perplexity diagnostics.
- **GM-VQ, "Gaussian Mixture Vector Quantization with Aggregated Categorical
  Posterior"**: learnable Gaussian component means, diagonal variances, mixture
  posterior, aggregated usage diagnostics.
- **Gaussian Quant / VQ-VAE-from-Gaussian-VAE**: optional KL-in-bits diagnostics
  for residual information rate.
- **GMVAE implementations**: categorical component plus conditional Gaussian
  residual interpretation.
- **QueST**: skill-token workflow: train on chunks, save token/residual arrays,
  inspect code usage and transfer-friendly segment reconstruction.

## Losses

The training objective is:

```text
total =
  recon_loss
+ beta_vel * velocity_loss
+ beta_theta * theta_l2
+ beta_rate * theta_rate
+ beta_commit * commit_loss
+ beta_usage * usage_loss
+ beta_mix * mix_loss
+ beta_balance * balance_loss
+ beta_sep * sep_loss
+ beta_theta_moments * theta_moments
+ beta_sigma * sigma_reg
```

Important terms:

- `recon_loss`: `MSE(x_recon, x)`.
- `velocity_loss`: temporal difference MSE for trajectory smoothness.
- `mix_loss`: Gaussian mixture NLL for `z_e`.
- `theta_l2` and `theta_rate`: keep residual magnitude and bit cost bounded.
- `commit_loss`: VQ-VAE-style commitment to the selected Gaussian mean.
- `usage_loss` / `balance_loss`: anti-collapse only; do not force uniform usage
  when the dataset is naturally biased.
- `sigma_reg` plus `sigma_max`: keep Gaussian balls from becoming too large.
- `sep_loss`: mild center separation to avoid identical components.
- `theta_moments`: per-code residual mean/variance regularization.

Task-specific contact/outcome losses can be plugged into `losses.py` through the
existing hooks.

## Recommended True-Baseline Setup

Current recommended run:

```text
runs/gmvq_true_baseline_n25d3_codes4_sigma05/checkpoint.pt
```

Configuration:

```text
K = 4
latent_dim = 8
theta_clip = 0.5
sigma_max = 0.5
weak usage/balance regularization
```

Observed diagnostics:

```text
MSE          ~= 0.1159
usage hist   = [164, 1014, 284, 266]
perplexity   ~= 3.07
pmax mean    ~= 0.913
sigma mean   ~= 0.433
sigma max    = 0.5
active codes = 4
```

This is a tight, non-uniform set of Gaussian balls. The non-uniformity is
expected for the true-baseline proto distribution; the goal is avoiding collapse,
not making code usage uniform.

## Training

Synthetic:

```bash
python -m gmvq.train_gmvq --synthetic --steps 2000
```

CRAM true-baseline proto:

```bash
python -m gmvq.train_gmvq \
  --data data/cram_proto/true_baseline_n25d3/cram_true_baseline_model_3150_segments.npz \
  --save_dir runs/gmvq_true_baseline_n25d3_codes4_sigma05 \
  --num_codes 4 \
  --latent_dim 8 \
  --t 25 \
  --d 3 \
  --batch_size 256 \
  --steps 2000 \
  --lr 0.0005 \
  --theta_clip 0.5 \
  --sigma_max 0.5 \
  --beta_sigma 0.005 \
  --beta_mix 0.02 \
  --beta_balance 0.05 \
  --beta_sep 0.001 \
  --beta_theta_moments 0.01
```

motion_edit full-body proto refs:

```bash
python -m gmvq.prepare_motion_edit_segments \
  --cut-summary /home/xiaz/motion_edit/data/workbench/raw_contact_29_cut_summary.json \
  --output data/motion_edit/raw_contact_29_cut_joint_pos_t192.npz \
  --feature-key joint_pos \
  --target-len 192 \
  --min-len 16 \
  --max-len 192

python -m gmvq.train_gmvq \
  --data data/motion_edit/raw_contact_29_cut_joint_pos_t192.npz \
  --save_dir runs/gmvq_motion_edit_cut_joint_pos_t192 \
  --num_codes 16 \
  --latent_dim 16 \
  --encoder_type bigru_masked \
  --batch_size 64 \
  --steps 2000
```

Standard motion_edit augmented-ref chain:

```bash
python -m gmvq.prepare_motion_edit_segments \
  --motion-edit-manifest /home/xiaz/motion_edit/data/exports/manifests/probe_chain_current.json \
  --motion-root /home/xiaz/motion_edit \
  --output data/motion_edit/probe_chain_current_ref_t512.npz \
  --feature-key joint_pos \
  --feature-key joint_vel \
  --feature-key body_pos_w \
  --feature-key body_quat_w \
  --feature-key body_lin_vel_w \
  --target-len 512 \
  --min-len 16 \
  --max-len 512

python -m gmvq.train_gmvq \
  --data data/motion_edit/probe_chain_current_ref_t512.npz \
  --save_dir runs/gmvq_motion_edit_probe_chain \
  --num_codes 16 \
  --latent_dim 32 \
  --encoder_type bigru_masked \
  --decoder_type time \
  --batch_size 16 \
  --steps 2000

python -m gmvq.decode_motion_edit_ref \
  --checkpoint runs/gmvq_motion_edit_probe_chain/checkpoint.pt \
  --data data/motion_edit/probe_chain_current_ref_t512.npz \
  --output /home/xiaz/holosoma_isaaclab3_newton/tmp/gmvq_play/probe_chain_current_gmvq_ref.npz \
  --latents-output /home/xiaz/holosoma_isaaclab3_newton/tmp/gmvq_play/probe_chain_current_gmvq_latents.npz
```

The prepared `.npz` keeps the standard padded `segments [N, T, D]` key for
batching and also writes `valid_mask`, `lengths`, segment IDs, motion IDs, frame
ranges, source paths, and active body labels. Training and analysis use
`valid_mask` when present, so padding does not contribute to reconstruction or
velocity losses. To recover the original-length reconstruction from analysis:

```python
recon_i = recon_padded[i, : lengths[i]]
```

Quick test:

```bash
python -m gmvq.quick_synthetic_test
```

## Analysis

```bash
python -m gmvq.analyze_gmvq \
  --checkpoint runs/gmvq_true_baseline_n25d3_codes4_sigma05/checkpoint.pt \
  --data data/cram_proto/true_baseline_n25d3/cram_true_baseline_model_3150_segments.npz \
  --out_dir runs/gmvq_true_baseline_n25d3_codes4_sigma05/analysis
```

The analysis writes:

```text
codes.npy
theta.npy
z_e.npy
z_q.npy
recon_subset.npy
code_usage.png
theta_pca.png
```
