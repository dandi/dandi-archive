# dandiarchive [![CircleCI](https://circleci.com/gh/dandi/dandiarchive/tree/master.svg?style=svg)](https://circleci.com/gh/dandi/dandiarchive/tree/master)
Infrastructure and code for the dandiarchive

Folders in this repo:

- Ansible: Ansible code for deploying the girder.dandiarchive.org site.
- web: Vue.js code for holding a Girder Web Components based client deployed at gui.dandiarchive.org .
- girder-dandi-archive: A Girder plugin for customizing the DANDI archive Girder instance.

## Developing Locally

### 1. Server

In order to get girder up and running with the required plugins, first create a python3 virtual environment.

```
mkvirtualenv dandiarchive --python=python3
```

Install girder dandiarchive plugin in editable mode.

```
cd girder-dandi-archive
pip install -e .
```

Build girder client.

```
girder build
```

Having a mongodb database locally is required to run Girder. If that is the case you are ready to get girder up and running.

```
girder serve
```

By default girder will start at port 8080 (http://localhost:8080).

1) Create an admin user, using Girder's web client. Click on the "Register" button on Girder's UI.
The first user created automatically becomes the admin user.

2) Create a filesystem assetstore (http://localhost:8080/#assetstores).

3) Set CORS settings so that the vue client can talk to the Girder server (http://localhost:8080/#settings).
In the "Advanced Settings" set the "CORS Allowed Origins" value to "*" and save.

### 2. Client

In order to the client up and running we need to install dependencies.
```
cd web
yarn install
```

Start vue client.
```
yarn run serve --port 8085
```

If you start girder in another port (etc: 8099), you can set api url in the vue .env.development file to point that server.

For example:

```
# Start girder
girder serve --port 8099

# Set VUE_APP_API_ROOT variable to http://localhost:8099/api/v1 in web/.env.development file

# Start vue client in any port you want
yarn run serve --port 8085
```

### 3. Testing

Currently there are only server side tests. In order to run the tests:

```
    cd girder-dandi-archive
    pip install -r requirements-dev.txt
    tox
```
