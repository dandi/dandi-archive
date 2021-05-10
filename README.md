# dandiarchive [![CircleCI](https://circleci.com/gh/dandi/dandiarchive/tree/master.svg?style=svg)](https://circleci.com/gh/dandi/dandiarchive/tree/master)
The DANDI Archive web client.

## Web App

### Install
```bash
cd web
yarn install
```

### Run
Ensure the server is running locally (see instructions [here](https://github.com/dandi/dandi-api/#dandi-api)), then:
```bash
# within "web"
yarn run serve
```

The web app will be served at `http://localhost:8085/`.

### Test
```bash
# within "web"
yarn run lint
```
