# Development Guidelines

## Getting Started

You would need a local clone of the `dandi-archive` repository to develop on it.

1. Run `git clone https://github.com/dandi/dandi-archive`
1. Run `cd dandi-archive`
1. Make sure your PostgreSQL port (5432) is available.

## Develop with Docker (recommended quickstart)
This is the simplest configuration for developers to start with.

### Initial Setup
1. Run `docker compose pull` to ensure you have the latest versions of the service container images.
1. Run `docker compose build --build-arg USERID=$(id -u) --build-arg GROUPID=$(id -g) --build-arg LOGIN=$(id -n -u) --build-arg GROUPNAME=$(id -n -g)` to build the development container image. This builds the image to work with your (non-root) development user so that the linting and formatting commands work inside and outside of the container. If you prefer to build the container image so that it runs as `root`, you can omit the `--build-arg` arguments (but you will likely run into trouble running those commands).
1. Run `docker compose run --rm django ./manage.py migrate`
1. Run `docker compose run --rm django ./manage.py createsuperuser --email $(git config user.email)`
   and follow the prompts to create your own user.
   This sets your username to your git email to ensure parity with how GitHub logins work. You can also replace the command substitution expression with a literal email address, or omit the `--email` option entirely to run the command in interactive mode.
1. Run `docker compose run --rm django ./manage.py create_dev_dandiset --owner $(git config user.email)`
   to create a dummy dandiset to start working with.

### Run Application
1. Run `docker compose up`
1. Access the site, starting at http://localhost:8000/admin/
1. When finished, use `Ctrl+C`

### Application Maintenance
Occasionally, new package dependencies or schema changes will necessitate
maintenance. To non-destructively update your development stack at any time:
1. Run `docker compose pull`
1. Run `docker compose build --pull --no-cache --build-arg USERID=$(id -u) --build-arg GROUPID=$(id -g) --build-arg LOGIN=$(id -n -u) --build-arg GROUPNAME=$(id -n -g)` (omitting the `--build-arg` arguments if you did so in Step 1 of *Initial Setup* above).
1. Run `docker compose run --rm django ./manage.py migrate`

## Develop Natively (advanced)
This configuration still uses Docker to run attached services in the background,
but allows developers to run Python code on their native system.

### Initial Setup
1. Install [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/)
1. Run `docker compose -f ./docker-compose.yml up -d`
1. Install Python 3.13
1. Create and activate a new Python virtualenv
1. Run `pip install -e ".[dev]"`
1. Run `source ./dev/export-env.sh`
1. Run `./manage.py migrate`
1. Run `./manage.py createsuperuser --email $(git config user.email)` and follow the prompts.
1. Run `./manage.py create_dev_dandiset --owner $(git config user.email)`
   to create a dummy dandiset to start working with.

### Run Application
1. Ensure `docker compose -f ./docker-compose.yml up -d` is still active
1. Run:
   1. `source ./dev/export-env.sh`
   1. `./manage.py runserver`
1. Run in a separate terminal:
   1. `source ./dev/export-env.sh`
   1. `celery --app dandiapi.celery worker --loglevel INFO --without-heartbeat -Q celery,calculate_sha256,ingest_zarr_archive,manifest-worker -B`
1. When finished, run `docker compose stop`

## Testing

### Initial Setup
tox is used to execute all tests.
tox is installed automatically with the `dev` package extra.
To install the tox pytest dependencies into your environment, run `pip install -e ".[test]"`.
These are useful for IDE autocompletion or if you want to run `pytest` directly (not recommended).

When running the "Develop with Docker" configuration, all tox commands must be run as
`docker compose run --rm django tox`; extra arguments may also be appended to this form.

### Running Tests
Run `tox` to launch the full test suite.

Individual test environments may be selectively run.
This also allows additional options to be be added.
Useful sub-commands include:
* `tox -e lint`: Run only the style checks
* `tox -e type`: Run only the type checks
* `tox -e test`: Run only the pytest-driven tests
* `tox -e test -- -k test_file`: Run the pytest-driven tests that match the regular expression `test_file`
* `tox -e test -- --cov=dandiapi`: Generate a test coverage report
* `tox -e test -- --cov=dandiapi --cov-report=html`: Generate an HTML test coverage report in the `htmlcov` directory

To automatically reformat all code to comply with
some (but not all) of the style checks, run `tox -e format`.

### E2E Tests

See the [e2e README](e2e/README.md).

### Profiling with Memray
To include a memory profile with your tests, add `--memray` at the end of your test command invocation. For example, to run a memory profile with all tests, you would run `tox -e test -- --memray`. This can be used in conjunction with other pytest CLI flags (like `-k`) as well. See the `pytest-memray` [docs](https://github.com/bloomberg/pytest-memray) for more invocation details.

#### NOTE: If you have an existing dandi-archive installation in which you have previously run tox, you may need to recreate the tox environment (by adding `-r` to your tox invocation) the first time you attempt to use memray. If your attempt to use the `--memray` flag fails with `pytest: error: unrecognized arguments: --memray`, this is likely why.

## dandiarchive.org WEB Interface

This repository now also contains sources for the web interface under [web/](./web/) folder.
If you would like to develop it locally, please see [web/README.md](./web/README.md) file for instructions.

## API Authentication
Read-only API endpoints (i.e. `GET`, `HEAD`) do not require any
authentication. All other endpoints require token authentication
to call.

### Creating a Token
Visit the URL `/admin` with a web browser, logging
in with the credentials entered during the `createsuperuser` setup step.
Then go to `/swagger` and use `GET /auth/token` end-point.

### Supplying the Token
In API endpoint calls, add the `Authorization` HTTP header with a value of
`Token <token_value>`. For example, for a token `1234`, include the header:
`Authorization: Token 1234`.

## Scripts

For frequent deployment administration tasks, `django-extensions` provides a convenient way to write and run scripts that execute in the Django context.

### create_dev_dandiset

```
python manage.py create_dev_dandiset --owner $(git config user.email) --name My Dummy Dandiset
```

This creates a dummy dandiset with valid metadata and a single dummy asset.
The dandiset should be valid and publishable out of the box.
This script is a simple way to get test data into your DB without having to use dandi-cli.

## Abbreviations

- DLP: Dataset Landing Page (e.g. https://dandiarchive.org/dandiset/000027)
