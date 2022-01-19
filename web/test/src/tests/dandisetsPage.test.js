import { vBtn } from 'jest-puppeteer-vuetify';
import moment from 'moment';
import {
  uniqueId,
  registerNewUser,
  registerDandiset,
  waitForRequestsToFinish,
  MY_DANDISETS_BTN_TEXT,
} from '../util';

describe('dandisets page', () => {
  it('view "My Dandisets"', async () => {
    // register user and create a new dandiset
    const { firstName, lastName } = await registerNewUser();
    const id = uniqueId();
    const name = `name ${id}`;
    const description = `description ${id}`;
    const identifier = await registerDandiset(name, description);
    await waitForRequestsToFinish();

    await expect(page).toClickXPath(vBtn(MY_DANDISETS_BTN_TEXT));
    await waitForRequestsToFinish();

    await expect(page).toMatch(name);
    await expect(page).toMatch(`DANDI:${identifier}`);
    await expect(page).toMatch(`Contact ${lastName}, ${firstName}`);
    await expect(page).toMatch(`Updated on ${moment(new Date()).format('LL')}`);
  });
});
