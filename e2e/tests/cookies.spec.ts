import { test, expect } from "@playwright/test";
import { clientUrl } from "../utils.ts";

const COOKIE_CONSENT_MESSAGE = 'We use cookies to ensure you get the best experience on DANDI.';
const COOKIE_DISABLED_MESSAGE = 'We noticed you\'re blocking cookies - note that certain aspects of the site may not work.';

test.describe("Cookie banner behavior", async () => {
  test("cookie banner when cookies are enabled", async ({ page }) => {
    await page.goto(clientUrl);
    await expect(page.getByText(COOKIE_CONSENT_MESSAGE)).toHaveCount(1);
    await page.getByText("Got it!").click();
    await expect(page.getByText(COOKIE_CONSENT_MESSAGE)).toHaveCount(0);
  });
  test("cookie banner when cookies are disabled", async ({ page }) => {
    // https://github.com/microsoft/playwright/issues/30115#issuecomment-2020821987
    await page.addInitScript(() => {
      Object.defineProperty(navigator.__proto__, "cookieEnabled", { get: () => false });
    });
    await page.goto(clientUrl);

    await expect(page.getByText(COOKIE_DISABLED_MESSAGE)).toHaveCount(1);
    await page.getByText("Got it!").click();
    await expect(page.getByText(COOKIE_CONSENT_MESSAGE)).toHaveCount(0);
  });
});
