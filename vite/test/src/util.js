import {
  vAvatar,
  vBtn,
  vIcon,
  vListItem,
  vTextField,
  vTextarea,
} from 'jest-puppeteer-vuetify';

export const { CLIENT_URL } = process.env;

export const LOGIN_BUTTON_TEXT = 'Log In with GitHub';
export const LOGOUT_BUTTON_TEXT = 'Logout';
export const MY_DANDISETS_BTN_TEXT = 'My Dandisets';

export function uniqueId() {
  // TODO think of something cleaner
  return Date.now().toString();
}

export const TEST_USER_FIRST_NAME = 'Test';
export const TEST_USER_LAST_NAME = `User_${uniqueId()}`;

export const TEST_USER_INITIALS = `${TEST_USER_FIRST_NAME.charAt(0)}${TEST_USER_LAST_NAME.charAt(0)}`;

/**
 * Waits for all network requests to finish before continuing.
 */
export async function waitForRequestsToFinish() {
  try {
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 5000 });
  } catch (e) {
    // ignore
  }
}

/**
 * Log in a user
 */
export async function login() {
  await expect(page).toClickXPath(vBtn(LOGIN_BUTTON_TEXT));
}

/**
 * Register a new user with a random username.
 *
 * @returns {object} { username, email, password, firstName, lastName }
 */
export async function registerNewUser() {
  const username = `user${uniqueId()}`;
  const email = `mr${username}@dandi.test`;
  const password = 'XtR4-S3curi7y-p4sSw0rd'; // Top secret

  const firstName = TEST_USER_FIRST_NAME;
  const lastName = `${TEST_USER_LAST_NAME}_${uniqueId()}`;

  await expect(page).toClickXPath(vBtn(LOGIN_BUTTON_TEXT));

  await waitForRequestsToFinish();

  // puppeteer sometimes can't detect the signup link to click, so just navigate to it manually.
  // This login/signup page is not used in production anyway, so we're not missing anything
  // in terms of testing.
  await page.goto(page.url().replace('/accounts/login', '/accounts/signup'));

  // API pages are not styled with Vuetify, so we can't use the vHelpers
  await expect(page).toFillXPath('//input[@name="email"]', email);
  await expect(page).toFillXPath('//input[@name="password1"]', password);
  await expect(page).toFillXPath('//input[@name="password2"]', password);

  // The locator is different in CI for some reason, just click the first button
  await expect(page).toClickXPath('//button');
  await waitForRequestsToFinish();

  await expect(page).toFillXPath('//input[@name="First Name"]', firstName);
  await expect(page).toFillXPath('//input[@name="Last Name"]', lastName);

  await expect(page).toClickXPath('//button');
  await waitForRequestsToFinish();

  await page.goto(CLIENT_URL, { timeout: 0 });
  await waitForRequestsToFinish();

  return {
    username, email, password, firstName, lastName,
  };
}

/**
 * Registers a new dandiset.
 *
 * @param {string} name
 * @param {string} description
 *
 * @returns {string} identifier of the new dandiset
 */
export async function registerDandiset(name, description) {
  // Dismiss the cookie banner, as it interferes with this test (the License
  // menu gets hidden right behind it, so the attempted click to open it does
  // not succeed).
  //
  // This is conditional on the banner's existence because some tests run this
  // function twice and the click will fail on the second run in those cases.
  const cookieBanner = await page.$('button.Cookie__button');
  if (cookieBanner) {
    await cookieBanner.click();
  }

  await expect(page).toClickXPath(vBtn('New Dandiset'));
  await expect(page).toFillXPath(vTextField('Title'), name);
  await expect(page).toFillXPath(vTextarea('Description'), description);
  // eslint-disable-next-line no-undef
  await page.evaluate(() => document.querySelector('button[type="submit"]').scrollIntoView());
  await expect(page).toClickXPath('//label[contains(.,"License")]/following::input[1]');
  await page.waitForTimeout(500); // Give dropdown time to render
  await expect(page).toClickXPath(vListItem('spdx:CC0-1.0'));
  await page.waitForTimeout(500); // Form validation can *sometimes* take too long
  await expect(page).toClickXPath(vBtn('Register Dandiset'));
  await waitForRequestsToFinish();
  return page.url().split('/').pop();
}

/**
 * Clears browser cookies and cache.
 */
export async function clearCookiesAndCache() {
  const client = await page.target().createCDPSession();
  await client.send('Network.clearBrowserCookies');
  await client.send('Network.clearBrowserCache');
}

/**
 * Disables all cookies (3rd party and otherwise) in the current browser session.
 */
export async function disableAllCookies() {
  const client = await page.target().createCDPSession();
  await client.send('Emulation.setDocumentCookieDisabled', { disabled: true });
  await page.reload();
  await waitForRequestsToFinish();
}

/**
 * Log out a user
 */
export async function logout() {
  await expect(page).toClickXPath(vAvatar(TEST_USER_INITIALS));
  await page.waitForTimeout(500);
  await expect(page).toClickXPath(vListItem(LOGOUT_BUTTON_TEXT, { action: vIcon('mdi-logout') }));
  await clearCookiesAndCache();
}
