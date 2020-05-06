import {
  CLIENT_URL,
  uniqueId,
  registerNewUser,
  registerDandiset,
} from '../util';
import * as homePage from '../pages/homePage';
import * as searchPage from '../pages/searchPage';


describe('dandiset search page', () => {
  const name = `test${uniqueId()}`;
  const description = `Description ${uniqueId()}`;

  beforeAll(async () => {
    await page.goto(CLIENT_URL);
    await registerNewUser();

    // create a new dandiset that will appear in search results
    await registerDandiset(name, description);
  });

  it('finds a dandiset that exists by name', async () => {
    // search from the home page
    await page.goto(CLIENT_URL);
    await homePage.search(name);

    // there should only be one result, the dandiset we just created
    const results = await searchPage.getSearchResults();
    expect(results).toHaveLength(1);
    expect(results[0].name).toStrictEqual(name);
  });

  it('does not find a dandiset that does not exist', async () => {
    // search for a nonexistent name
    await searchPage.search(`${name}!!!`);

    // no results
    const results = await searchPage.getSearchResults();
    expect(results).toStrictEqual([]);
  });

  it('finds a dandiset that exists by description', async () => {
    // search for the description
    await searchPage.search(description);

    const results = await searchPage.getSearchResults();
    expect(results).toHaveLength(1);
    expect(results[0].name).toStrictEqual(name);
  });
});
