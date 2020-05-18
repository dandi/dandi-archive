import {
  vBtn,
  vTextField,
  vIcon,
  vTextarea,
} from 'jest-puppeteer-vuetify';

export const { CLIENT_URL } = process.env;

export function uniqueId() {
  // TODO think of something cleaner
  return Date.now().toString();
}

/**
 * Register a new user with a random username.
 *
 * @returns {object} { username, email, password }
 */
export async function registerNewUser() {
  const username = `user${uniqueId()}`;
  const email = `${username}@dandi.test`;
  const password = 'password'; // Top secret

  await expect(page).toClickXPath(vBtn('Create Account'));

  await expect(page).toFillXPath(vTextField('Username'), username);
  await expect(page).toFillXPath(vTextField('Email'), email);
  await expect(page).toFillXPath(vTextField('First Name'), 'Mister');
  await expect(page).toFillXPath(vTextField('Last Name'), 'Roboto');
  await expect(page).toFillXPath(vTextField('Password'), password);
  await expect(page).toFillXPath(vTextField('Retype password'), password);

  await Promise.all([
    expect(page).toClickXPath(vBtn('Register')),
    page.waitForNavigation({ waitUntil: 'networkidle0' }),
  ]);

  return { username, email, password };
}

/**
 * Logs in.
 *
 * @param {string} username
 * @param {string} password
 */
export async function login(username, password) {
  await expect(page).toClickXPath(vBtn('Login'));
  await expect(page).toFillXPath(vTextField('Username or e-mail'), username);
  await expect(page).toFillXPath(vTextField('Password'), password);
  await Promise.all([
    // this button has the same text as the button in the app bar,
    // but also contains a mdi-login icon
    expect(page).toClickXPath(vBtn(['Login', vIcon('mdi-login')])),
    page.waitForNavigation({ waitUntil: 'networkidle0' }),
  ]);
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
