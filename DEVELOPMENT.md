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
