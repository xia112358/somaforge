# Climb00 Height 1.10 Production Pipeline

This is the retained production route for the first height-edited policy:

```text
validated ContactEditPlan
→ 6 Hz zero-phase rollout pose cleanup
→ direct Newton FK pose canonicalization
→ derived plan with separate pose/contact authorities
→ task-variant surface translation
→ contact-Laplacian semantic curves
→ Newton local contact patches
→ PyRoki trajectory IK with Newton soft signed-distance similarity
→ direct Newton FK canonical motion
→ frame-boundary Newton force replay
→ clean WBT policy reference
→ single-motion policy fine-tune
→ full-start acceptance evaluation
```

The reference implementation is the run named
`height110_soft_signed_distance_v2`. Its collision contract preserves the
source rollout's per-body/per-surface soft signed distance instead of enforcing
an arbitrary penetration depth:

```text
similarity weight       25
deeper-than-reference   100
maximum refinements       1
```

The recorded successful run solved all 1005 frames, had no unresolved semantic
or contact targets, and reduced excess penetration to 0.049 mm.

## 1. Prepare the low-jitter pose authority

The task keeps the learned rollout's full-body pose shape, but removes the
high-frequency kinematic jitter before editing. This filtered motion is only
the pose/IK authority. Contact timing, local patches, collision depth, and
recorded actuator torques continue to come from the unfiltered force rollout.

```bash
ROLL_OUT=/home/xiaz/somaforge/runtime/current/motions/newton_contact_force/climb_00_rollout_ref_contact_force.npz
PLAN_TEMPLATE=/home/xiaz/somaforge/tmp/climb00_augmentation_matrix/height_110/plans/climb_00_height_1p100.json
POSE_DIR="$PWD/tmp/climb00_rollout_cleanup_trial"
POSE_SEED="$POSE_DIR/cutoff_6hz_qseed.npz"
POSE_MOTION="$POSE_DIR/climb_00_rollout_clean_6hz_newton.npz"
DERIVED_PLAN="$POSE_DIR/climb_00_height_1p100_clean6hz.json"

python scripts/prepare_motion_edit_pose_shape.py \
  --rollout "$ROLL_OUT" \
  --output-seed "$POSE_SEED" \
  --plan-template "$PLAN_TEMPLATE" \
  --output-plan "$DERIVED_PLAN" \
  --canonical-motion "$POSE_MOTION" \
  --cutoff-hz 6

python scripts/canonicalize_motion_newton_direct.py \
  --input "$POSE_SEED" \
  --output "$POSE_MOTION" \
  --device cpu
```

The derived plan changes only `source_motion_path` and records the
`kinematic_cleanup` provenance. Its `metadata.contact_force_source_path`
continues to point at `ROLL_OUT`.

## 2. Generate edited kinematics

```bash
cd /home/xiaz/somaforge/tmp/pr1-newton-contact-taskspace-spec
export SOMAFORGE_ROOT=/home/xiaz/somaforge
export PYTHONPATH="$PWD/packages/motion_edit:$PWD/packages/somaforge_core:$PYTHONPATH"

RUN_DIR="$PWD/tmp/height110_soft_signed_distance_v2"

conda run --no-capture-output -n env_somaforge python \
  scripts/generate_contact_aware_edited_motion.py \
  --plan "$DERIVED_PLAN" \
  --output "$RUN_DIR/final_motion.npz" \
  --intermediate-dir "$RUN_DIR/work" \
  --ik-conda-env env_somaforge \
  --newton-device cpu \
  --overwrite
```

The default collision settings with the derived clean6hz plan reproduce the
retained v2 configuration. Running the unmodified template plan directly uses
the older motion asset as pose authority and is not the v2 production route.
The
final motion must report:

```text
environment_collision_backend = newton_soft_signed_distance_integrated_frame_ik
environment_collision_contract = source_rollout_soft_signed_distance_similarity
least_squares_failure_count = 0
unresolved_semantics = []
unresolved_contacts = []
```

## 3. Calculate force with frame-boundary replay

Force is never copied or migrated from the source motion. The source rollout
supplies recorded actuator torques as a dynamic reference. At every 20 ms
control boundary the edited trajectory state is made authoritative, Newton
advances four continuous 5 ms substeps, and the fourth substep supplies the
force sample.

Set the replay output and the rollout recording before invoking the normal
IsaacLab3-Newton experiment configuration:

```bash
export SOMAFORGE_FRAME_BOUNDARY_REPLAY_OUTPUT="$RUN_DIR/frame_state_playback_edited_newton.npz"
export SOMAFORGE_FORCE_ROLLOUT_RECORDING=/home/xiaz/somaforge/runtime/current/rollout/newton_contact_force/recordings/climb_00_attempt_01_eval_recording.npz
export SOMAFORGE_FORCE_ROLLOUT_ENV_ID=0

source /home/xiaz/somaforge/scripts/source_isaaclab3_newton_setup.sh

python scripts/replay_motion_newton_frame_boundary.py \
  exp:g1-29dof-wbt-contact-force \
  --headless \
  --device cuda:0 \
  --training.num-envs 1 \
  --command.setup-terms.motion-command.params.motion-config.motion-manifest \
  "$RUN_DIR/isaaclab_replay_manifest.json" \
  --terrain.terrain-term.motion-matched-manifest \
  "$RUN_DIR/isaaclab_replay_manifest.json" \
  --terrain.terrain-term.spawn.randomize-tiles False \
  --terrain.terrain-term.spawn.xy-offset-range 0.0
```

Frame zero is marked invalid because no preceding 20 ms interval exists.
Self-collision force and raw contacts are not written into the policy motion.

## 4. Build the policy reference

```bash
POLICY_DIR="$PWD/tmp/height110_policy_finetune"

python scripts/build_newton_force_policy_reference.py \
  --kinematics "$RUN_DIR/isaaclab_canonical/newton_replay_input.npz" \
  --replay-force "$RUN_DIR/frame_state_playback_edited_newton.npz" \
  --rollout-recording "$SOMAFORGE_FORCE_ROLLOUT_RECORDING" \
  --terrain /home/xiaz/somaforge/tmp/climb00_augmentation_matrix/height_110/terrain/multi_boxes_z_scale_1.100.obj \
  --output-motion "$POLICY_DIR/climb00_height110_frame_state_force_policy_ref.npz" \
  --output-manifest "$POLICY_DIR/manifest.json" \
  --motion-id climb00_height110
```

The output includes canonical kinematics and calculated eight-part Newton
force. It intentionally excludes `raw_contact_*`, stale force provenance, and
object arrays.

## 5. Fine-tune and evaluate

```bash
python scripts/train_motion_edit_policy_finetune.py \
  --headless \
  --device cuda:0 \
  --checkpoint /path/to/source/model_08000.pt \
  --motion-manifest "$POLICY_DIR/manifest.json" \
  --output-dir "$POLICY_DIR/train_logs" \
  --project Height110PolicyFinetune \
  --name climb00_height110_model08000_single_500iter \
  --num-envs 1024 \
  --iterations 500 \
  --save-interval 100
```

Run `scripts/eval_motion_edit_acceptance.py` from frame zero against the
resulting checkpoint. File-level acceptance is not sufficient: also inspect
the policy execution's phase-specific root height, knee flexion, contact masks,
force timing, and force magnitude.
