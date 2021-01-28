import {
  vAvatar,
  vBtn,
  vListItem,
  vIcon,
} from 'jest-puppeteer-vuetify';
import { registerNewUser } from '../util';

describe('account management', () => {
  it('logs the user out', async () => {
    await registerNewUser();

    await expect(page).toClickXPath(vAvatar('??'));
    await page.waitFor(500);
    await expect(page).toClickXPath(vListItem({ content: 'Logout', action: vIcon('mdi-logout') }));

    // this text is only displayed when not logged in
    await expect(page).toMatch('Want to create your own datasets?');
  });

  it('logs the user in', async () => {
    await registerNewUser();

    // Logout
    await expect(page).toClickXPath(vAvatar('??'));
    await page.waitFor(500);
    await expect(page).toClickXPath(vListItem('Logout', { action: vIcon('mdi-logout') }));

    // Test logging in
    await expect(page).toClickXPath(vBtn('Login'));

    // The user is still authenticated with the API server, we only need to authorize
    await Promise.all([
      // this button has the same text as the button in the app bar,
      // but also contains a mdi-login icon
      expect(page).toClickXPath('//input[@value="Authorize"]'),
      page.waitForNavigation({ waitUntil: 'networkidle0' }),
    ]);

    // the user avatar contains the initials and is only rendered when logged in successfully
    await expect(page).toContainXPath(vAvatar('??'));
  });
});
