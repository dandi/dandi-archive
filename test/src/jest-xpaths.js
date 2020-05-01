import 'expect-puppeteer';

// Some extensions to the Jest expect API to better support XPaths
expect.extend({
  async toContainXPath(page, xpath) {
    return page.waitForXPath(xpath)
      .then(() => {
        return { pass: true }; s
      });
  },
  async toClickXPath(page, xpath) {
    return (await page.waitForXPath(xpath))
      .click()
      .then(() => {
        return { pass: true };
      });
  },
  async toFillXPath(page, xpath, text) {
    return (await page.waitForXPath(xpath))
      .type(text)
      .then(() => {
        return { pass: true };
      });
  }
});
