const VERSION_LINK_REGEX = /https:\/\/github.com\/dandi\/dandi-archive\/commit\/[0-9a-f]{5,40}/;

describe('home page stats', () => {
  it('checks version link', async () => {
    /* eslint-disable-next-line no-undef */
    const versionLink = await page.evaluate(() => document.querySelector('.version-link').getAttribute('href'));
    expect(versionLink).toMatch(VERSION_LINK_REGEX);
  });
});
