#!/bin/bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if ! command -v sudo &> /dev/null; then
  # in docker build sudo isn't available, but it is ok
  echo "Warning: sudo could not be found, you may need to run this script with sudo"
  function sudo { "$@"; }
  export -f sudo
fi

cd "$SCRIPT_DIR"
chmod +x setup_isaaclab3_newton.sh
OMNI_KIT_ACCEPT_EULA=1 ./setup_isaaclab3_newton.sh

cat <<'EOF'

Newton WBT setup complete.

Retargeting setup is intentionally not run by this cleanup-scoped helper.
Run scripts/setup_retargeting.sh separately only when working on retargeting.
EOF
