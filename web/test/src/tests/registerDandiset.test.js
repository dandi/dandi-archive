import {
  vBtn,
  vListItem,
  vTextField,
  vTextarea,
} from 'jest-puppeteer-vuetify';
import { uniqueId, registerNewUser, waitForRequestsToFinish } from '../util';

describe('dandiset registration page', () => {
  it('registers a new dandiset', async () => {
    const id = uniqueId();
    const name = `name ${id}`;
    const description = `description ${id}`;

    await registerNewUser();

    await expect(page).toClickXPath(vBtn('New Dandiset'));

    await expect(page).toFillXPath(vTextField('Name*'), name);
    await expect(page).toFillXPath(vTextarea('Description*'), description);
    await expect(page).toClickXPath('//label[contains(.,"License*")]/following::input[1]');
    await page.waitForTimeout(500); // Give dropdown time to render
    await expect(page).toClickXPath(vListItem('spdx:CC0-1.0'));
    await page.waitForTimeout(500); // Form validation can *sometimes* take too long

    await expect(page).toClickXPath(vBtn('Register dataset'));
    await waitForRequestsToFinish();

    await expect(page).toMatch('Licenses: spdx:CC0-1.0');
  });
});
