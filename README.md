# motion_edit

Contact-centric motion editing workbench for rollout motions, surface-bound contact-anchor editing, explicit ContactEditPlan generation, and downstream exports.

The package stores metadata and segment layers under `motion_edit/data/` and keeps large motion files as path references by default.

## Layout

```text
data/
  catalogs/
  motions/
    raw/
    generated/
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

Install viewer dependencies into the project environment before launching the local Viser editor:

```bash
uv pip install --python .venv/bin/python -e ".[viewer]"
```

The main user-facing path is:

```text
MotionAsset / MotionVersion
  -> ContactGraph / surface binding
  -> contact-editor
  -> ContactEditPlan
  -> generate-lte-augmentation --mode lte_fullbody
  -> generated MotionVersion
```

```bash
./motion-edit register-motion \
  --motion-asset-id climb00 \
  --motion /path/to/climb_00_rollout_ref_contact_force.npz \
  --motion-id climb_00_z_scale_1.0 \
  --terrain-urdf /path/to/multi_boxes_z_scale_1.0.urdf \
  --fps 50 \
  --source rollout

./motion-edit import-force-proto \
  --motion-dir /path/to/rollout_motions \
  --layer-name force_contact \
  --use-registered-motion-ids

./motion-edit bind-contact-surfaces \
  --contact-layer contact/force_contact \
  --motion-id climb_00_z_scale_1.0 \
  --terrain-urdf /path/to/multi_boxes_z_scale_1.0.urdf \
  --output-contact-layer contact/force_contact_bound

./motion-edit summarize-surface-bindings \
  --contact-layer contact/force_contact_bound \
  --motion-id climb_00_z_scale_1.0

./motion-edit contact-editor

./motion-edit validate-contact-edit-plan \
  --plan data/workbench/climb00_surface_edits.json

./motion-edit generate-lte-augmentation \
  --plan data/workbench/climb00_surface_edits.json \
  --output-motion data/motions/generated/climb00_farther.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --mode lte_fullbody

./motion-edit export-manifest \
  --motion-version-id climb00_farther \
  --output data/exports/manifests/climb00_farther.json

./motion-edit export-split-npz \
  --motion-version-id climb00_farther
```

`contact-editor` is the only recommended interactive UI. It opens the local Viser Contact Editor wrapper page, loads registered rollout motions, displays the motion/timeline/contact anchors, edits surface-bound anchors, saves a `ContactEditPlan`, and can trigger explicit fullbody LTE generation. Anchor dragging is same-surface constrained: normal displacement is discarded, `surface_id`/`object_id` are preserved, and surface bounds use reject/clamp semantics.

`generate-lte-augmentation` exposes one public generation mode:

```bash
~/motion_edit/motion-edit generate-lte-augmentation \
  --plan data/workbench/climb00_surface_edits.json \
  --output-motion data/motions/generated/climb00_farther.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --mode lte_fullbody
