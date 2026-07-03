# motion_edit

Contact-force-centered motion editing workbench for surface-bound contact-anchor editing, explicit ContactEditPlan generation, and WBT-ready policy-reference trajectories.

The canonical generated trajectory is a force-bearing policy reference: it must include `contact_force_part_w`, `contact_force_part_mask`, and `contact_force_part_order`. Old/raw rollout trajectories are retained as immutable source archives for contact extraction and force retargeting; they are not the active training/export payload. The package stores local runtime metadata and segment layers under `data/` and keeps large motion files as path references by default. `data/` is intentionally ignored by Git; do not force-add local rollout, contact, or generated motion artifacts.

## Layout

```text
data/
  catalogs/
  motions/
    raw/          # archived source refs only
    generated/    # active outputs are *.policy_ref_v1.npz force refs
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
archived source rollout with contact-force channels
  -> MotionAsset / MotionVersion source reference
  -> ContactGraph / surface binding
  -> contact-editor
  -> ContactEditPlan
  -> generate-ref
  -> WBT-ready force trajectory / generated MotionVersion
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

`contact-editor` is the only recommended interactive UI. It opens the local Viser Contact Editor wrapper page, loads registered source motions, displays the motion/timeline/contact anchors, edits surface-bound anchors, and saves a `ContactEditPlan`. Any in-editor geometry generation is diagnostic; the standard force trajectory is written by `generate-ref`. Anchor dragging is same-surface constrained: normal displacement is discarded, `surface_id`/`object_id` are preserved, and surface bounds use reject/clamp semantics.

`generate-ref` is the formal policy-reference path and the only standard output
path for generated trajectories. It runs contact-aware geometry generation with
the batch contact-Laplacian backend, retargets source contact-force phases onto
the generated contact phases, validates the WBT six-part force-reference
contract, and writes the final `*.policy_ref_v1.npz`.

```bash
~/motion_edit/motion-edit generate-ref \
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
~/motion_edit/motion-edit generate-lte-augmentation \
  --plan data/workbench/climb00_surface_edits.json \
  --output-motion /tmp/climb00_farther.geometry_debug.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --mode lte_fullbody
```

Legacy/debug commands such as `surface-editor`, `surface-editor-sync`, `cutter`, `view`, `accept`, `reject`, `import-lte-catalog`, `move-contact-anchor`, and raw segment workbench actions remain available for tests, migration, or diagnostics, but they are hidden from the main `motion-edit --help` flow. New work should enter through `contact-editor` and `generate-ref`.

## Component Boundaries

Keep these boundaries clear when debugging or adding features:

| Component | Owns | Does not own |
| --- | --- | --- |
| `motion_edit/contact/` | Contact records, ContactGraph, ContactEditPlan, ContactPhase, surface binding, layer I/O | Running fullbody generation or policy rollout |
| `motion_edit/viewer/contact_timeline.py` | Main `motion-edit contact-editor` UI and anchor-edit workflow | Segmentation cutter as a primary workflow |
| `motion_edit/generation/` | ContactEditPlan -> WBT force-ref orchestration; hidden geometry diagnostics | Low-level contact graph storage |
| `motion_edit/contact_laplacian/` | Batch contact-Laplacian solver, ContactHandleSpec, residual weights, solver metadata | Policy-force writing or simulator rollout |
| `motion_edit/contact_force/` | Canonical contact-force fields, phase retargeting, prescribed-force diagnostics | Geometry optimization |
| `motion_edit/segmentation/` | Draft segmentation sessions and legacy cutter workflow | Main contact-anchor editing |
| `motion_edit/storage/` | MotionAsset, MotionVersion, canonical segments, token catalogs | Runtime `.npz` payload ownership |
| `data/` | Local runtime data and generated artifacts | Git-tracked package source |

The formal force-aware reference path has two separate stages:

```text
optimization:
  source force -> ContactLoadProfile over contact-local phase
  -> ContactHandleSpec.load_profile
  -> solver contact residual weights

