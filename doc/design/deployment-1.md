# Deployment procedures

## Current situation
Currently, we have a single `master` git branch. A GitHub CI workflow is triggered whenever anything is merged into `master` and deploys the changes to staging. [`auto`](https://intuit.github.io/) creates git tags and releases, which trigger a GitHub CI workflow which deploys to production.

The staging Netlify site is deployed automatically from `master`. The production Netlify site is deployed manually using the Netlify CLI from a GitHub CI workflow. This workflow also deletes the `netlify.toml` file so that it can manually specify the production configuration.

The staging and production Heroku apps are deployed manually from a GitHub CI workflow using a GitHub action.

Netlify and Heroku can deploy themselves automatically from a branch, but not from a release tag. This means we need to deploy manually from GitHub CI, which is quite complex and not ideal. Additionally, Netlify does not support multiple `netlify.toml` configuration files in a single project directory, which means the deployment CI step deletes the `netlify.toml` in the production deployment and specifies the environment with the Netlify CLI instead.

This proposed solution is to use a second `release` branch which tracks the released code. This allows us to use the automatic Netlify and Heroku deployments rather than pushing manually from GitHub CI.

## Git branches
There are two central git branches:

- **`master`**: the active development branch. PRs should always use `master` as their merge target.
- **`release`**: the *current* release branch. This will be reset to point to the top of master whenever a release occurs.

Staging is deployed from `master`, while production is deployed from `release`.

## The `release` branch
The `release` branch is kept up to date using a GitHub CI workflow. Whenever a release occurs, the `release` branch is reset to point to `master` (to avoid merge conflicts). The `release` branch should therefore always be pointed at the latest release tag.

## Netlify deployment
The staging and production Netlify sites are now both managed using a single `netlify.toml`. [Deploy contexts](https://docs.netlify.com/configure-builds/file-based-configuration/#deploy-contexts) allow us to differentiate between the production and staging sites. Production uses the default configuration, while staging uses a `branch-deploy` configuration.

## Heroku deployment
GitHub CI workflows [backend-staging-deploy.yml](../../.github/workflows/backend-staging-deploy.yml) and [backend-production-deploy.yml](../../.github/workflows/backend-production-deploy.yml) are used to deploy the staging and production Heroku apps respectively.

## Development process
To make changes to production, developers should:
- Push their changes to GitHub in a PR branch (there is currently no naming convention).
- Create a PR that will merge the PR branch to `master`.
  - Assign reviewers
  - Pay attention to CI results, investigate any failures
  - Add increment or "type" label (`major`, `minor`, `patch`, `documentation`, `tests`) to the PR.
    This informs [`auto`](https://intuit.github.io/) which section to attribute a corresponding changelog entry and what version bump to perform.
    See the [full list of default labels for auto](https://intuit.github.io/auto/docs/configuration/autorc#labels).
  - Add the `release` label to trigger [`auto`](https://intuit.github.io/) to make a release on merge.
    - Not all changes necessitate an immediate release. Simply leave the `release` label off if you don't want to release right away. The increment/type label will still be accounted for in a future auto release.
- Once the PR is approved, merge it.
  - If the appropriate release labels are present, `auto` will increment the version number, create a new git tag with that version, and create a new GitHub release.