```

Legacy/debug commands such as `surface-editor`, `surface-editor-sync`, `cutter`, `view`, `accept`, `reject`, `import-lte-catalog`, `move-contact-anchor`, and raw segment workbench actions remain available for tests, migration, or diagnostics, but they are hidden from the main `motion-edit --help` flow. New work should enter through `contact-editor` and `generate-lte-augmentation --mode lte_fullbody`.

## Concepts

- `MotionRef`: a path reference to qpos / Holosoma fullbody / OmniRetarget motion data.
- `MotionAssetRecord`: an immutable full-motion source reference.
- `MotionVersionRecord`: one raw or generated full-trajectory version. This is the durable motion unit.
- `ContactEventRecord`: a contact state change such as touchdown, liftoff, support switch, or active body change.
- `ContactAnchorRecord`: a persistent body-part contact interval. This is the primary handle for later visual editing.
- `ContactPatchRecord`: a concrete contact patch attached to an anchor, currently derived from anchor intervals.
- `ContactEditPlan`: a staged set of contact-anchor edits. It is a plan for later augmentation, not an augmented motion.
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

## Legacy Layer Policy

- `manual/original`: imported hand-made cutter cuts.
- `manual/current_cutter`: current cutter state.
- `candidates/force_contact`: automatically extracted force-contact proto candidates.
- `contact/force_contact`: contact graph sidecar generated from the same masks as `candidates/force_contact`.
- `accepted`: curated segments that downstream training/export should consume.
- `rejected`: candidates kept for provenance but excluded from export.

Accept/reject writes use upsert-by-segment-id semantics for legacy compatibility. For canonical storage, use `mark-segment-status` so accepted/rejected remains a status inside `data/segments/<motion_version_id>.jsonl`.

## Contact-Centric Pipeline

Contact points are the shared editing handle for anchor segmentation, cutter correction, and later LTE deformation.

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

`ContactAnchor.world_position` is not enough for safe dragging. Before Viser dragging can move an anchor, the anchor should be bound to its original terrain/object surface. A bound anchor stores `object_id`, `surface_id`, normal/tangent basis, surface bounds, and `surface_coordinates`. The editor moves anchors in surface coordinates; normal motion is removed and bounds prevent dragging off the original platform/face.

Surface binding is explicit and does not generate augmented motion. It writes a new ContactLayer by default.

```bash
~/motion_edit/motion-edit create-urdf-surface-catalog \
  --motion-id climb_00_z_scale_1.0 \
  --terrain-urdf /path/to/multi_boxes_z_scale_1.0.urdf \
  --output data/surfaces/climb_00_surfaces.jsonl

~/motion_edit/motion-edit refine-contact-anchor-positions \
  --contact-layer contact/force_contact \
  --motion-id climb_00_z_scale_1.0 \
  --motion /path/to/climb_00_with_raw_contacts.npz \
  --surface-catalog data/surfaces/climb_00_surfaces.jsonl \
  --output-contact-layer contact/force_contact_raw_point_refined

~/motion_edit/motion-edit merge-contact-anchors \
  --contact-layer contact/force_contact_raw_point_refined \
  --motion-id climb_00_z_scale_1.0 \
  --output-contact-layer contact/force_contact_raw_point_merged \
  --max-gap 3 \
  --max-distance 0.06

~/motion_edit/motion-edit bind-contact-surfaces \
  --contact-layer contact/force_contact_raw_point_merged \
  --motion-id climb_00_z_scale_1.0 \
  --surface-catalog data/surfaces/climb_00_surfaces.jsonl \
  --output-contact-layer contact/force_contact_bound
```

Surface catalogs are JSONL records with fields such as `surface_id`, `object_id`, `surface_type`, `origin`, `normal`, `tangent_u`, `tangent_v`, and bounds like `{"u": [-0.25, 0.25], "v": [-0.25, 0.25]}`. Prefer `create-urdf-surface-catalog` for terrain: it parses URDF OBJ meshes into real mesh face groups and adds an explicit `terrain_ground_z0` plane by default. URDF surface catalogs default to top/upward faces plus ground only; side faces are excluded unless `--include-side-surfaces` is passed. `bind-contact-surfaces` applies the same default filter even for an explicit catalog. Mesh faces bind and render from their true polygon vertices; there is no outer-rectangle fallback for mesh surfaces. If the motion npz includes `raw_contact_*` arrays, run `refine-contact-anchor-positions` before binding; it estimates anchor positions from raw terrain-side contact points instead of the whole-interval body-position mean. `create-box-surface-catalog` remains only a manual/debug bridge and should not be used as a substitute for real terrain.

## Surface Binding Inspection

Surface binding should be inspected before using bound anchors for ContactEditPlan work or future LTE/contact augmentation. The inspection exports are diagnostic artifacts only: they do not modify motion data, do not update canonical segmentation, and do not generate augmented `.npz` files.

The report export summarizes known surfaces, bound anchors, failed/unbound anchors, clamped bindings, and suspicious bindings. It also records that the binding granularity is `anchor_point`, not a full foot sole contact model.

The overlay export is a lightweight frontend-agnostic JSON file. It contains `surface_quad`, `anchor_point`, `projection_line`, and `normal_axis` objects with status tags. Future Viser integration can render those objects and color them by status.

```bash
~/motion_edit/motion-edit create-urdf-surface-catalog \
  --motion-id climb_00_z_scale_1.0 \
  --terrain-urdf /path/to/multi_boxes_z_scale_1.0.urdf \
  --output data/surfaces/climb_00_surfaces.jsonl

