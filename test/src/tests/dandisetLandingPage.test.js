import {
  vBtn, vListItem,
} from 'jest-puppeteer-vuetify';
import {
  uniqueId, registerNewUser, registerDandiset, logout, waitForRequestsToFinish,
} from '../util';

describe('dandiset landing page', () => {
  it('add an owner to a dandiset', async () => {
    const { username: otherUser } = await registerNewUser();
    await logout();

    const client = await page.target().createCDPSession();
    await client.send('Network.clearBrowserCookies');
    await client.send('Network.clearBrowserCache');

    const { username: owner } = await registerNewUser();

    const id = uniqueId();
    const name = `name ${id}`;
    const description = `description ${id}`;
    await registerDandiset(name, description);

    await waitForRequestsToFinish();

    // click the manage button, giving it some time to render
    await expect(page).toClickXPath(vBtn('Manage'));

    // otherUser should not be in the list of owners (yet)
    await expect(page).not.toMatch(otherUser);

    // owner should be in the list of owners
    await expect(page).toMatch(owner);

    // TODO: find a better way to do this (not using keyboard shortcuts)
    await page.keyboard.press('Tab');
    await page.type('.v-text-field__slot', otherUser);
    await waitForRequestsToFinish();
    await expect(page).toClickXPath(vListItem(otherUser));

    // otherUser should be in the list of owners now
    await expect(page).toMatch(otherUser);

    await expect(page).toClickXPath(vBtn('Save Changes'));

    // TODO: verify user shows up as owner in DLP
  });
});
