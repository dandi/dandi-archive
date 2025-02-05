# EMBER-DANDI Archive Web Application ![ci](https://github.com/dandi/dandi-archive/actions/workflows/frontend-ci.yml/badge.svg) [![Netlify Status](https://api.netlify.com/api/v1/badges/e7424684-fbdb-4b77-a546-d5757a0f7552/deploy-status)](https://app.netlify.com/sites/gui-dandiarchive-org/deploys)
The EMBER-DANDI Archive web application (i.e. the dandi-archive frontend).

## Develop

### Build and Run

```bash
git clone https://github.com/aplbrain/dandi-archive
cd web
yarn install
yarn run serve
```

**Note**: On Debian systems, the `yarn` command is from the unrelated `cmdtest` package.
Instead, install and use `yarnpkg`.

The web app will be served at `http://localhost:8085/`.

To be useful, this app requires a server component, which you can run locally; see the [instructions](https://github.com/aplbrain/dandi-archive/#dandi-archive).

### Test

To fix the code formatting and check for common errors, run:

```bash
yarn run lint
```

### Schema Migration
The web app uses TypeScript typings (src/types/schema.ts) that are automatically generated from the dandiset metadata's
[JSON schema](https://github.com/dandi/schema). To change the schema version (and as a result, the types),
use the `yarn migrate` command.

For example, to migrate to schema version 0.5.1, run:
```bash
yarn migrate 0.5.1
```


### Environment Variables

- VITE_APP_SERVER_DOWNTIME_MESSAGE
  - A custom error message displayed when the backend server can't be reached.
