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
    accepted/
    rejected/
  exports/
    cutter_segments/
    manifests/
    motions/
  backups/
```

## CLI

```bash
~/motion_edit/motion-edit import-force-proto --motion-dir /path/to/masked_motions --layer-name force_contact
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
~/motion_edit/motion-edit edit-clip --input in.npz --output out.npz --start 100 --end 160
~/motion_edit/motion-edit edit-splice --output stitched.npz a.npz b.npz c.npz
~/motion_edit/motion-edit summarize
```

## Concepts

- `MotionRef`: a path reference to qpos / Holosoma fullbody / OmniRetarget motion data.
- `SegmentRecord`: one motion interval with `source`, `status`, contact metadata, and cutter export fields.
- `EditRecord`: a provenance record for edits such as clip, splice, LTE edit, terrain offset, mirror, or relative-root transforms.

## Layer Policy

- `manual/original`: imported hand-made cutter cuts.
- `manual/current_cutter`: current cutter state.
- `candidates/force_contact`: automatically extracted force-contact proto candidates.
- `accepted`: curated segments that downstream training/export should consume.
- `rejected`: candidates kept for provenance but excluded from export.

## OmniRetarget Compatibility

`detect-motion` resolves common OmniRetarget/Holosoma paths:

- `OmniRetarget_Dataset/robot-terrain/*.npz`
- `OmniRetarget_Dataset/data/holosoma_motions_50hz/*.npz`
- terrain URDF / OBJ for `climb_XX`
- rollout/contact force demos for `climb_XX`

The viewer command currently launches the existing Holosoma Retargeting Viser cutter through an adapter. The motion-edit package owns the segment layers and exports cutter-compatible JSONL files on demand.

## Curation Flow

```bash
~/motion_edit/motion-edit list-layer --source candidates/force_contact --motion-id climb_00_z_scale_1.0
~/motion_edit/motion-edit accept --source candidates/force_contact --layer-name climb00_checked --motion-id climb_00_z_scale_1.0 --index 0 --index 1
~/motion_edit/motion-edit export-split-npz --source accepted/climb00_checked
~/motion_edit/motion-edit export-manifest --source accepted/climb00_checked --output data/exports/manifests/climb00_checked.json
```

This keeps automatic segmentation, manual review, and downstream export in one place.
