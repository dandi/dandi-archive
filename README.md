# dandiarchive ![ci](https://github.com/dandi/dandiarchive/actions/workflows/ci.yml/badge.svg)
The DANDI Archive web client.

## Web App

### Install
```bash
yarn install
```

### Run
Ensure the server is running locally (see instructions [here](https://github.com/dandi/dandi-api/#dandi-api)), then:
```bash
yarn run serve
```

The web app will be served at `http://localhost:8085/`.

### Test
```bash
yarn run lint
```

### Schema Migration
The web app uses TypeScript typings (src/types/schema.ts) automatically generated from the dandiset metadata JSON Schema (see https://github.com/dandi/schema). To change the schema version used (and as a result, the types), use the `yarn migrate` command.

For example, to migrate to schema version 0.5.1, run:
```bash
yarn migrate 0.5.1
```