reference output:
  source contact-force phases
  -> target/generated contact phases
  -> retargeted contact_force_part_w [T, 6, 3]
```

Current force-load profiles are explicitly recorded as
`source_target_interval_mapping = same_frame_interval`. This is intentional:
the optimizer hook redistributes contact residual strength inside each known
contact interval, while the force writer retargets force vectors by local
contact phase for the final policy reference.

## Avoiding Common Errors

- Use `motion-edit contact-editor` for interactive contact-anchor editing.
  `motion-edit-seg cutter` and `surface-editor` are legacy/debug tools.
- Use `motion-edit generate-ref` for every standard generated trajectory.
- Treat files without `contact_force_part_w`, `contact_force_part_mask`, and
  `contact_force_part_order` as diagnostics or stale data, not force-ckpt
  training/export refs.
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
  `body_ang_vel_w`, `contact_force_part_w [T, 6, 3]`,
  `contact_force_part_mask [T, 6]`, and `contact_force_part_order`.
- Keep old/raw rollout `.npz` files as archived source references only. Do not
  use them as active generated trajectories for the force checkpoint.
- Inspect `motion_edit_generation_metadata`, `solver_metadata`, and
  `motion_edit_force_metadata` for trajectory quality. A file existing is not a
  quality check.
- Do not run broad cleanup such as `git clean -fd` in this checkout without
  inspecting the dry-run output; local `.agents/` and `.codex/` directories are
  workspace configuration.

## Current Branch / PR Organization

The old `solver/contact-laplacian-stability` branch mixed solver, contact segmentation, Contact Editor cuts, timeline UI, motion asset bundle work, local rollout data cleanup, and third-party proto scripts. Do not merge it as one large branch. Keep the work split in reviewable dependency order:

```text
feature/contact-laplacian-core
  batch_contact_laplacian / dual_laplacian_contact_deformation core

feature/stable-contact-proto
  stable contact proto segmentation, graph transitions, fallback policies

feature/contact-editor-cuts
  cleaned parent-limb contact phases -> editor cut frames

feature/contact-timeline-cut-ui
  Contact Editor wrapper timeline, cut-frame markers, recent motion UI

feature/motion-asset-generation-bundle
  MotionAsset bundle compatibility and generated-motion recent entries

tools/holosoma-proto-extraction
  third_party/holosoma_proto extraction/reference scripts
```

The feature stack should sit on the data cleanup baseline that stops tracking runtime `data/` artifacts. Before opening or merging a PR, verify:

```bash
git ls-files data | wc -l
```

Expected:

```text
0
```

The primary UI path remains `motion_edit/viewer/contact_timeline.py` through `motion-edit contact-editor`. Do not promote `motion_edit/viewer/segmentation_timeline.py` or `motion-edit-seg cutter` as the main workflow; those are legacy/debug paths.

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

## Force Reference Generation

The standard generation entry is `generate-ref`. It writes the force-bearing
trajectory consumed by the force checkpoint:

```bash
~/motion_edit/motion-edit generate-ref \
  --plan data/workbench/climb00_edits.json \
  --output-motion data/motions/generated/climb00.policy_ref_v1.npz \
  --output-contact-layer contact/climb00_policy_ref \
  --output-segment-layer candidates/climb00_policy_ref \
  --output-motion-version-id climb00_policy_ref \
  --register-motion-version
```

The default solver is `batch_contact_laplacian`. This is the same backend used
inside `generate-ref`: `ContactEditPlan -> body-space batch contact-Laplacian
proxy -> IK trajectory -> retargeted contact-force reference`.

The geometry-only command is hidden and should be treated as a diagnostic
intermediate producer:

```bash
~/motion_edit/motion-edit generate-lte-augmentation \
  --mode lte_fullbody \
  --plan data/workbench/climb00_edits.json \
  --output-motion /tmp/climb00.geometry_debug.npz
