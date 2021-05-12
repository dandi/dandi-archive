# dandi-api

## TODO

## Scripts

For frequent deployment administration tasks, `django-extensions` provides a convenient way to write and run scripts that execute in the Django context.

### refresh_metadata

```
python manage.py runscript refresh_metadata
```

This will save all `Version`s and `Asset`s, forcing them to recompute their metadata.
This is useful any time changes are made to the precomputed metadata in `_populate_metadata`.
