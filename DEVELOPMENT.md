# dandi-api

## TODO

## Scripts

For frequent deployment administration tasks, `django-extensions` provides a convenient way to write and run scripts that execute in the Django context.

### refresh_metadata

```
python manage.py refresh_metadata
```

This will save all `Version`s and `Asset`s, forcing them to recompute their metadata.
This is useful any time changes are made to the precomputed metadata in `_populate_metadata`.

### create_dev_dandiset

```
python manage.py create_dev_dandiset --owner your.email@email.com --name My Dummy Dandiset
```

This creates a dummy dandiset with valid metadata and a single dummy asset.
The dandiset should be valid and publishable out of the box.
This script is a simple way to get test data into your DB without having to use dandi-cli.

### import_dandisets
```
python manage.py import_dandisets [API_URL] --all
```

This imports all dandisets (versions + metadata only, no assets) from the dandi-api deployment
living at `API_URL`. For example, to import all dandisets from the production server into your
local dev environment, run `python manage.py import_dandisets http://api.dandiarchive.org` from
your local terminal.

```
python manage.py import_dandisets [API_URL] --identifier 000005
```

This imports dandiset 000005 from `API_URL` into your local dev environment.

```
python manage.py import_dandisets [API_URL] --identifier 000005 --replace 000001
```

This imports dandiset 000005 from `API_URL` and replaces 000001 with it in your local dev environment.
