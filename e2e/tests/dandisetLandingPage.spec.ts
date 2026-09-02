import { expect, test, type Page } from "@playwright/test";
import { clientUrl, registerNewUser, LOGOUT_BUTTON_TEXT, registerDandiset } from "../utils.ts";
import { faker } from "@faker-js/faker";

test.describe("dandiset landing page", async () => {
  test("add an owner to the dandiset", async ({ page, browser }) => {
    // This test does 2 full user signups, a dandiset registration, and a dialog
    // interaction; under concurrent workers the default 30s budget is too tight.
    test.slow();
    // Create a user to add as an owner later
    const {
      email: otherUserEmail,
      firstname: otherUserFirstname,
      lastname: otherUserLastName,
    } = await registerNewUser(page);
    const otherUserName = `${otherUserFirstname} ${otherUserLastName}`;
    const otherUserInitials = `${otherUserFirstname.charAt(0)}${otherUserLastName.charAt(0)}`;
    // By default, getByRole does case-insensitive substring matches. If the user initials
    // appear as a substring in some other button on the page, this can cause issues finding
    // the avatar icon, so we have to use `exact: true`.
    await page.getByRole("button", { name: otherUserInitials, exact: true }).click();
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
    // With high concurrency, the default timeout of 5s was not enough, raising the
    // timeout reduces flakiness of this assertion.
    await expect(newPage.getByText(otherUserName)).toHaveCount(1, { timeout: 15000 });
    await context.close();
  });
  test("navigate to an invalid dandiset URL", async ({ page }) => {
    await page.goto(`${clientUrl}/dandiset/1`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Error: Dandiset does not exist")).toHaveCount(1);
  });

  test.describe("how to cite tab", () => {
    // Run these tests serially so we can create a single user + dandiset for the entire
    // set, instead of creating a fresh user + dandiset per-test. This reduces load on the
    // test server, which can cause flaky behavior.
    test.describe.configure({ mode: "serial" });

    let dandisetId: string | undefined;
    let page: Page;

    test.beforeAll(async ({ browser }) => {
      page = await browser.newPage();
      await registerNewUser(page);
      const dandisetName = faker.lorem.words();
      const dandisetDescription = faker.lorem.sentences();
      dandisetId = await registerDandiset(page, dandisetName, dandisetDescription);
    });

    test.afterAll(async () => {
      await page.close();
    });

    test("navigate to the How to Cite tab", async () => {
      // Click the "How to Cite" tab
      await page.getByRole("tab", { name: "How to Cite" }).click();

      // Verify the tab content is displayed
      await expect(page.getByText("How to Cite this Dataset")).toBeVisible();
    });

    test("displays draft warning for unpublished dandisets", async () => {
      await page.getByRole("tab", { name: "How to Cite" }).click();

      await expect(
        page.getByText("Citing draft dandisets is not recommended"),
      ).toBeVisible();
      await expect(
        page.getByText("Please contact the authors to request publication"),
      ).toBeVisible();
    });

    test("displays all expected sections", async () => {
      await page.getByRole("tab", { name: "How to Cite" }).click();

      // Check all section headers are present
      await expect(page.getByRole("heading", { name: "Full Citation" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Materials and Methods" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Data Availability Statement" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "DANDI Identifier" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "License" })).toBeVisible();
    });

    test("displays DANDI identifier with correct format", async () => {
      await page.getByRole("tab", { name: "How to Cite" }).click();

      // The identifier should follow the format DANDI:<id>/draft
      await expect(page.getByText(`DANDI:${dandisetId}/draft`)).toBeVisible();
      await expect(page.getByText("DANDI Archive RRID: SCR_017571")).toBeVisible();
    });

    test("displays citation format selector", async () => {
      await page.getByRole("tab", { name: "How to Cite" }).click();

      // The format dropdown should be visible with APA 7th as default
      await expect(page.getByText("APA 7th")).toBeVisible();
    });

    test("displays guide link", async () => {
      await page.getByRole("tab", { name: "How to Cite" }).click();

      await expect(
        page.getByRole("link", { name: "guide on citing dandisets" }),
      ).toBeVisible();
    });

    test("can switch back to Overview tab", async () => {
      await page.getByRole("tab", { name: "How to Cite" }).click();
      await expect(page.getByText("How to Cite this Dataset")).toBeVisible();

      await page.getByRole("tab", { name: "Overview" }).click();
      await expect(page.getByText("How to Cite this Dataset")).not.toBeVisible();
    });
  });
});
