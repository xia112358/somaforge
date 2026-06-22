# motion_edit

Standalone motion editing workbench for cutter/manual segments, contact-derived proto candidates, LTE edits, motion edits, visualization, and exports.

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

## CLI

```bash
~/motion_edit/motion-edit import-force-proto --motion-dir /path/to/masked_motions --layer-name force_contact
~/motion_edit/motion-edit register-motion-asset --motion-asset-id climb00 --motion /path/to/climb_00_z_scale_1.0.npz --fps 50 --source local
~/motion_edit/motion-edit register-motion-version --motion-version-id climb00_raw --motion /path/to/climb_00_z_scale_1.0.npz --kind raw --motion-asset-id climb00 --contact-layer contact/force_contact
~/motion_edit/motion-edit migrate-layer-to-canonical --motion-version-id climb00_raw --motion /path/to/climb_00_z_scale_1.0.npz --source candidates/force_contact --contact-layer contact/force_contact
~/motion_edit/motion-edit cutter /path/to/climb_00_z_scale_1.0.npz --motion-version-id climb00_raw --update-canonical --session-name climb00_check --with-terrain
~/motion_edit/motion-edit canonical-action --motion-version-id climb00_raw --segment-id SEG_ID --action trim --start-frame 120 --end-frame 180
~/motion_edit/motion-edit mark-segment-status --motion-version-id climb00_raw --segment-id SEG_ID --status accepted
~/motion_edit/motion-edit build-token-catalog --motion-version-id climb00_raw
~/motion_edit/motion-edit export-manifest --motion-version-id climb00_raw --output data/exports/manifests/climb00_raw.json
~/motion_edit/motion-edit export-split-npz --motion-version-id climb00_raw --status accepted
~/motion_edit/motion-edit list-contact-layer --source contact/force_contact --motion-id climb_00_z_scale_1.0
~/motion_edit/motion-edit move-contact-anchor --source contact/force_contact --motion-id climb_00_z_scale_1.0 --anchor-id climb_00_z_scale_1.0_anchor_LF_000100_000140 --delta-world 0.10 0.0 0.0 --output-source contact/force_contact_farther --edit-plan data/workbench/climb00_farther.json --source-motion /path/to/climb_00_z_scale_1.0.npz
~/motion_edit/motion-edit create-box-surface-catalog --motion-id climb_00_z_scale_1.0 --box box_0:1.0,0.0,0.4:0.5,0.5,0.8 --output data/surfaces/climb_00_surfaces.jsonl
~/motion_edit/motion-edit bind-contact-surfaces --contact-layer contact/force_contact --motion-id climb_00_z_scale_1.0 --surface-catalog data/surfaces/climb_00_surfaces.jsonl --output-contact-layer contact/force_contact_bound
~/motion_edit/motion-edit export-surface-binding-report --contact-layer contact/force_contact_bound --motion-id climb_00_z_scale_1.0 --output data/exports/surface_binding_reports/climb_00.json
~/motion_edit/motion-edit export-surface-binding-overlay --contact-layer contact/force_contact_bound --motion-id climb_00_z_scale_1.0 --output data/exports/surface_binding_overlays/climb_00.overlay.json
~/motion_edit/motion-edit validate-contact-edit-plan --plan data/workbench/climb00_farther.json
~/motion_edit/motion-edit generate-lte-augmentation --plan data/workbench/climb00_farther.json --output-motion data/exports/motions/climb00_farther.npz
~/motion_edit/motion-edit export-contact-overlay --source contact/force_contact --motion-id climb_00_z_scale_1.0 --output data/exports/contact_overlays/climb_00.json
~/motion_edit/motion-edit import-manual-cuts --segments-dir /path/to/data/motion_viewer/segments --layer-name current
~/motion_edit/motion-edit export-cutter-segments --source candidates/force_contact
~/motion_edit/motion-edit export-manifest --source candidates/force_contact --output data/exports/manifests/force_contact.json
~/motion_edit/motion-edit export-split-npz --source accepted/probe
~/motion_edit/motion-edit import-lte-catalog --catalog /path/to/lte/catalog.json --layer-name widthaway10
~/motion_edit/motion-edit list-layer --source candidates/force_contact --motion-id climb_00_z_scale_1.0
~/motion_edit/motion-edit accept --source candidates/force_contact --layer-name curated --motion-id climb_00_z_scale_1.0 --index 0
~/motion_edit/motion-edit reject --source candidates/force_contact --layer-name bad --segment-id some_segment_id
~/motion_edit/motion-edit detect-motion /path/to/climb_00_z_scale_1.0.npz --repo-root /path/to/holosoma_repo
~/motion_edit/motion-edit view /path/to/climb_00_z_scale_1.0.npz --layer candidates/force_contact --repo-root /path/to/holosoma_repo
~/motion_edit/motion-edit cutter /path/to/climb_00_z_scale_1.0.npz --source candidates/force_contact --session-name climb00_check --with-terrain
~/motion_edit/motion-edit edit-clip --input in.npz --output out.npz --start 100 --end 160
~/motion_edit/motion-edit edit-splice --output stitched.npz a.npz b.npz c.npz
~/motion_edit/motion-edit summarize
```

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

