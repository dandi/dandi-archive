FROM python:3.11-slim
# Install system librarires for Python packages:
# * psycopg2
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
    libpq-dev gcc libc6-dev git && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED 1

WORKDIR /opt/django
COPY . /opt/django/
RUN pip install -e .[dev]
