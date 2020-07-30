# End-to-End Tests

The end-to-end tests use [Puppeteer](https://github.com/puppeteer/puppeteer/) and [Jest](https://jestjs.io/en/) to connect to a running instance of the application and use it through a browser like a normal user would.

## Installation
```bash
cd test
yarn install
```

Puppeteer includes a bundled Chromium executable, but not all the various Chrome dependencies.
This is not generally an issue in development environments where Chrome is already installed.
Be aware of this when setting up CI or Docker images though.

## Running Tests
You will need a running instance of the app, both the `web` and `girder` components.
Assuming the web app is running at `http://localhost:8085`:
```bash
# within "test"
CLIENT_URL=http://localhost:8085 yarn run test
```

## Debugging Tests
Frequently when writing tests, they will not work the first time.
For browser based tests, it is very helpful to be able to see the state of the browser at the point of failure.
Use this command to run the browser in headful mode and extend the Jest test timeout to 1 hour:
```bash
# within "test"
CLIENT_URL=http://localhost:8085 yarn run test-debug
```
You can also include `await jestPuppeteer.debug();` at any point in the test to create a manual breakpoint.

## Writing Tests

### Behavior Driven Development (BDD)
Jest encourages BDD testing syntax.
All tests should be formatted roughly like this:
```javascript
describe('thing being tested', () => {
  it('should behave like this', async () => {
    // ... test steps ...
  });
  it('does the right thing', async () => {
    // ... test steps ...
  });
});
```
