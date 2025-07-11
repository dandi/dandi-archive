# End-to-End (E2E) Testing

The web application includes Playwright-based e2e tests located in `e2e/`.
See the [GitHub workflow](.github/workflows/frontend-ci.yml) for the complete setup.

### Install Dependencies

First, follow the `web/README.md` instructions to install web app dependencies, and then install the e2e requirements.

```bash
# Install e2e test dependencies
cd ../e2e && yarn install --frozen-lockfile

# Install Playwright browsers
npx playwright install --with-deps

# On some systems (ie Fedora), you will need to install the browser manually instead of --with-deps:
npx playwright install chromium
```

### Run Tests

After following instructions in `DEVELOPMENT.md` and `web/README.md`, you should have both the backend and frontend servers running on ports 8000 and 8085.

Note: Celery workers are not required for e2e tests.

Prior to executing the tests, you will need to login at `localhost:8085` to provide the superuser with a name.

```bash
cd e2e 

# Install testdata
./manage.py loaddata playwright

# Run all tests
npx playwright test

# Run specific test
npx playwright test -g "add an owner to the dandiset"

# Run with visible browser
npx playwright test --headed
```
