# Isaac Lab 3 Newton image
# Installs the pinned Isaac Lab 3.0 GA / Isaac Sim 6.2 base and Newton 1.7 overlay.
# PyTorch supplies its CUDA 13 runtime wheels; the host must provide a compatible driver.
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

USER root

ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
ENV WORKSPACE_DIR=/workspace
ENV CONDA_ROOT=/root/.holosoma_deps/miniconda3
ENV PATH=$CONDA_ROOT/bin:$PATH

RUN mkdir -p /var/lib/apt/lists/partial && \
    apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    swig \
    curl \
    wget \
    unzip \
    git \
    sudo

# Install Miniconda
RUN curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /miniconda.sh && \
    bash /miniconda.sh -b -u -p $CONDA_ROOT

# Configure conda for non-interactive use
RUN echo ". $CONDA_ROOT/etc/profile.d/conda.sh" >> ~/.bashrc && \
    conda config --set always_yes true

RUN mkdir -p $WORKSPACE_DIR
WORKDIR $WORKSPACE_DIR

COPY . ./holosoma

RUN . $CONDA_ROOT/etc/profile.d/conda.sh && \
    cd /workspace/holosoma/scripts && \
    chmod +x setup_isaaclab3_newton.sh && \
    conda create -y -n somaforge_setup python=3.12 && \
    SOMAFORGE_SETUP_PYTHON=$CONDA_ROOT/envs/somaforge_setup/bin/python ./setup_isaaclab3_newton.sh


WORKDIR /workspace/holosoma

ENTRYPOINT []
CMD ["/bin/bash"]
