import { test, expect, type Page } from "@playwright/test";
import { clientUrl, gotoAndLogin } from "../utils.ts";

const noLicenseSelector = async (page: Page) => {
  await page.getByRole("tab", { name: "General Badge" }).click();
  await expect(page.getByText("LicenseNo less than 1 items")).toBeVisible();
};
const noContributorSelector = async (page: Page) => {
  await expect(
    page.getByRole("tab", { name: "Dandiset contributors Badge" }),
  ).toBeVisible();
};
const invalidLicenseSelector = async (page: Page) => {
  await page.getByRole("tab", { name: "General Badge" }).click();
  await expect(
    page.getByRole("button", { name: "License spdx:CC-BY-NC-" }),
  ).toBeVisible();
};
const titleTooLongSelector = async (page: Page) => {
  await page.getByRole("tab", { name: "General Badge" }).click();
  await expect(
    page.getByText("Dandiset title150 characters maximum"),
  ).toBeVisible();
};

const dandisetsToTest = [
  "000003",
  "000018",
  "000024",
  "000071",
  "000106",
  "000107",
  "000362",
];

const invalidDandisets = {
  "000018": [noLicenseSelector],
  "000024": [noContributorSelector, noLicenseSelector],
  "000071": [noContributorSelector],
  "000106": [invalidLicenseSelector],
  "000107": [invalidLicenseSelector, noContributorSelector],
  "000362": [titleTooLongSelector],
};

test.describe("Test meditor validation errors", async () => {
  test.beforeEach(async ({ page }) => {
    await gotoAndLogin(page);
  });

  for (const dandisetId of dandisetsToTest) {
    test(`Test dandiset ${dandisetId}`, async ({ page }) => {
      await page.goto(`${clientUrl}/#/dandiset/${dandisetId}/draft/`);
      await page.getByRole("button", { name: "Metadata" }).click();

      await page.getByLabel("Dandiset title").click();
      await page.keyboard.press("End");
      await page.keyboard.press("Space");
      await page.keyboard.press("Tab");
      await page.getByLabel("Dandiset title").click();
      await page.keyboard.press("End");
      await page.keyboard.press("Backspace");
      await page.keyboard.press("Tab");
      await page.locator(".v-card__actions > button").first().click();
      await page.waitForTimeout(3000);
      await page.waitForLoadState("networkidle");

      const validIcon = await page.locator(".v-card__actions > i");
      const iconClass = await validIcon.getAttribute("class");

      if (Object.keys(invalidDandisets).includes(dandisetId)) {
        expect(iconClass).toContain("mdi-alert-circle");
        const tests = invalidDandisets[dandisetId];
        for (const test of tests) {
          await test(page);
        }
      } else {
        expect(iconClass).toContain("mdi-checkbox-marked-circle");
      }
    });
  }
});
