# Repository Working Notes

## Current Active Branch

Use this branch for current work:

```text
ui/timeline-transport-layout
```

This branch is the current consolidation line. It contains the Contact Editor UI
timeline work plus the contact-Laplacian / stable contact proto work merged from
`origin/solver/contact-laplacian-stability`.

Current intended UI entry is the Contact Editor wrapper:

```text
motion_edit/viewer/contact_timeline.py
```

Do not create or promote another primary UI path unless explicitly requested.

## Branch Status

Important branches:

```text
ui/timeline-transport-layout
  Active working branch. Continue here.

origin/solver/contact-laplacian-stability
  Historical algorithm/contact-proto development branch. Its relevant work has
  been merged into ui/timeline-transport-layout.

backup/segmentation-wrapper-main
  Backup of the accidental main-line segmentation wrapper work.
  Keep only as reference.

main / origin/main
  Older branch line that accidentally received the segmentation wrapper split.
  Do not use it as the active development base until it is intentionally cleaned.
```

The accidental segmentation wrapper work includes:

```text
motion-edit-seg cutter
motion_edit/viewer/segmentation_timeline.py
motion_edit/segmentation/cutter.py
```

These are not part of the desired primary workflow. If anything from that work is
needed later, port it deliberately into `motion_edit/viewer/contact_timeline.py`
instead of reviving a separate UI path.

The segmentation session backend is allowed on the main line:

```text
motion_edit/segmentation/session.py
motion_edit/segmentation/cli.py
motion-edit-seg start/list/trim/add/delete/relabel/save/discard
```

This CLI is a non-visual canonical segmentation draft/session utility. It must
not launch a separate wrapper UI.

## Product Direction

The current product shape is:

```text
Contact Editor
  -> ContactEditPlan
  -> generate-lte-augmentation --mode lte_fullbody
  -> generated MotionVersion
```

The preferred UI is the single browser-based Contact Editor shell:

```text
motion_edit/viewer/contact_timeline.py
```

The Viser iframe remains the 3D viewport. Timeline, transport, contact point
selection, cut-frame navigation, generation controls, and shell layout should
stay in the wrapper.

Do not reintroduce a separate segmentation timeline/wrapper as the main UI.

## Data Policy

`data/` is local runtime data and must not be tracked by Git.

`.gitignore` already ignores:

```text
data/
!data/.gitkeep
```

Before committing, verify:

```bash
git ls-files data | wc -l
```

Expected result:

```text
0
```

Local cleaned rollout/contact data may remain under `data/`, but it should show
as ignored, for example:

```text
!! data/
```

Do not `git add -f data/...` unless explicitly requested.

## Testing

After branch cleanup or UI/contact pipeline changes, run:

```bash
.venv/bin/python -m unittest discover -s tests
```

The current consolidated branch has passed:

```text
Ran 220 tests
OK (skipped=1)
```

## Collaboration Rules

Before adding, deleting, or changing code, first write a short plan and ask for
confirmation.

Exception: continuous diagnostics are allowed without asking first.

Do not silently revert user or generated changes. If the working tree is dirty,
inspect it and preserve unrelated user changes.

## Environment Note

Isaac Sim / CUDA initialization failures inside Codex sandbox are expected.
Those should be validated on the local machine environment instead.
