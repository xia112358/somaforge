#!/usr/bin/env bash
set -ex

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$(dirname "$SCRIPT_DIR")

if ! command -v sudo &> /dev/null; then
  echo "Warning: sudo could not be found, you may need to run this script with sudo"
  function sudo { "$@"; }
  export -f sudo
fi

CONDA_ENV_NAME=${CONDA_ENV_NAME:-env_holosoma_isaaclab3_newton}
ISAACLAB_PATH=${ISAACLAB_PATH:-$HOME/isaaclab_3.0}

source ${SCRIPT_DIR}/source_common.sh
ENV_ROOT=$CONDA_ROOT/envs/$CONDA_ENV_NAME
SENTINEL_FILE=${WORKSPACE_DIR}/.env_setup_finished_$CONDA_ENV_NAME

mkdir -p $WORKSPACE_DIR

if [[ ! -f $SENTINEL_FILE ]]; then
  if [[ ! -d $CONDA_ROOT ]]; then
    mkdir -p $CONDA_ROOT
    curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o $CONDA_ROOT/miniconda.sh
    bash $CONDA_ROOT/miniconda.sh -b -u -p $CONDA_ROOT
    rm $CONDA_ROOT/miniconda.sh
  fi

  if [[ ! -d $ENV_ROOT ]]; then
    $CONDA_ROOT/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true
    $CONDA_ROOT/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true
    if [[ ! -f $CONDA_ROOT/bin/mamba ]]; then
      $CONDA_ROOT/bin/conda install -y mamba -c conda-forge -n base
    fi
    MAMBA_ROOT_PREFIX=$CONDA_ROOT $CONDA_ROOT/bin/mamba create -y -n $CONDA_ENV_NAME python=3.12 -c conda-forge --override-channels
  fi

  source $CONDA_ROOT/bin/activate $CONDA_ENV_NAME

  conda install -c conda-forge -y ffmpeg libiconv libglu

  pip install --upgrade pip
  pip install -U torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128
  pip install "isaacsim[all,extscache]==6.0.0" --extra-index-url https://pypi.nvidia.com

  if [[ ! -d $ISAACLAB_PATH ]]; then
    git clone https://github.com/isaac-sim/IsaacLab.git --branch main $ISAACLAB_PATH
  fi

  sudo apt install -y cmake build-essential

  # Install only the Isaac Lab packages used by Holosoma Newton.  IsaacLab 3.0
  # still forwards several solver-common material cfg aliases through the
  # isaaclab_physx Python package, so install that package without its [newton]
  # extra and do not load its Kit extension.  Do not install isaaclab_ovphysx.
  pip install -e $ISAACLAB_PATH/source/isaaclab
  pip install -e $ISAACLAB_PATH/source/isaaclab_assets
  pip install -e $ISAACLAB_PATH/source/isaaclab_mimic
  pip install -e $ISAACLAB_PATH/source/isaaclab_newton[all]
  pip install -e $ISAACLAB_PATH/source/isaaclab_ov
  pip install -e $ISAACLAB_PATH/source/isaaclab_physx --no-deps
  pip install -e $ISAACLAB_PATH/source/isaaclab_rl[rsl-rl]
  pip install -e $ISAACLAB_PATH/source/isaaclab_tasks
  pip install -e $ISAACLAB_PATH/source/isaaclab_tasks_experimental
  pip install -e $ISAACLAB_PATH/source/isaaclab_visualizers
  pip install -e $ROOT_DIR/src/holosoma[unitree,booster]
  pip install -e $ROOT_DIR/src/holosoma_retargeting
  pip install --upgrade 'wandb>=0.21.1'

  touch $SENTINEL_FILE
fi
