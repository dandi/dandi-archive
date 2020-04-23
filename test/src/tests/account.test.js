import expectPuppeteer from 'expect-puppeteer';
import { CLIENT_URL, uniqueId } from '../util';
import { vAvatar, vBtn, vTextField, vListItem, vIcon } from '../vuetify-xpaths';


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
    await (await page.waitForXPath(vBtn('Create Account'))).click();

    await (await page.waitForXPath(vTextField('Username'))).type(username);
    await (await page.waitForXPath(vTextField('Email'))).type(email);
    await (await page.waitForXPath(vTextField('First Name'))).type('Mister');
    await (await page.waitForXPath(vTextField('Last Name'))).type('Roboto');
    await (await page.waitForXPath(vTextField('Password'))).type(password);
    await (await page.waitForXPath(vTextField('Retype password'))).type(password);

    await (await page.waitForXPath(vBtn('Register'))).click();

    // the user avatar contains the initials and is only rendered when logged in successfully
    await page.waitForXPath(vAvatar('MR'));
  });

  it('logout', async () => {
    await (await page.waitForXPath(vAvatar('MR'))).click();
    await page.waitFor(500);
    await (await page.waitForXPath(vListItem('Logout', vIcon('mdi-logout')))).click();

    // this text is only displayed when not logged in
    await expect(page).toMatch('Want to create your own datasets?');
  });

  it('login', async () => {
    await (await page.waitForXPath(vBtn('Login'))).click();

    await (await page.waitForXPath(vTextField('Username or e-mail'))).type(username);
    await (await page.waitForXPath(vTextField('Password'))).type(password);

    await (await page.waitForXPath(vBtn(['Login', vIcon('mdi-login')]))).click();

    // the user avatar contains the initials and is only rendered when logged in successfully
    await page.waitForXPath(vAvatar('MR'));
  });
});
