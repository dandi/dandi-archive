// This filename is not magic; it is referenced by Jest's setupFilesAfterEnv

import { setDefaultOptions } from 'expect-puppeteer';
import { CLIENT_URL } from './src/util';

// Set the default action timeout to something greater than 500ms
setDefaultOptions({ timeout: 10000 });

// this is not redundant
// it allows tests to be logged in already before doing setup in their own beforeAlls
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
