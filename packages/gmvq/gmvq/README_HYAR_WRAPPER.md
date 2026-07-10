# HyAR Wrapper over Residual GMVQ

This module adds a HyAR-style latent action wrapper on top of the learned
residual GMVQ atom-skill tokenizer.

The nested codec is:

```text
high-dimensional segment x
  -> frozen GMVQ encoder
  -> hybrid code (k, theta)
  -> HyAR conditional VAE encoder
  -> compact latent action z_h
  -> HyAR conditional VAE decoder
  -> reconstructed hybrid code (k, theta_hat)
  -> frozen GMVQ decoder
  -> reconstructed segment x_hat
```

## Reference Ideas

The implementation follows the modeling structure from:

```text
HyAR: Addressing Discrete-Continuous Action Reinforcement Learning via Hybrid Action Representation
```

Relevant HyAR ideas:

- discrete action embedding table;
- conditional VAE for continuous action parameters conditioned on the discrete
  action embedding and optional state;
- compact and decodable latent action representation;
- optional nearest/classifier-based latent-to-discrete retrieval;
- optional dynamics prediction loss for semantically smooth action latents.

GMVQ provides the structured hybrid action:

```text
k      = GMVQ discrete Gaussian ball id
theta  = residual coordinate inside that Gaussian ball
```

HyAR learns:

```text
(k, theta) <-> z_h
```

## GMVQ Latent vs HyAR Latent

GMVQ latents:

```text
z_e: encoder latent for segment tokenization
z_q: quantized/reconstructed GMVQ latent used by the segment decoder
```

HyAR latent:

```text
z_h: compact latent action representation of the hybrid code (k, theta)
```

These are intentionally separate. `z_h` is not a replacement for GMVQ `z_e` or
`z_q`; it is a second-stage action representation on top of the structured
GMVQ code.

## Training-Time Flow

```text
x
  -> FrozenGMVQCodec.encode_segment(x)
  -> k, theta
  -> HyARActionVAE.encode(k, theta, state_optional)
  -> z_h
  -> HyARActionVAE.decode(k, z_h, state_optional)
  -> theta_hat
  -> FrozenGMVQCodec.decode_hybrid(k, theta_hat)
  -> x_hat
```

Known-`k` reconstruction is the default. This is the stable supervised HyAR
training mode:

```text
q_phi(z_h | theta, embedding(k), state_optional)
p_psi(theta_hat | z_h, embedding(k), state_optional)
```

The decoder always conditions on `embedding(k)`. It does not reconstruct theta
from `z_h` alone.

## RL-Time Flow

Mode A, default:

```text
obs -> policy -> k, z_h
k, z_h -> HyAR decoder -> theta
k, theta -> GMVQ decoder -> segment
```

Mode B, optional:

```text
obs -> policy -> z_h
z_h -> classifier -> k
k, z_h -> HyAR decoder -> theta
k, theta -> GMVQ decoder -> segment
```

Mode B is implemented for research usage, but the current training path does not
depend on it for reconstruction.

## Loss

```text
hyar_loss =
  theta_recon_loss
+ beta_kl * kl_loss
+ beta_x * x_recon_loss
+ beta_vel * velocity_loss
+ beta_k * k_cls_loss
+ beta_dyn * dynamics_loss
+ beta_latent * latent_norm
```

Terms:

- `theta_recon_loss`: MSE between `theta_hat` and frozen-GMVQ `theta`.
- `kl_loss`: VAE KL from `q(z_h | theta, k)` to `N(0, I)`.
- `x_recon_loss`: full segment MSE after decoding through frozen GMVQ.
- `velocity_loss`: temporal velocity MSE for the reconstructed segment.
- `k_cls_loss`: optional classifier diagnostic from `z_h`/`z_mu` to `k`.
- `dynamics_loss`: optional HyAR semantic smoothness term when `state` and
  `next_state` are available.
- `latent_norm`: optional norm regularization.

## Not a U-Net

There is no skip connection from the segment encoder to the segment decoder.
The bottleneck is preserved:

```text
x -> (k, theta) -> z_h -> theta_hat -> x_hat
```

The only path to `x_hat` is through `z_h`, the known or recovered `k`, and the
frozen GMVQ decoder.

## Train

```bash
python -m gmvq.train_hyar_wrapper \
  --gmvq_checkpoint runs/gmvq_true_baseline_n25d3_codes4_sigma05/checkpoint.pt \
  --data data/cram_proto/true_baseline_n25d3/cram_true_baseline_model_3150_segments.npz \
  --save_dir runs/hyar_true_baseline \
  --hyar_latent_dim 4 \
  --action_emb_dim 16 \
  --batch_size 256 \
  --steps 2000 \
  --beta_kl 0.01
```

The CLI default keeps `beta_kl=1e-3`, matching the prototype defaults. For the
current true-baseline checkpoint, `beta_kl=0.01` is the recommended compact
baseline because it keeps `z_h` smaller with little reconstruction loss.

With optional state conditioning:

```bash
python -m gmvq.train_hyar_wrapper \
  --gmvq_checkpoint path/to/gmvq/checkpoint.pt \
  --data path/to/data_with_states.npz \
  --use_state_conditioning \
  --state_key states \
  --next_state_key next_states
```

The dataset may be `.npz` or `.pt` and must contain:

```text
segments: [N, T, D]
```

Optional:

```text
states:      [N, state_dim]
next_states: [N, state_dim]
```

## Analyze

```bash
python -m gmvq.analyze_hyar_wrapper \
  --hyar_checkpoint runs/hyar_true_baseline/checkpoint.pt \
  --data data/cram_proto/true_baseline_n25d3/cram_true_baseline_model_3150_segments.npz
```

Outputs:

```text
k.npy
theta.npy
z_h.npy
theta_hat.npy
x_hat_subset.npy
k_logits.npy
z_h_pca_by_k.png
theta_vs_theta_hat.png
per_code_theta_error_hist.png
```
