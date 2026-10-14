# Joint policy refinement and executed trajectory collection

Edited motions are kinematic references. This workflow jointly fine-tunes one
existing WBT policy against a reference collection, evaluates every motion, and
collects actual executions from one fixed refined checkpoint. Only individually
accepted collection trials enter the exported dataset.

```text
native source + authored edit plans + explicit source-clock prefix contract
  -> rigid source start and smooth transition to edited targets
  -> contact-aware generation + canonical Newton FK + fresh Newton labels
  -> reference manifest + matched terrains + base checkpoint
  -> prepare and fingerprint inputs
  -> joint PPO refinement (one policy, all references)
  -> repeated frame-zero evaluation per reference
  -> frozen-checkpoint collection for eligible references
  -> per-trial acceptance and unchanged-state extraction
  -> executed-motion manifest + native contact/load observations
```

The controller is `scripts/run_trajectory_refinement.py`. Its implementation
lives in `somaforge_core.trajectory_refinement` and `somaforge_core.rollout_dataset`.
It has no motion-name, collection-size, height or task-specific checkpoint
defaults. The current backend deliberately retains SomaForge's authoritative
G1 asset and Newton/MJWarp contact contract.

Standard batch augmentation requires the source-prefix contract on each plan
or via `generate-ref --source-prefix-config`. Its boundaries belong to that
source's event clock, without fixed angle/frame defaults. Semantic positions and
the root attitude share one source-to-target surface rotation; inconsistent yaw
conditions fail before solving. Root/body velocities come from the solved pose
clock. Preparation pins this recipe and its implementation, so changed recipes
require a fresh collection version. See the [augmentation entrypoint](../packages/motion_edit/README.md#dataset-augmentation).
Old collections remain available for historical comparison; the existing v12
example below is not a newly repaired standard augmentation collection.

Initial-state diagnosis (2026-10-14): an unstable augmented start can force the
policy to recover balance before following the task. Those recovery adjustments
can move the robot away from the reference, trigger tracking termination or
disrupt the intended contact sequence, making the task fail even when the
kinematic reference looks plausible. Check the initial stance, root attitude
and velocities together before attributing early failures to insufficient
training; a rotated reference must rotate its root attitude consistently.

With the same iteration-8800 policy, the diagnosed -10-degree case failed at
frame 51 before repair; three repaired trials completed all 932 frames. The
diagnosed +20-degree case failed at frame 15 in all three original trials;
all three repaired trials completed 932 frames, and two passed all 34 contact
event checks. These comparisons support an initial-state cause for these cases,
not a claim that every failure has this cause or that initial recovery alone
guarantees task acceptance. Abnormal side contacts still prevented dataset
admission. Evidence: project `tmp/trajectory_refinement_diagnostics/` under
`20261014_minus10_source_prefix_v1/validation_summary.json` and
`20261014_plus20_source_prefix/validation_summary.json`.

## Configuration and input adapters

Paths in a workflow configuration are relative to the repository root. Paths
inside input manifests, collection indexes and edit plans are relative to their
declaring file. Absolute paths are accepted for external inputs.

`input.kind` supports:

- `motion_manifest`: `motion_files` with `motion_file`, `terrain_id`, unique
  `motion_name` or `motion_id`, and optional positive `weight`; `terrains` with
  `terrain_id` and `terrain_file`. For contact-event acceptance, each motion also
  supplies `contact_catalog_file`, a Newton label NPZ from which only the explicit
  scene surface catalog is read. An entry's optional `task_contract` supplies its
  own intent contract, supporting different trajectory lengths and tasks in one
  joint training manifest; it overrides the shared `task.contract` default.
- `native_edit_collection`: an index with `motion_files` containing `motion_id`,
  full `motion`, `plan`, and `contacts`. The plan binds its target terrain through
  `metadata.target_terrain_mesh`. Cropped/soft-joined fields and old acceptance
  flags are intentionally not substituted for the full reference.

Both adapters validate the motion's robot and kinematics provenance, finite
state arrays and timing, and build the same canonical motion/terrain manifest.
Reference weights affect joint training; evaluation covers every reference.
The trainer currently reserves three start probes per reference, so
`train.num_envs` must be at least three times the collection size.

All settings are explicit in the configuration: `base_checkpoint`, `output_dir`,
training environment count/additional iterations/save interval, evaluation
attempt count/minimum success rate/seeds/reset noise, collection attempt count/
seeds/reset noise, and the task acceptance contract. Unknown configuration keys
fail validation rather than silently changing behavior.

The example [climb00_joint_v12.json](../configs/trajectory_refinement/climb00_joint_v12.json)
binds the existing full v12 collection (207 references, five terrains) to the
original motion's iteration-6000 WBT checkpoint. Its proposed budget is 3,000
additional PPO iterations, 4,096 environments and a checkpoint every 100
iterations. Evaluation requires 3/3 successful trials per reference; collection
requests ten further trials. These are configurable starting settings, not
measured sufficiency or an instruction to start training. Zero reset noise gives
repeatability checks, not perturbation robustness; use a separate configured
run with explicit reset noise to assess robustness.

## Prepare without GPU work

Select the normal project Python environment. Preparation needs NumPy and the
installed project packages, but does not import or initialize Isaac/Kit/CUDA.
For offline contact extraction/tests use the pinned Newton environment so that
runtime metadata can be checked without launching physics.

```bash
source scripts/source_somaforge.sh
runtime/environments/newton-main-20260914/bin/python -B \
  scripts/run_trajectory_refinement.py \
  --config configs/trajectory_refinement/climb00_joint_v12.json
```

The default stage is `prepare`, without writes or process launches. Adding
`--stage prepare --execute` writes the pinned `plan.json`, the joint
`references.json`, and per-motion recording manifests. This stage still does
no GPU work. Preparation can be repeated with identical inputs; changed files,
configuration or workflow implementation require a new output directory.
Checkpoint metadata is checked on CPU when planning/executing training or
evaluation; prepare only checks its existence and content hash.

```bash
runtime/environments/newton-main-20260914/bin/python -B \
  scripts/run_trajectory_refinement.py \
  --config configs/trajectory_refinement/climb00_joint_v12.json \
  --stage prepare --execute
```

## Explicit execution stages

Run the following stages only after GPU work is authorized and resources are
available. The controller does not wait for GPUs, schedule future jobs, stop
other processes, or automatically start the next stage.

Activate `scripts/source_isaaclab3_newton_setup.sh` before running simulator
stages. Each command below is a **dry run** until `--execute` is explicitly
added. Replace the example configuration for a different reference collection.

```bash
python scripts/run_trajectory_refinement.py \
  --config configs/trajectory_refinement/climb00_joint_v12.json --stage train

python scripts/run_trajectory_refinement.py \
  --config configs/trajectory_refinement/climb00_joint_v12.json \
  --stage evaluate --checkpoint /path/to/refined/model_09000.pt

python scripts/run_trajectory_refinement.py \
  --config configs/trajectory_refinement/climb00_joint_v12.json \
  --stage collect --checkpoint /path/to/refined/model_09000.pt

python scripts/run_trajectory_refinement.py \
  --config configs/trajectory_refinement/climb00_joint_v12.json \
  --stage export --checkpoint /path/to/refined/model_09000.pt
```

Training reuses `train_motion_edit_policy_finetune.py`: one joint manifest, one
policy, existing PPO/optimizer configuration, self-collision enabled and
failure-window sampling. `train.iterations` is an additional budget relative to
the base checkpoint. A training-stage `--checkpoint` resumes from a checkpoint
inside this workflow's training directory and uses the remaining budget.
The controller does not claim an exhausted budget means the references are
feasible. Unsuccessful motions remain explicit failures.

Simulator arguments `--device`, `--visualizer kit` and `--headless` are forwarded
to existing AppLauncher-first entrypoints. No visualizer means headless;
`--headless` takes precedence over `--visualizer kit`. The controller itself is
a CPU command dispatcher and does not consume a GPU to parse its options.

Evaluation and collection currently process **one motion/environment at a time**
in a resumable queue. This keeps world/terrain/recording identity explicit and
limits memory. Joint training still uses all configured environments. This
first adapter does not yet amortize simulator startup across collection trials.

## Acceptance and evidence

Two independent results are retained for each trial:

1. Complete execution: the first episode has a contiguous native clock from
   reference frame zero through its final frame, finite recorded states, no
   early reset/termination, and the expected motion identity. Only the recorder's
   duplicate initial/bootstrap sample may be skipped; later episodes cannot
   hide an earlier failure.
2. Configured task acceptance: `contact_events` applies the existing
   `motion_edit.generation.event_acceptance.audit_events` to freshly recorded
   active/allocated contacts, with explicit intended surface mapping.
   Establish/keep/release requirements and timing tolerances come from the
   supplied contract. `completion_only` is an explicit weaker mode: task intent
   remains `not_requested`, and the dataset's scope must not be called task
   acceptance. A different task metric requires a new explicit adapter.

Contact identity comes from actual solver `type`, `dist`, `includemargin`, and
all required `efc_address` rows. `newton_support.select_support_contacts` resolves
native primary faces and uses `contact_face_selection`; sides and other
non-upward faces remain abnormal evidence. `max_abnormal_contacts` is an
acceptance count budget, never a contact distance threshold. Self/cross-robot
contacts do not become terrain contact. No margins, gaps, collision assets or
policy physics are modified to fit reference labels.

Missing fields, stale runtime provenance, unknown surface mappings and
unallocated active contacts stop the queue with an `unknown` report. They cannot
silently pass, fall back to force thresholds, or be treated as observed task
failure. Normal task failures are recorded and the queue proceeds.

The pipeline retains same-solve force and relative tangent-velocity observations.
Contact establishment alone is not evidence of stationary or load-bearing
support. This adapter does not impose an undeclared load/slip budget and does
not claim unrecorded substep motion is verified.

Every requested evaluation trial must produce a known result before a motion
can pass the configured success-rate gate. Collection uses exactly that evaluated
checkpoint. Collection attempts are independently accepted; failure trials stay
in the audit, and are never retried until they become successes. With another
checkpoint the policy hash creates a new result tree and evaluation is required
again. Export includes only accepted collection trials, records omissions and
does not require pretending every original reference succeeded.

## Outputs and recovery

```text
output_dir/
  plan.json, references.json, references/motion_*.json
  training/<attempt>/command.json, process.log, models/, completed.json
  policies/<checkpoint-sha256>/
    evaluate/<motion-key>/trial_*/<attempt>/recording.npz, report.json
    evaluation_summary.json
    collect/<motion-key>/trial_*/<attempt>/recording.npz, report.json
    collection_summary.json
    dataset/<motion-key>/trial_*/motion.npz, observations.npz, export.json
    dataset/manifest.json
```

Resume by repeating the same stage/config/checkpoint. Completed trials are reused
only after checking their context and all artifact hashes. Interrupted or unknown
attempts get a new attempt directory; old evidence is preserved. A controller
file lock prevents concurrent execute commands against the same workflow output.
There are no cleanup or permanent deletion operations.

Export stores recorded root/joint poses, velocities and body states without
averaging, temporal interpolation, FK replacement or pose correction. Each trial
remains an independent trajectory. `observations.npz` contains fresh effective
contact labels, abnormal pairs, load/slip observations, mapping and sampling
provenance. The complete original raw and solver contact record remains linked
by SHA256. Post-integration poses and solver geometry are explicitly distinct.

The observation schema is `somaforge_executed_contact_observations_v1`.
Existing fixed-q label loaders intentionally cannot treat this sidecar as
strictly same-state fixed-q contact truth. Downstream Predictor/Infiller data
preparation must explicitly consume this native recording clock, or separately
materialize fixed-q diagnostics while retaining the original execution evidence.
This workflow does not silently replace current training datasets or baselines.

`--stage status` reports prepared references, completed training runs,
evaluations and exported manifests. GPU behavior remains unverified until the
explicit simulator stages have actually been run.

## CPU regression tests

```bash
runtime/environments/newton-main-20260914/bin/python -B -m pytest \
  tests/test_trajectory_refinement.py -q -p no:cacheprovider
```

Tests retain their generated artifacts under project `tmp/trajectory_refinement_tests/`.
They exercise actual CPU contact activation/face selection, task failure,
unallocated/missing solver evidence, unchanged pose/velocity export, altered
recording detection, fixed-policy stage gating and no-process dry runs. They do
not launch Isaac, train a policy or run a GPU smoke test.
