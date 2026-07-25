# motion_edit

Contact-centered motion editing workbench for surface-bound contact-anchor editing, explicit ContactEditPlan generation, and Newton-validated policy-reference trajectories.

Motion Edit writes an edited kinematic reference through contact-Laplacian,
PyRoki trajectory IK, and direct Newton FK. Production force fields are
calculated afterward by frame-boundary Newton replay and must carry
`contact_force_provenance_json`. Source forces may be optimization or
acceptance references, but are never copied or migrated onto edited kinematics.
No alternative dynamics backend is supported.
The package stores local runtime metadata and
segment layers under `data/`; large runtime artifacts remain untracked.

## Layout

```text
data/
  catalogs/
  motions/
    raw/          # archived source refs only
    generated/    # edited kinematic refs awaiting Newton validation
  motion_assets/
  motion_versions/
  segments/
  tokens/
  layers/
    manual/
    candidates/
    contact/
    accepted/
    rejected/
  workbench/
    sessions/
  exports/
    cutter_segments/
    contact_overlays/
    split_npz/
    manifests/
    motions/
  backups/
```

## Recommended Workflow

Motion Edit uses the shared Conda environment. Install the Python service and
build the bundled Three.js frontend before launching the editor:

```bash
conda run -n env_somaforge \
  python -m pip install -e .
npm --prefix web install
npm --prefix web run build
```

Set `MOTION_EDIT_CONDA_ENV` only when intentionally testing another Conda
environment. Project-local `.venv` environments are not used.

The main user-facing path starts from the canonical asset manifest:

```text
Somaforge Newton 8-part asset manifest
  -> verified force trajectory + canonical source motion + terrain OBJ
  -> MotionAsset / ContactGraph / surface catalog
  -> unified contact-editor + recent motion list
  -> validated surface-constrained ContactEditPlan
  -> optional 6 Hz rollout pose cleanup
  -> contact-Laplacian semantic curves
  -> Newton robot-local contact patches
  -> PyRoki trajectory IK + Newton soft signed-distance similarity
  -> direct Newton FK canonical edited trajectory
  -> frame-boundary Newton replay
  -> WBT-ready 8-part force trajectory
```

```bash
./motion-edit import-asset-manifest \
  --manifest ../../runtime/current/manifests/newton_contact_force_8part.json

./motion-edit contact-editor \
  --motion-asset-id climb_01_newton_8part

./motion-edit validate-contact-edit-plan \
  --plan data/workbench/climb00_surface_edits.json

./motion-edit generate-ref \
  --plan data/workbench/climb00_surface_edits.json \
  --output-motion data/motions/generated/climb00_farther.policy_ref_v1.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version

./motion-edit export-manifest \
  --motion-version-id climb00_farther \
  --output data/exports/manifests/climb00_farther.json

./motion-edit export-split-npz \
  --motion-version-id climb00_farther
```

`import-asset-manifest` verifies the recorded motion, canonical source motion,
terrain OBJ, Newton provenance, and solver fingerprint. It then writes the
standard `newton_8part` ContactGraph/candidate layers, a terrain surface
catalog, and one complete MotionAsset per available motion. The command is
idempotent, so rerun it after the training/extraction queue adds entries to the
manifest. Direct terrain OBJ loading is supported; a terrain URDF wrapper is
not required.

`contact-editor` starts one FastAPI/Uvicorn process on one port and serves the
bundled Three.js UI. It loads registered assets, displays the sphere robot,
terrain, raw point+force contact samples, an 8-part force/contact timeline and
contact-episode edit handles, and saves a `ContactEditPlan`. Handle dragging
moves the whole episode while remaining same-surface constrained. Selection
and dragging are separate actions, and edited handles retain a clickable ghost
at their session-start position for exact episode restore. The Output tab
validates the plan and runs the same formal `generate-ref` implementation as a
background job; the CLI remains available for batch and scripted runs.

The Contact Editor Generate action and `generate-ref` remain supported
orchestration surfaces. The retained production command for reproducible
contact-aware kinematics is:

```bash
conda run --no-capture-output -n env_somaforge python \
  ../../scripts/generate_contact_aware_edited_motion.py \
  --plan data/workbench/climb00_surface_edits.json \
  --output ../../tmp/motion_edit_run/final_motion.npz \
  --intermediate-dir ../../tmp/motion_edit_run/work \
  --ik-conda-env env_somaforge \
  --newton-device cpu \
  --overwrite
```