```

Do not put geometry-only outputs under `data/motions/generated` as canonical
training data. They are useful for debugging contact propagation before the
force writer, but they are not WBT policy references.

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

`ContactAnchor.world_position` is not enough for safe dragging. Before Viser dragging can move an anchor, the anchor should be bound to its original terrain/object surface. A bound anchor stores `object_id`, `surface_id`, normal/tangent basis, surface bounds, and `surface_coordinates`. The editor moves anchors in surface coordinates; normal motion is removed and bounds prevent dragging off the original platform/face.

Surface binding is explicit and does not generate a trajectory. It writes a new ContactLayer by default.

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

Surface binding should be inspected before using bound anchors for ContactEditPlan work or future force-reference generation. The inspection exports are diagnostic artifacts only: they do not modify motion data, do not update canonical segmentation, and do not generate `.npz` trajectory files.

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
- `Diagnostic Geometry`: write/validate the ContactEditPlan, dry-run the geometry stage, generate diagnostic geometry output, reset the session, and optionally export a debug ContactLayer. Use `generate-ref` for the standard force trajectory.

The bottom timeline top bar owns motion switching. It includes a recent-motion dropdown plus `Open`, `Open latest`, and `Reload`. All entries are treated as regular motions with the same bundle-style fields. Raw rollout motions are source/archive refs; diagnostic geometry outputs are not force-ckpt payloads. Standard generated trajectories are `generate-ref` outputs with the WBT force contract.

The bottom timeline separates contact-point intervals from edit cut frames:

- `contactPointBlock`: editable contact anchor intervals.
- `cutFrameMarker`: stable/contact-editor cut-frame boundaries.
- `proto_boundaries`: state payload for cut-frame navigation.

Avoid reviving old UI/test vocabulary such as `segmentBlock` or `protoBoundary` for the visible contact timeline.

3D selection and handle editing are same-surface constrained. Anchor markers can be clicked in the 3D view when supported by the local Viser runtime. The selected anchor shows a handle with tangent axes, normal axis, and surface bounds. Dragging this handle is not a free 3D transform: the dragged world point is projected back into the anchor's original surface coordinates, any normal component is discarded, and the anchor keeps the same `surface_id` and `object_id`. Bounds are enforced by the current reject/clamp mode. A normal-only drag is ignored as a no-op.

The local Viser direct editor renders the overlay, highlights the selected
anchor, moves anchors with same-surface constrained 3D handles, refreshes the
overlay, supports full-session reset, validates the edit plan, and can launch
diagnostic geometry generation from the Viser GUI. The final force-bearing
trajectory is still produced by `generate-ref`. A request-file bridge remains
for debug fallback but is not part of the normal workflow.

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

### Terrain Bundle Data

Terrain rendering expects the URDF bundle to be self-contained. For Holosoma/OmniRetarget climb assets, the runtime bundle has this shape:

```text
.../tmp/rollout_ref_contact_points_29/bundled/climb_00/
  multi_boxes_z_scale_1.0.urdf
  multi_boxes_z_scale_1.0.obj
  box_models/
    box1.obj
    box2.obj
    ...
```

If Viser prints an error like:

```text
Unable to resolve filename: box_models/box1.obj
Can't find box_models/box1.obj
```

that is a data bundle problem, not a Contact Editor code path problem. The URDF references `box_models/*.obj`, so copy the missing `box_models/` directory from the source terrain data into each bundled climb directory:

```bash
for d in /home/xiaz/holosoma_isaaclab3_newton/tmp/rollout_ref_contact_points_29/bundled/climb_*; do
  name=$(basename "$d")
  src="/home/xiaz/holosoma_isaaclab3_newton/OmniRetarget_Dataset/models/terrain/$name/box_models"
  if [ -d "$src" ] && [ ! -d "$d/box_models" ]; then
    cp -a "$src" "$d/box_models"
  fi
done
```

Validate that all bundled terrain URDF mesh references resolve before launching the editor:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path("/home/xiaz/holosoma_isaaclab3_newton/tmp/rollout_ref_contact_points_29/bundled")
missing = []
for urdf in sorted(root.glob("climb_*/multi_boxes_z_scale_1.0.urdf")):
    tree = ET.parse(urdf)
    for mesh in tree.findall(".//mesh"):
        filename = mesh.attrib.get("filename", "")
        if filename and not (urdf.parent / filename).exists():
            missing.append((str(urdf), filename))
