import { vBtn, vChip, vIcon } from 'jest-puppeteer-vuetify';
import {
  uniqueId,
  registerNewUser,
  registerDandiset,
  logout,
  waitForRequestsToFinish,
  clearCookiesAndCache,
  CLIENT_URL,
} from '../util';

describe('dandiset landing page', () => {
  it('add an owner to a dandiset', async () => {
    // Register a user
    const {
      email: otherUserEmail,
      firstName: otherUserFirstName,
      lastName: otherUserLastName,
    } = await registerNewUser();
    const otherUserName = `${otherUserFirstName} ${otherUserLastName}`;
    await logout();

    await clearCookiesAndCache();

    // Register another user and create a dandiset
    const { firstName: ownerFirstName, lastName: ownerLastName } = await registerNewUser();
    const ownerName = `${ownerFirstName} ${ownerLastName}`;

    const id = uniqueId();
    const name = `name ${id}`;
    const description = `description ${id}`;
    await registerDandiset(name, description);

    await waitForRequestsToFinish();

    // "owner" should be the only owner
    await expect(page).not.toContainXPath(vChip(otherUserName));
    await expect(page).toContainXPath(vChip(ownerName));

    // click the manage button
    await expect(page).toClickXPath(vBtn('Manage Owners'));

    // otherUser should not be in the list of owners (yet)
    await expect(page).not.toMatch(otherUserName);

    // owner should be in the list of owners
    await expect(page).toMatch(ownerName);
    // search for otherUser and add them as an owner
    await expect(page).toFillXPath('//label[text()="Filter users (by name/email)"]', otherUserEmail);
    await waitForRequestsToFinish();
    await expect(page).toClickXPath(vIcon('mdi-arrow-right'));

    // otherUser should be in the list of owners now
    await expect(page).toMatch(otherUserName);

    await expect(page).toClickXPath(vBtn('Done'));

    await waitForRequestsToFinish();

    // otherUser should be an owner now, too
    await expect(page).toContainXPath(vChip(otherUserName));
    await expect(page).toContainXPath(vChip(ownerName));
  });

  it('navigate to an invalid dandiset URL', async () => {
    await page.goto(new URL('/dandiset/1', CLIENT_URL).href);
    await waitForRequestsToFinish();
    await expect(page).toMatch('Error: Dandiset does not exist');
  });
});
