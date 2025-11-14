FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
RUN mv /root/.local/bin/uv /usr/local/bin/uv
RUN mv /root/.local/bin/uvx /usr/local/bin/uvx

# Install developer tools to make them available in devcontainers
RUN apt-get update && apt-get install --yes --no-install-recommends \
    gitk && \
  rm -rf /var/lib/apt/lists/*

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
