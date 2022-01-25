import {
  CLIENT_URL,
  registerNewUser,
  registerDandiset,
  uniqueId,
  waitForRequestsToFinish,
} from '../util';
import * as homePage from '../pages/homePage';

const VERSION_LINK_REGEX = /https:\/\/github.com\/dandi\/dandi-archive\/commit\/[0-9a-f]{5,40}/;

describe('home page stats', () => {
  it('increments users stat when a new user registers', async () => {
    // wait for stats to load
    const initialUserCount = await homePage.getStat('users');

    // register a new user to increment the user count
    await registerNewUser();

    // refresh the page to get the new stats
    await page.reload();
    await waitForRequestsToFinish();

    const finalUserCount = await homePage.getStat('users');

    expect(finalUserCount).toStrictEqual(initialUserCount + 1);
  });

  it('increments dandisets stat when a new dandiset is registered', async () => {
    await registerNewUser();

    const dandisetName = `dandiset${uniqueId()}`;
    const dandisetDescription = `Description! ${uniqueId()}`;

    // The value that `homePage.getStat` looks for is retrieved via XHR, so
    // wait until all requests are finished before trying to retrieve it.
    await waitForRequestsToFinish();

    const initialDandisetCount = await homePage.getStat('dandisets');

    // register a new dandiset to increment the dandiset count
    await registerDandiset(dandisetName, dandisetDescription);

    // refresh the page to get the new stats
    await page.goto(CLIENT_URL, { timeout: 0 });
    await waitForRequestsToFinish();

    const finalDandisetCount = await homePage.getStat('dandisets');

    expect(finalDandisetCount).toStrictEqual(initialDandisetCount + 1);
  });

  it('checks version link', async () => {
    /* eslint-disable-next-line no-undef */
    const versionLink = await page.evaluate(() => document.querySelector('.version-link').getAttribute('href'));
    expect(versionLink).toMatch(VERSION_LINK_REGEX);
  });
});
