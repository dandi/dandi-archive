FROM python:3.13-slim
# Install system librarires for Python packages
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
    gcc libc6-dev git && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED 1

WORKDIR /opt/django
COPY . /opt/django/
RUN pip install -e .[dev]