It deliberately does not invent contact forces. Run the canonical result
through `scripts/replay_motion_newton_frame_boundary.py`, then build the WBT
policy reference with `scripts/build_newton_force_policy_reference.py`.

`generate-lte-augmentation` remains available only as a hidden/internal
geometry diagnostic. Its output is not a standard generated trajectory because
it does not write the WBT contact-force contract:

```bash
./motion-edit generate-lte-augmentation \
  --plan data/workbench/climb00_surface_edits.json \
  --output-motion ../../tmp/motion_edit/climb00_farther.geometry_debug.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --mode lte_fullbody
```

The former viewer, iframe timeline, surface-editor bridge, and interactive
cutter commands were removed. New work enters through the unified
`contact-editor`; its recent list loads registered and newly generated motions
through the same backend.

## Component Boundaries

Keep these boundaries clear when debugging or adding features:

| Component | Owns | Does not own |
| --- | --- | --- |
| `motion_edit/contact/` | Contact records, ContactGraph, ContactEditPlan, ContactPhase, surface binding, layer I/O | Running fullbody generation or policy rollout |
| `motion_edit/web/` + `web/` | Single-port API and Three.js Contact Editor | Contact dynamics or policy rollout |
| `motion_edit/generation/` | ContactEditPlan -> edited kinematic reference; hidden geometry diagnostics | Contact dynamics or policy rollout |
| `motion_edit/contact_laplacian/` | One motion's whole-trajectory Contact Laplacian, ContactHandleSpec, residual weights, solver metadata | Multi-motion queueing, policy-force writing, or simulator rollout |
| `motion_edit/augmentation.py` | Dataset-level job state, static candidate acceptance, accepted manifest | Editing plans, trajectory solving, Newton replay, or training |
| `motion_edit/contact_force/` | Canonical contact-force schema and explicitly diagnostic prescribed-force tools | Production force generation |
| `motion_edit/segmentation/` | Draft segmentation sessions with explicit start/list/edit/save/discard commands | Main contact-anchor editing |
| `motion_edit/storage/` | MotionAsset, MotionVersion, canonical segments, token catalogs | Runtime `.npz` payload ownership |
| `data/` | Local runtime data and generated artifacts | Git-tracked package source |

The formal force-aware reference path has separate ownership:

```text
reference output:
  edited canonical spherehand motion
  -> baseline-policy Newton rollout
  -> heel/toe/hand/knee contact_force_part_w [T, 8, 3]
```

Heel and toe masks are independent per frame, so heel-only, toe-only, and
simultaneous heel-plus-toe contact are all preserved.

## Avoiding Common Errors

- Use `motion-edit contact-editor` for interactive contact-anchor editing.
  The old `motion-edit-seg cutter` and `surface-editor` entry points were
  removed; segmentation diagnostics use the explicit `motion-edit-seg`
  session commands.
- Use `motion-edit generate-ref` for edited kinematic trajectories.
- Force-training files require `contact_force_part_w`, `contact_force_part_mask`,
  `contact_force_part_order`, and Newton `contact_force_provenance_json`.
- Treat `contact_force_part_w` and `contact_force_part_history_w` as physical
  data. Do not smooth them for editing. For complete recordings, the former is
  the strongest valid sample in the control interval and is aligned with the
  raw contact point from the same physics substep; the latter stores all
  physics substeps in latest-first order. Legacy recordings without point
  history fall back to the latest physics step. Stable editor phases come from
  `contact_force_part_mask`, while
  `contact_force_part_mask_raw` retains the direct force-threshold decision.
- Use `generate-lte-augmentation --mode lte_fullbody` only for hidden geometry
  diagnostics.
- Pass a logical contact layer such as `contact/raw29_00_editor_ready`; it
  resolves under `data/layers/contact/...`.
- Non-dry-run `generate-ref` requires `--output-contact-layer` or
  `output_contact_layer` in the plan.
- Confirm `ContactEditPlan.source_motion_path` exists before generation. It may
  be an absolute path outside this repository.
- CUDA/JAX/Isaac initialization warnings inside Codex or a machine without GPU
  access are not by themselves a failure. Treat the process exit code, generated
  output, and validator result as authoritative.
