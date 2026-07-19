# Move the Isaac Lab 3/Newton environment to the system trash so setup can be rerun.
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$(dirname "$SCRIPT_DIR")

source ${SCRIPT_DIR}/source_common.sh
CONDA_ENV_NAME=${CONDA_ENV_NAME:-${SOMAFORGE_CONDA_ENV:-env_somaforge}}
ENV_ROOT=$CONDA_ROOT/envs/$CONDA_ENV_NAME
SENTINEL_FILE=${WORKSPACE_DIR}/.env_setup_finished_$CONDA_ENV_NAME

if ! command -v gio >/dev/null 2>&1; then
    echo "gio is required to move environment files to the system trash." >&2
    exit 1
fi

echo "Moving these targets to the system trash:"
echo "  $ENV_ROOT"
echo "  $SENTINEL_FILE"
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

[[ ! -e $ENV_ROOT ]] || gio trash "$ENV_ROOT"
[[ ! -e $SENTINEL_FILE ]] || gio trash "$SENTINEL_FILE"
