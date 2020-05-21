FROM python:3.8-slim
# Install system librarires for Python packages:
# * psycopg2
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
        libpq-dev gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /opt/dandi-publish/requirements.txt
RUN pip install --requirement /opt/dandi-publish/requirements.txt

WORKDIR /opt/dandi-publish
