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

    // Dismiss the cookie banner, as it interferes with this test (the License
    // menu gets hidden right behind it, so the attempted click to open it does
    // not succeed).
    await page.click('button.Cookie__button');

    await expect(page).toClickXPath(vBtn('New Dandiset'));

    await expect(page).toFillXPath(vTextField('Title'), name);
    await expect(page).toFillXPath(vTextarea('Description'), description);
    await page.evaluate(() => document.querySelector('button[type="submit"]').scrollIntoView());
    await expect(page).toClickXPath('//label[contains(.,"License")]/following::input[1]');
    await page.waitForTimeout(500); // Give dropdown time to render
    await expect(page).toClickXPath(vListItem('spdx:CC0-1.0'));
    await page.waitForTimeout(500); // Form validation can *sometimes* take too long

    await expect(page).toClickXPath(vBtn('Register Dandiset'));
    await waitForRequestsToFinish();

    await expect(page).toMatch('Licenses: spdx:CC0-1.0');
  });
});
