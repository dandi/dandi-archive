# dandiarchive ![ci](https://github.com/dandi/dandi-archive/actions/workflows/frontend-ci.yml/badge.svg) [![Netlify Status](https://api.netlify.com/api/v1/badges/e7424684-fbdb-4b77-a546-d5757a0f7552/deploy-status)](https://app.netlify.com/sites/gui-dandiarchive-org/deploys)
The DANDI Archive web client.

## Develop

### Build and Run

```bash
git clone https://github.com/dandi/dandi-archive
cd web
yarn install
yarn run serve
```

**Note**: on Debian systems `yarn` command is from unrelated `cmdtest` package.
Install and use (instead of `yarn`) `yarnpkg` instead.

The web app will be served at `http://localhost:8085/`.

This app requires a server component to be useful, which you can run locally; see the [instructions](https://github.com/dandi/dandi-archive/#dandi-archive)) for doing so.

### Test

In order to fix the code formatting and check for some common errors, run:

```bash
yarn run lint
```

### Schema Migration
The web app uses TypeScript typings (src/types/schema.ts) automatically generated from the dandiset metadata JSON Schema (see https://github.com/dandi/schema). To change the schema version used (and as a result, the types), use the `yarn migrate` command.

For example, to migrate to schema version 0.5.1, run:
```bash
yarn migrate 0.5.1
```


### Environment Variables

- VUE_APP_SERVER_DOWNTIME_MESSAGE
  - A custom error message to be displayed when the backend server can't be reached
