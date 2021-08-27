# dandiarchive [![CircleCI](https://circleci.com/gh/dandi/dandiarchive/tree/master.svg?style=svg)](https://circleci.com/gh/dandi/dandiarchive/tree/master)
The DANDI Archive web client.

## Develop

The repository is written using JavaScript ES6 together with [Vue.js framework](https://vuejs.org/) (currently we're using v.2). We are using [yarn](https://classic.yarnpkg.com/en/) as a package manager, please follow [the instruction](https://classic.yarnpkg.com/en/docs/install) if you need to install it.

### Clone and Install
```bash
git clone https://github.com/dandi/dandiarchive
cd dandiarchive
yarn install
```

### Run
```bash
yarn run serve
```
The web app will be served at `http://localhost:8085/`.

In order to interact with datasets, you have to run `dandi-api` locally, see instructions [here](https://github.com/dandi/dandi-api/#dandi-api)). Then you can access `http://localhost:8000/admin/` site in order to add assets, etc.

### Test
In order to fix the code formatting and check for some common errors, run:
```bash
yarn run lint
```

### Pull Requests and CI
In order to run all tests, you should create a new branch from the main repository (not from your fork) and create a PR to the `master` branch. If you don't have permission to do it, please ask one of the maintainers to create a new branch from the dandi repository and use your own fork to edit the code. 

Once the tests finish, you will be able to see your changes on the `netlify` platform, testing datasets from `https://gui-staging.dandiarchive.org/` will be used.
