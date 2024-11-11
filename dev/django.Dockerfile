FROM python:3.11-slim

# Install system librarires for Python packages:
# * psycopg2
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
    libpq-dev gcc libc6-dev git && \
    rm -rf /var/lib/apt/lists/*

# Set some behaviors for Python.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install pre-commit. Use `pip` instead of `apt` in order to get a recent
# version instead of whatever is in the image's package lists.
RUN pip install pre-commit

# Create a normal user (that can be made to match the dev's user stats), falling
# back to root; if the root user is specified, don't actually run the `adduser`
# command.
ARG USERID=0
ARG GROUPID=0
ARG LOGIN=root
RUN if [ "${USERID}" != 0 ]; then adduser --uid ${USERID} --gid ${GROUPID} --home /home/${LOGIN} $LOGIN; fi

# Create the project folder and make the user its owner.
RUN mkdir -p /opt/django-project
RUN chown ${USERID}:${GROUPID} /opt/django-project

# Only copy the pyproject.toml, setup.py, and setup.cfg.  It will still force all install_requires to be installed,
# but find_packages() will find nothing (which is fine). When Docker Compose mounts the real source
# over top of this directory, the .egg-link in site-packages resolves to the mounted directory
# and all package modules are importable.
COPY ./pyproject.toml /opt/django-project/pyproject.toml
COPY ./setup.cfg /opt/django-project/setup.cfg
COPY ./setup.py /opt/django-project/setup.py

# Copy the pre-commit config so that the pre-commit environments can be
# constructed later.
COPY ./.pre-commit-config.yaml /opt/django-project/.pre-commit-config.yaml

# Copy git folder for setuptools_scm. Make it owned by the user so that the
# pre-commit prep steps later don't complain about "dubious ownership" of the
# git repository.
COPY --chown=${USERID}:${GROUPID} ./.git/ /opt/django-project/.git/

# Don't install as editable, so that when the directory is mounted over with `docker compose`, the
# installation still exists (otherwise the dandiapi.egg-info/ directory would be overwritten, and
# the installation would no longer exist)
RUN pip install /opt/django-project[dev]

# Switch to the normal user.
USER $LOGIN

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project

# Run the pre-commit hooks (without --all-files, so that it won't actually run
# on any files) to create a reusable package cache.
RUN pre-commit run ruff-fix-only --hook-stage manual
RUN pre-commit run ruff-format-check --hook-stage manual
RUN pre-commit run codespell
