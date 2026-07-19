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
- The UI is the single-port `motion_edit/web/server.py` + `web/` Three.js app.
- Do not reintroduce Viser, iframe wrappers, a second UI port, or file-polling bridges.
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
conda run -n env_somaforge python -m unittest discover -s tests
npm --prefix web run build
npm --prefix web exec -- playwright test
```

- Isaac Sim / CUDA failures inside Codex sandbox are expected; validate those on the local machine.
