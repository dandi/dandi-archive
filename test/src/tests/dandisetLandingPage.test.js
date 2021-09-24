import { vChip, vListItem } from 'jest-puppeteer-vuetify';
import {
  uniqueId,
  registerNewUser,
  registerDandiset,
  logout,
  waitForRequestsToFinish,
  clearCookiesAndCache,
} from '../util';

describe('dandiset landing page', () => {
  it('add an owner to a dandiset', async () => {
    const { email: otherUser } = await registerNewUser();
    await logout();

    await clearCookiesAndCache();

    const { email: owner } = await registerNewUser();

    const id = uniqueId();
    const name = `name ${id}`;
    const description = `description ${id}`;
    await registerDandiset(name, description);

    await waitForRequestsToFinish();

    // "owner" should be the only owner
    await expect(page).not.toContainXPath(vChip(otherUser));
    await expect(page).toContainXPath(vChip(owner));

    // search for otherUser and add them as an owner
    await expect(page).toFillXPath('//input[@placeholder="enter email address"]', otherUser);
    await waitForRequestsToFinish();
    await expect(page).toClickXPath(vListItem(otherUser));

    await waitForRequestsToFinish();

    // otherUser should be an owner now, too
    await expect(page).toContainXPath(vChip(otherUser));
    await expect(page).toContainXPath(vChip(owner));
  });
});
