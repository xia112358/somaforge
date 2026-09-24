# Detect script directory (works in both bash and zsh)
if [ -n "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
elif [ -n "${ZSH_VERSION}" ]; then
    SCRIPT_DIR=$( cd -- "$( dirname -- "${(%):-%x}" )" &> /dev/null && pwd )
fi

ROOT_DIR=$(dirname "$SCRIPT_DIR")
source ${SCRIPT_DIR}/source_somaforge.sh

# Use a project-scoped Isaac Lab 3 / Newton environment by default.  Do not
# reuse the generic env_isaaclab env because it commonly has PhysX and older
# Isaac Sim/Lab packages installed for other projects.
CONDA_ENV_NAME=${CONDA_ENV_NAME:-${SOMAFORGE_CONDA_ENV:-env_somaforge}}
ISAACLAB_PATH=${ISAACLAB_PATH:-$HOME/isaaclab_3.0}

echo "conda environment name is set to: $CONDA_ENV_NAME"
echo "Isaac Lab path is set to: $ISAACLAB_PATH"

source ${SCRIPT_DIR}/source_common.sh
# Leave a previously activated overlay before selecting its base environment.
if [ -n "${VIRTUAL_ENV:-}" ] && type deactivate >/dev/null 2>&1; then
    deactivate
fi
source ${CONDA_ROOT}/bin/activate $CONDA_ENV_NAME

# Newton has exactly one supported runtime.  Keep the conda environment as the
# Isaac Lab base, but always overlay the project-pinned Newton main environment.
# There is deliberately no legacy selector or environment-path override.
export SOMAFORGE_NEWTON_PROFILE=main
export SOMAFORGE_NEWTON_ENV=$ROOT_DIR/runtime/environments/newton-main-20260914
if [ ! -f "$SOMAFORGE_NEWTON_ENV/bin/activate" ]; then
    echo "Missing required Newton main environment: $SOMAFORGE_NEWTON_ENV" >&2
    return 1
fi
source "$SOMAFORGE_NEWTON_ENV/bin/activate"

# Fail before launching Kit, training, evaluation, or a contact-query worker if
# shell activation ever resolves to the base environment or another Newton.
if ! python -c 'import pathlib, sys, newton
expected = pathlib.Path(sys.argv[1]).resolve()
module = pathlib.Path(newton.__file__).resolve()
prefix = pathlib.Path(sys.prefix).resolve()
if newton.__version__ != "1.7.0.dev0" or prefix != expected or not module.is_relative_to(expected):
    raise SystemExit(f"Wrong Newton runtime: version={newton.__version__}, prefix={prefix}, module={module}; expected 1.7.0.dev0 under {expected}")' "$SOMAFORGE_NEWTON_ENV"; then
    return 1
fi
echo "Newton runtime: 1.7.0.dev0 ($SOMAFORGE_NEWTON_ENV)"

export OMNI_KIT_ACCEPT_EULA=YES
export ISAACLAB_PATH
export HOLOSOMA_ISAACLAB3_NEWTON_HEADLESS_EXPERIENCE=${HOLOSOMA_ISAACLAB3_NEWTON_HEADLESS_EXPERIENCE:-$ROOT_DIR/apps/holosoma.isaaclab3_newton.headless.kit}
export HOLOSOMA_ISAACLAB3_NEWTON_KIT_EXPERIENCE=${HOLOSOMA_ISAACLAB3_NEWTON_KIT_EXPERIENCE:-$ROOT_DIR/apps/holosoma.isaaclab3_newton.kit}
export PYTHONPATH=$ROOT_DIR/src/holosoma:$ROOT_DIR/src/holosoma_retargeting:$ISAACLAB_PATH/source/isaaclab:$ISAACLAB_PATH/source/isaaclab_assets:$ISAACLAB_PATH/source/isaaclab_mimic:$ISAACLAB_PATH/source/isaaclab_newton:$ISAACLAB_PATH/source/isaaclab_ov:$ISAACLAB_PATH/source/isaaclab_rl:$ISAACLAB_PATH/source/isaaclab_tasks:$ISAACLAB_PATH/source/isaaclab_tasks_experimental:$ISAACLAB_PATH/source/isaaclab_visualizers:$PYTHONPATH
