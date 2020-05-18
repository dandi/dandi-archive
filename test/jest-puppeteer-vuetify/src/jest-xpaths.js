import 'expect-puppeteer';

// Some extensions to the Jest expect API to better support XPaths
global.expect.extend({
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
      const input = await page.waitForXPath(xpath);
      // triple click to select all text currently in the element
      await input.click({ clickCount: 3 });
      // typing will now overwrite the current text
      await input.type(text);
      return { pass: true };
    } catch (e) {
      return { pass: false, message: () => `XPath not found: ${xpath}` };
    }
  },
});