Contact anchors are editable first-class objects. When `body_pos_w` is available, anchor extraction estimates `world_position` from the mean body position over the contact interval and stores drift statistics. `move-contact-anchor` writes a new ContactLayer and records a `move_contact_anchor` edit without deforming the source motion. This is the persistent representation for edits such as "move this foot contact 10 cm farther."

## Surface Binding

`ContactAnchor.world_position` is not enough for safe dragging. Before a future Viser drag can move an anchor, the anchor should be bound to its original terrain/object surface. A bound anchor stores `object_id`, `surface_id`, normal/tangent basis, surface bounds, and `surface_coordinates`. `move-contact-anchor --tangent-delta DU DV` then moves in surface coordinates; normal motion is removed and bounds prevent dragging off the original platform/face.

Surface binding is explicit and does not generate augmented motion. It writes a new ContactLayer by default.

```bash
~/motion_edit/motion-edit create-box-surface-catalog \
  --motion-id climb_00_z_scale_1.0 \
  --box box_0:1.0,0.0,0.4:0.5,0.5,0.8 \
  --output data/surfaces/climb_00_surfaces.jsonl

~/motion_edit/motion-edit bind-contact-surfaces \
  --contact-layer contact/force_contact \
  --motion-id climb_00_z_scale_1.0 \
  --surface-catalog data/surfaces/climb_00_surfaces.jsonl \
  --output-contact-layer contact/force_contact_bound

~/motion_edit/motion-edit move-contact-anchor \
  --source contact/force_contact_bound \
  --motion-id climb_00_z_scale_1.0 \
  --anchor-id <anchor_id> \
  --tangent-delta 0.10 0.00 \
  --output-source contact/climb00_farther
```

Manual surface catalogs are JSONL records with fields such as `surface_id`, `object_id`, `surface_type`, `origin`, `normal`, `tangent_u`, `tangent_v`, and bounds like `{"u": [-0.25, 0.25], "v": [-0.25, 0.25]}`. `create-box-surface-catalog` provides a simple bridge by emitting top and side faces for box/platform descriptors. URDF, OBJ, terrain metadata, and heightfield loaders are intentionally left as explicit future loaders.

## Surface Binding Inspection

Surface binding should be inspected before using bound anchors for ContactEditPlan work or future LTE/contact augmentation. The inspection exports are diagnostic artifacts only: they do not modify motion data, do not update canonical segmentation, and do not generate augmented `.npz` files.

The report export summarizes known surfaces, bound anchors, failed/unbound anchors, clamped bindings, and suspicious bindings. It also records that the binding granularity is `anchor_point`, not a full foot sole contact model.

The overlay export is a lightweight frontend-agnostic JSON file. It contains `surface_quad`, `anchor_point`, `projection_line`, and `normal_axis` objects with status tags. Future Viser integration can render those objects and color them by status.