- For WBT policy refs, validate that the output includes `joint_pos`,
  `joint_vel`, `body_pos_w`, `body_quat_w`, `body_lin_vel_w`,
  `body_ang_vel_w`, `contact_force_part_w [T, 8, 3]`,
  `contact_force_part_mask [T, 8]`, and `contact_force_part_order`.
- Do not use historical force-reference `.npz` files produced with another
  robot asset.
- Inspect `motion_edit_generation_metadata`, `solver_metadata`, and
  `motion_edit_force_metadata` for trajectory quality. A file existing is not a
  quality check.
- Do not run broad cleanup such as `git clean -fd` in this checkout without
  inspecting the dry-run output; local `.agents/` and `.codex/` directories are
  workspace configuration.

## Integration and Review Boundaries

Keep future changes split by ownership: trajectory optimization and schemas,
Contact Editor UI/save behavior, Newton rollout and extraction, and
documentation. Do not revive the historical multi-branch Contact Editor stack
or mix local runtime data into a source change. Before opening or merging a PR,
verify:

```bash
git ls-files data | wc -l
```

Expected:

```text
0
```

The primary UI path is `motion_edit/web/server.py` plus the bundled `web/`
Three.js application through `motion-edit contact-editor`.

## Concepts

- `MotionRef`: a path reference to qpos / Holosoma fullbody / OmniRetarget motion data.
- `MotionAssetRecord`: an immutable full-motion source reference.
- `MotionVersionRecord`: one archived source or generated force-reference trajectory version. Standard generated versions point at WBT-ready `*.policy_ref_v1.npz` files.
- `ContactEventRecord`: a contact state change such as touchdown, liftoff, support switch, or active body change.
- `ContactAnchorRecord`: a persistent body-part contact interval. This is the primary handle for later visual editing.
- `ContactPatchRecord`: a concrete contact patch attached to an anchor, currently derived from anchor intervals.
- `ContactEditPlan`: a staged set of contact-anchor edits. It is a plan for later force-reference generation, not a generated trajectory.
- `ContactTransitionRecord`: a transfer segment between contact states or anchors.
- `ContactGraph`: the per-motion aggregate of events, anchors, patches, and transitions.
- `SegmentRecord`: one motion interval with `source`, `status`, backward-compatible mask strings, structured contact metadata, and cutter export fields.
- `TokenRecord`: a token index entry that references one canonical segment. It does not copy motion arrays.
- `EditRecord`: a provenance record for edits such as clip, splice, LTE edit, terrain offset, mirror, or relative-root transforms.

## Storage Rule

Full trajectories are stored as motion versions. Each motion version has exactly one current canonical segmentation:

```text
MotionVersionRecord
  -> full motion npz path
  -> ContactGraph
  -> data/segments/<motion_version_id>.jsonl
  -> data/tokens/<motion_version_id>.jsonl
```

The only active canonical segmentation path is `data/segments/<motion_version_id>.jsonl`. Commands that refine canonical storage update that same file. If a reset/refine/status operation needs history, history is written under `data/segments/history/`; those files are provenance/backups, not alternative active segmentations.

Motion assets and motion versions are path references; registering them does not copy the `.npz`. Contact-first segmentation is the default canonical segmentation source. Cutter/manual refinement updates the canonical segmentation with `cut_source=cutter_refined` or related provenance. `accepted`, `rejected`, `manual`, and cutter-refined states are statuses or provenance fields on canonical `SegmentRecord`s. They should not become competing active segment layers for the same motion version.

Legacy `data/layers/{candidates,manual,accepted,rejected}` paths remain for compatibility and migration. CLI commands that write these legacy layers print a warning and should not be treated as the primary storage path for new curation.

Split `.npz` files are export caches only. `export-split-npz` reads canonical segments and materializes clips for downstream training/export; those clips are safe to delete and regenerate.

## Edited Reference Generation

The production generator compiles one validated plan into a final canonical
motion:

```text
ContactEditPlan
  -> contact-Laplacian whole-body semantic curves
  -> Newton raw contacts reconstructed as rigid robot-local patches
  -> ContactAwareTaskspaceMotion
  -> PyRoki trajectory IK
  -> Newton soft signed-distance similarity to the source rollout
  -> direct Newton FK canonicalization
  -> final_motion.npz
```

