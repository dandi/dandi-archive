import { vBtn, vIcon, vTextField } from 'jest-puppeteer-vuetify';
import { faker } from '@faker-js/faker';
import moment from 'moment';
import {
  uniqueId,
  registerNewUser,
  registerDandiset,
  waitForRequestsToFinish,
  MY_DANDISETS_BTN_TEXT,
} from '../util';

describe('dandisets page', () => {
  it('view "My Dandisets"', async () => {
    // register user and create a new dandiset
    const { firstName, lastName } = await registerNewUser();
    const id = uniqueId();
    const name = `name ${id}`;
    const description = `description ${id}`;
    const identifier = await registerDandiset(name, description);
    await waitForRequestsToFinish();

    await expect(page).toClickXPath(vBtn(MY_DANDISETS_BTN_TEXT));
    await waitForRequestsToFinish();

    await expect(page).toMatch(name);
    await expect(page).toMatch(`DANDI:${identifier}`);
    await expect(page).toMatch(`Contact ${lastName}, ${firstName}`);
    await expect(page).toMatch(`Updated on ${moment(new Date()).format('LL')}`);
  });

  it('search for dandisets', async () => {
    await registerNewUser();

    const dandisetIdentifierNameMapping = new Map();

    // Create 10 dandisets
    for (let i = 0; i < 10; i += 1) {
      // Generate random dandiset name and description
      const name = faker.lorem.words();
      const description = faker.lorem.sentences();

      const identifier = await registerDandiset(name, description);
      await waitForRequestsToFinish();

      // Save dandiset identifier/name mapping so we can search for it later
      dandisetIdentifierNameMapping.set(identifier, name);
    }

    // Go to search page. Puppeteer crashes if you try to go to /dandiset/search directly
    // for some unknown reason; clicking the empty search bar and hitting the Enter key
    // accomplishes the same thing.
    await expect(page).toClickXPath(vTextField('Search Dandisets by name, description, identifier, or contributor name'));
    await page.keyboard.press('Enter');
    await waitForRequestsToFinish();

    // Configure the search filter to NOT exclude empty dandisets
    await expect(page).toClickXPath(vIcon('mdi-cog'));
    await page.waitForTimeout(500); // wait for the settings menu to open
    await expect(page).toClickXPath('//label[.= "Empty Dandisets"]');
    await page.waitForTimeout(500);
    await waitForRequestsToFinish();

    // Search for each dandiset we created above and assert that they show up in the search results
    for (const [dandisetIdentifier, dandisetName] of dandisetIdentifierNameMapping) {
      await expect(page).toFillXPath(vTextField('Search Dandisets by name, description, identifier, or contributor name'), dandisetIdentifierNameMapping.get(dandisetIdentifier));
      await page.keyboard.press('Enter');
      await waitForRequestsToFinish();

      // Assert that the dandiset we're looking for is in the search results
      await expect(page).toMatch(`DANDI:${dandisetIdentifier}`);
      await expect(page).toMatch(dandisetName);

      // Clear search box so that the xpath selector works again
      await page.keyboard.down('ControlLeft');
      await page.keyboard.press('KeyA');
      await page.keyboard.press('Backspace');
      await page.keyboard.up('ControlLeft');
      await page.keyboard.press('Tab');
    }
  });
});
