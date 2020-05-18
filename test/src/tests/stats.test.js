import {
  CLIENT_URL,
  registerNewUser,
  registerDandiset,
  uniqueId,
} from '../util';
import * as homePage from '../pages/homePage';

describe('home page stats', () => {
  beforeAll(async () => {
    await Promise.all([
      page.goto(CLIENT_URL),
      // wait until there are no active network connections for 500ms
      page.waitForNavigation({ waitUntil: 'networkidle0' }),
    ]);
  });

  it('increments users stat when a new user registers', async () => {
    // wait for stats to load
    const initialUserCount = await homePage.getStat('users');

    // register a new user to increment the user count
    await registerNewUser();

    // refresh the page to get the new stats
    await Promise.all([
      page.goto(CLIENT_URL),
      page.waitForNavigation({ waitUntil: 'networkidle0' }),
    ]);

    const finalUserCount = await homePage.getStat('users');

    expect(finalUserCount).toStrictEqual(initialUserCount + 1);
  });

  it('increments dandisets stat when a new dandiset is registered', async () => {
    const dandisetName = `dandiset${uniqueId()}`;
    const dandisetDescription = `Description! ${uniqueId()}`;

    const initialDandisetCount = await homePage.getStat('dandisets');

    // register a new dandiset to increment the dandiset count
    await registerDandiset(dandisetName, dandisetDescription);

    // refresh the page to get the new stats
    await Promise.all([
      page.goto(CLIENT_URL),
      page.waitForNavigation({ waitUntil: 'networkidle0' }),
    ]);

    const finalDandisetCount = await homePage.getStat('dandisets');

    expect(finalDandisetCount).toStrictEqual(initialDandisetCount + 1);
  });
});