The full-body semantic curves are soft shape targets. Contact patches are
actual multi-point rigid patches in canonical robot-local link frames. Edited
patches and their semantic handles receive the same world displacement; fixed
patches retain the source rollout world trajectory. Foot pose, joint velocity,
and acceleration priors come from the cleaned pose authority. Newton collision
queries preserve the source rollout's signed-distance relationship and penalize
only excess penetration more strongly.

```bash
conda run --no-capture-output -n env_somaforge python \
  ../../scripts/generate_contact_aware_edited_motion.py \
  --plan /path/to/validated_plan.json \
  --output ../../tmp/motion_edit_run/final_motion.npz \
  --intermediate-dir ../../tmp/motion_edit_run/work \
  --ik-conda-env env_somaforge \
  --newton-device cpu
```

The intermediate directory contains:

```text
*.semantic_task_proxy.npz
*.contact_aware_taskspace.npz
*.pyroki_preview.npz
*.pyroki_fk_preview.npz
```

These are diagnostics, not substitutes for `final_motion.npz`. The final file
must have `joint_pos [T,36]`, `joint_vel [T,35]`, complete finite body
pose/velocity arrays, canonical names, `robot_asset_json`, and direct Newton
kinematics provenance. It must not contain stale source `contact_force_part_w`,
`contact_force_provenance_json`, or `raw_contact_*`.

Force extraction is a separate dynamics stage. Frame-boundary replay makes the
edited state authoritative once per 20 ms control interval, advances four
continuous 5 ms Newton substeps, and records the fourth substep. The source
rollout's forces and torques are references for comparison/control only.
Production code must never migrate source forces into the edited trajectory.

See
[`docs/height110_production_pipeline.md`](docs/height110_production_pipeline.md)
for the retained end-to-end command sequence and measured acceptance values.

## Legacy Layer Policy

- `manual/original`: imported hand-made cutter cuts.
- `manual/current_cutter`: current cutter state.
- `candidates/force_contact`: automatically extracted force-contact proto candidates.
- `contact/force_contact`: contact graph sidecar generated from the same masks as `candidates/force_contact`.
- `accepted`: legacy curated segments. New force-ckpt exports should consume
  WBT-ready generated force-ref motion versions, not raw accepted clips.
- `rejected`: candidates kept for provenance but excluded from export.

Accept/reject writes use upsert-by-segment-id semantics for legacy compatibility. For canonical storage, use `mark-segment-status` so accepted/rejected remains a status inside `data/segments/<motion_version_id>.jsonl`.

## Contact-Centric Pipeline

Contact samples and edit handles are distinct. Each raw sample binds its point
and force from the same frame and contact index. Interactive editing instead
uses one representative handle for each continuous same-body, same-surface
contact episode.

```text
masked motion npz
  -> contact events
  -> contact anchors
  -> contact patches
  -> contact transitions
  -> SegmentRecord candidates
```

`import-force-proto` writes both segment candidates and a ContactLayer sidecar:

```text
data/layers/candidates/<layer>/<motion>.jsonl
data/layers/contact/<layer>/events/<motion>.jsonl
data/layers/contact/<layer>/anchors/<motion>.jsonl
data/layers/contact/<layer>/patches/<motion>.jsonl
data/layers/contact/<layer>/transitions/<motion>.jsonl
```

If proto boundaries are missing, initial segments can be derived from contact event pairs, for example liftoff to touchdown for the same active body. Existing exports remain segment-compatible, but include structured contact metadata when available.

Contact anchors are editable first-class objects. When `body_pos_w` is available, anchor extraction estimates `world_position` from the mean body position over the contact interval and stores drift statistics. In the main workflow, anchor edits are created inside `contact-editor` and stored as `ContactAnchorEditRecord` entries in a `ContactEditPlan`.

## Surface Binding

`ContactAnchor.world_position` is not enough for safe dragging. Before browser
dragging can move an anchor, it must be bound to its original terrain/object
surface. The Python API applies the authoritative surface projection and
reject/clamp bounds; the browser does not duplicate this solver.

Surface binding is explicit and does not generate a trajectory. It writes a new ContactLayer by default.

