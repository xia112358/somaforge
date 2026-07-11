# Repository Rules

## Branching

- `main` must stay runnable and reproducible.
- Do not develop directly on `main`.
- Start new work from latest `main`:

```bash
git switch main
git pull origin main
git switch -c feat/name
```

- Use short-lived branches:
  - `feat/...` for features
  - `fix/...` for bugs
  - `exp/...` for experiments
  - `refactor/...` for cleanup
  - `docs/...` for docs
- Before merging, sync with latest main:

```bash
git fetch origin
git rebase origin/main
```

- After merge, delete finished branches.

## Commits

- Keep commits focused.
- Use concise messages:
  - `feat: ...`
  - `fix: ...`
  - `exp: ...`
  - `refactor: ...`
  - `docs: ...`

## Project Workflow

- Primary UI path is `motion-edit contact-editor`.
- Primary wrapper is `motion_edit/viewer/contact_timeline.py`.
- Do not promote segmentation wrapper UI as the main workflow.
- Current product flow:

```text
MotionAsset / MotionVersion
-> ContactGraph / surface binding
-> Contact Editor
-> ContactEditPlan
-> generate-ref
-> generated MotionVersion
```

## Data

- `data/` is local runtime data and must not be tracked.
- Before pushing, verify:

```bash
git ls-files data | wc -l
```

Expected:

```text
0
```

- Do not commit checkpoints, logs, videos, `.npz`, `.npy`, or other large runtime artifacts unless explicitly requested.

## Tests

- Before merging to `main`, run:

```bash
conda run -n env_holosoma_isaaclab3_newton python -m unittest discover -s tests
```

- Isaac Sim / CUDA failures inside Codex sandbox are expected; validate those on the local machine.
