import {
  vAvatar,
} from 'jest-puppeteer-vuetify';
import {
  logoutUser, registerNewUser, LOGIN_BUTTON_TEXT, authorize,
} from '../util';

describe('account management', () => {
  it('logs the user out', async () => {
    await registerNewUser();

    await expect(page).toClickXPath(vAvatar('??'));

    await logoutUser();

    // this text is only displayed when not logged in
    await expect(page).toMatch(LOGIN_BUTTON_TEXT);
  });

  it('logs the user in', async () => {
    await registerNewUser();

    await expect(page).toClickXPath(vAvatar('??'));

    await logoutUser();

    await authorize();

    // the user avatar contains the initials and is only rendered when logged in successfully
    await expect(page).toContainXPath(vAvatar('??'));
  });
});
