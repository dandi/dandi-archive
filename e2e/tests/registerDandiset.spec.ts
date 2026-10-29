import { test, expect } from "@playwright/test";
import { gotoAndLogin } from "../utils.ts";

test.describe("dandiset registration page", async () => {
  test("register a dandiset", async ({ page }) => {
    await gotoAndLogin(page);

    await page.getByRole("link", { name: "New Dandiset" }).click();
    await page.getByLabel("Title").click();
    await page.getByLabel("Title").fill("My Dandiset");
    await page.getByLabel("Description").click();
    await page.getByLabel("Description").fill("My Dandiset Description");
    // Vuetify's v-select sets aria-label="Open" on its input, which overrides the
    // associated <label> in accessible-name computation, so getByLabel can't find it.
    await page.locator(".v-select").filter({ hasText: "License" }).click();
    await page.getByRole("option", { name: "spdx:CC0-" }).click();
    await page.getByRole("button", { name: "Register Dandiset" }).click();
    // Wait for the post-submit redirect to land on the new dandiset's page before
    // asserting on its content, instead of racing the default 5s expect timeout.
    await page.waitForURL(/\/dandiset\/\d+$/);

    await expect(page.getByText("Licenses: spdx:CC0-")).toHaveCount(1, { timeout: 15000 });
  });
});
