import { vBtn, vListItemSubtitle, vList } from 'jest-puppeteer-vuetify';
import {
  waitForRequestsToFinish,
} from '../util';

describe('file browser page', () => {
  it('view file browser', async () => {
    await expect(page).toClickXPath(vBtn('Public Dandisets'));
    await waitForRequestsToFinish();

    // Assert that the page has loaded with a list of dandisets
    await expect(page).toClickXPath(vListItemSubtitle('DANDI:000001'));
    await expect(page).toClickXPath(vBtn('Files'));
    await waitForRequestsToFinish();

    // Ensure that the page has loaded with a folder
    await expect(page).toContainXPath(vList());
  });
});
