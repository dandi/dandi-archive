import { test, expect } from "@playwright/test";
import { clientUrl } from "../utils.ts";

const devDandisetId = "000001";

test.describe("File browser page", async () => {
  test("there is a file browser", async ({ page }) => {
    await page.goto(`${clientUrl}/#/dandiset/${devDandisetId}`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("link", { name: "Files" }).click()
    await page.waitForLoadState("networkidle");

    // Ensure the page has loaded with a folder
    await expect(page.getByText("foo 20 B")).toHaveCount(1);
  });
});
