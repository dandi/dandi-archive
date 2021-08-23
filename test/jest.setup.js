// This filename is not magic; it is referenced by Jest's setupFilesAfterEnv

import { setDefaultOptions } from 'expect-puppeteer';
import { CLIENT_URL, waitForRequestsToFinish } from './src/util';

// Set the default action timeout to something greater than 500ms
setDefaultOptions({ timeout: 10000 });

// This is not redundant, do not remove it.
// It allows tests to start on the SPA in their own beforeAlls.
// It will result in an extra refresh for the first test,
// but now all methods start at the same place.
// eslint-disable-next-line jest/require-top-level-describe
beforeAll(async () => {
  await page.goto(CLIENT_URL, { timeout: 0 });
  await waitForRequestsToFinish();
});

// eslint-disable-next-line jest/require-top-level-describe
beforeEach(async () => {
  await jestPuppeteer.resetBrowser();
  // Widen the viewport to make sure puppeteer can see the full page. If we don't do this then part
  // of the navbar will be collapsed into a hamburger menu, which will break some tests
  await page.setViewport({ width: 1366, height: 768 });
  await page.goto(CLIENT_URL, { timeout: 0 });
  await waitForRequestsToFinish();
});
