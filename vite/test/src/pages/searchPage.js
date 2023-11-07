import {
  vIcon,
  vTextField,
  vToolbar,
  vListItem,
} from 'jest-puppeteer-vuetify';

/**
 * Searches for dandisets using the search bar on the search page
 *
 * @param {String} query
 */
export async function search(query) {
  await expect(page).toFillXPath(vToolbar() + vTextField(), query);
  await expect(page).toClickXPath(vIcon('mdi-magnify'));
  // TODO figure out a dynamic wait
  await page.waitForTimeout(2000);
}

/**
 * Gets the results currently visible on the search page
 */
export async function getSearchResults() {
  const elements = await page.$x(vListItem({ title: true, subtitle: true }));
  return Promise.all(elements.map(async (element) => {
    const name = await element.$eval('.v-list-item__title', (e) => e.innerText);
    const subtitle = await element.$eval('.v-list-item__subtitle', (e) => e.innerText);
    // TODO parse subtitles into something meaningful
    return { name, subtitle };
  }));
}
