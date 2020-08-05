import {
  vBtn,
  vTextField,
  vIcon,
  vTextarea,
} from 'jest-puppeteer-vuetify';

export const { CLIENT_URL, GIRDER_URL } = process.env;

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

  // there is no way to register a new user without using OAuth
  // use the girder API to create the user instead
  await page.evaluate(({ username, email, password, GIRDER_URL }) => {
    const params = `login=${username}&email=${email}&firstName=Mister&lastName=Roboto&password=${password}&admin=false`;
    return fetch(`${GIRDER_URL}/api/v1/user?${params}`, { method: 'POST' })
  }, { username, email, password, GIRDER_URL });

  await login(username, password);

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
