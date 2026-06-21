# motion_edit

Standalone motion editing workbench for cutter/manual segments, contact-derived proto candidates, LTE edits, motion edits, visualization, and exports.

The package stores metadata and segment layers under `motion_edit/data/` and keeps large motion files as path references by default.

## Layout

```text
data/
  catalogs/
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
    manifests/
    motions/
  backups/
```

## CLI

```bash
~/motion_edit/motion-edit import-force-proto --motion-dir /path/to/masked_motions --layer-name force_contact
~/motion_edit/motion-edit list-contact-layer --source contact/force_contact --motion-id climb_00_z_scale_1.0
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
- `ContactEventRecord`: a contact state change such as touchdown, liftoff, support switch, or active body change.
- `ContactAnchorRecord`: a persistent body-part contact interval. This is the primary handle for later visual editing.
- `ContactPatchRecord`: a concrete contact patch attached to an anchor, currently derived from anchor intervals.
- `ContactTransitionRecord`: a transfer segment between contact states or anchors.
- `ContactGraph`: the per-motion aggregate of events, anchors, patches, and transitions.
- `SegmentRecord`: one motion interval with `source`, `status`, backward-compatible mask strings, structured contact metadata, and cutter export fields.
- `EditRecord`: a provenance record for edits such as clip, splice, LTE edit, terrain offset, mirror, or relative-root transforms.

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
~/motion_edit/motion-edit list-layer --source candidates/force_contact --motion-id climb_00_z_scale_1.0
~/motion_edit/motion-edit list-contact-layer --source contact/force_contact --motion-id climb_00_z_scale_1.0
~/motion_edit/motion-edit cutter /path/to/climb_00_z_scale_1.0.npz --source candidates/force_contact --session-name climb00_check --with-terrain
~/motion_edit/motion-edit accept --source candidates/force_contact --layer-name climb00_checked --motion-id climb_00_z_scale_1.0 --index 0 --index 1
~/motion_edit/motion-edit export-split-npz --source accepted/climb00_checked
~/motion_edit/motion-edit export-manifest --source accepted/climb00_checked --output data/exports/manifests/climb00_checked.json
```

This keeps automatic segmentation, manual review, and downstream export in one place.
