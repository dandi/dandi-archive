// This filename is not magic; it is referenced by Jest's setupFilesAfterEnv

import { setDefaultOptions } from 'expect-puppeteer';
import { CLIENT_URL } from './src/util';

// Set the default action timeout to something greater than 500ms
setDefaultOptions({ timeout: 10000 });

// This is not redundant, do not remove it.
// It allows tests to start on the SPA in their own beforeAlls.
// It will result in an extra refresh for the first test,
// but now all methods start at the same place.
// eslint-disable-next-line jest/require-top-level-describe
beforeAll(async () => {
  await Promise.all([
    page.goto(CLIENT_URL),
    page.waitForNavigation({ waitUntil: 'networkidle0' }),
  ]);
});

// eslint-disable-next-line jest/require-top-level-describe
beforeEach(async () => {
  await jestPuppeteer.resetBrowser();
  await Promise.all([
    page.goto(CLIENT_URL),
    page.waitForNavigation({ waitUntil: 'networkidle0' }),
  ]);
});
