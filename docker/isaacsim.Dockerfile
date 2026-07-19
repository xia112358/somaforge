# Isaac Lab 3 Newton image
# Runs setup_isaaclab3_newton.sh to create the env_somaforge
# conda environment with Isaac Sim 6.0 and Isaac Lab Newton.
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
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /miniconda.sh && \
    bash /miniconda.sh -b -u -p $CONDA_ROOT && \
    rm /miniconda.sh

# Configure conda for non-interactive use
RUN echo ". $CONDA_ROOT/etc/profile.d/conda.sh" >> ~/.bashrc && \
    conda config --set always_yes true

RUN mkdir -p $WORKSPACE_DIR
WORKDIR $WORKSPACE_DIR

COPY . ./holosoma

RUN . $CONDA_ROOT/etc/profile.d/conda.sh && \
    cd /workspace/holosoma/scripts && \
    chmod +x setup_isaaclab3_newton.sh && \
    OMNI_KIT_ACCEPT_EULA=1 ./setup_isaaclab3_newton.sh


WORKDIR /workspace/holosoma

ENTRYPOINT []
CMD ["/bin/bash"]
