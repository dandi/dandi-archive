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

The staging web GUI will track the `master` branch in `dandiarchive` and will automatically redeploy whenever `master` is changed.
The configuration variables for the staging Netlify deployment will point it at the staging server rather than the production server.
To test code changes to the web GUI, branch previews will also be pointed at the staging server.

The production web GUI will track the `master` branch in `dandiarchive` and will automatically redeploy whenever `master` is changed.

A developer has a feature they want to add that impacts both the backend and the frontend.
* They checkout a new branch in `dandi-api` and `dandiarchive`, do the work, and submit related PRs in both repos.
* Once approved, the `dandi-api` PR is merged into `master`.
* The `dandiarchive` changes are tested in the branch preview, which points at the staging environment.
* Once `dandiarchive` is approved, the developer merges the PR, and tags a new release of `dandi-api`, which is then automatically deployed to production.

A developer has a feature they want to add that only impacts the frontend.
* They checkout a new branch in `dandiarchive`, do the work, and submit a PR.
* The changes are tested in the branch preview, which points at the staging environment.
* Once approved, the developer merges the PR to `master`, which is then automatically deployed to production.

A developer has a feature they want to add that only impacts the backend.
* They checkout a new branch in `dandi-api`, do the work, and submit a PR.
* Once approved, the PR is merged to `master` and automatically deployed to `api-staging.dandiarchive.org`.
* The changes are tested directly using `api-staging.dandiarchive.org`, or through the web GUI at `gui-staging.dandiarchive.org`.
* Once everything is tested, tags a new release of `dandi-api`, which is then automatically deployed to production.

## TODO
Figure out a less manual release procedure for `dandiarchive`.
