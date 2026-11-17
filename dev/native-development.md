# Native Development (advanced)

Runs Python on the host while using Docker Compose for services.

## Setup
1. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/)
1. Start services: `docker compose -f ./docker-compose.yml up -d`
1. Load environment: `source ./dev/export-env.sh`
1. `./manage.py migrate`
1. `./manage.py createsuperuser`

## Run
1. Ensure services are running: `docker compose -f ./docker-compose.yml up -d`
1. `source ./dev/export-env.sh`
1. `./manage.py runserver_plus`
1. In a separate terminal: `celery --app dandiapi.celery worker --loglevel INFO --without-mingle --without-heartbeat --without-gossip`
1. Access http://localhost:8000/

Stop services when done: `docker compose stop`
