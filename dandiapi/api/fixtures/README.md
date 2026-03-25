# Playwright Test Data Fixture

This directory contains a [Django fixture](https://docs.djangoproject.com/en/5.2/topics/db/fixtures/) that contains test data
for the Playwright-based e2e tests.

## How was this data generated?

To generate this data, a local DB was populated with test data and then dumped to a Django fixture using `manage.py dumpdata`. Note, the `--exclude` flags are important here because they prevent unneeded and/or deployment specific DB tables from being included in the dump.

```bash
./manage.py dumpdata --output dandiapi/api/fixtures/playwright.json.xz --exclude auth.permission --exclude authtoken --exclude contenttypes --exclude oauth2_provider --exclude sites
```
