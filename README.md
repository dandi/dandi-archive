# dandiarchive [![CircleCI](https://circleci.com/gh/dandi/dandiarchive/tree/master.svg?style=svg)](https://circleci.com/gh/dandi/dandiarchive/tree/master)
Infrastructure and code for the dandiarchive

| A [beta preview of the updated web app](https://refactor--gui-dandiarchive-org.netlify.com/) is online! |
| -- |

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

## Docker

Currently there is a docker-compose file which gets the necessary infrastructure up and running for dandiarchive.

In order to get up and running:

```
cd docker
docker-compose build
docker-compose up
```

This will spin up 4 containers:

1) MongoDB
2) Girder
3) Vue Web Client
4) Provision

Provision container creates a Girder admin user, creates a filesystem assetstore and set necessary CORS settings.
Credentials are username: admin, password: letmein.

When the provision container finishes, it will exit. The other three containers will remain running.

After docker-compose up succeeds and the provision container finishes, you should have:

1) Girder up and running on port 8091
2) Web client up and running on port 8092
3) MongoDB container up and running, and only visible to the other docker containers
