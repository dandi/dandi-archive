# dandiarchive [![CircleCI](https://circleci.com/gh/dandi/dandiarchive/tree/master.svg?style=svg)](https://circleci.com/gh/dandi/dandiarchive/tree/master)
The DANDI Archive web client.

## Develop

### Build and Run

```bash
git clone https://github.com/dandi/dandiarchive
cd dandiarchive
yarn install
yarn run serve
```

The web app will be served at `http://localhost:8085/`.

This app requires a server component to be useful, which you can run locally; see the [instructions](https://github.com/dandi/dandi-api/#dandi-api)) for doing so.

### Test

In order to fix the code formatting and check for some common errors, run:

```bash
yarn run lint
```

### Pull Requests and CI

In order to run all tests, you should create a new branch from the main repository (not from your fork) and create a PR to the `master` branch. If you don't have permission to do so, please ask one of the maintainers to create a new branch from the dandi repository and use your own fork to edit the code. 

Once the tests finish, you will be able to see your changes via a Netlify deploy preview, using testing datasets from the staging deployment (https://gui-staging.dandiarchive.org/).
