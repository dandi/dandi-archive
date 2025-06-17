# DANDI Archive Web Application ![ci](https://github.com/dandi/dandi-archive/actions/workflows/frontend-ci.yml/badge.svg) [![Netlify Status](https://api.netlify.com/api/v1/badges/e7424684-fbdb-4b77-a546-d5757a0f7552/deploy-status)](https://app.netlify.com/sites/gui-dandiarchive-org/deploys)
The DANDI Archive web application (i.e. the dandi-archive frontend).

## Develop

### Serve App in Development Server (requires [yarn](https://yarnpkg.com/))

```bash
git clone https://github.com/dandi/dandi-archive
cd dandi-archive/web
yarn install
yarn run dev
```

**Note**: On Debian systems, the `yarn` command is from the unrelated `cmdtest` package.
Instead, install and use `yarnpkg`.

The web app will be served at `http://localhost:8085/`.

To be useful, this app requires a server component, which you can run locally; see the [instructions](https://github.com/dandi/dandi-archive/#dandi-archive).

### Test

To fix the code formatting and check for common errors, run:

```bash
yarn run lint
```

### End-to-End (E2E) Testing

The web application includes Playwright-based e2e tests located in `../e2e/`.
See the [GitHub workflow](../.github/workflows/frontend-ci.yml) for the complete setup.

#### Required Services

You need these services running locally, see the root README:
- **PostgreSQL** (port 5432)
- **RabbitMQ** (port 5672)
- **MinIO** (port 9000) with access key `minioAccessKey` and secret `minioSecretKey`

#### Install Dependencies

```bash
# Install web app dependencies
cd web && yarn install --frozen-lockfile

# Install e2e test dependencies
cd ../e2e && yarn install --frozen-lockfile

# Install Playwright browsers
npx playwright install chromium

# On Fedora, install dependencies manually instead of --with-deps:
# npx playwright install chromium
```

#### Setup Django Backend

```bash
# From repository root
./manage.py migrate
./manage.py createcachetable
./manage.py loaddata playwright
```

#### Run Tests

```bash
# Start the backend server
python manage.py runserver &

# Start the frontend server
cd web && yarn run dev &

# Wait for servers, then run tests
cd e2e && npx playwright test

# Run specific test
npx playwright test -g "add an owner to the dandiset"

# Run with visible browser
npx playwright test --headed
```

### Schema Migration

The web app uses TypeScript typings (src/types/schema.ts) that are automatically generated from the dandiset metadata's
[JSON schema](https://github.com/dandi/schema).
These typings are used only for linting, and not to drive any functionality.
To change the schema version (and as a result, the types), use the `yarn migrate` command.

For example, to migrate to schema version 0.5.1, run:
```bash
yarn migrate 0.5.1
```

### Environment Variables

- VITE_APP_SERVER_DOWNTIME_MESSAGE
  - A custom error message displayed when the backend server can't be reached.

- VITE_APP_FOOTER_BANNER_TEXT
  - A custom message to show in an information banner on the DANDI homepage. The banner does not render if this isn't set.
