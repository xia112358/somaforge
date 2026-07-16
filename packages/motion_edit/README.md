# motion_edit

Contact-centered motion editing workbench for surface-bound contact-anchor editing, explicit ContactEditPlan generation, and Newton-validated policy-reference trajectories.

`generate-ref` writes an edited kinematic reference. Production force fields are
added only by a successful Isaac Lab 3/Newton policy rollout and must carry
`contact_force_provenance_json`. Existing Newton force references may be
retargeted onto edited kinematics; no alternative dynamics backend is supported.
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
conda run -n env_holosoma_isaaclab3_newton \
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
  -> ContactGraph / surface binding
  -> contact-editor
  -> ContactEditPlan
  -> generate-ref
  -> edited kinematic trajectory / generated MotionVersion
  -> Newton policy rollout
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
terrain, 8-part force/contact timeline and anchors, and saves a
`ContactEditPlan`. Anchor dragging remains same-surface constrained.

`generate-ref` is the formal edited-kinematics path. It runs contact-aware
geometry generation and full-body IK, but deliberately does not solve contact
forces. Run the result through the Holosoma Newton rollout recorder and
`scripts/extract_rollout_ref_contact_force_demo.py` before force-aware training.

```bash
./motion-edit generate-ref \
  --plan data/workbench/climb00_surface_edits.json \
  --output-motion data/motions/generated/climb00_farther.policy_ref_v1.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --overwrite
```

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
cutter commands were removed. New work enters through `contact-editor` and
`generate-ref`.

## Component Boundaries

Keep these boundaries clear when debugging or adding features:

| Component | Owns | Does not own |
| --- | --- | --- |
| `motion_edit/contact/` | Contact records, ContactGraph, ContactEditPlan, ContactPhase, surface binding, layer I/O | Running fullbody generation or policy rollout |
| `motion_edit/web/` + `web/` | Single-port API and Three.js Contact Editor | Contact dynamics or policy rollout |
| `motion_edit/generation/` | ContactEditPlan -> edited kinematic reference; hidden geometry diagnostics | Contact dynamics or policy rollout |
| `motion_edit/contact_laplacian/` | Batch contact-Laplacian solver, ContactHandleSpec, residual weights, solver metadata | Policy-force writing or simulator rollout |
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
  data. Do not smooth them for editing. The former is aligned with the latest
  raw contact point; the latter stores physics substeps in latest-first order.
  Stable editor phases come from `contact_force_part_mask`, while
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

The standard generation entry is `generate-ref`. It writes edited kinematics
that must subsequently pass a Newton policy rollout:

```bash
./motion-edit generate-ref \
  --plan data/workbench/climb00_edits.json \
  --output-motion data/motions/generated/climb00.policy_ref_v1.npz \
  --output-contact-layer contact/climb00_policy_ref \
  --output-segment-layer candidates/climb00_policy_ref \
  --output-motion-version-id climb00_policy_ref \
  --register-motion-version
```

The production projection backend is one whole-trajectory PyRoki/JAXLS graph.
All frames, floating-base poses, and joint configurations are optimized
together. The graph has exactly three objective families:

1. `contact_interaction_laplacian`
2. `temporal_laplacian`
3. `contact_force`

Joint limits, foot orientation, contact sticking, and nonpenetration are soft
residuals inside the contact/interaction family, not separate hard constraints.
The force family linearizes force response from the latest Newton rollout.
Newton evaluates each candidate and returns the next real 8-part force tensor;
contact points, penetration depth, and overlap distance are not extracted as
optimization targets. The temporary correction direction comes from the target
force vector itself. There is no per-frame SciPy/SQP production path.

Run the complete black-box Newton force loop from the PyRoki environment:

```bash
./motion-edit force-retarget \
  --initial-motion data/motions/generated/climb00.policy_ref_v1.npz \
  --lte data/motions/generated/climb00.policy_ref_v1/climb00.policy_ref_v1.contact_laplacian_keypoints.npz \
  --target-force-motion runtime/current/motions/newton_contact_force/climb_00_rollout_ref_contact_force.npz \
  --manifest runtime/current/manifests/newton_contact_force_8part.json \
  --motion-id 00 \
  --checkpoint /path/to/wbt_model.pt \
  --newton-python /home/xiaz/miniforge3/envs/env_holosoma_isaaclab3_newton/bin/python \
  --output-motion data/motions/generated/climb00.force_ref_v1.npz \
  --work-dir ../../tmp/motion_edit/climb00_force_retarget
```

Before every rollout, the command canonicalizes the PyRoki candidate with the
same sphere-hand URDF and Newton FK used by training, then writes a fully hashed
single-motion manifest. The final output is the accepted Newton rollout, not a
kinematically fabricated force field.