```bash
~/motion_edit/motion-edit create-box-surface-catalog \
  --motion-id climb_00_z_scale_1.0 \
  --box box_0:1.0,0.0,0.4:0.5,0.5,0.8 \
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

`surface-editor` is the Viser-connected entry point for anchor-level contact editing. It prepares a surface binding report, surface binding overlay, contact overlay, session state, request file, and pending edit file under `data/workbench/surface_sessions/<session_name>/`, then launches the local `motion_edit` Viser surface overlay adapter by default.

The local adapter reads the existing overlay JSON and renders `surface_quad`, `anchor_point`, `projection_line`, and `normal_axis` objects in Viser. Its minimal GUI lets a user enter/select an anchor id, set `du`/`dv` surface-coordinate deltas, choose `reject` or `clamp`, and write a move request. Requests are applied by `surface-editor-sync`, which routes every move through the same surface-constrained backend as `move-contact-anchor`.

The older external Holosoma viewer can still be used with `--external-viewer`, but it is no longer required for the surface overlay bridge. Direct draggable 3D handles are not claimed yet; this first in-viewer interaction is an explicit Viser control panel plus request/sync bridge.

Edits remain anchor-level and surface-constrained. They use `move_contact_anchor_on_surface`, never allow normal displacement, never jump to another surface, and do not model full foot sole contact, toe/heel rolling, pressure, or physical sticking.

```bash
~/motion_edit/motion-edit surface-editor /path/to/climb_00.npz \
  --motion-id climb_00_z_scale_1.0 \
  --contact-layer contact/force_contact_bound \
  --surface-catalog data/surfaces/climb_00_surfaces.jsonl \
  --session-name climb00_surface \
  --edit-plan data/workbench/climb00_surface_edits.json \
  --output-contact-layer contact/climb00_surface_edited \
  --with-terrain

~/motion_edit/motion-edit surface-editor-sync \
  --session data/workbench/surface_sessions/climb00_surface/session.json

~/motion_edit/motion-edit surface-editor-sync \
  --session data/workbench/surface_sessions/climb00_surface/session.json \
  --save

~/motion_edit/motion-edit surface-editor-move-anchor \
  --session data/workbench/surface_sessions/climb00_surface/session.json \
  --anchor-id <anchor_id> \
  --tangent-delta 0.10 0.00 \
  --save
```

Saving writes a moved ContactLayer and appends `ContactAnchorEditRecord` entries to the edit plan if configured. It does not modify the original motion `.npz`, does not generate LTE augmented motion, and does not mutate canonical segmentation.

## Contact Anchor Edit Plans

Contact-anchor editing is intentionally two-stage.

Stage 1 stages edits only:

```bash
~/motion_edit/motion-edit move-contact-anchor \
  --source contact/force_contact \
  --motion-id climb_00_z_scale_1.0 \
  --anchor-id <anchor_id> \
  --delta-world 0.10 0.0 0.0 \
  --output-source contact/climb00_anchor_farther \
  --edit-plan data/workbench/climb00_farther.json \
  --source-motion /path/to/climb_00_z_scale_1.0.npz \
  --source-segments candidates/force_contact
