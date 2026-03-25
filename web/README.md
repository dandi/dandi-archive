# DANDI Archive Web Application ![ci](https://github.com/dandi/dandi-archive/actions/workflows/frontend-ci.yml/badge.svg) [![Netlify Status](https://api.netlify.com/api/v1/badges/e7424684-fbdb-4b77-a546-d5757a0f7552/deploy-status)](https://app.netlify.com/sites/gui-dandiarchive-org/deploys)
The DANDI Archive web application (i.e. the dandi-archive frontend).

## Develop

### Serve App in Development Server

```bash
git clone https://github.com/dandi/dandi-archive
cd dandi-archive/web
npm install
npm run dev
```

The web app will be served at `http://localhost:8085/`.

To be useful, this app requires a server component, which you can run locally; see the [instructions](https://github.com/dandi/dandi-archive/#dandi-archive).

### Test

To fix the code formatting and check for common errors, run:

```bash
npm run lint
```

### Schema Migration

The web app uses TypeScript typings (src/types/schema.ts) that are automatically generated from the dandiset metadata's
[JSON schema](https://github.com/dandi/schema).
These typings are used only for linting, and not to drive any functionality.
To change the schema version (and as a result, the types), use the `npm run migrate` command.

For example, to migrate to schema version 0.5.1, run:
```bash
npm run migrate 0.5.1
```

### Environment Variables

- VITE_APP_SERVER_DOWNTIME_MESSAGE
  - A custom error message displayed when the backend server can't be reached.

- VITE_APP_FOOTER_BANNER_TEXT
  - A custom message to show in an information banner on the DANDI homepage. The banner does not render if this isn't set.