print("urdfs", len(list(root.glob("climb_*/multi_boxes_z_scale_1.0.urdf"))))
print("missing_mesh_refs", len(missing))
for item in missing[:20]:
    print(item)
PY
```

The expected `missing_mesh_refs` value is `0`.

In the Viser GUI, select an anchor from the bottom timeline or 3D view, drag its same-surface contact handle, then validate the plan. The in-viewer generate button is a diagnostic geometry path; use `motion-edit generate-ref` for the final force trajectory.

Practical in-viewer workflow:

1. Filter or select an anchor.
2. Inspect the selected anchor metadata and surface binding.
3. Move by 3D same-surface drag, `du`/`dv`, step buttons, or target `u/v`.
4. Use `Reset session` or `Discard unsaved edits` if needed.
5. Click `Validate plan`.
6. Run `motion-edit generate-ref` to write the WBT-ready force trajectory.

Validation writes pending `ContactAnchorEditRecord` entries into the ContactEditPlan and marks a valid draft plan as `validated`; it does not export a ContactLayer. Diagnostic geometry generation can create a non-force intermediate for inspection, but it is not the main workflow. `Export debug ContactLayer` is available for inspection. None of these actions modify the archived source motion `.npz` or mutate canonical segmentation by default.

## Force-Centered Motion Generation

Contact-anchor editing is intentionally staged. The editor only stages edits in
a `ContactEditPlan`; force-reference generation is explicit. Use `generate-ref`
for the formal WBT policy-reference path:

```bash
~/motion_edit/motion-edit validate-contact-edit-plan --plan data/workbench/climb00_farther.json
~/motion_edit/motion-edit generate-ref \
  --plan data/workbench/climb00_farther.json \
  --output-motion data/motions/generated/climb00_farther.policy_ref_v1.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --overwrite
```

Use `generate-lte-augmentation` only when debugging the geometry stage without
writing the WBT contact-force reference:

```bash
~/motion_edit/motion-edit validate-contact-edit-plan --plan data/workbench/climb00_farther.json
~/motion_edit/motion-edit generate-lte-augmentation \
  --plan data/workbench/climb00_farther.json \
  --output-motion /tmp/climb00_farther.geometry_debug.npz \
  --output-contact-layer contact/climb00_farther \
  --output-segment-layer candidates/climb00_farther \
  --output-motion-version-id climb00_farther \
  --register-motion-version \
  --mode lte_fullbody
```

Generation requires a `validated` or `locked` plan by default. In the standard path, `generate-ref` extracts semantic `body_pos_w` keypoints from the archived source motion, applies ContactEditPlan handles through the batch contact-Laplacian proxy solve, runs IK, retargets source force phases onto the generated contact phases, and writes one final WBT-ready `*.policy_ref_v1.npz`. Legacy external LTE/IK options such as `--lte-repo-root`, `--ik-script`, and `--ik-conda-env` only matter when explicitly selecting hidden diagnostic paths.

The archived source `.npz`, source ContactLayer, and source canonical segmentation are not modified. `--output-contact-layer` writes a graph derived from the source ContactGraph with edited anchor positions. `--output-segment-layer` writes candidate segments for the generated force ref. `--register-motion-version` registers the generated force trajectory as the active MotionVersion. Canonical segmentation for that new version is only built when `--build-canonical` is passed explicitly.

## Legacy And Developer Notes

Legacy layer curation, the old Holosoma cutter adapter, manual `surface-editor`
entry points, request-file sync, old LTE catalog import, and low-level clip
editing remain in the codebase for compatibility and tests. They are hidden
from the primary `motion-edit --help` output. Prefer the main workflow unless
you are migrating old data or debugging one subsystem.

See also:

- `docs/contact_laplacian_algorithms.md` for the contact-Laplacian geometry
  backend used inside `generate-ref`.
