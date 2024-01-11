import { vBtn, vList } from 'jest-puppeteer-vuetify';
import {
  waitForRequestsToFinish,
  CLIENT_URL,
} from '../util';

describe('file browser page', () => {
  it('view file browser', async () => {
    await page.goto(new URL('/dandiset/000001', CLIENT_URL).href);
    await waitForRequestsToFinish();

    await expect(page).toClickXPath(vBtn('Files'));
    await waitForRequestsToFinish();

    // Ensure that the page has loaded with a folder
    await expect(page).toContainXPath(vList('foo'));
  });
});
