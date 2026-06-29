# holosoma_newton

Research workspace for IsaacLab3/Newton whole-body tracking on climbing motions. This repository is the training and simulator-integration side of the current project: motion/contact references are prepared externally, then consumed here for WBT training, contact-force-aware rewards, and GMVQ/tokenized-reference experiments.

This is no longer maintained as a full upstream Holosoma framework mirror. Legacy upstream components unrelated to the current WBT climbing workflow should be removed or kept only when they are still required by active code paths.

## Active scope

- IsaacLab3/Newton setup and Kit/headless experiences.
- G1 whole-body tracking for climbing motions.
- Motion-matched climbing manifests and scene configuration.
- Contact-force demo extraction, smoothing, and manifest generation.
- WBT command, observation, reward, termination, replay, eval, and train logic.
- GMVQ/tokenized-reference integration points.
- PPO experiments used by the WBT workflow.

## Kept but not cleaned in this pass

`src/holosoma_retargeting/` is intentionally left untouched for now. It may still contain useful upstream retargeting assets or scripts, but it is not the primary focus of the current cleanup.

## Related repositories

- `motion_edit`: contact-anchor motion editing, ContactEditPlan generation, and LTE-style motion augmentation.
- `gmvq-vae`: GMVQ/VAE/token representation learning and export artifacts for this training stack.

## Repository map

```text
apps/                         IsaacLab3/Newton Kit experience files
configs/climbing_scenes.json  Climbing scene definitions
configs/motion_matched/       Motion/terrain/contact-force manifests
docs/                         Project notes, data policy, and training recipes
scripts/                      Setup, manifest, contact-force, and training helpers
src/holosoma/                 Active WBT training code
src/holosoma_retargeting/     Kept unchanged for now
```

## Setup

```bash
bash scripts/setup_isaaclab3_newton.sh
source scripts/source_isaaclab3_newton_setup.sh
pip install -e src/holosoma
```

## Current workflow

```text
motion_edit / external preprocessing
  -> climbing motion + contact/terrain manifests
  -> holosoma_newton configs/motion_matched
  -> WBT command/reward/observation/termination
  -> train/eval/replay in IsaacLab3/Newton
  -> optional GMVQ/tokenized reference experiments
```

## Cleanup policy

See `docs/data-policy.md`, `docs/repository-data.md`, and `docs/cleanup-scope.md` before adding large data, upstream framework leftovers, or new simulator/deployment code. Generated training outputs should stay local and under ignored paths such as `tmp/`, `logs/`, `runs/`, `wandb/`, or external storage.
