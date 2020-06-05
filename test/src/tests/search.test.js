import { uniqueId, registerNewUser, registerDandiset } from '../util';
import * as homePage from '../pages/homePage';
import * as searchPage from '../pages/searchPage';


describe('dandiset search page', () => {
  const name = `test${uniqueId()}`;
  const description = `Description ${uniqueId()}`;

  beforeAll(async () => {
    await registerNewUser();
    // create a new dandiset that will appear in search results
    await registerDandiset(name, description);
  });

  it('finds a dandiset that exists by name', async () => {
    await homePage.search(name);

    // there should only be one result, the dandiset we just created
    const results = await searchPage.getSearchResults();
    expect(results).toHaveLength(1);
    expect(results[0].name).toContain(name);
  });

  it('does not find a dandiset that does not exist', async () => {
    // search for a nonexistent name
    await homePage.search(`${name}!!!`);

    // no results
    const results = await searchPage.getSearchResults();
    expect(results).toStrictEqual([]);
  });

  it('finds a dandiset that exists by description', async () => {
    await homePage.search(description);

    const results = await searchPage.getSearchResults();
    expect(results).toHaveLength(1);
    expect(results[0].name).toContain(name);
  });
});
