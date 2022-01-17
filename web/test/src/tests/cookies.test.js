import { disableAllCookies } from '../util';

const COOKIE_CONSENT_MESSAGE = 'We use cookies to ensure you get the best experience on DANDI.';
const COOKIE_DISABLED_MESSAGE = 'We noticed you\'re blocking cookies - note that certain aspects of the site may not work.';

describe('cookie usage text', () => {
  it('click cookie usage acknowledgement', async () => {
    // Ensure that the cookie consent message is visible and disappears after button is clicked
    await expect(page).toMatch(COOKIE_CONSENT_MESSAGE);
    await page.click('button.Cookie__button');
    await expect(page).not.toMatch(COOKIE_CONSENT_MESSAGE);
  });

  it('test when cookies are disabled', async () => {
    // disable cookies
    await disableAllCookies();

    // Ensure that the cookie disabled message is visible and disappears after button is clicked
    await expect(page).toMatch(COOKIE_DISABLED_MESSAGE);
    await page.click('button.Cookie__button');
    await expect(page).not.toMatch(COOKIE_DISABLED_MESSAGE);
  });
});
