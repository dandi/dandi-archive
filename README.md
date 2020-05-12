# dandi-publish

## Develop with Docker (preferred)
1. Run `docker-compose run web ./manage.py migrate`
2. Run `docker-compose up`

## Develop natively (advanced)
This configuration still uses Docker to run attached services in the background.
1. Run `docker-compose -f ./docker-compose.yml up -d`
2. Install Python 3.8
3. Install [`psycopg2` build prerequisites](https://www.psycopg.org/docs/install.html#build-prerequisites)
4. Install `requirements.txt` into a new active Python virtualenv
5. Export the environment variables from `./dev/.env-docker-compose-native`
6. Run `./manage.py migrate`
7. Run both:
   1. `./manage.py runserver`
   2. `celery worker --app dandi.celery --loglevel info --without-heartbeat`
8. When finished, run `docker-compose stop`