~/motion_edit/motion-edit bind-contact-surfaces \
  --contact-layer contact/force_contact \
  --motion-id climb_00_z_scale_1.0 \
  --surface-catalog data/surfaces/climb_00_surfaces.jsonl \
  --output-contact-layer contact/force_contact_bound

~/motion_edit/motion-edit export-surface-binding-report \
  --contact-layer contact/force_contact_bound \
  --motion-id climb_00_z_scale_1.0 \
  --output data/exports/surface_binding_reports/climb_00.json

~/motion_edit/motion-edit export-surface-binding-overlay \
  --contact-layer contact/force_contact_bound \
  --motion-id climb_00_z_scale_1.0 \
  --output data/exports/surface_binding_overlays/climb_00.overlay.json

~/motion_edit/motion-edit summarize-surface-bindings \
  --contact-layer contact/force_contact_bound \
  --motion-id climb_00_z_scale_1.0
```

## Interactive Surface Editor

`contact-editor` is the single main entry point for anchor-level contact editing. It prepares an editor-ready ContactLayer and then launches the local `motion_edit` Viser surface overlay adapter. The command always runs the fixed preparation line first: merge nearby reliable anchors, filter invalid binding candidates, bind to real ground/top surfaces, validate that all remaining anchors are bound, and only then open Viser.

The editor preparation is intentionally strict:

- `raw_missing`, `edge_candidate`, and `outside_known_surfaces` anchors are filtered before editing.
- Side surfaces are not allowed in the main editor path.
- Fallback planes are not created.
- If any remaining anchor is unbound or failed, Viser is not opened.
- Low-level surface editor commands remain only for debug/internal prepared-layer checks.

The session includes a surface binding report, surface binding overlay, contact overlay, session state, request file, and pending edit file under `data/workbench/surface_sessions/<session_name>/`.

The local adapter reads the existing overlay JSON and renders the motion root trace, robot playback, optional terrain/object URDF, `surface_quad`, `anchor_point`, `projection_line`, and `normal_axis` objects in Viser. The bottom cutter-style timeline owns playback/scrubbing and contact interval selection. The right sidebar is organized around the current workflow:

- `Motion`: current motion/session, overlay reload, and status.
- `Contact Anchor`: selected-anchor metadata only.
- `Augmentation`: write/validate the ContactEditPlan, dry-run fullbody LTE, generate the augmented motion, reset the session, and optionally export a debug ContactLayer.

The bottom timeline top bar owns motion switching. It includes a recent-motion dropdown plus `Open`, `Open latest`, and `Reload`. All entries are treated as regular motions with the same bundle-style fields; raw rollout and LTE-augmented outputs are not special UI modes. Generated motions are added to `data/workbench/recent_motions.json` after successful generation, so the next step is usually `Open latest`.

3D selection and handle editing are same-surface constrained. Anchor markers can be clicked in the 3D view when supported by the local Viser runtime. The selected anchor shows a handle with tangent axes, normal axis, and surface bounds. Dragging this handle is not a free 3D transform: the dragged world point is projected back into the anchor's original surface coordinates, any normal component is discarded, and the anchor keeps the same `surface_id` and `object_id`. Bounds are enforced by the current reject/clamp mode. A normal-only drag is ignored as a no-op.

The local Viser direct editor renders the overlay, highlights the selected
anchor, moves anchors with same-surface constrained 3D handles, refreshes the
overlay, supports full-session reset, validates the edit plan, and can launch
fullbody LTE generation from the Viser GUI. A request-file bridge remains for
debug fallback but is not part of the normal workflow.

The older external Holosoma viewer can still be used with `--external-viewer`, but it is no longer required for the surface overlay bridge. The local editor owns the surface overlay and same-surface anchor handle interactions.

Edits remain anchor-level and surface-constrained. They use `move_contact_anchor_on_surface`, never allow normal displacement, never jump to another surface, and do not model full foot sole contact, toe/heel rolling, pressure, or physical sticking.

```bash
~/motion_edit/motion-edit contact-editor /path/to/climb_00.npz \
  --motion-id climb_00_z_scale_1.0 \
  --source-contact-layer contact/force_contact_raw_point_merged_wide \
  --terrain-urdf /path/to/multi_boxes_z_scale_1.0.urdf \
  --session-name climb00_surface \
  --edit-plan data/workbench/climb00_surface_edits.json \
  --output-contact-layer contact/climb00_surface_edited \
  --with-terrain
