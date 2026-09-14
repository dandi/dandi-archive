# Docker Compose Development (without VS Code)

An alternative to the recommended [dev container](../README.md) workflow.

## Setup
1. `docker compose run --rm django ./manage.py migrate`
1. `docker compose run --rm django ./manage.py createsuperuser`

## Run
1. `docker compose up`
1. Access http://localhost:8000/
1. `Ctrl+C` to stop

To include the Celery worker: `docker compose --profile celery up`

## Update
1. `docker compose down`
1. `docker compose pull`
1. `docker compose build --pull`
1. `docker compose run --rm django ./manage.py migrate`

## Reset
Remove all data and volumes: `docker compose down -v`
