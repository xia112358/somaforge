#!/usr/bin/env bash
# Install the GA base and the pinned project overlay without replacing older environments.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ISAACLAB_PATH="${SOMAFORGE_ISAACLAB_PATH:-$HOME/isaaclab_3.0_ga}"
LAB_COMMIT=e3f7d9ff1f5d7f8280de3ece9000b7117f66bcf4
BASE_ENV="$ROOT_DIR/runtime/environments/isaaclab-ga-3.0.0-base"
PROJECT_ENV="$ROOT_DIR/runtime/environments/isaaclab-ga-3.0.0-newton-1.7.0"
python3 "$SCRIPT_DIR/bootstrap_runtime.py"
if ! command -v uv >/dev/null 2>&1; then
    TOOLS_ENV="$ROOT_DIR/runtime/environments/runtime-tools"
    [[ -f "$TOOLS_ENV/pyvenv.cfg" ]] || python3 -m venv "$TOOLS_ENV"
    "$TOOLS_ENV/bin/python" -m pip install uv==0.13.3
    export PATH="$TOOLS_ENV/bin:$PATH"
fi
if [[ -n "${SOMAFORGE_SETUP_PYTHON:-}" ]]; then
    PYTHON_BIN="$SOMAFORGE_SETUP_PYTHON"
elif ! PYTHON_BIN="$(uv python find 3.12 2>/dev/null)"; then
    uv python install 3.12
    PYTHON_BIN="$(uv python find 3.12)"
fi
"$PYTHON_BIN" -c 'import sys; assert sys.version_info[:2] == (3, 12), "SomaForge requires Python 3.12"'
if [[ ! -d "$ISAACLAB_PATH" ]]; then
    git clone --branch v3.0.0 --depth 1 https://github.com/isaac-sim/IsaacLab.git "$ISAACLAB_PATH"
fi
if [[ "$(git -C "$ISAACLAB_PATH" rev-parse HEAD)" != "$LAB_COMMIT" ]]; then
    echo "Expected Isaac Lab GA $LAB_COMMIT at $ISAACLAB_PATH; refusing to overwrite a different checkout." >&2
    exit 1
fi
# --inexact preserves optional packages; never prune a pre-existing environment.
UV_PROJECT_ENVIRONMENT="$BASE_ENV" uv sync --project "$ISAACLAB_PATH" --frozen --inexact \
    --python "$PYTHON_BIN" --extra test --extra isaacsim
[[ -f "$PROJECT_ENV/pyvenv.cfg" ]] || "$PYTHON_BIN" -m venv --without-pip "$PROJECT_ENV"
uv pip install --python "$PROJECT_ENV/bin/python" --no-deps -r "$ROOT_DIR/configs/isaaclab-ga-overlay-requirements.txt"
"$PROJECT_ENV/bin/python" - "$BASE_ENV" <<'PYCODE'
import pathlib, sys, sysconfig
site = pathlib.Path(sysconfig.get_path("purelib"))
base_site = pathlib.Path(sys.argv[1]) / "lib/python3.12/site-packages"
(site / "somaforge_ga_base.pth").write_text(f"import site; site.addsitedir({str(base_site)!r})\n")
PYCODE
for package in packages/somaforge_core packages/contact_solver packages/generator packages/motion_edit src/holosoma; do
    uv pip install --python "$PROJECT_ENV/bin/python" --no-deps -e "$ROOT_DIR/$package"
done
source "$SCRIPT_DIR/source_isaaclab3_newton_setup.sh"
python -c 'from somaforge_core.newton_collision_compat import install; print(install())'
python -c 'from somaforge_core.robot_assets import canonical_g1_asset_metadata; print(canonical_g1_asset_metadata())'
echo "SomaForge GA installed. Source scripts/source_isaaclab3_newton_setup.sh to activate."
