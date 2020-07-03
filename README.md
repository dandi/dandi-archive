# dandi-publish

## Develop with Docker (recommended)

This is the simplest configuration for developers to start with.
### Initial Setup
1. Run `./dev/init-minio.sh`
2. Run `docker-compose run --rm web ./manage.py migrate`
3. Run `docker-compose run --rm web ./manage.py createsuperuser` and follow the prompts to create your own user

### Run Application
1. Run `docker-compose up`
2. When finished, use `Ctrl+C`

### Application Maintenance
Occasionally, new package dependencies or schema changes will necessitate
maintenance. To non-destructively update your development stack at any time:
1. Run `docker-compose build`
2. Run `docker-compose run --rm web ./manage.py migrate`

## Develop Natively (advanced)
This configuration still uses Docker to run attached services in the background,
but allows developers to run the Python code on their native system.

### Initial Setup
1. Run `./dev/init-minio.sh`
2. Run `docker-compose -f ./docker-compose.yml up -d`
3. Install Python 3.8
4. Install [`psycopg2` build prerequisites](https://www.psycopg.org/docs/install.html#build-prerequisites)
5. Create and activate a new Python virtualenv
6. Run `pip install -e .`
7. Run `source ./dev/.env-docker-compose-native.sh`
8. Run `./manage.py migrate`
9. Run `./manage.py createsuperuser` and follow the prompts to create your own user

### Run Application
1. Run (in separate windows) both:
   1. `./manage.py runserver`
   2. `celery worker --app dandi.celery --loglevel info --without-heartbeat`
2. When finished, run `docker-compose stop`

## Connecting to `dandiarchive`
`dandiarchive` is another application and will need to be setup and run separately. 
1. Login to the `dandiarchive` Girder client using the `publish` admin account. If 
you followed the README it will be located at `http://localhost:8080/`.
   * **NOTE**: the username of the Girder admin account used here must be `publish` for publishing to work properly. If an admin account with that username doesn't exist, it must be created.
2. Navigate to account settings, click on the 'API keys' tab, and generate an API key.
3. Save this API key and the Girder client URL in environment variables named `DJANGO_DANDI_GIRDER_API_KEY`
   and `DJANGO_DANDI_GIRDER_API_URL`.
4. Run `dandi-publish` as described above.

**NOTE**: `dandiarchive` also needs to be configured to connect to `dandi-publish`. See its README for instructions.

## Testing
### Initial Setup
Tox is required to execute all tests.
It may be installed with `pip install tox`.

### Running Tests
Run `tox` to launch the full test suite.

Individual test environments may be selectively run.
This also allows additional options to be be added.
Useful sub-commands include:
* `tox -e lint`: Run only the style checks.
* `tox -e type`: Run only the type checks.
* `tox -e py3`: Run only the unit tests.

To automatically reformat all code to comply with
some (but not all) of the style checks, run `tox -e format`.

## API Authentication
Read-only API endpoints (i.e. `GET`, `HEAD`) do not require any
authentication. All other endpoints require token authentication
to call.

### Creating a Token
Visit the URL `/admin/authtoken/token/add/` with a web browser, logging
in with the credentials entered during the `createsuperuser` setup step.
Select your user from the drop-down, and click SAVE. Copy the token value
from the KEY column in the token listing.

### Supplying the Token
In API endpoint calls, add the `Authorization` HTTP header with a value of
`Token <token_value>`. For example, for a token `1234`, include the header:
`Authorization: Token 1234`.
