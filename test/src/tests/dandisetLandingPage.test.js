import {
  vBtn, vChip, vListItem,
} from 'jest-puppeteer-vuetify';
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

    // click the manage button, giving it some time to render
    await expect(page).toClickXPath(vBtn('Manage'));

    // otherUser should not be in the list of owners (yet)
    await expect(page).not.toMatch(otherUser);

    // owner should be in the list of owners
    await expect(page).toMatch(owner);

    // search for otherUser and add them as an owner
    await expect(page).toFillXPath('//input[@placeholder="Search by first name, last name or username"]', otherUser);
    await waitForRequestsToFinish();
    await expect(page).toClickXPath(vListItem(otherUser));

    // otherUser should be in the list of owners now
    await expect(page).toMatch(otherUser);

    await expect(page).toClickXPath(vBtn('Save Changes'));

    await waitForRequestsToFinish();

    // otherUser should be an owner now, too
    await expect(page).toContainXPath(vChip(otherUser));
    await expect(page).toContainXPath(vChip(owner));
  });
});
