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
→ PyRoki trajectory IK with Newton full-body penetration barriers
  and active foot/hand/knee signed-distance similarity
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

The current reproduction solved all 1005 frames and had no unresolved semantic
or contact targets. Maximum environment penetration was 1.122 mm, of which
0.453 mm was deeper than the source reference. Contact target error was
0.545 mm mean / 23.019 mm max; semantic target error was 9.311 mm mean /
90.952 mm max. Maximum filtered self-collision penetration was 0.988 mm.

The collision objective is layered. Newton checks every unfiltered robot
collision body, including all hip-pitch/roll/yaw geometry. Every body receives
a one-sided no-new-penetration barrier. Physical foot, hand, and knee bodies
receive an additional priority multiplier when they are not the active
reference body. Active contact tracking remains restricted to the mature
six-part contract:

```text
LF / RF  -> left/right ankle_roll_link
LH / RH  -> left/right sphere_hand_link
LK / RK  -> left/right knee_link
```

For those six active reference bodies, the contact patch target, signed-depth
similarity, and deeper-than-reference weight are unchanged. Other bodies never
become contact targets: they are only prevented from penetrating. No separate
hip-protrusion Laplacian node or IK target is used because the full
`hip_pitch_link` collision mesh is already covered by Newton.

## 1. Prepare the low-jitter pose authority

The task keeps the learned rollout's full-body pose shape, but removes the
high-frequency kinematic jitter before editing. This filtered motion is only
the pose/IK authority. Contact timing, local patches, collision depth, and
recorded actuator torques continue to come from the unfiltered force rollout.

```bash
cd /home/xiaz/somaforge

ROLL_OUT=/home/xiaz/somaforge/runtime/current/motions/newton_contact_force/climb_00_rollout_ref_contact_force.npz
PLAN_TEMPLATE=/home/xiaz/somaforge/tmp/climb00_augmentation_matrix/height_110/plans/climb_00_height_1p100.json
RUN_DIR="$PWD/tmp/height110_soft_signed_distance_v2"
POSE_DIR="$RUN_DIR/reference"
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
cd /home/xiaz/somaforge
export SOMAFORGE_ROOT=/home/xiaz/somaforge
export PYTHONPATH="$PWD/packages/motion_edit:$PWD/packages/somaforge_core:$PYTHONPATH"

RUN_DIR="$PWD/tmp/height110_soft_signed_distance_v2"
DERIVED_PLAN="$RUN_DIR/reference/climb_00_height_1p100_clean6hz.json"

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
The final motion must report:

```text
environment_collision_backend = newton_soft_signed_distance_integrated_frame_ik
environment_collision_contract = source_rollout_soft_signed_distance_similarity
environment_collision_fullbody_deeper_weight_multiplier = 4
environment_collision_contact_capable_deeper_weight_multiplier = 4
environment_collision_active_contact_deeper_weight_multiplier = 1
least_squares_failure_count = 0
unresolved_semantics = []
unresolved_contacts = []
```

The canonical output contract is:

```text
joint_pos        [1005, 36]
joint_vel        [1005, 35]
body_pos_w       [1005, 53, 3]
body_quat_w      [1005, 53, 4]
body_lin_vel_w   [1005, 53, 3]
body_ang_vel_w   [1005, 53, 3]
joint_names      [29]
body_names       [53]
```

All numeric arrays must be finite. The body poses must equal direct Newton FK
of `joint_pos`. The file must carry the canonical `robot_asset_json` and
direct-Newton kinematics provenance, and must not carry stale source
`contact_force_part_w`, `contact_force_provenance_json`, or `raw_contact_*`.
Files in `work/` are diagnostic intermediates; they are not the final motion.

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
POLICY_DIR="$RUN_DIR/policy_finetune"

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

## 6. Regression and UI checks

Run the source regression in `env_somaforge`:

```bash
PYTHONPATH=packages/motion_edit:packages/somaforge_core:src/holosoma \
SOMAFORGE_ROOT=/home/xiaz/somaforge \
conda run --no-capture-output -n env_somaforge pytest -q \
  packages/motion_edit/tests \
  packages/somaforge_core/tests \
  src/holosoma/holosoma/agents/modules/tests/test_censored_normal.py \
  src/holosoma/holosoma/agents/ppo/tests/test_kl_early_stop_ppo.py
```

The retained main reproduction passes 357 tests plus 3 subtests. Launch the
current single-port editor and use its recent list for registered motions:

```bash
PYTHONPATH=packages/motion_edit:packages/somaforge_core \
conda run --no-capture-output -n env_somaforge \
  python -m motion_edit.cli contact-editor --port 8094
```

Before admitting a generated reference, inspect the complete motion in the
editor/player: the root and joint order must be correct, the timeline must
advance through all frames, and no quaternion-order, body-mapping, foot-pose,
or contact-phase discontinuity may be visible.