```

In the Viser GUI, select an anchor from the bottom timeline or 3D view, drag its same-surface contact handle, then click `Validate plan`, `Dry run fullbody LTE`, or `Generate fullbody LTE`. No terminal sync is needed in default direct mode.

Practical in-viewer workflow:

1. Filter or select an anchor.
2. Inspect the selected anchor metadata and surface binding.
3. Move by 3D same-surface drag, `du`/`dv`, step buttons, or target `u/v`.
4. Use `Reset session` or `Discard unsaved edits` if needed.
5. Click `Validate plan`, then `Dry run fullbody LTE` or `Generate fullbody LTE`.
6. Click `Open latest` in the bottom timeline bar to switch to the newly generated motion.

Validation writes pending `ContactAnchorEditRecord` entries into the ContactEditPlan and marks a valid draft plan as `validated`; it does not export a ContactLayer. `Generate fullbody LTE` then creates a new motion from that plan and records it in the recent-motion cache. `Export debug ContactLayer` is available for inspection, but it is not the main workflow. None of these actions modify the currently loaded motion `.npz` or mutate canonical segmentation by default.

## LTE-Style Motion Augmentation

Contact-anchor editing is intentionally two-stage. The editor only stages edits
in a `ContactEditPlan`; motion generation is explicit:

```bash
~/motion_edit/motion-edit validate-contact-edit-plan --plan data/workbench/climb00_farther.json
~/motion_edit/motion-edit generate-lte-augmentation \
  --plan data/workbench/climb00_farther.json \
  --output-motion data/motions/generated/climb00_farther.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --mode lte_fullbody \
  --lte-repo-root /home/xiaz/lte \
  --ik-conda-env env_pyroki_climb_projection
```

Generation requires a `validated` or `locked` plan by default. The primary backend, `lte_fullbody`, follows the old LTE structure but is driven from motion_edit data: it extracts semantic keypoints from the source motion, applies ContactEditPlan handles through the LTE keypoint solver, writes LTE keypoints and a dense taskspace motion as intermediates, calls the full-body IK runner, and writes one final augmented motion `.npz`. This path is explicit; it does not run automatically from the surface editor.

The source `.npz`, source ContactLayer, and source canonical segmentation are not modified. `--output-contact-layer` writes a graph derived from the source ContactGraph with edited anchor positions. `--output-segment-layer` writes candidate segments for the generated motion. `--register-motion-version` registers the generated full trajectory as an augmented MotionVersion. Canonical segmentation for that new version is only built when `--build-canonical` is passed explicitly.

## Legacy And Developer Notes

Legacy layer curation, the old Holosoma cutter adapter, manual `surface-editor`
entry points, request-file sync, old LTE catalog import, and low-level clip
editing remain in the codebase for compatibility and tests. They are hidden
from the primary `motion-edit --help` output. Prefer the main workflow unless
you are migrating old data or debugging one subsystem.

See also:

- `docs/contact_laplacian_algorithms.md` for the current production fullbody
  LTE path and the experimental batch contact-Laplacian direction.
