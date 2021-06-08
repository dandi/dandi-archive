# Staging Environment and Procedures

## Production Environment
* Django API server (`api.dandiarchive.org`), Postgres, and CloudAMQP running in Heroku
* Sponsored S3 bucket in the sponsored account in AWS
* Web GUI served at `gui.dandiarchive.org` through Netlify
* Sentry instance

## Staging Environment
* Django API server (`api-staging.dandiarchive.org`), Postgres, and CloudAMQP running in Heroku
* Private S3 bucket in the project account in AWS
* Web GUI served at `gui-staging.dandiarchive.org` through Netlify
* Sentry instance

This should exactly parallel production, except for the S3 bucket, which is private.
Nothing is actually shared, everything is hosted adjacently.

The staging server will contain some test data and some (smallish) real data that reflects the contents of production.
Developers will manage this manually and upload/delete data as necessary for testing.
All staging data is ephemeral and should never be relied on to continue existing.

## Release procedure
The staging server will track the `master` branch in `dandi-api` and will automatically redeploy whenever `master` is changed.

The production server will not track any branch. Instead, it will automatically redeploy whenever a release is tagged in GitHub.

The staging web GUI will track the `staging` branch in `dandiarchive` and will automatically redeploy whenever `staging` is changed.

The production web GUI will track the `master` branch in `dandiarchive` and will automatically redeploy whenever `master` is changed.

* A developer has a feature they want to add that impacts both the backend and the frontend.
* They checkout a new branch in `dandi-api` and `dandiarchive`, do the work, and submit related PRs in both repos.
* Once approved, the `dandi-api` PR is merged into `master` and the `dandiarchive` PR is merged into `staging`.
* The changes are tested in staging.
* Once approved, a new release of `dandi-api` is tagged, pushing the changes to production.
* Once approved, the developer manually merges `dandiarchive/staging` into `dandiarchive/master`.

## TODO
Figure out a less manual release procedure for `dandiarchive`.
