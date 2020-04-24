FROM python:3.8-slim
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
        libpq-dev gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# ENV PYTHONPATH=/code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --requirement /code/requirements.txt

WORKDIR /code
