FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

<<<<<<< before updating
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
RUN mv /root/.local/bin/uv /usr/local/bin/uv
RUN mv /root/.local/bin/uvx /usr/local/bin/uvx

# Make Python more friendly to running in containers
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Make uv install content in well-known locations
ENV UV_PROJECT_ENVIRONMENT=/var/lib/venv \
  UV_CACHE_DIR=/var/cache/uv/cache \
  UV_PYTHON_INSTALL_DIR=/var/cache/uv/bin \
  # The uv cache and environment are expected to be mounted on different volumes,
  # so hardlinks won't work
  UV_LINK_MODE=symlink

USER vscode

RUN mkdir /home/vscode/uv

WORKDIR /home/vscode/dandi
=======
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Ensure Python output appears immediately in container logs.
ENV PYTHONUNBUFFERED=1

# Override Node's default of attempting to bind to IPv6 interfaces over IPv4
ENV NODE_OPTIONS=--dns-result-order=ipv4first

# Put the uv and npm caches in a separate location,
# where they can persist and be shared across containers.
# The uv cache and virtual environment are on different volumes, so hardlinks won't work.
ENV UV_CACHE_DIR=/home/vscode/pkg-cache/uv \
  UV_PYTHON_INSTALL_DIR=/home/vscode/pkg-cache/uv-python \
  UV_LINK_MODE=symlink \
  NPM_CONFIG_CACHE=/home/vscode/pkg-cache/npm

# Put the virtual environment outside the project directory,
# to improve performance on macOS and prevent accidental usage from the host machine.
# Activate it, so `uv run` doesn't need to be prefixed.
ENV UV_PROJECT_ENVIRONMENT=/home/vscode/venv \
  PATH="/home/vscode/venv/bin:$PATH"

# Put tool scratch files outside the project directory too.
ENV TOX_WORK_DIR=/home/vscode/tox \
  RUFF_CACHE_DIR=/home/vscode/.cache/ruff \
  MYPY_CACHE_DIR=/home/vscode/.cache/mypy

RUN ["chsh", "-s", "/usr/bin/zsh", "vscode"]

USER vscode

# Pre-create named volume mount points, so the new volume inherits `vscode` user ownership:
# https://docs.docker.com/engine/storage/volumes/#populate-a-volume-using-a-container
RUN ["mkdir", "/home/vscode/pkg-cache"]
>>>>>>> after updating
