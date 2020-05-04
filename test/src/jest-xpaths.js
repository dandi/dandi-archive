import 'expect-puppeteer';

// Some extensions to the Jest expect API to better support XPaths
expect.extend({
  async toContainXPath(page, xpath) {
    try {
      await page.waitForXPath(xpath);
      return { pass: true };
    } catch (e) {
      return { pass: false, message: () => `XPath not found: ${xpath}` };
    }
  },
  async toClickXPath(page, xpath) {
    try {
      await (await page.waitForXPath(xpath)).click();
      return { pass: true };
    } catch (e) {
      return { pass: false, message: () => `XPath not found: ${xpath}` };
    }
  },
  async toFillXPath(page, xpath, text) {
    try {
      await (await page.waitForXPath(xpath)).type(text);
      return { pass: true };
    } catch (e) {
      return { pass: false, message: () => `XPath not found: ${xpath}` };
    }
  },
});
