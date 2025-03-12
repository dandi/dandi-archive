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
    await page.getByLabel("License").click()
    await page.getByRole("option", { name: "spdx:CC0-" }).click();
    await page.getByRole("button", { name: "Register Dandiset" }).click();

    await expect(page.getByText("Licenses: spdx:CC0-")).toHaveCount(1);
  });
});
