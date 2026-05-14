# DANDI Archive

<<<<<<< before updating
![](https://about.dandiarchive.org/assets/dandi_logo.svg)

## DANDI: Distributed Archives for Neurophysiology Data Integration

[DANDI](https://dandiarchive.org/) is a platform for publishing, sharing, and processing neurophysiology data
funded by the [BRAIN Initiative](https://braininitiative.nih.gov/). The archive
accepts cellular neurophysiology data including electrophysiology,
optophysiology, and behavioral time-series, and images from immunostaining
experiments. This archive is not just an endpoint to store data, it is intended as a living repository that enables
collaboration within and across labs, as well as the entry point for research.

## Structure

The dandi-archive repository contains a Django-based [backend](dandiapi/) to run the DANDI REST API, and a
Vue-based [frontend](web/) to provide a user interface to the archive.

## Resources

* To learn how to interact with the archive,
see the [DANDI Docs](https://docs.dandiarchive.org).

* To get help:
  - ask a question: https://github.com/dandi/helpdesk/discussions
  - file a feature request or bug report: https://github.com/dandi/helpdesk/issues/new/choose
  - contact the DANDI team: help@dandiarchive.org

* To understand how to hack on the archive codebase:
  - Django backend: [`DEVELOPMENT.md`](DEVELOPMENT.md)
  - Vue frontend: [`web/README.md`](web/README.md)
=======
## Setup
1. Install [VS Code with dev container support](https://code.visualstudio.com/docs/devcontainers/containers#_installation).
1. Open the project in VS Code, then run `Dev Containers: Reopen in Container`
   from the Command Palette (`Ctrl+Shift+P`).
1. Once the container is ready, open a terminal and run:
   ```sh
   ./manage.py migrate
   ./manage.py createsuperuser
   ```

## Run
Open the **Run and Debug** panel (`Ctrl+Shift+D`) and select a launch configuration:

* **Django: Server** — Starts the development server at http://localhost:8000/
* **Django: Server (eager Celery)** — Same, but Celery tasks run synchronously
  in the web process (useful for debugging task code without a worker)
* **Celery: Worker** — Starts only the Celery worker
* **Django + Celery** — Starts both the server and a Celery worker
* **Django: Management Command** — Pick and run any management command

## Test
Run the full test suite from a terminal: `tox`

Auto-format code: `tox -e format`

Run and debug individual tests from the **Testing** panel (`Ctrl+Shift+;`).

## Rebuild
After changes to the Dockerfile, Docker Compose files, or `devcontainer.json`,
run `Dev Containers: Rebuild Container` from the Command Palette (`Ctrl+Shift+P`).

For dependency changes in `pyproject.toml`, just run `uv sync --all-extras --all-groups`.
>>>>>>> after updating