```bash
./motion-edit create-urdf-surface-catalog \
  --motion-id climb_00_z_scale_1.0 \
  --terrain-urdf /path/to/multi_boxes_z_scale_1.0.urdf \
  --output data/surfaces/climb_00_surfaces.jsonl

./motion-edit refine-contact-anchor-positions \
  --contact-layer contact/force_contact \
  --motion-id climb_00_z_scale_1.0 \
  --motion /path/to/climb_00_with_raw_contacts.npz \
  --surface-catalog data/surfaces/climb_00_surfaces.jsonl \
  --output-contact-layer contact/force_contact_raw_point_refined

./motion-edit merge-contact-anchors \
  --contact-layer contact/force_contact_raw_point_refined \
  --motion-id climb_00_z_scale_1.0 \
  --output-contact-layer contact/force_contact_raw_point_merged \
  --max-gap 3 \
  --max-distance 0.06

./motion-edit bind-contact-surfaces \
  --contact-layer contact/force_contact_raw_point_merged \
  --motion-id climb_00_z_scale_1.0 \
  --surface-catalog data/surfaces/climb_00_surfaces.jsonl \
  --output-contact-layer contact/force_contact_bound
```

Surface catalogs are JSONL records with fields such as `surface_id`, `object_id`, `surface_type`, `origin`, `normal`, `tangent_u`, `tangent_v`, and bounds like `{"u": [-0.25, 0.25], "v": [-0.25, 0.25]}`. Prefer `create-urdf-surface-catalog` for terrain: it parses URDF OBJ meshes into real mesh face groups and adds an explicit `terrain_ground_z0` plane by default. URDF surface catalogs default to top/upward faces plus ground only; side faces are excluded unless `--include-side-surfaces` is passed. `bind-contact-surfaces` applies the same default filter even for an explicit catalog. Mesh faces bind and render from their true polygon vertices; there is no outer-rectangle fallback for mesh surfaces. If the motion npz includes `raw_contact_*` arrays, run `refine-contact-anchor-positions` before binding; it estimates anchor positions from raw terrain-side contact points instead of the whole-interval body-position mean. `create-box-surface-catalog` remains only a manual/debug bridge and should not be used as a substitute for real terrain.

## Surface Binding Inspection

Surface binding should be inspected before using bound anchors for ContactEditPlan work or future force-reference generation. The inspection exports are diagnostic artifacts only: they do not modify motion data, do not update canonical segmentation, and do not generate `.npz` trajectory files.

The report export summarizes known surfaces, bound anchors, failed/unbound anchors, clamped bindings, and suspicious bindings. It also records that the binding granularity is `anchor_point`, not a full foot sole contact model.

The overlay export is a lightweight frontend-agnostic JSON file containing
`surface_quad`, `anchor_point`, `projection_line`, and `normal_axis` objects.

```bash
./motion-edit create-urdf-surface-catalog \
  --motion-id climb_00_z_scale_1.0 \
  --terrain-urdf /path/to/multi_boxes_z_scale_1.0.urdf \
  --output data/surfaces/climb_00_surfaces.jsonl

./motion-edit bind-contact-surfaces \
  --contact-layer contact/force_contact \
  --motion-id climb_00_z_scale_1.0 \
  --surface-catalog data/surfaces/climb_00_surfaces.jsonl \
  --output-contact-layer contact/force_contact_bound

./motion-edit export-surface-binding-report \
  --contact-layer contact/force_contact_bound \
  --motion-id climb_00_z_scale_1.0 \
  --output data/exports/surface_binding_reports/climb_00.json

./motion-edit export-surface-binding-overlay \
  --contact-layer contact/force_contact_bound \
  --motion-id climb_00_z_scale_1.0 \
  --output data/exports/surface_binding_overlays/climb_00.overlay.json

./motion-edit summarize-surface-bindings \
  --contact-layer contact/force_contact_bound \
  --motion-id climb_00_z_scale_1.0
```

## Interactive Surface Editor

`contact-editor` is the single entry point for contact-episode editing. It
starts a single-port local service. Loading an asset runs the fixed preparation
line: merge reliable anchors, filter invalid candidates, bind to real
ground/top surfaces, and validate the remaining anchors before returning the
session to Three.js.

The editor preparation is intentionally strict:

- `raw_missing`, `edge_candidate`, and `outside_known_surfaces` anchors are filtered before editing.
- Side surfaces are not allowed in the main editor path.
- Fallback planes are not created.
- If any remaining anchor is unbound or failed, the asset is rejected before rendering.

