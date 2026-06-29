# Base CUDA image. Isaac Sim is installed into the project-scoped conda env.
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04

# Switch to root user for installation
USER root

# Environment variables
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

# Create workspace
RUN mkdir -p $WORKSPACE_DIR
WORKDIR $WORKSPACE_DIR

# Copy repository contents to holosoma
COPY . ./holosoma

##### Run setup
RUN bash /workspace/holosoma/scripts/setup_all.sh

# Set up conda activation for runtime
RUN echo "source $CONDA_ROOT/etc/profile.d/conda.sh" >> ~/.bashrc

# Set working directory
WORKDIR /workspace/holosoma

ENTRYPOINT []
CMD ["/bin/bash"]
