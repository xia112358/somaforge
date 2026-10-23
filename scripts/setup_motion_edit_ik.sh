#!/usr/bin/env bash
# Compatibility entrypoint: Motion Edit IK uses the unified managed main runtime.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
if [[ "${1:-}" == "--help" ]]; then
    echo "Usage: bash scripts/setup_motion_edit_ik.sh"
    echo "Creates/checks the managed main environment shared by Motion Edit and training."
    exit 0
fi
if [[ $# -ne 0 ]]; then
    echo "Separate IK environments are retired. Use scripts/manage_environment.py --help." >&2
    exit 2
fi
exec python3 "$ROOT_DIR/scripts/manage_environment.py" create --profile main