The session includes a surface binding report, surface binding overlay, contact overlay, session state, request file, and pending edit file under `data/workbench/surface_sessions/<session_name>/`.

The Three.js client renders the sphere URDF, terrain OBJ, surface catalog,
per-frame point+force sample glyphs and separate episode edit handles. The
bottom 8-part timeline owns playback and scrubbing; the right inspector owns
filtering, boundary mode and selection.

Heel, toe and sole are raw stages of the same parent foot, with no required
ordering. Any temporally connected contacts for the same parent body and the
same `surface_id`/`object_id` form one episode. That episode has one handle;
moving it applies one shared surface displacement to every member anchor while
preserving the original per-frame contact samples, forces and stage structure.

- Recent motions: a bottom-right vertical scroll list treats the source motion
  and every generated MotionVersion as peer entries. Selecting an entry opens
  its complete trajectory while preserving the owning asset context.
- Contact tab: body/surface/status filters, current-frame mode, previous/next
  contact, read-only surface-position offset and reject/clamp boundary mode.
- Display tab: terrain, contact surfaces, bound point+force samples, episode
  handles, root path, selection guides, handle size and force scale.
- Output tab: ContactEditPlan, generated motion/contact/segment paths, MotionVersion
  registration, overwrite policy, validation, generation status, reload and discard.
- Timeline: 8-part lane labels, adaptive time/frame ruler, stable cut markers,
  direct drag scrubbing, frame stepping and previous/next cut navigation. It is
  the only frame scrub control; there is no duplicate range slider.
- Toolbar: camera framing, undo, redo and save.

Opening a source or generated entry switches a complete MotionAsset-backed
bundle. Generated versions inherit robot, force, terrain and surface context,
but keep their own motion path, contact layer and version-scoped edit/output
paths. A successful Generate adds the new version to Recent and opens it
immediately. Raw paths must be registered first so asset context and provenance
cannot drift apart.

The bottom timeline keeps the original 8-part channels for inspection while
selection is parent-body based. Selecting a left-foot episode outlines both
`LHEE` and `LTOE` lanes over the episode interval. It also separates contact
intervals from edit cut frames:

- `contactPointBlock`: editable contact anchor intervals.
- `cutFrameMarker`: stable/contact-editor cut-frame boundaries.
- `proto_boundaries`: state payload for cut-frame navigation.

Avoid reviving old UI/test vocabulary such as `segmentBlock` or `protoBoundary` for the visible contact timeline.

3D selection and editing are same-surface constrained. The first click selects
an episode handle; a later drag on that selected handle arms the edit. Pointer
motion must exceed the screen drag threshold, and a submitted edit must exceed
the minimum world-space displacement, so clicks and small hand motion remain
no-ops. During a valid drag, Three.js previews the point on the bound surface
plane and shows read-only `Δu`/`Δv`. Python then projects the requested world
position into the authoritative surface coordinates, removes normal
displacement, preserves `surface_id`/`object_id`, and applies the current
reject/clamp mode.

After an edit, the translucent marker at the original position is a restore
target, not another contact sample or another episode handle. Clicking it
restores all member anchors and their metadata from the session-start snapshot.
Dragging away from it cancels restore. Escape, pointer cancellation and leaving
the viewport cancel an armed edit and put the preview back at the saved
position.

The API owns move, undo, redo and save state. There is no request-file bridge,
iframe, external viewer, or second port. The final force-bearing trajectory is
still produced by the subsequent Newton rollout.

Edits remain surface-constrained. One episode operation expands to its member
`ContactAnchorEditRecord` entries before generation. Each member uses
`move_contact_anchor_on_surface`: normal displacement and cross-surface jumps
are forbidden. The grouping does not impose heel/sole/toe phases or replace
the recorded point+force samples with the representative handle.

```bash
./motion-edit contact-editor \
  --motion-asset-id climb_01_newton_8part \
  --port 8094
```

Practical editor workflow:

1. Filter or select a contact episode.
2. Inspect its interval, parent body, members and surface binding.
3. Click once to select the episode, then drag the selected handle along its
   surface. Inspect the read-only `Δu`/`Δv` while moving it.
4. To restore that episode exactly, click its translucent original-position
   marker.
5. Use undo/redo as needed and save the edit plan.
6. In Output, validate and press Generate to write and register edited
   kinematics. Use `motion-edit generate-ref` instead for batch execution.
