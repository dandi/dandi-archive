# Deployment procedures

## Git branches
There are two central git branches:

- **`master`**: the active development branch. PRs should always use `master` as their merge target.
- **`release`**: the *current* release branch. This will be rebased on top of master whenever a release ocurrs.

Staging is deployed from `master`, while production is deployed from `release`.

## The `release` branch
The `release` branch is kept up to date using a GitHub CI workflow. Whenever a release ocurrs, the `release` branch is rebased on top of `master` (to avoid merge conflicts). The `release` branch should therefore always be pointed at the latest release tag.

## Netlify deployment
The staging and production Netlify sites are now both managed using a single `netlify.toml`. [Deploy contexts](https://docs.netlify.com/configure-builds/file-based-configuration/#deploy-contexts) allow us to differentiate between the production and staging sites. Production uses the default configuration, while staging uses a `branch-deploy` configuration.

## Heroku deployment
Heroku is configured to automatically deploy from `master` for the staging app and from `release` for the production app.

## Development process
To make changes to production, developers should:
- Push their changes to GitHub in a PR branch (there is currently no naming convention).
- Create a PR that will merge the PR branch to `master`.
  - Assign reviewers
  - Pay attention to CI results, investigate any failures
  - Add the `release` label and an increment label (`major`, `minor`, `patch`) to the PR. This informs [`auto`](https://intuit.github.io/) that it should make a release.
    - Not all changes necessitate an immediate release. Simply leave the labels off if you don't want to release right away.
- Once the PR is approved, merge it.
  - If the appropriate release labels are present, `auto` will increment the version number, create a new git tag with that version, and create a new GitHub release.
