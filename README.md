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
~/motion_edit/motion-edit migrate-layer-to-canonical --motion-version-id climb00_raw --motion /path/to/climb_00_z_scale_1.0.npz --source candidates/force_contact --contact-layer contact/force_contact
~/motion_edit/motion-edit cutter /path/to/climb_00_z_scale_1.0.npz --motion-version-id climb00_raw --update-canonical --session-name climb00_check --with-terrain
~/motion_edit/motion-edit mark-segment-status --motion-version-id climb00_raw --segment-id SEG_ID --status accepted
~/motion_edit/motion-edit build-token-catalog --motion-version-id climb00_raw
~/motion_edit/motion-edit export-split-npz --motion-version-id climb00_raw --status accepted
~/motion_edit/motion-edit list-contact-layer --source contact/force_contact --motion-id climb_00_z_scale_1.0
~/motion_edit/motion-edit move-contact-anchor --source contact/force_contact --motion-id climb_00_z_scale_1.0 --anchor-id climb_00_z_scale_1.0_anchor_LF_000100_000140 --delta-world 0.10 0.0 0.0 --output-source contact/force_contact_farther --edit-plan data/workbench/climb00_farther.json --source-motion /path/to/climb_00_z_scale_1.0.npz
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

`accepted`, `rejected`, `manual`, and cutter-refined states are statuses or provenance fields on canonical `SegmentRecord`s. They should not become competing active segment layers for the same motion version. Legacy `data/layers/{candidates,manual,accepted,rejected}` paths remain for compatibility and migration, but the canonical path is preferred for new curation.

Split `.npz` files are export caches only. `export-split-npz` reads canonical segments and materializes clips for downstream training/export; those clips are safe to delete and regenerate.

## Layer Policy

- `manual/original`: imported hand-made cutter cuts.
- `manual/current_cutter`: current cutter state.
- `candidates/force_contact`: automatically extracted force-contact proto candidates.
- `contact/force_contact`: contact graph sidecar generated from the same masks as `candidates/force_contact`.
- `accepted`: curated segments that downstream training/export should consume.
- `rejected`: candidates kept for provenance but excluded from export.

Accept/reject writes use upsert-by-segment-id semantics. They preserve previously curated records from the same motion unless a matching `segment_id` is replaced.

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

The cutter is still the visual frontend. `motion_edit` owns the durable session, layer sync, provenance, and exports. When the cutter exits, edited segment JSONL is synced back to `manual/<session_name>` by default. If a matching ContactLayer exists, synced segments are rebound to the current ContactGraph so edited boundaries get refreshed contact events, anchors, patches, and transition metadata.

## Curation Flow

```bash
~/motion_edit/motion-edit import-force-proto --motion-dir /path/to/masked_motions --layer-name force_contact
~/motion_edit/motion-edit migrate-layer-to-canonical \
  --motion-version-id climb00_raw \
  --motion /path/to/climb_00_z_scale_1.0.npz \
  --source candidates/force_contact \
  --contact-layer contact/force_contact
~/motion_edit/motion-edit list-contact-layer --source contact/force_contact --motion-id climb_00_z_scale_1.0
~/motion_edit/motion-edit move-contact-anchor --source contact/force_contact --motion-id climb_00_z_scale_1.0 --anchor-id <anchor_id> --delta-world 0.10 0.0 0.0 --output-source contact/climb00_anchor_farther --edit-plan data/workbench/climb00_farther.json --source-motion /path/to/climb_00_z_scale_1.0.npz --source-segments candidates/force_contact
~/motion_edit/motion-edit validate-contact-edit-plan --plan data/workbench/climb00_farther.json
~/motion_edit/motion-edit cutter /path/to/climb_00_z_scale_1.0.npz --motion-version-id climb00_raw --update-canonical --session-name climb00_check --with-terrain
~/motion_edit/motion-edit mark-segment-status --motion-version-id climb00_raw --segment-id <segment_id> --status accepted
~/motion_edit/motion-edit build-token-catalog --motion-version-id climb00_raw
~/motion_edit/motion-edit export-split-npz --motion-version-id climb00_raw --status accepted
```

This keeps automatic segmentation, manual review, and downstream export in one place.