7. Run and record the edited reference in Newton to produce the WBT-ready force trajectory.

Validation writes pending `ContactAnchorEditRecord` entries into the
ContactEditPlan, saves the edited ContactLayer and marks a valid draft plan as
`validated`. Generate then runs whole-trajectory Contact Laplacian and full-body
IK without contact-force baking. None of these actions modify the archived
source motion `.npz` or mutate canonical segmentation by default.

## Contact-Centered Motion Generation

Contact-anchor editing remains staged through a `ContactEditPlan`. The editor's
Generate action and the `generate-ref` CLI are two frontends to the same formal
edited-kinematics implementation; the CLI form is:

```bash
./motion-edit validate-contact-edit-plan --plan data/workbench/climb00_farther.json
./motion-edit generate-ref \
  --plan data/workbench/climb00_farther.json \
  --output-motion data/motions/generated/climb00_farther.policy_ref_v1.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --overwrite
```

Use `generate-lte-augmentation` only when debugging the geometry stage:

```bash
./motion-edit validate-contact-edit-plan --plan data/workbench/climb00_farther.json
./motion-edit generate-lte-augmentation \
  --plan data/workbench/climb00_farther.json \
  --output-motion ../../tmp/motion_edit/climb00_farther.geometry_debug.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --mode lte_fullbody
```

Generation requires a `validated` or `locked` plan by default. The production
facade extracts semantic `body_pos_w` keypoints, solves the whole-trajectory
contact-Laplacian curves, binds Newton contact patches in canonical robot-local
frames, and runs PyRoki IK with direct Newton collision/FK evaluation. The
source rollout supplies contact timing, patch geometry, pose/collision
references, and diagnostics; it does not supply force fields for the edited
file. Motion Edit never fabricates or migrates the force field written to a
training reference: force-bearing output comes only from the subsequent
frame-boundary Newton replay.

The archived source `.npz`, source ContactLayer, and source canonical segmentation are not modified. `--output-contact-layer` writes a graph derived from the source ContactGraph with edited anchor positions. `--output-segment-layer` writes candidate segments for the edited reference. `--register-motion-version` registers that edited trajectory. Canonical segmentation for the new version is only built when `--build-canonical` is passed explicitly.

## Dataset Augmentation Queue

Dataset augmentation has four separate stages:

```text
contact/jitter.py       generate independent ContactEditPlans
generation/             solve one plan over one complete trajectory
augmentation.py         schedule/resume/retry independent plan jobs,
                        statically validate, then admit accepted outputs
```

`batch_contact_laplacian` is retained as a solver compatibility string. Here
`batch` means that all frames and contact handles of one motion are optimized
together; it does not mean that several motions are solved in one tensor batch.
The outer augmentation queue intentionally runs independent plans one at a
time and persists progress after every state change.

```bash
/home/xiaz/somaforge/packages/motion_edit/motion-edit generate-contact-jitter-plans \
  --cut-summary data/exports/contact_cut_summary.json \
  --output-dir data/workbench/augmentations/climb_jitter

/home/xiaz/somaforge/packages/motion_edit/motion-edit generate-augmentations \
  --plan-manifest data/workbench/augmentations/climb_jitter/manifest.json \
  --output-motion-dir data/motions/generated \
  --register-motion-version \
  --continue-on-error
```

The queue file is execution state: pending/running/retrying/failed/accepted,
attempt counts and errors. The separate `.accepted.json` manifest contains only
outputs that passed canonical-asset, shape, finite-value, solver-provenance,
Contact Laplacian target-error and full-body IK anchor-error checks. A
MotionVersion is registered only after these checks pass. This is still
`static_kinematic` acceptance: every accepted manifest explicitly retains
`physics_replay_required: true`; Newton rollout and force extraction remain the
next stage before force-aware WBT data admission.

## Legacy And Developer Notes

Legacy layer curation, cutter segment export/sync helpers, request-file
migration, old LTE catalog import, and low-level clip editing remain in the
codebase for compatibility and tests. They are hidden from the primary
`motion-edit --help` output. Prefer the main workflow unless you are migrating
old data or debugging one subsystem.

See also:

- `docs/contact_laplacian_algorithms.md` for the contact-Laplacian geometry
  backend used inside `generate-ref`.
