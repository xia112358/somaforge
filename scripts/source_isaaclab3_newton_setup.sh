#!/usr/bin/env bash
# Source this file for the pinned GA runtime. Existing environments are retained.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/source_somaforge.sh"
export ISAACLAB_PATH="${SOMAFORGE_ISAACLAB_PATH:-$HOME/isaaclab_3.0_ga}"
export SOMAFORGE_NEWTON_PROFILE=main
export SOMAFORGE_NEWTON_ENV="$SOMAFORGE_ROOT/runtime/environments/isaaclab-ga-3.0.0-newton-1.7.0"
if [[ ! -f "$SOMAFORGE_NEWTON_ENV/bin/activate" ]]; then
    echo "Missing GA runtime. Run scripts/setup_isaaclab3_newton.sh" >&2
    return 1
fi
source "$SOMAFORGE_NEWTON_ENV/bin/activate"
unset PYTHONHOME HOLOSOMA_ISAACLAB3_NEWTON_HEADLESS_EXPERIENCE HOLOSOMA_ISAACLAB3_NEWTON_KIT_EXPERIENCE
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export OMNI_KIT_ACCEPT_EULA=YES
# Rebuild paths so sourcing over a prior Lab shell cannot mix checkouts.
export PYTHONPATH="$SOMAFORGE_ROOT:$SOMAFORGE_ROOT/src/holosoma"
for package in somaforge_core contact_solver generator motion_edit; do
    export PYTHONPATH="$PYTHONPATH:$SOMAFORGE_ROOT/packages/$package"
done
for package in "$ISAACLAB_PATH"/source/*; do
    [[ ! -d "$package" ]] || export PYTHONPATH="$PYTHONPATH:$package"
done
# Separate process: never preload Newton's USD before Kit in the actual application.
python -c 'from somaforge_core.newton_runtime_compat import runtime_provenance; print(runtime_provenance())' || return 1
