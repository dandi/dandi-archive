import expectPuppeteer from 'expect-puppeteer';
import { CLIENT_URL, uniqueId } from '../util';
import {
  vAvatar,
  vBtn,
  vTextField,
  vListItem,
  vIcon,
} from '../vuetify-xpaths';


beforeAll(async () => {
  // Set the default action timeout to something greater than 500ms
  expectPuppeteer.setDefaultOptions({ timeout: 10000 });
  await page.goto(CLIENT_URL);
});

describe('account', () => {
  const username = `user${uniqueId()}`;
  const email = `${username}@kitware.com`;
  const password = 'password'; // Top secret

  it('register', async () => {
    await expect(page).toClickXPath(vBtn('Create Account'));

    await expect(page).toFillXPath(vTextField('Username'), username);
    await expect(page).toFillXPath(vTextField('Email'), email);
    await expect(page).toFillXPath(vTextField('First Name'), 'Mister');
    await expect(page).toFillXPath(vTextField('Last Name'), 'Roboto');
    await expect(page).toFillXPath(vTextField('Password'), password);
    await expect(page).toFillXPath(vTextField('Retype password'), password);

    await expect(page).toClickXPath(vBtn('Register'));

    // the user avatar contains the initials and is only rendered when logged in successfully
    await expect(page).toContainXPath(vAvatar('MR'));
  });

  it('logout', async () => {
    await expect(page).toClickXPath(vAvatar('MR'));
    await page.waitFor(500);
    await expect(page).toClickXPath(vListItem('Logout', vIcon('mdi-logout')));

    // this text is only displayed when not logged in
    await expect(page).toMatch('Want to create your own datasets?');
  });

  it('login', async () => {
    await expect(page).toClickXPath(vBtn('Login'));

    await expect(page).toFillXPath(vTextField('Username or e-mail'), username);
    await expect(page).toFillXPath(vTextField('Password'), password);

    await expect(page).toClickXPath(vBtn(['Login', vIcon('mdi-login')]));

    // the user avatar contains the initials and is only rendered when logged in successfully
    await expect(page).toContainXPath(vAvatar('MR'));
  });
});