The geometry-only command is hidden and should be treated as a diagnostic
intermediate producer:

```bash
./motion-edit generate-lte-augmentation \
  --mode lte_fullbody \
  --plan data/workbench/climb00_edits.json \
  --output-motion ../../tmp/motion_edit/climb00.geometry_debug.npz
```

Do not use the edited output directly for force-aware WBT. First collect a
successful Newton rollout and extract the canonical 8-part reference.

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

Contact points are the shared editing handle for anchor segmentation, cutter correction, and force-reference generation.

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

`contact-editor` is the single entry point for anchor-level contact editing. It
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
contact anchors and force arrows. The bottom 8-part timeline owns playback and
scrubbing; the right inspector owns filtering, boundary mode and selection.

- Asset selector: registered Newton force assets and reload.
- Contact tab: body/surface/status filters, current-frame mode, previous/next
  contact, exact `u/v`, stepped `du/dv`, restore and reject/clamp.
- Display tab: terrain, contact surfaces, anchors, forces, root path, selection
  guides, anchor size and force scale.
- Output tab: ContactEditPlan path/status, output contact layer, save, validate,
  reload and discard.
- Timeline: 8-part lane labels, frame ruler, stable cut markers, direct scrub,
  frame stepping and previous/next cut navigation.
- Toolbar: camera framing, undo, redo and save.

The asset selector switches complete MotionAsset bundles. Raw paths must be
registered first so robot, force, terrain and provenance cannot drift apart.

The bottom timeline separates contact-point intervals from edit cut frames:

- `contactPointBlock`: editable contact anchor intervals.
- `cutFrameMarker`: stable/contact-editor cut-frame boundaries.
- `proto_boundaries`: state payload for cut-frame navigation.

Avoid reviving old UI/test vocabulary such as `segmentBlock` or `protoBoundary` for the visible contact timeline.

3D selection and editing are same-surface constrained. Three.js raycasts the
selected marker and drag plane, then sends the requested world position to the
Python API. Python projects it into the original surface coordinates, removes
normal displacement, preserves `surface_id`/`object_id`, and applies the
current reject/clamp mode.

The API owns move, undo, redo and save state. There is no request-file bridge,
iframe, external viewer, or second port. The final force-bearing trajectory is
still produced by the subsequent Newton rollout.

Edits remain anchor-level and surface-constrained. They use `move_contact_anchor_on_surface`, never allow normal displacement, never jump to another surface, and do not model full foot sole contact, toe/heel rolling, pressure, or physical sticking.

```bash
./motion-edit contact-editor \
  --motion-asset-id climb_01_newton_8part \
  --port 8094
```

Practical editor workflow:

1. Filter or select an anchor.
2. Inspect the selected anchor metadata and surface binding.
3. Move it with a same-surface 3D drag.
4. Use undo/redo as needed and save the edit plan.
5. Run `motion-edit generate-ref` to write edited kinematics.
6. Run and record the edited reference in Newton to produce the WBT-ready force trajectory.

Validation writes pending `ContactAnchorEditRecord` entries into the ContactEditPlan and marks a valid draft plan as `validated`; it does not export a ContactLayer. Diagnostic geometry generation can create a non-force intermediate for inspection, but it is not the main workflow. `Export debug ContactLayer` is available for inspection. None of these actions modify the archived source motion `.npz` or mutate canonical segmentation by default.

## Contact-Centered Motion Generation

Contact-anchor editing is intentionally staged. The editor only stages edits in
a `ContactEditPlan`; use `generate-ref` for the formal edited-kinematics path:

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

Generation requires a `validated` or `locked` plan by default. `generate-ref`
extracts semantic `body_pos_w` keypoints, applies ContactEditPlan handles through
the whole-trajectory three-family graph. A geometry-only run has a zero force
mask; a physics-guided run supplies target force plus the latest real Newton
force to the same graph. Motion Edit never fabricates the
force field written to a training reference: the final force-bearing trajectory
still comes from the accepted Newton rollout.

The archived source `.npz`, source ContactLayer, and source canonical segmentation are not modified. `--output-contact-layer` writes a graph derived from the source ContactGraph with edited anchor positions. `--output-segment-layer` writes candidate segments for the edited reference. `--register-motion-version` registers that edited trajectory. Canonical segmentation for the new version is only built when `--build-canonical` is passed explicitly.

## Legacy And Developer Notes

Legacy layer curation, cutter segment export/sync helpers, request-file
migration, old LTE catalog import, and low-level clip editing remain in the
codebase for compatibility and tests. They are hidden from the primary
`motion-edit --help` output. Prefer the main workflow unless you are migrating
old data or debugging one subsystem.

See also:

- `docs/contact_laplacian_algorithms.md` for the contact-Laplacian geometry
  backend used inside `generate-ref`.
