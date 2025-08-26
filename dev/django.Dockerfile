FROM ghcr.io/astral-sh/uv:debian

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

# Install system librarires for Python packages
# RUN apt-get update && \
#     apt-get install --no-install-recommends --yes \
#     gcc libc6-dev && \
#     rm -rf /var/lib/apt/lists/*