```

This writes a moved ContactLayer and appends a `ContactAnchorEditRecord` to the plan. It does not modify the source `.npz` and does not run LTE/contact deformation.

Stage 2 generates augmented motion explicitly:

```bash
~/motion_edit/motion-edit validate-contact-edit-plan --plan data/workbench/climb00_farther.json
~/motion_edit/motion-edit generate-lte-augmentation --plan data/workbench/climb00_farther.json --output-motion data/exports/motions/climb00_farther.npz
```

Generation requires a `validated` or `locked` plan by default. The generation backend is currently a stub that raises a clear `NotImplementedError`; this keeps anchor dragging from accidentally producing augmented motions before the LTE/contact deformation backend is implemented.

## OmniRetarget Compatibility

`detect-motion` resolves common OmniRetarget/Holosoma paths:

- `OmniRetarget_Dataset/robot-terrain/*.npz`
- `OmniRetarget_Dataset/data/holosoma_motions_50hz/*.npz`
- terrain URDF / OBJ for `climb_XX`
- rollout/contact force demos for `climb_XX`

The viewer command currently launches the existing Holosoma Retargeting Viser cutter through an adapter. The motion-edit package owns the segment layers and exports cutter-compatible JSONL files on demand.

## Viser Cutter Sessions

`motion-edit cutter` prepares a file-based editing session for the existing Holosoma/Viser cutter:

```text
data/workbench/sessions/<session_name>/
  session.json
  <motion_id>.segments.jsonl
  <motion_id>.contact_overlay.json
```

The cutter is still the visual frontend. `motion_edit` owns the durable session, layer sync, provenance, and exports. In the preferred canonical workflow, pass `--motion-version-id ... --update-canonical`; when the cutter exits, edited segment JSONL is rebound to the ContactGraph when available and written back to `data/segments/<motion_version_id>.jsonl`. Legacy cutter sessions without `--update-canonical` still sync to `manual/<session_name>` for compatibility.

## Curation Flow

```bash
~/motion_edit/motion-edit import-force-proto --motion-dir /path/to/masked_motions --layer-name force_contact
~/motion_edit/motion-edit register-motion-asset \
  --motion-asset-id climb00 \
  --motion /path/to/climb_00_z_scale_1.0.npz \
  --fps 50 \
  --source local
~/motion_edit/motion-edit register-motion-version \
  --motion-version-id climb00_raw \
  --motion /path/to/climb_00_z_scale_1.0.npz \
  --kind raw \
  --motion-asset-id climb00 \
  --contact-layer contact/force_contact
~/motion_edit/motion-edit migrate-layer-to-canonical \
  --motion-version-id climb00_raw \
  --motion /path/to/climb_00_z_scale_1.0.npz \
  --source candidates/force_contact \
  --contact-layer contact/force_contact
~/motion_edit/motion-edit list-contact-layer --source contact/force_contact --motion-id climb_00_z_scale_1.0
~/motion_edit/motion-edit create-box-surface-catalog --motion-id climb_00_z_scale_1.0 --box box_0:1.0,0.0,0.4:0.5,0.5,0.8 --output data/surfaces/climb_00_surfaces.jsonl
~/motion_edit/motion-edit bind-contact-surfaces --contact-layer contact/force_contact --motion-id climb_00_z_scale_1.0 --surface-catalog data/surfaces/climb_00_surfaces.jsonl --output-contact-layer contact/force_contact_bound
~/motion_edit/motion-edit export-surface-binding-report --contact-layer contact/force_contact_bound --motion-id climb_00_z_scale_1.0 --output data/exports/surface_binding_reports/climb_00.json
~/motion_edit/motion-edit export-surface-binding-overlay --contact-layer contact/force_contact_bound --motion-id climb_00_z_scale_1.0 --output data/exports/surface_binding_overlays/climb_00.overlay.json
~/motion_edit/motion-edit move-contact-anchor --source contact/force_contact_bound --motion-id climb_00_z_scale_1.0 --anchor-id <anchor_id> --tangent-delta 0.10 0.00 --output-source contact/climb00_anchor_farther --edit-plan data/workbench/climb00_farther.json --source-motion /path/to/climb_00_z_scale_1.0.npz --source-segments candidates/force_contact
~/motion_edit/motion-edit validate-contact-edit-plan --plan data/workbench/climb00_farther.json
~/motion_edit/motion-edit cutter /path/to/climb_00_z_scale_1.0.npz --motion-version-id climb00_raw --update-canonical --session-name climb00_check --with-terrain
~/motion_edit/motion-edit canonical-action --motion-version-id climb00_raw --segment-id <segment_id> --action split --frame 150
~/motion_edit/motion-edit mark-segment-status --motion-version-id climb00_raw --segment-id <segment_id> --status accepted
~/motion_edit/motion-edit build-token-catalog --motion-version-id climb00_raw
~/motion_edit/motion-edit export-manifest --motion-version-id climb00_raw --output data/exports/manifests/climb00_raw.json
~/motion_edit/motion-edit export-split-npz --motion-version-id climb00_raw --status accepted
```

This keeps automatic segmentation, manual review, and downstream export in one place.
