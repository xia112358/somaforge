# Remove the Isaac Lab 3 Newton environment so one can re-run the setup script.
# Exit on error, and print commands

# Ask for confirmation
read -p "Are you sure you want to reset the Isaac Lab 3 Newton environment? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

set -ex

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$(dirname "$SCRIPT_DIR")

source ${SCRIPT_DIR}/source_common.sh
CONDA_ENV_NAME=${CONDA_ENV_NAME:-env_holosoma_isaaclab3_newton}
ENV_ROOT=$CONDA_ROOT/envs/$CONDA_ENV_NAME
SENTINEL_FILE=${WORKSPACE_DIR}/.env_setup_finished_$CONDA_ENV_NAME

rm -rf $ENV_ROOT
rm -f $SENTINEL_FILE
