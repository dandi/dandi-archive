import { expect, test } from "@playwright/test";
import { clientUrl, registerNewUser, LOGOUT_BUTTON_TEXT, registerDandiset } from "../utils.ts";
import { faker } from "@faker-js/faker";
import { execSync } from "child_process";

test.describe("dandiset landing page", async () => {
  test("add an owner to the dandiset", async ({ page, browser }) => {
    // Create a user to add as an owner later
    const {
      email: otherUserEmail,
      firstname: otherUserFirstname,
      lastname: otherUserLastName,
    } = await registerNewUser(page);
    const otherUserName = `${otherUserFirstname} ${otherUserLastName}`;
    const otherUserInitials = `${otherUserFirstname.charAt(0)}${otherUserLastName.charAt(0)}`;
    await page.getByRole("button", { name: otherUserInitials }).click();
    await page.getByText(LOGOUT_BUTTON_TEXT).click();

    // Create a fresh browser context and page
    const context = await browser.newContext();
    const newPage = await context.newPage();

    // Create another user and a dandiset owned by them
    const { firstname: ownerFirstName, lastname: ownerLastName } = await registerNewUser(newPage);
    const ownerName = `${ownerFirstName} ${ownerLastName}`;
    const dandisetName = faker.lorem.words();
    const dandisetDescription = faker.lorem.sentences();
    await registerDandiset(newPage, dandisetName, dandisetDescription);
    await expect(newPage.getByText(otherUserName)).toHaveCount(0);
    await expect(newPage.getByText(ownerName)).toHaveCount(1);

    // Add the additional owner
    await newPage.getByRole("button", { name: "Manage Owners" }).click();
    await newPage.getByLabel("Filter users (by name/email)").click();
    await newPage.getByLabel("Filter users (by name/email)").fill(otherUserEmail);
    await newPage.keyboard.press(" ");
    await newPage.keyboard.press("Backspace");
    await newPage.waitForTimeout(250);
    await newPage.getByRole("dialog").getByRole("button").nth(1).click();
    await newPage.getByRole("button", { name: "Done" }).click();
    await expect(newPage.getByText(otherUserName)).toHaveCount(1);
    await context.close();
  });

  test("navigate to an invalid dandiset URL", async ({ page }) => {
    await page.goto(`${clientUrl}/dandiset/1`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Error: Dandiset does not exist")).toHaveCount(1);
  });

  test("draft dandiset shows dandiset DOI", async ({ page }) => {
    // Register a new user and create a dandiset
    await registerNewUser(page);
    const dandisetName = faker.lorem.words();
    const dandisetDescription = faker.lorem.sentences();
    const dandisetId = await registerDandiset(page, dandisetName, dandisetDescription);

    // Inject a DOI directly using Django management command
    const testDoi = `10.80507/dandi.${dandisetId}`;

    // Execute the Django management command to inject DOI
    try {
      execSync(`cd .. && python manage.py inject_doi ${dandisetId} --dandiset-version=draft --doi="${testDoi}"`, {
        stdio: 'inherit',
        timeout: 10000
      });
    } catch (error) {
      console.error('Failed to inject DOI:', error);
    }

    // Refresh the page to see the updated DOI
    await page.reload();
    await page.waitForLoadState("networkidle");

    // The draft version should show the injected Dandiset DOI
    await expect(page.getByText(testDoi)).toHaveCount(1);

    // Should not show a version DOI (since it's a draft)
    const versionDoiPattern = new RegExp(`10\\.(48324|80507)/dandi\\.${dandisetId}/`);
    await expect(page.getByText(versionDoiPattern)).toHaveCount(0);
  });
});
