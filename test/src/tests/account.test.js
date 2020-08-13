import {
  vAvatar,
  vBtn,
  vTextField,
  vListItem,
  vIcon,
} from 'jest-puppeteer-vuetify';
import { registerNewUser } from '../util';

describe('account management', () => {
  it('logs the user out', async () => {
    await registerNewUser();

    await expect(page).toClickXPath(vAvatar('MR'));
    await page.waitFor(500);
    await expect(page).toClickXPath(vListItem({ content: 'Logout', action: vIcon('mdi-logout') }));

    // this text is only displayed when not logged in
    await expect(page).toMatch('Want to create your own datasets?');
  });

  it('logs the user in', async () => {
    const { username, password } = await registerNewUser();

    // Logout
    await expect(page).toClickXPath(vAvatar('MR'));
    await page.waitFor(500);
    await expect(page).toClickXPath(vListItem('Logout', { action: vIcon('mdi-logout') }));

    // Test logging in
    await expect(page).toClickXPath(vBtn('Login'));

    await expect(page).toFillXPath(vTextField('Username or e-mail'), username);
    await expect(page).toFillXPath(vTextField('Password'), password);

    await expect(page).toClickXPath(vBtn(['Login', vIcon('mdi-login')]));

    // the user avatar contains the initials and is only rendered when logged in successfully
    await expect(page).toContainXPath(vAvatar('MR'));
  });
});
