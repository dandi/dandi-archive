import { expect, test } from "@playwright/test";
import { clientUrl, registerNewUser, LOGOUT_BUTTON_TEXT, registerDandiset } from "../utils.ts";
import { faker } from "@faker-js/faker";

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
    await page.getByRole("menuitem", { name: LOGOUT_BUTTON_TEXT }).click();

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
});
