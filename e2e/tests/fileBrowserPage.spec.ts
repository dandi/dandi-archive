import { test, expect } from "@playwright/test";
import { clientUrl } from "../utils.ts";

const devDandisetId = "000003";

test.describe("File browser page", async () => {
  test("there is a file browser", async ({ page }) => {
    await page.goto(`${clientUrl}/#/dandiset/${devDandisetId}`);
    await page.getByRole("link", { name: "Files" }).click()

    // Ensure the page has loaded with a folder
    await expect(page.getByText("foo")).toHaveCount(1);
  });

  test("browser back from the file browser to a versionless landing page has no errors", async ({ page }) => {
    // Regression test for https://github.com/dandi/dandi-archive/issues/3004
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
    page.on("console", (msg) => {
      if (msg.type() === "error" || msg.type() === "warning") errors.push(`${msg.type()}: ${msg.text()}`);
    });

    const landingUrl = `${clientUrl}/dandiset/${devDandisetId}`;
    await page.goto(landingUrl);
    await expect(page).toHaveURL(landingUrl); // must stay versionless for this regression
    await page.getByRole("link", { name: "Files" }).click();
    await expect(page).toHaveURL(/\/files/);
    await expect(page.getByText("foo")).toHaveCount(1);

    await page.goBack();
    await expect(page).toHaveURL(landingUrl);
    await expect(page.getByText("foo")).toHaveCount(0); // file browser is gone
    await expect(page.getByRole("link", { name: "Files" })).toBeVisible();
    await page.waitForTimeout(250); // let any post-flush error surface

    expect(errors.filter((m) => m.includes("Missing required param"))).toEqual([]);
    await expect(page.getByText("Sorry, something went wrong on our side")).toBeHidden();
  });
});
