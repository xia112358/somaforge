# Detect script directory (works in both bash and zsh)
if [ -n "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
elif [ -n "${ZSH_VERSION}" ]; then
    SCRIPT_DIR=$( cd -- "$( dirname -- "${(%):-%x}" )" &> /dev/null && pwd )
fi

ROOT_DIR=$(dirname "$SCRIPT_DIR")

# Use a project-scoped Isaac Lab 3 / Newton environment by default.  Do not
# reuse the generic env_isaaclab env because it commonly has PhysX and older
# Isaac Sim/Lab packages installed for other projects.
CONDA_ENV_NAME=${CONDA_ENV_NAME:-env_holosoma_isaaclab3_newton}
ISAACLAB_PATH=${ISAACLAB_PATH:-$HOME/isaaclab_3.0}

echo "conda environment name is set to: $CONDA_ENV_NAME"
echo "Isaac Lab path is set to: $ISAACLAB_PATH"

source ${SCRIPT_DIR}/source_common.sh
source ${CONDA_ROOT}/bin/activate $CONDA_ENV_NAME

export OMNI_KIT_ACCEPT_EULA=YES
export ISAACLAB_PATH
export HOLOSOMA_ISAACLAB3_NEWTON_HEADLESS_EXPERIENCE=${HOLOSOMA_ISAACLAB3_NEWTON_HEADLESS_EXPERIENCE:-$ROOT_DIR/apps/holosoma.isaaclab3_newton.headless.kit}
export HOLOSOMA_ISAACLAB3_NEWTON_KIT_EXPERIENCE=${HOLOSOMA_ISAACLAB3_NEWTON_KIT_EXPERIENCE:-$ROOT_DIR/apps/holosoma.isaaclab3_newton.kit}
export PYTHONPATH=$ROOT_DIR/src/holosoma:$ROOT_DIR/src/holosoma_inference:$ROOT_DIR/src/holosoma_retargeting:$ISAACLAB_PATH/source/isaaclab:$ISAACLAB_PATH/source/isaaclab_assets:$ISAACLAB_PATH/source/isaaclab_mimic:$ISAACLAB_PATH/source/isaaclab_newton:$ISAACLAB_PATH/source/isaaclab_ov:$ISAACLAB_PATH/source/isaaclab_rl:$ISAACLAB_PATH/source/isaaclab_tasks:$ISAACLAB_PATH/source/isaaclab_tasks_experimental:$ISAACLAB_PATH/source/isaaclab_visualizers:$PYTHONPATH
