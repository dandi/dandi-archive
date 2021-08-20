import {
  vAvatar,
  vBtn,
  vIcon,
  vListItem,
} from 'jest-puppeteer-vuetify';
import {
  registerNewUser, LOGIN_BUTTON_TEXT, LOGOUT_BUTTON_TEXT,
} from '../util';

describe('account management', () => {
  it('logs the user out', async () => {
    await registerNewUser();

    await expect(page).toClickXPath(vAvatar('??'));
    await expect(page).toClickXPath(vListItem(LOGOUT_BUTTON_TEXT, { action: vIcon('mdi-logout') }));

    // this text is only displayed when not logged in
    await expect(page).toMatch(LOGIN_BUTTON_TEXT);
  });

  it('logs the user in', async () => {
    await registerNewUser();

    // Logout
    await expect(page).toClickXPath(vAvatar('??'));
    await expect(page).toClickXPath(vListItem(LOGOUT_BUTTON_TEXT, { action: vIcon('mdi-logout') }));

    // Test logging in
    await expect(page).toClickXPath(vBtn(LOGIN_BUTTON_TEXT));

    // the user avatar contains the initials and is only rendered when logged in successfully
    await expect(page).toContainXPath(vAvatar('??'));
  });
});
