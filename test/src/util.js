export const { CLIENT_URL } = process.env;

export function uniqueId() {
  // TODO think of something cleaner
  return Date.now().toString();
}

/**
 * Register a new user with a random username.
 *
 * @returns {object} { username, email }
 */
export async function registerNewUser() {
  const username = `user${uniqueId()}`;
  const email = `${username}@kitware.com`;
  const password = 'password'; // Top secret

  await (await page.waitForXPath(vBtn('Create Account'))).click();

  await (await page.waitForXPath(vTextField('Username'))).type(username);
  await (await page.waitForXPath(vTextField('Email'))).type(email);
  await (await page.waitForXPath(vTextField('First Name'))).type('Mister');
  await (await page.waitForXPath(vTextField('Last Name'))).type('Roboto');
  await (await page.waitForXPath(vTextField('Password'))).type(password);
  await (await page.waitForXPath(vTextField('Retype password'))).type(password);

  await (await page.waitForXPath(vBtn('Register'))).click();

  return { username, email, password };
}

/**
 * Logs in.
 *
 * @param {string} username
 * @param {string} password
 */
export async function login(username, password) {
  await (await page.waitForXPath(vBtn('Login'))).click();
  await (await page.waitForXPath(vTextField('Username or e-mail'))).type(username);
  await (await page.waitForXPath(vTextField('Password'))).type(password);
  // this button has the same text as the button in the app bar, but also contains a mdi-login icon
  await (await page.waitForXPath(vBtn(['Login', vIcon('mdi-login')]))).click();
}
