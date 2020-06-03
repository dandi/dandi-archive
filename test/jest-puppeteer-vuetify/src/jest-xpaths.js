import { expect } from '@jest/globals';
// The "jest" package transitively depends on "@jest/globals". However,
// end users typically install "jest", so we depend on that as a
// "peerDependencies", to avoid the burden of end users having to explicitly
// install "@jest/globals".
// The fact that this package's depends on "*" version of "@jest/globals"
// and the fact that other test-ecosystem packages are unlikely to pull in
// conflicting versions of "@jest/globals" should still ensure that the
// version of "@jest/globals" implicitly installed by users resolves to the
// same one as what's imported / depended upon by this package.

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
