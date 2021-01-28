import {
  vBtn,
  vTextField,
  vTextarea,
} from 'jest-puppeteer-vuetify';

export const { CLIENT_URL, GIRDER_URL } = process.env;

export function uniqueId() {
  // TODO think of something cleaner
  return Date.now().toString();
}

/**
 * Authorizes the user account.
 */
export async function authorize() {
  await Promise.all([
    expect(page).toClickXPath(vBtn('Login')),
    page.waitForNavigation({ waitUntil: 'networkidle0' }),
  ]);

  await Promise.all([
    expect(page).toClickXPath('//input[@value="Authorize"]'),
    page.waitForNavigation({ waitUntil: 'networkidle0' }),
  ]);
}

/**
 * Register a new user with a random username.
 *
 * @returns {object} { username, email, password }
 */
export async function registerNewUser() {
  const username = `user${uniqueId()}`;
  const email = `mr${username}@dandi.test`;
  const password = 'XtR4-S3curi7y-p4sSw0rd'; // Top secret

  await expect(page).toClickXPath(vBtn('Login'));
  // API pages are not styled with Vuetify, so we can't use the vHelpers
  await expect(page).toClickXPath('//a[@href="/accounts/signup/"]');
  await expect(page).toFillXPath('//input[@name="email"]', email);
  await expect(page).toFillXPath('//input[@name="password1"]', password);
  await expect(page).toFillXPath('//input[@name="password2"]', password);

  await Promise.all([
    expect(page).toClickXPath('//button[@type="submit"]'),
    page.waitForNavigation({ waitUntil: 'networkidle0' }),
  ]);

  await Promise.all([
    page.goto(CLIENT_URL),
    page.waitForNavigation({ waitUntil: 'networkidle0' }),
  ]);

  await authorize(username, password);

  return { username, email, password };
}

/**
 * Registers a new dandiset.
 *
 * @param {string} name
 * @param {string} description
 */
export async function registerDandiset(name, description) {
  await expect(page).toClickXPath(vBtn('New Dandiset'));
  await expect(page).toFillXPath(vTextField('Name*'), name);
  await expect(page).toFillXPath(vTextarea('Description*'), description);
  await Promise.all([
    expect(page).toClickXPath(vBtn('Register dataset')),
    page.waitForNavigation({ waitUntil: 'networkidle0' }),
  ]);
}
