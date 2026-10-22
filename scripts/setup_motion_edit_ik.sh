#!/usr/bin/env bash
# Optional PyRoki GPU optimization environment, never part of Isaac Lab setup.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
if [[ "${1:-}" == "--help" ]]; then
    echo "Usage: bash scripts/setup_motion_edit_ik.sh [conda-environment-name]"
    echo "Default: env_somaforge. Requires Conda and the completed GA setup."
    exit 0
fi
if [[ $# -gt 1 ]]; then echo "Expected at most one environment name" >&2; exit 2; fi
IK_ENV="${1:-env_somaforge}"
command -v conda >/dev/null 2>&1 || { echo "Conda is required for the optional IK environment" >&2; exit 1; }
if command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
else
    UV_BIN="$ROOT_DIR/runtime/environments/runtime-tools/bin/uv"
fi
[[ -x "$UV_BIN" ]] || { echo "Run scripts/setup_isaaclab3_newton.sh first, or install uv" >&2; exit 1; }
if ! conda run -n "$IK_ENV" python -c 'import sys; assert sys.version_info[:2] == (3, 12)' >/dev/null 2>&1; then
    conda create -y -n "$IK_ENV" python=3.12
fi
IK_PYTHON="$(conda run -n "$IK_ENV" python -c 'import sys; print(sys.executable)')"
"$UV_BIN" pip install --python "$IK_PYTHON" \
    --overrides "$ROOT_DIR/configs/motion-edit-ik-overrides.txt" \
    -r "$ROOT_DIR/configs/motion-edit-ik-requirements.txt"
for package in packages/somaforge_core packages/contact_solver packages/motion_edit; do
    "$UV_BIN" pip install --python "$IK_PYTHON" --no-deps -e "$ROOT_DIR/$package"
done
"$IK_PYTHON" -c 'import pyroki, jaxls, coal, clarabel; print("IK imports ready")'
echo "IK configured. Pass --ik-conda-env $IK_ENV to Motion Edit generation."
