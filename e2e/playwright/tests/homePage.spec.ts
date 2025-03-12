import { test, expect } from "@playwright/test";
import { clientUrl } from "../utils.ts";

const VERSION_LINK_REGEX = /https:\/\/github.com\/dandi\/dandi-archive\/commit\/[0-9a-f]{5,40}/;

test.describe("Home page stats", async () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(clientUrl);
    await page.waitForLoadState("networkidle");
    // close the cookie popup
    await page.getByText("Got it!").click();
  });
  test("check version link", async ({ page }) => {
    const versionLinkElement = await page.locator(".version-link").first();
    const versionLinkHref = await versionLinkElement.getAttribute("href");
    expect(versionLinkHref).toMatch(VERSION_LINK_REGEX);
  });
});
